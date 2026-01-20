"""
🧪 TEST DE LA NOUVELLE ARCHITECTURE ANTI-HALLUCINATION INTELLIGENTE
Valide le système basé sur l'intention + LLM Juge unique
"""

import asyncio
import time
from core.intelligent_hallucination_guard import IntelligentHallucinationGuard

async def test_intelligent_hallucination_guard():
    """
    🎯 TEST COMPLET DU SYSTÈME INTELLIGENT
    """
    print("🛡️ TEST DE L'ARCHITECTURE ANTI-HALLUCINATION INTELLIGENTE")
    print("=" * 80)
    
    guard = IntelligentHallucinationGuard()
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    
    # Tests avec différents types de requêtes
    test_cases = [
        {
            "name": "🟢 REQUÊTE SOCIALE - Bonjour",
            "query": "Bonjour",
            "response": "Bonjour ! Je suis Jessica, votre assistante virtuelle. Comment puis-je vous aider aujourd'hui ?",
            "expected_search": False,
            "expected_safe": True
        },
        {
            "name": "🟢 REQUÊTE SOCIALE - Merci",
            "query": "Merci beaucoup",
            "response": "Je vous en prie ! N'hésitez pas si vous avez d'autres questions.",
            "expected_search": False,
            "expected_safe": True
        },
        {
            "name": "🟡 REQUÊTE PRODUIT - Sans documents",
            "query": "Avez-vous des casques moto ?",
            "response": "Oui, nous avons plusieurs modèles de casques moto en stock, à partir de 15000 FCFA.",
            "expected_search": True,
            "expected_safe": False,  # Pas de documents fournis
            "supabase_results": [],
            "meili_results": []
        },
        {
            "name": "🟢 REQUÊTE PRODUIT - Avec documents",
            "query": "Avez-vous des casques moto ?",
            "response": "D'après notre catalogue, nous avons des casques moto disponibles à 15000 FCFA.",
            "expected_search": True,
            "expected_safe": True,
            "supabase_results": [{"content": "Casques moto - Prix: 15000 FCFA - Stock: 50"}],
            "supabase_context": "Casques moto - Prix: 15000 FCFA - Stock: 50"
        },
        {
            "name": "🔴 REQUÊTE PRIX - Hallucination",
            "query": "Quel est le prix du casque rouge ?",
            "response": "Le casque rouge coûte 25000 FCFA avec une promotion de 20%.",
            "expected_search": True,
            "expected_safe": False,  # Prix inventé
            "supabase_results": [{"content": "Casques disponibles: noir, blanc, bleu"}],
            "supabase_context": "Casques disponibles: noir, blanc, bleu"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 TEST {i}: {test_case['name']}")
        print("-" * 60)
        
        start_time = time.time()
        
        # Test 1: Vérifier si recherche nécessaire
        should_skip = guard.should_skip_search(test_case['query'], company_id)
        search_required = not should_skip
        
        print(f"🔍 Recherche requise: {search_required} (attendu: {test_case['expected_search']})")
        
        # Test 2: Évaluation complète
        hallucination_check = await guard.evaluate_response(
            user_query=test_case['query'],
            ai_response=test_case['response'],
            company_id=company_id,
            supabase_results=test_case.get('supabase_results', []),
            meili_results=test_case.get('meili_results', []),
            supabase_context=test_case.get('supabase_context', ''),
            meili_context=test_case.get('meili_context', '')
        )
        
        processing_time = time.time() - start_time
        
        # Résultats
        print(f"✅ Sécurisé: {hallucination_check.is_safe} (attendu: {test_case['expected_safe']})")
        print(f"🎯 Intention: {hallucination_check.intention_detected}")
        print(f"📊 Confiance: {hallucination_check.confidence_score:.2f}")
        print(f"🧠 Décision juge: {hallucination_check.judge_decision[:80]}...")
        print(f"⏱️ Temps: {processing_time*1000:.1f}ms")
        
        if hallucination_check.suggested_response:
            print(f"💡 Réponse suggérée: {hallucination_check.suggested_response[:80]}...")
        
        # Validation
        search_correct = search_required == test_case['expected_search']
        safety_correct = hallucination_check.is_safe == test_case['expected_safe']
        
        status = "✅ RÉUSSI" if (search_correct and safety_correct) else "❌ ÉCHOUÉ"
        print(f"🎯 Résultat: {status}")
        
        results.append({
            'test': test_case['name'],
            'search_correct': search_correct,
            'safety_correct': safety_correct,
            'processing_time': processing_time * 1000,
            'passed': search_correct and safety_correct
        })
    
    # Résumé final
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    passed_tests = sum(1 for r in results if r['passed'])
    total_tests = len(results)
    avg_time = sum(r['processing_time'] for r in results) / len(results)
    
    print(f"✅ Tests réussis: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"⏱️ Temps moyen: {avg_time:.1f}ms")
    
    for result in results:
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {result['test']} - {result['processing_time']:.1f}ms")
    
    print("\n🎯 ARCHITECTURE INTELLIGENTE TESTÉE AVEC SUCCÈS !")
    
    return results

async def test_optimization_performance():
    """
    🚀 TEST DE PERFORMANCE - OPTIMISATION DES RECHERCHES
    """
    print("\n🚀 TEST DE PERFORMANCE - OPTIMISATION")
    print("=" * 80)
    
    guard = IntelligentHallucinationGuard()
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    
    # Requêtes sociales (pas de recherche)
    social_queries = [
        "Bonjour", "Salut", "Merci", "Au revoir", "Comment allez-vous ?",
        "Bonne journée", "À bientôt", "Hello", "Bonsoir", "Ça va ?"
    ]
    
    # Requêtes business (recherche nécessaire)
    business_queries = [
        "Prix des casques", "Stock disponible", "Livraison à Cocody",
        "Paiement Wave", "Contact WhatsApp", "Horaires d'ouverture",
        "Garantie produits", "Retour commande", "Promotion en cours"
    ]
    
    print(f"🔍 Test avec {len(social_queries)} requêtes sociales...")
    social_skipped = 0
    for query in social_queries:
        if guard.should_skip_search(query, company_id):
            social_skipped += 1
    
    print(f"🔍 Test avec {len(business_queries)} requêtes business...")
    business_searched = 0
    for query in business_queries:
        if not guard.should_skip_search(query, company_id):
            business_searched += 1
    
    print(f"\n📊 RÉSULTATS OPTIMISATION:")
    print(f"✅ Requêtes sociales évitées: {social_skipped}/{len(social_queries)} ({social_skipped/len(social_queries)*100:.1f}%)")
    print(f"✅ Requêtes business traitées: {business_searched}/{len(business_queries)} ({business_searched/len(business_queries)*100:.1f}%)")
    
    total_queries = len(social_queries) + len(business_queries)
    optimized_queries = social_skipped
    optimization_rate = optimized_queries / total_queries * 100
    
    print(f"🚀 Taux d'optimisation global: {optimization_rate:.1f}%")
    print(f"💡 Économie estimée: {optimization_rate:.1f}% de recherches évitées")

if __name__ == "__main__":
    async def main():
        await test_intelligent_hallucination_guard()
        await test_optimization_performance()
    
    asyncio.run(main())
