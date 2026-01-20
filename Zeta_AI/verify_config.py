#!/usr/bin/env python3
"""
Script pour vérifier que la configuration Meilisearch optimisée est appliquée
"""

import os
import sys
import meilisearch
import json

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILISEARCH_KEY", "")

def verify_config(company_id: str):
    """Vérifie la configuration pour une entreprise donnée"""
    
    if not MEILI_KEY:
        print("❌ ERREUR: Variable MEILISEARCH_KEY non définie")
        return False
    
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        index_name = f"company_docs_{company_id}"
        
        print(f"🔍 Vérification de la configuration pour: {index_name}")
        print("=" * 60)
        
        # 1. Vérifier que l'index existe
        try:
            stats = client.index(index_name).get_stats()
            doc_count = stats.numberOfDocuments if hasattr(stats, 'numberOfDocuments') else stats.get('numberOfDocuments', 0)
            print(f"📊 Index: {index_name}")
            print(f"📄 Documents: {doc_count}")
        except Exception as e:
            print(f"❌ Index non trouvé: {e}")
            return False
        
        # 2. Vérifier la configuration complète
        settings = client.index(index_name).get_settings()
        
        # 3. Vérifier les attributs de recherche
        searchable = settings.get("searchableAttributes", [])
        expected_searchable = ["searchable_text", "content_fr", "product_name", "color", "tags", "zone", "method"]
        
        print(f"\n🔍 ATTRIBUTS DE RECHERCHE:")
        print(f"Configurés: {searchable}")
        
        missing_attrs = [attr for attr in expected_searchable if attr not in searchable]
        if missing_attrs:
            print(f"❌ Attributs manquants: {missing_attrs}")
            config_ok = False
        else:
            print("✅ Tous les attributs prioritaires présents")
            config_ok = True
        
        # 4. Vérifier les synonymes
        synonyms = settings.get("synonyms", {})
        print(f"\n🔄 SYNONYMES:")
        if synonyms:
            print(f"✅ {len(synonyms)} groupes de synonymes configurés")
            key_synonyms = ["cocody", "abidjan", "casque", "noir", "bleu"]
            for key in key_synonyms:
                if key in synonyms:
                    print(f"  • {key}: {synonyms[key]}")
        else:
            print("❌ Aucun synonyme configuré")
            config_ok = False
        
        # 5. Vérifier la tolérance aux fautes
        typo_config = settings.get("typoTolerance", {})
        print(f"\n🔤 TOLÉRANCE AUX FAUTES:")
        if typo_config.get("enabled"):
            print("✅ Tolérance activée")
            disabled_words = typo_config.get("disableOnWords", [])
            disabled_attrs = typo_config.get("disableOnAttributes", [])
            if disabled_words:
                print(f"  • Mots désactivés: {disabled_words}")
            if disabled_attrs:
                print(f"  • Attributs désactivés: {disabled_attrs}")
        else:
            print("⚠️ Tolérance non configurée")
        
        # 6. Vérifier les stop-words
        stop_words = settings.get("stopWords", [])
        print(f"\n🚫 STOP-WORDS:")
        if stop_words:
            print(f"✅ {len(stop_words)} stop-words configurés: {stop_words[:10]}...")
        else:
            print("⚠️ Aucun stop-word configuré")
        
        # 7. Vérifier les règles de classement
        ranking_rules = settings.get("rankingRules", [])
        print(f"\n📊 RÈGLES DE CLASSEMENT:")
        print(f"Configurées: {ranking_rules}")
        
        print("\n" + "=" * 60)
        if config_ok:
            print("✅ CONFIGURATION OPTIMISÉE APPLIQUÉE")
        else:
            print("❌ CONFIGURATION INCOMPLÈTE")
        
        return config_ok
        
    except Exception as e:
        print(f"❌ Erreur vérification: {e}")
        return False

def list_company_indexes():
    """Liste tous les index d'entreprises disponibles"""
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        indexes = client.get_indexes()
        
        company_indexes = []
        for index in indexes['results']:
            if index['uid'].startswith('company_docs_'):
                company_id = index['uid'].replace('company_docs_', '')
                company_indexes.append(company_id)
        
        return company_indexes
    except Exception as e:
        print(f"❌ Erreur listage des index: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1:
        company_id = sys.argv[1]
        verify_config(company_id)
    else:
        print("🏢 Index d'entreprises disponibles:")
        companies = list_company_indexes()
        if companies:
            for i, company in enumerate(companies, 1):
                print(f"{i}. {company}")
            print(f"\nUsage: python3 verify_config.py COMPANY_ID")
            print(f"Exemple: python3 verify_config.py {companies[0]}")
        else:
            print("Aucun index d'entreprise trouvé")
