import streamlit as st

from manure_config import ADM1Simulator
from feedstock_library import feedstock_library

# =====================================================================
# ui_common.py -- Cok-sayfali uygulamada (app.py + pages/) ortak tema,
# sabitler ve girdi yardimcilari. Hem girdi hem sonuc sayfasi buradan
# apply_theme() cagirir; boylece glassmorphism tema tek yerde tutulur.
# =====================================================================

_THEME_CSS = """
<style>
    /* Arka Plan ve Temel Renkler */
    .stApp {
        background: #F2F2F7;
        background-image: radial-gradient(circle at 2% 2%, rgba(175, 82, 222, 0.05) 0%, transparent 40%),
                          radial-gradient(circle at 98% 98%, rgba(0, 122, 255, 0.05) 0%, transparent 40%);
        background-attachment: fixed;
        font-family: -apple-system, system-ui, sans-serif;
    }

    /* Header (Üst Başlık) - Sağa kaydırıldı ve Büyütüldü */
    .main-header {
        font-size: 80px !important;
        font-weight: 800 !important;
        color: #1C1C1E !important;
        letter-spacing: -2px !important;
        margin-bottom: 20px !important;
        margin-left: 40px !important;
    }

    /* 1. SADECE METİN İÇEREN LİKİT CAM KUTU */
    .glass-box {
        background: rgba(255, 255, 255, 0.45);
        backdrop-filter: blur(40px);
        -webkit-backdrop-filter: blur(40px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
        padding: 30px;
        margin-bottom: 25px;
        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease;
        transform-origin: center center;
    }

    /* 2. WIDGETLARI İÇİNE ALAN STREAMLIT KUTULARINI LİKİT CAM YAPMA (CSS Hack) */
    div[data-testid="stVerticalBlock"]:has(> div.element-container .glass-container-anchor) {
        background: rgba(255, 255, 255, 0.45);
        backdrop-filter: blur(40px);
        -webkit-backdrop-filter: blur(40px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
        padding: 30px;
        margin-bottom: 25px;
        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease;
        transform-origin: center center;
    }

    /* ANA KUTULAR İÇİN POP-UP ETKİSİ */
    .glass-box:hover, div[data-testid="stVerticalBlock"]:has(> div.element-container .glass-container-anchor):hover {
        transform: scale(1.015);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.08);
    }

    /* Çapayı gizle */
    .glass-container-anchor { display: none; }

    /* Kutu İçi Başlıklar */
    h3.box-title {
        margin-top: 0;
        font-size: 20px;
        color: #1C1C1E;
        font-weight: 700;
        margin-bottom: 20px;
    }

    /* Radyo Buton Kutusu (Simülasyon Modu) */
    div[role="radiogroup"] {
        background: rgba(255, 255, 255, 0.7);
        border-radius: 16px;
        padding: 10px 20px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        display: inline-flex;
    }

    /* Selectbox (Gübre Seçimi) Arka Planını Saf Beyaz Yapma */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
    }

    /* Girdi Kutucuklarında Sadece Gölge (İç elemanlarda pop-up iptal) */
    div[data-baseweb="select"], div[data-baseweb="input"], div[role="radiogroup"] {
        transition: box-shadow 0.3s ease !important;
    }
    div[data-baseweb="select"]:hover, div[data-baseweb="input"]:hover, div[role="radiogroup"]:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.06) !important;
    }

    /* Dosya Yükleme Alanları (Sadece gölge, pop-up yok) */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.85);
        border-radius: 16px;
        padding: 15px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        transition: box-shadow 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        box-shadow: 0 8px 25px rgba(0,0,0,0.06);
    }

    /* Streamlit Sağ Üst Menü Özelleştirmeleri */
    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Deploy Butonunu Kökten Yok Etme */
    [data-testid="stDeployButton"], [data-testid="stAppDeployButton"] {
        display: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* 3 Nokta Menü İkonu (Burada Pop-up KALDI) */
    [data-testid="stHeader"] button:last-child {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        border-radius: 50% !important;
        width: 44px !important;
        height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), background 0.4s ease !important;
        transform-origin: center center;
    }
    [data-testid="stHeader"] button:last-child:hover {
        transform: scale(1.15) !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }

    /* TÜM SAYFAYI BULANIKLAŞTIRAN SINIF (Grafik büyüdüğünde tetiklenecek) */
    .main-blur {
        filter: blur(15px);
        pointer-events: none; /* Blur varken ana sayfaya tıklanamasın */
        transition: filter 0.5s ease;
    }

    /* İNDİR BUTONU VE BAŞLAT BUTONU TASARIMI (EŞİTLENDİ) */
    div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(40px) !important;
        -webkit-backdrop-filter: blur(40px) !important;
        color: #1C1C1E !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 24px !important;
        padding: 15px 24px !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease !important;
        width: 100% !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05) !important;
        transform-origin: center center;
    }
    div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover {
        transform: scale(1.015) !important;
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.08) !important;
        background: rgba(255, 255, 255, 0.55) !important;
    }

    /* İndir butonu için Streamlit'in varsayılan alt çizgisini kaldır */
    div[data-testid="stDownloadButton"] a {
        text-decoration: none !important;
    }

    /* MODELLENİYOR DURUMUNDA (Disabled) BUTONUN GÖRÜNÜMÜ */
    div[data-testid="stButton"] > button:disabled {
        opacity: 0.9 !important;
        transform: none !important;
        cursor: wait !important;
        color: #AF52DE !important; /* Vurgulu mor yazı */
        border-color: rgba(175, 82, 222, 0.4) !important;
        background: rgba(255, 255, 255, 0.7) !important;
    }

    /* ========================================= */
    /* HAYALET KATMANLARI VE TOOLBARLARI GİZLEME */
    /* ========================================= */
    iframe {
        background: transparent !important;
        border: none !important;
    }
    [data-testid="stIFrame"] {
        background: transparent !important;
        border: none !important;
    }
    /* "st.iframe" yazan sinir bozucu araç çubuğunu yok eder */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* ===== ADIM 2: PRESET CHIP BUTONLARI (küçük, ikincil stil) ===== */
    div[data-testid="stButton"] > button[kind="secondary"] {
        font-size: 13px !important;
        padding: 8px 14px !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        background: rgba(255,255,255,0.7) !important;
    }

    /* ===== ADIM 2: FEEDSTOCK BİLGİ KARTLARI ===== */
    .fs-card {
        background: rgba(255,255,255,0.75);
        border: 1px solid rgba(255,255,255,0.8);
        border-radius: 18px;
        padding: 16px 18px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.04);
        margin-top: 10px;
        height: 100%;
    }
    .fs-name { font-size: 16px; font-weight: 700; color: #1C1C1E; margin-bottom: 8px; }
    .fs-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
    .fs-chip {
        font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px;
        background: rgba(0,0,0,0.05); color: #3A3A3C;
    }
    .fs-desc { font-size: 13px; line-height: 1.5; color: #6C6C70; }

    /* ===== ADIM 3.5: "st.iframe" ARAÇ ÇUBUĞUNU KESİN GİZLE ===== */
    [data-testid="stElementToolbar"],
    [data-testid="stElementToolbarButton"],
    [data-testid="stElementToolbarButtonContainer"] {
        display: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* ===== ADIM 3.5: TAM EKRAN SONUÇ GÖRÜNÜMÜ ===== */
    .results-bar {
        display: flex; align-items: center; justify-content: space-between;
        margin: 0 0 10px 40px;
    }
    .results-title { font-size: 30px; font-weight: 800; color: #1C1C1E; letter-spacing: -1px; }
    /* ===== ADIM 4: OTOMATIK SAYFA NAVIGASYONUNU GIZLE ===== */
    [data-testid="stSidebarNav"] { display: none !important; }
</style>
"""


def apply_theme():
    """Ortak glassmorphism temasini enjekte eder (her sayfa cagirmali)."""
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


INTRO_HTML = '''
<div class="glass-box">
    <h3 class="box-title">Dinamik Hibrit Biyogaz Simülatörü</h3>
    <p style="color: #3A3A3C; font-size: 15px; line-height: 1.6;">
        Bu platform, Anaerobic Digestion Model No. 1 (ADM1) tabanlı dinamik simülasyonlar gerçekleştirmenizi sağlar.
        Tek bir atık türünü simüle edebileceğiniz gibi, farklı atık türlerini belirlediğiniz oranlarda karıştırarak
        hibrit gübreleme senaryolarının biyogaz üretimine ve reaktör stabilitesine etkilerini analiz edebilirsiniz.
    </p>
    <p style="color: #3A3A3C; font-size: 15px; line-height: 1.6; margin-top:10px;">
        <strong>Nasıl Kullanılır?</strong><br>
        1. Influent ve Initial veri dosyalarınızı yükleyin.<br>
        2. Simülasyon ayarlarından atık türünü veya karışım oranlarını belirleyin.<br>
        3. Simülasyonu başlatın ve analiz sonuçlarını inceleyin.
    </p>
</div>
'''


sim_manager = ADM1Simulator()
gubre_tipleri = list(sim_manager.manure_data.keys())


def _buffer_info(s_ic_feed):
    """Feed alkalinitesine gore tampon seviyesi etiketi + renk."""
    if s_ic_feed >= 0.07:
        return "Yüksek tampon", "#34C759"
    if s_ic_feed >= 0.03:
        return "Orta tampon", "#FF9500"
    return "Düşük tampon (asitleşme riski)", "#FF3B30"


def render_feedstock_card(key):
    """Secilen gubre icin bilgi karti: COD, tampon seviyesi ve aciklama."""
    md = sim_manager.manure_data.get(key, {})
    fl = feedstock_library.get(key, {})
    cod = fl.get("total_cod")
    lvl, color = _buffer_info(fl.get("s_ic_feed", 0.03))
    cod_txt = f"COD {cod:.0f} gCOD/L" if cod is not None else "COD —"
    st.markdown(f'''
    <div class="fs-card">
        <div class="fs-name">{md.get("name", key)}</div>
        <div class="fs-chips">
            <span class="fs-chip">{cod_txt}</span>
            <span class="fs-chip" style="background:{color}22; color:{color};">{lvl}</span>
        </div>
        <div class="fs-desc">{md.get("desc", "")}</div>
    </div>
    ''', unsafe_allow_html=True)


# Hazir preset karisimlar (anahtarlar manure_config ile uyumlu)
PRESETS = {
    "Sığır %70 + Tavuk %30": {"sigir": 70, "tavuk": 30},
    "Sığır %60 + Mısır Silajı %40": {"sigir": 60, "misir_silaji": 40},
    "Arıtma Çamuru %50 + Peynir Altı Suyu %50": {"aritma_camuru": 50, "peynir_alti_suyu": 50},
}


def apply_preset(mix):
    """Preset'i Hibrit moda yazar; widget'lar rerun'da session_state'ten okur."""
    st.session_state["sim_type"] = "Hibrit Karışım"
    st.session_state["multi_sel"] = list(mix.keys())
    for k, v in mix.items():
        st.session_state[f"oran_{k}"] = v


def scenario_builder(prefix, baslik, accent):
    """Karsilastirma modunda tek senaryo (A/B) icin gubre + oran secici.
    Doner: {gubre: oran} karisim sozlugu."""
    st.markdown(f"<p style='font-size:16px; font-weight:700; color:{accent}; margin:14px 0 4px;'>{baslik}</p>", unsafe_allow_html=True)
    sel = st.multiselect("Gübreler", gubre_tipleri, key=f"{prefix}_sel",
                         label_visibility="collapsed",
                         placeholder="Bu senaryo için gübre(leri) seçin")
    mix = {}
    if sel:
        cols = st.columns(len(sel))
        for i, g in enumerate(sel):
            with cols[i]:
                okey = f"{prefix}_oran_{g}"
                kwargs = {} if okey in st.session_state else {"value": int(100 / len(sel))}
                oran = st.number_input(g.capitalize(), min_value=0, max_value=100,
                                       step=1, key=okey, **kwargs)
                if oran > 0:
                    mix[g] = oran
        tot = sum(mix.values())
        if tot != 100:
            st.warning(f"{baslik}: toplam %{tot} — bu orana göre normalize edilecek.")
    return mix
