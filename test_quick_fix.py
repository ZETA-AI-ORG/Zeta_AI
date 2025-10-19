#!/usr/bin/env python3
"""
Test rapide pour valider les corrections finales
"""

import asyncio
import sys
import os
import time

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_quick_fix():
    """Test rapide des corrections finales"""
    
    print("🚀 TEST RAPIDE DES CORRECTIONS FINALES")
    print("=" * 50)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        # Test avec la question la plus problématique
        question = "Quels sont vos differentes types de couches disponible svp?"
        print(f"🔍 Question: {question}")
        print("-" * 50)
        
        start_time = time.time()
        
        response = await get_rag_response_advanced(
            message=question,
            user_id="test_user",
            company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        )
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        
        print(f"✅ Réponse générée en {processing_time:.2f}ms")
        print(f"📝 Contenu: {response.get('response', 'N/A')[:200]}...")
        print(f"🎯 Confiance: {response.get('confidence', 'N/A')}")
        
        # Vérifications critiques
        print("\n🔍 VÉRIFICATIONS:")
        print(f"  - Réponse substantielle: {'✅' if len(response.get('response', '')) > 100 else '❌'}")
        print(f"  - Performance: {'✅' if processing_time < 10000 else '❌'} ({processing_time:.0f}ms)")
        print(f"  - Contient 'couches': {'✅' if 'couches' in response.get('response', '').lower() else '❌'}")
        print(f"  - Contient des prix: {'✅' if 'F CFA' in response.get('response', '') else '❌'}")
        
        print(f"\n🎉 TEST TERMINÉ")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print(f"🔍 Type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_quick_fix())