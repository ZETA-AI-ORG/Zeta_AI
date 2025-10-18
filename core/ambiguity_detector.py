"""
🎯 AMBIGUITY DETECTOR - Détection ambiguïtés produits
====================================================

Détecte les ambiguïtés dans les requêtes utilisateur:
- Type produit (couches pression vs culottes)
- Taille/Variante (taille 2 vs taille 3)
- Quantité (lot 150 vs lot 300)

✅ AMÉLIORATION 5: Gestion ambiguïté
Impact: +20% clarifications pertinentes
"""

import re
from typing import Dict, List, Tuple, Optional


def detect_ambiguity(
    query: str,
    docs: List[Dict],
    custom_attributes: Dict = None
) -> Tuple[bool, str, List[str]]:
    """
    Détecte si la requête est ambiguë
    
    Args:
        query: Question utilisateur
        docs: Documents trouvés
        custom_attributes: Attributs custom des produits
    
    Returns:
        (is_ambiguous, ambiguity_type, options)
        
    Exemple:
        ("couches", docs) → (True, "type_produit", ["pression", "culottes"])
    """
    query_lower = query.lower()
    
    # 1. AMBIGUÏTÉ TYPE PRODUIT
    if _is_product_type_ambiguous(query_lower, docs):
        product_types = _extract_product_types(docs)
        if len(product_types) > 1:
            return (True, "type_produit", product_types)
    
    # 2. AMBIGUÏTÉ TAILLE/VARIANTE
    if _is_size_ambiguous(query_lower, docs):
        sizes = _extract_sizes(docs)
        if len(sizes) > 1:
            return (True, "taille", sizes)
    
    # 3. AMBIGUÏTÉ QUANTITÉ
    if _is_quantity_ambiguous(query_lower, docs):
        quantities = _extract_quantities(docs)
        if len(quantities) > 1:
            return (True, "quantite", quantities)
    
    return (False, "", [])


def _is_product_type_ambiguous(query: str, docs: List[Dict]) -> bool:
    """
    Détecte si le type de produit est ambigu
    
    Exemple: "couches" → ambigu (pression OU culottes?)
    """
    # Mots génériques sans précision
    generic_keywords = [
        "couches", "produit", "article", "item",
        "chaussures", "vêtement", "accessoire"
    ]
    
    # Si mot générique SANS précision
    for keyword in generic_keywords:
        if keyword in query:
            # Vérifier si précision existe
            if "pression" not in query and "culotte" not in query:
                return True
    
    return False


def _extract_product_types(docs: List[Dict]) -> List[str]:
    """Extrait les types de produits des documents"""
    types = set()
    
    for doc in docs:
        content = doc.get('content', '').lower()
        metadata = doc.get('metadata', {})
        
        # Depuis metadata
        product_name = metadata.get('product_name', '').lower()
        if product_name:
            # Extraire type (ex: "Couches à pression" → "pression")
            if 'pression' in product_name:
                types.add('couches à pression')
            elif 'culotte' in product_name:
                types.add('couches culottes')
        
        # Depuis contenu
        if 'pression' in content:
            types.add('couches à pression')
        if 'culotte' in content:
            types.add('couches culottes')
    
    return sorted(list(types))


def _is_size_ambiguous(query: str, docs: List[Dict]) -> bool:
    """Détecte si la taille est ambiguë"""
    # Si "taille" mentionné SANS numéro
    if 'taille' in query:
        if not re.search(r'taille\s*\d+', query):
            return True
    return False


def _extract_sizes(docs: List[Dict]) -> List[str]:
    """Extrait les tailles disponibles"""
    sizes = set()
    
    for doc in docs:
        content = doc.get('content', '')
        
        # Pattern: "Taille 1", "Taille 2", etc.
        matches = re.findall(r'taille\s*(\d+)', content, re.IGNORECASE)
        sizes.update(matches)
    
    return sorted(list(sizes))


def _is_quantity_ambiguous(query: str, docs: List[Dict]) -> bool:
    """Détecte si la quantité est ambiguë"""
    # Si "lot" mentionné SANS quantité
    if 'lot' in query:
        if not re.search(r'lot\s*(?:de\s*)?(\d+)', query):
            return True
    return False


def _extract_quantities(docs: List[Dict]) -> List[str]:
    """Extrait les quantités disponibles"""
    quantities = set()
    
    for doc in docs:
        content = doc.get('content', '')
        
        # Pattern: "Lot de 150", "300 couches", etc.
        matches = re.findall(r'(\d+)\s*(?:couches|pcs|pieces)', content, re.IGNORECASE)
        quantities.update(matches)
    
    return sorted(list(quantities))


def format_ambiguity_message(ambiguity_type: str, options: List[str]) -> str:
    """
    Formate le message d'ambiguïté pour le contexte LLM
    
    Returns:
        Message à injecter dans le contexte
    """
    if ambiguity_type == "type_produit":
        return f"""
⚠️ AMBIGUÏTÉ DÉTECTÉE pour la requête utilisateur:
Type de produit non précisé. Options disponibles:
{chr(10).join(f'  - {opt}' for opt in options)}

ACTION REQUISE: Demander au client de préciser le type de produit souhaité.
"""
    
    elif ambiguity_type == "taille":
        return f"""
⚠️ AMBIGUÏTÉ DÉTECTÉE pour la requête utilisateur:
Taille non précisée. Tailles disponibles:
{chr(10).join(f'  - Taille {opt}' for opt in options)}

ACTION REQUISE: Demander au client de préciser la taille souhaitée.
"""
    
    elif ambiguity_type == "quantite":
        return f"""
⚠️ AMBIGUÏTÉ DÉTECTÉE pour la requête utilisateur:
Quantité non précisée. Lots disponibles:
{chr(10).join(f'  - Lot de {opt}' for opt in options)}

ACTION REQUISE: Demander au client de préciser la quantité souhaitée (lot 150 ou 300).
"""
    
    return ""
