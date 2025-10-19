"""
⚡ HYDE OPTIMIZER - Skip HYDE pour questions simples
Économie ~2s sur 60% des requêtes
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Patterns de questions simples (pas besoin de HYDE)
SIMPLE_QUERY_PATTERNS = [
    # Prix
    r'prix\s+(?:du\s+)?(?:lot\s+)?(?:de\s+)?\d+',
    r'combien\s+(?:coute|cout|coûte|coût)',
    r'ça\s+(?:coute|cout|coûte|coût)',
    r'\d+\s+(?:fcfa|cfa|francs?)',
    
    # Livraison
    r'livraison\s+(?:à|a|pour|vers)?\s*\w+',
    r'livre(?:r|z)?\s+(?:à|a)\s+\w+',
    r'frais\s+(?:de\s+)?livraison',
    r'délai\s+(?:de\s+)?livraison',
    
    # Contact
    r'contact(?:er)?',
    r'telephone|tel|phone|appel(?:er)?',
    r'whatsapp',
    r'numero|numéro',
    
    # Paiement
    r'paiement',
    r'payer|payé',
    r'wave|orange\s+money|mtn\s+money|moov\s+money',
    r'espèces|espece|cash',
    
    # Horaires
    r'horaire|heure',
    r'ouvert|fermé|ferme',
    r'quand\s+(?:ouvr|ferm)',
    
    # Localisation
    r'adresse',
    r'localisation',
    r'où\s+(?:êtes|etes)',
    r'situé|située',
    
    # Produits simples
    r'(?:couches?|culottes?)\s+(?:taille|t)\s*\d+',
    r'lot\s+(?:de\s+)?\d+',
    r'disponible',
    r'en\s+stock'
]

# Patterns de questions complexes (besoin de HYDE)
COMPLEX_QUERY_PATTERNS = [
    r'(?:comment|pourquoi|quelle?\s+(?:est|sont))',
    r'différence\s+entre',
    r'meilleur|mieux|préférable',
    r'conseil|recommand',
    r'expliqu|détail',
    r'compar(?:er|aison)',
    r'avantage|inconvénient'
]


def is_simple_query(query: str) -> bool:
    """
    Détecte si une question est simple (pas besoin de HYDE)
    
    Args:
        query: Question utilisateur
        
    Returns:
        True si simple, False si complexe
    """
    query_lower = query.lower()
    
    # Vérifier patterns complexes d'abord
    for pattern in COMPLEX_QUERY_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"🔍 [HYDE] Question COMPLEXE détectée: {pattern}")
            return False
    
    # Vérifier patterns simples
    for pattern in SIMPLE_QUERY_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"⚡ [HYDE] Question SIMPLE détectée: {pattern}")
            return True
    
    # Par défaut, considérer comme complexe (sécurité)
    logger.info(f"❓ [HYDE] Question INCONNUE, utiliser HYDE par sécurité")
    return False


def should_skip_hyde(query: str, force_hyde: bool = False) -> bool:
    """
    Détermine si HYDE doit être skippé
    
    Args:
        query: Question utilisateur
        force_hyde: Forcer HYDE même pour questions simples
        
    Returns:
        True si skip HYDE, False sinon
    """
    if force_hyde:
        logger.info("🔧 [HYDE] Forcé par paramètre")
        return False
    
    if is_simple_query(query):
        logger.info("⚡ [HYDE] SKIP - Question simple détectée")
        return True
    
    logger.info("🔍 [HYDE] ACTIF - Question complexe")
    return False


def get_hyde_stats() -> dict:
    """
    Retourne les statistiques d'utilisation de HYDE
    (À implémenter avec un compteur global)
    """
    return {
        "total_queries": 0,
        "hyde_skipped": 0,
        "hyde_used": 0,
        "skip_rate": 0.0
    }


# ========== EXEMPLES ==========

if __name__ == "__main__":
    # Tests
    test_queries = [
        # Simples (skip HYDE)
        "Prix du lot de 300 couches",
        "Combien coûte la livraison à Angré",
        "Votre numéro WhatsApp",
        "Vous acceptez Wave?",
        "Horaires d'ouverture",
        "Où êtes-vous situés",
        "Couches taille 3 disponibles",
        
        # Complexes (utiliser HYDE)
        "Quelle est la différence entre couches et couches culottes",
        "Pourquoi les prix varient selon les tailles",
        "Comment choisir la bonne taille",
        "Quel est le meilleur produit pour un bébé de 6 mois",
        "Expliquez-moi les modes de paiement",
        "Comparer les délais de livraison"
    ]
    
    print("=" * 60)
    print("TEST HYDE OPTIMIZER")
    print("=" * 60)
    
    simple_count = 0
    complex_count = 0
    
    for query in test_queries:
        skip = should_skip_hyde(query)
        status = "⚡ SKIP" if skip else "🔍 USE"
        print(f"{status} | {query}")
        
        if skip:
            simple_count += 1
        else:
            complex_count += 1
    
    print("=" * 60)
    print(f"Résultats: {simple_count} simples, {complex_count} complexes")
    print(f"Taux de skip: {simple_count/len(test_queries)*100:.1f}%")
    print(f"Économie estimée: {simple_count * 2:.1f}s (2s par skip)")
