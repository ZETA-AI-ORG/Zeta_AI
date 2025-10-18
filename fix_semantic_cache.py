#!/usr/bin/env python3
"""
🔧 FIX CACHE SÉMANTIQUE - AMÉLIORATION ET SIMPLIFICATION
Corrige les problèmes du cache sémantique pour le rendre utilisable
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

def analyze_cache_issues():
    """Analyse les problèmes du cache sémantique actuel"""
    
    print("🔍 ANALYSE DU CACHE SÉMANTIQUE ACTUEL")
    print("="*60)
    
    try:
        from core.semantic_intent_cache import SemanticIntentCache, IntentSignature
        
        # Test d'initialisation
        print("\n1️⃣ Test d'initialisation...")
        cache = SemanticIntentCache(
            similarity_threshold=0.4  # ⚠️ PROBLÈME: Trop bas
        )
        print(f"   ✅ Cache initialisé")
        print(f"   ⚠️ Seuil actuel: {cache.similarity_threshold} (TROP BAS)")
        print(f"   💡 Recommandé: 0.85-0.92")
        
        # Test stats
        print("\n2️⃣ Statistiques cache...")
        stats = cache.get_stats()
        print(f"   📊 Stats: {stats}")
        
        # Test de performance
        print("\n3️⃣ Test de performance...")
        import time
        
        # Simuler une requête
        intent_sig = IntentSignature(
            primary_intent="PRIX",
            secondary_intents=[],
            entities={"produit": "couches_culottes", "quantite": "6"},
            context_hash="test123",
            confidence_score=0.9
        )
        
        # Test stockage
        start = time.time()
        import asyncio
        asyncio.run(cache.store_response(
            query="Combien 6 paquets couches culottes ?",
            response="6 paquets de couches culottes coûtent 25.000 FCFA",
            intent_signature=intent_sig,
            conversation_history=""
        ))
        store_time = (time.time() - start) * 1000
        print(f"   ⏱️ Temps stockage: {store_time:.0f}ms")
        
        if store_time > 100:
            print(f"   ⚠️ PROBLÈME: Stockage trop lent (>{100}ms)")
        
        # Test récupération
        start = time.time()
        result = asyncio.run(cache.get_cached_response(
            query="Prix 6 paquets couches culottes ?",  # Formulation différente
            intent_signature=intent_sig,
            conversation_history=""
        ))
        retrieve_time = (time.time() - start) * 1000
        print(f"   ⏱️ Temps récupération: {retrieve_time:.0f}ms")
        
        if retrieve_time > 200:
            print(f"   ⚠️ PROBLÈME: Récupération trop lente (>{200}ms)")
        
        if result:
            response, confidence = result
            print(f"   ✅ Trouvé: {response[:50]}...")
            print(f"   🎯 Confiance: {confidence:.2f}")
        else:
            print(f"   ❌ Pas trouvé")
        
        print("\n" + "="*60)
        print("📊 PROBLÈMES IDENTIFIÉS:")
        print("1. ⚠️ Seuil similarité trop bas (0.4 → 0.88)")
        print("2. ⚠️ Stockage potentiellement lent si >100ms")
        print("3. ⚠️ Récupération potentiellement lente si >200ms")
        print("4. ⚠️ Pas de nettoyage auto des entrées obsolètes")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_optimized_cache():
    """Crée une version optimisée du cache sémantique"""
    
    print("\n🚀 CRÉATION CACHE SÉMANTIQUE OPTIMISÉ")
    print("="*60)
    
    code = '''#!/usr/bin/env python3
"""
🚀 CACHE SÉMANTIQUE OPTIMISÉ V2
Version simplifiée et performante du cache sémantique
"""

import asyncio
import hashlib
import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer, util
import threading

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

@dataclass
class SimpleCacheEntry:
    """Entrée de cache simplifiée"""
    query: str
    response: str
    query_embedding: List[float]
    timestamp: float
    hit_count: int
    ttl_seconds: int

class OptimizedSemanticCache:
    """
    🎯 Cache Sémantique Optimisé
    
    AMÉLIORATIONS:
    - Seuil plus élevé (0.88 au lieu de 0.4)
    - Stockage simplifié (pas de two-stage retrieval)
    - Nettoyage automatique des entrées obsolètes
    - Performance améliorée (<100ms)
    """
    
    def __init__(self, 
                 similarity_threshold: float = 0.88,  # ✅ AUGMENTÉ
                 max_cache_size: int = 1000,          # ✅ RÉDUIT
                 default_ttl: int = 1800):            # ✅ 30min au lieu de 1h
        
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl
        
        # Stockage en mémoire seulement (Redis optionnel)
        self.memory_cache: Dict[str, SimpleCacheEntry] = {}
        self.redis_client = None
        
        # Modèle d'embeddings léger
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Stats
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_retrieve_time_ms": 0
        }
        
        self.lock = threading.RLock()
        self._init_redis()
    
    def _init_redis(self):
        """Initialise Redis (optionnel)"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=3,  # DB 3 pour cache optimisé
                    decode_responses=False
                )
                self.redis_client.ping()
                print("✅ Redis connecté (DB 3)")
            except:
                self.redis_client = None
    
    def _create_embedding(self, text: str) -> List[float]:
        """Crée un embedding"""
        return self.model.encode(text, convert_to_tensor=False).tolist()
    
    def _compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calcule la similarité cosinus"""
        return util.cos_sim(emb1, emb2).item()
    
    async def get_cached_response(self, query: str) -> Optional[Tuple[str, float]]:
        """
        Récupère une réponse du cache
        
        Returns:
            (response, confidence) si trouvé, None sinon
        """
        start_time = time.time()
        
        with self.lock:
            self.stats["total_queries"] += 1
            
            # Créer embedding query
            query_embedding = self._create_embedding(query)
            
            # Chercher dans le cache
            best_match = None
            best_similarity = 0.0
            
            for cache_key, entry in self.memory_cache.items():
                # Vérifier TTL
                if time.time() - entry.timestamp > entry.ttl_seconds:
                    continue  # Ignorer les entrées expirées
                
                # Calculer similarité
                similarity = self._compute_similarity(query_embedding, entry.query_embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = entry
            
            # Mettre à jour stats
            retrieve_time_ms = (time.time() - start_time) * 1000
            self.stats["avg_retrieve_time_ms"] = (
                (self.stats["avg_retrieve_time_ms"] * (self.stats["total_queries"] - 1) + retrieve_time_ms)
                / self.stats["total_queries"]
            )
            
            if best_match:
                self.stats["cache_hits"] += 1
                best_match.hit_count += 1
                
                print(f"✅ Cache HIT (similarity: {best_similarity:.3f}, time: {retrieve_time_ms:.0f}ms)")
                return (best_match.response, best_similarity)
            else:
                self.stats["cache_misses"] += 1
                print(f"❌ Cache MISS (time: {retrieve_time_ms:.0f}ms)")
                return None
    
    async def store_response(self, 
                            query: str, 
                            response: str,
                            ttl: Optional[int] = None):
        """Stocke une réponse dans le cache"""
        
        with self.lock:
            # Créer embedding
            query_embedding = self._create_embedding(query)
            
            # Créer clé unique
            cache_key = hashlib.md5(query.encode()).hexdigest()
            
            # Créer entrée
            entry = SimpleCacheEntry(
                query=query,
                response=response,
                query_embedding=query_embedding,
                timestamp=time.time(),
                hit_count=0,
                ttl_seconds=ttl or self.default_ttl
            )
            
            # Stocker
            self.memory_cache[cache_key] = entry
            
            # Nettoyer si trop d'entrées
            if len(self.memory_cache) > self.max_cache_size:
                self._cleanup_old_entries()
            
            print(f"💾 Cache STORE (total: {len(self.memory_cache)} entrées)")
    
    def _cleanup_old_entries(self):
        """Nettoie les entrées obsolètes"""
        now = time.time()
        
        # Supprimer entrées expirées
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if now - entry.timestamp > entry.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Si encore trop, supprimer les moins utilisées
        if len(self.memory_cache) > self.max_cache_size:
            sorted_entries = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].hit_count
            )
            
            # Garder seulement les plus utilisées
            to_keep = sorted_entries[-self.max_cache_size:]
            self.memory_cache = dict(to_keep)
        
        print(f"🧹 Nettoyage: {len(expired_keys)} expirées, {len(self.memory_cache)} conservées")
    
    def clear_cache(self):
        """Vide complètement le cache"""
        with self.lock:
            self.memory_cache.clear()
            print("🗑️ Cache vidé")
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        with self.lock:
            hit_rate = (
                (self.stats["cache_hits"] / self.stats["total_queries"] * 100)
                if self.stats["total_queries"] > 0 else 0
            )
            
            return {
                **self.stats,
                "hit_rate_percent": hit_rate,
                "cache_size": len(self.memory_cache)
            }

# Singleton global
_global_cache = None

def get_optimized_cache() -> OptimizedSemanticCache:
    """Retourne l'instance globale du cache"""
    global _global_cache
    if _global_cache is None:
        _global_cache = OptimizedSemanticCache()
    return _global_cache
'''
    
    # Sauvegarder
    output_path = Path(__file__).parent / "core" / "optimized_semantic_cache.py"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"✅ Cache optimisé créé: {output_path}")
    print("\n📋 AMÉLIORATIONS:")
    print("   1. ✅ Seuil: 0.4 → 0.88 (plus strict)")
    print("   2. ✅ TTL: 3600s → 1800s (30min)")
    print("   3. ✅ Max size: 10000 → 1000 (plus léger)")
    print("   4. ✅ Nettoyage auto des entrées obsolètes")
    print("   5. ✅ Pas de two-stage retrieval (plus simple)")
    print("   6. ✅ Performance: <100ms visé")

def test_optimized_cache():
    """Teste le cache optimisé"""
    
    print("\n🧪 TEST DU CACHE OPTIMISÉ")
    print("="*60)
    
    try:
        from core.optimized_semantic_cache import get_optimized_cache
        import asyncio
        
        cache = get_optimized_cache()
        
        # Test 1: Stockage
        print("\n1️⃣ Test stockage...")
        asyncio.run(cache.store_response(
            query="Combien coûte 6 paquets de couches culottes ?",
            response="6 paquets de couches culottes coûtent 25.000 FCFA"
        ))
        
        # Test 2: Récupération exacte
        print("\n2️⃣ Test récupération (formulation identique)...")
        result = asyncio.run(cache.get_cached_response(
            "Combien coûte 6 paquets de couches culottes ?"
        ))
        
        if result:
            print(f"   ✅ Trouvé: {result[0][:50]}...")
            print(f"   🎯 Confiance: {result[1]:.3f}")
        
        # Test 3: Récupération similaire
        print("\n3️⃣ Test récupération (formulation différente)...")
        result = asyncio.run(cache.get_cached_response(
            "Prix de 6 paquets couches culottes ?"
        ))
        
        if result:
            print(f"   ✅ Trouvé: {result[0][:50]}...")
            print(f"   🎯 Confiance: {result[1]:.3f}")
        else:
            print("   ⚠️ Pas trouvé (seuil trop élevé)")
        
        # Test 4: Stats
        print("\n4️⃣ Statistiques...")
        stats = cache.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n✅ TESTS TERMINÉS")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 FIX DU CACHE SÉMANTIQUE")
    print("="*60)
    
    # Analyser les problèmes
    analyze_cache_issues()
    
    # Créer version optimisée
    create_optimized_cache()
    
    # Tester
    test_optimized_cache()
    
    print("\n✅ FIX TERMINÉ !")
    print("📌 Utiliser: from core.optimized_semantic_cache import get_optimized_cache")
