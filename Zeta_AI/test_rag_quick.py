#!/usr/bin/env python3
"""
🧪 TEST RAPIDE DU RAG
Vérification que le système peut répondre à "Que vendez vous?"
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_rag_quick():
    """Test rapide du RAG"""
    print("🧪 TEST RAPIDE DU RAG")
    print("=" * 30)
    
    try:
        # Test d'import
        print("1️⃣ Test d'import...")
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        print("✅ Import réussi")
        
        # Test de classification d'intention
        print("\n2️⃣ Test de classification...")
        message = "Que vendez vous?"
        
        # Classification simple
        if any(pattern in message.lower() for pattern in ['prix', 'coût', 'tarif', 'que vendez', 'produits', 'services']):
            intent_type = "factual_information"
            requires_docs = True
        else:
            intent_type = "general_conversation"
            requires_docs = False
        
        print(f"✅ Intention: {intent_type}")
        print(f"✅ Docs requis: {requires_docs}")
        
        # Test de recherche de documents
        print("\n3️⃣ Test de recherche de documents...")
        if requires_docs:
            try:
                from database.supabase_client import match_documents_via_rpc
                from embedding_models import get_embedding_model
                
                model = get_embedding_model()
                embedding = model.encode(message).tolist()
                
                print("✅ Embedding généré")
                
                # Test de la fonction RPC
                results = await match_documents_via_rpc(
                    embedding=embedding,
                    company_id="test_company",
                    top_k=5,
                    min_score=0.4
                )
                
                print(f"✅ Recherche Supabase: {len(results)} résultats")
                
                if results:
                    print("✅ Documents trouvés dans Supabase")
                else:
                    print("⚠️ Aucun document trouvé dans Supabase")
                
            except Exception as e:
                print(f"❌ Erreur recherche: {e}")
        
        print("\n🎉 TEST TERMINÉ")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag_quick())
