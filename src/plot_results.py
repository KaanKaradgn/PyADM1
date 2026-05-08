import pandas as pd
import json

def get_dashboard_html(df, manure_name="Seçilen Gübre"):
    """
    Pandas veri çerçevesini alır ve interaktif Chart.js 
    dashboard'unun HTML kodunu metin olarak döndürür.
    """
    sample_df = df.iloc[::20, :] 
    time_data = sample_df['time'].tolist() if 'time' in sample_df.columns else list(range(len(sample_df)))
    
    data_payload = {
        "manureName": manure_name,
        "labels": time_data,
        "ph": sample_df['pH'].tolist(),
        "ch4": sample_df['S_gas_ch4'].tolist(),
        "co2": sample_df['S_gas_co2'].tolist(),
        "ac": sample_df['S_ac'].tolist(),
        "pro": sample_df['S_pro'].tolist(),
        "bu": sample_df['S_bu'].tolist(),
        "su": sample_df['S_su'].tolist(),
        "aa": sample_df['S_aa'].tolist(),
        "fa": sample_df['S_fa'].tolist()
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
            body { background: transparent; padding: 10px; overflow-x: hidden; }
            
            .container { max-width: 1200px; margin: 0 auto; }
            
            header { margin-bottom: 35px; display: flex; justify-content: space-between; align-items: center; }
            .header-text h1 { font-size: 28px; font-weight: 800; color: #1C1C1E; letter-spacing: -0.5px; }
            
            .top-btns { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
            .btn { 
                width: 175px; padding: 10px; border-radius: 12px; font-weight: 600; cursor: pointer; 
                border: 1px solid rgba(0,0,0,0.05); backdrop-filter: blur(15px); 
                transition: transform 0.3s var(--ios-curve), box-shadow 0.3s ease; font-size: 13px; 
            }
            .btn:hover { transform: scale(1.05); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
            .btn-sync { background: rgba(175, 82, 222, 0.1); color: var(--accent-purple); }
            .btn-reset { background: rgba(0, 122, 255, 0.1); color: var(--accent-blue); }

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
            .card.expanded .expand-btn { display: none; }
            .card.expanded .close-btn { display: flex; }
            
            .chart-container { position: relative; width: 100%; flex-grow: 1; min-height: 0; height: 100%; }
            
            #overlay { 
                position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                background: transparent; 
                z-index: 1000; opacity: 0; pointer-events: none; transition: opacity 0.5s ease; 
            }
            #overlay.active { opacity: 1; pointer-events: all; }

            /* HAYALET KUTULARI GİZLEME MANTIĞI */
            body.is-expanded-mode .card-placeholder .card:not(.expanded) {
                opacity: 0 !important;
                pointer-events: none !important;
                transition: opacity 0.3s ease;
            }
        </style>
    </head>
    <body>
        <div id="overlay" onclick="shrinkCard()"></div>
        <div class="container">
            <header>
                <div class="header-text"><h1>Analiz Sonuçları</h1></div>
                <div class="top-btns">
                    <button class="btn btn-sync" onclick="syncAllZooms()">Görünümleri Eşitle</button>
                    <button class="btn btn-reset" onclick="resetAll()">Sıfırla (0-280 Gün)</button>
                </div>
            </header>
            <div class="grid">
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>pH Seviyesi</h3><div class="header-controls"><button class="icon-btn expand-btn" onclick="expandCard(this)">⤢</button><button class="icon-btn close-btn" onclick="shrinkCard(this)">✕</button></div></div><div class="chart-container"><canvas id="chartPH"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Biyogaz Bileşenleri</h3><div class="header-controls"><button class="icon-btn expand-btn" onclick="expandCard(this)">⤢</button><button class="icon-btn close-btn" onclick="shrinkCard(this)">✕</button></div></div><div class="chart-container"><canvas id="chartGas"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Uçucu Yağ Asitleri</h3><div class="header-controls"><button class="icon-btn expand-btn" onclick="expandCard(this)">⤢</button><button class="icon-btn close-btn" onclick="shrinkCard(this)">✕</button></div></div><div class="chart-container"><canvas id="chartVFA"></canvas></div></div></div>
                <div class="card-placeholder"><div class="card"><div class="card-header"><h3>Çözünmüş Substratlar</h3><div class="header-controls"><button class="icon-btn expand-btn" onclick="expandCard(this)">⤢</button><button class="icon-btn close-btn" onclick="shrinkCard(this)">✕</button></div></div><div class="chart-container"><canvas id="chartSub"></canvas></div></div></div>
            </div>
        </div>
        <script>
            const preventScroll = (e) => { e.preventDefault(); };
            const preventKeyScroll = (e) => {
                if(["Space", "ArrowUp", "ArrowDown", "PageUp", "PageDown"].includes(e.code)) { e.preventDefault(); }
            };

            function lockParentScroll() {
                try {
                    const parentDoc = window.parent.document;
                    
                    // Ana sayfadaki stApp blurunu zorla temizle
                    const mainContainer = parentDoc.querySelector('.stApp');
                    if(mainContainer) {
                        mainContainer.classList.remove('main-blur');
                        mainContainer.style.filter = 'none'; 
                    }
                    
                    // KUSURSUZ ARKA PLAN BUĞUSU
                    let blurOverlay = parentDoc.getElementById('global-streamlit-blur');
                    if (!blurOverlay) {
                        blurOverlay = parentDoc.createElement('div');
                        blurOverlay.id = 'global-streamlit-blur';
                        blurOverlay.style.position = 'fixed';
                        blurOverlay.style.top = '0';
                        blurOverlay.style.left = '0';
                        blurOverlay.style.width = '100vw';
                        blurOverlay.style.height = '100vh';
                        blurOverlay.style.background = 'rgba(255, 255, 255, 0.2)';
                        blurOverlay.style.backdropFilter = 'blur(15px)';
                        blurOverlay.style.webkitBackdropFilter = 'blur(15px)';
                        blurOverlay.style.zIndex = '999990';
                        blurOverlay.style.opacity = '0';
                        blurOverlay.style.transition = 'opacity 0.5s ease';
                        parentDoc.body.appendChild(blurOverlay);
                    }
                    
                    void blurOverlay.offsetWidth;
                    blurOverlay.style.opacity = '1';
                    
                    if (window.frameElement) {
                        window.frameElement.style.position = 'relative';
                        window.frameElement.style.zIndex = '999995'; 
                        window.frameElement.style.background = 'transparent'; // Varsayılan Streamlit arkaplanını ezer
                        window.frameElement.style.border = 'none';
                    }
                    
                    window.parent.addEventListener('wheel', preventScroll, { passive: false });
                    window.parent.addEventListener('touchmove', preventScroll, { passive: false });
                    window.parent.addEventListener('keydown', preventKeyScroll, { passive: false });
                } catch(e) {}
            }

            function unlockParentScroll() {
                try {
                    const parentDoc = window.parent.document;
                    
                    let blurOverlay = parentDoc.getElementById('global-streamlit-blur');
                    if (blurOverlay) {
                        blurOverlay.style.opacity = '0';
                        setTimeout(() => {
                            if(blurOverlay && blurOverlay.parentNode) blurOverlay.parentNode.removeChild(blurOverlay);
                        }, 500);
                    }
                    
                    if (window.frameElement) {
                        window.frameElement.style.zIndex = '1';
                        setTimeout(() => { window.frameElement.style.position = ''; }, 500);
                    }
                    
                    window.parent.removeEventListener('wheel', preventScroll);
                    window.parent.removeEventListener('touchmove', preventScroll);
                    window.parent.removeEventListener('keydown', preventKeyScroll);
                } catch(e) {}
            }

            const rawData = {{DATA_JSON}};
            const mapData = (arr) => rawData.labels.map((t, i) => ({ x: t, y: arr[i] }));
            let syncMin = 0; let syncMax = 280;

            const handleZoom = (e) => {
                const chart = e.chart;
                syncMin = chart.scales.x.min; syncMax = chart.scales.x.max;
                const range = syncMax - syncMin;
                chart.options.scales.x.ticks.stepSize = (range > 80) ? 35 : undefined;
                chart.update('none');
            };

            const baseOptions = {
                responsive: true, maintainAspectRatio: false, animation: { duration: 0 }, 
                plugins: {
                    tooltip: { enabled: true, backgroundColor: 'rgba(0, 0, 0, 0.8)', padding: 10, cornerRadius: 8 },
                    legend: { position: 'bottom', labels: { usePointStyle: true, font: { size: 11, weight: '600' } } },
                    zoom: { 
                        limits: { x: { min: 0, max: 280, minRange: 0.1 } },
                        pan: { enabled: true, mode: 'x', onPanComplete: handleZoom },
                        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x', onZoomComplete: handleZoom }
                    }
                },
                scales: {
                    x: { type: 'linear', min: 0, max: 280, ticks: { stepSize: 35, color: '#8E8E93' }, grid: { display: false } },
                    y: { grid: { color: 'rgba(0,0,0,0.03)' }, ticks: { color: '#8E8E93' } }
                },
                elements: { line: { tension: 0.35 }, point: { radius: 0, hoverRadius: 8 } },
                interaction: { mode: 'index', intersect: false }
            };

            const charts = {
                ph: new Chart(document.getElementById('chartPH'), { type: 'line', data: { datasets: [{ label: 'pH', data: mapData(rawData.ph), borderColor: '#AF52DE', borderWidth: 2.5, fill: false }] }, options: JSON.parse(JSON.stringify(baseOptions)) }),
                gas: new Chart(document.getElementById('chartGas'), { type: 'line', data: { datasets: [{ label: 'Metan', data: mapData(rawData.ch4), borderColor: '#34C759', borderWidth: 2.5, fill: false }, { label: 'CO2', data: mapData(rawData.co2), borderColor: '#8E8E93', borderWidth: 2, borderDash: [5,5], fill: false }]}, options: JSON.parse(JSON.stringify(baseOptions)) }),
                vfa: new Chart(document.getElementById('chartVFA'), { type: 'line', data: { datasets: [{ label: 'Asetat', data: mapData(rawData.ac), borderColor: '#FF3B30', borderWidth: 2.5, fill: false }, { label: 'Propiyonat', data: mapData(rawData.pro), borderColor: '#FF9500', borderWidth: 2 }, { label: 'Bütirat', data: mapData(rawData.bu), borderColor: '#A2845E', borderWidth: 2 }]}, options: JSON.parse(JSON.stringify(baseOptions)) }),
                sub: new Chart(document.getElementById('chartSub'), { type: 'line', data: { datasets: [{ label: 'Şekerler', data: mapData(rawData.su), borderColor: '#007AFF', borderWidth: 2.5, fill: false }, { label: 'Amino Asitler', data: mapData(rawData.aa), borderColor: '#FF2D55', borderWidth: 2 }, { label: 'Yağ Asitleri', data: mapData(rawData.fa), borderColor: '#5AC8FA', borderWidth: 2 }]}, options: JSON.parse(JSON.stringify(baseOptions)) })
            };

            function resetAll() { syncMin = 0; syncMax = 280; Object.values(charts).forEach(c => { c.options.scales.x.min = 0; c.options.scales.x.max = 280; c.options.scales.x.ticks.stepSize = 35; c.update(); }); }
            function syncAllZooms() { Object.values(charts).forEach(c => { c.options.scales.x.min = syncMin; c.options.scales.x.max = syncMax; const r = syncMax-syncMin; c.options.scales.x.ticks.stepSize = (r > 80) ? 35 : undefined; c.update('none'); }); }

            function forceChartResize() {
                Object.values(charts).forEach(c => { c.resize(); c.update('none'); });
            }
            
            function expandCard(btn) {
                const card = btn.closest('.card'); 
                const rect = card.getBoundingClientRect();
                
                // Diğer grafikleri görünmez yap
                document.body.classList.add('is-expanded-mode');
                
                lockParentScroll();
                
                card.style.transition = 'none'; 
                card.style.position = 'fixed'; 
                card.style.top = rect.top + 'px'; 
                card.style.left = rect.left + 'px';
                card.style.width = rect.width + 'px'; 
                card.style.height = rect.height + 'px';
                card.style.zIndex = '1001';
                
                void card.offsetWidth;
                
                const targetWidth = window.innerWidth * 0.94;
                const targetHeight = Math.min(window.innerHeight * 0.65, 600);
                const targetLeft = (window.innerWidth - targetWidth) / 2;
                let targetTop = (window.innerHeight - targetHeight) / 2;
                
                try {
                    if (window.frameElement) {
                        const iframeRect = window.frameElement.getBoundingClientRect();
                        const parentCenterY = window.parent.innerHeight / 2;
                        let desiredTop = parentCenterY - iframeRect.top - (targetHeight / 2);
                        targetTop = Math.max(20, Math.min(desiredTop, window.innerHeight - targetHeight - 20));
                    }
                } catch(e) {}

                card.style.transition = 'all 0.5s var(--ios-curve), box-shadow 0.5s var(--ios-curve)';
                card.classList.add('expanded'); 
                document.getElementById('overlay').classList.add('active');
                
                card.style.width = targetWidth + 'px'; 
                card.style.height = targetHeight + 'px';
                card.style.left = targetLeft + 'px'; 
                card.style.top = targetTop + 'px';
                
                let startTime = Date.now();
                let animLoop = setInterval(() => {
                    Object.values(charts).forEach(c => c.resize());
                    if (Date.now() - startTime > 550) {
                        clearInterval(animLoop);
                        forceChartResize();
                    }
                }, 15);
            }
            
            function shrinkCard(btn) {
                const card = btn ? btn.closest('.card') : document.querySelector('.card.expanded'); 
                if(!card) return;
                
                const placeholder = card.parentElement;
                const rect = placeholder.getBoundingClientRect();
                
                document.getElementById('overlay').classList.remove('active'); 
                card.classList.remove('expanded');
                
                // Diğer grafikleri görünür yap
                document.body.classList.remove('is-expanded-mode');
                
                unlockParentScroll();
                
                card.style.width = rect.width + 'px'; 
                card.style.height = rect.height + 'px';
                card.style.left = rect.left + 'px'; 
                card.style.top = rect.top + 'px';
                
                let startTime = Date.now();
                let animLoop = setInterval(() => {
                    Object.values(charts).forEach(c => c.resize());
                    if (Date.now() - startTime > 550) {
                        clearInterval(animLoop);
                        card.style.transition = 'none';
                        card.style.position = 'absolute';
                        card.style.top = '0';
                        card.style.left = '0';
                        card.style.width = '100%';
                        card.style.height = '100%';
                        card.style.zIndex = '1';
                        forceChartResize();
                        setTimeout(() => {
                            card.style.transition = 'transform 0.3s var(--ios-curve), box-shadow 0.3s var(--ios-curve)';
                        }, 50);
                    }
                }, 15);
            }
        </script>
    </body>
    </html>
    """

    final_html = html_template.replace("{{DATA_JSON}}", json.dumps(data_payload))
    final_html = final_html.replace("{{MANURE_NAME}}", manure_name)

    return final_html