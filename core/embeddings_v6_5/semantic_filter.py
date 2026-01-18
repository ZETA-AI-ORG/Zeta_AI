# -*- coding: utf-8 -*-
"""
SEMANTIC FILTER V6.5 - Layer 3 Embeddings (Filet de sécurité)

ARCHITECTURE :
- Layer 1 : V6 Prefilter (Paiement/Contact/SAV) → PRIORITÉ MAX
- Layer 2 : V5 Keywords (Prix/Livraison/Achat) → GARDE-FOU
- Layer 3 : Embeddings V6.5 (CE MODULE) → FILET DE SÉCURITÉ
- Layer 4 : SetFit ML → FALLBACK

RÈGLES STRICTES :
- Seuil min : 0.75 (en dessous = ignore)
- Confiance max : 0.88 (ne jamais dépasser V6/V5)
- Cache embeddings obligatoire (performance)
- Pas d'auto-learning
"""

import logging
import pickle
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Any
import numpy as np

logger = logging.getLogger(__name__)

# Import lazy pour éviter chargement au démarrage si non utilisé
_SENTENCE_TRANSFORMER_MODEL = None


def _get_sentence_transformer():
    """Lazy loading du modèle SentenceTransformer (singleton)."""
    global _SENTENCE_TRANSFORMER_MODEL
    
    if _SENTENCE_TRANSFORMER_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[EMBEDDINGS_V6.5] Chargement modèle SentenceTransformer...")
            _SENTENCE_TRANSFORMER_MODEL = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2'
            )
            logger.info("[EMBEDDINGS_V6.5] Modèle chargé avec succès")
        except ImportError:
            logger.warning(
                "[EMBEDDINGS_V6.5] sentence-transformers non installé. "
                "Layer 3 désactivé. Installer avec: pip install sentence-transformers"
            )
            return None
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur chargement modèle: {e}")
            return None
    
    return _SENTENCE_TRANSFORMER_MODEL


class SemanticFilterV65:
    """
    Layer 3 : Filtrage sémantique par embeddings.
    
    Mode conservateur :
    - Seuil 0.75 minimum
    - Confiance plafonnée à 0.88
    - Cache embeddings pour performance
    - Logging suggestions si >= 0.82
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        from .prototypes import INTENT_PROTOTYPES_V65, EMBEDDINGS_CONFIG_V65
        
        self.config = EMBEDDINGS_CONFIG_V65
        self.prototypes = INTENT_PROTOTYPES_V65
        self.prototype_embeddings: Dict[str, np.ndarray] = {}
        
        # Chemins cache
        if cache_dir:
            self.cache_file = Path(cache_dir) / "prototype_embeddings_v6_5.pkl"
        else:
            self.cache_file = Path("cache/prototype_embeddings_v6_5.pkl")
        
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Seuils
        self.threshold_min = self.config["threshold_min"]
        self.confidence_max = self.config["confidence_max"]
        
        # État
        self._initialized = False
        self._model = None
    
    def _ensure_initialized(self) -> bool:
        """Initialisation lazy (premier appel uniquement)."""
        if self._initialized:
            return self._model is not None
        
        self._initialized = True
        self._model = _get_sentence_transformer()
        
        if self._model is None:
            logger.warning("[EMBEDDINGS_V6.5] Modèle non disponible, Layer 3 désactivé")
            return False
        
        # Charger ou calculer embeddings prototypes
        if self._load_cache():
            logger.info("[EMBEDDINGS_V6.5] Cache prototypes chargé")
        else:
            logger.info("[EMBEDDINGS_V6.5] Calcul embeddings prototypes...")
            self._compute_prototype_embeddings()
            self._save_cache()
            logger.info("[EMBEDDINGS_V6.5] Cache prototypes sauvegardé")
        
        return True
    
    def _load_cache(self) -> bool:
        """Charge les embeddings depuis le cache."""
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'rb') as f:
                cached = pickle.load(f)
            
            # Vérifier que le cache correspond aux prototypes actuels
            cached_intents = set(cached.keys())
            current_intents = set(self.prototypes.keys())
            
            if cached_intents != current_intents:
                logger.info("[EMBEDDINGS_V6.5] Cache invalide (intents différents)")
                return False
            
            # Vérifier nombre de prototypes par intent
            for intent, embeddings in cached.items():
                if len(embeddings) != len(self.prototypes.get(intent, [])):
                    logger.info(f"[EMBEDDINGS_V6.5] Cache invalide pour {intent}")
                    return False
            
            self.prototype_embeddings = cached
            return True
            
        except Exception as e:
            logger.warning(f"[EMBEDDINGS_V6.5] Erreur lecture cache: {e}")
            return False
    
    def _save_cache(self) -> bool:
        """Sauvegarde les embeddings dans le cache."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.prototype_embeddings, f)
            return True
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur sauvegarde cache: {e}")
            return False
    
    def _compute_prototype_embeddings(self):
        """Calcule les embeddings de tous les prototypes."""
        if self._model is None:
            return
        
        for intent, proto_list in self.prototypes.items():
            if proto_list:
                embeddings = self._model.encode(proto_list, convert_to_numpy=True)
                self.prototype_embeddings[intent] = embeddings
                logger.debug(
                    f"[EMBEDDINGS_V6.5] {intent}: {len(proto_list)} prototypes encodés"
                )
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcule la similarité cosine entre deux vecteurs."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def detect(
        self,
        message: str
    ) -> Tuple[Optional[str], float, Optional[str], Dict[str, Any]]:
        """
        Détecte l'intent via similarité sémantique avec les prototypes.
        
        Args:
            message: Message utilisateur à classifier
            
        Returns:
            Tuple (intent, confidence, matched_prototype, debug_info)
            - intent: Intent détecté ou None si sous seuil
            - confidence: Score confiance (0.75-0.88)
            - matched_prototype: Prototype le plus similaire
            - debug_info: Infos debug (similarité brute, tous scores, etc.)
        """
        debug_info = {
            "layer": "v6_5_embeddings",
            "initialized": False,
            "similarity_raw": 0.0,
            "all_scores": {},
        }
        
        # Initialisation lazy
        if not self._ensure_initialized():
            return None, 0.0, None, debug_info
        
        debug_info["initialized"] = True
        
        if not message or not message.strip():
            return None, 0.0, None, debug_info
        
        try:
            # Encoder le message
            msg_embedding = self._model.encode([message], convert_to_numpy=True)[0]
            
            # Comparer avec tous les prototypes
            best_intent = None
            best_similarity = 0.0
            best_prototype = None
            all_scores = {}
            
            for intent, proto_embeddings in self.prototype_embeddings.items():
                intent_best_sim = 0.0
                intent_best_proto = None
                
                for i, proto_emb in enumerate(proto_embeddings):
                    sim = self._cosine_similarity(msg_embedding, proto_emb)
                    
                    if sim > intent_best_sim:
                        intent_best_sim = sim
                        intent_best_proto = self.prototypes[intent][i]
                
                all_scores[intent] = round(intent_best_sim, 4)
                
                if intent_best_sim > best_similarity:
                    best_similarity = intent_best_sim
                    best_intent = intent
                    best_prototype = intent_best_proto
            
            debug_info["similarity_raw"] = round(best_similarity, 4)
            debug_info["all_scores"] = all_scores
            debug_info["best_prototype"] = best_prototype
            
            # Vérifier seuil minimum
            if best_similarity < self.threshold_min:
                logger.debug(
                    f"[EMBEDDINGS_V6.5] Sous seuil: sim={best_similarity:.3f} < {self.threshold_min}"
                )
                return None, 0.0, None, debug_info
            
            # Plafonner confiance à 0.88
            confidence = min(best_similarity, self.confidence_max)
            
            logger.info(
                f"[EMBEDDINGS_V6.5] Match: intent={best_intent} "
                f"sim={best_similarity:.3f} conf={confidence:.3f} "
                f"proto='{best_prototype[:40]}...'"
            )
            
            return best_intent, confidence, best_prototype, debug_info
            
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur detect: {e}")
            debug_info["error"] = str(e)
            return None, 0.0, None, debug_info
    
    def is_available(self) -> bool:
        """Vérifie si le Layer 3 est disponible (modèle chargé)."""
        return self._ensure_initialized()
    
    def get_stats(self) -> dict:
        """Statistiques du filtre."""
        return {
            "initialized": self._initialized,
            "model_loaded": self._model is not None,
            "cache_file": str(self.cache_file),
            "cache_exists": self.cache_file.exists(),
            "intents_count": len(self.prototypes),
            "total_prototypes": sum(len(p) for p in self.prototypes.values()),
            "threshold_min": self.threshold_min,
            "confidence_max": self.confidence_max,
        }
    
    def invalidate_cache(self) -> bool:
        """Invalide le cache (force recalcul au prochain appel)."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            self.prototype_embeddings = {}
            self._initialized = False
            logger.info("[EMBEDDINGS_V6.5] Cache invalidé")
            return True
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur invalidation cache: {e}")
            return False
