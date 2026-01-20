#!/usr/bin/env python3
"""
🎭 SCÉNARIOS DE TEST CONVERSATIONNEL

3 niveaux de difficulté pour tester le chatbot:
- LIGHT: Client informé, conversion facile
- MEDIUM: Client hésitant, plusieurs objections
- HARDCORE: Client difficile, multiples changements, objections fortes

Basé sur: Rue du Grossiste (couches bébé en gros)
"""

# ============================================================================
# 🔵 SCÉNARIO MICRO - Test Fallback OCR Uniquement
# ============================================================================
# Objectif: Valider UNIQUEMENT le système de fallback OCR automatique
# Difficulté: ⭐☆☆☆☆
# Tours attendus: 3
# Temps estimé: ~15s

SCENARIO_MICRO = {
    "name": "micro_ocr_fallback",
    "description": "Test minimal du fallback OCR : 1 paiement insuffisant + 1 paiement valide",
    "persona": {
        "profil": "Test technique",
        "motivation": "Valider OCR",
        "niveau_urgence": "Test"
    },
    "objectif_test": "Vérifier que le système détecte automatiquement les images de paiement et active Botlive",
    "messages": [
        # Tour 1: Envoi paiement INSUFFISANT (1000 FCFA)
        {"text": "Voici mon paiement Wave", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=DamxAq1f9OwQ7kNvwFSbPlg&_nc_oc=AdlYZF2Q2WyPz7SoP6HFp7gZCnmgAysN4ZCziXM2nHv8itrZrced2lMSff1szWQ9V-7WRbl3vV_-uJ9l3-Uxq7ha&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFO-SvfS03vBW39la32NGTcsXuPEGNsnVA6mSvUHOResw&oe=691D864A"},
        
        # Tour 2: Correction
        "Ok je renvoie le bon montant",
        
        # Tour 3: Envoi paiement CORRECT (2000 FCFA)
        {"text": "Voilà 2000 FCFA", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=7oeAkz1vXk4Q7kNvwHsBEm8&_nc_oc=AdkRG6vf8C7mCWK6G0223SycGhXGPZ9S5mn8iK369aoCBNGNFLGSYK0R-yFITkJ-uro_BO7rcX9W2ximO0S4l25C&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFy4KBx2MWFGHs3HzwWsG7vQiUcM4NU3IBpkP2B5ZoWAQ&oe=691D9DCA"}
    ],
    "kpis_attendus": {
        "temps_total": "<20s",
        "ocr_1000_detecte": True,
        "ocr_2000_detecte": True,
        "fallback_botlive_active": True,
        "statut_insuffisant": "rejeté",
        "statut_valide": "accepté"
    }
}

# ============================================================================
# 🟢 SCÉNARIO LIGHT - Client Informé & Décidé
# ============================================================================
# Objectif: Tester qualification rapide et closing efficace
# Difficulté: ⭐☆☆☆☆
# Tours attendus: 4-6
# Taux conversion attendu: 90%+

SCENARIO_LIGHT = {
    "name": "light_client_informe",
    "description": "Client pressé qui sait ce qu'il veut, test complet avec paiement OCR",
    "persona": {
        "profil": "Mère de famille, cliente fidèle, connaît le produit",
        "motivation": "Réappro rapide",
        "niveau_urgence": "Haute"
    },
    "objectif_test": "Vérifier vitesse de qualification, précision des réponses et fallback paiement OCR",
    "messages": [
        # Tour 1: Question directe prix
        "Bonjour, combien coûte un lot de 300 couches taille 3?",
        
        # Tour 2: Choix type + livraison
        "Je prends les couches à pression. Je suis à Yopougon, c'est combien la livraison?",
        
        # Tour 3: Validation + demande commande
        "Super! Je veux commander alors. Comment faire?",
        
        # Tour 4: Fourniture téléphone
        "Mon numéro c'est le 0708123456",
        
        # Tour 5: Envoi paiement INSUFFISANT (1000 FCFA)
        {"text": "Voilà j'ai envoyé le paiement Wave", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=DamxAq1f9OwQ7kNvwFSbPlg&_nc_oc=AdlYZF2Q2WyPz7SoP6HFp7gZCnmgAysN4ZCziXM2nHv8itrZrced2lMSff1szWQ9V-7WRbl3vV_-uJ9l3-Uxq7ha&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFO-SvfS03vBW39la32NGTcsXuPEGNsnVA6mSvUHOResw&oe=691D864A"},
        
        # Tour 6: Correction après rejet
        "Ah désolé, je renvoie le bon montant",
        
        # Tour 7: Envoi paiement CORRECT (2000 FCFA)
        {"text": "Voilà 2000 FCFA maintenant", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=7oeAkz1vXk4Q7kNvwHsBEm8&_nc_oc=AdkRG6vf8C7mCWK6G0223SycGhXGPZ9S5mn8iK369aoCBNGNFLGSYK0R-yFITkJ-uro_BO7rcX9W2ximO0S4l25C&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFy4KBx2MWFGHs3HzwWsG7vQiUcM4NU3IBpkP2B5ZoWAQ&oe=691D9DCA"},
        
        # Tour 8: Confirmation finale
        "Oui je confirme ma commande. Livraison demain ok"
    ],
    "kpis_attendus": {
        "confiance_finale": ">90%",
        "completude": "5/5 (100%)",
        "temps_moyen_tour": "<5s",
        "conversion": True,
        "ocr_paiement_insuffisant": "detecte",
        "ocr_paiement_valide": "detecte",
        "fallback_botlive": "active"
    }
}

# ============================================================================
# 🟡 SCÉNARIO MEDIUM - Client Hésitant
# ============================================================================
# Objectif: Tester gestion objections et réassurance
# Difficulté: ⭐⭐⭐☆☆
# Tours attendus: 8-12
# Taux conversion attendu: 70%

SCENARIO_MEDIUM = {
    "name": "medium_client_hesitant",
    "description": "Client intéressé mais plusieurs objections (prix, qualité, délais)",
    "persona": {
        "profil": "Nouveau client, méfiant, compare les offres",
        "motivation": "Cherche bon rapport qualité/prix",
        "niveau_urgence": "Moyenne"
    },
    "objectif_test": "Vérifier capacité à rassurer, gérer objections, maintenir l'engagement",
    "messages": [
        # Tour 1: Question vague
        "Salut, vous vendez des couches?",
        
        # Tour 2: Demande détails
        "C'est quoi vos tailles disponibles? Mon bébé fait 8kg",
        
        # Tour 3: Objection prix
        "22.900 FCFA c'est cher! J'ai vu moins cher ailleurs...",
        
        # Tour 4: Hésitation + comparaison
        "Oui mais comment je sais que vos couches sont de bonne qualité?",
        
        # Tour 5: Question livraison
        "D'accord... Et vous livrez à Cocody?",
        
        # Tour 6: Objection délais
        "1500 FCFA de livraison? Et ça prend combien de temps?",
        
        # Tour 7: Réflexion + changement d'avis
        "Hmm... En fait je vais prendre des culottes plutôt. C'est combien?",
        
        # Tour 8: Question paiement
        "Ok je réfléchis... Vous acceptez quel mode de paiement?",
        
        # Tour 9: Objection acompte
        "Il faut payer 2000 FCFA d'avance?? Pourquoi?",
        
        # Tour 10: Tentative négociation
        "Et si je commande 2 lots, vous faites un geste sur le prix?",
        
        # Tour 11: Hésitation finale
        "Bon... Laissez-moi voir. Comment je passe commande si je me décide?",
        
        # Tour 12: Engagement (ou pas)
        "Ok je prends. Mon numéro: 0701234567"
    ],
    "kpis_attendus": {
        "confiance_finale": ">75%",
        "completude": "4/5 ou 5/5",
        "temps_moyen_tour": "<7s",
        "objections_gerees": 5,
        "conversion": True
    }
}

# ============================================================================
# 🔴 SCÉNARIO HARDCORE - Client Très Difficile
# ============================================================================
# Objectif: Test limite du système (objections fortes, changements multiples, confusion)
# Difficulté: ⭐⭐⭐⭐⭐
# Tours attendus: 15-20
# Taux conversion attendu: 40-50%

SCENARIO_HARDCORE = {
    "name": "hardcore_client_difficile",
    "description": "Client confus, change d'avis constamment, objections fortes, teste les limites",
    "persona": {
        "profil": "Client suspicieux, mauvaise expérience passée, cherche la faille",
        "motivation": "Méfiant, besoin de beaucoup de réassurance",
        "niveau_urgence": "Basse"
    },
    "objectif_test": "Tester robustesse, cohérence, gestion situations complexes",
    "messages": [
        # Tour 1: Question floue
        "Yo",
        
        # Tour 2: Question hors sujet
        "Vous vendez aussi des biberons?",
        
        # Tour 3: Retour au sujet mais confus
        "Ah ok. Bon euh... mon bébé a 5 mois, il fait 7kg je crois... ou 8... j'sais plus. Vous avez quoi?",
        
        # Tour 4: Objection prix violente
        "QUOI 22.900???? C'est du vol! Sur Internet c'est 15.000!",
        
        # Tour 5: Remise en question qualité
        "Et c'est même pas des vraies marques! C'est chinois vos trucs non?",
        
        # Tour 6: Changement sujet brusque
        "Bon laissez tomber. Parlez-moi plutôt des culottes",
        
        # Tour 7: Confusion totale
        "Attendez c'est 150 ou 300? Je comprends rien à vos prix",
        
        # Tour 8: Objection livraison
        "Je suis à Anyama. 2500 FCFA??? Non mais c'est abusé!",
        
        # Tour 9: Teste limite service
        "Et si je viens chercher moi-même? Vous êtes où exactement?",
        
        # Tour 10: Objection paiement
        "Wave seulement? J'ai pas Wave moi! Vous prenez pas MTN Money?",
        
        # Tour 11: Changement d'avis complet
        "Vous savez quoi, je vais plutôt prendre les couches à pression finalement",
        
        # Tour 12: Question pièges mix informations
        "Taille 4 ça va pour 7kg c'est bon? Parce que taille 3 c'est jusqu'à 11kg vous avez dit",
        
        # Tour 13: Objection acompte agressive
        "2000 FCFA d'acompte?! Et si vous disparaissez avec mon argent? Comment je suis sûr?",
        
        # Tour 14: Demande garantie excessive
        "Vous avez une garantie? Genre si mon bébé fait une allergie je peux retourner?",
        
        # Tour 15: Tentative négociation impossible
        "Et si je prends 10 lots là, vous me faites 50% de réduction?",
        
        # Tour 16: Comparaison concurrence
        "Parce que chez Carrefour ils font des promos à -30%...",
        
        # Tour 17: Question livraison impossible
        "Vous livrez au Ghana? Mon cousin habite là-bas",
        
        # Tour 18: Retour brutal au sujet
        "Bon ok forget. Recapitulez-moi TOUT pour taille 3, 300 couches, Anyama",
        
        # Tour 19: Dernière objection
        "Hmm... Et je peux payer moitié maintenant moitié à la livraison?",
        
        # Tour 20: Acceptation conditionnelle
        "Bon ok... Je vais faire le dépôt. C'est quoi déjà le numéro Wave?",
        
        # Tour 21: Envoi screenshot paiement INSUFFISANT (URL image réelle)
        {"text": "Voilà j'ai envoyé", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=DamxAq1f9OwQ7kNvwFSbPlg&_nc_oc=AdlYZF2Q2WyPz7SoP6HFp7gZCnmgAysN4ZCziXM2nHv8itrZrced2lMSff1szWQ9V-7WRbl3vV_-uJ9l3-Uxq7ha&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFO-SvfS03vBW39la32NGTcsXuPEGNsnVA6mSvUHOResw&oe=691D864A"},
        
        # Tour 22: Correction après rejet OCR
        "Ah merde j'ai envoyé que 202. Attends je renvoie le bon montant",
        
        # Tour 23: Envoi screenshot paiement CORRECT 2020 FCFA (URL image réelle)
        {"text": "Voilà maintenant c'est bon, 2020 FCFA", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=7oeAkz1vXk4Q7kNvwHsBEm8&_nc_oc=AdkRG6vf8C7mCWK6G0223SycGhXGPZ9S5mn8iK369aoCBNGNFLGSYK0R-yFITkJ-uro_BO7rcX9W2ximO0S4l25C&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFy4KBx2MWFGHs3HzwWsG7vQiUcM4NU3IBpkP2B5ZoWAQ&oe=691D9DCA"},
        
        # Tour 24: Confirmation numéro
        "Ok c'est validé? Mon numéro: 0701234567",
        
        # Tour 25: Demande récapitulatif complet
        "Bon récapitule-moi TOUT avant que je valide définitivement",
        
        # Tour 26: Validation finale
        "Ok c'est bon, je confirme la commande. Livraison demain possible?"
    ],
    "kpis_attendus": {
        "confiance_finale": ">90%",
        "completude": "5/5 (100%)",
        "temps_moyen_tour": "<10s",
        "objections_gerees": 10,
        "coherence_maintenue": True,
        "conversion": True,
        "recap_complet": True
    }
}

# ============================================================================
# DICTIONNAIRE GLOBAL
# ============================================================================

SCENARIOS = {
    "micro": SCENARIO_MICRO,
    "light": SCENARIO_LIGHT,
    "medium": SCENARIO_MEDIUM,
    "hardcore": SCENARIO_HARDCORE
}

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def get_scenario(name: str):
    """Récupère un scénario par nom"""
    return SCENARIOS.get(name)

def list_scenarios():
    """Liste tous les scénarios disponibles"""
    for name, scenario in SCENARIOS.items():
        print(f"\n📋 {name.upper()}:")
        print(f"   Description: {scenario['description']}")
        print(f"   Tours: {len(scenario['messages'])}")
        print(f"   Persona: {scenario['persona']['profil']}")

def get_scenario_summary():
    """Retourne résumé de tous les scénarios"""
    summary = {}
    for name, scenario in SCENARIOS.items():
        summary[name] = {
            "description": scenario["description"],
            "nb_tours": len(scenario["messages"]),
            "difficulte": scenario.get("difficulte", "N/A"),
            "conversion_attendue": scenario["kpis_attendus"].get("conversion", "N/A")
        }
    return summary


if __name__ == "__main__":
    print("🎭 SCÉNARIOS DE TEST DISPONIBLES\n")
    list_scenarios()
    
    print("\n" + "="*80)
    print("💡 UTILISATION:")
    print("   python tests/conversation_simulator.py --scenario micro     # 3 tours - Test OCR uniquement")
    print("   python tests/conversation_simulator.py --scenario light     # 8 tours - Client informé")
    print("   python tests/conversation_simulator.py --scenario medium    # 15 tours - Client hésitant")
    print("   python tests/conversation_simulator.py --scenario hardcore  # 26 tours - Client difficile")
    print("="*80)
