#!/usr/bin/env python3
"""
🚨 DIAGNOSTIC CRITIQUE SUPABASE - PROBLÈME 0 DOCUMENTS
Analyse complète de l'état de la base de données Supabase
"""
import asyncio
import httpx
import json
from config import SUPABASE_URL, SUPABASE_KEY

async def diagnostic_supabase_complet():
    """Diagnostic complet de l'état Supabase"""
    print("🔍 DIAGNOSTIC CRITIQUE SUPABASE")
    print("=" * 50)
    
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # 1. TEST CONNEXION SUPABASE
        print("\n1️⃣ TEST CONNEXION SUPABASE")
        try:
            response = await client.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
            print(f"✅ Connexion Supabase: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return
        
        # 2. VÉRIFICATION TABLE DOCUMENTS
        print("\n2️⃣ VÉRIFICATION TABLE DOCUMENTS")
        try:
            # Compter TOUS les documents
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers={**headers, "Prefer": "count=exact"},
                params={"select": "id", "limit": "1"}
            )
            total_count = response.headers.get("Content-Range", "0").split("/")[-1]
            print(f"📊 Total documents dans la base: {total_count}")
            
            # Compter documents pour cette entreprise
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers={**headers, "Prefer": "count=exact"},
                params={
                    "company_id": f"eq.{company_id}",
                    "select": "id",
                    "limit": "1"
                }
            )
            company_count = response.headers.get("Content-Range", "0").split("/")[-1]
            print(f"🏢 Documents pour company_id {company_id}: {company_count}")
            
        except Exception as e:
            print(f"❌ Erreur vérification table: {e}")
        
        # 3. ÉCHANTILLON DE DONNÉES
        print("\n3️⃣ ÉCHANTILLON DE DONNÉES")
        try:
            # Récupérer quelques documents de cette entreprise
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={
                    "company_id": f"eq.{company_id}",
                    "select": "id,content,metadata,created_at",
                    "limit": "3"
                }
            )
            
            if response.status_code == 200:
                documents = response.json()
                print(f"📄 Échantillon trouvé: {len(documents)} documents")
                
                for i, doc in enumerate(documents, 1):
                    print(f"\n   Document {i}:")
                    print(f"   - ID: {doc.get('id', 'N/A')}")
                    print(f"   - Contenu: {doc.get('content', '')[:100]}...")
                    print(f"   - Métadonnées: {doc.get('metadata', {})}")
                    print(f"   - Créé: {doc.get('created_at', 'N/A')}")
            else:
                print(f"❌ Erreur récupération échantillon: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Erreur échantillon: {e}")
        
        # 4. TEST REQUÊTE EXACTE DU SYSTÈME
        print("\n4️⃣ TEST REQUÊTE EXACTE DU SYSTÈME")
        try:
            # Reproduire exactement la requête du système
            params = {
                "company_id": f"eq.{company_id}",
                "select": "id,content,embedding,metadata",
                "limit": "15"  # top_k * 3
            }
            
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params=params
            )
            
            print(f"🔍 Status Code: {response.status_code}")
            print(f"🔍 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                documents = response.json()
                print(f"📊 Documents retournés: {len(documents)}")
                
                if documents:
                    # Analyser le premier document
                    first_doc = documents[0]
                    print(f"\n   Premier document:")
                    print(f"   - ID: {first_doc.get('id')}")
                    print(f"   - A un embedding: {'embedding' in first_doc and first_doc['embedding'] is not None}")
                    print(f"   - Taille embedding: {len(first_doc.get('embedding', [])) if first_doc.get('embedding') else 0}")
                    print(f"   - Contenu: {first_doc.get('content', '')[:100]}...")
                else:
                    print("❌ AUCUN DOCUMENT TROUVÉ - C'EST LE PROBLÈME !")
            else:
                print(f"❌ Erreur requête: {response.text}")
                
        except Exception as e:
            print(f"❌ Erreur test requête: {e}")
        
        # 5. VÉRIFICATION AUTRES COMPANY_IDS
        print("\n5️⃣ VÉRIFICATION AUTRES COMPANY_IDS")
        try:
            # Voir quels company_ids existent
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={
                    "select": "company_id",
                    "limit": "10"
                }
            )
            
            if response.status_code == 200:
                documents = response.json()
                company_ids = list(set(doc.get('company_id') for doc in documents if doc.get('company_id')))
                print(f"🏢 Company IDs trouvés: {company_ids}")
                
                if company_id not in company_ids:
                    print(f"❌ PROBLÈME: {company_id} n'existe pas dans la base !")
                    print(f"✅ Company IDs disponibles: {company_ids}")
            
        except Exception as e:
            print(f"❌ Erreur vérification company_ids: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC TERMINÉ")

if __name__ == "__main__":
    asyncio.run(diagnostic_supabase_complet())
