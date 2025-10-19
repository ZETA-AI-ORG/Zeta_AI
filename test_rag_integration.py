#!/usr/bin/env python3
"""
🧪 TEST INTÉGRATION RAG + SUPABASE SIMPLE
Vérifie que le RAG engine utilise bien notre nouvelle classe SupabaseSimple
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_rag_integration():
    """Test complet de l'intégration RAG + SupabaseSimple"""
    print("🧪 TEST INTÉGRATION RAG + SUPABASE SIMPLE")
    print("=" * 60)
    
    try:
        # Import du RAG engine
        from core.universal_rag_engine import get_universal_rag_response
        
        # Test avec la même requête que notre test standalone
        print("🔍 Test requête: 'couches bébé 9kg prix'")
        print("🏢 Company ID: MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
        print("-" * 40)
        
        result = await get_universal_rag_response(
            message="couches bébé 9kg prix",
            company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
            user_id="test_user",
            company_name="Rue du Gros"
        )
        
        print("🎯 RÉSULTATS:")
        print(f"✅ Succès: {result['success']}")
        print(f"📄 Documents trouvés: {result['documents_found']}")
        print(f"🎯 Confiance: {result['confidence']:.3f}")
        print(f"⏱️  Temps: {result['processing_time_ms']:.0f}ms")
        print(f"🔍 Méthode: {result['search_method']}")
        
        print(f"\n📝 RÉPONSE:")
        print(f"{result['response']}")
        
        print(f"\n📋 CONTEXTE UTILISÉ:")
        context = result['context_used']
        if context and context != "Aucun":
            print(f"{context[:500]}...")
        else:
            print("❌ Aucun contexte utilisé")
        
        # Vérifications
        print(f"\n🔍 VÉRIFICATIONS:")
        if result['documents_found']:
            print("✅ Documents Supabase trouvés")
        else:
            print("❌ Aucun document Supabase trouvé")
            
        if result['confidence'] > 0.5:
            print("✅ Confiance élevée")
        else:
            print("⚠️ Confiance faible")
            
        if "couches" in result['response'].lower():
            print("✅ Réponse pertinente (contient 'couches')")
        else:
            print("⚠️ Réponse peut-être non pertinente")
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag_integration())
