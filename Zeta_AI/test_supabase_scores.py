#!/usr/bin/env python3
"""
🎯 TEST SCORES SUPABASE - DIAGNOSTIC PRÉCIS
Teste les scores de similarité réels pour identifier le problème
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.supabase_vector_search import SupabaseVectorSearch

async def test_scores_supabase():
    """Test des scores réels de Supabase"""
    print("🎯 TEST SCORES SUPABASE")
    print("=" * 50)
    
    # Requête de test (celle qui échoue)
    query = "dite cc couches culottes pression disponible bebe 9kg?"
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    # Initialisation du moteur
    engine = SupabaseVectorSearch()
    await engine.initialize()
    
    print(f"🔍 Requête: {query}")
    print(f"🏢 Company ID: {company_id}")
    
    try:
        # 1. TEST AVEC SEUIL TRÈS BAS
        print("\n1️⃣ TEST AVEC SEUIL TRÈS BAS (0.1)")
        results_low = await engine.search_vectors(
            query_embedding=await engine.generate_embedding(query),
            company_id=company_id,
            top_k=5,
            min_score=0.1,  # Seuil très bas
            include_metadata=True
        )
        
        print(f"📊 Résultats avec seuil 0.1: {len(results_low)}")
        for i, result in enumerate(results_low, 1):
            print(f"   {i}. Score: {result.score:.4f} | ID: {result.id}")
            print(f"      Contenu: {result.content[:100]}...")
        
        # 2. TEST AVEC SEUIL NORMAL
        print("\n2️⃣ TEST AVEC SEUIL NORMAL (0.3)")
        results_normal = await engine.search_vectors(
            query_embedding=await engine.generate_embedding(query),
            company_id=company_id,
            top_k=5,
            min_score=0.3,  # Seuil normal
            include_metadata=True
        )
        
        print(f"📊 Résultats avec seuil 0.3: {len(results_normal)}")
        for i, result in enumerate(results_normal, 1):
            print(f"   {i}. Score: {result.score:.4f} | ID: {result.id}")
            print(f"      Contenu: {result.content[:100]}...")
        
        # 3. TEST AVEC SEUIL ÉLEVÉ
        print("\n3️⃣ TEST AVEC SEUIL ÉLEVÉ (0.5)")
        results_high = await engine.search_vectors(
            query_embedding=await engine.generate_embedding(query),
            company_id=company_id,
            top_k=5,
            min_score=0.5,  # Seuil élevé
            include_metadata=True
        )
        
        print(f"📊 Résultats avec seuil 0.5: {len(results_high)}")
        for i, result in enumerate(results_high, 1):
            print(f"   {i}. Score: {result.score:.4f} | ID: {result.id}")
            print(f"      Contenu: {result.content[:100]}...")
        
        # 4. ANALYSE DES SCORES
        print("\n4️⃣ ANALYSE DES SCORES")
        if results_low:
            best_score = max(result.score for result in results_low)
            worst_score = min(result.score for result in results_low)
            avg_score = sum(result.score for result in results_low) / len(results_low)
            
            print(f"📈 Meilleur score: {best_score:.4f}")
            print(f"📉 Pire score: {worst_score:.4f}")
            print(f"📊 Score moyen: {avg_score:.4f}")
            
            # Recommandation de seuil
            if best_score < 0.3:
                print(f"⚠️  PROBLÈME: Meilleur score ({best_score:.4f}) < seuil normal (0.3)")
                print(f"💡 SOLUTION: Réduire min_score à {best_score * 0.8:.2f}")
            else:
                print(f"✅ Scores normaux, problème ailleurs")
        
        # 5. TEST RECHERCHE COMPLÈTE
        print("\n5️⃣ TEST RECHERCHE COMPLÈTE")
        results_complete, context = await engine.semantic_search(
            query=query,
            company_id=company_id,
            top_k=5,
            min_score=0.1,  # Seuil très permissif
            enable_reranking=True
        )
        
        print(f"📊 Recherche complète: {len(results_complete)} résultats")
        print(f"📄 Contexte généré: {len(context)} caractères")
        
        if context:
            print(f"📝 Aperçu contexte: {context[:200]}...")
        else:
            print("❌ Aucun contexte généré")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await engine.cleanup()
    
    print("\n" + "=" * 50)
    print("🎯 TEST TERMINÉ")

if __name__ == "__main__":
    asyncio.run(test_scores_supabase())
