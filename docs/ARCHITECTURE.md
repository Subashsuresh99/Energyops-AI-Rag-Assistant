# Architecture and design decisions

The application separates numerical analysis and document knowledge. FastAPI exposes narrowly scoped read APIs and an assistant endpoint. SQLite contains buildings, hourly readings, documents and indexed text chunks. Streamlit visualizes stored measurements and asks the API questions.

## Query flow

1. A deterministic router identifies a building ID and whether a user requests consumption statistics or anomalies.
2. Prewritten SQL/Python routines retrieve numerical facts, never unrestricted LLM-generated SQL.
3. TF-IDF (or optional Sentence Transformers) scores indexed document chunks.
4. The default answer is a cited evidence extract with structured `analytics` and `sources` fields. Optional Ollama can synthesize a natural-language answer from those fields.

## Limitations

- Synthetic demo data and SOPs; no real equipment diagnosis is demonstrated.
- Anomalies represent high consumption against a small historical median, not validated equipment faults.
- No occupancy, floor area, building operational state, calendar filters, or calibrated weather attribution.
- BDG2 data is historical; site-local timestamps need normalization for cross-site real-time comparison.
- In-process retrieval recomputes vectors per query and is not suitable for millions of chunks.
- Optional LLM text is not formally verified against sources.
- No user authentication or tenant data isolation; do not deploy publicly with confidential documents.
- All stored inputs must be considered untrusted; use trusted documents and follow applicable rights.
