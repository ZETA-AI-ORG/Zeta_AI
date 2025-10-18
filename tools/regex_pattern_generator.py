#!/usr/bin/env python3
"""
Script d'analyse automatique de la base documentaire MeiliSearch pour suggérer des regex patterns métier pertinents.
- Scanne tous les documents d'un index (ou plusieurs)
- Détecte les structures récurrentes (montants, dates, emails, numéros, IBAN, phrases métier)
- Génère une liste de regex patterns adaptés à la data réelle
"""

import re
import sys
import os
from collections import Counter

# Correction PYTHONPATH pour import local
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.vector_store import get_all_documents_for_company

# Patterns de base à tester
BASE_PATTERNS = {
    "montant_fcfa": r"(\d{1,3}(?:[ .]\d{3})*|\d+)\s*f\.?\s*cfa",
    "acompte": r"acompte.*?(\d{1,3}(?:[ .]\d{3})*|\d+).*?fcfa",
    "pourcentage": r"(\d{1,3})%",
    "date_fr": r"\d{1,2}/\d{1,2}/\d{2,4}",
    "phone": r"\+225\d{8,10}|0\d{9}",
    "email": r"[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}",
    "iban": r"[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}",
    "whatsapp": r"whatsapp.*?(\+225\d{8,10}|0\d{9})",
    "condition": r"condition.*?commande.*?acompte.*?(\d+).*?fcfa"
}


def suggest_patterns(company_id, index_name=None, max_docs=500):
    """Scanne la base Meili et suggère les patterns les plus fréquents"""
    # Récupère tous les documents (ou les N premiers)
    docs = get_all_documents_for_company(company_id, index_name=index_name, limit=max_docs)
    text_corpus = "\n".join([doc.get('content', '') for doc in docs])
    suggestions = {}
    print(f"[INFO] Analyse de {len(docs)} documents pour '{company_id}' (index: {index_name})...")
    
    for label, pattern in BASE_PATTERNS.items():
        matches = re.findall(pattern, text_corpus, re.IGNORECASE)
        if matches:
            count = len(matches)
            unique = set(matches)
            suggestions[label] = {
                "regex": pattern,
                "count": count,
                "unique_examples": list(unique)[:5]
            }
    
    print("\n=== PATTERNS SUGGÉRÉS ===")
    for label, info in suggestions.items():
        print(f"- {label} : {info['regex']}")
        print(f"  Exemples trouvés: {info['unique_examples']}")
        print(f"  Occurrences: {info['count']}")
    
    return suggestions

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python regex_pattern_generator.py <company_id> [index_name]")
        sys.exit(1)
    company_id = sys.argv[1]
    index_name = sys.argv[2] if len(sys.argv) > 2 else None
    suggest_patterns(company_id, index_name)
