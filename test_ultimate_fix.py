#!/usr/bin/env python3
"""
Test ultime pour valider toutes les corrections finales
"""

import asyncio
import sys
import os
import time

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_ultimate_fix():
    """Test ultime de toutes les corrections"""
    
    print("🚀 TEST ULTIME DES CORRECTIONS FINALES")
    print("=" * 60)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        # Tests multiples pour valider la stabilité
        test_questions = [
            "Quels sont vos differentes types de couches disponible svp?",
            "Que vendez vous?",
            "Quel est le prix des couches?"
        ]
        
        total_time = 0
        success_count = 0
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n🔍 TEST {i}: {question}")
            print("-" * 50)
            
            start_time = time.time()
            
            try:
                response = await get_rag_response_advanced(
                    message=question,
                    user_id="test_user",
                    company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
                )
                
                end_time = time.time()
                processing_time = (end_time - start_time) * 1000
                total_time += processing_time
                
                print(f"✅ Réponse générée en {processing_time:.2f}ms")
                print(f"📝 Contenu: {response.get('response', 'N/A')[:150]}...")
                
                # Vérifications critiques
                response_text = response.get('response', '')
                checks = {
                    "Réponse substantielle": len(response_text) > 100,
                    "Performance acceptable": processing_time < 15000,  # 15s max
                    "Contient des informations": 'couches' in response_text.lower() or 'produit' in response_text.lower(),
                    "Format professionnel": response_text.startswith('Bonjour') or response_text.startswith('Nous')
                }
                
                print(f"\n🔍 VÉRIFICATIONS:")
                for check_name, passed in checks.items():
                    print(f"  - {check_name}: {'✅' if passed else '❌'}")
                
                if all(checks.values()):
                    success_count += 1
                    print(f"✅ TEST {i} RÉUSSI")
                else:
                    print(f"⚠️  TEST {i} PARTIELLEMENT RÉUSSI")
                    
            except Exception as e:
                print(f"❌ Erreur dans le test {i}: {e}")
        
        # Résumé final
        avg_time = total_time / len(test_questions)
        success_rate = (success_count / len(test_questions)) * 100
        
        print(f"\n📊 RÉSUMÉ FINAL:")
        print(f"  - Tests réussis: {success_count}/{len(test_questions)} ({success_rate:.1f}%)")
        print(f"  - Temps moyen: {avg_time:.2f}ms")
        print(f"  - Temps total: {total_time:.2f}ms")
        
        if success_rate >= 80 and avg_time < 10000:
            print(f"\n🎉 SYSTÈME RAG OPTIMISÉ AVEC SUCCÈS !")
        elif success_rate >= 60:
            print(f"\n✅ SYSTÈME RAG FONCTIONNEL")
        else:
            print(f"\n⚠️  SYSTÈME RAG NÉCESSITE ENCORE DES CORRECTIONS")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        print(f"🔍 Type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_ultimate_fix())
