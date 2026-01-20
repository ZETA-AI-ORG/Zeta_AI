#!/usr/bin/env python3
"""
🔍 TEST SCHÉMA SUPABASE
Vérifie la structure des données et les colonnes disponibles
"""

import asyncio
import aiohttp
import json

async def test_supabase_schema():
    """Test pour vérifier le schéma et les données Supabase"""
    
    print("🔍 TEST SCHÉMA SUPABASE")
    print("=" * 60)
    
    # Configuration Supabase
    url = "https://ilbihprkxcgsigvueeme.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Test table documents
        print("📋 TEST TABLE DOCUMENTS")
        print("-" * 40)
        
        documents_url = f"{url}/rest/v1/documents"
        params = {
            "company_id": f"eq.{company_id}",
            "select": "*",
            "limit": "3"
        }
        
        async with session.get(documents_url, headers=headers, params=params) as response:
            if response.status == 200:
                documents = await response.json()
                print(f"✅ Documents trouvés: {len(documents)}")
                
                if documents:
                    doc = documents[0]
                    print(f"\n📄 STRUCTURE DU PREMIER DOCUMENT:")
                    for key, value in doc.items():
                        if key == 'embedding_dense' and value:
                            print(f"  {key}: [vector de {len(value) if isinstance(value, list) else 'N/A'} dimensions]")
                        elif key == 'metadata' and value:
                            print(f"  {key}: {json.dumps(value, indent=2)[:100]}...")
                        else:
                            value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                            print(f"  {key}: {value_str}")
                    
                    # Vérifier les colonnes d'embedding
                    embedding_cols = ['embedding', 'embedding_dense', 'embedding_sparse', 'embedding_multi_vector']
                    print(f"\n🔍 COLONNES D'EMBEDDING DISPONIBLES:")
                    for col in embedding_cols:
                        has_data = doc.get(col) is not None
                        data_type = type(doc.get(col)).__name__ if has_data else "None"
                        print(f"  {col}: {'✅' if has_data else '❌'} ({data_type})")
                else:
                    print("❌ Aucun document trouvé pour cette company")
            else:
                error_text = await response.text()
                print(f"❌ Erreur documents {response.status}: {error_text}")
        
        # 2. Test table company_rag_configs
        print(f"\n📋 TEST TABLE COMPANY_RAG_CONFIGS")
        print("-" * 40)
        
        configs_url = f"{url}/rest/v1/company_rag_configs"
        params = {
            "company_id": f"eq.{company_id}",
            "select": "*"
        }
        
        async with session.get(configs_url, headers=headers, params=params) as response:
            if response.status == 200:
                configs = await response.json()
                print(f"✅ Configurations trouvées: {len(configs)}")
                
                if configs:
                    config = configs[0]
                    print(f"\n⚙️ CONFIGURATION COMPANY:")
                    important_fields = ['company_id', 'company_name', 'ai_name', 'secteur_activite', 
                                      'system_prompt_template', 'rag_enabled']
                    for field in important_fields:
                        value = config.get(field)
                        if field == 'system_prompt_template' and value:
                            print(f"  {field}: {value[:100]}...")
                        else:
                            print(f"  {field}: {value}")
                else:
                    print("❌ Aucune configuration trouvée pour cette company")
            else:
                error_text = await response.text()
                print(f"❌ Erreur configs {response.status}: {error_text}")
        
        # 3. Test statistiques générales
        print(f"\n📊 STATISTIQUES GÉNÉRALES")
        print("-" * 40)
        
        # Compter tous les documents
        count_url = f"{url}/rest/v1/documents"
        count_params = {
            "select": "count",
            "company_id": f"eq.{company_id}"
        }
        
        async with session.head(count_url, headers=headers, params=count_params) as response:
            if response.status == 200:
                total_count = response.headers.get('Content-Range', '0').split('/')[-1]
                print(f"📄 Total documents pour company: {total_count}")
            else:
                print(f"⚠️ Impossible de compter les documents")

if __name__ == "__main__":
    print("🚀 Démarrage du test schéma Supabase...")
    asyncio.run(test_supabase_schema())
    print("\n🏁 Test terminé !")
