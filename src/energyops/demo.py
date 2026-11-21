"""Explicitly synthetic energy readings and example operating procedures."""
from datetime import datetime,timedelta
from math import pi,sin
from .storage import add_document,connection,initialize
DOCS=[
("Demo HVAC Inspection SOP","demo://hvac-inspection","DEMONSTRATION DOCUMENT — not manufacturer advice. When HVAC electrical demand increases, verify operating schedules, occupancy, weather, setpoints and recent control overrides. Compare with similar-temperature periods and check available BMS logs for unexpected runtime. Trained personnel must follow approved safety procedures. An anomaly alone cannot establish equipment failure."),
("Demo Energy Anomaly Triage Guide","demo://anomaly-triage","DEMONSTRATION DOCUMENT. Validate meter quality and missing measurements before escalating an energy alert. Compare readings against prior weeks at the same weekday and hour; check holidays, temperature, occupancy, sensor faults and operating schedules. Without evidence, do not invent a root cause."),
("Demo Energy Reporting Policy","demo://energy-reporting","DEMONSTRATION DOCUMENT. Energy readings are hourly kilowatt-hours, kWh, not instantaneous kilowatts. Sum hourly kWh to report period consumption. Report measured energy, reference baseline, percentage deviation, reference sample count and timestamp. Missing readings must not be treated as zero.")
]
def seed_demo(path=None,days=35,buildings=6):
    initialize(path)
    with connection(path) as con:
        count=con.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
        if count: return {"seeded":False,"reason":"database already contains buildings","buildings":count}
        start=datetime(2026,1,1)
        for b in range(1,buildings+1):
            bid="B"+str(b).zfill(3)
            con.execute("INSERT INTO buildings VALUES (?,?,?,1)",(bid,"Demo Building "+str(b),"DEMO_SITE"))
            batch=[]
            for h in range(days*24):
                ts=start+timedelta(hours=h)
                daily=sin(2*pi*(ts.hour-7)/24)
                temp=11+8*sin(2*pi*h/(24*14))+3*daily
                weekday=1 if ts.weekday()<5 else 0.7
                base=(24+b*7)*(1+0.30*max(0,daily))*weekday
                kwh=max(0.1,base+0.6*max(0,15-temp)+1.4*sin(h/7+b))
                if b==1 and ts.day in (22,29) and ts.hour in (13,14): kwh*=2.2
                if b==3 and ts.day==26 and ts.hour in (9,10,11): kwh*=1.9
                batch.append((bid,ts.isoformat(timespec="seconds"),round(kwh,4),round(temp,3)))
            con.executemany("INSERT INTO readings VALUES (?,?,?,?)",batch)
    for title,source,content in DOCS: add_document(title,source,[(1,content)],path)
    return {"seeded":True,"buildings":buildings,"hours_per_building":days*24,"dataset":"synthetic_demo"}
if __name__=="__main__": print(seed_demo())
