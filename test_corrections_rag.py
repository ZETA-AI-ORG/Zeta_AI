#!/usr/bin/env python3
"""
Script de test pour valider les corrections apportées au système RAG
"""

import asyncio
import sys
import os
import time

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_rag_corrections():
    """Test des corrections apportées au système RAG"""
    
    print("🧪 TEST DES CORRECTIONS RAG")
    print("=" * 50)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        # Test avec la question qui posait problème
        test_questions = [
            "Quels sont vos differentes types de couches disponible svp?",
            "Que vendez vous?",
            "Quel est le prix des couches?",
            "Comment commander?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n🔍 TEST {i}: {question}")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                response = await get_rag_response_advanced(
                    message=question,
                    user_id="test_user",
                    company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
                )
                
                end_time = time.time()
                processing_time = (end_time - start_time) * 1000
                
                print(f"✅ Réponse générée en {processing_time:.2f}ms")
                print(f"📝 Contenu: {response.get('response', 'N/A')[:100]}...")
                print(f"🎯 Confiance: {response.get('confidence', 'N/A')}")
                print(f"📊 Sources: {response.get('sources_found', 'N/A')}")
                
                # Vérifications
                if response.get('response') and len(response.get('response', '')) > 50:
                    print("✅ Réponse substantielle générée")
                else:
                    print("⚠️  Réponse trop courte ou vide")
                    
                if processing_time < 5000:  # Moins de 5 secondes
                    print("✅ Performance acceptable")
                else:
                    print("⚠️  Performance lente")
                    
            except Exception as e:
                print(f"❌ Erreur: {e}")
                print(f"🔍 Type d'erreur: {type(e).__name__}")
        
        print(f"\n🎉 TESTS TERMINÉS")
        print("=" * 50)
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("🔧 Vérifiez que tous les modules sont disponibles")
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        print(f"🔍 Type d'erreur: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_rag_corrections())
