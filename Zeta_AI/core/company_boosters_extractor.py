"""
🎯 COMPANY BOOSTERS EXTRACTOR
Extrait automatiquement les infos clés pour booster la recherche (1 à 1000 entreprises)
"""

import re
from typing import Dict, List, Any, Set
import logging

logger = logging.getLogger(__name__)


def extract_company_boosters(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les boosters de recherche depuis les données d'entreprise
    
    Args:
        company_data: {
            "company_id": "xxx",
            "text_documents": [
                {
                    "content": "...",
                    "metadata": {"type": "product", ...}
                }
            ]
        }
    
    Returns:
        {
            "company_id": "xxx",
            "keywords": ["couches", "yopougon", ...],
            "categories": {
                "PRODUIT": {...},
                "LIVRAISON": {...},
                "PAIEMENT": {...},
                "CONTACT": {...},
                "ENTREPRISE": {...}
            },
            "filters": {
                "price_range": {"min": 13500, "max": 24900},
                "delivery_zones": {"yopougon": 1500, ...},
                "payment_methods": ["Wave"],
                "product_names": ["Couches à pression", ...]
            }
        }
    """
    
    company_id = company_data.get("company_id", "")
    text_documents = company_data.get("text_documents", [])
    
    boosters = {
        "company_id": company_id,
        "keywords": set(),
        "categories": {
            "PRODUIT": {
                "products": [],
                "keywords": set()
            },
            "LIVRAISON": {
                "zones": [],
                "keywords": set()
            },
            "PAIEMENT": {
                "methods": [],
                "keywords": set()
            },
            "CONTACT": {
                "phones": [],
                "keywords": set()
            },
            "ENTREPRISE": {
                "name": "",
                "sector": "",
                "keywords": set()
            }
        },
        "filters": {
            "price_range": {"min": float('inf'), "max": 0},
            "delivery_zones": {},
            "payment_methods": [],
            "product_names": []
        }
    }
    
    for doc in text_documents:
        content = doc.get("content", "")
        content_lower = content.lower()
        metadata = doc.get("metadata", {})
        doc_type = metadata.get("type", "")
        
        # ═══════════════════════════════════════════════════════════
        # CATÉGORIE 1: PRODUIT
        # ═══════════════════════════════════════════════════════════
        if doc_type == "product":
            product_name = metadata.get("product_name", "")
            category = metadata.get("category", "")
            subcategory = metadata.get("subcategory", "")
            price_min = metadata.get("price_min", 0)
            price_max = metadata.get("price_max", 0)
            
            product_info = {
                "name": product_name,
                "category": category,
                "subcategory": subcategory,
                "price_min": price_min,
                "price_max": price_max
            }
            
            boosters["categories"]["PRODUIT"]["products"].append(product_info)
            boosters["filters"]["product_names"].append(product_name)
            
            # Keywords
            if product_name:
                boosters["keywords"].add(product_name.lower())
                boosters["categories"]["PRODUIT"]["keywords"].add(product_name.lower())
                # Mots individuels du nom produit
                for word in product_name.lower().split():
                    if len(word) > 3:  # Ignorer mots courts
                        boosters["keywords"].add(word)
                        boosters["categories"]["PRODUIT"]["keywords"].add(word)
            
            if category:
                boosters["keywords"].add(category.lower())
            
            # Prix range global
            if price_min and price_min < boosters["filters"]["price_range"]["min"]:
                boosters["filters"]["price_range"]["min"] = price_min
            if price_max and price_max > boosters["filters"]["price_range"]["max"]:
                boosters["filters"]["price_range"]["max"] = price_max
        
        # ═══════════════════════════════════════════════════════════
        # CATÉGORIE 2: LIVRAISON
        # ═══════════════════════════════════════════════════════════
        elif doc_type == "delivery":
            zone_names = metadata.get("zone_names", [])
            price = metadata.get("price", metadata.get("price_min", 0))
            
            for zone in zone_names:
                zone_lower = zone.lower()
                
                boosters["categories"]["LIVRAISON"]["zones"].append({
                    "name": zone,
                    "price": price
                })
                boosters["filters"]["delivery_zones"][zone_lower] = price
                
                # Keywords
                boosters["keywords"].add(zone_lower)
                boosters["categories"]["LIVRAISON"]["keywords"].add(zone_lower)
        
        # ═══════════════════════════════════════════════════════════
        # CATÉGORIE 3: PAIEMENT
        # ═══════════════════════════════════════════════════════════
        elif doc_type == "payment":
            methods = metadata.get("methods", [])
            deposit_amount = metadata.get("deposit_amount", 0)
            
            for method in methods:
                boosters["categories"]["PAIEMENT"]["methods"].append({
                    "name": method,
                    "deposit": deposit_amount
                })
                boosters["filters"]["payment_methods"].append(method)
                
                # Keywords
                boosters["keywords"].add(method.lower())
                boosters["categories"]["PAIEMENT"]["keywords"].add(method.lower())
        
        # ═══════════════════════════════════════════════════════════
        # CATÉGORIE 4: CONTACT
        # ═══════════════════════════════════════════════════════════
        elif doc_type == "support":
            phone = metadata.get("phone", "")
            
            if phone:
                # Extraire numéro propre
                phone_clean = re.sub(r'[^\d+]', '', phone)
                boosters["categories"]["CONTACT"]["phones"].append(phone_clean)
                
                # Keywords
                boosters["keywords"].add("contact")
                boosters["keywords"].add("whatsapp")
                boosters["categories"]["CONTACT"]["keywords"].add("contact")
                boosters["categories"]["CONTACT"]["keywords"].add("whatsapp")
        
        # ═══════════════════════════════════════════════════════════
        # CATÉGORIE 5: ENTREPRISE
        # ═══════════════════════════════════════════════════════════
        elif doc_type == "company":
            name = metadata.get("name", "")
            sector = metadata.get("sector", "")
            ai_name = metadata.get("ai_name", "")
            
            boosters["categories"]["ENTREPRISE"]["name"] = name
            boosters["categories"]["ENTREPRISE"]["sector"] = sector
            
            # Keywords
            if name:
                boosters["keywords"].add(name.lower())
                boosters["categories"]["ENTREPRISE"]["keywords"].add(name.lower())
            if sector:
                boosters["keywords"].add(sector.lower())
            if ai_name:
                boosters["keywords"].add(ai_name.lower())
        
        # ═══════════════════════════════════════════════════════════
        # CATÉGORIE 6: LOCALISATION
        # ═══════════════════════════════════════════════════════════
        elif doc_type == "location":
            zone = metadata.get("zone", "")
            
            if zone:
                for z in zone.split(","):
                    z_clean = z.strip().lower()
                    if z_clean:
                        boosters["keywords"].add(z_clean)
    
    # ═══════════════════════════════════════════════════════════
    # CONVERSION SETS → LISTS (pour JSON)
    # ═══════════════════════════════════════════════════════════
    boosters["keywords"] = list(boosters["keywords"])
    
    for category in boosters["categories"].values():
        if "keywords" in category:
            category["keywords"] = list(category["keywords"])
    
    # Nettoyer prix range si vide
    if boosters["filters"]["price_range"]["min"] == float('inf'):
        boosters["filters"]["price_range"]["min"] = 0
    
    logger.info(f"✅ Boosters extraits pour {company_id[:12]}...")
    logger.info(f"   - Keywords: {len(boosters['keywords'])}")
    logger.info(f"   - Produits: {len(boosters['categories']['PRODUIT']['products'])}")
    logger.info(f"   - Zones: {len(boosters['categories']['LIVRAISON']['zones'])}")
    logger.info(f"   - Prix: {boosters['filters']['price_range']['min']} - {boosters['filters']['price_range']['max']} FCFA")
    
    return boosters


def get_boosters_summary(boosters: Dict[str, Any]) -> str:
    """
    Génère un résumé textuel des boosters pour logging
    """
    summary = f"""
📊 BOOSTERS EXTRAITS:
- Company ID: {boosters['company_id'][:20]}...
- Keywords globaux: {len(boosters['keywords'])} mots-clés
- Produits: {len(boosters['categories']['PRODUIT']['products'])} produits
- Zones livraison: {len(boosters['categories']['LIVRAISON']['zones'])} zones
- Méthodes paiement: {len(boosters['categories']['PAIEMENT']['methods'])} méthodes
- Prix range: {boosters['filters']['price_range']['min']} - {boosters['filters']['price_range']['max']} FCFA
"""
    return summary.strip()


# ═══════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test avec données exemple
    test_data = {
        "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb",
        "text_documents": [
            {
                "content": "PRODUIT: Couches à pression...",
                "metadata": {
                    "type": "product",
                    "product_name": "Couches à pression",
                    "category": "Bébé & Puériculture",
                    "price_min": 17900,
                    "price_max": 24900
                }
            },
            {
                "content": "LIVRAISON - ZONES CENTRALES...",
                "metadata": {
                    "type": "delivery",
                    "zone_names": ["Yopougon", "Cocody", "Angré"],
                    "price": 1500
                }
            },
            {
                "content": "PAIEMENT: Wave...",
                "metadata": {
                    "type": "payment",
                    "methods": ["Wave"],
                    "deposit_amount": 2000
                }
            }
        ]
    }
    
    boosters = extract_company_boosters(test_data)
    print(get_boosters_summary(boosters))
    
    import json
    print("\n📋 BOOSTERS JSON:")
    print(json.dumps(boosters, indent=2, ensure_ascii=False))
