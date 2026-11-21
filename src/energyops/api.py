"""FastAPI service for energy analytics and evidence-backed QA."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Query
from pydantic import BaseModel,Field
from .analytics import consumption_summary,detect_anomalies
from .assistant import answer
from .config import db_path
from .demo import seed_demo
from .storage import add_document,initialize,list_buildings,list_documents,readings

class Question(BaseModel):
    question:str=Field(min_length=1,max_length=2000)
class DocumentInput(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    source:str=Field(min_length=1,max_length=300)
    text:str=Field(min_length=1,max_length=200000)
@asynccontextmanager
async def lifespan(app):
    initialize()
    if os.getenv("ENERGYOPS_AUTO_SEED","true").lower() in ("true","1","yes"): seed_demo()
    yield
app=FastAPI(title="EnergyOps AI",version="0.1.0",lifespan=lifespan)
@app.get("/health")
def health(): return {"status":"ok","db_path":str(db_path()),"version":"0.1.0"}
@app.get("/buildings")
def buildings(): return list_buildings()
@app.get("/readings/{building_id}")
def get_readings(building_id:str,limit:int=Query(336,ge=1,le=5000)):
    if building_id not in {b["building_id"] for b in list_buildings()}:
        raise HTTPException(status_code=404,detail="Building not found")
    return {"building_id":building_id,"units":{"kwh":"kWh","temperature_c":"°C"},"readings":readings(building_id,limit)}
@app.get("/summary")
def summary(building_id:str|None=None): return consumption_summary(building_id)
@app.get("/anomalies")
def anomalies(building_id:str|None=None,threshold_ratio:float=Query(1.45,gt=1,le=10),limit:int=Query(50,ge=1,le=500)):
    try: return detect_anomalies(building_id,threshold_ratio=threshold_ratio,limit=limit)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
@app.get("/documents")
def documents(): return list_documents()
@app.post("/documents",status_code=201)
def ingest_document(item:DocumentInput):
    try: doc_id=add_document(item.title,item.source,[(None,item.text)])
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"document_id":doc_id,"title":item.title}
@app.post("/ask")
def ask(item:Question):
    try: return answer(item.question)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
