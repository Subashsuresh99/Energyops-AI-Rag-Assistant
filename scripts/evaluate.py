"""Five-case synthetic retrieval sanity check; not a general benchmark."""
from energyops.demo import seed_demo
from energyops.retrieval import retrieve
CASES=[
("Which checks should I do when HVAC demand increases?","Demo HVAC Inspection SOP"),
("What is a kilowatt-hour?","Demo Energy Reporting Policy"),
("How to triage high consumption meter alerts?","Demo Energy Anomaly Triage Guide"),
("What should I check for unexpected occupancy scheduling?","Demo HVAC Inspection SOP"),
("How do you report percentage deviation from baseline?","Demo Energy Reporting Policy")]
def main():
    seed_demo()
    matched=sum(expected in [r["title"] for r in retrieve(q,top_k=3)] for q,expected in CASES)
    print("Synthetic document hit@3:",matched,"/",len(CASES))
    print("Not a validated real-world RAG score.")
if __name__=="__main__": main()
