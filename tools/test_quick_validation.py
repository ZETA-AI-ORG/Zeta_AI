#!/usr/bin/env python3
"""
🔥 TEST RAPIDE DE VALIDATION - CORRECTION MÉMOIRE
Test minimal pour vérifier que la correction fonctionne

OBJECTIF: Valider que la mémoire conversationnelle fonctionne maintenant
"""

import asyncio
import sys
import time
import os
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 🎯 TEST MINIMAL : 5 ÉCHANGES CRITIQUES
QUICK_TEST = [
    {
        "user_message": "Bonjour, je cherche des couches pour mon bébé de 9kg",
        "expected_memory": ["bébé", "9kg", "couches"],
        "delay": 3.0
    },
    {
        "user_message": "Mon budget est de 20000 FCFA maximum",
        "expected_memory": ["budget", "20000 FCFA"],
        "delay": 3.0
    },
    {
        "user_message": "Je veux 2 paquets taille 3",
        "expected_memory": ["2 paquets", "taille 3"],
        "delay": 3.0
    },
    {
        "user_message": "Livraison à Cocody s'il vous plaît",
        "expected_memory": ["livraison", "Cocody"],
        "delay": 3.0
    },
    {
        "user_message": "Rappelez-moi combien pèse mon bébé ?",
        "expected_memory": ["TEST_MÉMOIRE", "9kg"],
        "delay": 3.0
    }
]

async def run_quick_validation():
    """Test rapide de validation"""
    print(f"🔥 TEST RAPIDE DE VALIDATION - CORRECTION MÉMOIRE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(QUICK_TEST)} échanges de validation")
    print(f"{'='*60}")
    
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()
    
    # Paramètres de test
    COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "quick_validation_user"
    
    success_count = 0
    total_tests = len(QUICK_TEST)
    
    for i, test_data in enumerate(QUICK_TEST, 1):
        user_message = test_data["user_message"]
        expected_memory = test_data["expected_memory"]
        delay = test_data.get("delay", 3.0)
        
        print(f"\n🔥 TEST {i}/{total_tests}")
        print(f"👤 USER: {user_message}")
        
        start_time = time.time()
        try:
            # Recherche et génération
            search_results = await rag.search_sequential_sources(user_message, COMPANY_ID)
            # Injection robuste de l'historique utilisateur dans search_results
            search_results['conversation_history'] = user_message if 'conversation_history' not in search_results else search_results['conversation_history']
            response = await rag.generate_response(
                user_message, search_results, COMPANY_ID, COMPANY_NAME, USER_ID
            )
            
            response_time = time.time() - start_time
            
            # Vérifier si réponse non vide
            if response and len(response.strip()) > 0:
                print(f"🤖 GAMMA: {response[:80]}{'...' if len(response) > 80 else ''}")
                print(f"⏱️  Temps: {response_time:.2f}s")
                
                # Test de mémoire
                found_elements = []
                response_lower = response.lower()
                
                for expected in expected_memory:
                    if expected.lower() in response_lower:
                        found_elements.append(expected)
                
                coherence = len(found_elements) / len(expected_memory) * 100
                
                print(f"🧠 Cohérence: {coherence:.1f}%", end="")
                if "TEST_MÉMOIRE" in expected_memory:
                    print(" [CRITIQUE]", end="")
                
                if coherence >= 50:
                    print(" ✅")
                    success_count += 1
                else:
                    print(f" ❌ - Manque: {[e for e in expected_memory if e not in found_elements]}")
                    
            else:
                print(f"❌ RÉPONSE VIDE - Temps: {response_time:.2f}s")
            
        except Exception as e:
            response_time = time.time() - start_time
            print(f"❌ ERREUR: {str(e)[:60]}... - Temps: {response_time:.2f}s")
        
        # Délai entre tests
        if i < total_tests:
            print(f"⏳ Attente {delay}s...")
            await asyncio.sleep(delay)
    
    # Résultat final
    success_rate = (success_count / total_tests) * 100
    print(f"\n{'='*60}")
    print(f"🎯 RÉSULTAT VALIDATION:")
    print(f"   • Tests réussis: {success_count}/{total_tests}")
    print(f"   • Taux de succès: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("   🟢 CORRECTION RÉUSSIE - Système fonctionnel")
    elif success_rate >= 60:
        print("   🟡 AMÉLIORATION - Nécessite ajustements")
    else:
        print("   🔴 ÉCHEC - Problèmes persistent")
    
    return success_rate

if __name__ == "__main__":
    asyncio.run(run_quick_validation())
