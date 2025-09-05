# src/rag/retriever.py

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# 需要全域變數：chunks, emb, index, embedder
# (通常這些在 Notebook 載入 PDF/embedding 後傳進來)


def search(query, embedder, index, emb, chunks, k=5, mmr_lambda=0.5):
    """
    Day2 版本：只回傳 chunks 純文字
    """
    qv = embedder.encode([query], normalize_embeddings=True).astype("float32")
    fetch = max(k*4, 20)
    D, I = index.search(qv, fetch)
    cands = [(i, float(D[0][j])) for j, i in enumerate(I[0])]

    selected, selected_vecs = [], []
    for idx, score in cands:
        cv = emb[idx]
        if not selected:
            selected.append((idx, score))
            selected_vecs.append(cv)
            if len(selected) >= k: break
            continue
        sim_to_S = max(float(np.dot(cv, sv)) for sv in selected_vecs)
        mmr = mmr_lambda*score - (1-mmr_lambda)*sim_to_S
        if mmr > -0.2 or len(selected) < k:
            selected.append((idx, score))
            selected_vecs.append(cv)
            if len(selected) >= k: break
    return [chunks[i] for i,_ in selected]


def search_with_meta(query, k=5, mmr_lambda=0.5, fetch=None):
    """
    回傳: list[dict]，每個 dict = {idx, score, chunk}
    """
    # 1) query 向量化
    qv = embedder.encode([query], normalize_embeddings=True).astype("float32")

    # 2) 先抓更多候選
    if fetch is None:
        fetch = max(k*4, 20)
    D, I = index.search(qv, fetch)
    cands = [(i, float(D[0][j])) for j, i in enumerate(I[0])]

    # 3) 簡易 MMR
    selected, selected_vecs = [], []
    for idx, score in cands:
        cv = emb[idx]
        if not selected:
            selected.append((idx, score))
            selected_vecs.append(cv)
            if len(selected) >= k: break
            continue

        sim_to_S = max(float(np.dot(cv, sv)) for sv in selected_vecs)
        mmr = mmr_lambda*score - (1-mmr_lambda)*sim_to_S
        if mmr > -0.2 or len(selected) < k:
            selected.append((idx, score))
            selected_vecs.append(cv)
            if len(selected) >= k: break

    results = [{"idx": i, "score": s, "chunk": chunks[i]} for i, s in selected]
    return results
