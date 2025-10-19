#!/usr/bin/env python3
"""
🔧 TEST RAPIDE CORRECTION SUPABASE
Vérifie que la colonne 'embedding' est maintenant utilisée
"""

import asyncio
from core.supabase_simple import SupabaseSimple

async def test_supabase_fix():
    """Test rapide de la correction"""
    
    print("🔧 TEST CORRECTION SUPABASE")
    print("=" * 50)
    
    supabase = SupabaseSimple()
    
    # Test avec une requête simple
    results = await supabase.search_documents(
        query="couches bébé",
        company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
        limit=3
    )
    
    print(f"\n🎯 RÉSULTAT: {len(results)} documents trouvés")
    
    if results:
        print("✅ CORRECTION RÉUSSIE !")
        for i, doc in enumerate(results, 1):
            print(f"{i}. Score: {doc['similarity_score']:.3f} - {doc.get('content', '')[:50]}...")
    else:
        print("❌ Toujours aucun résultat")
    
    return len(results) > 0

if __name__ == "__main__":
    success = asyncio.run(test_supabase_fix())
    if success:
        print("\n🎉 Supabase fonctionne maintenant !")
    else:
        print("\n❌ Problème persistant")
