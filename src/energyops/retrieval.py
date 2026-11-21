"""Grounded document retrieval: TF-IDF default, optional semantic embeddings."""
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .storage import connection

def split_text(text, words_per_chunk=170, overlap=28):
    words=text.split()
    if not 0 <= overlap < words_per_chunk:
        raise ValueError("invalid chunk overlap")
    step=words_per_chunk-overlap
    return [" ".join(words[i:i+words_per_chunk]) for i in range(0,len(words),step) if words[i:i+words_per_chunk]]

def retrieve(query, top_k=3, min_score=0.055, path=None):
    if not query.strip() or not 1 <= top_k <= 10: return []
    with connection(path) as con:
        rows=[dict(r) for r in con.execute("SELECT c.chunk_id,c.page_number,c.content,d.title,d.source FROM chunks c JOIN documents d ON d.document_id=c.document_id ORDER BY c.chunk_id")]
    if not rows: return []
    corpus=[r["content"] for r in rows]
    model_name=os.getenv("ENERGYOPS_EMBEDDING_MODEL","").strip()
    if model_name:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install optional embeddings dependency") from exc
        model=SentenceTransformer(model_name)
        vectors=model.encode(corpus+[query],normalize_embeddings=True)
        scores=(vectors[:-1] @ vectors[-1]).tolist()
        engine="sentence-transformers:"+model_name
    else:
        vect=TfidfVectorizer(stop_words="english",ngram_range=(1,2),sublinear_tf=True)
        try: matrix=vect.fit_transform(corpus+[query])
        except ValueError: return []
        scores=cosine_similarity(matrix[:-1],matrix[-1]).ravel().tolist()
        engine="tfidf-baseline"
    ranked=sorted(enumerate(scores),key=lambda p:p[1],reverse=True)
    return [{"citation":"["+str(i+1)+"]","title":rows[idx]["title"],"source":rows[idx]["source"],"page":rows[idx]["page_number"],"excerpt":rows[idx]["content"],"score":round(float(score),4),"retriever":engine} for i,(idx,score) in enumerate(ranked[:top_k]) if score>=min_score]
