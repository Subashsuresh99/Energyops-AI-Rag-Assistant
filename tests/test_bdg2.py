from energyops.analytics import consumption_summary
from energyops.storage import connection
from scripts.import_bdg2 import import_bdg2

def test_import_and_no_overwrite(tmp_path):
    raw=tmp_path/"raw";raw.mkdir()
    (raw/"metadata.csv").write_text("building_id,site_id\nFox_A,Fox\nFox_B,Fox\n")
    (raw/"electricity.csv").write_text("timestamp,Fox_A,Fox_B\n2026-01-01 00:00:00,12,30\n2026-01-01 01:00:00,13,\n2026-01-01 02:00:00,-2,31\n")
    (raw/"weather.csv").write_text("timestamp,site_id,airTemperature\n2026-01-01 00:00:00,Fox,5\n2026-01-01 01:00:00,Fox,6\n")
    db=tmp_path/"import.sqlite3"
    result=import_bdg2(raw/"electricity.csv",raw/"metadata.csv",raw/"weather.csv",max_buildings=2,path=db)
    assert result["readings_imported"]==4
    assert result["missing_temperature"]==1
    assert consumption_summary("Fox_A",db)["buildings"][0]["total_kwh"]==25
    with connection(db) as con: assert con.execute("SELECT is_demo FROM buildings LIMIT 1").fetchone()[0]==0
    try: import_bdg2(raw/"electricity.csv",raw/"metadata.csv",path=db,replace_demo=True)
    except ValueError as e: assert "non-demo" in str(e)
    else: raise AssertionError("non-demo data must not be overwritten")
