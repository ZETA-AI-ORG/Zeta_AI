from typing import List, Dict, Any
from transformers import pipeline

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: int = -1):
        """
        Initialise le cross-encoder HuggingFace pour le reranking sémantique.
        """
        self.reranker = pipeline(
            "text-classification",
            model=model_name,
            device=device,
            top_k=None,
            truncation=True
        )

    def rerank(self, query: str, passages: List[Dict[str, Any]], content_key: str = "content", top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank les passages (dicts) selon la similarité avec la requête.
        passages: liste de dicts avec au moins la clé content_key (ex: "content")
        Retourne les top_k passages rerankés (avec score).
        """
        pairs = [(query, p[content_key]) for p in passages]
        scores = self.reranker(pairs)
        # scores = [{'label': 'LABEL_1', 'score': 0.87}, ...]
        for p, s in zip(passages, scores):
            p['rerank_score'] = s['score']
        reranked = sorted(passages, key=lambda x: x['rerank_score'], reverse=True)
        return reranked[:top_k]
