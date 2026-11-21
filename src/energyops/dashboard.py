"""Streamlit energy analytics dashboard. Use streamlit run src/energyops/dashboard.py."""
import io,os
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from pypdf import PdfReader
API=os.getenv("ENERGYOPS_API_URL","http://localhost:8000").rstrip("/")
def get(path,params=None):
    r=requests.get(API+path,params=params,timeout=20);r.raise_for_status();return r.json()
def post(path,payload):
    r=requests.post(API+path,json=payload,timeout=60);r.raise_for_status();return r.json()
st.set_page_config(page_title="EnergyOps AI",page_icon="⚡",layout="wide")
st.title("⚡ EnergyOps AI")
st.caption("Energy analytics + evidence retrieval | SYNTHETIC DEMONSTRATION DATA")
try:
    get("/health"); buildings=get("/buildings")
except (requests.RequestException,ValueError) as exc:
    st.error("API unavailable: "+str(exc));st.stop()
names={b["building_id"]:b["name"] for b in buildings}
if not names: st.warning("No buildings loaded");st.stop()
selected=st.sidebar.selectbox("Building",list(names),format_func=lambda x:names[x])
ratio=st.sidebar.slider("Anomaly ratio threshold",1.1,3.0,1.45,0.05)
st.sidebar.caption("Anomalies do not establish causality.")
try:
    readings=get("/readings/"+selected,{"limit":840})["readings"]
    events=get("/anomalies",{"building_id":selected,"threshold_ratio":ratio})
except (requests.RequestException,ValueError) as exc:
    st.error(str(exc));st.stop()
df=pd.DataFrame(readings)
a,b,c=st.columns(3)
a.metric("Stored energy",format(df["kwh"].sum(),",.0f")+" kWh" if not df.empty else "N/A")
b.metric("Hours",len(df));c.metric("High-consumption alerts",len(events))
if not df.empty:
    df["timestamp"]=pd.to_datetime(df["timestamp"])
    st.plotly_chart(px.line(df,x="timestamp",y="kwh",title="Hourly electricity usage — "+selected),use_container_width=True)
    temp_df=df.dropna(subset=["temperature_c"])
    if not temp_df.empty:
        st.plotly_chart(px.scatter(temp_df,x="temperature_c",y="kwh",title="Energy vs. outdoor temperature"),use_container_width=True)
left,right=st.columns(2)
with left:
    st.subheader("Detected anomalies")
    if events:
        st.dataframe(pd.DataFrame(events)[["timestamp","actual_kwh","baseline_kwh","deviation_pct","reference_hours"]],hide_index=True,use_container_width=True)
    else: st.info("No alerts meet the chosen criteria.")
with right:
    st.subheader("Ask EnergyOps AI")
    question=st.text_area("Question",value="Why did "+selected+" show unusual electricity consumption?")
    if st.button("Analyze",type="primary"):
        try:
            result=post("/ask",{"question":question})
            st.write(result["answer"])
            st.caption("Mode: "+result["mode"])
            if result["warning"]: st.warning(result["warning"])
            for src in result["sources"]:
                with st.expander(src["citation"]+" "+src["title"]):
                    st.caption("Source "+src["source"]+" | page "+str(src["page"]))
                    st.write(src["excerpt"])
        except requests.RequestException as exc: st.error(str(exc))
st.divider()
st.subheader("Index a reference document")
file=st.file_uploader("Text-searchable PDF",type=["pdf"])
text=st.text_area("Or paste technical documentation")
if st.button("Index document"):
    try:
        if file:
            reader=PdfReader(io.BytesIO(file.getvalue()))
            body="\n".join(page.extract_text() or "" for page in reader.pages)
            title=file.name;source="uploaded://"+file.name
        else:
            body=text;title="User-supplied document";source="user://pasted-text"
        if not body.strip(): st.warning("No extractable text; image-only PDFs require OCR.")
        else:
            result=post("/documents",{"title":title,"source":source,"text":body[:200000]})
            st.success("Indexed document "+str(result["document_id"]))
    except (requests.RequestException,ValueError) as exc: st.error(str(exc))
