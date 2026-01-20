#!/usr/bin/env python3
"""
🔧 CONFIGURATION AUTOMATIQUE .env

Aide à configurer correctement le fichier .env pour Botlive
"""

import os
import sys

def check_env_file():
    """Vérifie la configuration du fichier .env"""
    env_path = ".env"
    
    if not os.path.exists(env_path):
        print("❌ Fichier .env non trouvé!")
        print("📝 Crée un fichier .env à la racine du projet")
        return False
    
    print("✅ Fichier .env trouvé")
    
    # Lire le contenu
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n🔍 Vérification des variables...")
    
    # Vérifier variables critiques
    checks = {
        "SUPABASE_URL": "SUPABASE_URL" in content,
        "SUPABASE_SERVICE_KEY": "SUPABASE_SERVICE_KEY" in content,
        "GROQ_API_KEY": "GROQ_API_KEY" in content,
    }
    
    all_ok = True
    for var, present in checks.items():
        status = "✅" if present else "❌"
        print(f"{status} {var}: {'Présent' if present else 'MANQUANT'}")
        if not present:
            all_ok = False
    
    # Avertissement si SUPABASE_KEY présent mais pas SUPABASE_SERVICE_KEY
    if "SUPABASE_KEY=" in content and not "SUPABASE_SERVICE_KEY" in content:
        print("\n⚠️  ATTENTION!")
        print("   Ton .env contient SUPABASE_KEY mais pas SUPABASE_SERVICE_KEY")
        print("   Le système Botlive requiert SUPABASE_SERVICE_KEY (service_role)")
        print("\n💡 Solution:")
        print("   Ajoute cette ligne dans ton .env:")
        print('   SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."')
    
    return all_ok


def suggest_env_template():
    """Affiche un template .env recommandé"""
    print("\n" + "="*80)
    print("📝 TEMPLATE .env RECOMMANDÉ")
    print("="*80)
    
    template = """
# ========= 🤖 LLM APIs =========
GROQ_API_KEY="your-groq-key"

# ========= 🔗 SUPABASE =========
SUPABASE_URL="https://ilbihprkxcgsigvueeme.supabase.co"

# ⚠️ IMPORTANT: service_role key (pas anon key)
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"

PG_CONNECTION_STRING="postgresql://postgres.ilbihprkxcgsigvueeme:Bac2018mado%40@aws-0-eu-west-3.pooler.supabase.com:5432/postgres"

# ========= 🔍 MEILISEARCH =========
MEILISEARCH_HOST="http://127.0.0.1:7700"
MEILISEARCH_KEY="your-master-key"

# ========= ⚡ PERFORMANCE =========
ENABLE_AUTO_LEARNING=true
CACHE_ENABLED=true
HYDE_ENABLED=true
"""
    
    print(template)
    print("="*80)


def main():
    print("="*80)
    print("🔧 CONFIGURATION .env POUR BOTLIVE")
    print("="*80)
    
    all_ok = check_env_file()
    
    if not all_ok:
        print("\n⚠️  Configuration incomplète")
        suggest_env_template()
        print("\n💡 Copie le template ci-dessus et adapte-le")
        return 1
    
    print("\n✅ Configuration semble correcte!")
    print("\n🧪 Prochaine étape:")
    print("   1. Installe EasyOCR: pip install easyocr")
    print("   2. Vérifie système: python tests/verify_botlive_ocr.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
