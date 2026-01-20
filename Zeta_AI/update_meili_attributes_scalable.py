import requests
import json

# CONFIGURATION
MEILI_URL = "http://localhost:7700"
API_KEY = "Bac2018mado@2066"
headers = {"Authorization": f"Bearer {API_KEY}"}

def get_all_indexes():
    """Récupère tous les index"""
    response = requests.get(f"{MEILI_URL}/indexes", headers=headers)
    return response.json()

def update_index_attributes(index_name, attributes):
    """Met à jour les attributs d'un index"""
    try:
        response = requests.patch(
            f"{MEILI_URL}/indexes/{index_name}/settings",
            headers={**headers, "Content-Type": "application/json"},
            json=attributes
        )
        print(f"✅ {index_name}: {response.status_code}")
        if response.status_code != 202:
            print(f"   Erreur: {response.text}")
        return response.status_code == 202
    except Exception as e:
        print(f"❌ {index_name}: {e}")
        return False

def get_attributes_by_index_type(index_name):
    """Retourne les attributs optimisés selon le type d'index"""
    
    # Index de produits
    if index_name.startswith("products_"):
        return {
            "sortableAttributes": ["price", "created_at", "updated_at", "stock"],
            "displayedAttributes": ["id", "name", "title", "description", "price", "brand", "category", "color", "sku", "stock"]
        }
    
    # Index de livraison
    elif index_name.startswith("delivery_"):
        return {
            "sortableAttributes": ["price", "delay_abidjan", "delay_hors_abidjan", "created_at"],
            "displayedAttributes": ["id", "zone", "zone_group", "city", "price", "delay_abidjan", "delay_hors_abidjan", "content", "area"]
        }
    
    # Index de support/paiement
    elif index_name.startswith("support_") or index_name.startswith("support_paiement_"):
        return {
            "sortableAttributes": ["created_at", "updated_at", "priority"],
            "displayedAttributes": ["id", "faq_question", "content", "tags", "language", "title", "answer"]
        }
    
    # Index de documents d'entreprise
    elif index_name.startswith("company_docs_"):
        return {
            "sortableAttributes": ["created_at", "updated_at", "section", "priority"],
            "displayedAttributes": ["id", "title", "content", "section", "language", "file_name", "type"]
        }
    
    # Index de localisation
    elif index_name.startswith("localisation_") or index_name.startswith("LOCALISATION_"):
        return {
            "sortableAttributes": ["created_at", "updated_at", "priority"],
            "displayedAttributes": ["id", "title", "content", "name", "zone", "city"]
        }
    
    # Index générique (fallback)
    else:
        return {
            "sortableAttributes": ["created_at", "updated_at"],
            "displayedAttributes": ["id", "title", "content", "name", "type"]
        }

def update_all_indexes_scalable():
    """Met à jour TOUS les index de manière scalable"""
    print("🔧 MISE À JOUR SCALABLE DES ATTRIBUTS MEILISEARCH")
    print("=" * 70)
    
    # Récupérer tous les index
    indexes_data = get_all_indexes()
    all_indexes = indexes_data.get('results', [])
    
    print(f"📊 {len(all_indexes)} index trouvés")
    
    success_count = 0
    for index_info in all_indexes:
        index_name = index_info['uid']
        
        # Ignorer les index de test
        if "test" in index_name.lower():
            print(f"⏭️  {index_name}: Ignoré (index de test)")
            continue
        
        # Obtenir les attributs optimisés selon le type
        attributes = get_attributes_by_index_type(index_name)
        
        print(f"\n🔧 Mise à jour de {index_name}...")
        print(f"   Type détecté: {index_name.split('_')[0]}")
        print(f"   Attributs: {json.dumps(attributes, indent=4)}")
        
        if update_index_attributes(index_name, attributes):
            success_count += 1
    
    print(f"\n✅ {success_count}/{len([i for i in all_indexes if 'test' not in i['uid'].lower()])} index mis à jour avec succès")
    print("\n🚀 SYSTÈME SCALABLE CONFIGURÉ !")
    print("   - Tous les index sont optimisés")
    print("   - Configuration automatique par type")
    print("   - Prêt pour de nouveaux company_id")

if __name__ == "__main__":
    update_all_indexes_scalable()






