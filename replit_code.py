# ═══════════════════════════════════════════════════════
#  SolarGuard — منصة التنبؤ بإنتاج الطاقة الشمسية
#  تشغيل: streamlit run app.py
#  مكتبات: pip install streamlit pandas numpy plotly requests
# ═══════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests

# ── إعداد الصفحة ────────────────────────────────────────
st.set_page_config(
    page_title="SolarGuard | منصة التنبؤ الشمسي",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS مخصص ────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
  .metric-card {
    background: linear-gradient(135deg, #1e3a5f, #2563eb);
    border-radius: 16px; padding: 20px; color: white;
    text-align: center; margin: 6px 0;
  }
  .alert-red   { background: #fee2e2; border-right: 5px solid #dc2626;
                 border-radius: 10px; padding: 14px; margin: 8px 0; }
  .alert-yellow{ background: #fef9c3; border-right: 5px solid #ca8a04;
                 border-radius: 10px; padding: 14px; margin: 8px 0; }
  .alert-green { background: #dcfce7; border-right: 5px solid #16a34a;
                 border-radius: 10px; padding: 14px; margin: 8px 0; }
  .section-title { font-size: 1.3rem; font-weight: 700;
                   color: #1e3a5f; margin: 20px 0 10px; }
</style>
""", unsafe_allow_html=True)

# ── بيانات وهمية واقعية ──────────────────────────────────
STATIONS = {
    "محطة الرياض الشمالية": {"lat": 24.95, "lon": 46.72, "capacity_mw": 50},
    "محطة نيوم الشمسية":    {"lat": 28.00, "lon": 35.50, "capacity_mw": 120},
    "محطة جدة الساحلية":    {"lat": 21.49, "lon": 39.18, "capacity_mw": 80},
    "محطة القصيم":           {"lat": 26.33, "lon": 43.97, "capacity_mw": 60},
}

def fetch_weather(lat, lon):
    """جلب بيانات الطقس من Open-Meteo (مجاني، لا يحتاج API key)"""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,cloudcover,windspeed_10m,direct_radiation"
            f"&forecast_days=3&timezone=Asia%2FRiyadh"
        )
        r = requests.get(url, timeout=8)
        d = r.json()["hourly"]
        df = pd.DataFrame({
            "time":        pd.to_datetime(d["time"]),
            "temp":        d["temperature_2m"],
            "cloud":       d["cloudcover"],
            "wind":        d["windspeed_10m"],
            "radiation":   d["direct_radiation"],
        })
        return df
    except Exception:
        # بيانات احتياطية عند فشل الاتصال
        hours = pd.date_range(datetime.now(), periods=72, freq="h")
        return pd.DataFrame({
            "time":      hours,
            "temp":      np.random.normal(38, 5, 72).clip(25, 50),
            "cloud":     np.random.uniform(0, 60, 72),
            "wind":      np.random.uniform(5, 45, 72),
            "radiation": np.random.uniform(100, 900, 72),
        })

def predict_output(df, capacity_mw):
    """
    نموذج تنبؤ مبسط:
      production = radiation × temp_factor × cloud_factor × dust_factor
    """
    temp_factor  = 1 - np.clip((df["temp"] - 25) * 0.004, 0, 0.3)
    cloud_factor = 1 - df["cloud"] / 100 * 0.85
    dust_factor  = np.where(df["wind"] > 30, 0.65,
                   np.where(df["wind"] > 20, 0.80, 0.95))

    raw = df["radiation"] / 1000 * capacity_mw
    predicted = raw * temp_factor * cloud_factor * dust_factor
    ideal      = df["radiation"] / 1000 * capacity_mw
    pr = np.where(ideal > 0, predicted / ideal, 0)

    df = df.copy()
    df["predicted_mw"]  = predicted.clip(0)
    df["ideal_mw"]      = ideal.clip(0)
    df["perf_ratio"]    = pr.clip(0, 1)
    df["temp_loss"]     = (1 - temp_factor)  * 100
    df["cloud_loss"]    = (1 - cloud_factor) * 100
    df["dust_loss"]     = (1 - dust_factor)  * 100
    df["alert_level"]   = np.where(
        (df["wind"] > 30) | (df["cloud"] > 70), "🔴 خطر",
        np.where((df["wind"] > 20) | (df["cloud"] > 40), "🟡 تحذير", "🟢 طبيعي")
    )
    return df

# ════════════════════════════════════════════════════════
#  الواجهة الرئيسية
# ════════════════════════════════════════════════════════

# ── الشريط الجانبي ───────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/KACARE_Logo.png/320px-KACARE_Logo.png",
             width=140)
    st.markdown("## ☀️ SolarGuard")
    st.caption("منصة التنبؤ بإنتاج الطاقة الشمسية")
    st.divider()
    station_name = st.selectbox("📍 اختر المحطة", list(STATIONS.keys()))
    st.divider()
    st.markdown("**📌 إحداثيات المحطة**")
    info = STATIONS[station_name]
    st.caption(f"خط العرض: {info['lat']}  |  خط الطول: {info['lon']}")
    st.caption(f"الطاقة المركبة: {info['capacity_mw']} ميجاواط")

station   = STATIONS[station_name]
df_raw    = fetch_weather(station["lat"], station["lon"])
df        = predict_output(df_raw, station["capacity_mw"])
now_row   = df.iloc[0]

# ── العنوان ──────────────────────────────────────────────
st.markdown(f"# ☀️ SolarGuard — {station_name}")
st.caption(f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d  %H:%M')}")
st.divider()

# ════════════════════════════════════════════════════════
#  القسم 1 — التنبيهات
# ════════════════════════════════════════════════════════
st.markdown('<div class="section-title">🚨 التنبيهات الاستباقية — 72 ساعة القادمة</div>',
            unsafe_allow_html=True)

alerts = df[df["alert_level"] != "🟢 طبيعي"].head(5)

if alerts.empty:
    st.markdown('<div class="alert-green">✅ لا توجد تنبيهات — الإنتاج متوقع طبيعي خلال الـ 72 ساعة القادمة.</div>',
                unsafe_allow_html=True)
else:
    for _, row in alerts.iterrows():
        level = row["alert_level"]
        css   = "alert-red" if "خطر" in level else "alert-yellow"
        drop  = round((1 - row["perf_ratio"]) * 100)
        cause = []
        if row["dust_loss"] > 15: cause.append(f"عاصفة رملية ({row['wind']:.0f} كم/س)")
        if row["cloud_loss"] > 20: cause.append(f"غيوم ({row['cloud']:.0f}%)")
        if row["temp_loss"]  > 10: cause.append(f"حرارة ({row['temp']:.0f}°C)")
        cause_str = " + ".join(cause) if cause else "عوامل مناخية"
        st.markdown(
            f'<div class="{css}">'
            f'<b>{level} | {row["time"].strftime("%a %d/%m %H:00")}</b><br>'
            f'📉 انخفاض متوقع في الإنتاج: <b>{drop}%</b><br>'
            f'📌 السبب: {cause_str}<br>'
            f'💡 التوصية: تشغيل الاحتياطي وتأجيل الأحمال الثقيلة'
            f'</div>',
            unsafe_allow_html=True
        )

st.divider()

# ════════════════════════════════════════════════════════
#  القسم 2 — مؤشرات الأداء
# ════════════════════════════════════════════════════════
st.markdown('<div class="section-title">📊 مؤشرات الأداء الحالية</div>',
            unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    pr_pct = round(now_row["perf_ratio"] * 100, 1)
    color  = "#16a34a" if pr_pct > 75 else ("#ca8a04" if pr_pct > 55 else "#dc2626")
    st.markdown(f'<div class="metric-card"><div style="font-size:2rem;font-weight:700;color:{color}">{pr_pct}%</div><div>معدل الأداء PR</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div style="font-size:2rem;font-weight:700">{now_row["predicted_mw"]:.1f} MW</div><div>الإنتاج المتوقع الآن</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div style="font-size:2rem;font-weight:700">{now_row["temp"]:.0f}°C</div><div>درجة الحرارة</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div style="font-size:2rem;font-weight:700">{now_row["wind"]:.0f} كم/س</div><div>سرعة الرياح</div></div>', unsafe_allow_html=True)

st.divider()

# ════════════════════════════════════════════════════════
#  القسم 3 — الرسوم البيانية
# ════════════════════════════════════════════════════════
st.markdown('<div class="section-title">📈 توقع الإنتاج — 72 ساعة</div>',
            unsafe_allow_html=True)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=df["time"], y=df["ideal_mw"],
    name="الإنتاج المثالي", line=dict(color="#93c5fd", dash="dash"), fill="tozeroy", fillcolor="rgba(147,197,253,0.15)"
))
fig1.add_trace(go.Scatter(
    x=df["time"], y=df["predicted_mw"],
    name="الإنتاج المتوقع", line=dict(color="#2563eb", width=3), fill="tozeroy", fillcolor="rgba(37,99,235,0.15)"
))
# تظليل ساعات الخطر
for _, row in df[df["alert_level"] == "🔴 خطر"].iterrows():
    fig1.add_vrect(x0=row["time"], x1=row["time"] + timedelta(hours=1),
                   fillcolor="rgba(220,38,38,0.15)", line_width=0)

fig1.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=1.1),
    yaxis_title="ميجاواط", xaxis_title="",
    height=350, margin=dict(t=20, b=20)
)
st.plotly_chart(fig1, use_container_width=True)

# ── تحليل خسائر الأداء ──────────────────────────────────
st.markdown('<div class="section-title">🔍 تحليل العوامل المؤثرة على الأداء</div>',
            unsafe_allow_html=True)

daily = df.resample("D", on="time").mean(numeric_only=True).reset_index()
fig2 = go.Figure()
fig2.add_bar(x=daily["time"].dt.strftime("%A"), y=daily["dust_loss"].round(1),
             name="🌪️ غبار/رياح", marker_color="#f97316")
fig2.add_bar(x=daily["time"].dt.strftime("%A"), y=daily["cloud_loss"].round(1),
             name="☁️ غيوم", marker_color="#94a3b8")
fig2.add_bar(x=daily["time"].dt.strftime("%A"), y=daily["temp_loss"].round(1),
             name="🌡️ حرارة", marker_color="#ef4444")
fig2.update_layout(
    barmode="stack", height=300,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    yaxis_title="% خسارة في الأداء",
    legend=dict(orientation="h", y=1.1),
    margin=dict(t=20, b=10)
)
st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════
#  القسم 4 — توصية الصيانة
# ════════════════════════════════════════════════════════
st.markdown('<div class="section-title">🔧 توصية جدول الصيانة</div>',
            unsafe_allow_html=True)

avg_dust = df["dust_loss"].mean()
best_day = daily.loc[daily["dust_loss"].idxmin(), "time"].strftime("%A %d/%m")

col1, col2 = st.columns(2)
with col1:
    urgency = "عاجل خلال 48 ساعة ⚠️" if avg_dust > 20 else "مخطط — الأسبوع القادم ✅"
    st.info(f"**أولوية تنظيف الألواح:** {urgency}")
    st.info(f"**أفضل يوم للصيانة:** {best_day} (أقل رياح متوقعة)")
with col2:
    daily_loss_mwh = (df["ideal_mw"] - df["predicted_mw"]).clip(0).sum()
    sar_loss = round(daily_loss_mwh * 0.25)  # تقدير 0.25 ريال/kWh
    st.error(f"**الخسارة التقديرية (72 ساعة):** {daily_loss_mwh:.0f} MWh")
    st.error(f"**الأثر الاقتصادي:** ~{sar_loss:,} ريال")

st.divider()
st.caption("SolarGuard © 2025 | بيانات الطقس: Open-Meteo | مبني لدعم أهداف رؤية 2030 🇸🇦")
