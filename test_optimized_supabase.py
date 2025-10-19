"""
🧪 TEST DU NOUVEAU MOTEUR SUPABASE OPTIMISÉ
Test uniquement de la recherche sémantique Supabase
"""
import asyncio
from core.supabase_vector_search import supabase_semantic_search

async def test_optimized_supabase():
    """Test du nouveau moteur de recherche vectorielle Supabase"""
    
    print("🚀 TEST MOTEUR SUPABASE OPTIMISÉ")
    print("=" * 50)
    
    # Configuration de test
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    test_queries = [
        "information produit catalogue prix",
        "livraison commande délai",
        "service client contact support"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 TEST {i}: '{query}'")
        print("-" * 30)
        
        try:
            # Test avec le nouveau moteur optimisé
            results, context = await supabase_semantic_search(
                query=query,
                company_id=company_id,
                top_k=3,
                min_score=0.2,
                enable_reranking=True
            )
            
            print(f"✅ Résultats trouvés: {len(results)}")
            print(f"📄 Contexte généré: {len(context)} caractères")
            
            # Affichage des résultats
            for j, result in enumerate(results, 1):
                print(f"  📋 Doc {j}: Score={result['score']:.3f}")
                print(f"      Contenu: {result['content'][:100]}...")
                
        except Exception as e:
            print(f"💥 ERREUR: {type(e).__name__}: {str(e)}")
    
    print("\n🏁 Tests terminés")

if __name__ == "__main__":
    asyncio.run(test_optimized_supabase())
