import streamlit as st
import streamlit.components.v1 as components

from ui_common import apply_theme

# =====================================================================
# pages/1_Sonuclar.py  --  SONUÇ SAYFASI
# Girdi sayfasında (app.py) hesaplanıp session_state'e yazılan panoyu
# tam ekran gösterir. Girdi formu bu sayfada hiç yoktur -> "sayfa
# içinde sayfa" yığılması olmaz.
# =====================================================================
st.set_page_config(
    page_title="Analiz Sonuçları · PyADM1",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

INPUT_PAGE = "app.py"

# Henüz bir simülasyon çalıştırılmadıysa kullanıcıyı girdi sayfasına yönlendir
if "results" not in st.session_state:
    st.markdown('<p class="main-header" style="font-size:48px !important;">Henüz sonuç yok</p>', unsafe_allow_html=True)
    st.info("Önce bir simülasyon çalıştırın.")
    if st.button("← Girdi ekranına dön", key="back_empty"):
        st.switch_page(INPUT_PAGE)
    st.stop()

res = st.session_state["results"]

# Üst bar: geri dön + başlık
bar = st.columns([1.3, 5])
with bar[0]:
    if st.button("← Yeni Simülasyon", key="back_btn"):
        st.switch_page(INPUT_PAGE)
with bar[1]:
    st.markdown('<div class="results-bar"><span class="results-title">Analiz Sonuçları</span></div>', unsafe_allow_html=True)

# Pano + CSV indirme
if res.get("mode") == "cmp":
    # scrolling=False + HTML icindeki autoFitFrame -> ic kaydirma cubugu yok,
    # pano ana sayfanin parcasi gibi akar. Yukseklik ilk yukleme icin baslangic;
    # icerik yuklenince JS gercek yukseklige cekiyor.
    components.html(res["html"], height=2050, scrolling=False)
    dcol_a, dcol_b = st.columns(2)
    with dcol_a:
        st.download_button("Senaryo A — CSV İndir", data=res["csv_a"],
                           file_name="karsilastirma_A.csv", mime="text/csv", key="dl_a")
    with dcol_b:
        st.download_button("Senaryo B — CSV İndir", data=res["csv_b"],
                           file_name="karsilastirma_B.csv", mime="text/csv", key="dl_b")
else:
    components.html(res["html"], height=1550, scrolling=False)
    st.download_button(
        label="Sonuçları CSV Olarak İndir",
        data=res["csv"],
        file_name="codigestion_out.csv",
        mime="text/csv",
        key="dl_btn",
    )
