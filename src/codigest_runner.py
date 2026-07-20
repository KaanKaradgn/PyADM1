"""
codigest_runner.py  --  App <-> cok-substratli motor kopru katmani
===================================================================
Secilen gubre karisimindan (anahtar + oran) besleme listesini kurar, mevsimsel
sicaklik ve dinamik debi profillerini BELLEKTE uretir (ayri influent dosyasi
YOK) ve PyADM1_codigest.run_codigestion motorunu calistirir.

Kompozisyon feedstock_library'den, kinetik/stokiyometri manure_config'ten gelir.
Ko-digestion artik kinetik ORTALAMASI ile degil, her substratin ayri havuzuyla
modellenir.
"""
import os
import numpy as np

from manure_config import ADM1Simulator
from feedstock_library import feedstock_library
from PyADM1_codigest import run_codigestion

HERE = os.path.dirname(os.path.abspath(__file__))

# Mevsimsel sicaklik varsayilanlari (25..40 C, kis->yaz)
T_MEAN, T_AMP, T_PERIOD = 32.5, 7.5, 300.0


def build_feedstocks(mix_dict):
    """mix_dict ({'sigir':70,'tavuk':30}) -> motor besleme listesi.
    Oranlar hacimsel akis payina (flow_share, toplam=1) normalize edilir."""
    total = sum(mix_dict.values())
    if total <= 0:
        raise ValueError("Karisim oranlari toplami 0 olamaz.")
    sim = ADM1Simulator()
    out = []
    for key, w in mix_dict.items():
        if key not in sim.manure_data or key not in feedstock_library:
            raise KeyError(f"'{key}' manure_config/feedstock_library'de yok.")
        mc = sim.manure_data[key]
        fl = feedstock_library[key]
        out.append({
            "name": mc["name"],
            "kinetics": mc["kinetics"],
            "stoich": mc["stoich"],
            "inf_comp": fl["inf_comp"],
            "total_cod": fl["total_cod"],
            "flow_share": w / total,
        })
    return out


def seasonal_temp_series(times):
    """Mevsimsel sicaklik (C): kis 25 -> yaz 40."""
    return T_MEAN - T_AMP * np.cos(2 * np.pi * times / T_PERIOD)


def dynamic_flow_series(times):
    """Gercek BSM2 debi profilini yeni zaman eksenine yeniden ornekler (dosya
    URETMEZ; sadece sekil sablonu olarak okur). Referans yoksa sentetik profile
    duser."""
    ref = os.path.join(HERE, "digester_influent.csv")
    try:
        import pandas as pd
        q = pd.read_csv(ref, usecols=["time", "Q"])
        return np.interp(times, q["time"].values, q["Q"].values)
    except Exception:
        return 178.46 * (1.0 + 0.20 * np.sin(2 * np.pi * times))


def load_default_initial():
    """Uygulamada baslangic dosyasi yuklenmezse repodaki digester_initial.csv."""
    import pandas as pd
    return pd.read_csv(os.path.join(HERE, "digester_initial.csv"))


def simulate_mixture(mix_dict, df_initial=None, sim_days=150.0, dt=1.0/24.0,
                     seasonal=True, dynamic=True):
    """
    Bir gubre karisimini (tekli veya coklu) uctan uca simule eder.
    Doner: (sonuc_DataFrame, besleme_listesi, karisim_adi)
    """
    if df_initial is None:
        df_initial = load_default_initial()

    feedstocks = build_feedstocks(mix_dict)

    n = int(round(sim_days / dt)) + 1
    times = np.round(np.arange(n) * dt, 6)
    temp = seasonal_temp_series(times) if seasonal else np.full(n, 35.0)
    flow = dynamic_flow_series(times) if dynamic else np.full(n, 178.46)

    results = run_codigestion(feedstocks, df_initial, sim_days=sim_days, dt=dt,
                              temp_series=temp, flow_series=flow)

    total = sum(mix_dict.values())
    if len(mix_dict) == 1:
        name = feedstocks[0]["name"]
    else:
        name = "Ko-digestion: " + ", ".join(
            f"{feedstock_library[k]['name']} %{int(v/total*100)}"
            for k, v in mix_dict.items())

    return results, feedstocks, name
