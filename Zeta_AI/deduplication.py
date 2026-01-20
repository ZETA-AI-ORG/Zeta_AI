from embedding_models import get_embedding_model
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Utilise le même modèle que pour l'embedding RAG
MODEL_NAME = "mpnet-base-v2"
model = get_embedding_model(MODEL_NAME)


def fuzzy_deduplicate(texts, threshold=0.85):
    """
    Supprime les doublons sémantiques dans une liste de textes.
    Deux textes sont considérés comme doublons si leur similarité cosinus > threshold.
    """
    if len(texts) < 2:
        return texts
    embeddings = model.encode(texts)
    keep = []
    seen = set()
    for i, emb in enumerate(embeddings):
        if i in seen:
            continue
        keep.append(texts[i])
        sims = cosine_similarity([emb], embeddings)[0]
        for j, sim in enumerate(sims):
            if j > i and sim > threshold:
                seen.add(j)
    return keep
