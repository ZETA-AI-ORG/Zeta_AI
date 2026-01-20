"""
🧪 TEST SYSTÈME HYBRIDE BOTLIVE
Vérifie que le système Python ↔ LLM fonctionne correctement
"""

import asyncio
import sys
import os

# Ajouter le répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(__file__))

async def test_hybrid_system():
    """Test du système hybride"""
    
    print("🧪 TEST SYSTÈME HYBRIDE BOTLIVE")
    print("=" * 50)
    
    # Test 1: Vérifier que les modules s'importent
    try:
        from core.loop_botlive_engine import get_loop_engine
        from core.persistent_collector import get_collector
        print("✅ Import modules OK")
    except Exception as e:
        print(f"❌ Erreur import: {e}")
        return
    
    # Test 2: Vérifier que le moteur est activé
    try:
        loop_engine = get_loop_engine()
        print(f"🔄 Moteur hybride activé: {loop_engine.is_enabled()}")
        
        if not loop_engine.is_enabled():
            loop_engine.enable()
            print("✅ Moteur activé manuellement")
    except Exception as e:
        print(f"❌ Erreur moteur: {e}")
        return
    
    # Test 3: Test collecteur
    try:
        collector = get_collector()
        
        # Test collecte simple
        result = collector.collect_and_persist(
            notepad={},
            vision_result=None,
            ocr_result=None,
            message="bonjour"
        )
        
        print(f"📊 Collecteur résultat: {result['missing']}")
        print("✅ Collecteur OK")
    except Exception as e:
        print(f"❌ Erreur collecteur: {e}")
        return
    
    # Test 4: Test moteur boucle
    try:
        def dummy_llm(prompt):
            return "Bonjour ! Envoyez photo du paquet 📦"
        
        result = loop_engine.process_message(
            message="bonjour",
            notepad={},
            vision_result=None,
            ocr_result=None,
            llm_function=dummy_llm
        )
        
        print(f"🤖 Réponse: {result['response']}")
        print(f"📊 Source: {result['source']}")
        print("✅ Moteur boucle OK")
    except Exception as e:
        print(f"❌ Erreur moteur boucle: {e}")
        return
    
    print("\n🎉 TOUS LES TESTS PASSÉS !")
    print("Le système hybride est opérationnel.")

if __name__ == "__main__":
    asyncio.run(test_hybrid_system())
