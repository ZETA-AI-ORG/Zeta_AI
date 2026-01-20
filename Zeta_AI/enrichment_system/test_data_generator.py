#!/usr/bin/env python3
"""
💩 GÉNÉRATEUR DE DONNÉES POURRIES - Test de robustesse
Crée des documents volontairement ambigus, avec fautes, brouillons
"""
from typing import List, Dict

def generate_messy_test_data() -> List[Dict]:
    """
    Génère des données volontairement mauvaises pour tester la robustesse
    
    Returns:
        Liste de documents avec problèmes variés
    """
    
    return [
        # TEST 1: Fautes d'orthographe + ambiguïté tailles
        {
            "id": "test_001",
            "product_name": "Couch culottes bébé",  # Faute: Couch au lieu de Couches
            "category": "baby_care",
            "description": "couches disponnible en toute les taille entre 5 et 30kg",  # Plusieurs fautes
            "price": 13500,
            "notes": "prix 13500 fcfa",
            "expected_issues": [
                "Faute: 'Couch' → 'Couches'",
                "Faute: 'disponnible' → 'disponible'",
                "Ambiguïté: Quelles tailles exactement ?",
                "Ambiguïté: Prix unique ou variable ?"
            ]
        },
        
        # TEST 2: Texte très brouillon + informations manquantes
        {
            "id": "test_002",
            "product_name": "livrasion abidjan",  # Faute + mal catégorisé
            "category": "delivery",
            "description": "on livre partout a abidjan , les prix varie selon zone",  # Vague
            "notes": "livrasion rapide garanti client satisfait ou remboursé",  # Fautes multiples
            "expected_issues": [
                "Faute: 'livrasion' → 'livraison'",
                "Faute: 'garanti' → 'garantie'",
                "Ambiguïté: Prix non précisés",
                "Ambiguïté: Quelles zones exactement ?",
                "Ambiguïté: Délais non mentionnés"
            ]
        },
        
        # TEST 3: Quantités floues + contradictions
        {
            "id": "test_003",
            "product_name": "Couches à pression",
            "category": "baby_care",
            "description": "vendu par lot minimum , disponible en plusieur taille , tres bonne qualité",  # Vague
            "price": 17000,
            "notes": "lot de 300 ou 150 pièce selon dispo",  # Contradiction avec "minimum"
            "expected_issues": [
                "Faute: 'plusieur' → 'plusieurs'",
                "Faute: 'pièce' → 'pièces'",
                "Ambiguïté: Lot minimum = combien ?",
                "Ambiguïté: Tailles disponibles ?",
                "Contradiction: '300 ou 150' vs 'minimum'"
            ]
        },
        
        # TEST 4: Informations éparpillées + structure chaotique
        {
            "id": "test_004",
            "product_name": "paiemant wave",  # Faute + mal catégorisé
            "category": "payment",
            "description": "on accepte wave seulment , acompte obligatoir , le solde a la livraison",  # Fautes partout
            "notes": "numéro : +225 07 XX XX XX XX , contactez nous pour commander",
            "expected_issues": [
                "Faute: 'paiemant' → 'paiement'",
                "Faute: 'seulment' → 'seulement'",
                "Faute: 'obligatoir' → 'obligatoire'",
                "Ambiguïté: Montant acompte non précisé",
                "Info manquante: Numéro incomplet"
            ]
        },
        
        # TEST 5: Mélange français/abréviations + aucune structure
        {
            "id": "test_005",
            "product_name": "couche bb t2 t3 t4",  # Abréviation + format télégraphique
            "category": "baby_care",
            "description": "couche bb toute taille dispo 5-30kg bon prix qualité top livraison 24h abj",  # Tout condensé
            "price": 18500,
            "notes": "prix varient selon qt commandé , appelé pour info",  # Fautes + vague
            "expected_issues": [
                "Format télégraphique non professionnel",
                "Faute: 'qt' → 'quantité'",
                "Faute: 'appelé' → 'appelez'",
                "Ambiguïté: Prix variables comment ?",
                "Ambiguïté: Tailles exactes ?",
                "Info manquante: Prix livraison"
            ]
        },
        
        # TEST 6: Données contradictoires + logique cassée
        {
            "id": "test_006",
            "product_name": "Couches premium",
            "category": "baby_care",
            "description": "prix unique 20000 fcfa pour toute commande , mais le prix change selon la quantité",  # Contradiction flagrante
            "notes": "minimum 100 pièces mais on vend aussi à l'unité",  # Contradiction
            "expected_issues": [
                "Contradiction: 'prix unique' vs 'prix change'",
                "Contradiction: 'minimum 100' vs 'vend à l'unité'",
                "Ambiguïté: Quel est le vrai prix ?",
                "Logique cassée: Incohérence totale"
            ]
        },
        
        # TEST 7: Informations critiques manquantes
        {
            "id": "test_007",
            "product_name": "Produit bébé",  # Trop vague
            "category": "baby_care",
            "description": "très bon produit pour bébé , recommandé par les mamans",  # Aucune info utile
            "notes": "contactez nous",
            "expected_issues": [
                "Nom produit trop vague",
                "Aucune info prix",
                "Aucune info taille/quantité",
                "Description inutile (marketing vide)",
                "Pas actionnable pour le client"
            ]
        },
        
        # TEST 8: Format chaotique + ponctuation aléatoire
        {
            "id": "test_008",
            "product_name": "COUCHES!!!PROMO!!!",  # Caps + ponctuation excessive
            "category": "baby_care",
            "description": "super promo !!! couches de 0 a 25 kg !!!! prix cassé!!!! appelez vite !!!",  # Spam-like
            "price": 15000,
            "notes": "quantite limité!!!stock disponible!!!",  # Faute + spam
            "expected_issues": [
                "Faute: 'quantite' → 'quantité'",
                "Format non professionnel (caps + !!!)",
                "Ambiguïté: 'Prix cassé' = combien exactement ?",
                "Ambiguïté: 'Quantité limitée' = combien ?",
                "Ambiguïté: Tailles exactes couvertes ?"
            ]
        },
        
        # TEST 9: Données numériques incohérentes
        {
            "id": "test_009",
            "product_name": "Couches économiques",
            "category": "baby_care",
            "description": "lot de 300 couches taille 2-6 pour bébé de 5 à 30kg",
            "price": 999999,  # Prix aberrant
            "quantity": -50,  # Quantité négative (!!)
            "notes": "livraison en 0 jours",  # Impossible
            "expected_issues": [
                "Prix aberrant: 999 999 FCFA (trop élevé)",
                "Quantité négative: -50",
                "Délai impossible: 0 jours",
                "Incohérence numérique globale"
            ]
        },
        
        # TEST 10: Tout mélangé (worst case scenario)
        {
            "id": "test_010",
            "product_name": "produi bb",  # Faute + abréviation
            "category": "baby_care",
            "description": "couch culottes disponnible toute taille 5-30kg vendu lot ou unitée prix varie 10000 ou 20000 selon livrasion abidjan ou pas garanti 100%",  # Tout cassé
            "notes": "contacté nous vite stock limité promo fin bientot appelé maintenan",  # Fautes partout
            "expected_issues": [
                "TOUTES les catégories d'erreurs",
                "Multiples fautes orthographe",
                "Multiples ambiguïtés",
                "Structure chaotique",
                "Ponctuation absente",
                "Informations contradictoires"
            ]
        }
    ]

def generate_clean_reference_data() -> List[Dict]:
    """
    Génère la version IDÉALE attendue après enrichissement
    Pour comparer avec les résultats de l'agent
    """
    
    return [
        # RÉFÉRENCE pour TEST 1
        {
            "id": "test_001",
            "product_name": "Couches culottes bébé",  # Corrigé
            "description": "Couches disponibles en toutes les tailles entre 5 et 30kg",  # Corrigé
            "searchable_text": """Couches culottes bébé
Prix UNIQUE: 13 500 FCFA pour TOUTES les tailles (5-30kg)
Tailles standard disponibles (à confirmer):
- Taille 2 (5-8kg): 13 500 FCFA
- Taille 3 (8-11kg): 13 500 FCFA
- Taille 4 (11-14kg): 13 500 FCFA
- Taille 5 (14-18kg): 13 500 FCFA
- Taille 6 (18-30kg): 13 500 FCFA
⚠️ Veuillez confirmer les tailles exactes disponibles""",
            "quality_improvements": [
                "Orthographe corrigée",
                "Ambiguïté prix levée",
                "Tailles listées explicitement",
                "Demande de confirmation ajoutée"
            ]
        },
        # ... (autres références)
    ]

if __name__ == "__main__":
    # Test génération
    messy_data = generate_messy_test_data()
    
    print(f"{'='*80}")
    print(f"💩 DONNÉES DE TEST GÉNÉRÉES")
    print(f"{'='*80}\n")
    print(f"Total documents pourris: {len(messy_data)}")
    
    for doc in messy_data:
        print(f"\n📄 {doc['id']}: {doc['product_name']}")
        print(f"   Problèmes attendus: {len(doc['expected_issues'])}")
        for issue in doc['expected_issues'][:3]:
            print(f"   - {issue}")
        if len(doc['expected_issues']) > 3:
            print(f"   - ... et {len(doc['expected_issues']) - 3} autres")
