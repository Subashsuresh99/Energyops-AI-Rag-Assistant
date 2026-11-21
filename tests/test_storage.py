from energyops.storage import add_document,list_buildings,list_documents,readings

def test_seeded_data(demo_db):
    assert len(list_buildings(demo_db))==6
    rows=readings("B001",12,demo_db)
    assert len(rows)==12
    assert rows==sorted(rows,key=lambda r:r["timestamp"])
    assert all(r["kwh"]>0 for r in rows)

def test_documents_and_rollback(demo_db):
    add_document("My SOP","test://sop",[(2,"HVAC filters and setpoints")],demo_db)
    count=len(list_documents(demo_db))
    try: add_document("Empty","test://empty",[(1,"   ")],demo_db)
    except ValueError: pass
    else: raise AssertionError("empty document must fail")
    assert len(list_documents(demo_db))==count
