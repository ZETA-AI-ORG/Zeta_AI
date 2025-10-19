#!/usr/bin/env python3
"""
Script de test simplifié pour l'intégration Supabase.
Vérifie uniquement les fonctionnalités critiques.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Configuration du path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from database.supabase_client import get_company_system_prompt, get_company_context

# Charger les variables d'environnement
load_dotenv()

# Configuration
COMPANY_ID = os.getenv("COMPANY_ID", "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3")

async def test_supabase_connection():
    """Teste la connexion et les fonctionnalités de base de Supabase."""
    print("=== Test d'intégration Supabase ===\n")
    
    # 1. Test de récupération du prompt système
    print("1. Test de récupération du prompt système...")
    try:
        prompt = await get_company_system_prompt(COMPANY_ID)
        if prompt:
            print(f"✅ Succès! Longueur du prompt: {len(prompt)} caractères")
            print(f"Extrait: {prompt[:150]}...")
        else:
            print("⚠️ Aucun prompt système trouvé")
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

    # 2. Test de récupération du contexte entreprise
    print("\n2. Test de récupération du contexte entreprise...")
    try:
        context = await get_company_context(COMPANY_ID)
        if context:
            print("✅ Contexte récupéré avec succès!")
            print(f"ID: {context.get('id')}")
            print(f"Nom: {context.get('company_name')}")
            print(f"Secteur: {context.get('secteur_activite')}")
            print(f"IA: {context.get('ai_name')}")
            print(f"RAG activé: {context.get('rag_enabled', False)}")
        else:
            print("⚠️ Aucun contexte trouvé pour cette entreprise")
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

    print("\n=== Tests de base terminés avec succès ===\n")
    print("Pour les tests avancés de recherche vectorielle, veuillez vérifier")
    print("la configuration de la fonction RPC dans Supabase.")
    
    return True

if __name__ == "__main__":
    print(f"=== Démarrage des tests pour l'entreprise {COMPANY_ID} ===")
    success = asyncio.run(test_supabase_connection())
    
    if success:
        print("\n✅ Les tests de base se sont terminés avec succès!")
    else:
        print("\n❌ Certains tests ont échoué. Vérifiez les messages d'erreur ci-dessus.")
    
    print("\n=== Fin des tests ===")
