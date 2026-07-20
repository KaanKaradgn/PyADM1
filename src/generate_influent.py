"""
generate_influent.py
=====================
9 gübre türü (+ hibrit karışımlar) için PyADM1_2_2 motorunun okuyabileceği
dinamik influent (digester_influent) CSV dosyaları üretir.

Tasarım kararları (2026-07, kullanıcı ile netleştirildi — önceki tasarımın yerini alır):
--------------------------------------------------------------------------------
1) KOMPOZİSYON: Her gübrenin içeriği feedstock_library.py'deki `inf_comp`
   fraksiyonlarına göre dağıtılır (X_xc baskın kompozit + küçük X_ch/X_pr/X_li +
   inert X_I/S_I). Böylece manure_config.py'deki disintegrasyon/stoich parametreleri
   (f_ch_xc, k_dis ...) X_xc üzerinden aktif hale gelir.

2) ORGANİK YÜK: GÜBREYE ÖZGÜ. Her gübrenin kendi tipik toplam COD'si
   (feedstock_library[...]['total_cod'], kgCOD/m^3) kullanılır. Ortak yük DEĞİL.

3) DEBİ (Q): DİNAMİK. Gerçek BSM2 debi profili yeni zaman eksenine yeniden
   örneklenerek gerçekçi besleme dalgalanması sağlanır (ort. ~183 m^3/gün).

4) SICAKLIK: MEVSİMSEL, 25–40 C. Kosinüs ile kış(25)->yaz(40) geçişi;
   PyADM1_2_2'nin CTM sıcaklık modelini besler (`temp` sütunu).

5) SÜRE / ADIM: 150 gün, 1 saatlik besleme (3601 satır).

6) SÜTUN FORMATI: PyADM1_2_2 motoru ('q_ad' ve 'temp' sütunları).

7) BAŞLANGIÇ DURUMU: Ortak digester_initial.csv kullanılır (gübreye göre değişmez;
   reaktörün tohum/inokulum durumudur).

Kullanım:
    python generate_influent.py                 # 9 gübre + örnek hibrit dosyası üretir
    python generate_influent.py sigir           # tek gübre
    python generate_influent.py sigir:70,tavuk:30   # hibrit karışım
"""

import os
import sys
import numpy as np
import pandas as pd

from feedstock_library import feedstock_library, create_hybrid_feedstock

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# GLOBAL AYARLAR
# ------------------------------------------------------------------
SIM_DAYS      = 150.0
DT_DAYS       = 1.0 / 24.0     # 1 saatlik adım

# Mevsimsel sıcaklık: kış(25) -> yaz(40); 25..40 C bandı
T_MEAN        = 32.5           # C
T_AMP         = 7.5            # C  -> MEAN +/- AMP = 25..40
T_PERIOD_DAYS = 300.0          # yarım periyot = 150 gün -> tam 25->40 taraması

# İnorganik taban değerler (tohum/tamponlama). Amonyak/alkalinite reaktörde
# protein ayrışmasıyla üretildiği için influent tabanı küçük tutulur.
S_IC_BASE     = 0.008          # kmole C/m^3
S_IN_BASE     = 0.002          # kmole N/m^3
S_ANION_BASE  = 0.0053
S_CATION_BASE = 0.0

# PyADM1_2_2 motorunun beklediği influent sütun sırası
COLUMNS = [
    "time",
    "S_su", "S_aa", "S_fa", "S_va", "S_bu", "S_pro", "S_ac", "S_h2", "S_ch4",
    "S_IC", "S_IN", "S_I",
    "X_xc", "X_ch", "X_pr", "X_li", "X_su", "X_aa", "X_fa", "X_c4", "X_pro",
    "X_ac", "X_h2", "X_I",
    "S_cation", "S_anion",
    "q_ad", "temp",
]

FRACTION_KEYS = ["X_xc", "X_ch", "X_pr", "X_li", "X_I", "S_I"]


# ------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ------------------------------------------------------------------
def normalize_fractions(inf_comp):
    """inf_comp fraksiyonlarını 1.0'a normalize eder."""
    total = sum(inf_comp.get(k, 0.0) for k in FRACTION_KEYS)
    if total <= 0:
        raise ValueError("inf_comp fraksiyon toplamı sıfır olamaz.")
    return {k: inf_comp.get(k, 0.0) / total for k in FRACTION_KEYS}


def temperature_profile(t_array):
    """Mevsimsel dinamik sıcaklık (C): kış 25 -> yaz 40."""
    return T_MEAN - T_AMP * np.cos(2 * np.pi * t_array / T_PERIOD_DAYS)


def dynamic_flow(t_array):
    """Gerçek BSM2 Q profilini yeni (saatlik) zaman eksenine yeniden örnekler.
    Referans dosya yoksa sinüzoidal + taban sentetik profile düşer."""
    ref = os.path.join(HERE, "digester_influent.csv")
    try:
        orig = pd.read_csv(ref, usecols=["time", "Q"])
        return np.interp(t_array, orig["time"].values, orig["Q"].values)
    except Exception:
        return 178.46 * (1.0 + 0.20 * np.sin(2 * np.pi * t_array))


def build_influent(fractions, total_cod, load=1.0, sim_days=SIM_DAYS, dt=DT_DAYS):
    """
    Verilen kompozisyon fraksiyonları ve toplam COD'den influent DataFrame üretir.

    fractions : {X_xc, X_ch, X_pr, X_li, X_I, S_I} fraksiyonları
    total_cod : gübrenin toplam COD'si [kgCOD/m^3]
    load      : opsiyonel yük çarpanı (konsantrasyonu ölçekler; stres senaryosu için)
    """
    fr = normalize_fractions(fractions)
    eff_cod = total_cod * load

    n = int(round(sim_days / dt)) + 1
    t = np.round(np.arange(n) * dt, 6)

    df = pd.DataFrame(0.0, index=range(n), columns=COLUMNS)
    df["time"] = t

    # COD fraksiyonlarını konsantrasyona çevir (zaman içinde sabit besleme kompozisyonu)
    df["X_xc"] = eff_cod * fr["X_xc"]
    df["X_ch"] = eff_cod * fr["X_ch"]
    df["X_pr"] = eff_cod * fr["X_pr"]
    df["X_li"] = eff_cod * fr["X_li"]
    df["X_I"]  = eff_cod * fr["X_I"]
    df["S_I"]  = eff_cod * fr["S_I"]

    # İnorganik taban değerler
    df["S_IC"]     = S_IC_BASE
    df["S_IN"]     = S_IN_BASE
    df["S_anion"]  = S_ANION_BASE
    df["S_cation"] = S_CATION_BASE

    # Dinamik debi + mevsimsel sıcaklık
    df["q_ad"] = dynamic_flow(t)
    df["temp"] = temperature_profile(t)

    return df


# ------------------------------------------------------------------
# ÜRETİM
# ------------------------------------------------------------------
def generate_for_key(key, out_dir=HERE):
    """Tek gübre için influent dosyası üretir."""
    data = feedstock_library[key]
    df = build_influent(data["inf_comp"], data["total_cod"])
    fname = os.path.join(out_dir, f"influent_{key}.csv")
    df.to_csv(fname, index=False)
    print(f"[OK] {data['name']:<32s} COD={data['total_cod']:>5.0f} kgCOD/m3  "
          f"{len(df)} satır -> {os.path.basename(fname)}")
    return fname


def generate_hybrid(mixture_dict, out_dir=HERE, label=None):
    """Hibrit karışım için influent dosyası üretir (kompozisyon + COD harmanlanır)."""
    fs = create_hybrid_feedstock(mixture_dict)
    df = build_influent(fs["inf_comp"], fs["total_cod"])
    if label is None:
        label = "hibrit_" + "_".join(f"{k}{int(v)}" for k, v in mixture_dict.items())
    fname = os.path.join(out_dir, f"influent_{label}.csv")
    df.to_csv(fname, index=False)
    print(f"[OK] {fs['name']:<40s} COD={fs['total_cod']:>5.1f}  -> {os.path.basename(fname)}")
    return fname


def parse_and_generate(arg):
    if ":" in arg:  # hibrit: "sigir:70,tavuk:30"
        mix = {}
        for part in arg.split(","):
            k, r = part.split(":")
            mix[k.strip()] = float(r.strip())
        return generate_hybrid(mix)
    if arg not in feedstock_library:
        raise KeyError(f"'{arg}' bulunamadı. Mevcut: {list(feedstock_library.keys())}")
    return generate_for_key(arg)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        parse_and_generate(sys.argv[1])
    else:
        for key in feedstock_library:
            generate_for_key(key)
        # Örnek hibrit: %70 sığır + %30 tavuk (klasik ko-digestion)
        generate_hybrid({"sigir": 70, "tavuk": 30})
