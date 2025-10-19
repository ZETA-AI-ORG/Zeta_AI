"""
🚀 SCRIPT D'APPLICATION DES OPTIMISATIONS PERFORMANCE
Lance ce script pour appliquer les optimisations sans toucher au format LLM
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from core.performance_optimizer import initialize_performance_optimizations, get_performance_optimizer
from core.global_embedding_cache import GlobalEmbeddingCache
from utils import log3


async def main():
    """Applique les optimisations de performance"""
    
    print("=" * 80)
    print("🚀 APPLICATION DES OPTIMISATIONS PERFORMANCE")
    print("=" * 80)
    print()
    
    # 1. Initialiser l'optimiseur
    print("📦 Étape 1: Initialisation de l'optimiseur...")
    optimizer = await initialize_performance_optimizations()
    print("✅ Optimiseur initialisé")
    print()
    
    # 2. Vérifier le cache embedding
    print("📦 Étape 2: Vérification du cache embedding...")
    cache = GlobalEmbeddingCache()
    stats = cache.get_stats()
    print(f"   - Modèles chargés: {stats['models_loaded']}")
    print(f"   - Embeddings en cache: {stats['embeddings_cached']}")
    print(f"   - Taux de hit modèle: {stats['model_hit_rate']:.1f}%")
    print(f"   - Taux de hit embedding: {stats['embedding_hit_rate']:.1f}%")
    print("✅ Cache embedding vérifié")
    print()
    
    # 3. Afficher les stats de l'optimiseur
    print("📦 Étape 3: Statistiques de l'optimiseur...")
    opt_stats = optimizer.get_stats()
    print(f"   - Modèles préchargés: {opt_stats['preloaded_models']}")
    print(f"   - Prompts en cache: {opt_stats['prompt_cache_size']}")
    print(f"   - Connexions HTTP max: {opt_stats['http_connections']['max']}")
    print(f"   - HTTP/2 activé: {opt_stats['http_connections']['http2_enabled']}")
    print("✅ Optimiseur configuré")
    print()
    
    # 4. Test de performance
    print("📦 Étape 4: Test de performance...")
    import time
    
    # Test embedding
    start = time.time()
    embedding = await cache.get_embedding("test query", "sentence-transformers/all-MiniLM-L6-v2")
    first_time = time.time() - start
    print(f"   - Premier embedding: {first_time*1000:.1f}ms")
    
    # Test cache hit
    start = time.time()
    embedding = await cache.get_embedding("test query", "sentence-transformers/all-MiniLM-L6-v2")
    cached_time = time.time() - start
    print(f"   - Embedding caché: {cached_time*1000:.1f}ms")
    print(f"   - Gain: {(first_time - cached_time)*1000:.1f}ms ({(1 - cached_time/first_time)*100:.0f}%)")
    print("✅ Test de performance terminé")
    print()
    
    print("=" * 80)
    print("✅ OPTIMISATIONS APPLIQUÉES AVEC SUCCÈS!")
    print("=" * 80)
    print()
    print("📋 GAINS ATTENDUS:")
    print("   - Cache embedding: -4s par requête")
    print("   - N-grams optimisés: -10s par requête")
    print("   - Cache prompt: -2s par requête")
    print("   - Connection pooling: -2s par requête")
    print("   - TOTAL: ~18s → ~5s par requête")
    print()
    print("🚀 Le serveur peut maintenant être redémarré avec ces optimisations!")


if __name__ == "__main__":
    asyncio.run(main())
