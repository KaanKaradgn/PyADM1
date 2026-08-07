"""
PyADM1_codigest.py  --  Cok-substratli (paralel havuzlu) ADM1 ko-digestion motoru
==================================================================================
Her substrat kendi disintegrasyon/hidroliz hizi (k_dis, k_hyd_*) ve kompozisyonu
(f_*_xc) ile AYRI bir partikul "treni" olarak modellenir. Trenler ortak bir
biyokimyasal cekirdegi (cozunmusler, VFA'lar, bakteri kutleleri, gazlar, pH)
besler. Boylece hizli ve yavas substratlar ayni anda kendi hizlarinda cozunur;
ko-digestion artik kinetik ORTALAMASI ile degil, fiziksel olarak dogru sekilde
temsil edilir.

Durum vektoru:  [ortak cekirdek: 34] + [tren basina 4] x (N+1)
  - Trenler 0..N-1 : beslenen gubreler (feedstock)
  - Tren N         : endojen/bozunma treni (standart ADM1 kinetigi; olen biyokutle
                     ve reaktor tohumu buraya gider)

Sicaklik: PyADM1_2_2 ile ayni CTM modeli (tum kinetikler alpha_T ile olceklenir)
ve van't Hoff dinamik denge sabitleri.
"""
import numpy as np
import scipy.integrate

# ---- CTM sicaklik carpani (PyADM1_2_2 ile ayni) ----
def get_ctm_multiplier(T, T_min=15.0, T_opt=37.0, T_max=44.0, T_ref=35.0):
    if T <= T_min or T >= T_max:
        return 0.0
    def core(t):
        num = (t - T_max) * ((t - T_min) ** 2)
        den = (T_opt - T_min) * ((T_opt - T_min) * (t - T_opt) - (T_opt - T_max) * (T_opt + T_min - 2 * t))
        return num / den
    return core(T) / core(T_ref)

# ---- Ortak cekirdek durum indeksleri (0..33) ----
(I_S_su, I_S_aa, I_S_fa, I_S_va, I_S_bu, I_S_pro, I_S_ac, I_S_h2, I_S_ch4,
 I_S_IC, I_S_IN, I_S_I, I_X_su, I_X_aa, I_X_fa, I_X_c4, I_X_pro, I_X_ac,
 I_X_h2, I_X_I, I_S_cat, I_S_ani, I_S_H, I_S_va_i, I_S_bu_i, I_S_pro_i,
 I_S_ac_i, I_S_hco3, I_S_co2, I_S_nh3, I_S_nh4, I_S_gh2, I_S_gch4, I_S_gco2) = range(34)
N_CORE = 34

CORE_NAMES = [
    "S_su", "S_aa", "S_fa", "S_va", "S_bu", "S_pro", "S_ac", "S_h2", "S_ch4",
    "S_IC", "S_IN", "S_I", "X_su", "X_aa", "X_fa", "X_c4", "X_pro", "X_ac",
    "X_h2", "X_I", "S_cation", "S_anion", "S_H_ion", "S_va_ion", "S_bu_ion",
    "S_pro_ion", "S_ac_ion", "S_hco3_ion", "S_co2", "S_nh3", "S_nh4_ion",
    "S_gas_h2", "S_gas_ch4", "S_gas_co2",
]

# Endojen/bozunma treni standart ADM1 parametreleri (Rosen BSM2)
ENDOGENOUS_PARAMS = {
    "name": "endojen (decay)",
    "kinetics": {"k_dis": 0.5, "k_hyd_ch": 10.0, "k_hyd_pr": 10.0, "k_hyd_li": 10.0},
    "stoich": {"f_ch_xc": 0.2, "f_pr_xc": 0.2, "f_li_xc": 0.3, "f_xI_xc": 0.2, "f_sI_xc": 0.1},
}


def _xc(train):  return N_CORE + 4 * train + 0   # X_xc  indeksi
def _ch(train):  return N_CORE + 4 * train + 1   # X_ch
def _pr(train):  return N_CORE + 4 * train + 2   # X_pr
def _li(train):  return N_CORE + 4 * train + 3   # X_li


def run_codigestion(feedstocks, df_initial, sim_days=150.0, dt=1.0/24.0,
                    temp_series=None, flow_series=None,
                    feed_cv_comp=0.0, feed_cv_cod=0.0, seed=0):
    """
    feedstocks: liste. Her eleman:
      {
        'name': str,
        'kinetics': {k_dis, k_hyd_ch, k_hyd_pr, k_hyd_li},   # manure_config
        'stoich':   {f_ch_xc, f_pr_xc, f_li_xc, f_xI_xc, f_sI_xc},
        'inf_comp': {X_xc, X_ch, X_pr, X_li, X_I, S_I},       # feedstock_library (fraksiyon)
        'total_cod': float,   # kgCOD/m^3
        'flow_share': float,  # bu gubrenin toplam debideki hacimsel payi (0..1)
      }
    df_initial: reaktor baslangic durumu (tek satir; klasik ADM1 kolonlari)
    temp_series, flow_series: opsiyonel; zaman dizisiyle ayni uzunlukta sicaklik(C)/debi.
                              Verilmezse sabit 35C / 178.46 kullanilir.
    """
    # ---- Sabitler (BSM2, PyADM1_2_2 ile ayni) ----
    R = 0.083145; T_base = 298.15; p_atm = 1.013
    V_liq = 3400.0; V_gas = 300.0
    k_L_a = 200.0; k_p = 5e4

    N_xc, N_I, N_aa, N_bac = 0.0376/14, 0.06/14, 0.007, 0.08/14
    C_xc, C_sI, C_ch, C_pr, C_li, C_xI, C_su, C_aa, C_fa, C_bu, C_pro, C_ac, C_bac, C_ch4, C_va = \
        0.02786, 0.03, 0.0313, 0.03, 0.022, 0.03, 0.0313, 0.03, 0.0217, 0.025, 0.0268, 0.0313, 0.0313, 0.0156, 0.024
    f_fa_li, f_h2_su, f_bu_su, f_pro_su, f_ac_su = 0.95, 0.19, 0.13, 0.27, 0.41
    f_h2_aa, f_va_aa, f_bu_aa, f_pro_aa, f_ac_aa = 0.06, 0.23, 0.26, 0.05, 0.40
    Y_su, Y_aa, Y_fa, Y_c4, Y_pro, Y_ac, Y_h2 = 0.1, 0.08, 0.06, 0.06, 0.04, 0.05, 0.06

    K_S_IN, k_m_su, K_S_su, k_m_aa, K_S_aa, k_m_fa, K_S_fa, K_I_h2_fa, k_m_c4, K_S_c4, \
        K_I_h2_c4, k_m_pro, K_S_pro, K_I_h2_pro, k_m_ac, K_S_ac, K_I_nh3, k_m_h2, K_S_h2 = \
        1e-4, 30, 0.5, 50, 0.3, 6, 0.4, 5e-6, 20, 0.2, 1e-5, 13, 0.1, 3.5e-6, 8, 0.15, 0.0018, 35, 7e-6
    k_dec = 0.02

    pH_UL_aa, pH_LL_aa, pH_UL_ac, pH_LL_ac, pH_UL_h2, pH_LL_h2 = 5.5, 4.0, 7.0, 6.0, 6.0, 5.0
    K_pH_aa = 10 ** (-(pH_LL_aa + pH_UL_aa) / 2.0); nn_aa = 3.0 / (pH_UL_aa - pH_LL_aa)
    K_pH_ac = 10 ** (-(pH_LL_ac + pH_UL_ac) / 2.0); n_ac = 3.0 / (pH_UL_ac - pH_LL_ac)
    K_pH_h2 = 10 ** (-(pH_LL_h2 + pH_UL_h2) / 2.0); n_h2 = 3.0 / (pH_UL_h2 - pH_LL_h2)
    K_a_va, K_a_bu, K_a_pro, K_a_ac = 10**-4.86, 10**-4.82, 10**-4.88, 10**-4.76

    # ---- Tren parametre dizileri (gubreler + endojen tren) ----
    trains = list(feedstocks) + [ENDOGENOUS_PARAMS]
    M = len(trains)
    ENDO = M - 1

    k_dis = np.array([tr["kinetics"]["k_dis"] for tr in trains])
    k_hyd_ch = np.array([tr["kinetics"]["k_hyd_ch"] for tr in trains])
    k_hyd_pr = np.array([tr["kinetics"]["k_hyd_pr"] for tr in trains])
    k_hyd_li = np.array([tr["kinetics"]["k_hyd_li"] for tr in trains])
    f_ch = np.array([tr["stoich"]["f_ch_xc"] for tr in trains])
    f_pr = np.array([tr["stoich"]["f_pr_xc"] for tr in trains])
    f_li = np.array([tr["stoich"]["f_li_xc"] for tr in trains])
    f_xI = np.array([tr["stoich"]["f_xI_xc"] for tr in trains])
    f_sI = np.array([tr["stoich"]["f_sI_xc"] for tr in trains])
    s1 = -C_xc + f_sI * C_sI + f_ch * C_ch + f_pr * C_pr + f_li * C_li + f_xI * C_xI

    # ---- Influent (trenlere gore) ----
    # Beslenen gubre trenleri icin akis-agirlikli konsantrasyon; endojen tren beslenmez.
    # Baz: her gubrenin COD yuku (_T) + komponent fraksiyonlari (_F). Salinim bunlara
    # carpan olarak uygulanip her adimda _set_influent ile guncellenir (kompozisyon +
    # total_cod stokastik dalgalanmasi -> gercekci hammadde degiskenligi).
    _COMP = ["X_xc", "X_ch", "X_pr", "X_li", "X_I", "S_I"]
    Nfeed = len(feedstocks)
    _T = np.array([fs["total_cod"] * fs.get("flow_share", 1.0) for fs in feedstocks])
    _F = np.array([[fs["inf_comp"].get(k, 0.0) for k in _COMP] for fs in feedstocks])
    Xxc_in = np.zeros(M); Xch_in = np.zeros(M); Xpr_in = np.zeros(M); Xli_in = np.zeros(M)
    XI_in_total = 0.0; SI_in_total = 0.0

    def _set_influent(mcod, mfrac):
        """mcod:(Nfeed,) total_cod carpani, mfrac:(Nfeed,6) komponent carpani."""
        nonlocal XI_in_total, SI_in_total
        Fi = _F * mfrac
        ssum = Fi.sum(axis=1, keepdims=True); ssum[ssum == 0] = 1.0
        Fi = Fi / ssum                          # oranlar kayar, toplam=1 (kompozisyon salinimi)
        conc = (_T * mcod)[:, None] * Fi         # (Nfeed,6) etkin konsantrasyon
        Xxc_in[:Nfeed] = conc[:, 0]; Xch_in[:Nfeed] = conc[:, 1]
        Xpr_in[:Nfeed] = conc[:, 2]; Xli_in[:Nfeed] = conc[:, 3]
        XI_in_total = float(conc[:, 4].sum()); SI_in_total = float(conc[:, 5].sum())

    _set_influent(np.ones(Nfeed), np.ones((Nfeed, 6)))   # salinimsiz baz

    # Cozunmus taban influent (ortak)
    # GUBRE-BASINA TAMPON: feed alkalinitesi (S_IC) ve katyon (S_cat) her gubrenin
    # kendi degerinden, akis-payi agirlikli olarak gelir. Gubreler yuksek (tamponlu),
    # asidik besinler (peynir suyu/melas/silaj) dusuk -> gercekci asitlesme/cokme.
    _tot_share = sum(fs.get("flow_share", 1.0) for fs in feedstocks) or 1.0
    S_IC_in  = sum(fs.get("s_ic_feed", 0.03) * fs.get("flow_share", 1.0) for fs in feedstocks) / _tot_share
    S_cat_in = sum(fs.get("s_cat_feed", 0.02) * fs.get("flow_share", 1.0) for fs in feedstocks) / _tot_share
    S_IN_in = 0.01; S_anion_in = 0.0053

    # ---- Baslangic durumu ----
    y0 = np.zeros(N_CORE + 4 * M)
    for idx, name in enumerate(CORE_NAMES):
        if name in df_initial.columns:
            y0[idx] = float(df_initial[name].iloc[0])
    # Reaktor tohumu (baslangic partikulleri) endojen trene konur
    for col, fn in (("X_xc", _xc), ("X_ch", _ch), ("X_pr", _pr), ("X_li", _li)):
        if col in df_initial.columns:
            y0[fn(ENDO)] = float(df_initial[col].iloc[0])

    # ---- ODE ----
    def ode(t, y, q_ad, T_c):
        T_k = T_c + 273.15
        alpha = get_ctm_multiplier(T_c)

        K_w_d = 10**-14.0 * np.exp((55900/(100*R)) * (1/T_base - 1/T_k))
        K_a_co2_d = 10**-6.35 * np.exp((7646/(100*R)) * (1/T_base - 1/T_k))
        K_a_IN_d = 10**-9.25 * np.exp((51965/(100*R)) * (1/T_base - 1/T_k))
        K_H_co2_d = 0.035 * np.exp((-19410/(100*R)) * (1/T_base - 1/T_k))
        K_H_ch4_d = 0.0014 * np.exp((-14240/(100*R)) * (1/T_base - 1/T_k))
        K_H_h2_d = 7.8e-4 * np.exp(-4180/(100*R) * (1/T_base - 1/T_k))
        p_h2o_d = 0.0313 * np.exp(5290 * (1/T_base - 1/T_k))

        # ortak cekirdek degiskenleri
        S_su, S_aa, S_fa = y[I_S_su], y[I_S_aa], y[I_S_fa]
        S_va, S_bu, S_pro, S_ac = y[I_S_va], y[I_S_bu], y[I_S_pro], y[I_S_ac]
        S_h2, S_ch4, S_IC, S_IN, S_I = y[I_S_h2], y[I_S_ch4], y[I_S_IC], y[I_S_IN], y[I_S_I]
        X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2 = (y[I_X_su], y[I_X_aa], y[I_X_fa],
                                                     y[I_X_c4], y[I_X_pro], y[I_X_ac], y[I_X_h2])
        X_I = y[I_X_I]
        S_cat, S_ani = y[I_S_cat], y[I_S_ani]
        S_H = y[I_S_H]; S_hco3 = y[I_S_hco3]; S_co2 = S_IC - S_hco3; S_nh3 = y[I_S_nh3]
        S_gh2, S_gch4, S_gco2 = y[I_S_gh2], y[I_S_gch4], y[I_S_gco2]

        # inhibisyon (ortak)
        I_pH_aa = (K_pH_aa**nn_aa)/(S_H**nn_aa + K_pH_aa**nn_aa)
        I_pH_ac = (K_pH_ac**n_ac)/(S_H**n_ac + K_pH_ac**n_ac)
        I_pH_h2 = (K_pH_h2**n_h2)/(S_H**n_h2 + K_pH_h2**n_h2)
        I_IN = 1/(1 + K_S_IN/S_IN)
        I_h2_fa = 1/(1 + S_h2/K_I_h2_fa)
        I_h2_c4 = 1/(1 + S_h2/K_I_h2_c4)
        I_h2_pro = 1/(1 + S_h2/K_I_h2_pro)
        I_nh3 = 1/(1 + S_nh3/K_I_nh3)
        I5 = I_pH_aa*I_IN; I7 = I5*I_h2_fa; I8 = I5*I_h2_c4; I10 = I5*I_h2_pro
        I11 = I_pH_ac*I_IN*I_nh3; I12 = I_pH_h2*I_IN

        # --- Tren hizlari (her substrat kendi hizinda) ---
        Xxc = y[N_CORE+0::4][:M]; Xch = y[N_CORE+1::4][:M]
        Xpr = y[N_CORE+2::4][:M]; Xli = y[N_CORE+3::4][:M]
        Rdis = k_dis * alpha * Xxc
        Rhch = k_hyd_ch * alpha * Xch
        Rhpr = k_hyd_pr * alpha * Xpr
        Rhli = k_hyd_li * alpha * Xli
        tot_hch = Rhch.sum(); tot_hpr = Rhpr.sum(); tot_hli = Rhli.sum()

        # --- Ortak uptake hizlari (sicaklikla olcekli) ---
        R5 = k_m_su*alpha * S_su/(K_S_su+S_su) * X_su * I5
        R6 = k_m_aa*alpha * S_aa/(K_S_aa+S_aa) * X_aa * I5
        R7 = k_m_fa*alpha * S_fa/(K_S_fa+S_fa) * X_fa * I7
        R8 = k_m_c4*alpha * S_va/(K_S_c4+S_va) * X_c4 * (S_va/(S_bu+S_va+1e-6)) * I8
        R9 = k_m_c4*alpha * S_bu/(K_S_c4+S_bu) * X_c4 * (S_bu/(S_bu+S_va+1e-6)) * I8
        R10 = k_m_pro*alpha * S_pro/(K_S_pro+S_pro) * X_pro * I10
        R11 = k_m_ac*alpha * S_ac/(K_S_ac+S_ac) * X_ac * I11
        R12 = k_m_h2*alpha * S_h2/(K_S_h2+S_h2) * X_h2 * I12
        # bozunma (decay)
        D_su=k_dec*X_su; D_aa=k_dec*X_aa; D_fa=k_dec*X_fa; D_c4=k_dec*X_c4
        D_pro=k_dec*X_pro; D_ac=k_dec*X_ac; D_h2=k_dec*X_h2
        sum_dec = D_su+D_aa+D_fa+D_c4+D_pro+D_ac+D_h2

        # gaz
        p_gh2 = S_gh2*R*T_k/16.0; p_gch4 = S_gch4*R*T_k/64.0; p_gco2 = S_gco2*R*T_k
        p_gas = p_gh2 + p_gch4 + p_gco2 + p_h2o_d
        q_gas = k_p*(p_gas - p_atm)
        if q_gas < 0: q_gas = 0.0
        RT8 = k_L_a*(S_h2 - 16*K_H_h2_d*p_gh2)
        RT9 = k_L_a*(S_ch4 - 64*K_H_ch4_d*p_gch4)
        RT10 = k_L_a*(S_co2 - K_H_co2_d*p_gco2)

        dy = np.zeros_like(y)
        qv = q_ad / V_liq

        # ortak cozunmusler (toplam hidroliz kullanilir)
        dy[I_S_su] = qv*(0 - S_su) + tot_hch + (1-f_fa_li)*tot_hli - R5
        dy[I_S_aa] = qv*(0 - S_aa) + tot_hpr - R6
        dy[I_S_fa] = qv*(0 - S_fa) + f_fa_li*tot_hli - R7
        dy[I_S_va] = qv*(0 - S_va) + (1-Y_aa)*f_va_aa*R6 - R8
        dy[I_S_bu] = qv*(0 - S_bu) + (1-Y_su)*f_bu_su*R5 + (1-Y_aa)*f_bu_aa*R6 - R9
        dy[I_S_pro] = qv*(0 - S_pro) + (1-Y_su)*f_pro_su*R5 + (1-Y_aa)*f_pro_aa*R6 + (1-Y_c4)*0.54*R8 - R10
        dy[I_S_ac] = qv*(0 - S_ac) + (1-Y_su)*f_ac_su*R5 + (1-Y_aa)*f_ac_aa*R6 + (1-Y_fa)*0.7*R7 \
                     + (1-Y_c4)*0.31*R8 + (1-Y_c4)*0.8*R9 + (1-Y_pro)*0.57*R10 - R11
        dy[I_S_h2] = 0.0  # DAE
        dy[I_S_ch4] = qv*(0 - S_ch4) + (1-Y_ac)*R11 + (1-Y_h2)*R12 - RT9

        # karbon dengesi Sigma (tren s1'leri + toplam hidroliz + ortak)
        s2 = -C_ch + C_su; s3 = -C_pr + C_aa; s4 = -C_li + (1-f_fa_li)*C_su + f_fa_li*C_fa
        s5 = -C_su + (1-Y_su)*(f_bu_su*C_bu + f_pro_su*C_pro + f_ac_su*C_ac) + Y_su*C_bac
        s6 = -C_aa + (1-Y_aa)*(f_va_aa*C_va + f_bu_aa*C_bu + f_pro_aa*C_pro + f_ac_aa*C_ac) + Y_aa*C_bac
        s7 = -C_fa + (1-Y_fa)*0.7*C_ac + Y_fa*C_bac
        s8 = -C_va + (1-Y_c4)*0.54*C_pro + (1-Y_c4)*0.31*C_ac + Y_c4*C_bac
        s9 = -C_bu + (1-Y_c4)*0.8*C_ac + Y_c4*C_bac
        s10 = -C_pro + (1-Y_pro)*0.57*C_ac + Y_pro*C_bac
        s11 = -C_ac + (1-Y_ac)*C_ch4 + Y_ac*C_bac
        s12 = (1-Y_h2)*C_ch4 + Y_h2*C_bac
        s13 = -C_bac + C_xc
        Sigma = (s1*Rdis).sum() + s2*tot_hch + s3*tot_hpr + s4*tot_hli \
                + s5*R5 + s6*R6 + s7*R7 + s8*R8 + s9*R9 + s10*R10 + s11*R11 + s12*R12 + s13*sum_dec

        dy[I_S_IC] = qv*(S_IC_in - S_IC) - Sigma - RT10
        # azot: tren disintegrasyon terimleri + ortak biyokutle terimleri
        dis_N = ((N_xc - f_xI*N_I - f_sI*N_I - f_pr*N_aa) * Rdis).sum()
        dy[I_S_IN] = qv*(S_IN_in - S_IN) + dis_N - Y_su*N_bac*R5 + (N_aa - Y_aa*N_bac)*R6 \
                     - Y_fa*N_bac*R7 - Y_c4*N_bac*R8 - Y_c4*N_bac*R9 - Y_pro*N_bac*R10 \
                     - Y_ac*N_bac*R11 - Y_h2*N_bac*R12 + (N_bac - N_xc)*sum_dec
        dy[I_S_I] = qv*(SI_in_total - S_I) + (f_sI*Rdis).sum()

        # ortak bakteri kutleleri
        dy[I_X_su] = qv*(0 - X_su) + Y_su*R5 - D_su
        dy[I_X_aa] = qv*(0 - X_aa) + Y_aa*R6 - D_aa
        dy[I_X_fa] = qv*(0 - X_fa) + Y_fa*R7 - D_fa
        dy[I_X_c4] = qv*(0 - X_c4) + Y_c4*R8 + Y_c4*R9 - D_c4
        dy[I_X_pro] = qv*(0 - X_pro) + Y_pro*R10 - D_pro
        dy[I_X_ac] = qv*(0 - X_ac) + Y_ac*R11 - D_ac
        dy[I_X_h2] = qv*(0 - X_h2) + Y_h2*R12 - D_h2
        dy[I_X_I] = qv*(XI_in_total - X_I) + (f_xI*Rdis).sum()

        dy[I_S_cat] = qv*(S_cat_in - S_cat)   # gubre-basina feed katyonu (akis-payi agirlikli)
        dy[I_S_ani] = qv*(S_anion_in - S_ani)

        # trenler
        for m in range(M):
            b = N_CORE + 4*m
            dy[b+0] = qv*(Xxc_in[m] - Xxc[m]) - Rdis[m] + (sum_dec if m == ENDO else 0.0)
            dy[b+1] = qv*(Xch_in[m] - Xch[m]) + f_ch[m]*Rdis[m] - Rhch[m]
            dy[b+2] = qv*(Xpr_in[m] - Xpr[m]) + f_pr[m]*Rdis[m] - Rhpr[m]
            dy[b+3] = qv*(Xli_in[m] - Xli[m]) + f_li[m]*Rdis[m] - Rhli[m]

        # gaz fazi
        dy[I_S_gh2] = -q_gas/V_gas*S_gh2 + RT8*V_liq/V_gas
        dy[I_S_gch4] = -q_gas/V_gas*S_gch4 + RT9*V_liq/V_gas
        dy[I_S_gco2] = -q_gas/V_gas*S_gco2 + RT10*V_liq/V_gas
        # ion/DAE durumlari sabit (diff=0)
        return dy

    # ---- DAESolve (S_H_ion + S_h2), ortak cekirdek uzerinde ----
    def dae_solve(y, q_ad, T_c):
        T_k = T_c + 273.15
        alpha = get_ctm_multiplier(T_c)
        K_w_d = 10**-14.0 * np.exp((55900/(100*R)) * (1/T_base - 1/T_k))
        K_a_co2_d = 10**-6.35 * np.exp((7646/(100*R)) * (1/T_base - 1/T_k))
        K_a_IN_d = 10**-9.25 * np.exp((51965/(100*R)) * (1/T_base - 1/T_k))
        K_H_h2_d = 7.8e-4 * np.exp(-4180/(100*R) * (1/T_base - 1/T_k))

        S_va, S_bu, S_pro, S_ac = y[I_S_va], y[I_S_bu], y[I_S_pro], y[I_S_ac]
        S_IC, S_IN = y[I_S_IC], y[I_S_IN]
        S_cat, S_ani = y[I_S_cat], y[I_S_ani]
        S_su, S_aa, S_fa = y[I_S_su], y[I_S_aa], y[I_S_fa]
        X_su, X_aa, X_fa, X_c4, X_pro, X_h2 = (y[I_X_su], y[I_X_aa], y[I_X_fa],
                                               y[I_X_c4], y[I_X_pro], y[I_X_h2])
        S_gh2 = y[I_S_gh2]
        tol, maxit, eps = 1e-12, 1000, 1e-7

        # --- S_H_ion (Newton) ---
        S_H = y[I_S_H] if y[I_S_H] > 0 else 1e-7
        prev_SH = S_H
        for _ in range(maxit):
            S_va_i = K_a_va*S_va/(K_a_va+S_H); S_bu_i = K_a_bu*S_bu/(K_a_bu+S_H)
            S_pro_i = K_a_pro*S_pro/(K_a_pro+S_H); S_ac_i = K_a_ac*S_ac/(K_a_ac+S_H)
            S_hco3 = K_a_co2_d*S_IC/(K_a_co2_d+S_H); S_nh3 = K_a_IN_d*S_IN/(K_a_IN_d+S_H)
            delta = (S_cat + (S_IN - S_nh3) + S_H - S_hco3 - S_ac_i/64.0 - S_pro_i/112.0
                     - S_bu_i/160.0 - S_va_i/208.0 - K_w_d/S_H - S_ani)
            grad = (1 + K_a_IN_d*S_IN/((K_a_IN_d+S_H)**2) + K_a_co2_d*S_IC/((K_a_co2_d+S_H)**2)
                    + 1/64.0*K_a_ac*S_ac/((K_a_ac+S_H)**2) + 1/112.0*K_a_pro*S_pro/((K_a_pro+S_H)**2)
                    + 1/160.0*K_a_bu*S_bu/((K_a_bu+S_H)**2) + 1/208.0*K_a_va*S_va/((K_a_va+S_H)**2)
                    + K_w_d/(S_H**2))
            S_H = S_H - delta/grad
            if S_H <= 0: S_H = tol
            if abs(delta) < tol: break

        # --- S_h2 (Newton), ortak uptake ile ---
        S_h2 = y[I_S_h2] if y[I_S_h2] > 0 else 1e-8
        km_fa=k_m_fa*alpha; km_c4=k_m_c4*alpha; km_pro=k_m_pro*alpha; km_h2=k_m_h2*alpha
        km_su=k_m_su*alpha; km_aa=k_m_aa*alpha
        I_pH_aa = (K_pH_aa**nn_aa)/(prev_SH**nn_aa + K_pH_aa**nn_aa)
        I_pH_h2 = (K_pH_h2**n_h2)/(prev_SH**n_h2 + K_pH_h2**n_h2)
        I_IN = 1/(1 + K_S_IN/S_IN)
        for _ in range(maxit):
            I_h2_fa = 1/(1+S_h2/K_I_h2_fa); I_h2_c4 = 1/(1+S_h2/K_I_h2_c4); I_h2_pro = 1/(1+S_h2/K_I_h2_pro)
            I5 = I_pH_aa*I_IN; I7 = I5*I_h2_fa; I8 = I5*I_h2_c4; I10 = I5*I_h2_pro; I12 = I_pH_h2*I_IN
            R5 = km_su*(S_su/(K_S_su+S_su))*X_su*I5
            R6 = km_aa*(S_aa/(K_S_aa+S_aa))*X_aa*I5
            R7 = km_fa*(S_fa/(K_S_fa+S_fa))*X_fa*I7
            R8 = km_c4*(S_va/(K_S_c4+S_va))*X_c4*(S_va/(S_bu+S_va+1e-6))*I8
            R9 = km_c4*(S_bu/(K_S_c4+S_bu))*X_c4*(S_bu/(S_bu+S_va+1e-6))*I8
            R10 = km_pro*(S_pro/(K_S_pro+S_pro))*X_pro*I10
            R12 = km_h2*(S_h2/(K_S_h2+S_h2))*X_h2*I12
            p_gh2 = S_gh2*R*T_k/16.0
            RT8 = k_L_a*(S_h2 - 16*K_H_h2_d*p_gh2)
            d = ((1-Y_su)*f_h2_su*R5 + (1-Y_aa)*f_h2_aa*R6 + (1-Y_fa)*0.3*R7
                 + (1-Y_c4)*0.15*R8 + (1-Y_c4)*0.2*R9 + (1-Y_pro)*0.43*R10 - R12 - RT8)
            g = (- 3.0/10.0*(1-Y_fa)*km_fa*S_fa/(K_S_fa+S_fa)*X_fa*I_pH_aa/(1+K_S_IN/S_IN)/((1+S_h2/K_I_h2_fa)**2)/K_I_h2_fa
                 - 3.0/20.0*(1-Y_c4)*km_c4*S_va*S_va/(K_S_c4+S_va)*X_c4/(S_bu+S_va+eps)*I_pH_aa/(1+K_S_IN/S_IN)/((1+S_h2/K_I_h2_c4)**2)/K_I_h2_c4
                 - 1.0/5.0*(1-Y_c4)*km_c4*S_bu*S_bu/(K_S_c4+S_bu)*X_c4/(S_bu+S_va+eps)*I_pH_aa/(1+K_S_IN/S_IN)/((1+S_h2/K_I_h2_c4)**2)/K_I_h2_c4
                 - 43.0/100.0*(1-Y_pro)*km_pro*S_pro/(K_S_pro+S_pro)*X_pro*I_pH_aa/(1+K_S_IN/S_IN)/((1+S_h2/K_I_h2_pro)**2)/K_I_h2_pro
                 - km_h2/(K_S_h2+S_h2)*X_h2*I_pH_h2/(1+K_S_IN/S_IN)
                 + km_h2*S_h2/((K_S_h2+S_h2)**2)*X_h2*I_pH_h2/(1+K_S_IN/S_IN) - k_L_a)
            S_h2 = S_h2 - d/g
            if S_h2 <= 0: S_h2 = tol
            if abs(d) < tol: break

        # sonuclari yaz
        y[I_S_H] = S_H; y[I_S_h2] = S_h2
        y[I_S_va_i] = K_a_va*S_va/(K_a_va+S_H); y[I_S_bu_i] = K_a_bu*S_bu/(K_a_bu+S_H)
        y[I_S_pro_i] = K_a_pro*S_pro/(K_a_pro+S_H); y[I_S_ac_i] = K_a_ac*S_ac/(K_a_ac+S_H)
        y[I_S_hco3] = K_a_co2_d*S_IC/(K_a_co2_d+S_H); y[I_S_nh3] = K_a_IN_d*S_IN/(K_a_IN_d+S_H)
        y[I_S_co2] = S_IC - y[I_S_hco3]; y[I_S_nh4] = S_IN - y[I_S_nh3]
        return y

    # ---- Zaman dongusu ----
    n = int(round(sim_days / dt)) + 1
    times = np.round(np.arange(n) * dt, 6)
    if temp_series is None:
        temp_series = np.full(n, 35.0)
    if flow_series is None:
        flow_series = np.full(n, 178.46)

    # ---- Besleme salinimi (yumusak, tohumlu): kompozisyon + total_cod ----
    rng = np.random.default_rng(seed)
    def _smooth_mult(cv, shape):
        if cv <= 0:
            return np.ones((n,) + shape)
        node = max(1, int(round(2.0 / dt)))        # ~2 gunde bir dugum -> yumusak git-gel
        idx = np.arange(0, n, node)
        vals = rng.normal(0.0, cv, size=(len(idx),) + shape)
        full = np.empty((n,) + shape)
        for j in np.ndindex(shape):
            full[(slice(None),) + j] = np.interp(np.arange(n), idx, vals[(slice(None),) + j])
        return np.clip(1.0 + full, 1 - 3*cv, 1 + 3*cv)
    cod_mult  = _smooth_mult(feed_cv_cod,  (Nfeed,))
    frac_mult = _smooth_mult(feed_cv_comp, (Nfeed, 6))

    import pandas as pd
    y = y0.copy()
    rows = [y.copy()]
    inflow = [np.zeros(6)]                          # anlik harmanlanmis influent (t=0 placeholder)
    for i in range(1, n):
        _set_influent(cod_mult[i], frac_mult[i])    # bu adimin beslemesi (salinimli)
        inflow.append(np.array([Xxc_in[:Nfeed].sum(), Xch_in[:Nfeed].sum(),
                                Xpr_in[:Nfeed].sum(), Xli_in[:Nfeed].sum(),
                                XI_in_total, SI_in_total]))
        q_ad = float(flow_series[i]); T_c = float(temp_series[i])
        sol = scipy.integrate.solve_ivp(ode, [times[i-1], times[i]], y,
                                        args=(q_ad, T_c), method="DOP853")
        y = sol.y[:, -1].copy()
        y = dae_solve(y, q_ad, T_c)
        rows.append(y.copy())

    Y = np.array(rows)
    # ---- Cikti: ortak cekirdek + toplam partikuller (plot_results uyumlu) ----
    out = pd.DataFrame({name: Y[:, idx] for idx, name in enumerate(CORE_NAMES)})
    out.insert(0, "time", times)
    # toplam partikuller (tum trenlerin toplami)
    out["X_xc"] = Y[:, [_xc(m) for m in range(M)]].sum(axis=1)
    out["X_ch"] = Y[:, [_ch(m) for m in range(M)]].sum(axis=1)
    out["X_pr"] = Y[:, [_pr(m) for m in range(M)]].sum(axis=1)
    out["X_li"] = Y[:, [_li(m) for m in range(M)]].sum(axis=1)
    # her tren icin ayri kompozit (inceleme icin)
    for m, tr in enumerate(trains):
        out[f"X_xc_train{m}"] = Y[:, _xc(m)]
    out["pH"] = -np.log10(np.clip(Y[:, I_S_H], 1e-14, None))

    # ---- Biyogaz uretim debileri (her adimin sicakligina gore) ----
    T_k_arr = temp_series + 273.15
    p_h2 = Y[:, I_S_gh2] * R * T_k_arr / 16.0
    p_ch4 = Y[:, I_S_gch4] * R * T_k_arr / 64.0
    p_co2 = Y[:, I_S_gco2] * R * T_k_arr
    p_h2o = 0.0313 * np.exp(5290 * (1/T_base - 1/T_k_arr))
    p_tot = p_h2 + p_ch4 + p_co2 + p_h2o
    q_gas = np.clip(k_p * (p_tot - p_atm), 0.0, None)      # toplam biyogaz debisi [m3/gun]
    q_ch4 = np.where(p_tot > 0, q_gas * p_ch4 / p_tot, 0.0)  # metan uretim debisi [m3/gun]
    out["q_gas"] = q_gas
    out["q_ch4"] = q_ch4
    out["ch4_pct"] = np.where(p_tot > 0, 100.0 * p_ch4 / p_tot, 0.0)  # metan icerigi [%]

    # ---- Anlik harmanlanmis influent (miktar-tabanli feature'lar) + debi ----
    infl = np.array(inflow)
    for j, nm in enumerate(["in_X_xc", "in_X_ch", "in_X_pr", "in_X_li", "in_X_I", "in_S_I"]):
        out[nm] = infl[:, j]
    out["q_ad"] = flow_series
    return out
