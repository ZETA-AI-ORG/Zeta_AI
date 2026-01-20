#!/usr/bin/env python3
"""
🎯 SPLITTER INTELLIGENT DE CATALOGUES
Parse un gros document et crée 1 document par prix/variante

PRINCIPE:
- Détecte automatiquement le type de contenu
- Split les catalogues en documents séparés
- 1 prix = 1 document = recherche précise
"""

import re
from typing import List, Dict, Any, Optional

def detect_catalog_type(content: str) -> str:
    """
    ✅ DÉTECTION GÉNÉRIQUE de type de catalogue (scalable pour tout secteur)
    
    Returns:
        "structured_catalog" : Format structuré avec sections produits
        "pricing_list" : Liste de prix simple
        "unknown" : Autre type, pas de split
    """
    # ✅ Pattern 1: Catalogue structuré (fonctionne pour TOUT secteur)
    # Cherche des marqueurs de sections : "PRODUIT", "ARTICLE", "SERVICE", "OFFRE", etc.
    structured_markers = [
        r'PRODUITS?\s*:',      # Ex: "PRODUITS : Couches"
        r'ARTICLES?\s*:',      # Ex: "ARTICLE : Chaussures Nike"
        r'SERVICES?\s*:',      # Ex: "SERVICE : Consulting"
        r'OFFRES?\s*:',        # Ex: "OFFRE : Abonnement Pro"
        r'VARIANTES?\s*ET\s*PRIX',  # Ex: "VARIANTES ET PRIX :"
    ]
    
    for marker in structured_markers:
        if re.search(marker, content, re.IGNORECASE):
            return "structured_catalog"
    
    # ✅ Pattern 2: Liste de prix simple (fonctionne pour N'IMPORTE quelle unité)
    # Cherche: [nombre] [unité quelconque] [séparateur] [prix]
    # Ex: "6 paquets - 25000", "10 kg - 5000", "1 heure - 15000", "5 litres - 8000"
    if re.search(r'\d+\s*[a-zA-Zéèêàâôûç]+\s*[-:=]\s*\d+', content, re.IGNORECASE):
        return "pricing_list"
    
    return "unknown"

def split_structured_catalog(content: str, company_id: str, base_doc_id: str) -> List[Dict]:
    """
    Split pour format structuré (Rue_du_gros style)
    
    Input:
        PRODUITS : Couches culottes
        VARIANTES ET PRIX :
        1 paquet - 5.500 F CFA | 5.500 F/paquet
        6 paquets - 25.000 F CFA | 4.150 F/paquet
    
    Output:
        [
          {"id": "..._item_1", "content": "1 paquet de Couches culottes : 5.500 F CFA", ...},
          {"id": "..._item_2", "content": "6 paquets de Couches culottes : 25.000 F CFA", ...}
        ]
    """
    
    documents = []
    current_product = None
    lines = content.split('\n')
    doc_counter = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # ✅ Détecter nom du produit/article/service (générique)
        # Formats supportés: "PRODUIT:", "ARTICLE:", "SERVICE:", "OFFRE:", etc.
        product_markers = [
            r'PRODUITS?\s*:\s*([^(]+)',
            r'ARTICLES?\s*:\s*([^(]+)',
            r'SERVICES?\s*:\s*([^(]+)',
            r'OFFRES?\s*:\s*([^(]+)',
            r'ITEM\s*:\s*([^(]+)',
        ]
        
        for marker_pattern in product_markers:
            match = re.search(marker_pattern, line, re.IGNORECASE)
            if match:
                current_product = match.group(1).strip()
                print(f"   📦 Produit: {current_product}")
                break  # Sortir de la boucle après avoir trouvé
        
        if any(re.search(p, line, re.IGNORECASE) for p in product_markers):
            continue
        
        # Détecter ligne de prix
        # Formats supportés:
        # - "6 paquets - 25.000 F CFA | 4.150 F/paquet"
        # - "1 paquet (10 unités) - 5.880 F CFA/paquet"
        # - "Taille 3 - 6 à 11 kg - 300 couches | 22.900 F CFA"
        
        # ✅ PATTERN GÉNÉRIQUE 1: Quantité + Unité + Prix
        # Exemples: "6 paquets - 25.000 F CFA", "1 kg - 5.000 F CFA", "10 litres - 15.000 F CFA"
        price_match = re.search(
            r'(\d+)\s*([a-zA-Zéèêàâôûç]+)\s*(?:\((\d+)(?:\s*[a-zA-Zéèêàâôûç]+)?\))?\s*[-:=]\s*([0-9.,\s]+)\s*F?\s*CFA',
            line,
            re.IGNORECASE
        )
        
        # ✅ PATTERN GÉNÉRIQUE 2: Taille/Variante + Prix (flexible)
        # Exemples: "Taille 3 - 22.900 F CFA", "Taille 3: 22.900 F CFA", "Version Pro = 50.000 F CFA"
        if not price_match:
            # Pattern plus flexible : accepte n'importe quoi entre la variante et le prix
            price_match = re.search(
                r'([A-Za-zéèêàâôûç]+)\s+(\d+|[A-Z]+)[:\-=\s]*.*?([0-9.,\s]+)\s*F?\s*CFA',
                line,
                re.IGNORECASE
            )
            if price_match:
                # ✅ Format générique pour variantes (Taille, Version, Modèle, etc.)
                variant_type = price_match.group(1)  # Ex: "Taille", "Version", "Modèle"
                variant_value = price_match.group(2)  # Ex: "3", "XL", "Pro"
                price_str = price_match.group(3).replace('.', '').replace(',', '').replace(' ', '')
                
                try:
                    price = int(price_str)
                    doc_counter += 1
                    
                    doc = {
                        "id": f"{base_doc_id}_item_{doc_counter}",
                        "company_id": company_id,
                        "type": "pricing",
                        "product": current_product or "Produit",
                        "variant": f"{variant_type} {variant_value}",
                        "price": price,
                        "content": line.strip(),
                        "searchable": f"{variant_type} {variant_value} {current_product or ''} {price} FCFA"
                    }
                    
                    documents.append(doc)
                    print(f"      ✅ {variant_type} {variant_value}: {price:,} F CFA".replace(',', '.'))
                    
                except ValueError:
                    pass
                
                continue
        
        if price_match and current_product:
            quantity = price_match.group(1)
            unit = price_match.group(2)
            units_in_pack = price_match.group(3) if len(price_match.groups()) >= 3 else None
            price_str = price_match.group(4) if len(price_match.groups()) >= 4 else price_match.group(2)
            price_str = price_str.replace('.', '').replace(',', '').replace(' ', '')
            
            try:
                price = int(price_str)
                doc_counter += 1
                
                # Construire contenu optimisé
                content_parts = [
                    f"{quantity} {unit} de {current_product}"
                ]
                
                if units_in_pack:
                    content_parts[0] += f" ({units_in_pack} unités)"
                
                content_parts.append(f"{price:,} F CFA".replace(',', '.'))
                
                content_text = " : ".join(content_parts)
                
                # Document structuré
                doc = {
                    "id": f"{base_doc_id}_item_{doc_counter}",
                    "company_id": company_id,
                    "type": "pricing",
                    "product": current_product,
                    "quantity": int(quantity),
                    "unit": unit.rstrip('s'),  # "paquets" → "paquet"
                    "price": price,
                    "content": content_text,
                    "searchable": f"{quantity} {unit} {current_product} {price} FCFA"
                }
                
                if units_in_pack:
                    doc["units_per_pack"] = int(units_in_pack)
                
                documents.append(doc)
                print(f"      ✅ {quantity} {unit}: {price:,} F CFA".replace(',', '.'))
                
            except (ValueError, IndexError):
                continue
    
    return documents

def split_pricing_list(content: str, company_id: str, base_doc_id: str) -> List[Dict]:
    """
    Split pour liste de prix simple
    
    Input:
        3 items - 15 EUR
        6 items - 25 EUR
    
    Output:
        Documents séparés pour chaque prix
    """
    
    documents = []
    doc_counter = 0
    
    # ✅ Pattern 100% générique pour TOUTE unité et TOUTE devise
    # Exemple: "6 kg - 5000 FCFA", "10 heures - 15000 EUR", "1 bouteille - 2500 CFA"
    pattern = r'(\d+)\s*([a-zA-Zéèêàâôûç]+)\s*[-:=]\s*([0-9.,\s]+)\s*([A-ZÉÈÊÀÂÔÛÇa-zéèêàâôûç€$£¥]{1,6})'
    
    matches = re.finditer(pattern, content, re.IGNORECASE)
    
    for match in matches:
        quantity = match.group(1)
        unit = match.group(2)
        price_str = match.group(3).replace(',', '')
        currency = match.group(4)
        
        try:
            price = float(price_str)
            doc_counter += 1
            
            doc = {
                "id": f"{base_doc_id}_item_{doc_counter}",
                "company_id": company_id,
                "type": "pricing",
                "quantity": int(quantity),
                "unit": unit,
                "price": price,
                "currency": currency.upper(),
                "content": f"{quantity} {unit} : {price} {currency}",
                "searchable": f"{quantity} {unit} {price} {currency}"
            }
            
            documents.append(doc)
            
        except ValueError:
            continue
    
    return documents

def smart_split_document(doc: Dict[str, Any], company_id: str) -> List[Dict[str, Any]]:
    """
    Point d'entrée principal : analyse un document et le split si nécessaire
    
    Args:
        doc: Document original {"id": "...", "content": "...", "metadata": {...}}
        company_id: ID de l'entreprise
        
    Returns:
        Liste de documents (peut être 1 si pas de split nécessaire)
    """
    
    content = doc.get("content", "")
    doc_id = doc.get("id", "unknown")
    metadata = doc.get("metadata", {})
    
    # Détecter type
    catalog_type = detect_catalog_type(content)
    
    # Si c'est un catalogue structuré, on split
    if catalog_type == "structured_catalog":
        print(f"🔪 Split catalogue structuré: {doc_id}")
        
        split_docs = split_structured_catalog(content, company_id, doc_id)
        
        if split_docs:
            # ✨ CORRECTION: Wrapper chaque doc splité dans le format attendu
            wrapped_docs = []
            for split_doc in split_docs:
                wrapped = {
                    "content": split_doc.get("content", ""),
                    "metadata": {
                        **metadata,  # Préserver metadata original
                        "type": "pricing",  # Type pour routage
                        "document_id": split_doc.get("id", ""),
                        "product": split_doc.get("product", ""),
                        "price": split_doc.get("price", 0),
                        "variant": split_doc.get("variant", ""),
                        "split_from": doc_id
                    }
                }
                # Ajouter searching_text/searchable si présent
                if "searchable" in split_doc:
                    wrapped["searching_text"] = split_doc["searchable"]
                
                wrapped_docs.append(wrapped)
            
            print(f"   ✅ {len(wrapped_docs)} documents créés")
            return wrapped_docs
        else:
            print(f"   ⚠️ Aucun split effectué, document conservé")
            return [doc]
    
    elif catalog_type == "pricing_list":
        print(f"🔪 Split liste de prix: {doc_id}")
        
        split_docs = split_pricing_list(content, company_id, doc_id)
        
        if split_docs:
            # ✨ CORRECTION: Wrapper chaque doc splité
            wrapped_docs = []
            for split_doc in split_docs:
                wrapped = {
                    "content": split_doc.get("content", ""),
                    "metadata": {
                        **metadata,
                        "type": "pricing",
                        "document_id": split_doc.get("id", ""),
                        "split_from": doc_id
                    }
                }
                if "searchable" in split_doc:
                    wrapped["searching_text"] = split_doc["searchable"]
                
                wrapped_docs.append(wrapped)
            
            print(f"   ✅ {len(wrapped_docs)} documents créés")
            return wrapped_docs
        else:
            print(f"   ⚠️ Aucun split effectué, document conservé")
            return [doc]
    
    # Si pas de split nécessaire, retourner tel quel
    else:
        return [doc]

def process_documents_with_smart_split(documents: List[Dict[str, Any]], company_id: str) -> List[Dict[str, Any]]:
    """
    Traite une liste de documents et applique le smart split
    
    Args:
        documents: Liste des documents bruts
        company_id: ID de l'entreprise
        
    Returns:
        Liste des documents finaux (certains splittés, d'autres non)
    """
    
    print(f"\n🎯 SMART SPLIT pour {len(documents)} documents")
    print("="*60)
    
    final_documents = []
    
    for doc in documents:
        split_results = smart_split_document(doc, company_id)
        final_documents.extend(split_results)
    
    print("="*60)
    print(f"📊 RÉSUMÉ:")
    print(f"   Documents entrants: {len(documents)}")
    print(f"   Documents finaux: {len(final_documents)}")
    
    if len(documents) > 0:
        ratio = len(final_documents) / len(documents)
        print(f"   Ratio: {ratio:.1f}x")
        
        if ratio > 1:
            print(f"   ✅ {len(final_documents) - len(documents)} documents supplémentaires créés")
    
    print("="*60)
    
    return final_documents


# Test unitaire
if __name__ == "__main__":
    print("🧪 TEST DU SPLITTER\n")
    
    # Test 1: Catalogue Rue_du_gros
    doc_test = {
        "id": "catalogue_couches_culottes",
        "content": """
PRODUITS : Couches culottes ( pour enfant de 5 à 30 kg )
VARIANTES ET PRIX :
1 paquet - 5.500 F CFA | 5.500 F/paquet
2 paquets - 9.800 F CFA | 4.900 F/paquet
3 paquets - 13.500 F CFA | 4.500 F/paquet
6 paquets - 25.000 F CFA | 4.150 F/paquet
12 paquets - 48.000 F CFA | 4.000 F/paquet
        """,
        "metadata": {"type": "pricing"}
    }
    
    result = smart_split_document(doc_test, "test_company")
    
    print(f"\n✅ Résultat: {len(result)} documents")
    for doc in result[:3]:  # Afficher les 3 premiers
        print(f"   • {doc['content']}")
    
    if len(result) > 3:
        print(f"   ... et {len(result) - 3} autres")
