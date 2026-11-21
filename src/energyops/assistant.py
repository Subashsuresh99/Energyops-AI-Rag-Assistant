"""Route questions to bounded SQL/Python tools and evidence retrieval."""
import re
from .analytics import consumption_summary,detect_anomalies
from .llm import synthesize
from .retrieval import retrieve
from .storage import list_buildings

def answer(question,path=None):
    question=question.strip()
    if not 1 <= len(question) <= 2000: raise ValueError("question length must be 1 to 2000")
    q=question.lower()
    match=re.search(r"\bB\d{3}\b",question,re.I)
    building_id=match.group().upper() if match else None
    if building_id is None:
        numbered=re.search(r"\bbuilding\s+(\d{1,3})\b",q)
        if numbered: building_id="B"+str(int(numbered.group(1))).zfill(3)
    if building_id and building_id not in {b["building_id"] for b in list_buildings(path)}:
        return {"answer":"Unknown building ID "+building_id,"sources":[],"analytics":{},"mode":"validation","warning":None}
    wants_anomalies=bool(re.search(r"anomal|spike|unusual|alert|outlier|why",q))
    wants_consumption=bool(re.search(r"consum|kwh|highest|most energy|usage|total energy|ranking|overview",q))
    results={}
    facts=[]
    if wants_consumption:
        results["consumption"]=consumption_summary(building_id,path)
        facts.append("Stored consumption summary: "+str(results["consumption"]))
    if wants_anomalies:
        results["anomalies"]=detect_anomalies(building_id,limit=8,path=path)
        facts.append("Historical same-hour/week anomalies: "+str(results["anomalies"]))
    sources=retrieve(question,top_k=3,path=path)
    llm_answer,warning=synthesize(question,"\n".join(facts),sources)
    if llm_answer is not None:
        return {"answer":llm_answer,"sources":sources,"analytics":results,"mode":"ollama","warning":warning}
    parts=[]
    if wants_consumption:
        entries=results["consumption"]["buildings"]
        if entries:
            top=max(entries,key=lambda b:b["total_kwh"])
            parts.append("Highest stored consumption: "+top["building_id"]+" — "+format(top["total_kwh"],",.2f")+" kWh across "+str(top["hours"])+" stored hours. Building sizes are not normalized.")
        else: parts.append("No readings are stored for that building.")
    if wants_anomalies:
        anomalies=results["anomalies"]
        if anomalies:
            e=anomalies[0]
            parts.append("Largest high-consumption anomaly: "+e["building_id"]+" at "+e["timestamp"]+": "+str(e["actual_kwh"])+" kWh versus baseline "+str(e["baseline_kwh"])+" kWh (+"+str(e["deviation_pct"])+"%). Root cause is unknown.")
        else: parts.append("No high-consumption anomalies matched the baseline criteria.")
    if any(x in q for x in ("last week","yesterday","today","this month","last month")):
        parts.append("This response covers stored readings, not the requested relative calendar period.")
    if sources:
        parts.append("Retrieved reference excerpts (not a diagnosis): "+" ".join(s["citation"]+" "+s["title"]+": "+s["excerpt"][:260] for s in sources))
    if not parts: parts.append("Insufficient evidence. Try asking about energy consumption, anomalies, or procedures.")
    return {"answer":"\n\n".join(parts),"sources":sources,"analytics":results,"mode":"grounded-extractive-fallback","warning":warning}
