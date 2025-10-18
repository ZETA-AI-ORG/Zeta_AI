import re
from typing import Dict, List, Any

def extract_product_attributes(text: str, attribute_list: List[str]) -> Dict[str, Any]:
    """
    Extrait dynamiquement les attributs produits présents dans un texte utilisateur,
    à partir d'une liste d'attributs (ex : fixed_attributes Meilisearch ou base).
    Retourne un dict {attribut: valeur trouvée}
    """
    attributes = {}
    for attr in attribute_list:
        # Génère un pattern flexible pour chaque attribut (clé suivie de : ou = ou - ou espace)
        # Ex: nom_produit: xyz, nom produit = xyz, nom produit - xyz
        pattern = rf"{attr}\s*[:=\-]?\s*([^\n\r\|\,]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            attributes[attr] = match.group(1).strip()
    return attributes

# Optionnel : helper pour récupérer dynamiquement les attributs depuis Meilisearch
try:
    from core.meilisearch_utils import get_index_attributes
except ImportError:
    get_index_attributes = None

def get_dynamic_product_attributes(meili_client, index_name: str) -> List[str]:
    """
    Récupère dynamiquement la liste des attributs produits pertinents (hors champs techniques)
    """
    if get_index_attributes:
        structure = get_index_attributes(meili_client, index_name)
        # Fusionne tous les types d'attributs, retire les doublons, filtre les champs techniques
        all_attrs = set()
        for k in ('searchableAttributes', 'filterableAttributes', 'displayedAttributes', 'sortableAttributes'):
            all_attrs.update(structure.get(k, []))
        # Exclure les champs purement techniques/id
        filtered = [a for a in all_attrs if a not in {'id','company_id','document_type','content'}]
        return filtered
    else:
        # Fallback : liste statique minimale
        return [
            "nom_produit", "catégorie", "sous_catégorie", "description", "images", "conditions_vente", "disponibilité", "variantes", "tarifs"
        ]
