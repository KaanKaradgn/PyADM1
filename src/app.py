"""
PyADM1 Analitik Paneli — Flask sürümü.

Streamlit'in iframe kabuğu yerine, elle yazdığımız HTML/CSS/Chart.js panosunu
DOĞRUDAN tam sayfa olarak sunar. Böylece iframe kaynaklı boyutlandırma/çakışma
hataları (alttaki 'st.iframe' etiketi, CSV butonu ile grafik çakışması vb.)
tamamen ortadan kalkar. Simülasyon motoru (ADM1) Python'da aynen korunur.

Çalıştırma:
    pip install flask
    python app.py
    -> tarayıcıda http://127.0.0.1:8501 açılır.
"""
import base64
import io
import json
import os
import threading
import webbrowser

import pandas as pd
from flask import Flask, request, Response

from plot_results import get_dashboard_html, get_comparison_html
from codigest_runner import simulate_mixture
from manure_config import ADM1Simulator
from feedstock_library import feedstock_library

app = Flask(__name__)

# --- Gübre meta verisi (form + bilgi kartları için) -------------------------
_sim = ADM1Simulator()
FEEDSTOCKS = []
for _k in _sim.manure_data:
    _md = _sim.manure_data[_k]
    _fl = feedstock_library.get(_k, {})
    FEEDSTOCKS.append({
        "key": _k,
        "name": _md.get("name", _k),
        "desc": _md.get("desc", ""),
        "cod": _fl.get("total_cod"),
        "s_ic": _fl.get("s_ic_feed", 0.03),
    })
FEEDSTOCKS_JSON = json.dumps(FEEDSTOCKS, ensure_ascii=False)

PRESETS = {
    "Sığır %70 + Tavuk %30": {"sigir": 70, "tavuk": 30},
    "Sığır %60 + Mısır Silajı %40": {"sigir": 60, "misir_silaji": 40},
    "Arıtma Çamuru %50 + Peynir Altı Suyu %50": {"aritma_camuru": 50, "peynir_alti_suyu": 50},
}
PRESETS_JSON = json.dumps(PRESETS, ensure_ascii=False)


# =====================================================================
#  ORTAK TEMA (cam efekti) + GİRİŞ SAYFASI
# =====================================================================
THEME_CSS = """
    * { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system, system-ui, sans-serif; }
    html, body {
        background:#F2F2F7;
        background-image: radial-gradient(circle at 2% 2%, rgba(175,82,222,0.05) 0%, transparent 40%),
                         radial-gradient(circle at 98% 98%, rgba(0,122,255,0.05) 0%, transparent 40%);
        background-attachment:fixed; min-height:100%; color:#1C1C1E;
    }
    body { padding:36px 24px 80px; }
    .wrap { max-width:1040px; margin:0 auto; }
    .main-header { font-size:56px; font-weight:800; letter-spacing:-1.5px; margin:4px 0 22px 6px; }

    .glass {
        background:rgba(255,255,255,0.45); backdrop-filter:blur(40px); -webkit-backdrop-filter:blur(40px);
        border-radius:24px; border:1px solid rgba(255,255,255,0.6);
        box-shadow:0 8px 32px rgba(0,0,0,0.05); padding:28px 30px; margin-bottom:24px;
        transition:transform .4s cubic-bezier(0.16,1,0.3,1), box-shadow .4s ease;
    }
    .glass:hover { transform:scale(1.008); box-shadow:0 15px 40px rgba(0,0,0,0.08); }
    .box-title { font-size:22px; font-weight:800; margin-bottom:6px; }
    .box-sub { font-size:14px; color:#8E8E93; line-height:1.55; margin-bottom:18px; }
    .box-sub b { color:#3A3A3C; }

    label.fld { display:block; font-size:13px; font-weight:700; color:#6C6C70; margin:14px 0 7px; }
    input[type=file] { font-size:13px; color:#3A3A3C; }
    input[type=file]::file-selector-button {
        font-weight:700; font-size:13px; padding:8px 14px; margin-right:12px; cursor:pointer;
        border:none; border-radius:12px; background:rgba(0,122,255,0.10); color:#007AFF;
        transition:background .2s ease;
    }
    input[type=file]::file-selector-button:hover { background:rgba(0,122,255,0.18); }

    select, input[type=number] {
        width:100%; font-size:15px; font-weight:600; color:#1C1C1E; padding:11px 14px;
        border:1px solid rgba(0,0,0,0.08); border-radius:14px; background:rgba(255,255,255,0.7);
        outline:none; transition:border .2s ease, box-shadow .2s ease;
    }
    select:focus, input[type=number]:focus { border-color:#007AFF; box-shadow:0 0 0 3px rgba(0,122,255,0.12); }

    /* Segment (mod seçici) */
    .seg { display:flex; gap:8px; background:rgba(118,118,128,0.10); padding:5px; border-radius:16px; margin:4px 0 6px; }
    .seg label { flex:1; text-align:center; font-size:14px; font-weight:700; color:#3A3A3C;
        padding:10px 8px; border-radius:12px; cursor:pointer; transition:all .25s ease; }
    .seg input { display:none; }
    .seg label.on { background:#fff; color:#007AFF; box-shadow:0 2px 8px rgba(0,0,0,0.08); }

    /* Slider */
    .rangewrap { display:flex; align-items:center; gap:16px; }
    input[type=range] { -webkit-appearance:none; flex:1; height:6px; border-radius:3px;
        background:linear-gradient(90deg,#007AFF,#AF52DE); outline:none; }
    input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:22px; height:22px; border-radius:50%;
        background:#fff; box-shadow:0 2px 8px rgba(0,0,0,0.25); cursor:pointer; border:1px solid rgba(0,0,0,0.05); }
    .rangeval { font-size:16px; font-weight:800; color:#007AFF; min-width:96px; text-align:right; }

    /* Preset butonları */
    .presets { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:6px; }
    .preset-btn { font-size:13px; font-weight:700; padding:9px 15px; border-radius:14px; cursor:pointer;
        border:1px solid rgba(0,0,0,0.06); background:rgba(255,255,255,0.7); color:#3A3A3C; transition:all .2s ease; }
    .preset-btn:hover { background:#fff; color:#007AFF; box-shadow:0 4px 12px rgba(0,0,0,0.06); transform:translateY(-1px); }

    /* Gübre oran ızgarası */
    .fs-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:6px; }
    @media (max-width:820px){ .fs-grid { grid-template-columns:1fr 1fr; } }
    .fs-item { background:rgba(255,255,255,0.55); border:1px solid rgba(255,255,255,0.7);
        border-radius:18px; padding:14px 15px; }
    .fs-name { font-size:14px; font-weight:700; margin-bottom:4px; }
    .fs-chips { display:flex; flex-wrap:wrap; gap:5px; margin:6px 0 9px; }
    .fs-chip { font-size:11px; font-weight:700; padding:3px 9px; border-radius:20px; background:rgba(0,0,0,0.05); color:#3A3A3C; }
    .fs-item input[type=number] { padding:8px 10px; font-size:14px; }
    .fs-desc { font-size:12px; line-height:1.5; color:#8E8E93; margin-top:8px; }

    .totalline { font-size:13px; font-weight:700; margin-top:12px; }
    .totalline.warn { color:#B25000; }
    .totalline.ok { color:#1B7A32; }

    .cmp-cols { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
    @media (max-width:820px){ .cmp-cols { grid-template-columns:1fr; } }
    .cmp-cols h4 { font-size:16px; font-weight:800; margin:2px 0 10px; }
    .cmp-cols .a { color:#007AFF; } .cmp-cols .b { color:#AF52DE; }

    .startbtn { width:100%; font-size:17px; font-weight:800; color:#fff; padding:16px; border:none; cursor:pointer;
        border-radius:18px; background:linear-gradient(90deg,#007AFF,#AF52DE); box-shadow:0 10px 26px rgba(0,122,255,0.28);
        transition:transform .2s ease, box-shadow .2s ease; }
    .startbtn:hover { transform:translateY(-2px); box-shadow:0 16px 34px rgba(0,122,255,0.34); }
    .startbtn:active { transform:translateY(0); }
    .err { background:rgba(255,59,48,0.10); color:#C0392B; border:1px solid rgba(255,59,48,0.2);
        padding:12px 16px; border-radius:14px; font-weight:700; font-size:14px; margin-bottom:18px; }
    .hidden { display:none !important; }

    /* Yükleniyor bindirmesi */
    #loading { position:fixed; inset:0; background:rgba(242,242,247,0.72); backdrop-filter:blur(8px);
        -webkit-backdrop-filter:blur(8px); display:none; align-items:center; justify-content:center; flex-direction:column;
        z-index:9999; gap:22px; }
    #loading.on { display:flex; }
    .spinner { width:54px; height:54px; border-radius:50%; border:5px solid rgba(0,122,255,0.15);
        border-top-color:#007AFF; animation:spin 0.9s linear infinite; }
    @keyframes spin { to { transform:rotate(360deg); } }
    #loading p { font-size:16px; font-weight:700; color:#3A3A3C; }
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PyADM1 Analitik Paneli</title>
<style>__CSS__</style></head>
<body>
<div id="loading"><div class="spinner"></div><p>Modelleniyor… büyük simülasyonlar birkaç dakika sürebilir.</p></div>
<div class="wrap">
  <div class="main-header">PyADM1 Analitik Paneli</div>

  <div class="glass">
    <div class="box-title">Dinamik Hibrit Biyogaz Simülatörü</div>
    <div class="box-sub">
      ADM1 tabanlı dinamik simülasyon. Tek bir atığı çalıştırabilir ya da farklı atıkları belirlediğin
      oranlarda karıştırarak hibrit senaryoların biyogaz üretimine ve reaktör stabilitesine etkisini analiz edebilirsin.
    </div>
  </div>

  <form id="simform" method="POST" action="/simulate" enctype="multipart/form-data">
    __ERR__

    <!-- 1) Veri dosyaları -->
    <div class="glass">
      <div class="box-title">Veri Dosyaları</div>
      <div class="box-sub">Influent kompozisyonu seçilen gübrelerden otomatik oluşur — ayrı influent dosyası gerekmez.
        İstersen reaktör başlangıç durumunu (initial) ve bir sıcaklık/debi profilini yükleyebilirsin; boş bırakırsan güvenli varsayılanlar kullanılır.</div>
      <label class="fld">Reaktör Başlangıç Durumu (Initial) — opsiyonel, .csv</label>
      <input type="file" name="initial" accept=".csv">
      <label class="fld">Sıcaklık &amp; Debi Profili (sütunlar: <b>time</b>, <b>T (C)</b>/<b>temp</b>, <b>Q</b>/<b>q_ad</b>) — opsiyonel, .csv</label>
      <input type="file" name="profile" accept=".csv">
    </div>

    <!-- 2) Simülasyon ayarları -->
    <div class="glass">
      <div class="box-title">Simülasyon Ayarları</div>

      <label class="fld">Hazır Karışımlar</label>
      <div class="presets" id="presets"></div>

      <label class="fld">Simülasyon Modu</label>
      <div class="seg" id="modeseg">
        <label data-mode="tek"><input type="radio" name="mode" value="tek" checked>Tek Tip</label>
        <label data-mode="hibrit"><input type="radio" name="mode" value="hibrit">Hibrit Karışım</label>
        <label data-mode="karsilastirma"><input type="radio" name="mode" value="karsilastirma">Karşılaştırma</label>
      </div>

      <label class="fld">Simülasyon Süresi (gün)</label>
      <div class="rangewrap">
        <input type="range" name="sim_days" id="simdays" min="30" max="280" step="10" value="150">
        <div class="rangeval"><span id="simdaysval">150</span> gün</div>
      </div>

      <!-- Tek Tip -->
      <div id="panel-tek" class="panel">
        <label class="fld">Gübre Türü</label>
        <select name="single" id="single"></select>
        <div id="single-info" style="margin-top:14px;"></div>
      </div>

      <!-- Hibrit -->
      <div id="panel-hibrit" class="panel hidden">
        <label class="fld">Karışım Yüzdeleri (%) — dahil etmek istemediğin gübreyi 0 bırak</label>
        <div class="fs-grid" id="hibrit-grid"></div>
        <div class="totalline" id="hibrit-total"></div>
      </div>

      <!-- Karşılaştırma -->
      <div id="panel-karsilastirma" class="panel hidden">
        <div class="box-sub" style="margin-top:8px;">İki senaryoyu aynı süre/koşulda çalıştırıp yan yana kıyaslar. Her senaryo için oranları gir.</div>
        <div class="cmp-cols">
          <div>
            <h4 class="a">Senaryo A</h4>
            <div class="fs-grid" id="a-grid" style="grid-template-columns:1fr;"></div>
            <div class="totalline" id="a-total"></div>
          </div>
          <div>
            <h4 class="b">Senaryo B</h4>
            <div class="fs-grid" id="b-grid" style="grid-template-columns:1fr;"></div>
            <div class="totalline" id="b-total"></div>
          </div>
        </div>
      </div>
    </div>

    <button type="submit" class="startbtn">Simülasyonu Başlat</button>
  </form>
</div>

<script>
  const FS = __FEEDSTOCKS__;
  const PRESETS = __PRESETS__;

  function bufInfo(s){ if(s>=0.07) return ["Yüksek tampon","#34C759"]; if(s>=0.03) return ["Orta tampon","#FF9500"]; return ["Düşük tampon (asitleşme riski)","#FF3B30"]; }
  function chips(f){ const cod = f.cod!=null ? ("COD "+f.cod.toFixed(0)+" gCOD/L") : "COD —"; const bi=bufInfo(f.s_ic); const lvl=bi[0], c=bi[1];
    return '<div class="fs-chips"><span class="fs-chip">'+cod+'</span><span class="fs-chip" style="background:'+c+'22;color:'+c+';">'+lvl+'</span></div>'; }

  // Tek Tip select
  const sel = document.getElementById('single');
  FS.forEach(function(f){ const o=document.createElement('option'); o.value=f.key; o.textContent=f.name; sel.appendChild(o); });
  function renderSingleInfo(){ const f=FS.find(function(x){return x.key===sel.value;}); if(!f)return;
    document.getElementById('single-info').innerHTML =
      '<div class="fs-item"><div class="fs-name">'+f.name+'</div>'+chips(f)+'<div class="fs-desc">'+f.desc+'</div></div>'; }
  sel.addEventListener('change', renderSingleInfo); renderSingleInfo();

  // Hibrit ızgarası
  const hg=document.getElementById('hibrit-grid');
  FS.forEach(function(f){ const d=document.createElement('div'); d.className='fs-item';
    d.innerHTML='<div class="fs-name">'+f.name+'</div>'+chips(f)+
      '<input type="number" name="pct_'+f.key+'" min="0" max="100" step="1" value="0" data-grp="hibrit">'+
      '<div class="fs-desc">'+f.desc+'</div>'; hg.appendChild(d); });

  // Karşılaştırma A/B ızgaraları (kompakt: isim + oran)
  ['a','b'].forEach(function(side){ const g=document.getElementById(side+'-grid');
    FS.forEach(function(f){ const row=document.createElement('div'); row.className='fs-item';
      row.style.display='flex'; row.style.alignItems='center'; row.style.justifyContent='space-between'; row.style.gap='10px'; row.style.padding='10px 13px';
      row.innerHTML='<span style="font-size:13px;font-weight:600;">'+f.name+'</span>'+
        '<input style="max-width:92px;" type="number" name="pct_'+side+'_'+f.key+'" min="0" max="100" step="1" value="0" data-grp="'+side+'">';
      g.appendChild(row); }); });

  // Toplam göstergeleri
  function sumGrp(grp){ let t=0; document.querySelectorAll('input[data-grp="'+grp+'"]').forEach(function(i){ t+=parseInt(i.value||0,10); }); return t; }
  function updTotals(){
    const h=sumGrp('hibrit'); const he=document.getElementById('hibrit-total');
    he.textContent = h===0 ? 'Toplam %0 — en az bir gübreye oran gir.' : (h===100 ? 'Toplam %100 ✓' : 'Toplam %'+h+' — bu orana göre normalize edilir.');
    he.className='totalline '+(h===100?'ok':'warn');
    ['a','b'].forEach(function(s){ const v=sumGrp(s); const e=document.getElementById(s+'-total');
      e.textContent = v===0 ? 'Toplam %0' : (v===100?'Toplam %100 ✓':'Toplam %'+v+' (normalize)');
      e.className='totalline '+(v===100?'ok':(v===0?'':'warn')); });
  }
  document.addEventListener('input', function(e){ if(e.target.dataset && e.target.dataset.grp) updTotals(); });
  updTotals();

  // Süre etiketi
  const sd=document.getElementById('simdays'); sd.addEventListener('input',function(){ document.getElementById('simdaysval').textContent=sd.value; });

  // Mod değişimi
  function showMode(m){ ['tek','hibrit','karsilastirma'].forEach(function(x){
      document.getElementById('panel-'+x).classList.toggle('hidden', x!==m);
      document.querySelector('.seg label[data-mode="'+x+'"]').classList.toggle('on', x===m); }); }
  document.querySelectorAll('input[name=mode]').forEach(function(r){ r.addEventListener('change',function(){showMode(r.value);}); });
  showMode('tek');

  // Presetler
  const pc=document.getElementById('presets');
  Object.keys(PRESETS).forEach(function(label){ const b=document.createElement('button'); b.type='button'; b.className='preset-btn'; b.textContent=label;
    b.addEventListener('click',function(){ const mix=PRESETS[label];
      document.querySelector('input[name=mode][value=hibrit]').checked=true; showMode('hibrit');
      FS.forEach(function(f){ const inp=document.querySelector('input[name=pct_'+f.key+']'); if(inp) inp.value = mix[f.key]||0; });
      updTotals(); window.scrollTo({top:document.getElementById('hibrit-grid').offsetTop-120, behavior:'smooth'}); });
    pc.appendChild(b); });

  // Gönderimde yükleniyor bindirmesi
  document.getElementById('simform').addEventListener('submit', function(){ document.getElementById('loading').classList.add('on'); });
</script>
</body></html>
"""


def _render_index(error=None):
    err_html = f'<div class="err">{error}</div>' if error else ""
    return (INDEX_HTML
            .replace("__CSS__", THEME_CSS)
            .replace("__FEEDSTOCKS__", FEEDSTOCKS_JSON)
            .replace("__PRESETS__", PRESETS_JSON)
            .replace("__ERR__", err_html))


def _error_page(msg):
    return Response(_render_index(error=msg), mimetype="text/html")


def _read_csv(file_storage):
    """Yüklenen dosyayı (varsa) DataFrame'e çevirir; boşsa None."""
    if file_storage is None or not file_storage.filename:
        return None
    return pd.read_csv(io.BytesIO(file_storage.read()))


def _b64_csv(df):
    return base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("ascii")


def _collect_mix(prefix):
    """Formdan pct_<prefix><key> alanlarını toplayıp {key: oran} sözlüğü üretir."""
    mix = {}
    for f in FEEDSTOCKS:
        raw = request.form.get(f"pct_{prefix}{f['key']}", "0")
        try:
            v = int(float(raw))
        except (TypeError, ValueError):
            v = 0
        if v > 0:
            mix[f["key"]] = v
    return mix


@app.route("/")
def index():
    return Response(_render_index(), mimetype="text/html")


@app.route("/simulate", methods=["POST"])
def simulate():
    mode = request.form.get("mode", "tek")
    try:
        sim_days = int(float(request.form.get("sim_days", 150)))
    except (TypeError, ValueError):
        sim_days = 150

    try:
        df_initial = _read_csv(request.files.get("initial"))
        df_profile = _read_csv(request.files.get("profile"))
    except Exception as e:
        return _error_page(f"Yüklenen CSV okunamadı: {e}")

    try:
        if mode == "karsilastirma":
            mix_a = _collect_mix("a_")
            mix_b = _collect_mix("b_")
            if not mix_a or not mix_b:
                return _error_page("Karşılaştırma için A ve B senaryolarının ikisinde de en az bir gübreye oran girilmelidir.")
            df_a, _, name_a = simulate_mixture(mix_a, df_initial=df_initial, sim_days=sim_days, df_profile=df_profile)
            df_b, _, name_b = simulate_mixture(mix_b, df_initial=df_initial, sim_days=sim_days, df_profile=df_profile)
            html = get_comparison_html(df_a, name_a, df_b, name_b, sim_days=sim_days,
                                       back_url="/", csv_a_b64=_b64_csv(df_a), csv_b_b64=_b64_csv(df_b))
            return Response(html, mimetype="text/html")

        if mode == "hibrit":
            mix = _collect_mix("")
            if not mix:
                return _error_page("Hibrit simülasyon için en az bir gübreye oran girmelisin.")
        else:  # tek
            single = request.form.get("single")
            if not single:
                return _error_page("Lütfen bir gübre türü seç.")
            mix = {single: 100}

        df_out, _, mix_name = simulate_mixture(mix, df_initial=df_initial, sim_days=sim_days, df_profile=df_profile)
        html = get_dashboard_html(df_out, mix_name, sim_days=sim_days, back_url="/", csv_b64=_b64_csv(df_out))
        return Response(html, mimetype="text/html")

    except Exception as e:
        return _error_page(f"Simülasyon sırasında hata oluştu: {e}")


def _open_browser():
    webbrowser.open("http://127.0.0.1:8501")


if __name__ == "__main__":
    # Reloader ikinci süreç açtığında tarayıcıyı iki kez açmayı önle
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.2, _open_browser).start()
    app.run(host="127.0.0.1", port=8501, debug=False)
