"""EnergyOps visual analytics console. Launch with streamlit run src/energyops/dashboard.py."""
from __future__ import annotations

import io
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from pypdf import PdfReader

API = os.getenv("ENERGYOPS_API_URL", "http://localhost:8000").rstrip("/")
TEAL = "#22D3A7"
CYAN = "#55BFFA"
ORANGE = "#FFAE69"
RED = "#FC7080"
BLUE = "#86A8FF"


def get(path: str, params: dict | None = None):
    response = requests.get(f"{API}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def post(path: str, payload: dict):
    response = requests.post(f"{API}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def style_chart(fig: go.Figure, *, height: int = 340):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#C9D9EC", size=12),
        title=dict(font=dict(size=15, color="#F5FAFF")),
        margin=dict(l=10, r=12, t=48, b=14),
        height=height,
        legend=dict(orientation="h", y=1.13, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(190,209,228,0.12)", zeroline=False)
    return fig


st.set_page_config(page_title="EnergyOps AI | Operations Console", page_icon="⚡", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; max-width: 1600px;}
[data-testid="stMetric"] {background: #14283A; border: 1px solid #263E51; border-radius: 14px; padding: 16px 18px;}
[data-testid="stMetricLabel"] {color: #9AB4C9;}
[data-testid="stMetricValue"] {color: #F3FAFF;}
[data-testid="stSidebar"] {border-right: 1px solid #24394C;}
</style>
""", unsafe_allow_html=True)

header_left, header_right = st.columns([5, 2], vertical_alignment="center")
with header_left:
    st.title("⚡ EnergyOps AI")
    st.caption("ENERGY INTELLIGENCE  /  MONITORING  /  GROUNDED DOCUMENT ASSISTANT")
with header_right:
    st.info("DEMO DATA · Synthetic energy readings and sample procedures", icon="ℹ️")

try:
    status = get("/health")
    buildings = get("/buildings")
    overall = get("/summary")
except (requests.RequestException, ValueError) as exc:
    st.error(f"Cannot connect to EnergyOps API: {exc}")
    st.code("uvicorn energyops.api:app --reload")
    st.stop()

names = {b["building_id"]: b["name"] for b in buildings}
if not names:
    st.warning("No buildings found. Import a dataset or enable demo seeding.")
    st.stop()

with st.sidebar:
    st.subheader("⚙️ Workspace filters")
    selected = st.selectbox("Building", list(names), format_func=lambda bid: f"{bid} · {names[bid]}")
    window = st.select_slider("Period within loaded dataset", options=["7 days", "14 days", "30 days", "All"], value="30 days")
    ratio = st.slider("High-use anomaly threshold", min_value=1.1, max_value=3.0, value=1.45, step=0.05)
    st.divider()
    st.caption("The selected window ends at the newest available reading, not today.")
    st.caption("Anomaly flags are statistical deviations, not evidence of equipment failure.")
    st.caption(f"API status: {status.get('status', 'unknown')}")

try:
    values = get(f"/readings/{selected}", {"limit": 5000})["readings"]
    all_events = get("/anomalies", {"building_id": selected, "threshold_ratio": ratio, "limit": 500})
    documents = get("/documents")
except (requests.RequestException, ValueError) as exc:
    st.error(f"Data request failed: {exc}")
    st.stop()

all_df = pd.DataFrame(values)
if all_df.empty:
    st.warning("This building has no readings. Select another building.")
    st.stop()
all_df["timestamp"] = pd.to_datetime(all_df["timestamp"])
all_df = all_df.sort_values("timestamp")
cutoff = None if window == "All" else all_df["timestamp"].max() - pd.Timedelta(days=int(window.split()[0]))
df = all_df if cutoff is None else all_df.loc[all_df["timestamp"] >= cutoff].copy()
events = [event for event in all_events if cutoff is None or pd.Timestamp(event["timestamp"]) >= cutoff]

# KPIs use filtered rows and never claim to represent current/live consumption.
energy_total = float(df["kwh"].sum())
peak = float(df["kwh"].max())
avg = float(df["kwh"].mean())
first = df["timestamp"].min().strftime("%d %b %Y")
last = df["timestamp"].max().strftime("%d %b %Y")
st.caption(f"Showing {selected} · {first} – {last} · hourly measurements · site-local dataset timestamps")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Energy used", f"{energy_total:,.0f} kWh")
m2.metric("Avg. hourly energy", f"{avg:,.1f} kWh")
m3.metric("Peak hourly energy", f"{peak:,.1f} kWh")
m4.metric("Measured hours", f"{len(df):,}")
m5.metric("High-use alerts", len(events))

overview_tab, patterns_tab, alerts_tab, ai_tab = st.tabs(
    ["📈 Overview", "🗓️ Usage patterns", "🚨 Anomalies & weather", "🤖 AI & documents"]
)

with overview_tab:
    daily = df.assign(date=df["timestamp"].dt.date).groupby("date", as_index=False)["kwh"].sum()
    left, right = st.columns([1.75, 1.0])
    with left:
        line = go.Figure()
        line.add_trace(go.Scatter(
            x=df["timestamp"], y=df["kwh"], name="Hourly electricity",
            mode="lines", line=dict(color=TEAL, width=2),
            fill="tozeroy", fillcolor="rgba(34,211,167,0.07)",
        ))
        if events:
            alert_df = pd.DataFrame(events)
            line.add_trace(go.Scatter(
                x=pd.to_datetime(alert_df["timestamp"]), y=alert_df["actual_kwh"],
                name="High-use alert", mode="markers",
                marker=dict(color=RED, size=9, line=dict(color="#0D1D2C", width=1.5)),
            ))
        style_chart(line, height=365)
        line.update_layout(title="Electricity load · highlighted high-use events", yaxis_title="Hourly energy (kWh)")
        st.plotly_chart(line, use_container_width=True)
    with right:
        bars = px.bar(daily, x="date", y="kwh", title="Daily electricity consumption")
        bars.update_traces(marker_color=CYAN, marker_line_width=0)
        style_chart(bars, height=365)
        bars.update_layout(yaxis_title="Daily energy (kWh)", xaxis_title="")
        st.plotly_chart(bars, use_container_width=True)

    st.subheader("Portfolio comparison")
    st.caption("Totals span all stored hours per building, so buildings with different data coverage are not directly comparable.")
    comparison = pd.DataFrame(overall.get("buildings", []))
    if not comparison.empty:
        comparison = comparison.sort_values("total_kwh", ascending=True)
        fig = px.bar(
            comparison, x="total_kwh", y="building_id", orientation="h",
            color="total_kwh", color_continuous_scale=["#18475B", CYAN, TEAL],
            hover_data=["hours", "avg_temperature_c"],
            title="Building energy totals · complete stored dataset",
        )
        style_chart(fig, height=315)
        fig.update_layout(xaxis_title="Recorded consumption (kWh)", yaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

with patterns_tab:
    left, right = st.columns(2)
    with left:
        by_hour = df.assign(hour=df["timestamp"].dt.hour).groupby("hour", as_index=False)["kwh"].mean()
        hourly = px.line(by_hour, x="hour", y="kwh", markers=True, title="Average hourly usage pattern")
        hourly.update_traces(line_color=TEAL, marker_color=CYAN, line_width=3)
        style_chart(hourly)
        hourly.update_layout(xaxis_title="Hour (site-local)", yaxis_title="Mean hourly energy (kWh)")
        st.plotly_chart(hourly, use_container_width=True)
    with right:
        by_day = df.assign(weekday=df["timestamp"].dt.day_name()).groupby("weekday", as_index=False)["kwh"].mean()
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday = px.bar(by_day, x="weekday", y="kwh", category_orders={"weekday": order}, title="Average usage by weekday")
        weekday.update_traces(marker_color=BLUE)
        style_chart(weekday)
        weekday.update_layout(xaxis_title="", yaxis_title="Mean hourly energy (kWh)")
        st.plotly_chart(weekday, use_container_width=True)
    st.subheader("Energy intensity heatmap")
    heat = df.assign(date=df["timestamp"].dt.strftime("%d %b"), hour=df["timestamp"].dt.hour)
    heat = heat.pivot_table(index="date", columns="hour", values="kwh", aggfunc="mean", sort=False)
    heatmap = go.Figure(data=go.Heatmap(
        z=heat.values, x=list(heat.columns), y=list(heat.index),
        colorscale=[[0, "#172E48"], [0.45, "#267C9E"], [1, TEAL]],
        colorbar=dict(title="kWh"), hovertemplate="Date %{y}<br>Hour %{x}:00<br>%{z:.1f} kWh<extra></extra>",
    ))
    style_chart(heatmap, height=420)
    heatmap.update_layout(title="Daily × hourly electricity intensity", xaxis_title="Hour (site-local)", yaxis_title="Dataset date")
    st.plotly_chart(heatmap, use_container_width=True)

with alerts_tab:
    left, right = st.columns([1.1, 1.0])
    with left:
        if events:
            alert_df = pd.DataFrame(events).sort_values("timestamp")
            compare = go.Figure()
            compare.add_trace(go.Bar(x=alert_df["timestamp"], y=alert_df["baseline_kwh"], name="Reference median", marker_color=CYAN))
            compare.add_trace(go.Bar(x=alert_df["timestamp"], y=alert_df["actual_kwh"], name="Measured", marker_color=RED))
            style_chart(compare, height=360)
            compare.update_layout(title="Anomalous hours · actual vs. reference", barmode="group", yaxis_title="Energy (kWh)")
            st.plotly_chart(compare, use_container_width=True)
        else:
            st.info("No high-consumption anomalies detected at this threshold and period.")
    with right:
        if df["temperature_c"].notna().any():
            scatter = px.scatter(
                df.dropna(subset=["temperature_c"]), x="temperature_c", y="kwh",
                title="Outside temperature vs. electricity",
                opacity=0.65, color_discrete_sequence=[ORANGE],
            )
            style_chart(scatter, height=360)
            scatter.update_layout(xaxis_title="Outdoor temperature (°C)", yaxis_title="Hourly energy (kWh)")
            st.plotly_chart(scatter, use_container_width=True)
        else:
            st.info("No matching weather measurements available.")
    st.subheader("High-use events")
    st.caption("Reference = median of available same-weekday/same-hour observations from up to four prior weeks. Deviation does not establish root cause.")
    if events:
        columns = ["building_id", "timestamp", "actual_kwh", "baseline_kwh", "deviation_pct", "reference_hours"]
        st.dataframe(pd.DataFrame(events)[columns], hide_index=True, use_container_width=True)
        st.download_button("Download flagged hours (CSV)", pd.DataFrame(events)[columns].to_csv(index=False), file_name=f"{selected}_energy_anomalies.csv", mime="text/csv")
    else:
        st.write("No events meet the criteria.")

with ai_tab:
    left, right = st.columns([1.3, 1.0])
    with left:
        st.subheader("Ask EnergyOps AI")
        st.caption("SQL/Python calculates metrics; retrieved documents provide context. Local LLM synthesis is optional.")
        suggestion = st.selectbox("Example questions", [
            f"Why is {selected} showing unusually high energy consumption?",
            "Which building has the highest recorded energy usage?",
            "What checks are recommended when HVAC demand increases?",
        ])
        question = st.text_area("Your question", value=suggestion, height=95)
        if st.button("Analyze energy data", type="primary"):
            try:
                result = post("/ask", {"question": question})
                st.markdown(result["answer"])
                st.caption(f"Mode: {result['mode']}")
                if result.get("warning"):
                    st.warning(result["warning"])
                for src in result.get("sources", []):
                    with st.expander(f"{src['citation']} {src['title']} · retrieval score {src['score']}"):
                        st.caption(f"Source: {src['source']} · Page: {src['page']}")
                        st.write(src["excerpt"])
            except requests.RequestException as exc:
                st.error(f"AI API request failed: {exc}")
    with right:
        st.subheader("Reference library")
        st.metric("Indexed documents", len(documents))
        if documents:
            st.dataframe(pd.DataFrame(documents)[["title", "chunks", "source"]], hide_index=True, use_container_width=True)
        file = st.file_uploader("Text-searchable PDF", type=["pdf"])
        pasted = st.text_area("Or paste a technical procedure", height=110)
        if st.button("Index document"):
            try:
                if file is not None:
                    if len(file.getvalue()) > 20_000_000:
                        st.error("Maximum PDF size is 20 MB.")
                        st.stop()
                    reader = PdfReader(io.BytesIO(file.getvalue()))
                    content = "\n".join(page.extract_text() or "" for page in reader.pages)
                    title, source = file.name, f"uploaded://{file.name}"
                else:
                    content = pasted
                    title, source = "User-supplied procedure", "user://pasted-text"
                if not content.strip():
                    st.warning("No searchable text found; scanned PDFs require OCR.")
                else:
                    doc = post("/documents", {"title": title, "source": source, "text": content[:200_000]})
                    st.success(f"Document {doc['document_id']} indexed")
            except (ValueError, requests.RequestException) as exc:
                st.error(f"Document ingestion failed: {exc}")

st.caption("EnergyOps AI · Demo charts use synthetic historical readings · Do not use for safety-critical operational decisions.")
