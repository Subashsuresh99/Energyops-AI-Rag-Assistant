from energyops.assistant import answer
from energyops.retrieval import retrieve,split_text

def test_overlap():
    parts=split_text(" ".join(map(str,range(20))),words_per_chunk=10,overlap=2)
    assert parts[0].split()[-2:]==parts[1].split()[:2]

def test_citation(demo_db):
    hits=retrieve("How do I check unexpected HVAC electrical demand?",path=demo_db)
    assert hits
    assert any(h["title"]=="Demo HVAC Inspection SOP" for h in hits)
    assert hits[0]["citation"]=="[1]"

def test_sql_plus_document_answer(demo_db):
    r=answer("Why is B001 unusual energy consumption high?",demo_db)
    assert r["mode"]=="grounded-extractive-fallback"
    assert r["analytics"]["anomalies"]
    assert "Root cause is unknown" in r["answer"]

def test_unknown_building(demo_db):
    r=answer("What did B999 consume?",demo_db)
    assert "Unknown building" in r["answer"] and r["analytics"]=={}

def test_no_hallucinated_unknown_fact(demo_db):
    r=answer("What is the price of moon dust?",demo_db)
    assert r["analytics"]=={} and not r["sources"]
    assert "Insufficient evidence" in r["answer"]
