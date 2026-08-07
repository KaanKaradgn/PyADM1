# Hammadde fraksiyon kütüphanesi (t=0 anı influent dağılımları)
# s_ic_feed / s_cat_feed: gübre-başına feed alkalinitesi (bikarbonat) ve katyonu.
#   Gübreler yüksek (gerçekte iyi tamponlu, kararlı); asidik besinler (peynir suyu,
#   melas, silaj, zeytin) düşük (gerçekte hızlı asitleşir). Motor bunları akış-payı
#   ağırlıklı olarak influent tamponuna çevirir.

feedstock_library = {
    "sigir": {
        "name": "Sığır Gübresi",
        "total_cod": 55.0,
        "s_ic_feed": 0.10, "s_cat_feed": 0.05,
        "inf_comp": {"X_xc": 0.65, "X_ch": 0.03, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.25, "S_I": 0.04}
    },
    "tavuk": {
        "name": "Tavuk Gübresi",
        "total_cod": 90.0,
        "s_ic_feed": 0.08, "s_cat_feed": 0.05,
        # İNERT AYARI: fr-ultimate çapaya (0.525) getirildi; X_I 0.30->0.24.
        "inf_comp": {"X_xc": 0.66, "X_ch": 0.02, "X_pr": 0.03, "X_li": 0.01, "X_I": 0.24, "S_I": 0.04}
    },
    "koyun_keci": {
        "name": "Küçükbaş (Koyun/Keçi) Gübresi",
        "total_cod": 65.0,
        "s_ic_feed": 0.08, "s_cat_feed": 0.04,
        # İNERT AYARI: fr-ultimate çapaya (0.40) getirildi; X_I 0.37->0.27.
        "inf_comp": {"X_xc": 0.65, "X_ch": 0.02, "X_pr": 0.01, "X_li": 0.01, "X_I": 0.27, "S_I": 0.04}
    },
    "peynir_alti_suyu": {
        "name": "Peynir Altı Suyu",
        "total_cod": 50.0,
        "s_ic_feed": 0.005, "s_cat_feed": 0.005,   # asidik, düşük alkalinite -> aşırı yükte çöker
        # ~%85 biyobozunur. İNERT AYARI: S_I 0.15->0.09 (fr-ultimate=çapa 0.85).
        "inf_comp": {"X_xc": 0.11, "X_ch": 0.59, "X_pr": 0.13, "X_li": 0.03, "X_I": 0.05, "S_I": 0.09}
    },
    "seker_pancari_posasi": {
        "name": "Şeker Pancarı Posası",
        "total_cod": 85.0,
        "s_ic_feed": 0.01, "s_cat_feed": 0.01,     # düşük tampon
        # DBFZ press-cake 0.218 Nm3CH4/kgVS (~%52 biyobozunur).
        "inf_comp": {"X_xc": 0.60, "X_ch": 0.09, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.24, "S_I": 0.04}
    },
    "zeytin_pirinasi": {
        "name": "Zeytin Karasuyu / Pirinası",
        "total_cod": 120.0,
        "s_ic_feed": 0.005, "s_cat_feed": 0.005,   # asidik + fenolik
        "inf_comp": {"X_xc": 0.50, "X_ch": 0.02, "X_pr": 0.01, "X_li": 0.05, "X_I": 0.40, "S_I": 0.02}
    },
    "mezbaha_atigi": {
        "name": "Mezbaha Atıkları",
        "total_cod": 110.0,
        "s_ic_feed": 0.05, "s_cat_feed": 0.03,     # protein -> orta tampon
        # X_I 0.30->0.10; kan/yağ/organ ~%85 biyobozunur.
        "inf_comp": {"X_xc": 0.55, "X_ch": 0.02, "X_pr": 0.20, "X_li": 0.10, "X_I": 0.10, "S_I": 0.03}
    },
    "misir_silaji": {
        "name": "Mısır Silajı",
        "total_cod": 130.0,
        "s_ic_feed": 0.005, "s_cat_feed": 0.01,    # silaj asidik, düşük tampon
        # İNERT AYARI: fr-ultimate çapaya (0.75); X_I 0.18->0.05, serbest X_xc'ye.
        "inf_comp": {"X_xc": 0.82, "X_ch": 0.06, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.05, "S_I": 0.04}
    },
    "aritma_camuru": {
        "name": "Belediye Arıtma Çamuru",
        "total_cod": 45.0,
        "s_ic_feed": 0.07, "s_cat_feed": 0.04,     # orta-iyi tampon
        "inf_comp": {"X_xc": 0.60, "X_ch": 0.03, "X_pr": 0.02, "X_li": 0.01, "X_I": 0.30, "S_I": 0.04}
    }
}
