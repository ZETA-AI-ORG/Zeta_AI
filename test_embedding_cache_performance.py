"""
🚀 TEST DE PERFORMANCE DU CACHE GLOBAL D'EMBEDDINGS
Vérifie que le nouveau système élimine les rechargements de modèles
"""
import asyncio
import time
from typing import List, Dict
import statistics

from core.global_embedding_cache import get_global_embedding_cache, get_cached_embedding, get_cached_model
from utils import log3


async def test_model_loading_performance():
    """Test de performance du chargement de modèles"""
    log3("[PERFORMANCE_TEST]", "🚀 Début test performance chargement modèles")
    
    cache = get_global_embedding_cache()
    model_name = "sentence-transformers/all-mpnet-base-v2"
    
    # Test 1: Premier chargement (devrait être lent)
    start_time = time.time()
    model1 = await get_cached_model(model_name)
    first_load_time = time.time() - start_time
    log3("[PERFORMANCE_TEST]", f"⏱️ Premier chargement: {first_load_time:.3f}s")
    
    # Test 2: Rechargements multiples (devraient être rapides)
    reload_times = []
    for i in range(5):
        start_time = time.time()
        model2 = await get_cached_model(model_name)
        reload_time = time.time() - start_time
        reload_times.append(reload_time)
        log3("[PERFORMANCE_TEST]", f"⏱️ Rechargement {i+1}: {reload_time:.3f}s")
        
        # Vérification que c'est la même instance
        assert model1 is model2, f"Échec: instances différentes au rechargement {i+1}"
    
    avg_reload_time = statistics.mean(reload_times)
    max_reload_time = max(reload_times)
    
    log3("[PERFORMANCE_TEST]", f"📊 Statistiques chargement modèle:")
    log3("[PERFORMANCE_TEST]", f"   Premier chargement: {first_load_time:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Rechargement moyen: {avg_reload_time:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Rechargement max: {max_reload_time:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Amélioration: {(first_load_time/avg_reload_time):.1f}x plus rapide")
    
    return {
        'first_load_time': first_load_time,
        'avg_reload_time': avg_reload_time,
        'max_reload_time': max_reload_time,
        'speedup_factor': first_load_time / avg_reload_time
    }


async def test_embedding_generation_performance():
    """Test de performance de génération d'embeddings"""
    log3("[PERFORMANCE_TEST]", "🚀 Début test performance génération embeddings")
    
    test_texts = [
        "Quels sont vos casques disponibles ?",
        "Livraison à Cocody combien ça coûte ?",
        "Je cherche un casque rouge",
        "Paiement par Wave possible ?",
        "Contact WhatsApp de l'entreprise"
    ]
    
    # Test 1: Première génération (cache miss)
    first_gen_times = []
    first_embeddings = {}
    for text in test_texts:
        start_time = time.time()
        embedding = await get_cached_embedding(text)
        gen_time = time.time() - start_time
        first_gen_times.append(gen_time)
        first_embeddings[text] = embedding
        log3("[PERFORMANCE_TEST]", f"⏱️ Première génération '{text[:30]}...': {gen_time:.3f}s")
    
    # Test 2: Régénération (cache hit)
    cache_hit_times = []
    for text in test_texts:
        start_time = time.time()
        embedding = await get_cached_embedding(text)
        hit_time = time.time() - start_time
        cache_hit_times.append(hit_time)
        log3("[PERFORMANCE_TEST]", f"⏱️ Cache hit '{text[:30]}...': {hit_time:.3f}s")
        
        # Vérification que les embeddings sont identiques
        assert first_embeddings[text] == embedding, f"Échec: embeddings différents pour '{text}'"
    
    avg_first_gen = statistics.mean(first_gen_times)
    avg_cache_hit = statistics.mean(cache_hit_times)
    
    log3("[PERFORMANCE_TEST]", f"📊 Statistiques génération embeddings:")
    log3("[PERFORMANCE_TEST]", f"   Première génération moyenne: {avg_first_gen:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Cache hit moyen: {avg_cache_hit:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Amélioration: {(avg_first_gen/avg_cache_hit):.1f}x plus rapide")
    
    return {
        'avg_first_gen': avg_first_gen,
        'avg_cache_hit': avg_cache_hit,
        'cache_speedup': avg_first_gen / avg_cache_hit
    }


async def test_concurrent_access():
    """Test d'accès concurrent au cache"""
    log3("[PERFORMANCE_TEST]", "🚀 Début test accès concurrent")
    
    async def worker_task(worker_id: int, text: str):
        """Tâche worker pour test concurrent"""
        start_time = time.time()
        embedding = await get_cached_embedding(f"{text} worker_{worker_id}")
        duration = time.time() - start_time
        return {
            'worker_id': worker_id,
            'duration': duration,
            'embedding_size': len(embedding)
        }
    
    # Lancement de 10 workers en parallèle
    tasks = []
    for i in range(10):
        task = worker_task(i, "Test concurrent access")
        tasks.append(task)
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    durations = [r['duration'] for r in results]
    avg_duration = statistics.mean(durations)
    max_duration = max(durations)
    
    log3("[PERFORMANCE_TEST]", f"📊 Statistiques accès concurrent:")
    log3("[PERFORMANCE_TEST]", f"   Temps total: {total_time:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Durée moyenne par worker: {avg_duration:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Durée max par worker: {max_duration:.3f}s")
    log3("[PERFORMANCE_TEST]", f"   Workers réussis: {len(results)}/10")
    
    return {
        'total_time': total_time,
        'avg_worker_duration': avg_duration,
        'max_worker_duration': max_duration,
        'success_count': len(results)
    }


async def test_cache_statistics():
    """Test des statistiques du cache"""
    log3("[PERFORMANCE_TEST]", "🚀 Test statistiques du cache")
    
    cache = get_global_embedding_cache()
    
    # Génération de quelques embeddings pour avoir des stats
    test_queries = [
        "Casque moto rouge disponible",
        "Livraison Yopougon prix",
        "Paiement mobile money",
        "Support client WhatsApp"
    ]
    
    for query in test_queries:
        await get_cached_embedding(query)
    
    stats = cache.get_stats()
    
    log3("[PERFORMANCE_TEST]", f"📊 Statistiques du cache global:")
    log3("[PERFORMANCE_TEST]", f"   Modèles chargés: {stats['models_loaded']}")
    log3("[PERFORMANCE_TEST]", f"   Embeddings en cache: {stats['embeddings_cached']}")
    log3("[PERFORMANCE_TEST]", f"   Taux hit modèles: {stats['model_hit_rate']:.1f}%")
    log3("[PERFORMANCE_TEST]", f"   Taux hit embeddings: {stats['embedding_hit_rate']:.1f}%")
    log3("[PERFORMANCE_TEST]", f"   Cache disque activé: {stats['disk_cache_enabled']}")
    log3("[PERFORMANCE_TEST]", f"   Répertoire cache: {stats['cache_dir']}")
    
    return stats


async def run_complete_performance_test():
    """Exécute tous les tests de performance"""
    log3("[PERFORMANCE_TEST]", "🎯 DÉBUT TEST COMPLET DE PERFORMANCE DU CACHE GLOBAL")
    
    start_time = time.time()
    
    try:
        # Test 1: Performance chargement modèles
        model_results = await test_model_loading_performance()
        
        # Test 2: Performance génération embeddings
        embedding_results = await test_embedding_generation_performance()
        
        # Test 3: Accès concurrent
        concurrent_results = await test_concurrent_access()
        
        # Test 4: Statistiques
        cache_stats = await test_cache_statistics()
        
        total_time = time.time() - start_time
        
        # Résumé final
        log3("[PERFORMANCE_TEST]", "🏆 RÉSUMÉ FINAL DES PERFORMANCES:")
        log3("[PERFORMANCE_TEST]", f"⏱️ Temps total des tests: {total_time:.2f}s")
        log3("[PERFORMANCE_TEST]", f"🚀 Amélioration chargement modèle: {model_results['speedup_factor']:.1f}x")
        log3("[PERFORMANCE_TEST]", f"⚡ Amélioration cache embeddings: {embedding_results['cache_speedup']:.1f}x")
        log3("[PERFORMANCE_TEST]", f"🔄 Accès concurrent réussi: {concurrent_results['success_count']}/10")
        log3("[PERFORMANCE_TEST]", f"📈 Taux hit embeddings: {cache_stats['embedding_hit_rate']:.1f}%")
        
        # Validation des performances
        success = True
        if model_results['avg_reload_time'] > 0.1:  # Rechargement devrait être < 100ms
            log3("[PERFORMANCE_TEST]", "❌ ÉCHEC: Rechargement modèle trop lent")
            success = False
        
        if embedding_results['avg_cache_hit'] > 0.01:  # Cache hit devrait être < 10ms
            log3("[PERFORMANCE_TEST]", "❌ ÉCHEC: Cache hit embeddings trop lent")
            success = False
        
        if concurrent_results['success_count'] < 10:
            log3("[PERFORMANCE_TEST]", "❌ ÉCHEC: Accès concurrent incomplet")
            success = False
        
        if success:
            log3("[PERFORMANCE_TEST]", "✅ SUCCÈS: Tous les tests de performance réussis!")
        else:
            log3("[PERFORMANCE_TEST]", "⚠️ ATTENTION: Certains tests ont échoué")
        
        return {
            'success': success,
            'total_time': total_time,
            'model_performance': model_results,
            'embedding_performance': embedding_results,
            'concurrent_performance': concurrent_results,
            'cache_statistics': cache_stats
        }
        
    except Exception as e:
        log3("[PERFORMANCE_TEST]", f"❌ ERREUR lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    asyncio.run(run_complete_performance_test())
