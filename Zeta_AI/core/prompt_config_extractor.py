#!/usr/bin/env python3
"""
🔧 EXTRACTEUR DE CONFIGURATION ENTREPRISE DEPUIS PROMPT
======================================================

Extrait les données de configuration (acompte, numéro Wave, etc.)
depuis le prompt RAG pour validation paiement dynamique.

Format attendu dans le prompt:
```
## CONFIGURATION ENTREPRISE (NE PAS MODIFIER)
WHATSAPP_ENTREPRISE: +225 0160924560
WAVE_ENTREPRISE: +225 0787360757
ACOMPTE_REQUIS: 2000 FCFA
```
"""

import re
from typing import Dict, Optional


def extract_company_config(prompt: str) -> Dict[str, str]:
    """
    Extrait la configuration entreprise depuis le prompt RAG
    
    Args:
        prompt: Prompt complet du RAG
        
    Returns:
        {
            'whatsapp': '+225 0160924560',
            'wave': '+225 0787360757',
            'acompte': '2000',
            'acompte_full': '2000 FCFA'
        }
    """
    config = {
        'whatsapp': None,
        'wave': None,
        'acompte': None,
        'acompte_full': None
    }
    
    # Pattern pour extraire la section CONFIGURATION ENTREPRISE
    config_section_pattern = r'## CONFIGURATION ENTREPRISE.*?(?=##|---|\Z)'
    config_match = re.search(config_section_pattern, prompt, re.DOTALL | re.IGNORECASE)
    
    if not config_match:
        print("[CONFIG_EXTRACTOR] ⚠️ Section CONFIGURATION ENTREPRISE non trouvée")
        return config
    
    config_section = config_match.group(0)
    
    # Extraire WhatsApp
    whatsapp_pattern = r'WHATSAPP_ENTREPRISE:\s*(\+?\d+[\s\d]+)'
    whatsapp_match = re.search(whatsapp_pattern, config_section)
    if whatsapp_match:
        config['whatsapp'] = whatsapp_match.group(1).strip()
    
    # Extraire Wave
    wave_pattern = r'WAVE_ENTREPRISE:\s*(\+?\d+[\s\d]+)'
    wave_match = re.search(wave_pattern, config_section)
    if wave_match:
        config['wave'] = wave_match.group(1).strip()
    
    # Extraire Acompte
    acompte_pattern = r'ACOMPTE_REQUIS:\s*(\d+)\s*FCFA'
    acompte_match = re.search(acompte_pattern, config_section)
    if acompte_match:
        config['acompte'] = acompte_match.group(1)
        config['acompte_full'] = f"{acompte_match.group(1)} FCFA"
    
    print(f"[CONFIG_EXTRACTOR] ✅ Configuration extraite:")
    print(f"   - WhatsApp: {config['whatsapp']}")
    print(f"   - Wave: {config['wave']}")
    print(f"   - Acompte: {config['acompte_full']}")
    
    return config


def get_required_deposit(prompt: str) -> int:
    """
    Extrait le montant de l'acompte requis depuis le prompt
    
    Args:
        prompt: Prompt complet du RAG
        
    Returns:
        Montant en FCFA (int), par défaut 2000
    """
    config = extract_company_config(prompt)
    
    if config['acompte']:
        try:
            return int(config['acompte'])
        except ValueError:
            pass
    
    # Fallback: chercher "2000 FCFA" n'importe où dans le prompt
    fallback_pattern = r'(\d{3,5})\s*FCFA'
    matches = re.findall(fallback_pattern, prompt)
    
    if matches:
        # Prendre le montant le plus fréquent (probablement l'acompte)
        from collections import Counter
        most_common = Counter(matches).most_common(1)
        if most_common:
            try:
                return int(most_common[0][0])
            except ValueError:
                pass
    
    print("[CONFIG_EXTRACTOR] ⚠️ Acompte non trouvé, fallback à 2000 FCFA")
    return 2000


def get_company_wave_number(prompt: str) -> Optional[str]:
    """
    Extrait le numéro Wave de l'entreprise depuis le prompt
    
    Args:
        prompt: Prompt complet du RAG
        
    Returns:
        Numéro Wave normalisé (ex: "0787360757") ou None
    """
    config = extract_company_config(prompt)
    
    if config['wave']:
        # Normaliser le numéro (retirer +225, espaces, etc.)
        import re
        normalized = re.sub(r'[^\d]', '', config['wave'])
        # Garder les 10 derniers chiffres
        return normalized[-10:] if len(normalized) >= 10 else normalized
    
    return None


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("🧪 TEST EXTRACTEUR CONFIGURATION\n")
    
    # Prompt de test
    test_prompt = """# IDENTITÉ
Tu es Jessica, agent commercial IA de RUEDUGROSSISTE.

## CONFIGURATION ENTREPRISE (NE PAS MODIFIER)
WHATSAPP_ENTREPRISE: +225 0160924560
WAVE_ENTREPRISE: +225 0787360757
ACOMPTE_REQUIS: 2000 FCFA

---

## MISSION
Collecter 5 données...
"""
    
    print("Test 1: Extraction complète")
    config = extract_company_config(test_prompt)
    assert config['whatsapp'] == '+225 0160924560', "WhatsApp incorrect"
    assert config['wave'] == '+225 0787360757', "Wave incorrect"
    assert config['acompte'] == '2000', "Acompte incorrect"
    print("   ✅ SUCCÈS\n")
    
    print("Test 2: Extraction acompte seul")
    acompte = get_required_deposit(test_prompt)
    assert acompte == 2000, f"Acompte incorrect: {acompte}"
    print(f"   ✅ SUCCÈS: {acompte} FCFA\n")
    
    print("Test 3: Extraction numéro Wave normalisé")
    wave = get_company_wave_number(test_prompt)
    assert wave == '0787360757', f"Wave incorrect: {wave}"
    print(f"   ✅ SUCCÈS: {wave}\n")
    
    print("Test 4: Prompt sans section config (fallback)")
    prompt_sans_config = "Tu es Jessica. Acompte 2000 FCFA requis."
    acompte_fallback = get_required_deposit(prompt_sans_config)
    assert acompte_fallback == 2000, "Fallback incorrect"
    print(f"   ✅ SUCCÈS (fallback): {acompte_fallback} FCFA\n")
    
    print("✅ TOUS LES TESTS PASSÉS!")
