"""
🎯 OPTIMISEUR DE CONTEXTE RAG
Réduit les coûts en tokens tout en gardant la qualité
"""

import re
from typing import List, Dict, Tuple

def optimize_context_for_tokens(supabase_context: str, meili_context: str, target_chars: int = 2500) -> str:
    """
    🔧 OPTIMISE LE CONTEXTE POUR RÉDUIRE LES COÛTS EN TOKENS
    
    Args:
        supabase_context: Contexte sémantique Supabase
        meili_context: Contexte textuel MeiliSearch  
        target_chars: Objectif de caractères (défaut: 2500)
    
    Returns:
        Contexte optimisé et dédupliqué
    """
    
    # 1. DÉDUPLICATION INTELLIGENTE
    optimized_context = deduplicate_content(supabase_context, meili_context)
    
    # 2. COMPRESSION DU FORMATAGE
    optimized_context = compress_formatting(optimized_context)
    
    # 3. PRIORISATION DU CONTENU
    if len(optimized_context) > target_chars:
        optimized_context = prioritize_content(optimized_context, target_chars)
    
    return optimized_context

def deduplicate_content(supabase_context: str, meili_context: str) -> str:
    """
    🔄 SUPPRIME LES DOUBLONS ENTRE SUPABASE ET MEILISEARCH
    """
    
    # Extraire les sections uniques de chaque source
    supabase_sections = extract_product_sections(supabase_context)
    meili_sections = extract_meili_sections(meili_context)
    
    # Identifier les doublons
    unique_content = {}
    
    # Prioriser MeiliSearch (plus structuré avec headers)
    for section_id, content in meili_sections.items():
        unique_content[section_id] = content
    
    # Ajouter Supabase seulement si nouveau contenu
    for section_id, content in supabase_sections.items():
        if section_id not in unique_content:
            unique_content[section_id] = content
    
    # Reconstruire le contexte optimisé
    optimized_parts = []
    
    # Grouper par catégorie
    products = []
    delivery = []
    support = []
    
    for section_id, content in unique_content.items():
        if 'produit' in section_id.lower() or 'couches' in content.lower():
            products.append(content)
        elif 'livraison' in content.lower() or 'delivery' in section_id.lower():
            delivery.append(content)
        elif 'support' in content.lower() or 'contact' in content.lower():
            support.append(content)
    
    # Construire le contexte final optimisé
    if products:
        optimized_parts.append("=== PRODUITS ===")
        optimized_parts.extend(products)
    
    if delivery:
        optimized_parts.append("=== LIVRAISON ===")
        optimized_parts.extend(delivery)
    
    if support:
        optimized_parts.append("=== SUPPORT ===")
        optimized_parts.extend(support)
    
    return "\n\n".join(optimized_parts)

def extract_product_sections(context: str) -> Dict[str, str]:
    """
    📦 EXTRAIT LES SECTIONS PRODUITS DU CONTEXTE
    """
    sections = {}
    
    # Regex pour identifier les produits
    product_pattern = r"PRODUITS\s*:\s*([^n]+(?:\n[^=]+)*)"
    matches = re.findall(product_pattern, context, re.MULTILINE | re.IGNORECASE)
    
    for i, match in enumerate(matches):
        product_type = "couches_adultes" if "adultes" in match.lower() else f"produit_{i+1}"
        sections[product_type] = f"PRODUITS : {match.strip()}"
    
    return sections

def extract_meili_sections(context: str) -> Dict[str, str]:
    """
    🔍 EXTRAIT LES SECTIONS MEILISEARCH AVEC HEADERS
    """
    sections = {}
    
    # Regex pour les sections MeiliSearch
    meili_pattern = r"POUR \(([^)]+)\)[^:]*:([^=]+)(?===|$)"
    matches = re.findall(meili_pattern, context, re.MULTILINE | re.DOTALL)
    
    for category, content in matches:
        clean_content = content.strip()
        if clean_content:
            sections[f"meili_{category}"] = clean_content
    
    return sections

def compress_formatting(context: str) -> str:
    """
    📝 COMPRESSE LE FORMATAGE REDONDANT
    """
    
    # Supprimer les headers redondants
    context = re.sub(r"=== INFORMATIONS [^=]+ ===\n", "", context)
    
    # Supprimer les index IDs longs
    context = re.sub(r"Index: [a-zA-Z_]+_[a-zA-Z0-9]{28,} - ", "", context)
    
    # Compresser les séparateurs
    context = re.sub(r"\n---\n\n", "\n\n", context)
    context = re.sub(r"\n{3,}", "\n\n", context)
    
    # Supprimer les métadonnées inutiles
    context = re.sub(r"Document \d+/\d+ :", "", context)
    
    return context.strip()

def prioritize_content(context: str, target_chars: int) -> str:
    """
    🎯 PRIORISE LE CONTENU LE PLUS IMPORTANT
    """
    
    sections = context.split("=== ")
    prioritized_sections = []
    current_length = 0
    
    # Ordre de priorité
    priority_order = ["PRODUITS", "LIVRAISON", "SUPPORT"]
    
    for priority in priority_order:
        for section in sections:
            if section.startswith(priority) and current_length + len(section) < target_chars:
                prioritized_sections.append("=== " + section if not section.startswith("===") else section)
                current_length += len(section)
                break
    
    return "\n\n".join(prioritized_sections)

def get_context_stats(context: str) -> Dict[str, int]:
    """
    📊 STATISTIQUES DU CONTEXTE
    """
    return {
        "characters": len(context),
        "tokens_estimate": len(context) // 4,
        "lines": len(context.split("\n")),
        "sections": len(re.findall(r"===.*===", context))
    }

# EXEMPLE D'UTILISATION
if __name__ == "__main__":
    # Test avec données exemple
    sample_supabase = """PRODUITS : Couches à pression ( pour enfant de 0 à 30 kg )
VARIANTES ET PRIX :
Taille 1 - 0 à 4 kg - 300 couches | 17.900 F CFA"""
    
    sample_meili = """POUR (produits) - Index: products_long_id - Document 1/2 :
PRODUITS : Couches à pression ( pour enfant de 0 à 30 kg )
VARIANTES ET PRIX :
Taille 1 - 0 à 4 kg - 300 couches | 17.900 F CFA"""
    
    optimized = optimize_context_for_tokens(sample_supabase, sample_meili, 2500)
    stats = get_context_stats(optimized)
    
    print(f"📊 Contexte optimisé:")
    print(f"   Caractères: {stats['characters']}")
    print(f"   Tokens estimés: {stats['tokens_estimate']}")
    print(f"   Réduction: {((3423 - stats['characters']) / 3423) * 100:.1f}%")




