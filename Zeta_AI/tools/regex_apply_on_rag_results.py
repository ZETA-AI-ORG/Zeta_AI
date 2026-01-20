#!/usr/bin/env python3
"""
Script pour appliquer des regex prédéfinis sur les documents pertinents récupérés par le RAG.
- Charge une liste de patterns (fichier JSON ou dict python)
- Applique chaque regex sur chaque document du résultat RAG
- Enrichit le contexte transmis au LLM avec les extraits trouvés (pour test ou debug)
"""

import re
import json
import sys
from typing import List, Dict

# Exemple de patterns (à remplacer par un chargement JSON si besoin)
PATTERNS = {
    "montant_fcfa": r"(\d{1,3}(?:[ .]\d{3})*|\d+)\s*f\.?\s*cfa",
    "acompte": r"acompte.*?(\d{1,3}(?:[ .]\d{3})*|\d+).*?fcfa",
    "pourcentage": r"(\d{1,3})%",
    "date_fr": r"\d{1,2}/\d{1,2}/\d{2,4}",
    "phone": r"\+225\d{8,10}|0\d{9}",
    "email": r"[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}",
    "whatsapp": r"whatsapp.*?(\+225\d{8,10}|0\d{9})"
}

def apply_regex_patterns_on_docs(docs: List[Dict], patterns: Dict[str, str] = PATTERNS) -> Dict[str, List[str]]:
    """Applique chaque regex sur chaque document et retourne les extraits trouvés"""
    results = {label: [] for label in patterns}
    for doc in docs:
        content = doc.get('content', '')
        for label, pattern in patterns.items():
            found = re.findall(pattern, content, re.IGNORECASE)
            if found:
                # Pour debug, on peut stocker un extrait du texte autour du match
                for match in found:
                    snippet = extract_snippet(content, match)
                    results[label].append(snippet)
    return results

def extract_snippet(text, match, window=40):
    """Retourne un extrait de texte autour du match pour contexte"""
    idx = text.lower().find(str(match).lower())
    if idx == -1:
        return str(match)
    start = max(0, idx - window)
    end = min(len(text), idx + len(str(match)) + window)
    return text[start:end]

if __name__ == "__main__":
    # Simulation : charger des docs depuis un fichier json ou autre
    if len(sys.argv) < 2:
        print("Usage: python regex_apply_on_rag_results.py <docs.json>")
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        docs = json.load(f)
    results = apply_regex_patterns_on_docs(docs)
    print(json.dumps(results, indent=2, ensure_ascii=False))
