import os

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[DEBUG] .env chargé avec load_dotenv() !")
except ImportError:
    print("[DEBUG] python-dotenv non installé, skip load_dotenv()")

print("[DEBUG] SUPABASE_KEY:", os.getenv("SUPABASE_KEY"))
print("[DEBUG] SUPABASE_URL:", os.getenv("SUPABASE_URL"))

# Vérifie aussi les variables dans le module config.py si utilisé
try:
    import config
    print("[DEBUG] config.SUPABASE_KEY:", getattr(config, "SUPABASE_KEY", None))
    print("[DEBUG] config.SUPABASE_URL:", getattr(config, "SUPABASE_URL", None))
except ImportError:
    print("[DEBUG] Pas de module config.py trouvé.")

# Test simple d'appel API (optionnel)
try:
    import httpx
    url = os.getenv("SUPABASE_URL") + "/rest/v1/company_rag_configs"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}"
    }
    resp = httpx.get(url, headers=headers, timeout=10)
    print("[DEBUG] HTTP status:", resp.status_code)
    print("[DEBUG] HTTP body:", resp.text[:200])
except Exception as e:
    print("[DEBUG] Erreur httpx:", e)
