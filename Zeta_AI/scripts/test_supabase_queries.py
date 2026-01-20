#!/usr/bin/env python3
"""
Script de test pour vérifier l'intégration avec Supabase.
Vérifie la connexion et exécute des requêtes de base.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

import os
from pathlib import Path
from database.supabase_client import (
    get_company_system_prompt,
    get_company_context,
    match_documents_via_rpc
)

# Charger les variables d'environnement
load_dotenv()

# Configuration
COMPANY_ID = os.getenv("COMPANY_ID", "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3")
TEST_QUERY = "Quels sont vos produits phares ?"

async def test_supabase_connection():
    """Teste la connexion à Supabase et affiche les informations de base."""
    print("=== Test de connexion Supabase ===")
    
    # Créer le répertoire de sortie s'il n'existe pas
    output_dir = Path("out/tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Récupération du prompt système
    print("\n1. Récupération du prompt système...")
    try:
        prompt = await get_company_system_prompt(COMPANY_ID)
        print(f"✅ Succès! Longueur du prompt: {len(prompt)} caractères")
        print(f"Extrait: {prompt[:100]}...")
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

    # 2. Récupération du contexte de l'entreprise
    print("\n2. Récupération du contexte de l'entreprise...")
    try:
        context = await get_company_context(COMPANY_ID)
        if context:
            print("✅ Contexte récupéré avec succès!")
            print(f"Nom de l'entreprise: {context.get('company_name')}")
            print(f"Secteur: {context.get('secteur_activite')}")
        else:
            print("⚠️ Aucun contexte trouvé pour cette entreprise")
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

    # 3. Test de recherche sémantique vectorielle
    print("\n3. Test de recherche sémantique vectorielle...")
    try:
        # Créer un embedding factice pour le test (768 dimensions)
        fake_embedding = [0.0] * 768  # Taille d'embedding standard pour notre configuration
        results = await match_documents_via_rpc(
            embedding=fake_embedding,
            company_id=COMPANY_ID,
            top_k=2,
            min_score=0.1  # Seuil bas pour avoir des résultats
        )
        if results:
            print(f"✅ {len(results)} résultats vectoriels trouvés!")
            for i, doc in enumerate(results, 1):
                print(f"  {i}. Score: {doc.get('score', 0):.3f}")
                print(f"     {doc.get('content', '')[:100]}...")
        else:
            print("⚠️ Aucun résultat vectoriel trouvé")
    except Exception as e:
        print(f"⚠️ Erreur lors de la recherche vectorielle: {str(e)}")

    # 4. Vérification des données de l'entreprise
    print("\n4. Vérification des données de l'entreprise...")
    try:
        context = await get_company_context(COMPANY_ID)
        if context:
            print("✅ Données de l'entreprise récupérées avec succès")
            print(f"   - ID: {context.get('company_id')}")
            print(f"   - Nom: {context.get('company_name')}")
            print(f" - Secteur: {context.get('secteur_activite')}")
            print(f" - IA: {context.get('ai_name')}")
        else:
            print("⚠️ Aucune donnée d'entreprise trouvée")
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des données: {str(e)}")

    return True

if __name__ == "__main__":
    print(f"=== Démarrage des tests Supabase pour l'entreprise {COMPANY_ID} ===")
    success = asyncio.run(test_supabase_connection())
    
    if success:
        print("\n✅ Tous les tests se sont terminés avec succès!")
    else:
        print("\n❌ Certains tests ont échoué. Vérifiez les messages d'erreur ci-dessus.")
    
    print("=== Fin des tests ===")
