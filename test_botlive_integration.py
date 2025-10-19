#!/usr/bin/env python3
"""
Test d'intégration complète du système Botlive.
Simule une conversation Messenger avec envoi d'images séquentielles.
"""

import asyncio
import json
import sys
import os

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(__file__))

async def test_botlive_conversation():
    """Test complet d'une conversation Botlive avec images"""
    
    print("🧪 [TEST] Démarrage test intégration Botlive")
    
    try:
        # Import des modules
        from core.universal_rag_engine import UniversalRAGEngine
        from core.live_mode_manager import LiveModeManager
        from core.live_conversation_state import get_live_conversation_state
        
        # Initialisation
        engine = UniversalRAGEngine()
        await engine.initialize()
        
        live_manager = LiveModeManager()
        live_state = get_live_conversation_state()
        
        # Données de test
        company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"  # Company ID réel
        company_name = "Ma Boutique Test"
        user_id = "test_user_123"
        
        # URLs d'images de test (remplace par de vraies URLs)
        product_image_url = "https://picsum.photos/seed/product/600/400"
        payment_image_url = "https://picsum.photos/seed/payment/600/400"
        
        print(f"🧪 [TEST] Company: {company_id}")
        print(f"🧪 [TEST] User: {user_id}")
        
        # Étape 1: Activer le mode Live
        print("\n📍 [ÉTAPE 1] Activation du mode Live")
        live_manager.enable_live_mode()
        print(f"✅ Mode Live: {live_manager.get_status()}")
        
        # Étape 2: Nettoyer l'état (au cas où)
        print("\n📍 [ÉTAPE 2] Nettoyage état utilisateur")
        live_state.clear(user_id)
        
        # Étape 3: Première image (produit)
        print("\n📍 [ÉTAPE 3] Envoi première image (produit)")
        response1 = await engine.generate_response(
            query="Bonjour, voici mon produit",
            search_results={},
            company_id=company_id,
            company_name=company_name,
            user_id=user_id,
            images=[product_image_url]
        )
        
        print(f"🤖 [RÉPONSE 1] {response1}")
        
        # Vérifier l'état
        missing = live_state.get_missing(user_id)
        print(f"📊 [ÉTAT] Manque: {missing}")
        
        # Étape 4: Message texte intermédiaire
        print("\n📍 [ÉTAPE 4] Message texte (sans image)")
        response2 = await engine.generate_response(
            query="C'est quoi la suite ?",
            search_results={},
            company_id=company_id,
            company_name=company_name,
            user_id=user_id,
            images=None
        )
        
        print(f"🤖 [RÉPONSE 2] {response2}")
        
        # Étape 5: Deuxième image (paiement)
        print("\n📍 [ÉTAPE 5] Envoi deuxième image (paiement)")
        response3 = await engine.generate_response(
            query="Voici ma capture de paiement",
            search_results={},
            company_id=company_id,
            company_name=company_name,
            user_id=user_id,
            images=[payment_image_url]
        )
        
        print(f"🤖 [RÉPONSE 3] {response3}")
        
        # Vérifier que la session est nettoyée
        final_state = live_state.get_session(user_id)
        print(f"📊 [ÉTAT FINAL] Session: {final_state}")
        
        # Étape 6: Test question hors sujet
        print("\n📍 [ÉTAPE 6] Question hors sujet")
        response4 = await engine.generate_response(
            query="Quels sont vos horaires d'ouverture ?",
            search_results={},
            company_id=company_id,
            company_name=company_name,
            user_id=user_id,
            images=None
        )
        
        print(f"🤖 [RÉPONSE 4] {response4}")
        
        print("\n✅ [TEST] Test d'intégration terminé avec succès !")
        
    except Exception as e:
        print(f"\n❌ [TEST] Erreur: {e}")
        import traceback
        traceback.print_exc()

async def test_live_state_manager():
    """Test unitaire du gestionnaire d'état Live"""
    
    print("\n🧪 [TEST] Test LiveConversationState")
    
    from core.live_conversation_state import LiveConversationState
    
    # Créer instance de test
    state = LiveConversationState("./test_live_sessions.json")
    
    user_id = "test_user_456"
    company_id = "test_company"
    
    # Test ajout détection produit
    product_detection = {"name": "test_product", "confidence": 0.85}
    status1 = state.add_detection(user_id, company_id, "url1", product_detection, "product")
    print(f"📊 Après produit: {status1}")
    
    # Test contexte LLM
    context = state.get_context_for_llm(user_id)
    print(f"📝 Contexte: {context}")
    
    # Test ajout détection paiement
    payment_detection = {"amount": "5000", "currency": "FCFA", "reference": "WAVE123"}
    status2 = state.add_detection(user_id, company_id, "url2", payment_detection, "payment")
    print(f"📊 Après paiement: {status2}")
    
    # Test session complète
    session = state.get_session(user_id)
    print(f"📋 Session complète: {json.dumps(session, indent=2)}")
    
    # Nettoyage
    state.clear(user_id)
    
    # Supprimer fichier de test
    try:
        os.remove("./test_live_sessions.json")
    except:
        pass
    
    print("✅ Test LiveConversationState terminé")

if __name__ == "__main__":
    print("🚀 Lancement des tests Botlive")
    
    # Test 1: Gestionnaire d'état
    asyncio.run(test_live_state_manager())
    
    # Test 2: Intégration complète
    asyncio.run(test_botlive_conversation())
    
    print("\n🎉 Tous les tests terminés !")
