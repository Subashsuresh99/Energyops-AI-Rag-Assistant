import pytest
from datetime import datetime,timedelta
from energyops.analytics import consumption_summary,detect_anomalies
from energyops.storage import initialize,connection

def test_totals(demo_db):
    summary=consumption_summary("B001",demo_db)
    assert summary["buildings"][0]["hours"]==840
    assert summary["buildings"][0]["total_kwh"]>0
    assert summary["units"]=="kWh"

def test_anomalies(demo_db):
    events=detect_anomalies("B001",threshold_ratio=1.45,path=demo_db)
    assert events
    assert any(e["timestamp"].startswith("2026-01-22T13") for e in events)
    assert all(e["reference_hours"]>=2 for e in events)

def test_invalid_threshold(demo_db):
    for ratio in (0.5,1.0,float("inf"),float("nan")):
        with pytest.raises(ValueError):
            detect_anomalies(threshold_ratio=ratio,path=demo_db)

def test_no_future_leakage(tmp_path):
    db=tmp_path/"test.sqlite3";initialize(db)
    with connection(db) as con:
        con.execute("INSERT INTO buildings VALUES ('B111','Test','SITE',0)")
        start=datetime(2026,1,1,12)
        rows=[("B111",(start+timedelta(days=7*i)).isoformat(timespec="seconds"),v,None) for i,v in enumerate([10,10,40,10])]
        con.executemany("INSERT INTO readings VALUES (?,?,?,?)",rows)
    result=detect_anomalies("B111",path=db)
    assert len(result)==1 and result[0]["actual_kwh"]==40 and result[0]["baseline_kwh"]==10
