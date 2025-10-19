#!/usr/bin/env python3
"""
🧪 TEST RAG AVEC RECHERCHE DE DOCUMENTS
Test pour vérifier que le RAG recherche des documents pour les questions produits
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_rag_with_documents():
    """Test RAG avec recherche de documents"""
    print("🧪 TEST RAG AVEC RECHERCHE DE DOCUMENTS")
    print("=" * 50)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        # Test avec une question qui devrait déclencher la recherche
        print("📝 Test avec: 'Que vendez vous?'")
        
        result = await get_rag_response_advanced(
            message="Que vendez vous?",
            user_id="test_documents",
            company_id="test_company"
        )
        
        print(f"\n📊 RÉSULTATS:")
        print(f"   Intent: {result['intent']}")
        print(f"   Confidence: {result['confidence']:.3f}")
        print(f"   Requires documents: {result['requires_documents']}")
        print(f"   Documents found: {result['documents_found']}")
        print(f"   Validation safe: {result['validation_safe']}")
        print(f"   Processing time: {result['processing_time_ms']:.0f}ms")
        
        print(f"\n💬 RÉPONSE:")
        print(f"   {result['response']}")
        
        # Vérifier si la recherche de documents a été déclenchée
        if result['requires_documents']:
            print(f"\n✅ RECHERCHE DE DOCUMENTS DÉCLENCHÉE")
        else:
            print(f"\n❌ RECHERCHE DE DOCUMENTS NON DÉCLENCHÉE")
        
        # Vérifier si des documents ont été trouvés
        if result['documents_found']:
            print(f"✅ DOCUMENTS TROUVÉS")
        else:
            print(f"⚠️  AUCUN DOCUMENT TROUVÉ (normal si pas de données)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rag_with_documents())
    if success:
        print("\n🎉 TEST TERMINÉ !")
    else:
        print("\n⚠️  TEST ÉCHOUÉ !")
