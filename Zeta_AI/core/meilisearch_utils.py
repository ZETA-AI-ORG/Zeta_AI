from typing import List, Dict

def get_index_attributes(meili_client, index_name: str) -> Dict[str, List[str]]:
    """
    Récupère dynamiquement la structure d'un index Meilisearch :
    - searchableAttributes
    - filterableAttributes
    - displayedAttributes
    - sortableAttributes
    Retourne un dict {type: [attributs]}
    """
    index = meili_client.index(index_name)
    structure = {}
    # Les méthodes sont synchrones dans le client python officiel
    structure['searchableAttributes'] = index.get_searchable_attributes()
    structure['filterableAttributes'] = index.get_filterable_attributes()
    structure['displayedAttributes'] = index.get_displayed_attributes()
    structure['sortableAttributes'] = index.get_sortable_attributes()
    
    # --- Optimisation : Générer dynamiquement la liste des attributs pertinents pour la recherche ---
    try:
        from core.concept_extractor import UNIVERSAL_STRUCTURE
        fixed_attrs = set(UNIVERSAL_STRUCTURE.get('fixed_attributes', []))
    except Exception:
        fixed_attrs = set()
    # Intersection entre les fixed_attributes et les attributs de l'index
    relevant_search_attrs = list(fixed_attrs.intersection(structure['searchableAttributes']))
    relevant_filter_attrs = list(fixed_attrs.intersection(structure['filterableAttributes']))
    structure['relevant_searchable'] = relevant_search_attrs
    structure['relevant_filterable'] = relevant_filter_attrs
    return structure

def ensure_meili_index_settings(meili_client, index_name: str, filterable: list = None, sortable: list = None, searchable: list = None, displayed: list = None):
    """
    Vérifie et applique dynamiquement les settings Meilisearch pour l'index donné.
    - Ajoute les attributs manquants en filterable/sortable/searchable/displayed
    - Log les changements
    """
    index = meili_client.index(index_name)
    try:
        current_settings = {
            'filterableAttributes': set(index.get_filterable_attributes()),
            'sortableAttributes': set(index.get_sortable_attributes()),
            'searchableAttributes': set(index.get_searchable_attributes()),
            'displayedAttributes': set(index.get_displayed_attributes()),
        }
        updated = False
        if filterable:
            to_add = set(filterable) - current_settings['filterableAttributes']
            if to_add:
                index.update_filterable_attributes(list(current_settings['filterableAttributes'] | set(filterable)))
                updated = True
        if sortable:
            to_add = set(sortable) - current_settings['sortableAttributes']
            if to_add:
                index.update_sortable_attributes(list(current_settings['sortableAttributes'] | set(sortable)))
                updated = True
        if searchable:
            to_add = set(searchable) - current_settings['searchableAttributes']
            if to_add:
                index.update_searchable_attributes(list(current_settings['searchableAttributes'] | set(searchable)))
                updated = True
        if displayed:
            to_add = set(displayed) - current_settings['displayedAttributes']
            if to_add:
                index.update_displayed_attributes(list(current_settings['displayedAttributes'] | set(displayed)))
                updated = True
        if updated:
            print(f"[MEILI] Settings mis à jour pour l'index {index_name}")
        else:
            print(f"[MEILI] Settings déjà à jour pour l'index {index_name}")
    except Exception as e:
        print(f"[MEILI][ERROR] Impossible de vérifier/patcher les settings de l'index {index_name}: {e}")
