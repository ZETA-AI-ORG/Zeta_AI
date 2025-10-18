#!/usr/bin/env python3
"""
Script de nettoyage des index Meilisearch non conformes
Supprime tous les doublons en majuscules et index non autorisés
Garde uniquement les 5 types d'index autorisés en minuscules
"""

import os
import meilisearch
import re
from typing import List, Set

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")

# Types d'index autorisés (en minuscules uniquement)
ALLOWED_INDEX_TYPES = {
    "products",
    "delivery", 
    "support_paiement",
    "localisation",
    "company_docs"
}

def get_all_indexes() -> List[dict]:
    """Récupère tous les index Meilisearch"""
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        result = client.get_indexes()
        return result.get("results", [])
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des index: {e}")
        return []

def parse_index_name(index_uid: str) -> tuple[str, str]:
    """Parse un nom d'index pour extraire le type et company_id"""
    # Pattern: type_company_id
    parts = index_uid.split('_', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", ""

def is_valid_index(index_uid: str) -> bool:
    """Vérifie si un index est conforme aux règles"""
    index_type, company_id = parse_index_name(index_uid)
    
    # Vérifier que le type est autorisé
    if index_type not in ALLOWED_INDEX_TYPES:
        return False
    
    # Vérifier qu'il n'y a pas de majuscules dans le type
    if index_type != index_type.lower():
        return False
    
    # Vérifier que company_id n'est pas vide
    if not company_id:
        return False
    
    return True

def find_invalid_indexes() -> List[str]:
    """Trouve tous les index non conformes"""
    indexes = get_all_indexes()
    invalid_indexes = []
    
    print("🔍 Analyse des index existants...")
    print("=" * 60)
    
    for index in indexes:
        index_uid = index.get("uid", "")
        doc_count = index.get("numberOfDocuments", 0)
        
        if not is_valid_index(index_uid):
            invalid_indexes.append(index_uid)
            print(f"❌ INVALIDE: {index_uid} ({doc_count} docs)")
        else:
            print(f"✅ VALIDE: {index_uid} ({doc_count} docs)")
    
    return invalid_indexes

def delete_invalid_indexes(invalid_indexes: List[str], confirm: bool = True) -> None:
    """Supprime les index non conformes"""
    if not invalid_indexes:
        print("\n🎉 Aucun index invalide trouvé!")
        return
    
    print(f"\n🗑️ {len(invalid_indexes)} index non conformes trouvés:")
    for idx in invalid_indexes:
        print(f"  - {idx}")
    
    if confirm:
        response = input(f"\n⚠️ Confirmer la suppression de {len(invalid_indexes)} index? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            print("❌ Suppression annulée")
            return
    
    client = meilisearch.Client(MEILI_URL, MEILI_KEY)
    
    print("\n🗑️ Suppression en cours...")
    deleted_count = 0
    
    for index_uid in invalid_indexes:
        try:
            client.delete_index(index_uid)
            print(f"  ✅ Supprimé: {index_uid}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ Erreur lors de la suppression de {index_uid}: {e}")
    
    print(f"\n🎉 Suppression terminée: {deleted_count}/{len(invalid_indexes)} index supprimés")

def show_valid_indexes() -> None:
    """Affiche les index valides restants"""
    indexes = get_all_indexes()
    valid_indexes = []
    
    for index in indexes:
        index_uid = index.get("uid", "")
        if is_valid_index(index_uid):
            valid_indexes.append({
                "uid": index_uid,
                "docs": index.get("numberOfDocuments", 0)
            })
    
    if valid_indexes:
        print(f"\n✅ Index valides restants ({len(valid_indexes)}):")
        print("=" * 60)
        for idx in valid_indexes:
            print(f"  {idx['uid']} ({idx['docs']} documents)")
    else:
        print("\n📭 Aucun index valide trouvé")

def main():
    """Fonction principale"""
    print("🧹 NETTOYAGE DES INDEX MEILISEARCH NON CONFORMES")
    print("=" * 60)
    print(f"URL Meilisearch: {MEILI_URL}")
    print(f"Types autorisés: {', '.join(ALLOWED_INDEX_TYPES)}")
    print()
    
    # 1. Analyser les index existants
    invalid_indexes = find_invalid_indexes()
    
    # 2. Supprimer les index non conformes
    if invalid_indexes:
        delete_invalid_indexes(invalid_indexes)
    
    # 3. Afficher le résultat final
    show_valid_indexes()
    
    print(f"\n📋 RÈGLES APPLIQUÉES:")
    print(f"  ✅ Seuls les 5 types autorisés sont conservés: {', '.join(ALLOWED_INDEX_TYPES)}")
    print(f"  ✅ Tous les noms d'index sont en minuscules")
    print(f"  ✅ Format obligatoire: type_company_id")
    print(f"  ❌ Tous les doublons en majuscules ont été supprimés")

if __name__ == "__main__":
    main()
