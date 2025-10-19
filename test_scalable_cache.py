#!/usr/bin/env python3
"""
🧪 TEST DU CACHE SÉMANTIQUE SCALABLE
Valide l'isolation par company_id
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

async def test_cache_isolation():
    """Test principal : isolation entre companies"""
    
    print("🧪 TEST CACHE SÉMANTIQUE SCALABLE")
    print("="*60)
    
    from core.scalable_semantic_cache import get_scalable_cache
    
    cache = get_scalable_cache()
    
    # SCÉNARIO: 2 companies différentes, même question, réponses différentes
    
    print("\n1️⃣ Company A (Côte d'Ivoire) stocke une réponse...")
    await cache.store_response(
        query="Quel est le prix de livraison ?",
        response="La livraison coûte 1.500 FCFA à Abidjan",
        company_id="company_cote_ivoire_A"
    )
    print("   ✅ Réponse stockée: 1.500 FCFA")
    
    print("\n2️⃣ Company B (France) stocke MÊME question, réponse différente...")
    await cache.store_response(
        query="Quel est le prix de livraison ?",
        response="La livraison coûte 15 EUR en France",
        company_id="company_france_B"
    )
    print("   ✅ Réponse stockée: 15 EUR")
    
    print("\n3️⃣ Company A récupère sa réponse...")
    result_A = await cache.get_cached_response(
        query="Prix de livraison ?",
        company_id="company_cote_ivoire_A"
    )
    
    if result_A:
        response, confidence = result_A
        print(f"   ✅ Trouvé: {response}")
        print(f"   🎯 Confiance: {confidence:.3f}")
        
        if "1.500 FCFA" in response:
            print("   ✅ CORRECT: Réponse de Company A (Côte d'Ivoire)")
        else:
            print("   ❌ ERREUR: Mauvaise réponse !")
    else:
        print("   ❌ Pas trouvé")
    
    print("\n4️⃣ Company B récupère sa réponse...")
    result_B = await cache.get_cached_response(
        query="Prix de livraison ?",
        company_id="company_france_B"
    )
    
    if result_B:
        response, confidence = result_B
        print(f"   ✅ Trouvé: {response}")
        print(f"   🎯 Confiance: {confidence:.3f}")
        
        if "15 EUR" in response:
            print("   ✅ CORRECT: Réponse de Company B (France)")
        else:
            print("   ❌ ERREUR: Mauvaise réponse !")
    else:
        print("   ❌ Pas trouvé")
    
    # Test pollution croisée
    print("\n5️⃣ Test pollution : Company A reçoit-elle réponse de Company B ?...")
    result_pollution = await cache.get_cached_response(
        query="Quel est le prix de livraison ?",
        company_id="company_cote_ivoire_A"
    )
    
    if result_pollution:
        response, _ = result_pollution
        if "15 EUR" in response:
            print("   ❌ POLLUTION DÉTECTÉE ! Company A a reçu réponse de Company B")
            print("   ❌ CACHE NON ISOLÉ !")
        elif "1.500 FCFA" in response:
            print("   ✅ PAS DE POLLUTION : Company A reçoit sa propre réponse")
            print("   ✅ CACHE BIEN ISOLÉ !")
    
    # Stats par company
    print("\n6️⃣ Stats par company...")
    stats_A = cache.get_company_stats("company_cote_ivoire_A")
    stats_B = cache.get_company_stats("company_france_B")
    
    print(f"\n   Company A (Côte d'Ivoire):")
    print(f"      • Requêtes: {stats_A['total_queries']}")
    print(f"      • Hits: {stats_A['cache_hits']}")
    print(f"      • Hit rate: {stats_A['hit_rate_percent']:.1f}%")
    print(f"      • Cache size: {stats_A['cache_size']}")
    
    print(f"\n   Company B (France):")
    print(f"      • Requêtes: {stats_B['total_queries']}")
    print(f"      • Hits: {stats_B['cache_hits']}")
    print(f"      • Hit rate: {stats_B['hit_rate_percent']:.1f}%")
    print(f"      • Cache size: {stats_B['cache_size']}")
    
    # Stats globales
    print("\n7️⃣ Stats globales...")
    global_stats = cache.get_global_stats()
    print(f"   • Total companies: {global_stats['total_companies']}")
    print(f"   • Total entries: {global_stats['total_entries']}")
    print(f"   • Hit rate global: {global_stats['global_hit_rate_percent']:.1f}%")
    
    print("\n" + "="*60)
    
    # Validation
    if result_A and result_B:
        if "1.500 FCFA" in result_A[0] and "15 EUR" in result_B[0]:
            print("✅ TEST RÉUSSI : CACHE PARFAITEMENT ISOLÉ PAR COMPANY")
            return True
        else:
            print("❌ TEST ÉCHOUÉ : POLLUTION ENTRE COMPANIES")
            return False
    else:
        print("⚠️ TEST INCOMPLET : Certaines réponses non trouvées")
        return False

async def test_scalability():
    """Test scalabilité avec plusieurs companies"""
    
    print("\n\n🔥 TEST SCALABILITÉ (10 COMPANIES)")
    print("="*60)
    
    from core.scalable_semantic_cache import get_scalable_cache
    
    cache = get_scalable_cache()
    
    # Créer 10 companies avec données différentes
    companies = [
        ("company_france", "15 EUR", "France"),
        ("company_usa", "20 USD", "USA"),
        ("company_uk", "12 GBP", "UK"),
        ("company_ci", "1500 FCFA", "Côte d'Ivoire"),
        ("company_senegal", "2000 FCFA", "Sénégal"),
        ("company_maroc", "50 MAD", "Maroc"),
        ("company_tunisie", "30 TND", "Tunisie"),
        ("company_canada", "25 CAD", "Canada"),
        ("company_suisse", "18 CHF", "Suisse"),
        ("company_belgique", "14 EUR", "Belgique"),
    ]
    
    # Stocker pour chaque company
    print("\n1️⃣ Stockage pour 10 companies...")
    for company_id, price, country in companies:
        await cache.store_response(
            query="Prix de livraison ?",
            response=f"La livraison coûte {price} en {country}",
            company_id=company_id
        )
    print(f"   ✅ {len(companies)} companies configurées")
    
    # Récupérer pour chaque company
    print("\n2️⃣ Vérification isolation...")
    errors = 0
    for company_id, expected_price, country in companies:
        result = await cache.get_cached_response(
            query="Quel est le prix de livraison ?",
            company_id=company_id
        )
        
        if result:
            response, confidence = result
            if expected_price in response:
                print(f"   ✅ {country}: {expected_price} (OK)")
            else:
                print(f"   ❌ {country}: Attendu {expected_price}, reçu: {response}")
                errors += 1
        else:
            print(f"   ❌ {country}: Pas de réponse")
            errors += 1
    
    # Stats finales
    print("\n3️⃣ Stats finales...")
    global_stats = cache.get_global_stats()
    print(f"   • Companies actives: {global_stats['total_companies']}")
    print(f"   • Total entrées: {global_stats['total_entries']}")
    print(f"   • Hit rate: {global_stats['global_hit_rate_percent']:.1f}%")
    
    print("\n" + "="*60)
    if errors == 0:
        print("✅ SCALABILITÉ VALIDÉE : 10 companies isolées parfaitement")
        return True
    else:
        print(f"❌ SCALABILITÉ ÉCHOUÉE : {errors} erreurs")
        return False

async def main():
    """Point d'entrée"""
    
    # Test 1: Isolation
    success1 = await test_cache_isolation()
    
    # Test 2: Scalabilité
    success2 = await test_scalability()
    
    print("\n\n" + "="*60)
    print("📊 RÉSULTATS FINAUX")
    print("="*60)
    print(f"Test isolation: {'✅ RÉUSSI' if success1 else '❌ ÉCHOUÉ'}")
    print(f"Test scalabilité: {'✅ RÉUSSI' if success2 else '❌ ÉCHOUÉ'}")
    
    if success1 and success2:
        print("\n🎉 CACHE SÉMANTIQUE SCALABLE 100% FONCTIONNEL")
        print("✅ Prêt pour production avec ∞ entreprises")
    else:
        print("\n⚠️ Problèmes détectés, à corriger")

if __name__ == "__main__":
    asyncio.run(main())
