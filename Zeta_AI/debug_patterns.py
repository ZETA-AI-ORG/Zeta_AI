#!/usr/bin/env python3
"""
🔍 DEBUG DES PATTERNS DE DÉTECTION
"""

import re

def test_patterns():
    """Test des patterns de détection"""
    print("🔍 TEST DES PATTERNS DE DÉTECTION")
    print("=" * 40)
    
    # Patterns de prix
    price_patterns = [
        r'\b\d+[€$£¥]\b',                    # Prix : "10€", "25$"
        r'\b\d+[.,]\d+[€$£¥]\b',            # Prix décimaux : "10.50€"
        r'\b\d+\s*(euros?|dollars?|€)\b',   # Prix en mots : "10 euros"
    ]
    
    test_texts = [
        "Le prix de notre produit est de 25€",
        "Bonjour ! Le prix est de 25€",
        "C'est notre produit X qui coûte 100€",
        "Le prix est de 50€",
        "25€",
        "100€",
    ]
    
    for text in test_texts:
        print(f"\nTexte: '{text}'")
        for i, pattern in enumerate(price_patterns):
            matches = re.findall(pattern, text)
            print(f"  Pattern {i+1}: {pattern}")
            print(f"  Matches: {matches}")
            if matches:
                print(f"  ✅ DÉTECTÉ")
            else:
                print(f"  ❌ NON DÉTECTÉ")

if __name__ == "__main__":
    test_patterns()