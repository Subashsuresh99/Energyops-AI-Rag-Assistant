"""Import wide-format BDG2 electricity readings and optional weather for a controlled subset."""
import argparse,csv,math
from pathlib import Path
from energyops.storage import connection,initialize

def _valid_float(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError): return None

def import_bdg2(electricity:Path,metadata:Path,weather:Path|None=None,max_buildings=8,max_hours=1200,replace_demo=False,path=None):
    if max_buildings<1 or max_hours<1: raise ValueError("limits must be positive")
    initialize(path)
    with connection(path) as con:
        existing=con.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
        if existing and not replace_demo: raise ValueError("Use a new database or --replace-demo")
        if existing:
            if con.execute("SELECT COUNT(*) FROM buildings WHERE is_demo=0").fetchone()[0]:
                raise ValueError("Refusing to overwrite non-demo readings")
            for table in ("readings","buildings","chunks","documents"): con.execute("DELETE FROM "+table)
        with metadata.open(newline="",encoding="utf-8-sig") as fh:
            meta={r["building_id"]:r for r in csv.DictReader(fh)}
        with electricity.open(newline="",encoding="utf-8-sig") as fh:
            reader=csv.DictReader(fh)
            if not reader.fieldnames or "timestamp" not in reader.fieldnames: raise ValueError("Expected wide timestamp CSV")
            selected=[c for c in reader.fieldnames if c!="timestamp" and c in meta][:max_buildings]
            if not selected: raise ValueError("No electricity columns match building metadata")
            sites={meta[bid]["site_id"] for bid in selected}
            temps={}
            if weather:
                with weather.open(newline="",encoding="utf-8-sig") as wfh:
                    for w in csv.DictReader(wfh):
                        site=w.get("site_id") or w.get("siteID")
                        if site in sites: temps[(site,w["timestamp"])]=_valid_float(w.get("airTemperature"))
            for bid in selected: con.execute("INSERT INTO buildings VALUES(?,?,?,0)",(bid,bid,meta[bid]["site_id"]))
            batch=[];count=0;missing=0
            for index,row in enumerate(reader):
                if index>=max_hours: break
                stamp=row["timestamp"].strip().replace(" ","T")
                if len(stamp)==16: stamp+=":00"
                for bid in selected:
                    kwh=_valid_float(row.get(bid))
                    if kwh is None or kwh<0: continue
                    temp=temps.get((meta[bid]["site_id"],row["timestamp"]))
                    if temp is None: missing+=1
                    batch.append((bid,stamp,kwh,temp))
                if len(batch)>=4000:
                    con.executemany("INSERT OR REPLACE INTO readings VALUES(?,?,?,?)",batch)
                    count+=len(batch);batch=[]
            if batch:
                con.executemany("INSERT OR REPLACE INTO readings VALUES(?,?,?,?)",batch);count+=len(batch)
    return {"buildings":len(selected),"readings_imported":count,"missing_temperature":missing,"weather_provided":bool(weather),"units":"hourly kWh","timestamps":"site-local naive"}
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--electricity",type=Path,required=True)
    p.add_argument("--metadata",type=Path,required=True)
    p.add_argument("--weather",type=Path)
    p.add_argument("--max-buildings",type=int,default=8)
    p.add_argument("--max-hours",type=int,default=1200)
    p.add_argument("--replace-demo",action="store_true")
    o=p.parse_args()
    print(import_bdg2(o.electricity,o.metadata,o.weather,o.max_buildings,o.max_hours,o.replace_demo))
