import asyncio
import os
import json
from supabase import create_client
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def check_catalog(company_id):
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"🔍 Recherche du catalogue pour: {company_id}")
    
    resp = (
        client.table("company_catalogs_v2")
        .select("catalog")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .execute()
    )
    
    data = getattr(resp, "data", None) or []
    print(f"📊 Nombre de catalogues actifs trouvés: {len(data)}")
    
    for i, row in enumerate(data):
        catalog = row.get("catalog")
        print(f"\n--- Catalogue {i+1} ---")
        print(f"Type: {type(catalog)}")
        
        if isinstance(catalog, dict):
            pid = catalog.get("product_id")
            pname = catalog.get("product_name") or catalog.get("name")
            print(f"✅ Clé 'product_id' trouvée: {pid}")
            print(f"✅ Clé 'product_name' trouvée: {pname}")
            
            if not pid:
                print("❌ ERREUR: 'product_id' est manquant à la racine du JSON!")
                print("Contenu des clés à la racine:", list(catalog.keys()))
        else:
            print("❌ ERREUR: Le catalogue n'est pas un dictionnaire!")

if __name__ == "__main__":
    cid = "W27PwOPiblP8TlOrhPcjOtxd0cza"
    asyncio.run(check_catalog(cid))
