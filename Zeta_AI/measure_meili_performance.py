#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 PHASE 2: MESURE PERFORMANCE MEILISEARCH
Script pour calibrer le timeout optimal
"""

import asyncio
import time
from typing import List, Dict
from database.vector_store_clean_v2 import search_all_indexes_parallel

# Queries de test représentatives
TEST_QUERIES = [
    # Queries produit (doivent réussir)
    "Prix lot 300 taille 4",
    "Couches bébé 8kg",
    "Lot 150 ou 300",
    "Taille 3 combien",
    "Prix couches",
    
    # Queries livraison (doivent réussir)
    "Livraison Cocody",
    "Frais livraison Yopougon",
    "Vous livrez à Abidjan",
    "Délai livraison",
    
    # Queries paiement (doivent réussir)
    "Paiement Wave",
    "Comment payer",
    "Orange Money",
    
    # Queries générales (peuvent échouer)
    "Bonjour",
    "Je veux commander",
    "C'est combien",
    "Vous livrez",
    "Merci"
]

COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"


async def measure_meilisearch_performance():
    """Mesure les temps de réponse MeiliSearch"""
    
    print("\n" + "="*80)
    print("📊 PHASE 2: MESURE PERFORMANCE MEILISEARCH")
    print("="*80 + "\n")
    
    results_success = []
    results_failure = []
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n🔍 Test {i}/{len(TEST_QUERIES)}: '{query}'")
        
        start = time.time()
        try:
            # ✅ Fonction correcte: search_all_indexes_parallel
            # Retourne une STRING formatée, pas JSON!
            context_string = await search_all_indexes_parallel(
                query=query,
                company_id=COMPANY_ID,
                limit=5
            )
            duration = time.time() - start
            
            # Compter les documents dans la string
            # Format: "DOCUMENT #1", "DOCUMENT #2", etc.
            docs_count = context_string.count("DOCUMENT #") if context_string else 0
            
            if docs_count > 0:
                # ✅ SUCCÈS
                results_success.append({
                    'query': query,
                    'duration': duration,
                    'docs_count': docs_count
                })
                print(f"  ✅ Succès: {duration:.3f}s | {docs_count} docs")
            else:
                # ❌ ÉCHEC (0 résultats)
                results_failure.append({
                    'query': query,
                    'duration': duration,
                    'docs_count': 0
                })
                print(f"  ❌ Échec: {duration:.3f}s | 0 docs")
        
        except Exception as e:
            duration = time.time() - start
            results_failure.append({
                'query': query,
                'duration': duration,
                'error': str(e)
            })
            print(f"  ❌ Erreur: {duration:.3f}s | {str(e)[:50]}")
    
    # ============================================================================
    # ANALYSE RÉSULTATS
    # ============================================================================
    
    print("\n" + "="*80)
    print("📊 RÉSULTATS ANALYSE")
    print("="*80 + "\n")
    
    if results_success:
        durations_success = [r['duration'] for r in results_success]
        avg_success = sum(durations_success) / len(durations_success)
        min_success = min(durations_success)
        max_success = max(durations_success)
        
        print(f"✅ REQUÊTES RÉUSSIES ({len(results_success)}/{len(TEST_QUERIES)}):")
        print(f"  ├─ Temps moyen: {avg_success:.3f}s")
        print(f"  ├─ Temps min: {min_success:.3f}s")
        print(f"  ├─ Temps max: {max_success:.3f}s")
        print(f"  └─ Médiane: {sorted(durations_success)[len(durations_success)//2]:.3f}s")
        
        # ✅ CALCUL TIMEOUT OPTIMAL
        # Formule: MAX + MARGE_SÉCURITÉ
        marge_securite = 0.5  # 500ms de marge
        timeout_optimal = max_success + marge_securite
        
        print(f"\n🎯 TIMEOUT OPTIMAL RECOMMANDÉ:")
        print(f"  ├─ Formule: MAX({max_success:.3f}s) + MARGE({marge_securite}s)")
        print(f"  └─ TIMEOUT: {timeout_optimal:.2f}s ✅")
        
        print(f"\n💡 CONFIGURATION À APPLIQUER:")
        print(f"  Dans core/parallel_search_engine.py:")
        print(f"  MEILISEARCH_TIMEOUT = {timeout_optimal:.2f}")
    
    else:
        print("❌ AUCUNE REQUÊTE RÉUSSIE!")
        print("⚠️ Problème avec MeiliSearch - Vérifier configuration")
    
    if results_failure:
        durations_failure = [r['duration'] for r in results_failure if 'duration' in r]
        if durations_failure:
            avg_failure = sum(durations_failure) / len(durations_failure)
            print(f"\n❌ REQUÊTES ÉCHOUÉES ({len(results_failure)}/{len(TEST_QUERIES)}):")
            print(f"  └─ Temps moyen: {avg_failure:.3f}s")
    
    print("\n" + "="*80)
    print("✅ MESURE TERMINÉE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(measure_meilisearch_performance())
