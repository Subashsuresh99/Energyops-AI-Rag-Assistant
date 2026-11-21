# Evaluation strategy

Run `pytest` for the deterministic tests and `python scripts/evaluate.py` for a small synthetic five-query retrieval hit@3 sanity check.

The synthetic check is not a valid claim of production retrieval accuracy. A stronger benchmark should include:

1. At least 50 representative annotated questions across maintenance, energy analytics and unanswerable cases.
2. Ground-truth source passages for each retrievable question.
3. Retrieval recall@k and mean reciprocal rank across TF-IDF and dense embeddings.
4. Numerical consistency tests against direct SQL totals and anomaly computations.
5. Answer-level faithfulness, source citation correctness and unsupported-cause rate.
6. Measured response latency and model execution cost.
7. Adversarial content tests for document-based prompt injection and unknown-building requests.
8. Evaluation on an unseen real BDG2 subset and separately curated public energy documentation.

Report counts, seeds, dataset provenance and uncertainty. Do not present synthetic anomaly alerts as equipment failures or model performance on real buildings.
