#!/usr/bin/env python3
"""
Test de validation du système HYDE désactivé
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_hyde_disabled():
    """Test que le système HYDE est complètement désactivé"""
    
    print("🧪 TEST DU SYSTÈME HYDE DÉSACTIVÉ")
    print("=" * 50)
    
    try:
        # Importer la fonction HYDE
        from core.improved_hyde_scorer import improved_hyde_filter
        
        # Test 1: Query simple
        print("\n1️⃣ Test query simple:")
        query1 = "Vous vendez que des couches?"
        result1 = await improved_hyde_filter(query1, "test_company", 6)
        print(f"   Query originale: '{query1}'")
        print(f"   Query filtrée: '{result1}'")
        print(f"   ✅ Identique: {query1 == result1}")
        
        # Test 2: Query complexe
        print("\n2️⃣ Test query complexe:")
        query2 = "Quels sont vos différents types de couches disponibles svp?"
        result2 = await improved_hyde_filter(query2, "test_company", 6)
        print(f"   Query originale: '{query2}'")
        print(f"   Query filtrée: '{result2}'")
        print(f"   ✅ Identique: {query2 == result2}")
        
        # Test 3: Query avec caractères spéciaux
        print("\n3️⃣ Test query avec caractères spéciaux:")
        query3 = "Prix des couches Pampers taille M?"
        result3 = await improved_hyde_filter(query3, "test_company", 6)
        print(f"   Query originale: '{query3}'")
        print(f"   Query filtrée: '{result3}'")
        print(f"   ✅ Identique: {query3 == result3}")
        
        # Résumé
        print("\n📊 RÉSUMÉ:")
        print(f"   - Test 1: {'✅ PASSÉ' if query1 == result1 else '❌ ÉCHOUÉ'}")
        print(f"   - Test 2: {'✅ PASSÉ' if query2 == result2 else '❌ ÉCHOUÉ'}")
        print(f"   - Test 3: {'✅ PASSÉ' if query3 == result3 else '❌ ÉCHOUÉ'}")
        
        all_passed = all([query1 == result1, query2 == result2, query3 == result3])
        print(f"\n🎯 RÉSULTAT FINAL: {'✅ SYSTÈME HYDE COMPLÈTEMENT DÉSACTIVÉ' if all_passed else '❌ SYSTÈME HYDE ENCORE ACTIF'}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_hyde_disabled())
    sys.exit(0 if success else 1)
