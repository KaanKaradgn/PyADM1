import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# from PyADM1_2 import run_simulation 
from plot_results import get_dashboard_html
from manure_config import ADM1Simulator

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="PyADM1 Analitik Paneli",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ÖZEL CSS STİLİ (Likit Cam / iOS Tarzı ve Dengeli Animasyonlar) ---
st.markdown("""
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
</style>
""", unsafe_allow_html=True)


# --- BİLGİLENDİRME BÖLÜMÜ ---
st.markdown('<p class="main-header">PyADM1 Analitik Paneli</p>', unsafe_allow_html=True)

st.markdown('''
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
''', unsafe_allow_html=True)


# --- KONTROL PANELİ ---
sim_manager = ADM1Simulator()
gubre_tipleri = list(sim_manager.manure_data.keys())

# 1. Kutu: Veri Dosyaları
with st.container():
    st.markdown('<div class="glass-container-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<h3 class="box-title">Veri Dosyaları</h3>', unsafe_allow_html=True)
    
    col_file1, col_file2 = st.columns(2)
    with col_file1:
        influent_file = st.file_uploader("Influent (Giriş) Verisi", type=["csv"])
    with col_file2:
        initial_file = st.file_uploader("Initial (Başlangıç) Verisi", type=["csv"])

# 2. Kutu: Simülasyon Ayarları
with st.container():
    st.markdown('<div class="glass-container-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<h3 class="box-title">Simülasyon Ayarları</h3>', unsafe_allow_html=True)
    
    sim_type = st.radio("Simülasyon Modu:", ["Tek Tip", "Hibrit Karışım"], horizontal=True)

    if sim_type == "Tek Tip":
        secilen_gubre = st.selectbox("Gübre Türü Seçin:", gubre_tipleri)
        karisim_oranlari = None 
    else:
        secilenler = st.multiselect("Karışıma dahil edilecek gübreleri seçin:", gubre_tipleri)
        karisim_oranlari = {}
        
        if secilenler:
            st.markdown("<p style='font-size:14px; color:#8E8E93; margin-top:10px;'>Karışım Yüzdelerini Belirleyin (%)</p>", unsafe_allow_html=True)
            cols = st.columns(len(secilenler))
            for i, gubre in enumerate(secilenler):
                with cols[i]:
                    oran = st.number_input(f"{gubre.capitalize()}", min_value=0, max_value=100, value=int(100/len(secilenler)), step=1)
                    if oran > 0:
                        karisim_oranlari[gubre] = oran
            
            toplam_oran = sum(karisim_oranlari.values())
            if toplam_oran != 100:
                st.warning(f"Toplam oran %{toplam_oran}. Hesaplamalar bu orana göre normalize edilecektir.")

# --- ÇALIŞTIRMA BUTONU VE MANTIK ---
btn_placeholder = st.empty()
baslat_butonu = btn_placeholder.button("Simülasyonu Başlat", key="btn_start")

if baslat_butonu:
    if influent_file is None or initial_file is None:
        st.error("Lütfen influent ve initial CSV dosyalarını yükleyin.")
    elif sim_type == "Hibrit Karışım" and (not karisim_oranlari or sum(karisim_oranlari.values()) == 0):
        st.error("Hibrit simülasyon için oranlar toplamı 0 olamaz.")
    else:
        # 1. AŞAMA: Tıklanınca Modelleniyor yazıp kilitlenir
        btn_placeholder.button("Modelleniyor... Lütfen bekleyin.", disabled=True, key="btn_loading")
        
        try:
            df_influent = pd.read_csv(influent_file)
            df_initial = pd.read_csv(initial_file)
            
            if sim_type == "Tek Tip":
                params = sim_manager.manure_data[secilen_gubre]
            else:
                params = sim_manager.create_hybrid_manure(karisim_oranlari)
            
            from PyADM1_2 import run_simulation
            dynamic_out_df = run_simulation(df_influent, df_initial, params)
            
            html_kodu = get_dashboard_html(dynamic_out_df, params['name'])
            components.html(html_kodu, height=1050, scrolling=True)
            
            csv_cikti = dynamic_out_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Sonuçları CSV Olarak İndir",
                data=csv_cikti,
                file_name='dynamic_out.csv',
                mime='text/csv'
            )
            
            # 2. AŞAMA: İşlem bitince Tamamlandı yazısına dönüşür
            btn_placeholder.button("Modelleme Tamamlandı ✓", disabled=True, key="btn_done")
            
        except Exception as e:
            st.error(f"Simülasyon sırasında hata oluştu: {e}")
            btn_placeholder.button("Hata Oluştu", disabled=True, key="btn_error")