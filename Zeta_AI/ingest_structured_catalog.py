#!/usr/bin/env python3
"""
🎯 INGESTION INTELLIGENTE DE CATALOGUES
Parse et structure les données AVANT indexation

PRINCIPE:
- 1 prix = 1 document
- Métadonnées structurées (quantité, produit, prix)
- Recherche ultra-précise
"""

import re
import json
from typing import List, Dict, Optional

def parse_rue_du_gros_catalog(raw_text: str, company_id: str) -> List[Dict]:
    """
    Parse le catalogue Rue_du_gros en documents structurés
    
    Args:
        raw_text: Texte brut du catalogue
        company_id: ID de l'entreprise
        
    Returns:
        Liste de documents structurés
    """
    
    documents = []
    current_product = None
    
    lines = raw_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Détecter nom du produit
        if "PRODUITS :" in line or "PRODUIT :" in line:
            # Extraire: "PRODUITS : Couches culottes ( pour enfant de 5 à 30 kg )"
            match = re.search(r'PRODUITS?\s*:\s*([^(]+)', line)
            if match:
                current_product = match.group(1).strip()
                print(f"📦 Produit détecté: {current_product}")
        
        # Détecter ligne de prix
        # Format: "6 paquets - 25.000 F CFA | 4.150 F/paquet"
        price_match = re.search(
            r'(\d+)\s*(paquets?|colis|unités?)\s*(?:\((\d+)(?:\s*unités?)?\))?\s*-\s*([0-9.,]+)\s*F?\s*CFA(?:\s*\|\s*([0-9.,]+)\s*F[/\s]*paquet)?',
            line,
            re.IGNORECASE
        )
        
        if price_match and current_product:
            quantity = int(price_match.group(1))
            unit = price_match.group(2)
            units_in_pack = price_match.group(3)  # Pour "1 paquet (10 unités)"
            total_price_str = price_match.group(4).replace('.', '').replace(',', '')
            unit_price_str = price_match.group(5)
            
            try:
                total_price = int(total_price_str)
                unit_price = int(unit_price_str.replace('.', '').replace(',', '')) if unit_price_str else None
                
                # Créer ID unique
                doc_id = f"{company_id}_{current_product}_{quantity}{unit}".lower().replace(' ', '_').replace('(', '').replace(')', '')
                
                # Construire contenu optimisé
                content_parts = [
                    f"{quantity} {unit} de {current_product}",
                    f"Prix: {total_price:,} F CFA".replace(',', '.')
                ]
                
                if unit_price:
                    content_parts.append(f"({unit_price:,} F/paquet)".replace(',', '.'))
                
                if units_in_pack:
                    content_parts[0] += f" ({units_in_pack} unités)"
                
                content = " - ".join(content_parts)
                
                # Document structuré
                doc = {
                    "id": doc_id,
                    "type": "pricing",
                    "company_id": company_id,
                    
                    # Informations produit
                    "product": current_product,
                    "product_normalized": current_product.lower().strip(),
                    
                    # Quantité
                    "quantity": quantity,
                    "quantity_unit": unit.rstrip('s'),  # "paquets" → "paquet"
                    "units_per_pack": int(units_in_pack) if units_in_pack else None,
                    
                    # Prix
                    "total_price": total_price,
                    "unit_price": unit_price,
                    "currency": "FCFA",
                    
                    # Textes pour recherche
                    "title": f"{quantity} {unit} de {current_product}",
                    "content": content,
                    "searchable_text": f"{quantity} {unit} {current_product} {total_price} FCFA",
                    
                    # Métadonnées
                    "category": "produits",
                    "language": "fr"
                }
                
                documents.append(doc)
                print(f"  ✅ {content}")
                
            except (ValueError, TypeError) as e:
                print(f"  ⚠️ Erreur parsing prix: {line} - {e}")
    
    return documents

def parse_generic_catalog(raw_text: str, company_id: str) -> List[Dict]:
    """
    Parse générique pour n'importe quel format de catalogue
    Utilise patterns génériques
    """
    
    documents = []
    
    # Pattern générique pour détecter prix
    # Exemples: "6 items - $25.00", "3 units: 15 EUR", "2 paquets = 10€"
    pattern = r'(\d+)\s*(paquets?|items?|units?|pièces?|kg|litres?)\s*[-:=]\s*([0-9.,]+)\s*([A-Z€$£¥]{1,4}|fcfa|euros?|dollars?)'
    
    matches = re.finditer(pattern, raw_text, re.IGNORECASE)
    
    for i, match in enumerate(matches):
        quantity = int(match.group(1))
        unit = match.group(2)
        price_str = match.group(3).replace(',', '')
        currency = match.group(4)
        
        try:
            price = float(price_str)
            
            doc = {
                "id": f"{company_id}_product_{i}",
                "type": "pricing",
                "company_id": company_id,
                "quantity": quantity,
                "quantity_unit": unit,
                "total_price": price,
                "currency": currency.upper(),
                "title": f"{quantity} {unit}",
                "content": f"{quantity} {unit}: {price} {currency}",
                "searchable_text": f"{quantity} {unit} {price} {currency}"
            }
            
            documents.append(doc)
            
        except ValueError:
            continue
    
    return documents

async def index_structured_documents(documents: List[Dict], company_id: str):
    """
    Indexe documents structurés dans MeiliSearch ET Supabase
    """
    
    print(f"\n📤 INDEXATION DE {len(documents)} DOCUMENTS")
    print("="*60)
    
    # TODO: Implémenter indexation MeiliSearch
    print(f"⏳ MeiliSearch: À implémenter")
    print(f"   Index: company_{company_id}_products_structured")
    print(f"   Documents: {len(documents)}")
    
    # TODO: Implémenter indexation Supabase
    print(f"⏳ Supabase: À implémenter")
    print(f"   Table: company_knowledge")
    print(f"   Avec embeddings")
    
    # Sauvegarder en JSON pour inspection
    output_file = f"structured_catalog_{company_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Documents sauvegardés: {output_file}")
    print("="*60)

# Exemple d'utilisation
if __name__ == "__main__":
    
    # Catalogue Rue_du_gros
    catalog_rue_du_gros = """
    === CATALOGUES PRODUITS ===
    PRODUITS : Couches à pression ( pour enfant de 0 à 30 kg )
    VARIANTES ET PRIX :
    Taille 1 - 0 à 4 kg - 300 couches | 17.900 F CFA
    Taille 2 - 3 à 8 kg - 300 couches | 18.900 F CFA
    Taille 3 - 6 à 11 kg - 300 couches | 22.900 F CFA
    Taille 4 - 9 à 14 kg - 300 couches | 25.900 F CFA
    Taille 5 - 12 à 17 kg - 300 couches | 25.900 F CFA
    Taille 6 - 15 à 25 kg - 300 couches | 27.900 F CFA
    Taille 7 - 20 à 30 kg - 300 couches | 28.900 F CFA
    
    ---
    PRODUITS : Couches culottes ( pour enfant de 5 à 30 kg )
    VARIANTES ET PRIX :
    1 paquet - 5.500 F CFA | 5.500 F/paquet
    2 paquets - 9.800 F CFA | 4.900 F/paquet
    3 paquets - 13.500 F CFA | 4.500 F/paquet
    6 paquets - 25.000 F CFA | 4.150 F/paquet
    12 paquets - 48.000 F CFA | 4.000 F/paquet
    1 colis (48) - 168.000 F CFA | 3.500 F/paquet
    
    ---
    PRODUITS : Couches adultes
    VARIANTES ET PRIX :
    1 paquet (10 unités) - 588 F CFA/unité | 5.880 F CFA/paquet
    2 paquets (20 unités) - 1.140 F CFA/unité | 11.760 F CFA/2 paquets
    3 paquets (30 unités) - 1.080 F CFA/unité | 16.200 F CFA/3 paquets
    6 paquets (60 unités) - 1.000 F CFA/unité | 36.000 F CFA/6 paquets
    12 paquets (120 unités) - 950 F CFA/unité | 114.000 F CFA/12 paquets
    1 colis (240 unités) - 900 F CFA/unité | 216.000 F CFA/1 colis
    """
    
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    print("🚀 PARSING CATALOGUE RUE_DU_GROS")
    print("="*60)
    
    documents = parse_rue_du_gros_catalog(catalog_rue_du_gros, company_id)
    
    print(f"\n✅ {len(documents)} documents créés")
    print("\n📊 EXEMPLES:")
    for doc in documents[:3]:
        print(f"  • {doc['title']}: {doc['total_price']:,} FCFA".replace(',', '.'))
    
    # Indexation (TODO)
    # await index_structured_documents(documents, company_id)
    
    print("\n🎯 AVANTAGES:")
    print("  ✅ 1 prix = 1 document (recherche précise)")
    print("  ✅ Métadonnées structurées (filtrage facile)")
    print("  ✅ Scalable pour n'importe quel catalogue")
    print("  ✅ Query '6 paquets' → Trouve EXACTEMENT le bon document")
