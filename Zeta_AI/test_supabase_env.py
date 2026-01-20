import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

print("[DEBUG] SUPABASE_KEY:", os.getenv("SUPABASE_KEY"))
print("[DEBUG] SUPABASE_URL:", os.getenv("SUPABASE_URL"))

if not os.getenv("SUPABASE_KEY") or not os.getenv("SUPABASE_URL"):
    print("[ERREUR] Les variables d'environnement ne sont toujours pas détectées. Vérifie le chemin et les permissions du fichier .env !")
else:
    import httpx
    url = os.getenv("SUPABASE_URL") + "/rest/v1/company_rag_configs"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}"
    }
    params = {"select": "system_prompt_template", "company_id": "eq.XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=10)
        print("[TEST] HTTP status:", resp.status_code)
        print("[TEST] HTTP body:", resp.text[:300])
    except Exception as e:
        print("[TEST] Erreur httpx:", e)
