#!/usr/bin/env python3
"""
🚀 SYSTÈME DE CACHE DYNAMIQUE INTENTION-FAQ RÉVOLUTIONNAIRE
===========================================================
Basé sur les recherches 2024/2025 - Architecture ContextCache + Semantic Caching

INNOVATIONS IMPLÉMENTÉES:
- Cache multi-granulaire (intention + entités + contexte)
- Two-Stage Dynamic Retrieval (recherche rapide + matching précis)
- Embeddings contextuels pour similarité sémantique
- Cache conscient du contexte conversationnel

PERFORMANCE ATTENDUE:
- 10x plus rapide que l'invocation LLM
- Réutilisation accrue des réponses (même si formulation diffère)
- Résilience aux variations de langage (synonymes, paraphrases)
"""

import asyncio
import hashlib
import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
import threading

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from utils import log3

@dataclass
class IntentSignature:
    """🎯 Signature d'intention pour le cache multi-granulaire"""
    primary_intent: str
    secondary_intents: List[str]
    entities: Dict[str, str]  # {type: value} ex: {"zone": "Cocody", "produit": "casque"}
    context_hash: str  # Hash du contexte conversationnel
    confidence_score: float

@dataclass
class CacheEntry:
    """📦 Entrée de cache avec métadonnées complètes"""
    response: str
    intent_signature: IntentSignature
    query_embedding: List[float]
    context_embedding: List[float]
    timestamp: float
    hit_count: int
    last_accessed: float
    ttl_seconds: int

class TwoStageRetrievalEngine:
    """
    ⚡ Moteur de récupération en deux étapes
    Stage 1: Recherche vectorielle rapide (candidats)
    Stage 2: Matching contextuel précis avec attention
    """
    
    def __init__(self, similarity_threshold: float = 0.4, context_weight: float = 0.3):
        self.similarity_threshold = similarity_threshold
        self.context_weight = context_weight
        self.embedding_model = None
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """Initialise le modèle d'embeddings (réutilise le cache global si possible)"""
        try:
            from core.global_embedding_cache_optimized import get_global_embedding_cache
            cache = get_global_embedding_cache()
            self.embedding_model = cache.model
            log3("[SEMANTIC_CACHE]", "🔗 Réutilisation du modèle d'embeddings global")
        except Exception as e:
            # Fallback: charger le modèle directement
            self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
            log3("[SEMANTIC_CACHE]", f"📥 Modèle d'embeddings chargé directement: {e}")
    
    def create_query_embedding(self, query: str) -> List[float]:
        """Crée l'embedding d'une requête"""
        if self.embedding_model is None:
            self._init_embedding_model()
        
        embedding = self.embedding_model.encode(query, convert_to_tensor=False)
        return embedding.tolist()
    
    def create_context_embedding(self, conversation_history: str) -> List[float]:
        """Crée l'embedding du contexte conversationnel"""
        if not conversation_history.strip():
            return [0.0] * 768  # Embedding vide pour contexte vide
        
        if self.embedding_model is None:
            self._init_embedding_model()
        
        # Tronquer le contexte pour éviter les embeddings trop longs
        context_truncated = conversation_history[-1000:] if len(conversation_history) > 1000 else conversation_history
        embedding = self.embedding_model.encode(context_truncated, convert_to_tensor=False)
        return embedding.tolist()
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Éviter la division par zéro
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            log3("[SEMANTIC_CACHE]", f"❌ Erreur calcul similarité: {e}")
            return 0.0
    
    def stage1_rapid_search(self, query_embedding: List[float], cache_entries: Dict[str, CacheEntry]) -> List[Tuple[str, float]]:
        """
        🚀 Stage 1: Recherche vectorielle rapide
        Retourne les candidats avec leur score de similarité
        """
        candidates = []
        
        for cache_key, entry in cache_entries.items():
            # Similarité basée sur l'embedding de la requête
            query_similarity = self.calculate_similarity(query_embedding, entry.query_embedding)
            
            if query_similarity >= self.similarity_threshold * 0.8:  # Seuil plus bas pour Stage 1
                candidates.append((cache_key, query_similarity))
        
        # Trier par similarité décroissante et garder les top 10
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:10]
    
    def stage2_contextual_matching(self, 
                                 query_embedding: List[float],
                                 context_embedding: List[float],
                                 intent_signature: IntentSignature,
                                 candidates: List[Tuple[str, float]],
                                 cache_entries: Dict[str, CacheEntry]) -> Optional[Tuple[str, float]]:
        """
        🎯 Stage 2: Matching contextuel précis avec attention
        Analyse les candidats avec le contexte et les intentions
        """
        best_match = None
        best_score = 0.0
        
        for cache_key, query_sim in candidates:
            entry = cache_entries[cache_key]
            
            # Score composite: requête + contexte + intention
            context_sim = self.calculate_similarity(context_embedding, entry.context_embedding)
            
            # Score d'intention (basé sur la correspondance des intentions et entités)
            intent_score = self._calculate_intent_similarity(intent_signature, entry.intent_signature)
            
            # Score final pondéré
            final_score = (
                query_sim * 0.5 +  # 50% similarité requête
                context_sim * self.context_weight +  # 30% similarité contexte
                intent_score * 0.2  # 20% similarité intention
            )
            
            if final_score > best_score and final_score >= self.similarity_threshold:
                best_score = final_score
                best_match = (cache_key, final_score)
        
        return best_match
    
    def _calculate_intent_similarity(self, intent1: IntentSignature, intent2: IntentSignature) -> float:
        """Calcule la similarité entre deux signatures d'intention"""
        score = 0.0
        
        # Intention primaire (50% du score)
        if intent1.primary_intent == intent2.primary_intent:
            score += 0.5
        
        # Entités communes (30% du score)
        common_entities = set(intent1.entities.keys()) & set(intent2.entities.keys())
        if common_entities:
            matching_values = sum(1 for key in common_entities 
                                if intent1.entities[key] == intent2.entities[key])
            entity_score = matching_values / len(intent1.entities) if intent1.entities else 0
            score += entity_score * 0.3
        
        # Intentions secondaires (20% du score)
        if intent1.secondary_intents and intent2.secondary_intents:
            common_secondary = set(intent1.secondary_intents) & set(intent2.secondary_intents)
            secondary_score = len(common_secondary) / max(len(intent1.secondary_intents), len(intent2.secondary_intents))
            score += secondary_score * 0.2
        
        return score

class SemanticIntentCache:
    """
    🧠 Cache Dynamique Intention-FAQ Révolutionnaire
    
    FONCTIONNALITÉS:
    - Cache multi-granulaire basé sur les intentions et entités
    - Recherche sémantique avec embeddings vectoriels
    - Two-Stage Retrieval pour performance optimale
    - Gestion intelligente du TTL et de l'expiration
    """
    
    def __init__(self, 
                 default_ttl: int = 3600,  # 1 heure par défaut
                 max_cache_size: int = 10000,
                 similarity_threshold: float = 0.4):
        
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.similarity_threshold = similarity_threshold
        
        # Stockage en mémoire et Redis
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.redis_client = None
        
        # Moteur de récupération en deux étapes
        self.retrieval_engine = TwoStageRetrievalEngine(similarity_threshold)
        
        # Statistiques
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_matches": 0,
            "exact_matches": 0,
            "total_time_saved": 0.0
        }
        
        self.lock = threading.RLock()
        
        # Initialiser Redis si disponible
        self._init_redis()
        
        log3("[SEMANTIC_CACHE]", "🚀 Cache Dynamique Intention-FAQ initialisé")
    
    def _init_redis(self):
        """Initialise la connexion Redis si disponible"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost', 
                    port=6379, 
                    db=2,  # DB séparée pour le cache sémantique
                    decode_responses=False  # Pour stocker les données binaires
                )
                # Test de connexion
                self.redis_client.ping()
                log3("[SEMANTIC_CACHE]", "✅ Redis connecté (DB 2)")
            except Exception as e:
                self.redis_client = None
                log3("[SEMANTIC_CACHE]", f"⚠️ Redis non disponible: {e}")
    
    def _create_cache_key(self, intent_signature: IntentSignature, query_hash: str) -> str:
        """Crée une clé de cache basée sur la signature d'intention"""
        key_data = {
            "intent": intent_signature.primary_intent,
            "entities": sorted(intent_signature.entities.items()),
            "query_hash": query_hash[:16]  # Premiers 16 caractères du hash
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _serialize_entry(self, entry: CacheEntry) -> bytes:
        """Sérialise une entrée de cache pour Redis"""
        try:
            data = asdict(entry)
            return json.dumps(data).encode('utf-8')
        except Exception as e:
            log3("[SEMANTIC_CACHE]", f"❌ Erreur sérialisation: {e}")
            return b""
    
    def _deserialize_entry(self, data: bytes) -> Optional[CacheEntry]:
        """Désérialise une entrée de cache depuis Redis"""
        try:
            json_data = json.loads(data.decode('utf-8'))
            
            # Reconstruire l'IntentSignature
            intent_data = json_data['intent_signature']
            intent_signature = IntentSignature(
                primary_intent=intent_data['primary_intent'],
                secondary_intents=intent_data['secondary_intents'],
                entities=intent_data['entities'],
                context_hash=intent_data['context_hash'],
                confidence_score=intent_data['confidence_score']
            )
            
            # Reconstruire le CacheEntry
            return CacheEntry(
                response=json_data['response'],
                intent_signature=intent_signature,
                query_embedding=json_data['query_embedding'],
                context_embedding=json_data['context_embedding'],
                timestamp=json_data['timestamp'],
                hit_count=json_data['hit_count'],
                last_accessed=json_data['last_accessed'],
                ttl_seconds=json_data['ttl_seconds']
            )
        except Exception as e:
            log3("[SEMANTIC_CACHE]", f"❌ Erreur désérialisation: {e}")
            return None
    
    async def get_cached_response(self, 
                                query: str,
                                intent_signature: IntentSignature,
                                conversation_history: str = "") -> Optional[Tuple[str, float]]:
        """
        🔍 Recherche une réponse dans le cache avec matching sémantique
        
        Returns:
            Tuple[response, confidence_score] si trouvé, None sinon
        """
        start_time = time.time()
        
        with self.lock:
            self.stats["total_queries"] += 1
            
            # Créer les embeddings
            query_embedding = self.retrieval_engine.create_query_embedding(query)
            context_embedding = self.retrieval_engine.create_context_embedding(conversation_history)
            
            # Stage 1: Recherche rapide des candidats
            candidates = self.retrieval_engine.stage1_rapid_search(query_embedding, self.memory_cache)
            
            if not candidates:
                self.stats["cache_misses"] += 1
                log3("[SEMANTIC_CACHE]", f"❌ Aucun candidat trouvé pour: {query[:50]}...")
                return None
            
            # Stage 2: Matching contextuel précis
            best_match = self.retrieval_engine.stage2_contextual_matching(
                query_embedding, context_embedding, intent_signature, candidates, self.memory_cache
            )
            
            if best_match:
                cache_key, confidence = best_match
                entry = self.memory_cache[cache_key]
                
                # Mettre à jour les statistiques d'accès
                entry.hit_count += 1
                entry.last_accessed = time.time()
                
                # Statistiques globales
                self.stats["cache_hits"] += 1
                if confidence > 0.95:
                    self.stats["exact_matches"] += 1
                else:
                    self.stats["semantic_matches"] += 1
                
                elapsed = time.time() - start_time
                self.stats["total_time_saved"] += max(0, 5.0 - elapsed)  # Estimation: 5s économisés vs LLM
                
                log3("[SEMANTIC_CACHE]", f"✅ Cache HIT (conf: {confidence:.3f}): {query[:50]}...")
                return (entry.response, confidence)
            
            self.stats["cache_misses"] += 1
            log3("[SEMANTIC_CACHE]", f"❌ Cache MISS: {query[:50]}...")
            return None
    
    async def store_response(self,
                           query: str,
                           response: str,
                           intent_signature: IntentSignature,
                           conversation_history: str = "",
                           ttl_seconds: Optional[int] = None) -> bool:
        """
        💾 Stocke une réponse dans le cache avec signature sémantique
        """
        try:
            with self.lock:
                # Créer les embeddings
                query_embedding = self.retrieval_engine.create_query_embedding(query)
                context_embedding = self.retrieval_engine.create_context_embedding(conversation_history)
                
                # Créer la clé de cache
                query_hash = hashlib.sha256(query.encode()).hexdigest()
                cache_key = self._create_cache_key(intent_signature, query_hash)
                
                # Créer l'entrée de cache
                entry = CacheEntry(
                    response=response,
                    intent_signature=intent_signature,
                    query_embedding=query_embedding,
                    context_embedding=context_embedding,
                    timestamp=time.time(),
                    hit_count=0,
                    last_accessed=time.time(),
                    ttl_seconds=ttl_seconds or self.default_ttl
                )
                
                # Stocker en mémoire
                self.memory_cache[cache_key] = entry
                
                # Stocker dans Redis si disponible
                if self.redis_client:
                    try:
                        serialized = self._serialize_entry(entry)
                        self.redis_client.setex(
                            f"semantic_cache:{cache_key}",
                            entry.ttl_seconds,
                            serialized
                        )
                    except Exception as e:
                        log3("[SEMANTIC_CACHE]", f"⚠️ Erreur Redis store: {e}")
                
                # Nettoyage si le cache devient trop grand
                if len(self.memory_cache) > self.max_cache_size:
                    await self._cleanup_old_entries()
                
                log3("[SEMANTIC_CACHE]", f"💾 Réponse stockée: {intent_signature.primary_intent}")
                return True
                
        except Exception as e:
            log3("[SEMANTIC_CACHE]", f"❌ Erreur stockage: {e}")
            return False
    
    async def _cleanup_old_entries(self):
        """🧹 Nettoie les anciennes entrées du cache"""
        try:
            current_time = time.time()
            
            # Supprimer les entrées expirées
            expired_keys = []
            for key, entry in self.memory_cache.items():
                if current_time - entry.timestamp > entry.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            # Si encore trop d'entrées, supprimer les moins utilisées
            if len(self.memory_cache) > self.max_cache_size:
                # Trier par hit_count et last_accessed
                sorted_entries = sorted(
                    self.memory_cache.items(),
                    key=lambda x: (x[1].hit_count, x[1].last_accessed)
                )
                
                # Garder seulement les 80% les plus utilisées
                keep_count = int(self.max_cache_size * 0.8)
                to_remove = sorted_entries[:-keep_count] if keep_count > 0 else sorted_entries
                
                for key, _ in to_remove:
                    del self.memory_cache[key]
            
            log3("[SEMANTIC_CACHE]", f"🧹 Nettoyage: {len(expired_keys)} expirées, cache: {len(self.memory_cache)} entrées")
            
        except Exception as e:
            log3("[SEMANTIC_CACHE]", f"❌ Erreur nettoyage: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """📊 Retourne les statistiques du cache"""
        with self.lock:
            hit_rate = (self.stats["cache_hits"] / max(1, self.stats["total_queries"])) * 100
            
            return {
                **self.stats,
                "hit_rate_percent": round(hit_rate, 2),
                "cache_size": len(self.memory_cache),
                "redis_available": self.redis_client is not None,
                "avg_time_saved_per_hit": (
                    self.stats["total_time_saved"] / max(1, self.stats["cache_hits"])
                )
            }
    
    async def clear_cache(self, company_id: Optional[str] = None):
        """🗑️ Vide le cache (optionnellement pour une entreprise spécifique)"""
        with self.lock:
            if company_id:
                # Vider seulement pour une entreprise (à implémenter si nécessaire)
                pass
            else:
                # Vider tout le cache
                self.memory_cache.clear()
                
                if self.redis_client:
                    try:
                        # Supprimer toutes les clés du cache sémantique
                        keys = self.redis_client.keys("semantic_cache:*")
                        if keys:
                            self.redis_client.delete(*keys)
                    except Exception as e:
                        log3("[SEMANTIC_CACHE]", f"⚠️ Erreur vidage Redis: {e}")
                
                log3("[SEMANTIC_CACHE]", "🗑️ Cache vidé complètement")

# Singleton global
_semantic_cache_instance = None
_cache_lock = threading.Lock()

def get_semantic_intent_cache() -> SemanticIntentCache:
    """🎯 Récupère l'instance singleton du cache sémantique"""
    global _semantic_cache_instance
    
    if _semantic_cache_instance is None:
        with _cache_lock:
            if _semantic_cache_instance is None:
                _semantic_cache_instance = SemanticIntentCache()
    
    return _semantic_cache_instance

# Fonctions utilitaires pour l'intégration avec le nouveau système d'intention
def create_intent_signature_from_detection(detection_result: Dict[str, Any]) -> IntentSignature:
    """
    🎯 NOUVELLE VERSION: Crée une signature d'intention à partir du système révolutionnaire
    
    Args:
        detection_result: Résultat du nouveau système de détection d'intention binaire
    """
    intentions = detection_result.get("detected_intentions", [])
    structured_data = detection_result.get("structured_data", {})
    
    return IntentSignature(
        primary_intent=structured_data.get("primary_focus", "GENERAL"),
        secondary_intents=structured_data.get("secondary_aspects", []),
        entities={},  # Les entités seront extraites des documents reranked
        context_hash=structured_data.get("intention_signature", ""),
        confidence_score=detection_result.get("confidence_score", 1.0)
    )

def create_intent_signature_from_binary_detection(
    detected_intentions: List[str], 
    query: str, 
    results_by_index: Dict[str, List]) -> IntentSignature:
    """
    🎯 CRÉATION DIRECTE DE SIGNATURE DEPUIS LA LOGIQUE BINAIRE
    
    Args:
        detected_intentions: Liste des intentions détectées (binaire)
        query: Requête originale
        results_by_index: Résultats par index
    """
    # Extraire des entités basiques depuis la requête et les résultats
    entities = extract_basic_entities_from_query_and_results(query, results_by_index)
    
    return IntentSignature(
        primary_intent=detected_intentions[0] if detected_intentions else "GENERAL",
        secondary_intents=detected_intentions[1:] if len(detected_intentions) > 1 else [],
        entities=entities,
        context_hash="|".join(sorted(detected_intentions)),
        confidence_score=1.0 if detected_intentions else 0.0
    )

def extract_basic_entities_from_query_and_results(query: str, results_by_index: Dict[str, List]) -> Dict[str, str]:
    """Extrait des entités basiques depuis la requête et les index qui ont des résultats"""
    entities = {}
    query_lower = query.lower()
    
    # Entités géographiques
    zones = ["cocody", "yopougon", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville", "angré"]
    for zone in zones:
        if zone in query_lower:
            entities["zone"] = zone.title()
            break
    
    # Entités produits (basiques)
    produits = ["casque", "couche", "smartphone", "ordinateur", "paquet"]
    for produit in produits:
        if produit in query_lower:
            entities["produit"] = produit
            break
    
    # Entités couleurs
    couleurs = ["rouge", "bleu", "noir", "blanc", "vert", "jaune", "gris"]
    for couleur in couleurs:
        if couleur in query_lower:
            entities["couleur"] = couleur
            break
    
    # Entités depuis les index qui ont des résultats
    active_indexes = [idx for idx, docs in results_by_index.items() if len(docs) >= 1]
    if active_indexes:
        entities["active_indexes"] = "|".join([idx.split('_')[0] for idx in active_indexes])
    
    return entities

if __name__ == "__main__":
    # Test du système
    async def test_semantic_cache():
        print("🚀 TEST DU CACHE SÉMANTIQUE RÉVOLUTIONNAIRE")
        print("=" * 60)
        
        cache = get_semantic_intent_cache()
        
        # Test 1: Stocker une réponse
        intent_sig = IntentSignature(
            primary_intent="PRIX_LIVRAISON",
            secondary_intents=["ZONE_GEOGRAPHIQUE"],
            entities={"zone": "Cocody", "type": "livraison"},
            context_hash="test123",
            confidence_score=0.95
        )
        
        await cache.store_response(
            query="Combien coûte la livraison à Cocody ?",
            response="La livraison à Cocody coûte 1500 FCFA.",
            intent_signature=intent_sig,
            conversation_history="L'utilisateur demande des informations sur la livraison."
        )
        
        # Test 2: Rechercher avec une formulation différente
        result = await cache.get_cached_response(
            query="Quel est le tarif pour envoyer à Cocody ?",
            intent_signature=intent_sig,
            conversation_history="L'utilisateur s'intéresse aux coûts de livraison."
        )
        
        if result:
            response, confidence = result
            print(f"✅ Cache HIT: {response} (confiance: {confidence:.3f})")
        else:
            print("❌ Cache MISS")
        
        # Afficher les statistiques
        stats = cache.get_stats()
        print(f"\n📊 Statistiques:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    # Exécuter le test
    asyncio.run(test_semantic_cache())
