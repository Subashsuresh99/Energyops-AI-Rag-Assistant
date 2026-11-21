"""Numerical analysis is deterministic and never delegated to an LLM."""
import statistics
from datetime import datetime, timedelta
from math import isfinite
from .storage import connection

def consumption_summary(building_id=None, path=None):
    with connection(path) as con:
        if building_id:
            rows = con.execute("SELECT building_id,COUNT(*) AS hours,ROUND(SUM(kwh),2) AS total_kwh,ROUND(AVG(temperature_c),2) AS avg_temperature_c,MIN(timestamp) AS first_timestamp,MAX(timestamp) AS last_timestamp FROM readings WHERE building_id=? GROUP BY building_id", (building_id,)).fetchall()
        else:
            rows = con.execute("SELECT building_id,COUNT(*) AS hours,ROUND(SUM(kwh),2) AS total_kwh,ROUND(AVG(temperature_c),2) AS avg_temperature_c,MIN(timestamp) AS first_timestamp,MAX(timestamp) AS last_timestamp FROM readings GROUP BY building_id ORDER BY total_kwh DESC").fetchall()
    return {"units":"kWh", "scope":"all stored hours, not a calendar period", "buildings":[dict(r) for r in rows], "data_source":"database"}

def detect_anomalies(building_id=None, threshold_ratio=1.45, min_reference_hours=2, limit=50, path=None):
    """Same-hour/weekday median over the preceding 1–4 weeks, without leakage."""
    if not isfinite(threshold_ratio) or threshold_ratio <= 1:
        raise ValueError("threshold_ratio must be finite and > 1")
    if not 2 <= min_reference_hours <= 4 or not 1 <= limit <= 500:
        raise ValueError("invalid reference count or result limit")
    with connection(path) as con:
        if building_id:
            rows=con.execute("SELECT building_id,timestamp,kwh,temperature_c FROM readings WHERE building_id=? ORDER BY building_id,timestamp",(building_id,)).fetchall()
        else:
            rows=con.execute("SELECT building_id,timestamp,kwh,temperature_c FROM readings ORDER BY building_id,timestamp").fetchall()
    series={}
    for r in rows:
        series.setdefault(r["building_id"],{})[r["timestamp"]]=dict(r)
    events=[]
    for b_id,data in series.items():
        for stamp,row in data.items():
            current=datetime.fromisoformat(stamp)
            prior=[data.get((current-timedelta(days=7*week)).isoformat(timespec="seconds")) for week in range(1,5)]
            values=[r["kwh"] for r in prior if r is not None]
            if len(values)<min_reference_hours: continue
            baseline=statistics.median(values)
            if baseline<=0 or row["kwh"]<baseline*threshold_ratio: continue
            events.append({"building_id":b_id,"timestamp":stamp,"actual_kwh":round(row["kwh"],2),"baseline_kwh":round(baseline,2),"deviation_pct":round((row["kwh"]/baseline-1)*100,2),"temperature_c":row["temperature_c"],"reference_hours":len(values),"method":"prior 1-4 weeks, same weekday/hour, median","caveat":"Deviation does not prove root cause."})
    return sorted(events,key=lambda x:(x["deviation_pct"],x["timestamp"]),reverse=True)[:limit]
