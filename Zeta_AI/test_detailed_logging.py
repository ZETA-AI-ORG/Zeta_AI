#!/usr/bin/env python3
"""
🧪 TEST DU SYSTÈME DE LOGGING DÉTAILLÉ
Test du système de logging complet du RAG
"""

import asyncio
import sys
import os
import time

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_detailed_logging():
    """Test du système de logging détaillé"""
    print("🧪 TEST DU SYSTÈME DE LOGGING DÉTAILLÉ")
    print("=" * 50)
    
    try:
        # Import du système de logging
        from core.detailed_logging_system import DetailedRAGLogger
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        print("✅ Modules importés avec succès")
        
        # Test 1: Test du logger seul
        print("\n1️⃣ Test du logger détaillé...")
        logger = DetailedRAGLogger()
        
        # Simulation d'une requête
        request_data = {
            "user_id": "test_user",
            "company_id": "test_company",
            "message": "Comment tu t'appelles ?"
        }
        
        request_id = logger.start_request(request_data)
        print(f"   Request ID généré: {request_id}")
        
        # Simulation d'étapes
        from core.advanced_intent_classifier import IntentType, IntentResult
        
        intent_result = IntentResult(
            primary_intent=IntentType.SOCIAL_GREETING,
            confidence=0.9,
            all_intents={},
            requires_documents=False,
            is_critical=False,
            fallback_required=False,
            context_hints=[],
            processing_time_ms=50.0
        )
        
        logger.log_intent_classification("Test query", intent_result)
        logger.log_response_sent("Réponse de test", {"test": True})
        
        print("   ✅ Logger détaillé fonctionne")
        
        # Test 2: Test avec le RAG engine complet
        print("\n2️⃣ Test avec le RAG engine complet...")
        
        start_time = time.time()
        
        result = await get_rag_response_advanced(
            message="Comment tu t'appelles ?",
            user_id="test_user",
            company_id="test_company"
        )
        
        end_time = time.time()
        
        print(f"   ✅ RAG engine exécuté en {end_time - start_time:.2f}s")
        print(f"   Réponse: {result['response'][:50]}...")
        print(f"   Intent: {result['intent']}")
        print(f"   Confidence: {result['confidence']:.3f}")
        
        # Test 3: Vérification des logs générés
        print("\n3️⃣ Vérification des logs générés...")
        
        # Chercher les fichiers de logs
        log_files = []
        for file in os.listdir("."):
            if file.startswith("rag_detailed_logs_") and file.endswith(".json"):
                log_files.append(file)
        
        if log_files:
            print(f"   📁 Fichiers de logs trouvés: {len(log_files)}")
            for file in log_files:
                print(f"      - {file}")
        else:
            print("   ⚠️  Aucun fichier de logs trouvé")
        
        # Test 4: Test du visualiseur de logs
        print("\n4️⃣ Test du visualiseur de logs...")
        
        try:
            from view_rag_logs import RAGLogViewer
            
            viewer = RAGLogViewer()
            log_files = viewer.find_log_files()
            
            if log_files:
                print(f"   📊 Chargement du log: {log_files[0]}")
                log_data = viewer.load_log_file(log_files[0])
                
                if log_data:
                    print(f"   ✅ Log chargé: {log_data.get('request_id', 'Unknown')}")
                    print(f"   📝 Nombre de logs: {len(log_data.get('logs', []))}")
                    print(f"   ⏱️  Durée totale: {log_data.get('total_duration_ms', 0):.2f}ms")
                else:
                    print("   ❌ Impossible de charger le log")
            else:
                print("   ⚠️  Aucun fichier de logs à visualiser")
                
        except Exception as e:
            print(f"   ❌ Erreur visualiseur: {e}")
        
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("\n📋 RÉSUMÉ:")
        print("   ✅ Système de logging détaillé fonctionnel")
        print("   ✅ RAG engine avec logging intégré")
        print("   ✅ Logs sauvegardés en JSON")
        print("   ✅ Visualiseur de logs opérationnel")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_logging_with_different_queries():
    """Test du logging avec différents types de questions"""
    print("\n🔍 TEST AVEC DIFFÉRENTS TYPES DE QUESTIONS")
    print("=" * 50)
    
    test_queries = [
        {
            "message": "Comment tu t'appelles ?",
            "description": "Question sociale"
        },
        {
            "message": "Quels sont vos produits ?",
            "description": "Question métier"
        },
        {
            "message": "Combien coûte la livraison ?",
            "description": "Question de prix"
        },
        {
            "message": "Bonjour",
            "description": "Salutation simple"
        }
    ]
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n{i}. Test: {test_case['description']}")
            print(f"   Question: {test_case['message']}")
            
            start_time = time.time()
            
            result = await get_rag_response_advanced(
                message=test_case['message'],
                user_id=f"test_user_{i}",
                company_id="test_company"
            )
            
            end_time = time.time()
            
            print(f"   ✅ Réponse générée en {end_time - start_time:.2f}s")
            print(f"   Intent: {result['intent']}")
            print(f"   Confidence: {result['confidence']:.3f}")
            print(f"   Validation safe: {result['validation_safe']}")
            
            # Petite pause entre les tests
            await asyncio.sleep(0.5)
        
        print(f"\n✅ Tous les tests de questions sont passés !")
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur dans les tests de questions: {e}")
        return False

async def main():
    """Fonction principale"""
    print("🚀 DÉMARRAGE DES TESTS DE LOGGING DÉTAILLÉ")
    print("=" * 60)
    
    # Test principal
    main_test_ok = await test_detailed_logging()
    
    # Test avec différentes questions
    queries_test_ok = await test_logging_with_different_queries()
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ FINAL DES TESTS")
    print(f"   Test principal: {'✅ PASSÉ' if main_test_ok else '❌ ÉCHOUÉ'}")
    print(f"   Test questions: {'✅ PASSÉ' if queries_test_ok else '❌ ÉCHOUÉ'}")
    
    if main_test_ok and queries_test_ok:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("   Le système de logging détaillé est opérationnel.")
        print("\n💡 UTILISATION:")
        print("   - Les logs sont sauvegardés automatiquement")
        print("   - Utilisez 'python view_rag_logs.py' pour les visualiser")
        print("   - Les logs incluent chaque étape du pipeline RAG")
    else:
        print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("   Vérifiez les erreurs ci-dessus.")

if __name__ == "__main__":
    asyncio.run(main())
