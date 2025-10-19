#!/usr/bin/env python3
"""
Test de debug pour vérifier si Supabase utilise la vraie question
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_supabase_query_debug():
    """Test pour vérifier si Supabase utilise la vraie question"""
    
    print("🧪 TEST DEBUG SUPABASE QUERY")
    print("=" * 50)
    
    try:
        from database.supabase_client import match_documents_via_rpc
        from embedding_models import get_embedding_model
        
        # Test avec une vraie question
        question = "Quels sont vos produits de couches?"
        print(f"\n1️⃣ Question de test: '{question}'")
        
        # Générer l'embedding
        model = get_embedding_model()
        embedding = model.encode(question).tolist()
        print(f"   Embedding généré: {len(embedding)} dimensions")
        
        # Appel avec original_query
        print(f"\n2️⃣ Appel avec original_query:")
        results = await match_documents_via_rpc(
            embedding=embedding,
            company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
            top_k=3,
            min_score=0.1,
            original_query=question
        )
        
        print(f"   Résultats trouvés: {len(results)}")
        for i, result in enumerate(results):
            if isinstance(result, dict) and 'content' in result:
                content = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                print(f"   Document {i+1}: {content}")
        
        # Test sans original_query (fallback)
        print(f"\n3️⃣ Appel SANS original_query (fallback):")
        results_fallback = await match_documents_via_rpc(
            embedding=embedding,
            company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
            top_k=3,
            min_score=0.1
            # Pas d'original_query
        )
        
        print(f"   Résultats fallback: {len(results_fallback)}")
        for i, result in enumerate(results_fallback):
            if isinstance(result, dict) and 'content' in result:
                content = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                print(f"   Document {i+1}: {content}")
        
        # Comparaison
        print(f"\n📊 COMPARAISON:")
        print(f"   Avec original_query: {len(results)} documents")
        print(f"   Sans original_query: {len(results_fallback)} documents")
        print(f"   Identiques: {results == results_fallback}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_supabase_query_debug())
    print(f"\n🎯 RÉSULTAT: {'✅ SUCCÈS' if success else '❌ ÉCHEC'}")
    sys.exit(0 if success else 1)
