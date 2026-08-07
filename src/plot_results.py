import pandas as pd
import numpy as np
import json

# numpy 2.x'te np.trapz -> np.trapezoid olarak yeniden adlandirildi; ikisini de destekle
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))


def _compute_metrics(df, sim_days):
    """Ham simulasyon cikitisindan ozet KPI'lari ve stabilite verdisini uretir.
    Motorun urettigi q_gas / q_ch4 / ch4_pct / pH sutunlarini kullanir; eksik
    olursa guvenli sekilde None doner (UI o karti gizler)."""
    t = df["time"].values if "time" in df.columns else np.arange(len(df))
    span = float(t[-1] - t[0]) if len(t) > 1 else float(sim_days)
    if span <= 0:
        span = float(sim_days)

    def _has(col):
        return col in df.columns

    # --- Uretim metrikleri (zaman uzerinden integral -> toplam hacim) ---
    toplam_ch4 = toplam_gas = gunluk_ch4 = tepe_gas = ort_ch4_pct = None
    if _has("q_ch4"):
        toplam_ch4 = float(_trapz(df["q_ch4"].values, t))   # m3 (tum periyot)
        gunluk_ch4 = toplam_ch4 / span                         # m3/gun ortalama
    if _has("q_gas"):
        toplam_gas = float(_trapz(df["q_gas"].values, t))
        tepe_gas = float(np.nanmax(df["q_gas"].values))
    if _has("ch4_pct"):
        # kararli hal: son %30'un ortalamasi (baslangic gecici rejimini disla)
        tail = df["ch4_pct"].values[int(len(df) * 0.7):]
        ort_ch4_pct = float(np.nanmean(tail)) if len(tail) else float(np.nanmean(df["ch4_pct"].values))

    # --- Stabilite (pH tabanli) ---
    min_ph = son_ph = None
    durum = "bilinmiyor"
    if _has("pH"):
        ph = df["pH"].values
        # ilk 15 gunu (devreye alma / gecici asitlenme) verdikten sonraki minimum
        mask = t >= min(15.0, span * 0.1)
        ph_after = ph[mask] if mask.any() else ph
        min_ph = float(np.nanmin(ph_after))
        son_ph = float(ph[-1])
        if min_ph < 6.5:
            durum = "kritik"     # asitlesme / pH cokusu
        elif min_ph < 6.8:
            durum = "sinirda"
        else:
            durum = "stabil"

    # --- VFA birikim trendi (asetat sonu vs ortasi) ---
    vfa_uyari = False
    if _has("S_ac"):
        ac = df["S_ac"].values
        orta = np.nanmean(ac[int(len(ac) * 0.4):int(len(ac) * 0.6)])
        son = np.nanmean(ac[int(len(ac) * 0.9):])
        if orta > 0 and son > orta * 1.5 and son > 1.0:
            vfa_uyari = True

    return {
        "toplam_ch4": toplam_ch4,
        "toplam_gas": toplam_gas,
        "gunluk_ch4": gunluk_ch4,
        "tepe_gas": tepe_gas,
        "ort_ch4_pct": ort_ch4_pct,
        "min_ph": min_ph,
        "son_ph": son_ph,
        "durum": durum,
        "vfa_uyari": vfa_uyari,
        "sim_days": span,
    }


def _fmt(v, digits=0, suffix=""):
    if v is None or (isinstance(v, float) and (np.isnan(v))):
        return "—"
    if digits == 0:
        return f"{v:,.0f}{suffix}"
    return f"{v:,.{digits}f}{suffix}"


def _build_kpi_html(m):
    """KPI serit + stabilite rozeti HTML'ini uretir."""
    durum_map = {
        "stabil":   ("Stabil",   "#34C759", "rgba(52,199,89,0.12)",  "Reaktor saglikli calisiyor"),
        "sinirda":  ("Sinirda",  "#FF9500", "rgba(255,149,0,0.12)",  "pH dusuk — yuku azaltmayi degerlendirin"),
        "kritik":   ("Kritik",   "#FF3B30", "rgba(255,59,48,0.12)",  "Asitlesme / pH cokusu — reaktor riskli"),
        "bilinmiyor": ("Belirsiz", "#8E8E93", "rgba(142,142,147,0.12)", "Yeterli veri yok"),
    }
    d_label, d_color, d_bg, d_desc = durum_map.get(m["durum"], durum_map["bilinmiyor"])

    vfa_html = ""
    if m["vfa_uyari"]:
        vfa_html = ('<div class="kpi-warn">⚠ Simulasyon sonuna dogru asetat (VFA) birikimi '
                    'gozleniyor — organik yuk fazla olabilir.</div>')

    cards = [
        ("Toplam Metan Verimi", _fmt(m["toplam_ch4"], 0, " m³"), f"{_fmt(m['sim_days'],0)} gunluk periyot", "#34C759"),
        ("Gunluk Ort. Metan",   _fmt(m["gunluk_ch4"], 1, " m³/gun"), "periyot ortalamasi", "#30B0C7"),
        ("Ort. CH₄ İçeriği",    _fmt(m["ort_ch4_pct"], 1, "%"), "kararli hal (son %30)", "#007AFF"),
        ("Tepe Biyogaz Debisi", _fmt(m["tepe_gas"], 1, " m³/gun"), "maksimum anlik uretim", "#AF52DE"),
        ("Min / Son pH",        f"{_fmt(m['min_ph'],2)} / {_fmt(m['son_ph'],2)}", "devreye alma sonrasi min", d_color),
    ]
    card_html = ""
    for title, val, sub, color in cards:
        card_html += f'''
        <div class="kpi-card">
            <div class="kpi-accent" style="background:{color};"></div>
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">{sub}</div>
        </div>'''

    return f'''
    <div class="verdict" style="background:{d_bg}; border-color:{d_color}33;">
        <div class="verdict-dot" style="background:{d_color};"></div>
        <div class="verdict-text">
            <span class="verdict-label" style="color:{d_color};">Reaktor Durumu: {d_label}</span>
            <span class="verdict-desc">{d_desc}</span>
        </div>
    </div>
    {vfa_html}
    <div class="kpi-strip">{card_html}</div>
    '''


def get_dashboard_html(df, manure_name="Seçilen Gübre", sim_days=None,
                       back_url=None, csv_b64=None):
    """
    Pandas veri cercevesini alir ve interaktif Chart.js dashboard'unun HTML
    kodunu metin olarak dondurur. sim_days verilmezse df'teki son zamandan
    turetilir (x-ekseni ve zoom limitleri buna gore dinamik ayarlanir).

    back_url: verilirse ust barda "Yeni Simulasyon" geri linki cizilir.
    csv_b64:  verilirse ust barda CSV indirme butonu (data-URI) cizilir.
    """
    if sim_days is None:
        sim_days = float(df["time"].iloc[-1]) if "time" in df.columns else len(df)
    axis_max = float(np.ceil(sim_days))

    metrics = _compute_metrics(df, sim_days)
    kpi_html = _build_kpi_html(metrics)

    sample_df = df.iloc[::20, :]
    time_data = sample_df['time'].tolist() if 'time' in sample_df.columns else list(range(len(sample_df)))

    def col(name):
        return sample_df[name].tolist() if name in sample_df.columns else []

    data_payload = {
        "manureName": manure_name,
        "labels": time_data,
        "ph": col('pH'),
        "ch4": col('S_gas_ch4'),
        "co2": col('S_gas_co2'),
        "ac": col('S_ac'),
        "pro": col('S_pro'),
        "bu": col('S_bu'),
        "su": col('S_su'),
        "aa": col('S_aa'),
        "fa": col('S_fa'),
        "qgas": col('q_gas'),
        "qch4": col('q_ch4'),
        "ch4pct": col('ch4_pct'),
    }

    html_template = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
        <style>
            :root {
                --ios-blur: blur(40px);
                --card-bg: rgba(255, 255, 255, 0.75);
                --border: 1px solid rgba(255, 255, 255, 0.8);
                --accent-blue: #007AFF;
                --accent-purple: #AF52DE;
                --ios-curve: cubic-bezier(0.16, 1, 0.3, 1);
            }
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, system-ui, sans-serif; }
            html, body {
                background: #F2F2F7;
                background-image: radial-gradient(circle at 2% 2%, rgba(175, 82, 222, 0.05) 0%, transparent 40%),
                                  radial-gradient(circle at 98% 98%, rgba(0, 122, 255, 0.05) 0%, transparent 40%);
                background-attachment: fixed;
                min-height: 100%;
            }
            body { padding: 28px 24px 60px; overflow-x: hidden; }

            .container { max-width: 1200px; margin: 0 auto; }

            /* Ust aksiyon barindaki geri / indirme butonlari */
            .top-link {
                display: inline-flex; align-items: center; gap: 6px; text-decoration: none;
                font-size: 14px; font-weight: 700; padding: 9px 16px; border-radius: 14px;
                border: 1px solid rgba(255,255,255,0.7); background: rgba(255,255,255,0.6);
                backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
                color: #1C1C1E; box-shadow: 0 4px 14px rgba(0,0,0,0.05);
                transition: transform .25s var(--ios-curve), box-shadow .25s ease;
            }
            .top-link:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
            .top-link.dl { background: rgba(0,122,255,0.10); color: var(--accent-blue); border-color: rgba(0,122,255,0.2); }

            header { margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
            .header-text h1 { font-size: 28px; font-weight: 800; color: #1C1C1E; letter-spacing: -0.5px; }
            .header-text .sub { font-size: 14px; color: #8E8E93; font-weight: 500; margin-top: 2px; }

            .top-btns { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
            .btn {
                width: 175px; padding: 10px; border-radius: 12px; font-weight: 600; cursor: pointer;
                border: 1px solid rgba(0,0,0,0.05); backdrop-filter: blur(15px);
                transition: transform 0.3s var(--ios-curve), box-shadow 0.3s ease; font-size: 13px;
            }
            .btn:hover { transform: scale(1.05); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
            .btn-sync { background: rgba(175, 82, 222, 0.1); color: var(--accent-purple); }
            .btn-reset { background: rgba(0, 122, 255, 0.1); color: var(--accent-blue); }

            /* ---- STABILITE VERDISI ---- */
            .verdict {
                display: flex; align-items: center; gap: 14px; padding: 16px 22px;
                border-radius: 20px; border: 1px solid; margin-bottom: 14px;
                backdrop-filter: var(--ios-blur); -webkit-backdrop-filter: var(--ios-blur);
            }
            .verdict-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
                box-shadow: 0 0 0 4px rgba(255,255,255,0.5); }
            .verdict-text { display: flex; flex-direction: column; }
            .verdict-label { font-size: 17px; font-weight: 700; }
            .verdict-desc { font-size: 13px; color: #3A3A3C; margin-top: 1px; }
            .kpi-warn {
                background: rgba(255,149,0,0.10); color: #B25000; font-size: 13px; font-weight: 600;
                padding: 12px 18px; border-radius: 16px; margin-bottom: 14px;
                border: 1px solid rgba(255,149,0,0.25);
            }

            /* ---- KPI SERIDI ---- */
            .kpi-strip {
                display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 35px;
            }
            .kpi-card {
                position: relative; overflow: hidden;
                background: var(--card-bg); backdrop-filter: var(--ios-blur); -webkit-backdrop-filter: var(--ios-blur);
                border: var(--border); border-radius: 22px; padding: 18px 18px 16px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.04);
                transition: transform 0.3s var(--ios-curve), box-shadow 0.3s ease;
            }
            .kpi-card:hover { transform: scale(1.03); box-shadow: 0 15px 35px rgba(0,0,0,0.08); }
            .kpi-accent { position: absolute; top: 0; left: 0; width: 100%; height: 4px; }
            .kpi-title { font-size: 12px; font-weight: 600; color: #8E8E93; margin-bottom: 8px;
                text-transform: uppercase; letter-spacing: 0.3px; }
            .kpi-value { font-size: 24px; font-weight: 800; color: #1C1C1E; letter-spacing: -0.5px; line-height: 1.1; }
            .kpi-sub { font-size: 11px; color: #AEAEB2; margin-top: 6px; }

            @media (max-width: 900px) { .kpi-strip { grid-template-columns: repeat(2, 1fr); } }

            .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 30px; }
            .card-placeholder { width: 100%; height: 420px; position: relative; }

            .card {
                width: 100%; height: 100%; background: var(--card-bg); backdrop-filter: var(--ios-blur); -webkit-backdrop-filter: var(--ios-blur);
                border-radius: 30px; border: var(--border); box-shadow: 0 8px 25px rgba(0,0,0,0.04); padding: 25px;
                display: flex; flex-direction: column; position: absolute; top: 0; left: 0; z-index: 1;
                transition: all 0.5s var(--ios-curve), box-shadow 0.5s var(--ios-curve);
            }
            .card:hover:not(.expanded) { transform: scale(1.02); box-shadow: 0 15px 40px rgba(0,0,0,0.08); }

            .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
            .card-header h3 { font-size: 18px; font-weight: 700; color: #1C1C1E; }

            .icon-btn {
                background: rgba(0,0,0,0.05); border: none; border-radius: 50%; width: 38px; height: 38px;
                cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px;
                color: #3A3A3C; transition: transform 0.3s var(--ios-curve), background 0.3s ease;
            }
            .icon-btn:hover { transform: scale(1.08); background: rgba(255, 255, 255, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .close-btn:hover { color: #FF3B30; }

            .card.expanded {
                z-index: 1001 !important;
                padding: 30px;
                box-shadow: 0 40px 100px rgba(0,0,0,0.4) !important;
            }

            .close-btn { display: none; }
            .card.expanded .close-btn { display: flex; }

            .chart-container { position: relative; width: 100%; flex-grow: 1; min-height: 0; height: 100%; }

            #overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(242, 242, 247, 0.45);
                backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
                z-index: 1000; opacity: 0; pointer-events: none; transition: opacity 0.4s ease;
            }
            #overlay.active { opacity: 1; pointer-events: all; }

            body.is-expanded-mode .card-placeholder .card:not(.expanded) {
                opacity: 0 !important;
                pointer-events: none !important;
                transition: opacity 0.3s ease;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="header-text">
                    {{BACK_LINK}}
                    <h1>Analiz Sonuçları</h1>
                    <div class="sub">{{MANURE_NAME}}</div>
                </div>
                <div class="top-btns">
                    {{DOWNLOAD_BTN}}
                    <button class="btn btn-sync" onclick="syncAllZooms()">Görünümleri Eşitle</button>
                    <button class="btn btn-reset" onclick="resetAll()">Sıfırla (0-{{AXIS_MAX}} Gün)</button>
                </div>
            </header>

            {{KPI_HTML}}

            <div class="grid">
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Biyogaz Üretim Debisi</h3></div><div class="chart-container"><canvas id="chartProd"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>pH Seviyesi</h3></div><div class="chart-container"><canvas id="chartPH"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Biyogaz Bileşenleri (gaz fazı)</h3></div><div class="chart-container"><canvas id="chartGas"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Uçucu Yağ Asitleri</h3></div><div class="chart-container"><canvas id="chartVFA"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Çözünmüş Substratlar</h3></div><div class="chart-container"><canvas id="chartSub"></canvas></div></div></div>
            </div>
        </div>
        <script>
            // NOT: Buyutme artik yalnizca iframe kendi viewport'u icinde calisir.
            // window.parent'a uzanan blur/scroll hack'leri kaldirildi (kirilgan +
            // "sayfa icinde sayfa" hissini bozuyordu).
            const rawData = {{DATA_JSON}};
            const AXIS_MAX = {{AXIS_MAX}};
            const mapData = (arr) => rawData.labels.map((t, i) => ({ x: t, y: (arr && arr[i] !== undefined) ? arr[i] : null }));
            let syncMin = 0; let syncMax = AXIS_MAX;

            const stepFor = (range) => (range > AXIS_MAX * 0.28) ? Math.max(5, Math.round(AXIS_MAX/8)) : undefined;

            const handleZoom = (e) => {
                const chart = e.chart;
                syncMin = chart.scales.x.min; syncMax = chart.scales.x.max;
                chart.options.scales.x.ticks.stepSize = stepFor(syncMax - syncMin);
                chart.update('none');
            };

            const baseOptions = {
                responsive: true, maintainAspectRatio: false, animation: { duration: 0 },
                plugins: {
                    tooltip: { enabled: true, backgroundColor: 'rgba(0, 0, 0, 0.8)', padding: 10, cornerRadius: 8 },
                    legend: { position: 'bottom', labels: { usePointStyle: true, font: { size: 11, weight: '600' } } },
                    zoom: {
                        limits: { x: { min: 0, max: AXIS_MAX, minRange: 0.1 } },
                        pan: { enabled: true, mode: 'x', onPanComplete: handleZoom },
                        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x', onZoomComplete: handleZoom }
                    }
                },
                scales: {
                    x: { type: 'linear', min: 0, max: AXIS_MAX, ticks: { stepSize: Math.max(5, Math.round(AXIS_MAX/8)), color: '#8E8E93' }, grid: { display: false } },
                    y: { grid: { color: 'rgba(0,0,0,0.03)' }, ticks: { color: '#8E8E93' } }
                },
                elements: { line: { tension: 0.35 }, point: { radius: 0, hoverRadius: 8 } },
                interaction: { mode: 'index', intersect: false }
            };

            const charts = {
                prod: new Chart(document.getElementById('chartProd'), { type: 'line', data: { datasets: [{ label: 'Toplam Biyogaz (m³/gün)', data: mapData(rawData.qgas), borderColor: '#AF52DE', borderWidth: 2.5, fill: false }, { label: 'Metan (m³/gün)', data: mapData(rawData.qch4), borderColor: '#34C759', borderWidth: 2.5, fill: false }]}, options: JSON.parse(JSON.stringify(baseOptions)) }),
                ph: new Chart(document.getElementById('chartPH'), { type: 'line', data: { datasets: [{ label: 'pH', data: mapData(rawData.ph), borderColor: '#AF52DE', borderWidth: 2.5, fill: false }] }, options: JSON.parse(JSON.stringify(baseOptions)) }),
                gas: new Chart(document.getElementById('chartGas'), { type: 'line', data: { datasets: [{ label: 'Metan', data: mapData(rawData.ch4), borderColor: '#34C759', borderWidth: 2.5, fill: false }, { label: 'CO2', data: mapData(rawData.co2), borderColor: '#8E8E93', borderWidth: 2, borderDash: [5,5], fill: false }]}, options: JSON.parse(JSON.stringify(baseOptions)) }),
                vfa: new Chart(document.getElementById('chartVFA'), { type: 'line', data: { datasets: [{ label: 'Asetat', data: mapData(rawData.ac), borderColor: '#FF3B30', borderWidth: 2.5, fill: false }, { label: 'Propiyonat', data: mapData(rawData.pro), borderColor: '#FF9500', borderWidth: 2 }, { label: 'Bütirat', data: mapData(rawData.bu), borderColor: '#A2845E', borderWidth: 2 }]}, options: JSON.parse(JSON.stringify(baseOptions)) }),
                sub: new Chart(document.getElementById('chartSub'), { type: 'line', data: { datasets: [{ label: 'Şekerler', data: mapData(rawData.su), borderColor: '#007AFF', borderWidth: 2.5, fill: false }, { label: 'Amino Asitler', data: mapData(rawData.aa), borderColor: '#FF2D55', borderWidth: 2 }, { label: 'Yağ Asitleri', data: mapData(rawData.fa), borderColor: '#5AC8FA', borderWidth: 2 }]}, options: JSON.parse(JSON.stringify(baseOptions)) })
            };

            function resetAll() { syncMin = 0; syncMax = AXIS_MAX; Object.values(charts).forEach(c => { c.options.scales.x.min = 0; c.options.scales.x.max = AXIS_MAX; c.options.scales.x.ticks.stepSize = Math.max(5, Math.round(AXIS_MAX/8)); c.update(); }); }
            function syncAllZooms() { Object.values(charts).forEach(c => { c.options.scales.x.min = syncMin; c.options.scales.x.max = syncMax; c.options.scales.x.ticks.stepSize = stepFor(syncMax - syncMin); c.update('none'); }); }

            // NOT: Tam-ekran buyutme (expand) kaldirildi. Grafikler fare tekeri /
            // surukleme ile yakinlastirilabilir; yakindan inceleme bununla yapilir.
            // Pano artik Flask tarafindan dogrudan tam sayfa olarak sunuluyor (iframe yok).
        </script>
    </body>
    </html>
    """

    back_link = f'<a class="top-link" href="{back_url}">← Yeni Simülasyon</a>' if back_url else ""
    download_btn = (
        f'<a class="top-link dl" download="codigestion_out.csv" '
        f'href="data:text/csv;base64,{csv_b64}">↓ CSV İndir</a>' if csv_b64 else ""
    )

    final_html = html_template.replace("{{DATA_JSON}}", json.dumps(data_payload))
    final_html = final_html.replace("{{KPI_HTML}}", kpi_html)
    final_html = final_html.replace("{{AXIS_MAX}}", str(int(axis_max)))
    final_html = final_html.replace("{{MANURE_NAME}}", manure_name)
    final_html = final_html.replace("{{BACK_LINK}}", back_link)
    final_html = final_html.replace("{{DOWNLOAD_BTN}}", download_btn)

    return final_html


# =====================================================================
# ADIM 3: KARSILASTIRMA MODU  (2 senaryo A / B)
# =====================================================================
_DURUM_RANK = {"stabil": 3, "sinirda": 2, "kritik": 1, "bilinmiyor": 0}
_DURUM_LBL = {"stabil": "Stabil", "sinirda": "Sınırda", "kritik": "Kritik", "bilinmiyor": "Belirsiz"}


def _cmp_rows(ma, mb):
    """(etiket, a_str, b_str, kazanan) satirlarini uretir. kazanan: 'a'|'b'|None."""
    def hi(a, b):  # yuksek olan kazanir
        if a is None or b is None:
            return None
        if abs(a - b) < 1e-9:
            return None
        return "a" if a > b else "b"

    rows = [
        ("Toplam Metan (m³)", _fmt(ma["toplam_ch4"], 0), _fmt(mb["toplam_ch4"], 0),
         hi(ma["toplam_ch4"], mb["toplam_ch4"])),
        ("Günlük Ort. Metan (m³/gün)", _fmt(ma["gunluk_ch4"], 1), _fmt(mb["gunluk_ch4"], 1),
         hi(ma["gunluk_ch4"], mb["gunluk_ch4"])),
        ("Ort. CH₄ İçeriği (%)", _fmt(ma["ort_ch4_pct"], 1), _fmt(mb["ort_ch4_pct"], 1),
         hi(ma["ort_ch4_pct"], mb["ort_ch4_pct"])),
        ("Tepe Biyogaz (m³/gün)", _fmt(ma["tepe_gas"], 1), _fmt(mb["tepe_gas"], 1),
         hi(ma["tepe_gas"], mb["tepe_gas"])),
        ("Min pH (devreye alma sonrası)", _fmt(ma["min_ph"], 2), _fmt(mb["min_ph"], 2),
         hi(ma["min_ph"], mb["min_ph"])),
    ]
    # Reaktor durumu (siralamaya gore)
    ra, rb = _DURUM_RANK.get(ma["durum"], 0), _DURUM_RANK.get(mb["durum"], 0)
    win_d = None if ra == rb else ("a" if ra > rb else "b")
    rows.append(("Reaktör Durumu", _DURUM_LBL.get(ma["durum"]), _DURUM_LBL.get(mb["durum"]), win_d))
    return rows


def _sample_payload(df):
    s = df.iloc[::20, :]

    def col(n):
        return s[n].tolist() if n in s.columns else []
    return {
        "labels": s["time"].tolist() if "time" in s.columns else list(range(len(s))),
        "ph": col("pH"), "ch4": col("S_gas_ch4"), "co2": col("S_gas_co2"),
        "ac": col("S_ac"), "pro": col("S_pro"), "bu": col("S_bu"),
        "su": col("S_su"), "aa": col("S_aa"), "fa": col("S_fa"),
        "qgas": col("q_gas"), "qch4": col("q_ch4"),
    }


def get_comparison_html(df_a, name_a, df_b, name_b, sim_days=None,
                        back_url=None, csv_a_b64=None, csv_b_b64=None):
    """Iki senaryoyu (A/B) karsilastiran pano: ustte kazanan-vurgulu KPI tablosu,
    altta her metrik icin A ve B grafikleri yan yana.

    back_url / csv_a_b64 / csv_b_b64: verilirse ust barda geri linki ve
    A/B icin CSV indirme butonlari cizilir."""
    if sim_days is None:
        sim_days = max(
            float(df_a["time"].iloc[-1]) if "time" in df_a.columns else len(df_a),
            float(df_b["time"].iloc[-1]) if "time" in df_b.columns else len(df_b),
        )
    axis_max = int(np.ceil(sim_days))

    ma = _compute_metrics(df_a, sim_days)
    mb = _compute_metrics(df_b, sim_days)
    rows = _cmp_rows(ma, mb)

    # --- KPI tablosu HTML ---
    tr_html = ""
    for label, av, bv, win in rows:
        a_cls = "win" if win == "a" else ""
        b_cls = "win" if win == "b" else ""
        tr_html += (f'<tr><td class="mlabel">{label}</td>'
                    f'<td class="{a_cls}">{av}</td><td class="{b_cls}">{bv}</td></tr>')

    payload = {"a": _sample_payload(df_a), "b": _sample_payload(df_b)}

    html = """
    <!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
    <style>
        :root { --ios-blur: blur(40px); --card-bg: rgba(255,255,255,0.75);
            --border: 1px solid rgba(255,255,255,0.8); --ios-curve: cubic-bezier(0.16,1,0.3,1); }
        * { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system, system-ui, sans-serif; }
        html, body {
            background:#F2F2F7;
            background-image: radial-gradient(circle at 2% 2%, rgba(175,82,222,0.05) 0%, transparent 40%),
                             radial-gradient(circle at 98% 98%, rgba(0,122,255,0.05) 0%, transparent 40%);
            background-attachment:fixed; min-height:100%;
        }
        body { padding:28px 24px 60px; overflow-x:hidden; }
        .container { max-width:1200px; margin:0 auto; }
        .cmp-topbar { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:18px; flex-wrap:wrap; }
        .cmp-topbar .dl-group { display:flex; gap:10px; }
        .top-link { display:inline-flex; align-items:center; gap:6px; text-decoration:none;
            font-size:14px; font-weight:700; padding:9px 16px; border-radius:14px;
            border:1px solid rgba(255,255,255,0.7); background:rgba(255,255,255,0.6);
            backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
            color:#1C1C1E; box-shadow:0 4px 14px rgba(0,0,0,0.05);
            transition:transform .25s var(--ios-curve), box-shadow .25s ease; }
        .top-link:hover { transform:translateY(-1px); box-shadow:0 8px 20px rgba(0,0,0,0.08); }
        .top-link.dl-a { background:rgba(0,122,255,0.10); color:#007AFF; border-color:rgba(0,122,255,0.2); }
        .top-link.dl-b { background:rgba(175,82,222,0.10); color:#AF52DE; border-color:rgba(175,82,222,0.2); }
        h1 { font-size:28px; font-weight:800; color:#1C1C1E; letter-spacing:-0.5px; margin-bottom:20px; }

        .cmp-table-wrap { background:var(--card-bg); backdrop-filter:var(--ios-blur); -webkit-backdrop-filter:var(--ios-blur);
            border:var(--border); border-radius:24px; padding:10px 22px 18px; box-shadow:0 8px 25px rgba(0,0,0,0.04); margin-bottom:35px; }
        table { width:100%; border-collapse:collapse; }
        th, td { padding:13px 14px; text-align:right; font-size:15px; }
        th { font-size:13px; font-weight:700; color:#1C1C1E; border-bottom:2px solid rgba(0,0,0,0.06); }
        th.a-head { color:#007AFF; } th.b-head { color:#AF52DE; }
        td { color:#1C1C1E; font-weight:600; border-bottom:1px solid rgba(0,0,0,0.04); }
        td.mlabel { text-align:left; color:#6C6C70; font-weight:600; }
        td.win { background:rgba(52,199,89,0.14); color:#1B7A32; font-weight:800; border-radius:8px; }
        .legend-note { font-size:12px; color:#AEAEB2; margin-top:8px; text-align:right; }

        .cmp-grid { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
        .cmp-rowtitle { grid-column:1/-1; font-size:16px; font-weight:700; color:#1C1C1E; margin:6px 0 -6px 6px; }
        .cchip { display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; margin-left:8px; vertical-align:middle; }
        .cchip.a { background:rgba(0,122,255,0.12); color:#007AFF; }
        .cchip.b { background:rgba(175,82,222,0.12); color:#AF52DE; }
        .ccard { background:var(--card-bg); backdrop-filter:var(--ios-blur); -webkit-backdrop-filter:var(--ios-blur);
            border:var(--border); border-radius:24px; box-shadow:0 8px 25px rgba(0,0,0,0.04); padding:18px; height:320px;
            display:flex; flex-direction:column; transition:transform 0.3s var(--ios-curve), box-shadow 0.3s ease; }
        .ccard:hover { transform:scale(1.02); box-shadow:0 15px 40px rgba(0,0,0,0.08); }
        .ccard .lbl { font-size:12px; font-weight:700; margin-bottom:8px; }
        .ccard.a .lbl { color:#007AFF; } .ccard.b .lbl { color:#AF52DE; }
        .cc-cont { position:relative; flex-grow:1; min-height:0; }
        @media (max-width:820px){ .cmp-grid{ grid-template-columns:1fr; } }
    </style></head><body>
    <div class="container">
        {{TOPBAR}}
        <h1>Karşılaştırma: A / B</h1>
        <div class="cmp-table-wrap">
            <table>
                <tr><th class="mlabel" style="text-align:left;">Metrik</th>
                    <th class="a-head">A · {{NAME_A}}</th><th class="b-head">B · {{NAME_B}}</th></tr>
                {{ROWS}}
            </table>
            <div class="legend-note">Yeşil hücre = o metrikte daha iyi senaryo.</div>
        </div>
        <div class="cmp-grid">{{CARDS}}</div>
    </div>
    <script>
        const D = {{DATA}};
        const AX = {{AXIS}};
        const md = (labels, arr) => labels.map((t,i)=>({x:t, y:(arr&&arr[i]!==undefined)?arr[i]:null}));
        const step = Math.max(5, Math.round(AX/8));
        function baseOpts(){ return {
            responsive:true, maintainAspectRatio:false, animation:{duration:0},
            plugins:{ tooltip:{enabled:true, backgroundColor:'rgba(0,0,0,0.8)', padding:10, cornerRadius:8},
                legend:{position:'bottom', labels:{usePointStyle:true, font:{size:10, weight:'600'}}},
                zoom:{ limits:{x:{min:0,max:AX,minRange:0.1}}, pan:{enabled:true,mode:'x'},
                    zoom:{wheel:{enabled:true}, pinch:{enabled:true}, mode:'x'} } },
            scales:{ x:{type:'linear',min:0,max:AX,ticks:{stepSize:step,color:'#8E8E93'},grid:{display:false}},
                y:{grid:{color:'rgba(0,0,0,0.03)'},ticks:{color:'#8E8E93'}} },
            elements:{line:{tension:0.35}, point:{radius:0,hoverRadius:7}}, interaction:{mode:'index',intersect:false}
        }; }
        function mk(id, side, sets){
            const S = D[side];
            new Chart(document.getElementById(id), { type:'line',
                data:{ datasets: sets.map(s=>({label:s.l, data:md(S.labels, S[s.k]), borderColor:s.c,
                    borderWidth:s.w||2, borderDash:s.d||[], fill:false})) }, options: baseOpts() });
        }
        const SPEC = [
            ['prod', [{k:'qgas',l:'Toplam Biyogaz',c:'#AF52DE',w:2.5},{k:'qch4',l:'Metan',c:'#34C759',w:2.5}]],
            ['ph',   [{k:'ph',l:'pH',c:'#AF52DE',w:2.5}]],
            ['gas',  [{k:'ch4',l:'Metan',c:'#34C759',w:2.5},{k:'co2',l:'CO2',c:'#8E8E93',w:2,d:[5,5]}]],
            ['vfa',  [{k:'ac',l:'Asetat',c:'#FF3B30',w:2.5},{k:'pro',l:'Propiyonat',c:'#FF9500'},{k:'bu',l:'Bütirat',c:'#A2845E'}]],
            ['sub',  [{k:'su',l:'Şekerler',c:'#007AFF',w:2.5},{k:'aa',l:'Amino Asitler',c:'#FF2D55'},{k:'fa',l:'Yağ Asitleri',c:'#5AC8FA'}]],
        ];
        SPEC.forEach(([base, sets])=>{ mk(base+'_a','a',sets); mk(base+'_b','b',sets); });
    </script></body></html>
    """

    METRIC_TITLES = [
        ("prod", "Biyogaz Üretim Debisi"),
        ("ph", "pH Seviyesi"),
        ("gas", "Biyogaz Bileşenleri (gaz fazı)"),
        ("vfa", "Uçucu Yağ Asitleri"),
        ("sub", "Çözünmüş Substratlar"),
    ]
    cards = ""
    for base, title in METRIC_TITLES:
        cards += f'<div class="cmp-rowtitle">{title}</div>'
        cards += (f'<div class="ccard a"><div class="lbl">A · {name_a}</div>'
                  f'<div class="cc-cont"><canvas id="{base}_a"></canvas></div></div>')
        cards += (f'<div class="ccard b"><div class="lbl">B · {name_b}</div>'
                  f'<div class="cc-cont"><canvas id="{base}_b"></canvas></div></div>')

    topbar = ""
    if back_url or csv_a_b64 or csv_b_b64:
        back = f'<a class="top-link" href="{back_url}">← Yeni Simülasyon</a>' if back_url else "<span></span>"
        dls = ""
        if csv_a_b64:
            dls += (f'<a class="top-link dl-a" download="karsilastirma_A.csv" '
                    f'href="data:text/csv;base64,{csv_a_b64}">↓ A · CSV</a>')
        if csv_b_b64:
            dls += (f'<a class="top-link dl-b" download="karsilastirma_B.csv" '
                    f'href="data:text/csv;base64,{csv_b_b64}">↓ B · CSV</a>')
        topbar = f'<div class="cmp-topbar">{back}<div class="dl-group">{dls}</div></div>'

    html = html.replace("{{DATA}}", json.dumps(payload))
    html = html.replace("{{AXIS}}", str(axis_max))
    html = html.replace("{{ROWS}}", tr_html)
    html = html.replace("{{CARDS}}", cards)
    html = html.replace("{{NAME_A}}", name_a)
    html = html.replace("{{NAME_B}}", name_b)
    html = html.replace("{{TOPBAR}}", topbar)
    return html
