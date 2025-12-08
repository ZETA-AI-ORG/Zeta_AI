import re
from typing import List

from core.smart_stopwords import STOP_WORDS_ECOMMERCE, KEEP_WORDS_ECOMMERCE
from core.custom_stopwords import CUSTOM_STOP_WORDS

# Version Botlive du système de stopwords / keywords.
# Objectif:
# - Réutiliser la base RAG (STOP_WORDS_ECOMMERCE + CUSTOM_STOP_WORDS)
# - MAIS protéger certains mots/expressions importants pour la détection d'intent
#   ("je veux", "où", "quand", "comment", "combien", etc.).
# - Ne JAMAIS modifier le comportement RAG existant.

# Mots/expressions à toujours garder visibles côté Botlive
# Même s'ils apparaissent dans les listes de stopwords RAG.
BOTLIVE_PROTECTED_SINGLE = {
    # Interrogatifs très liés aux intents (suivi, info, etc.)
    "ou", "où", "quand", "comment", "combien", "pourquoi",
    # Marques d'intention explicites
    "veux", "voudrais", "aimerais", "souhaite", "souhaiterais",
    # Termes fréquents mais utiles pour comprendre le type de demande
    "changer", "modifier", "annuler", "suivi", "commande", "livraison",
}

# Expressions multi-mots typiques à garder telles quelles dans l'analyse
BOTLIVE_PROTECTED_MULTI = [
    "je veux", "je voudrais", "je souhaite",
    "je veux changer", "je veux annuler", "je veux modifier",
    "ou est", "où est", "quand arrive",
]

# Base de stopwords côté Botlive:
# - On part de la liste e-commerce + custom
# - On retire les mots critiques RAG (KEEP_WORDS_ECOMMERCE)
# - On retire aussi les tokens que l'on veut absolument garder côté intent
_BASE_STOPWORDS = set(STOP_WORDS_ECOMMERCE) | CUSTOM_STOP_WORDS
BOTLIVE_STOPWORDS = (_BASE_STOPWORDS - set(KEEP_WORDS_ECOMMERCE) - BOTLIVE_PROTECTED_SINGLE)


def _normalize(text: str) -> str:
    """Normalisation légère pour l'extraction de keywords Botlive.

    - lowercase
    - suppression ponctuation lourde
    - normalisation des espaces
    """
    t = (text or "").lower().strip()
    # Garder lettres/chiffres + accents basiques, remplacer le reste par des espaces
    t = re.sub(r"[^0-9a-zA-ZàâäéèêëïîôöùûüÿçœæÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÇŒÆ]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def extract_botlive_keywords(text: str) -> List[str]:
    """Extrait une liste de mots-clés pour Botlive.

    Important:
    - NE modifie PAS le texte utilisé pour l'embedding (c'est juste un outil annexe).
    - Réutilise la base de stopwords RAG, mais avec une whitelist adaptée Botlive.
    - Conserve explicitement certains mots/expressions utiles pour l'intent.
    """
    norm = _normalize(text)
    if not norm:
        return []

    words = norm.split()
    keywords: List[str] = []

    # Détection simple des expressions multi-mots protégées
    joined = f" {norm} "
    protected_multi_hits = []
    for expr in BOTLIVE_PROTECTED_MULTI:
        expr_norm = _normalize(expr)
        if not expr_norm:
            continue
        if f" {expr_norm} " in joined and expr_norm not in protected_multi_hits:
            protected_multi_hits.append(expr_norm)

    for w in words:
        if not w:
            continue
        # Toujours garder les tokens explicitement protégés
        if w in BOTLIVE_PROTECTED_SINGLE:
            keywords.append(w)
            continue
        # Filtrer les vrais mots vides
        if w in BOTLIVE_STOPWORDS:
            continue
        keywords.append(w)

    # Ajouter les expressions multi-mots détectées en fin de liste
    for expr in protected_multi_hits:
        if expr not in keywords:
            keywords.append(expr)

    # Déduplication en préservant l'ordre
    seen = set()
    deduped: List[str] = []
    for w in keywords:
        if w in seen:
            continue
        seen.add(w)
        deduped.append(w)

    return deduped
