import re
from typing import List, Dict
import json
import os

# Chargement dynamique des patterns depuis le JSON config/patterns_metier.json
PATTERNS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'patterns_metier.json')
try:
    with open(PATTERNS_PATH, 'r', encoding='utf-8') as f:
        PATTERNS = json.load(f)
except FileNotFoundError:
    # Fallback patterns si le fichier JSON n'existe pas
    PATTERNS = {
        "acompte": r"acompte.*?(\d{1,3}(?:[ .]\d{3})*|\d+).*?fcfa",
        "montant_fcfa": r"(\d{1,3}(?:[ .]\d{3})*|\d+)\s*f\.?\s*cfa",
        "pourcentage": r"(\d{1,3})%",
        "phone": r"\+225\d{8,10}|0\d{9}",
        "email": r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
        "whatsapp": r"whatsapp.*?(\+225\d{8,10}|0\d{9})",
        "iban": r"[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}",
        "date_fr": r"\d{1,2}/\d{1,2}/\d{2,4}",
        "siret": r"\d{14}",
        "condition_commande": r"condition.*?commande.*?(\d+).*?fcfa"
    }

# Import du système d'auto-apprentissage
try:
    from .dynamic_pattern_learner import auto_learn_patterns
    AUTO_LEARNING_ENABLED = True
except ImportError:
    AUTO_LEARNING_ENABLED = False

def extract_regex_entities_from_docs(docs: List[Dict], patterns: Dict[str, str] = PATTERNS, enable_learning: bool = True) -> Dict[str, List[str]]:
    """Applique chaque regex sur chaque document et retourne les extraits trouvés"""
    results = {label: [] for label in patterns}
    
    # Phase 1: Extraction avec patterns existants
    for doc in docs:
        content = doc.get('content', '')
        for label, pattern in patterns.items():
            found = re.findall(pattern, content, re.IGNORECASE)
            if found:
                for match in found:
                    snippet = extract_snippet(content, match)
                    if snippet and snippet not in results[label]:
                        results[label].append(snippet)
    
    # Phase 2: Auto-apprentissage de nouveaux patterns (si activé)
    if enable_learning and AUTO_LEARNING_ENABLED:
        try:
            new_patterns_count = auto_learn_patterns(docs, PATTERNS_PATH)
            if new_patterns_count > 0:
                print(f" {new_patterns_count} nouveaux patterns appris automatiquement!")
                
                # Recharger les patterns mis à jour
                global PATTERNS
                with open(PATTERNS_PATH, 'r', encoding='utf-8') as f:
                    PATTERNS = json.load(f)
                
                # Ré-extraire avec les nouveaux patterns
                for doc in docs:
                    content = doc.get('content', '')
                    for label, pattern in PATTERNS.items():
                        if label not in results:
                            results[label] = []
                        found = re.findall(pattern, content, re.IGNORECASE)
                        if found:
                            for match in found:
                                snippet = extract_snippet(content, match)
                                if snippet and snippet not in results[label]:
                                    results[label].append(snippet)
        except Exception as e:
            print(f" Erreur auto-apprentissage: {e}")
    
    return results

def extract_snippet(text, match, window=40):
    idx = text.lower().find(str(match).lower())
    if idx == -1:
        return str(match)
    start = max(0, idx - window)
    end = min(len(text), idx + len(str(match)) + window)
    return text[start:end]
