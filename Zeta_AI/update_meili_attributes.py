import requests
import json

# CONFIGURATION
MEILI_URL = "http://localhost:7700"
API_KEY = "Bac2018mado@2066"
headers = {"Authorization": f"Bearer {API_KEY}"}

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

def update_all_attributes():
    """Met à jour tous les attributs"""
    print("🔧 MISE À JOUR DES ATTRIBUTS MEILISEARCH")
    print("=" * 60)
    
    # Configuration des attributs par index
    updates = {
        "products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3": {
            "sortableAttributes": ["price", "created_at", "updated_at"],
            "displayedAttributes": ["id", "name", "title", "description", "price", "brand", "category", "color", "sku"]
        },
        "delivery_MpfnlSbqwaZ6F4HvxQLRL9du0yG3": {
            "sortableAttributes": ["price", "delay_abidjan", "delay_hors_abidjan", "created_at"],
            "displayedAttributes": ["id", "zone", "zone_group", "city", "price", "delay_abidjan", "delay_hors_abidjan", "content"]
        },
        "support_paiement_MpfnlSbqwaZ6F4HvxQLRL9du0yG3": {
            "sortableAttributes": ["created_at", "updated_at"],
            "displayedAttributes": ["id", "faq_question", "content", "tags", "language", "title"]
        },
        "company_docs_MpfnlSbqwaZ6F4HvxQLRL9du0yG3": {
            "sortableAttributes": ["created_at", "updated_at", "section"],
            "displayedAttributes": ["id", "title", "content", "section", "language", "file_name"]
        },
        "localisation_MpfnlSbqwaZ6F4HvxQLRL9du0yG3": {
            "sortableAttributes": ["created_at", "updated_at"],
            "displayedAttributes": ["id", "title", "content", "name"]
        }
    }
    
    success_count = 0
    for index_name, attributes in updates.items():
        if update_index_attributes(index_name, attributes):
            success_count += 1
    
    print(f"\n✅ {success_count}/{len(updates)} index mis à jour avec succès")

if __name__ == "__main__":
    update_all_attributes()






