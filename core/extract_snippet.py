import re
from typing import List, Optional, Dict

def extract_relevant_snippet(question: str, doc_text: str, extra_keywords: Optional[List[str]] = None) -> str:
    """
    Extraction 100% dynamique et scalable : transforme AUTOMATIQUEMENT la question en regex multi-critères.
    Aucun hardcoding d'attributs.
    """
    q = question.lower()
    
    # Stopwords à ignorer (ne servent pas à discriminer)
    stopwords = {"un", "une", "le", "la", "les", "de", "du", "des", "d", "à", "a", "pour", "dans", "sur", "est", "sont", "et", "ou", "comment", "combien", "quel", "quelle", "quels", "quelles"}
    
    # 1. Extraction AUTOMATIQUE de TOUS les mots significatifs
    words = [w for w in re.findall(r'\b\w+\b', q) if w not in stopwords and len(w) >= 2]
    
    # 2. Séparer chiffres et mots-clés de la question
    question_numbers = [w for w in words if w.isdigit()]
    question_keywords = [w for w in words if not w.isdigit()]
    
    criteria = []
    
    # 3. NE COMPTER QUE LES CHIFFRES PRÉSENTS DANS LA QUESTION
    for number in question_numbers:
        criteria.append((r"\b" + number + r"\b", 50))
    
    # 4. Ajouter les mots-clés avec poids selon longueur
    for word in question_keywords:
        if len(word) >= 6:
            # Mots longs (ex: "pression", "culottes") → poids élevé
            criteria.append((r"\b" + re.escape(word) + r"\b", 15))
        elif len(word) >= 4:
            # Mots moyens (ex: "taille") → poids moyen
            criteria.append((r"\b" + re.escape(word) + r"\b", 10))
        elif len(word) >= 2:
            # Mots courts → poids faible
            criteria.append((r"\b" + re.escape(word) + r"\b", 5))
    
    # 2. Scoring de chaque ligne du document
    lines = doc_text.splitlines()
    line_scores: Dict[int, int] = {}
    
    for i, line in enumerate(lines):
        score = 0
        for pattern, weight in criteria:
            if re.search(pattern, line, re.IGNORECASE):
                score += weight
        if score > 0:
            line_scores[i] = score
    
    # 3. Retourner le bloc avec le meilleur score (ligne + contexte)
    if line_scores:
        best_line_idx = max(line_scores, key=line_scores.get)
        # Contexte élargi : ligne + 2 avant/après
        context = '\n'.join(lines[max(0, best_line_idx-2):min(len(lines), best_line_idx+3)])
        return context.strip()
    
    # 4. Fallback : début du doc si aucun critère ne matche
    return doc_text[:500]
