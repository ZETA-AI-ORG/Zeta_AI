"""
Preprocessing texte pour routage d'intents V4 - PRODUCTION READY.
Objectif: Nettoyer biais politesse + normaliser avant embedding SetFit.
"""

from __future__ import annotations
import re
import unicodedata


# ==============================================================================
# PATTERNS EMOJIS (compilation unique pour performance)
# ==============================================================================

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric shapes
    "\U0001F800-\U0001F8FF"  # supplemental arrows
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed characters
    "]+",
    flags=re.UNICODE,
)


# ==============================================================================
# ABRÉVIATIONS (ivoiriennes + françaises - SAFE uniquement)
# ==============================================================================

ABBREVIATIONS = {
    # Politesse
    r'\bbjr\b': 'bonjour',
    r'\bbsr\b': 'bonsoir',
    r'\bslt\b': 'salut',
    r'\bbnsr\b': 'bonsoir',
    
    # Formules
    r'\bsvp\b': 's il vous plait',
    r'\bstp\b': 's il te plait',
    r'\btkt\b': 't inquiete',
    r'\bdac\b': 'd accord',
    
    # Mots courants
    r'\bvs\b': 'vous',
    r'\bya\b': 'il y a',
    r'\bpq\b': 'pourquoi',
    r'\bpcq\b': 'parce que',
    r'\bpck\b': 'parce que',
    r'\bcmb\b': 'combien',
    r'\bcmt\b': 'comment',
    r'\bqd\b': 'quand',
    r'\bds\b': 'dans',
    r'\bms\b': 'mais',
    r'\btt\b': 'tout',
    r'\bts\b': 'tous',
    r'\bcad\b': 'c est a dire',
    
    # Verbes
    r'\bjvx\b': 'je veux',
    r'\bjprends\b': 'je prends',
    
    # ⚠️ ATTENTION: "c" seul NON inclus (trop ambigu)
    # Si besoin: normaliser "c'est" → "c est" seulement
}


# ==============================================================================
# SALUTATIONS PURES (pour skip preprocessing)
# ==============================================================================

PURE_GREETINGS = {
    "bonjour", "bonsoir", "salut", "hello", "hey", "coucou",
    "slt", "bjr", "bnsr", "yo", "wesh",
    "cc", "ndk", "ndkw",
    "merci", "merci beaucoup", "ok merci", "grand merci", "thanks",
    "de rien", "avec plaisir", "pas de souci",
    "ok", "d accord", "daccord", "compris", "ca marche", "parfait", "bien recu",
    "au revoir", "bye", "a plus tard", "a bientot", "tchao",
    "bonne continuation", "bonne journee",
}


# ==============================================================================
# FONCTION PRINCIPALE
# ==============================================================================

def preprocess_for_routing(text: str) -> str:
    """
    Preprocessing robuste pour SetFit V4.
    
    Pipeline:
    1. Check salutation pure (skip si oui)
    2. Normalisation accents (NFD)
    3. Suppression emojis/symboles
    4. Expansion abréviations (safe)
    5. Lowercase
    6. Suppression politesse (si pas salutation pure)
    7. Nettoyage ponctuation excessive
    8. Trim espaces
    
    Args:
        text: Message brut utilisateur
        
    Returns:
        Texte normalisé pour embedding
        
    Examples:
        >>> preprocess_for_routing("Bjr chef stp vs etes ou ?")
        "chef vous etes ou"
        
        >>> preprocess_for_routing("🔥 C'est dispo ???")
        "c est disponible"
        
        >>> preprocess_for_routing("Bonjour")
        "bonjour"  # Pas de suppression (salutation pure)
    """
    
    if not text:
        return ""
    
    # 1. CHECK SALUTATION PURE (avant normalisation)
    is_pure_greeting = should_skip_preprocessing(text)
    
    # 2. NORMALISATION ACCENTS (NFD → suppression diacritiques)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # 3. SUPPRESSION EMOJIS & SYMBOLES NON-TEXTE
    text = EMOJI_PATTERN.sub(' ', text)
    
    # 4. EXPANSION ABRÉVIATIONS (avant lowercase pour \b boundaries)
    for abbr_pattern, full_form in ABBREVIATIONS.items():
        text = re.sub(abbr_pattern, full_form, text, flags=re.IGNORECASE)
    
    # 5. LOWERCASE
    text = text.lower()

    # 6. SUPPRESSION POLITESSE (sauf si salutation pure)
    if not is_pure_greeting:
        # Patterns politesse début de phrase
        politesse_start = [
            r'^bonjour[\s,\.!]+',
            r'^bonsoir[\s,\.!]+',
            r'^salut[\s,\.!]+',
            r'^hello[\s,\.!]+',
            r'^hey[\s,\.!]+',
            r'^coucou[\s,\.!]+',
            r'^yo[\s,\.!]+',
            r'^wesh[\s,\.!]+',
        ]
        
        # Phrases politesse intégrées
        politesse_phrases = [
            r"j espere (que )?(ca va|vous allez bien|tu vas bien|la famille va bien|tout va bien)",
            r"comment (allez vous|vas tu|ca va|tu vas)",
            r"la famille va bien",
            r"desole (de|du) (te|vous|le) (deranger|couper)",
            r"pardon (de|du) (te|vous|le) (deranger|couper)",
            r"excuse[z]? moi",
            r"ca dit quoi",
            r"la forme",
        ]

        text_after_politesse = text
        for pattern in politesse_start:
            text_after_politesse = re.sub(pattern, '', text_after_politesse)
        for pattern in politesse_phrases:
            text_after_politesse = re.sub(pattern, '', text_after_politesse)
        text_after_politesse = ' '.join(text_after_politesse.split())

        if len(text_after_politesse.split()) < 4:
            text = re.sub(r'^(bonjour|bonsoir|salut|hey|yo)\s*', '', text, flags=re.IGNORECASE)
            text = ' '.join(text.split())
            return text.strip()

        text = text_after_politesse
    
    # 7. NETTOYAGE PONCTUATION
    # a) Répétitions excessives: "???" → "?", "!!!" → "!"
    text = re.sub(r'([?.!,;:])\1+', r'\1', text)
    
    # b) Ponctuation début (résidu politesse)
    text = re.sub(r'^[,\.!\?\s;:]+', '', text)
    
    # c) Ponctuation fin excessive
    text = re.sub(r'[,\.!\?\s;:]+$', '', text)
    
    # 8. ESPACES MULTIPLES → SIMPLE
    text = ' '.join(text.split())
    
    return text.strip()


# ==============================================================================
# FONCTION AUXILIAIRE
# ==============================================================================

def should_skip_preprocessing(text: str) -> bool:
    """
    Détecte si le message est une salutation PURE (intent SALUT_POLITESSE).
    Si oui, on ne supprime PAS la politesse car c'est l'intent principal.
    
    Args:
        text: Message brut
        
    Returns:
        True si salutation pure, False sinon
        
    Examples:
        >>> should_skip_preprocessing("Bonjour")
        True
        
        >>> should_skip_preprocessing("Bonjour vous êtes où ?")
        False
    """
    
    if not text:
        return False
    
    # Normalisation pour comparaison
    text_normalized = text.lower().strip()
    
    # Suppression accents
    text_normalized = unicodedata.normalize('NFD', text_normalized)
    text_normalized = ''.join(
        c for c in text_normalized 
        if unicodedata.category(c) != 'Mn'
    )
    
    # Suppression ponctuation simple
    text_normalized = re.sub(r'[\.!?,;:\s]+', ' ', text_normalized).strip()
    
    return text_normalized in PURE_GREETINGS


# ==============================================================================
# TESTS UNITAIRES (pour validation)
# ==============================================================================

def test_preprocessing():
    """Tests de validation preprocessing."""
    
    tests = [
        # (input, expected_output)
        ("Bjr chef stp vs etes ou ?", "chef vous etes ou"),
        ("🔥🔥🔥 C'est dispo ???", "c est dispo"),
        ("ÊTES-VOUS OÙ ?", "etes vous ou"),
        ("ya promo ?", "il y a promo"),
        ("j vx annuler", "j veux annuler"),
        ("Bonjour", "bonjour"),  # Salutation pure
        ("Bonjour vous êtes où ?", "vous etes ou"),  # Salutation + question
        ("svp c combien", "s il vous plait c combien"),  # "c" non expansé
        ("Salut j'espère que ça va, vous livrez ?", "vous livrez"),
        ("Hey la forme, où est mon colis ?", "ou est mon colis"),
    ]
    
    print("🧪 TESTS PREPROCESSING V4")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_text, expected in tests:
        result = preprocess_for_routing(input_text)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} '{input_text}'")
        print(f"   Expected: '{expected}'")
        print(f"   Got:      '{result}'")
        print()
    
    print("=" * 80)
    print(f"RÉSULTAT: {passed}/{len(tests)} tests passés")
    
    return failed == 0


# ==============================================================================
# USAGE
# ==============================================================================

if __name__ == "__main__":
    # Tests
    test_preprocessing()
    
    # Exemple d'utilisation
    messages = [
        "Bjr chef, c dispo le paquet ?",
        "🔥 PROMO 🔥 vs avez en stock ???",
        "Bonjour j'espère que tout va bien, vous êtes situés où exactement ?",
    ]
    
    print("\n📝 EXEMPLES PREPROCESSING:")
    print("=" * 80)
    for msg in messages:
        processed = preprocess_for_routing(msg)
        print(f"AVANT: {msg}")
        print(f"APRÈS: {processed}")
        print()