"""
build_dataset.py -- ADM1 ko-digestion ML veri seti üretici
===========================================================
Koşum matrisini (karışım × HRT/yük × çökme) çalıştırır, her koşumdan zaman-serisi
FEATURE tablosu + q_ch4 ETİKETİ + REJİM etiketi çıkarır, hepsini tek CSV'de birleştirir.

Feature felsefesi:
  - Besleme: ANLIK harmanlanmış MİKTAR (in_X_*), yüzdelik değil (miktar = COD×pay×fraksiyon,
    kompozisyon+total_cod salınımı yansımış). Sabit-uzunluk -> mono ve co-digestion tek modelde.
  - İşletme: debi (q_ad), HRT, sıcaklık.
  - Kinetik (harmanlanmış): k_dis, k_hyd_* (karışımın karakteri).
  - Reaktör durumu: pH, VFA (ac/pro/bu/va), S_IN, S_IC, S_nh3, gaz -> çökme nedeni
    (asit/amonyak/tampon) DURUM üzerinden görünür (gizli değişken yok).
  - Autoregresyon: q_ch4 gecikmeleri (lag 1-3).
Etiket: q_ch4 (+ ch4_pct, q_gas) ve rejim (healthy/overload/recovery/acidified/ammonia_stress).
"""
import numpy as np, pandas as pd, warnings, scipy.integrate
warnings.filterwarnings("ignore")
from feedstock_library import feedstock_library as FL
from manure_config import ADM1Simulator
import PyADM1_codigest as eng
from crash_generator import build_profiles, label_health_from_state

# Hız için LSODA (stiff-uyumlu; steady-state DOP853 ile ayni, cok daha hizli).
_o = scipy.integrate.solve_ivp
eng.scipy.integrate.solve_ivp = lambda f, span, y0, args=None, **k: _o(f, span, y0, args=args, method="LSODA")

V_LIQ = 3400.0
SIMM = ADM1Simulator()

STATE_FEATS = ["pH", "S_ac", "S_pro", "S_bu", "S_va", "S_IN", "S_IC", "S_nh3",
               "S_gas_ch4", "S_gas_co2", "X_ac", "X_h2"]
IN_FEATS = ["in_X_xc", "in_X_ch", "in_X_pr", "in_X_li", "in_X_I", "in_S_I"]


def build_fs(mix):
    out = []
    for k, sh in mix.items():
        mc = SIMM.manure_data[k]; fl = FL[k]
        out.append({"name": mc["name"], "kinetics": mc["kinetics"], "stoich": mc["stoich"],
                    "inf_comp": fl["inf_comp"], "total_cod": fl["total_cod"],
                    "s_ic_feed": fl["s_ic_feed"], "s_cat_feed": fl["s_cat_feed"], "flow_share": sh})
    return out


def blended_kinetics(mix):
    tot = sum(mix.values())
    ks = {"k_dis": 0, "k_hyd_ch": 0, "k_hyd_pr": 0, "k_hyd_li": 0}
    for k, sh in mix.items():
        for kk in ks:
            ks[kk] += SIMM.manure_data[k]["kinetics"][kk] * sh / tot
    return ks


def run_scenario(spec, downsample_days=1.0):
    """spec: dict(id, mix, hrt, crashes, temp_mode, cv_comp, cv_cod, seed)"""
    days = spec.get("days", 120.0); dt = spec.get("dt", 1.0)
    cod_mix = sum(FL[k]["total_cod"] * sh for k, sh in spec["mix"].items()) / sum(spec["mix"].values())
    prof = build_profiles(days, dt, cod_mix, hrt=spec["hrt"],
                          temp_mode=spec.get("temp_mode", "const"),
                          temp_const=spec.get("temp_const", 37.0),
                          crashes=spec.get("crashes"), seed=spec["seed"])
    # Isıtma arızası: sıcaklık geçici düşer -> aktivite (α_T) düşer -> metan düşer
    if spec.get("temp_drop"):
        td = spec["temp_drop"]
        m = (prof["times"] >= td["start_day"]) & (prof["times"] < td["start_day"] + td["duration"])
        prof["temp"][m] = td["to"]
        prof["regime"][m] = "temp_stress"
    out = eng.run_codigestion(build_fs(spec["mix"]), pd.read_csv("digester_initial.csv"),
                              sim_days=days, dt=dt, temp_series=prof["temp"], flow_series=prof["flow"],
                              feed_cv_comp=spec.get("cv_comp", 0.05),
                              feed_cv_cod=spec.get("cv_cod", 0.06), seed=spec["seed"])
    df = pd.DataFrame({"time": out["time"]})
    # --- Besleme miktarlari + isletme ---
    for c in IN_FEATS:
        df[c] = out[c].values
    df["q_ad"] = out["q_ad"].values
    df["HRT"] = V_LIQ / out["q_ad"].values
    df["temp"] = prof["temp"]
    # --- Sıcaklığa bağlı DİNAMİK kinetik: k_eff = k_base × α_T(temp) (CTM) ---
    alpha = np.array([eng.get_ctm_multiplier(float(T)) for T in prof["temp"]])
    df["alpha_T"] = alpha
    for kk, vv in blended_kinetics(spec["mix"]).items():
        df[kk] = vv * alpha         # dinamik efektif kinetik (her adım sıcaklıkla değişir)
        df[kk + "_base"] = vv        # taban/karakter (sabit, referans)
    # --- Reaktor durumu ---
    for c in STATE_FEATS:
        df[c] = out[c].values if c in out.columns else np.nan
    # --- Autoregresyon (q_ch4 gecikmeleri) ---
    q = out["q_ch4"].values
    for L in (1, 2, 3):
        df[f"q_ch4_lag{L}"] = pd.Series(q).shift(L).values
    # --- Etiketler ---
    df["q_ch4"] = q
    df["q_gas"] = out["q_gas"].values
    df["ch4_pct"] = out["ch4_pct"].values
    # rejim: enjekte edilen olay (crash_generator) + durumdan turetilen saglik
    reg_event = prof["regime"]
    reg_state = label_health_from_state(out)
    regime = np.array(reg_event, dtype=object)
    # durum-tabanli asit/amonyak, 'healthy' event'lerin uzerine yazar (daha bilgilendirici)
    for i in range(len(regime)):
        if regime[i] == "healthy" and reg_state[i] != "healthy":
            regime[i] = reg_state[i]
    df["regime"] = regime
    df["scenario"] = spec["id"]
    df["mix"] = "+".join(f"{k}{int(100*sh/sum(spec['mix'].values()))}" for k, sh in spec["mix"].items())
    # ilk 10 gunu (baslangic transiyenti) at + gunluk downsample
    df = df[df["time"] >= 10.0].iloc[::max(1, int(downsample_days/dt))].reset_index(drop=True)
    return df


# ---- KOŞUM MATRİSİ (prototip) ----
RUN_MATRIX = [
    # sağlıklı — farklı sıcaklık rejimleri
    dict(id="H1", mix={"sigir": 1.0}, hrt=30, temp_mode="const", temp_const=37, crashes=None, seed=1),
    dict(id="H2", mix={"sigir": 0.6, "misir_silaji": 0.4}, hrt=28, temp_mode="seasonal", crashes=None, seed=2),
    dict(id="H3", mix={"tavuk": 0.5, "sigir": 0.5}, hrt=32, temp_mode="const", temp_const=33, crashes=None, seed=3),
    dict(id="H4", mix={"aritma_camuru": 0.5, "misir_silaji": 0.5}, hrt=30, temp_mode="seasonal", crashes=None, seed=7),
    # geçici aşırı yük (stres+toparlanma)
    dict(id="S1", mix={"misir_silaji": 0.7, "sigir": 0.3}, hrt=25, temp_mode="const", temp_const=37,
         crashes=[{"type": "overload", "start_day": 45, "duration": 6, "magnitude": 3.5}], seed=4),
    # ısıtma arızası (sıcaklık 37->20, 15 gün) -> aktivite düşer
    dict(id="T1", mix={"sigir": 0.5, "misir_silaji": 0.5}, hrt=28, temp_mode="const", temp_const=37,
         temp_drop={"start_day": 40, "duration": 15, "to": 20}, seed=8),
    # washout çöküşü (sürekli kısa HRT)
    dict(id="C1", mix={"misir_silaji": 1.0}, hrt=7, temp_mode="const", temp_const=37, crashes=None, seed=5),
    # asidik besin yüksek yükte çöküş
    dict(id="C2", mix={"peynir_alti_suyu": 0.7, "seker_pancari_posasi": 0.3}, hrt=9, temp_mode="const", temp_const=37, crashes=None, seed=6),
]


def main(out_path="adm1_ml_dataset.csv"):
    frames = []
    for spec in RUN_MATRIX:
        df = run_scenario(spec)
        frames.append(df)
        print(f"  {spec['id']:4} {df['mix'].iloc[0]:28} satır={len(df):4}  "
              f"rejim={dict(df['regime'].value_counts())}")
    master = pd.concat(frames, ignore_index=True).dropna().reset_index(drop=True)
    master.to_csv(out_path, index=False)
    return master


if __name__ == "__main__":
    m = main()
    print("\nTOPLAM:", len(m), "satır |", len(m.columns), "sütun")
    print("Rejim dağılımı:", dict(m["regime"].value_counts()))
    print("Sütunlar:", list(m.columns))
