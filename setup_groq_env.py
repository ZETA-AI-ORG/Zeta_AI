#!/usr/bin/env python3
"""
🔑 CONFIGURATION GROQ API KEY
Script pour configurer la clé API Groq dans l'environnement
"""

import os
import sys

def setup_groq_key():
    """Configure la clé API Groq"""
    
    print("🔑 CONFIGURATION GROQ API KEY")
    print("=" * 40)
    
    # Vérifier si la clé existe déjà
    existing_key = os.getenv("GROQ_API_KEY")
    if existing_key:
        print(f"✅ Clé API Groq déjà configurée: {existing_key[:10]}...")
        return existing_key
    
    # Demander la clé à l'utilisateur
    print("⚠️ Clé API Groq non trouvée dans l'environnement")
    print("📝 Veuillez entrer votre clé API Groq:")
    
    api_key = input("Clé API Groq: ").strip()
    
    if not api_key:
        print("❌ Clé API vide - Abandon")
        return None
    
    # Définir la variable d'environnement
    os.environ["GROQ_API_KEY"] = api_key
    
    print(f"✅ Clé API Groq configurée: {api_key[:10]}...")
    
    # Créer un fichier .env pour persistance
    try:
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nGROQ_API_KEY={api_key}\n")
        print("💾 Clé sauvegardée dans .env")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde .env: {e}")
    
    return api_key

if __name__ == "__main__":
    key = setup_groq_key()
    if key:
        print("\n🚀 Configuration terminée - Vous pouvez maintenant lancer les tests")
    else:
        print("\n❌ Configuration échouée")
        sys.exit(1)
