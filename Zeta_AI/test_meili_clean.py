"""
🧪 TEST DE LA VERSION PROPRE MEILISEARCH
Vérifie que les documents sont retournés complets et non fragmentés
"""
import asyncio
from database.vector_store_clean import search_meili_keywords, get_available_indexes

async def test_meili_clean():
    """Test de la recherche MeiliSearch propre"""
    
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    # Test 1: Recherche "couches à pression"
    print("\n" + "="*60)
    print("🧪 TEST 1: Recherche 'couches à pression' (CIBLÉ PRODUCTS)")
    print("="*60)
    
    # CIBLER UNIQUEMENT L'INDEX PRODUCTS
    result = search_meili_keywords(
        query="couches à pression",
        company_id=company_id,
        target_indexes=[f"products_{company_id}"],  # UNIQUEMENT products
        limit=3
    )
    
    print(f"\n📋 Résultat ({len(result)} chars):")
    print("-" * 40)
    
    if result:
        # Afficher les premiers 500 caractères pour vérifier
        print(result[:500])
        
        # Vérifier qu'on a bien des documents complets
        if "=== " in result:
            print("\n✅ Documents avec séparateurs trouvés")
            
            # Compter les documents
            doc_count = result.count("===")
            print(f"📊 Nombre de documents: {doc_count}")
            
            # Vérifier qu'on a les bonnes infos
            if "Taille 1" in result and "Taille 7" in result:
                print("✅ Document complet des couches à pression trouvé!")
            else:
                print("⚠️ Document incomplet - manque certaines tailles")
                
            # Vérifier qu'on n'a PAS les couches culottes
            if "5.500 F CFA" in result or "paquet" in result.lower():
                print("❌ ERREUR: Mélange avec les couches culottes détecté!")
            else:
                print("✅ Pas de mélange avec d'autres produits")
    else:
        print("❌ Aucun résultat")
    
    # Test 2: Recherche "couches culottes"
    print("\n" + "="*60)
    print("🧪 TEST 2: Recherche 'couches culottes' (CIBLÉ PRODUCTS)")
    print("="*60)
    
    # CIBLER UNIQUEMENT L'INDEX PRODUCTS
    result2 = search_meili_keywords(
        query="couches culottes",
        company_id=company_id,
        target_indexes=[f"products_{company_id}"],  # UNIQUEMENT products
        limit=3
    )
    
    print(f"\n📋 Résultat ({len(result2)} chars):")
    print("-" * 40)
    
    if result2:
        print(result2[:500])
        
        # Vérifier qu'on a les bons prix
        if "5.500 F CFA" in result2 and "paquet" in result2.lower():
            print("✅ Document des couches culottes trouvé!")
        else:
            print("⚠️ Document incomplet")
            
        # Vérifier qu'on n'a PAS les couches à pression
        if "Taille 1 - 0 à 4 kg" in result2:
            print("❌ ERREUR: Mélange avec les couches à pression détecté!")
        else:
            print("✅ Pas de mélange avec d'autres produits")
    else:
        print("❌ Aucun résultat")
    
    # Test 3: Lister les indexes disponibles
    print("\n" + "="*60)
    print("🧪 TEST 3: Indexes disponibles")
    print("="*60)
    
    indexes = get_available_indexes(company_id)
    print(f"\n📂 {len(indexes)} indexes trouvés:")
    for idx in indexes:
        print(f"  - {idx}")
    
    print("\n" + "="*60)
    print("✅ TESTS TERMINÉS")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_meili_clean())
