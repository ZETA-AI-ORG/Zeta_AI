"""
Test du générateur de prompt dynamique
Valide la génération avec les vraies données company_booster
"""

import json
from core.dynamic_prompt_generator import generate_prompt_from_booster, get_prompt_for_company


# Données de test (copie de la table company_booster)
TEST_BOOSTER_DATA = {
    "id": 1,
    "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb",
    "keywords": ["abidjan", "rue du grossite", "whatsapp", "anyama", "bébé & puériculture", "culottes", "adjamé", "hors abidjan", "yopougon", "bingerville", "port-bouët", "dabou", "koumassi", "contact", "cocody", "couches à pression", "plateau", "abobo", "couches culottes", "grand-bassam", "brofodoumé", "wave", "treichville", "songon", "autres villes", "jessica", "attécoubé", "riviera", "cote d'ivoire", "marcory", "angré", "pression", "couches"],
    "categories": {
        "CONTACT": {
            "name": "",
            "zones": [],
            "phones": ["+2250160924560"],
            "sector": "",
            "methods": [],
            "keywords": ["whatsapp", "contact"],
            "products": []
        },
        "PRODUIT": {
            "name": "",
            "zones": [],
            "phones": [],
            "sector": "",
            "methods": [],
            "keywords": ["couches à pression", "couches culottes", "culottes", "pression", "couches"],
            "products": [
                {
                    "name": "Couches à pression",
                    "category": "Bébé & Puériculture",
                    "price_max": 24900,
                    "price_min": 17900,
                    "subcategory": "Soins Bébé - Couches"
                },
                {
                    "name": "Couches culottes",
                    "category": "Bébé & Puériculture",
                    "price_max": 24000,
                    "price_min": 13500,
                    "subcategory": "Soins Bébé - Couches"
                }
            ]
        },
        "PAIEMENT": {
            "name": "",
            "zones": [],
            "phones": [],
            "sector": "",
            "methods": [{"name": "Wave", "deposit": 2000}],
            "keywords": ["wave"],
            "products": []
        },
        "LIVRAISON": {
            "name": "",
            "zones": [
                {"name": "Yopougon", "price": 1500},
                {"name": "Cocody", "price": 1500},
                {"name": "Plateau", "price": 1500},
                {"name": "Adjamé", "price": 1500},
                {"name": "Abobo", "price": 1500},
                {"name": "Marcory", "price": 1500},
                {"name": "Koumassi", "price": 1500},
                {"name": "Treichville", "price": 1500},
                {"name": "Angré", "price": 1500},
                {"name": "Riviera", "price": 1500},
                {"name": "Port-Bouët", "price": 2000},
                {"name": "Attécoubé", "price": 2000},
                {"name": "Bingerville", "price": 2000},
                {"name": "Songon", "price": 2000},
                {"name": "Anyama", "price": 2000},
                {"name": "Brofodoumé", "price": 2000},
                {"name": "Grand-Bassam", "price": 2000},
                {"name": "Dabou", "price": 2000},
                {"name": "Hors Abidjan", "price": 3500},
                {"name": "Autres villes", "price": 3500}
            ],
            "phones": [],
            "sector": "",
            "methods": [],
            "keywords": ["anyama", "adjamé", "hors abidjan", "yopougon", "bingerville", "dabou", "port-bouët", "koumassi", "cocody", "plateau", "abobo", "grand-bassam", "brofodoumé", "treichville", "songon", "autres villes", "attécoubé", "riviera", "marcory", "angré"],
            "products": []
        },
        "ENTREPRISE": {
            "name": "RUEDUGROSSISTE",
            "zones": [],
            "phones": [],
            "sector": "Bébé & Puériculture",
            "methods": [],
            "keywords": ["rue du grossite"],
            "products": []
        }
    },
    "filters": {
        "price_range": {"max": 24900, "min": 13500},
        "product_names": ["Couches à pression", "Couches culottes"],
        "delivery_zones": {
            "abobo": 1500,
            "dabou": 2000,
            "angré": 1500,
            "anyama": 2000,
            "cocody": 1500,
            "songon": 2000,
            "adjamé": 1500,
            "marcory": 1500,
            "plateau": 1500,
            "riviera": 1500,
            "koumassi": 1500,
            "yopougon": 1500,
            "attécoubé": 2000,
            "bingerville": 2000,
            "brofodoumé": 2000,
            "port-bouët": 2000,
            "treichville": 1500,
            "grand-bassam": 2000,
            "hors abidjan": 3500,
            "autres villes": 3500
        },
        "payment_methods": ["Wave"]
    }
}


def test_prompt_generation():
    """Test de génération du prompt"""
    print("=" * 80)
    print("🧪 TEST GÉNÉRATION PROMPT DYNAMIQUE")
    print("=" * 80)
    
    try:
        # Génération du prompt
        prompt = generate_prompt_from_booster(TEST_BOOSTER_DATA, assistant_name="Jessica")
        
        print(f"\n✅ Prompt généré avec succès ({len(prompt)} caractères)\n")
        
        # Vérifications
        checks = [
            ("RUEDUGROSSISTE" in prompt, "Nom entreprise"),
            ("Bébé & Puériculture" in prompt, "Secteur"),
            ("+2250160924560" in prompt, "Téléphone WhatsApp"),
            ("2 000 Fcfa" in prompt, "Acompte"),
            ("Couches à pression" in prompt, "Produit 1"),
            ("Couches culottes" in prompt, "Produit 2"),
            ("17 900" in prompt, "Prix min"),
            ("24 900" in prompt, "Prix max"),
            ("Yopougon: 1 500 FCFA" in prompt, "Zone livraison 1"),
            ("Bingerville: 2 000 FCFA" in prompt, "Zone livraison 2"),
            ("Wave" in prompt, "Moyen de paiement"),
            ("<thinking>" in prompt, "Format thinking"),
            ("<response>" in prompt, "Format response"),
        ]
        
        print("📋 VÉRIFICATIONS:")
        all_passed = True
        for check, label in checks:
            status = "✅" if check else "❌"
            print(f"  {status} {label}")
            if not check:
                all_passed = False
        
        if all_passed:
            print("\n🎉 TOUS LES TESTS PASSÉS!")
        else:
            print("\n⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        
        # Afficher un extrait du prompt
        print("\n" + "=" * 80)
        print("📄 EXTRAIT DU PROMPT GÉNÉRÉ:")
        print("=" * 80)
        print(prompt[:1500] + "\n...\n[TRONQUÉ]\n...")
        
        # Sauvegarder le prompt complet
        with open("prompt_generated_test.txt", "w", encoding="utf-8") as f:
            f.write(prompt)
        print("\n💾 Prompt complet sauvegardé dans: prompt_generated_test.txt")
        
        return prompt
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_cache():
    """Test du système de cache"""
    print("\n" + "=" * 80)
    print("🧪 TEST SYSTÈME DE CACHE")
    print("=" * 80)
    
    from core.dynamic_prompt_generator import _prompt_cache, clear_prompt_cache
    
    company_id = TEST_BOOSTER_DATA["company_id"]
    
    # Vider le cache
    clear_prompt_cache()
    print(f"✅ Cache vidé")
    
    # Premier appel (cache miss)
    print(f"\n1️⃣ Premier appel (cache miss attendu)...")
    prompt1 = get_prompt_for_company(company_id, booster_data=TEST_BOOSTER_DATA)
    print(f"   Cache size: {len(_prompt_cache)}")
    
    # Deuxième appel (cache hit)
    print(f"\n2️⃣ Deuxième appel (cache hit attendu)...")
    prompt2 = get_prompt_for_company(company_id, booster_data=TEST_BOOSTER_DATA)
    print(f"   Cache size: {len(_prompt_cache)}")
    
    # Vérifier que les prompts sont identiques
    if prompt1 == prompt2:
        print(f"\n✅ Cache fonctionne correctement (prompts identiques)")
    else:
        print(f"\n❌ Erreur cache (prompts différents)")
    
    # Forcer le refresh
    print(f"\n3️⃣ Appel avec force_refresh...")
    prompt3 = get_prompt_for_company(company_id, booster_data=TEST_BOOSTER_DATA, force_refresh=True)
    print(f"   Cache size: {len(_prompt_cache)}")
    
    # Vider le cache spécifique
    print(f"\n4️⃣ Vidage cache spécifique...")
    clear_prompt_cache(company_id)
    print(f"   Cache size: {len(_prompt_cache)}")


if __name__ == "__main__":
    # Test génération
    prompt = test_prompt_generation()
    
    # Test cache
    if prompt:
        test_cache()
    
    print("\n" + "=" * 80)
    print("✅ TESTS TERMINÉS")
    print("=" * 80)
