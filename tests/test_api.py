from fastapi.testclient import TestClient
from energyops.api import app

def test_api(demo_db):
    with TestClient(app) as client:
        assert client.get("/health").status_code==200
        assert len(client.get("/buildings").json())==6
        assert len(client.get("/readings/B001",params={"limit":5}).json()["readings"])==5
        assert client.get("/readings/BOGUS").status_code==404
        result=client.post("/ask",json={"question":"Which building has highest usage?"})
        assert result.status_code==200
        assert result.json()["analytics"]["consumption"]["buildings"]

def test_validation(demo_db):
    with TestClient(app) as client:
        item={"title":"Safety SOP","source":"unit-test","text":"Monitor meter readings daily."}
        assert client.post("/documents",json=item).status_code==201
        assert any(d["title"]=="Safety SOP" for d in client.get("/documents").json())
        assert client.get("/anomalies",params={"threshold_ratio":0.5}).status_code==422
        assert client.post("/ask",json={"question":""}).status_code==422
