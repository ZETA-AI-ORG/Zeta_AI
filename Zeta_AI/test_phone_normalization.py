#!/usr/bin/env python3
"""
🧪 TEST NORMALISATION NUMÉROS DE TÉLÉPHONE
Valide que le système gère TOUS les formats possibles
"""

from core.botlive_engine import BotliveEngine

def test_phone_normalization():
    """
    Teste tous les formats de numéros de téléphone possibles
    """
    engine = BotliveEngine()
    
    # Format: (input, expected_output, description)
    test_cases = [
        # Formats standards Côte d'Ivoire
        ("0787360757", "0787360757", "Format standard 10 chiffres"),
        ("07 87 36 07 57", "0787360757", "Avec espaces"),
        ("07-87-36-07-57", "0787360757", "Avec tirets"),
        ("07.87.36.07.57", "0787360757", "Avec points"),
        
        # Avec code pays
        ("+2250787360757", "0787360757", "Code pays collé"),
        ("+225 0787360757", "0787360757", "Code pays + espace"),
        ("+225 07 87 36 07 57", "0787360757", "Code pays + espaces"),
        ("+225-07-87-36-07-57", "0787360757", "Code pays + tirets"),
        ("225 07 87 36 07 57", "0787360757", "Code pays sans +"),
        
        # Avec emojis et caractères spéciaux
        ("📞 +225 07 87 36 07 57 ☎️", "0787360757", "Emojis téléphone"),
        ("📱 0787360757 ✅", "0787360757", "Emoji smartphone"),
        ("💬 +225 07 87 36 07 57", "0787360757", "Emoji message"),
        ("🇨🇮 +225 07 87 36 07 57", "0787360757", "Drapeau CI"),
        
        # Avec mots-clés
        ("WhatsApp: 07 87 36 07 57", "0787360757", "WhatsApp"),
        ("Tel: +225 07 87 36 07 57", "0787360757", "Tel"),
        ("Contact: 0787360757", "0787360757", "Contact"),
        ("Téléphone: 07 87 36 07 57", "0787360757", "Téléphone"),
        
        # Formats complexes
        ("Tel: 📱 +225-07.87.36.07.57 ✅", "0787360757", "Multi-formats combinés"),
        ("Contact: 💬 225 07 87 36 07 57 (WhatsApp)", "0787360757", "Avec parenthèses"),
        ("☎️ +225 (0)7 87 36 07 57", "0787360757", "Avec (0)"),
        
        # Autres pays (pour tester la scalabilité)
        ("+33 6 12 34 56 78", "0612345678", "France"),
        ("+1-555-123-4567", "5551234567", "USA"),
        ("+44 20 7123 4567", "2071234567", "UK"),
        ("🇫🇷 +33 6.12.34.56.78", "0612345678", "France avec drapeau"),
    ]
    
    print("="*80)
    print("🧪 TEST NORMALISATION NUMÉROS DE TÉLÉPHONE")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for input_phone, expected, description in test_cases:
        result = engine._normalize_phone(input_phone)
        
        if result == expected:
            print(f"✅ {description:40} | {input_phone:35} → {result}")
            passed += 1
        else:
            print(f"❌ {description:40} | {input_phone:35} → {result} (attendu: {expected})")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 RÉSULTATS: {passed}/{len(test_cases)} tests réussis ({passed/len(test_cases)*100:.1f}%)")
    
    if failed == 0:
        print("✅ TOUS LES FORMATS GÉRÉS CORRECTEMENT")
    else:
        print(f"⚠️ {failed} tests échoués")
    
    print("="*80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_phone_normalization()
    exit(0 if success else 1)
