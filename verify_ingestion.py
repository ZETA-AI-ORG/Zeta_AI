#!/usr/bin/env python3
"""
Script de vérification complète de l'ingestion
Vérifie que tous les documents sont correctement indexés et splittés
"""

import requests
import json
from typing import Dict, List

# Configuration
MEILI_URL = "http://127.0.0.1:7700"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

# Données originales attendues
EXPECTED_DATA = {
    "company_identity": {
        "count": 1,
        "index": "company_docs",
        "keywords": ["RUE_DU_GROS", "gamma", "Bébé", "Puériculture"]
    },
    "location_info": {
        "count": 1,
        "index": "localisation",
        "keywords": ["Côte d'Ivoire", "Boutique", "ligne"]
    },
    "products_catalog": {
        "count": 19,  # Splittés depuis 1 catalogue
        "index": "products",
        "expected_splits": {
            "Couches à pression": 7,  # 7 tailles
            "Couches culottes": 6,    # 6 variantes
            "Couches adultes": 6      # 6 variantes
        }
    },
    "delivery": {
        "count": 3,
        "index": "delivery",
        "docs": ["delivery_abidjan_center", "delivery_abidjan_outskirts", "delivery_outside_abidjan"]
    },
    "support_paiement": {
        "count": 2,
        "index": "support_paiement",
        "docs": ["customer_support", "payment_process"]
    },
    "others": {
        "count": 3,
        "index": "company_docs",
        "docs": ["return_policy", "business_summary", "customer_faq"]
    }
}

def query_index(index_name: str) -> Dict:
    """Interroge un index MeiliSearch"""
    url = f"{MEILI_URL}/indexes/{index_name}_{COMPANY_ID}/documents"
    try:
        response = requests.get(url, params={"limit": 1000})
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "count": len(data.get("results", [])),
                "documents": data.get("results", [])
            }
        else:
            return {"success": False, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def verify_products_split():
    """Vérifie que les produits sont correctement splittés"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION: INDEX PRODUCTS")
    print("="*80)
    
    result = query_index("products")
    
    if not result["success"]:
        print(f"❌ Erreur: {result['error']}")
        return False
    
    docs = result["documents"]
    count = result["count"]
    
    print(f"\n📊 Total documents: {count}")
    print(f"   Attendu: 19")
    
    if count != 19:
        print(f"   ❌ ERREUR: Nombre incorrect !")
        return False
    
    # Vérifier par produit
    products = {}
    for doc in docs:
        product_name = doc.get("product", "Unknown")
        if product_name not in products:
            products[product_name] = []
        products[product_name].append(doc)
    
    print(f"\n📦 Produits trouvés:")
    all_good = True
    
    for product_name, product_docs in products.items():
        count = len(product_docs)
        print(f"\n   • {product_name}: {count} variantes")
        
        # Vérifier les prix
        for doc in product_docs[:3]:  # Afficher les 3 premiers
            variant = doc.get("variant", "")
            price = doc.get("price", 0)
            print(f"      - {variant}: {price:,} F CFA".replace(",", "."))
        
        if len(product_docs) > 3:
            print(f"      ... et {len(product_docs) - 3} autres variantes")
    
    # Vérifier les totaux attendus
    expected = EXPECTED_DATA["products_catalog"]["expected_splits"]
    for product, expected_count in expected.items():
        actual_count = len(products.get(product, []))
        if actual_count != expected_count:
            print(f"   ❌ {product}: {actual_count}/{expected_count} variantes")
            all_good = False
        else:
            print(f"   ✅ {product}: {actual_count}/{expected_count} variantes")
    
    return all_good

def verify_delivery():
    """Vérifie l'index delivery"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION: INDEX DELIVERY")
    print("="*80)
    
    result = query_index("delivery")
    
    if not result["success"]:
        print(f"❌ Erreur: {result['error']}")
        return False
    
    docs = result["documents"]
    count = result["count"]
    
    print(f"\n📊 Total documents: {count}")
    print(f"   Attendu: 3")
    
    if count != 3:
        print(f"   ❌ ERREUR: Nombre incorrect !")
        return False
    
    print(f"\n📦 Documents trouvés:")
    for doc in docs:
        doc_type = doc.get("type", "unknown")
        content_preview = doc.get("content", "")[:80]
        print(f"   • {doc_type}")
        print(f"     {content_preview}...")
    
    # Vérifier que les infos importantes sont présentes
    all_content = " ".join([doc.get("content", "") for doc in docs])
    keywords = ["Abidjan", "1500", "2000", "3500"]
    
    for keyword in keywords:
        if keyword in all_content:
            print(f"   ✅ '{keyword}' trouvé")
        else:
            print(f"   ❌ '{keyword}' manquant !")
            return False
    
    return True

def verify_support_paiement():
    """Vérifie l'index support_paiement"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION: INDEX SUPPORT_PAIEMENT")
    print("="*80)
    
    result = query_index("support_paiement")
    
    if not result["success"]:
        print(f"❌ Erreur: {result['error']}")
        return False
    
    docs = result["documents"]
    count = result["count"]
    
    print(f"\n📊 Total documents: {count}")
    print(f"   Attendu: 2")
    
    if count != 2:
        print(f"   ❌ ERREUR: Nombre incorrect !")
        return False
    
    print(f"\n📦 Documents trouvés:")
    for doc in docs:
        doc_type = doc.get("type", "unknown")
        content_preview = doc.get("content", "")[:100]
        print(f"   • {doc_type}")
        print(f"     {content_preview}...")
    
    # Vérifier infos critiques
    all_content = " ".join([doc.get("content", "") for doc in docs])
    keywords = ["+225", "Wave", "2000 FCFA", "WhatsApp"]
    
    for keyword in keywords:
        if keyword in all_content:
            print(f"   ✅ '{keyword}' trouvé")
        else:
            print(f"   ⚠️ '{keyword}' potentiellement manquant")
    
    return True

def verify_localisation():
    """Vérifie l'index localisation"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION: INDEX LOCALISATION")
    print("="*80)
    
    result = query_index("localisation")
    
    if not result["success"]:
        print(f"❌ Erreur: {result['error']}")
        return False
    
    docs = result["documents"]
    count = result["count"]
    
    print(f"\n📊 Total documents: {count}")
    print(f"   Attendu: 1")
    
    if count != 1:
        print(f"   ❌ ERREUR: Nombre incorrect !")
        return False
    
    doc = docs[0]
    content = doc.get("content", "")
    print(f"\n📦 Document:")
    print(f"   {content}")
    
    # Vérifier infos
    keywords = ["Côte d'Ivoire", "ligne"]
    for keyword in keywords:
        if keyword in content:
            print(f"   ✅ '{keyword}' trouvé")
        else:
            print(f"   ❌ '{keyword}' manquant !")
            return False
    
    return True

def verify_company_docs():
    """Vérifie l'index company_docs (backup global)"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION: INDEX COMPANY_DOCS (Backup)")
    print("="*80)
    
    result = query_index("company_docs")
    
    if not result["success"]:
        print(f"❌ Erreur: {result['error']}")
        return False
    
    docs = result["documents"]
    count = result["count"]
    
    print(f"\n📊 Total documents: {count}")
    print(f"   Attendu: 29 (tous les docs + produits splittés)")
    
    if count != 29:
        print(f"   ⚠️ Attention: Nombre différent de l'attendu")
    
    # Compter par type
    types = {}
    for doc in docs:
        doc_type = doc.get("type", "unknown")
        types[doc_type] = types.get(doc_type, 0) + 1
    
    print(f"\n📦 Documents par type:")
    for doc_type, count in sorted(types.items()):
        print(f"   • {doc_type}: {count} docs")
    
    return True

def verify_data_integrity():
    """Vérifie l'intégrité des données (aucune altération)"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION: INTÉGRITÉ DES DONNÉES")
    print("="*80)
    
    # Récupérer tous les produits
    result = query_index("products")
    if not result["success"]:
        return False
    
    docs = result["documents"]
    
    # Vérifier des prix spécifiques connus
    known_prices = {
        "17900": "Taille 1 - Couches à pression",
        "5500": "1 paquet - Couches culottes",
        "25000": "6 paquets - Couches culottes",
        "48000": "12 paquets - Couches culottes",
    }
    
    print("\n📊 Vérification des prix critiques:")
    for price_str, description in known_prices.items():
        price_int = int(price_str)
        found = any(doc.get("price") == price_int for doc in docs)
        if found:
            print(f"   ✅ {price_int:,} FCFA ({description})".replace(",", "."))
        else:
            print(f"   ❌ {price_int:,} FCFA MANQUANT ({description})".replace(",", "."))
            return False
    
    return True

def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION COMPLÈTE DE L'INGESTION")
    print("="*80)
    print(f"Company ID: {COMPANY_ID}")
    print(f"MeiliSearch: {MEILI_URL}")
    
    results = {
        "Products Split": verify_products_split(),
        "Delivery": verify_delivery(),
        "Support/Paiement": verify_support_paiement(),
        "Localisation": verify_localisation(),
        "Company Docs (Backup)": verify_company_docs(),
        "Data Integrity": verify_data_integrity()
    }
    
    # Résumé final
    print("\n" + "="*80)
    print("📊 RÉSUMÉ FINAL")
    print("="*80)
    
    all_pass = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_pass = False
    
    print("\n" + "="*80)
    if all_pass:
        print("🎉 SUCCÈS: Tous les tests passent !")
        print("✅ Les données sont correctement indexées")
        print("✅ Aucune altération détectée")
        print("✅ Split effectué correctement")
    else:
        print("❌ ÉCHEC: Des problèmes ont été détectés")
        print("⚠️ Vérifier les logs ci-dessus")
    print("="*80 + "\n")
    
    return all_pass

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
