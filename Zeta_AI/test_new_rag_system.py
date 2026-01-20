#!/usr/bin/env python3
"""
🧪 TEST DU NOUVEAU SYSTÈME RAG UNIVERSEL
Architecture séquentielle MeiliSearch → Supabase avec preprocessing avancé
"""

import asyncio
import time
import sys
import os

# Ajouter le répertoire racine au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.universal_rag_engine import get_universal_rag_response

async def test_new_rag_system(company_id=None, user_id=None, company_name=None):
    """Test complet du nouveau système RAG - VRAIMENT DYNAMIQUE"""
    
    print("🧪 TEST DU NOUVEAU SYSTÈME RAG UNIVERSEL")
    print("=" * 60)
    
    # Configuration DYNAMIQUE - IDs passés en paramètres
    default_company_id = company_id or "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    default_user_id = user_id or "testuser129"
    default_company_name = company_name or "Rue du Gros"
    
    print(f"🏢 Company ID: {default_company_id}")
    print(f"👤 User ID: {default_user_id}")
    print(f"🏪 Company Name: {default_company_name}")
    print("-" * 60)
    
    # Questions de test - IDs dynamiques
    test_cases = [
        {
            "name": "Question complexe avec preprocessing",
            "message": "Bonjour, je suis un parent de jumeaux de 8 mois et 13 mois qui pèsent respectivement 10kg et 16kg. quelle est la taille de couches recommandée pour chacun de mes bébés ?",
        },
        {
            "name": "Question simple produit",
            "message": "Que vendez-vous ?",
        },
        {
            "name": "Question avec stop words",
            "message": "Bonjour, est-ce que vous avez des casques rouges en stock ?",
        },
        {
            "name": "Question livraison spécifique",
            "message": "Livraison Cocody combien ça coûte ?",
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test_case['name']}")
        print(f"📝 Question: {test_case['message']}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Test du nouveau système RAG avec IDs dynamiques
            result = await get_universal_rag_response(
                message=test_case['message'],
                company_id=default_company_id,
                user_id=default_user_id,
                company_name=default_company_name
            )
            
            processing_time = time.time() - start_time
            
            # Affichage des résultats
            print(f"✅ SUCCÈS - Temps: {processing_time:.2f}s")
            print(f"🤖 Réponse: {result['response'][:200]}...")
            print(f"📊 Confiance: {result['confidence']:.2f}")
            print(f"📄 Documents trouvés: {result['documents_found']}")
            print(f"🔍 Méthode: {result['search_method']}")
            print(f"⏱️  Temps traitement: {result['processing_time_ms']:.0f}ms")
            
            results.append({
                'test': test_case['name'],
                'success': True,
                'time': processing_time,
                'confidence': result['confidence'],
                'documents_found': result['documents_found'],
                'method': result['search_method']
            })
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ ERREUR - Temps: {processing_time:.2f}s")
            print(f"💥 Exception: {str(e)}")
            
            results.append({
                'test': test_case['name'],
                'success': False,
                'time': processing_time,
                'error': str(e)
            })
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    total_tests = len(results)
    avg_time = sum(r['time'] for r in results) / len(results)
    
    print(f"✅ Tests réussis: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
    print(f"⏱️  Temps moyen: {avg_time:.2f}s")
    
    if success_count > 0:
        successful_results = [r for r in results if r['success']]
        avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
        print(f"📊 Confiance moyenne: {avg_confidence:.2f}")
        
        methods_used = [r['method'] for r in successful_results]
        meili_count = methods_used.count('meilisearch')
        supabase_count = methods_used.count('supabase_fallback')
        
        print(f"🔍 MeiliSearch utilisé: {meili_count} fois")
        print(f"🔄 Supabase fallback: {supabase_count} fois")
    
    # Détails par test
    print(f"\n📋 DÉTAILS PAR TEST:")
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['test']}: {result['time']:.2f}s")
        if not result['success']:
            print(f"   💥 {result['error']}")
    
    return results

if __name__ == "__main__":
    import sys
    
    # Paramètres dynamiques depuis la ligne de commande
    company_id = sys.argv[1] if len(sys.argv) > 1 else None
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    company_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("🚀 Démarrage du test du nouveau système RAG...")
    if company_id:
        print(f"📋 Utilisation des paramètres: company_id={company_id}, user_id={user_id}")
    else:
        print("📋 Utilisation des valeurs par défaut")
    
    results = asyncio.run(test_new_rag_system(company_id, user_id, company_name))
    print("\n🏁 Tests terminés !")
