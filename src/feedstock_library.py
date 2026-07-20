# Hammadde (feedstock) kutuphanesi
# - inf_comp : influent kompozisyon FRAKSIYONLARI (toplami = 1.0). Toplam COD icindeki paylar.
#              X_xc kompozit baskindir; disintegrasyon sirasinda manure_config'teki
#              f_ch_xc/f_pr_xc/f_li_xc/f_xI_xc/f_sI_xc oranlarina gore protein/karb/yaga ayrilir.
# - total_cod: bu gubrenin tipik toplam COD konsantrasyonu [kgCOD/m3].
#              NOT: Bu degerler literatur "kaba tahmin" araligindadir; kendi verinle guncelle.

feedstock_library = {
    "sigir": {
        "name": "Sığır Gübresi",
        "total_cod": 55.0,
        "inf_comp": {"X_xc": 0.65, "X_ch": 0.03, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.25, "S_I": 0.04}
    },
    "tavuk": {
        "name": "Tavuk Gübresi",
        "total_cod": 90.0,
        "inf_comp": {"X_xc": 0.60, "X_ch": 0.02, "X_pr": 0.03, "X_li": 0.01, "X_I": 0.30, "S_I": 0.04}
    },
    "koyun_keci": {
        "name": "Küçükbaş (Koyun/Keçi) Gübresi",
        "total_cod": 65.0,
        "inf_comp": {"X_xc": 0.55, "X_ch": 0.02, "X_pr": 0.01, "X_li": 0.01, "X_I": 0.37, "S_I": 0.04}
    },
    "peynir_alti_suyu": {
        "name": "Peynir Altı Suyu",
        "total_cod": 50.0,
        "inf_comp": {"X_xc": 0.20, "X_ch": 0.25, "X_pr": 0.10, "X_li": 0.05, "X_I": 0.05, "S_I": 0.35}
    },
    "seker_pancari_posasi": {
        "name": "Şeker Pancarı Posası",
        "total_cod": 85.0,
        "inf_comp": {"X_xc": 0.70, "X_ch": 0.05, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.18, "S_I": 0.04}
    },
    "zeytin_pirinasi": {
        "name": "Zeytin Karasuyu / Pirinası",
        "total_cod": 120.0,
        "inf_comp": {"X_xc": 0.50, "X_ch": 0.02, "X_pr": 0.01, "X_li": 0.05, "X_I": 0.40, "S_I": 0.02}
    },
    "mezbaha_atigi": {
        "name": "Mezbaha Atıkları",
        "total_cod": 110.0,
        "inf_comp": {"X_xc": 0.50, "X_ch": 0.01, "X_pr": 0.10, "X_li": 0.05, "X_I": 0.30, "S_I": 0.04}
    },
    "misir_silaji": {
        "name": "Mısır Silajı",
        "total_cod": 130.0,
        "inf_comp": {"X_xc": 0.70, "X_ch": 0.05, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.18, "S_I": 0.04}
    },
    "aritma_camuru": {
        "name": "Belediye Arıtma Çamuru",
        "total_cod": 45.0,
        "inf_comp": {"X_xc": 0.60, "X_ch": 0.03, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.30, "S_I": 0.04}
    }
}


def create_hybrid_feedstock(mixture_dict):
    """Birden fazla gubreyi verilen agirlik oranlariyla harmanlayip hibrit
    kompozisyon + toplam COD dondurur. manure_config.create_hybrid_manure ile
    ayni oranlama mantigini kullanir (kutle/agirlik bazli).

    mixture_dict: ornek {"sigir": 70, "tavuk": 30}
    """
    total_weight = sum(mixture_dict.values())
    if total_weight == 0:
        raise ValueError("Toplam karisim orani 0 olamaz.")

    comp_keys = ["X_xc", "X_ch", "X_pr", "X_li", "X_I", "S_I"]
    hybrid_comp = {k: 0.0 for k in comp_keys}
    hybrid_cod = 0.0

    for key, weight in mixture_dict.items():
        if key not in feedstock_library:
            raise KeyError(f"'{key}' feedstock_library'de bulunamadi.")
        w = weight / total_weight
        data = feedstock_library[key]
        for k in comp_keys:
            hybrid_comp[k] += data["inf_comp"].get(k, 0.0) * w
        hybrid_cod += data["total_cod"] * w

    name = "Hibrit (" + ", ".join(
        f"{k}: %{int((v / total_weight) * 100)}" for k, v in mixture_dict.items()
    ) + ")"
    return {"name": name, "total_cod": hybrid_cod, "inf_comp": hybrid_comp}
