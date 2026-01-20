#!/usr/bin/env python3
"""
🧪 TEST DU SYSTÈME LLM HYDE
Teste la structuration automatique des données
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

async def test_llm_hyde():
    """Test complet du système LLM Hyde"""
    
    print("🧪 TEST SYSTÈME LLM HYDE")
    print("="*80)
    
    # Données brutes (copier-coller typique d'un utilisateur)
    raw_data = """
Bonjour, je m'appelle Rue du gros, on vend des couches pour bébé en Cote d'Ivoire.

Nos produit:
- couche culotte 1 paket 5500f
- couche culotte 2 pakets 9800 francs  
- couche culotte 6 pakets 25000 francs
- couche adulte 1 paquet (10 unité) 5880f

On livre a yopougon cocody plateau pour 1500f
Port-Bouët Attécoubé c'est 2000f
Les zones loin c'est 2500f

Contact: 07 87 36 07 57 (wave aussi)
Whatsapp: 01 60 92 45 60

On travaille tout le temps, 24/7

Paiement: wave seulement, il faut payer acompte de 2000f d'abord

Retour possible sous 24h si problème
    """
    
    print("\n📝 DONNÉES BRUTES (ce que l'utilisateur envoie):")
    print("-"*80)
    print(raw_data)
    print("-"*80)
    
    # Initialiser LLM
    print("\n1️⃣ Initialisation LLM client...")
    from core.llm_client import get_groq_llm_client
    llm_client = get_groq_llm_client()
    print("   ✅ LLM client prêt")
    
    # Initialiser Hyde
    print("\n2️⃣ Initialisation LLM Hyde...")
    from core.llm_hyde_ingestion import get_llm_hyde_ingestion
    hyde = get_llm_hyde_ingestion(llm_client)
    print("   ✅ Hyde prêt")
    
    # Test 1: Structuration
    print("\n3️⃣ TEST STRUCTURATION...")
    print("="*80)
    
    try:
        structured_data = await hyde.structure_raw_data(raw_data, "test_company")
        
        print("\n✅ STRUCTURATION RÉUSSIE")
        print("\n📊 DONNÉES STRUCTURÉES:")
        print("-"*80)
        
        import json
        print(json.dumps(structured_data, indent=2, ensure_ascii=False))
        
        # Test 2: Génération documents
        print("\n4️⃣ TEST GÉNÉRATION DOCUMENTS...")
        print("="*80)
        
        documents = hyde.structured_to_documents(structured_data, "test_company")
        
        print(f"\n✅ {len(documents)} DOCUMENTS GÉNÉRÉS")
        print("\n📦 APERÇU DES DOCUMENTS:")
        print("-"*80)
        
        for i, doc in enumerate(documents, 1):
            print(f"\nDocument #{i}:")
            print(f"  Type: {doc.get('type', 'N/A')}")
            print(f"  ID: {doc.get('id', 'N/A')}")
            print(f"  Contenu: {doc.get('content', 'N/A')[:100]}...")
        
        # Test 3: Validation
        print("\n5️⃣ VALIDATION...")
        print("="*80)
        
        validations = []
        
        # Vérifier corrections orthographe
        original_fautes = ["paket", "produit"]
        has_corrections = True
        for doc in documents:
            content = doc.get('content', '').lower()
            if any(faute in content for faute in original_fautes):
                has_corrections = False
        
        validations.append(("Fautes corrigées", has_corrections))
        
        # Vérifier prix normalisés
        has_normalized_prices = any(
            doc.get('price') and isinstance(doc.get('price'), (int, float))
            for doc in documents
        )
        validations.append(("Prix normalisés", has_normalized_prices))
        
        # Vérifier séparation documents
        pricing_docs = [d for d in documents if d.get('type') == 'pricing']
        validations.append(("Documents séparés", len(pricing_docs) >= 3))
        
        # Vérifier zones structurées
        delivery_docs = [d for d in documents if d.get('type') == 'delivery']
        validations.append(("Zones structurées", len(delivery_docs) >= 1))
        
        # Afficher résultats
        print("\n📋 RÉSULTATS VALIDATION:")
        all_passed = True
        for check, passed in validations:
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            if not passed:
                all_passed = False
        
        print("\n" + "="*80)
        if all_passed:
            print("🎉 TOUS LES TESTS RÉUSSIS !")
            print("\n💡 Le système est prêt:")
            print("   1. Les fautes sont corrigées automatiquement")
            print("   2. Les prix sont normalisés")
            print("   3. Les documents sont séparés (1 prix = 1 document)")
            print("   4. Les zones sont structurées")
            print("\n✅ Prêt pour production !")
        else:
            print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
            print("Vérifiez les validations ci-dessus")
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoint():
    """Test de l'endpoint API"""
    
    print("\n\n🌐 TEST ENDPOINT API")
    print("="*80)
    
    print("\n📌 Pour tester l'endpoint API:")
    print("-"*80)
    print("""
1. Démarrer le serveur:
   uvicorn app:app --host 0.0.0.0 --port 8001 --reload

2. Tester avec curl:
   curl -X POST "http://localhost:8001/hyde/test" \\
     -H "Content-Type: application/json" \\
     -d '{
       "company_id": "test",
       "raw_data": "Je vends couches 1 paquet 5500f contact 07123456"
     }'

3. Indexation réelle:
   curl -X POST "http://localhost:8001/hyde/ingest" \\
     -H "Content-Type: application/json" \\
     -d '{
       "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
       "raw_data": "..."
     }'
    """)

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" "*20 + "🎯 TEST LLM HYDE - INGESTION INTELLIGENTE")
    print("="*80 + "\n")
    
    # Test principal
    success = asyncio.run(test_llm_hyde())
    
    # Test API
    asyncio.run(test_api_endpoint())
    
    # Résumé final
    print("\n" + "="*80)
    if success:
        print("✅ SYSTÈME VALIDÉ - PRÊT À UTILISER")
    else:
        print("⚠️ PROBLÈMES DÉTECTÉS - À CORRIGER")
    print("="*80 + "\n")
