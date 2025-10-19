#!/usr/bin/env python3
"""
Test de validation du retour à l'ancien système sans HYDE
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_old_system_restored():
    """Test que l'ancien système est restauré"""
    
    print("🧪 TEST DU RETOUR À L'ANCIEN SYSTÈME")
    print("=" * 50)
    
    try:
        # Importer les fonctions de recherche
        from database.vector_store import search_meili_keywords
        from database.supabase_client import get_semantic_company_context
        
        # Test 1: Recherche MeiliSearch directe
        print("\n1️⃣ Test recherche MeiliSearch directe:")
        query1 = "Vous vendez que des couches?"
        result1 = await search_meili_keywords(query1, "MpfnlSbqwaZ6F4HvxQLRL9du0yG3", 3)
        print(f"   Query: '{query1}'")
        print(f"   Résultat: {type(result1)} - {len(str(result1))} caractères")
        print(f"   ✅ Recherche directe: {'✅' if result1 else '❌'}")
        
        # Test 2: Recherche Supabase directe (avec la bonne fonction)
        print("\n2️⃣ Test recherche Supabase directe:")
        query2 = "Quels sont vos produits?"
        try:
            # Utiliser la bonne fonction RPC
            from database.supabase_client import match_documents_via_rpc
            from embedding_models import get_embedding_model
            
            # Générer l'embedding
            model = get_embedding_model()
            embedding = model.encode(query2).tolist()
            
            result2 = await match_documents_via_rpc(embedding, "MpfnlSbqwaZ6F4HvxQLRL9du0yG3", 3, 0.3)
            print(f"   Query: '{query2}'")
            print(f"   Résultat: {type(result2)} - {len(str(result2))} caractères")
            print(f"   ✅ Recherche directe: {'✅' if result2 else '❌'}")
        except Exception as e:
            print(f"   Query: '{query2}'")
            print(f"   Erreur: {e}")
            print(f"   ✅ Recherche directe: ❌")
            result2 = None
        
        # Test 3: Performance
        print("\n3️⃣ Test performance:")
        import time
        start_time = time.time()
        await search_meili_keywords("test performance", "MpfnlSbqwaZ6F4HvxQLRL9du0yG3", 3)
        end_time = time.time()
        duration = end_time - start_time
        print(f"   Temps de recherche: {duration:.2f} secondes")
        print(f"   ✅ Performance: {'✅' if duration < 5 else '❌'} (< 5s)")
        
        # Résumé
        print("\n📊 RÉSUMÉ:")
        print(f"   - MeiliSearch direct: {'✅ PASSÉ' if result1 else '❌ ÉCHOUÉ'}")
        print(f"   - Supabase direct: {'✅ PASSÉ' if result2 else '❌ ÉCHOUÉ'}")
        print(f"   - Performance: {'✅ PASSÉ' if duration < 5 else '❌ ÉCHOUÉ'}")
        
        all_passed = all([result1, result2, duration < 5])
        print(f"\n🎯 RÉSULTAT FINAL: {'✅ ANCIEN SYSTÈME RESTAURÉ' if all_passed else '❌ SYSTÈME ENCORE DÉFAILLANT'}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_old_system_restored())
    sys.exit(0 if success else 1)
