# Hammadde fraksiyon kütüphanesi (t=0 anı influent dağılımları)

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
        # DÜZELTİLDİ: S_I 0.35 çok yüksekti; peynir altı suyu ~%85 biyobozunur (BMP geri-testi ile doğrulandı)
        "inf_comp": {"X_xc": 0.10, "X_ch": 0.55, "X_pr": 0.12, "X_li": 0.03, "X_I": 0.05, "S_I": 0.15}
    },
    "seker_pancari_posasi": {
        "name": "Şeker Pancarı Posası",
        "total_cod": 85.0,
        # DÜZELTİLDİ: X_I 0.18 -> 0.08 (f_xI_xc de 0.15->0.05, manure_config'te)
        "inf_comp": {"X_xc": 0.70, "X_ch": 0.15, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.08, "S_I": 0.04}
    },
    "zeytin_pirinasi": {
        "name": "Zeytin Karasuyu / Pirinası",
        "total_cod": 120.0,
        "inf_comp": {"X_xc": 0.50, "X_ch": 0.02, "X_pr": 0.01, "X_li": 0.05, "X_I": 0.40, "S_I": 0.02}
    },
    "mezbaha_atigi": {
        "name": "Mezbaha Atıkları",
        "total_cod": 110.0,
        # DÜZELTİLDİ: X_I 0.30 -> 0.10; kan/yağ/organ ~%85 biyobozunur (BMP geri-testi ile doğrulandı)
        "inf_comp": {"X_xc": 0.55, "X_ch": 0.02, "X_pr": 0.20, "X_li": 0.10, "X_I": 0.10, "S_I": 0.03}
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
