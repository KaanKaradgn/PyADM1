"""
crash_generator.py -- Çökme senaryolu besleme profili üreteci
==============================================================
run_codigestion motoru için zaman-serisi girdileri (flow_series, temp_series)
ve satır-bazlı REJİM etiketi üretir. "Görünür kollar" yaklaşımı:
  - Akut çöküş  : DEBİ şoku (flow spike) -> organik aşırı yükleme -> asitleşme
  - Kronik stres: KOMPOZİSYON (protein-ağırlıklı -> amonyak; karbonhidrat-ağırlıklı
                  yüksek yük -> asit). Bu, karışım/besin seçimiyle (run matrisi) gelir.

Motor değişikliği YOK. Debi zaten dinamik; kompozisyon run-seviyesi.
"""
import numpy as np

DEFAULT_HRT = 42.55        # Konya tesisi bekletme süresi (gün)
V_LIQ = 3400.0


def _operational_variability(times, rng, daily=0.10, weekly=0.05, noise=0.03):
    """Gerçek beslemedeki günlük/haftalık dalgalanma + küçük gürültü (çarpan)."""
    daily_c  = 1.0 + daily  * np.sin(2*np.pi*times/1.0)      # günlük ritim
    weekly_c = 1.0 + weekly * np.sin(2*np.pi*times/7.0)      # haftalık ritim
    noise_c  = 1.0 + rng.normal(0, noise, size=len(times))   # ölçüm/besleme gürültüsü
    return np.clip(daily_c * weekly_c * noise_c, 0.5, 2.0)


def seasonal_temp(times, mean=35.0, amp=5.0, period=180.0):
    return mean + amp*np.sin(2*np.pi*times/period)


def build_profiles(sim_days, dt, total_cod_mix, hrt=DEFAULT_HRT,
                   temp_mode="const", temp_const=37.0,
                   crashes=None, seed=0, variability=True):
    """
    total_cod_mix : karışımın efektif COD'si (kgCOD/m^3) = Σ flow_share_i * total_cod_i
                    -> taban debiyi ve OLR'yi anlamlandırmak için (şu an sadece HRT'den
                       debi belirliyoruz; COD bilgisi etiket/analiz için tutuluyor).
    crashes       : liste. Her biri:
        {"type":"overload", "start_day":40, "duration":4, "magnitude":2.5}
        (overload = flow spike; magnitude = taban debinin katı)
    Döner: dict(times, flow, temp, regime)  -- regime: str dizisi (her satır)
    """
    rng = np.random.default_rng(seed)
    n = int(round(sim_days/dt)) + 1
    times = np.round(np.arange(n)*dt, 6)

    base_flow = V_LIQ / hrt
    flow = np.full(n, base_flow, dtype=float)
    if variability:
        flow *= _operational_variability(times, rng)

    regime = np.array(["healthy"]*n, dtype=object)

    # --- Çökme olaylarını enjekte et ---
    for ev in (crashes or []):
        t0, dur = ev["start_day"], ev["duration"]
        mask = (times >= t0) & (times < t0 + dur)
        if ev["type"] == "overload":
            flow[mask] *= ev.get("magnitude", 2.5)
            regime[mask] = "overload"
            # toparlanma penceresi (olay sonrası birkaç gün) da etiketlensin
            rec = (times >= t0+dur) & (times < t0+dur+ev.get("recovery", 6))
            regime[rec] = "recovery"

    # --- Sıcaklık ---
    if temp_mode == "seasonal":
        temp = seasonal_temp(times)
    else:
        temp = np.full(n, temp_const)

    return dict(times=times, flow=flow, temp=temp, regime=regime,
                base_flow=base_flow, total_cod_mix=total_cod_mix)


def label_health_from_state(df_out, ph_acid=6.6, nh3_inhib=0.010):
    """
    Reaktör DURUMUNDAN sağlık etiketi türet (rejim etiketini tamamlar):
      - 'acidified'      : pH < ph_acid
      - 'ammonia_stress' : serbest NH3 (S_nh3) > nh3_inhib  (kmole N/m^3)
      - 'healthy'        : diğer
    Not: ADM1 K_I_nh3 = 0.0018 M civarı; S_nh3 bunu aşınca metanojen inhibisyonu.
    """
    ph = df_out["pH"].values
    nh3 = df_out["S_nh3"].values if "S_nh3" in df_out.columns else np.zeros_like(ph)
    lab = np.array(["healthy"]*len(ph), dtype=object)
    lab[nh3 > nh3_inhib] = "ammonia_stress"
    lab[ph < ph_acid] = "acidified"     # asit önce gelir (daha kritik)
    return lab
