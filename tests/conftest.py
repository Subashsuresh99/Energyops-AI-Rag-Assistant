import pytest
from energyops.demo import seed_demo
@pytest.fixture
def demo_db(tmp_path,monkeypatch):
    db=tmp_path/"energyops.sqlite3"
    monkeypatch.setenv("ENERGYOPS_DB_PATH",str(db))
    monkeypatch.setenv("ENERGYOPS_USE_OLLAMA","false")
    monkeypatch.delenv("ENERGYOPS_EMBEDDING_MODEL",raising=False)
    seed_demo(db)
    return db
