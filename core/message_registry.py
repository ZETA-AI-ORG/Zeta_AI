import random
from typing import Dict, List, Optional

def get_system_response(category: str, tone: str = "formal", **kwargs) -> str:
    """
    Génère une réponse système aléatoire basée sur la catégorie et le ton.
    Sécurité Niveau 1 : Zéro appel externe.
    
    Categories:
        - error_tech : Problèmes techniques, API, Database.
        - fallback_search : RAG n'a rien trouvé ou confiance faible.
        - ocr_product : Confirmation après détection produit.
        - ocr_payment : Confirmation après détection reçu de paiement.
        - price_list_intro : Introduction de la table des tarifs.
        - price_list_outro : Conclusion de la table des tarifs.
        - subscription_expired : Abonnement boutique expiré (Guardian).
        - quota_reached : Quota mensuel atteint (Guardian).
        - session_limit : Client a atteint sa limite de messages (Guardian).
    """
    
    registry: Dict[str, Dict[str, List[str]]] = {
        "error_tech": {
            "formal": [
                "Je rencontre une difficulté technique passagère. Un instant s'il vous plaît, je réessaie.",
                "Notre système est actuellement un peu ralenti. Merci de patienter quelques secondes.",
                "Une erreur réseau empêche temporairement l'accès au service. Je tente de rétablir la connexion."
            ],
            "casual": [
                "Oups, j'ai un petit bug technique ! Je règle ça et je reviens vers vous. 🛠️",
                "Mon système fait des siennes... On patiente une seconde ?",
                "Désolé, j'ai un petit souci pour accéder à l'info. Je retente le coup !"
            ]
        },
        "fallback_search": {
            "formal": [
                "Je n'ai pas pu identifier d'informations spécifiques sur ce sujet dans notre catalogue. Pourriez-vous préciser votre demande ?",
                "Mes recherches n'ont pas abouti pour l'instant. Pourriez-vous reformuler votre question ?",
                "Je ne suis pas certain de bien comprendre votre requête. Pourriez-vous me donner plus de contexte ?"
            ],
            "casual": [
                "Je n'arrive pas à mettre la main sur l'info exacte... Tu peux m'en dire plus ? 😊",
                "Je sèche un peu sur cette question. On parle bien d'un produit du catalogue ?",
                "Désolé, ma recherche n'a rien donné pour le moment. Tu peux reformuler ?"
            ]
        },
        "ocr_product": {
            "formal": [
                "Le produit suivant a été identifié : {name}. (Confiance : {confidence:.1f}%)",
                "J'ai reconnu l'article suivant : {name}. Est-ce correct ?",
                "Détection réussie. Il s'agit du produit : {name}."
            ],
            "casual": [
                "C'est bien noté ! J'ai reconnu : {name}. ✅",
                "Parfait, je vois que c'est le produit {name}. On continue ?",
                "Top ! J'ai bien identifié : {name}."
            ]
        },
        "ocr_payment": {
            "formal": [
                "Votre paiement de {amount} {currency} a été détecté avec succès. Référence : {ref}.",
                "Merci. J'ai bien validé la réception de {amount} {currency}.",
                "Le reçu de paiement a été analysé : montant de {amount} {currency} confirmé."
            ],
            "casual": [
                "Reçu 5/5 ! J'ai validé votre paiement de {amount} {currency}. 🎉",
                "Merci ! Le virement de {amount} {currency} est bien arrivé dans mon système.",
                "Super, c'est payé ! ({amount} {currency}). Je m'occupe de la suite."
            ]
        },
        "price_list_intro": {
            "formal": [
                "Voici les tarifs et formats disponibles actuellement pour ce produit :",
                "Veuillez trouver ci-dessous notre catalogue de prix à jour :",
                "Voici les options que nous pouvons vous proposer :"
            ],
            "casual": [
                "Bien sûr ! Voici ce que nous avons en stock actuellement :",
                "Voici nos tarifs et formats disponibles pour ce produit :",
                "Regarde ce qu'on a en rayon pour ça : 👇"
            ]
        },
        "price_list_outro": {
            "formal": [
                "Veuillez m'indiquer le numéro correspondant à votre choix.",
                "Quel format souhaitez-vous commander ? Dites-moi simplement le numéro.",
                "Je reste à votre disposition pour enregistrer le numéro de votre choix."
            ],
            "casual": [
                "Quel numéro te tente le plus ? Dis-le moi simplement. 😊",
                "Tu n'as plus qu'à me donner le numéro qui te convient !",
                "Dis-moi le numéro que tu préfères et on valide ça !"
            ]
        },
        # ══════════════════════════════════════════════════════════════════
        # 🛡️ GUARDIAN (V2.0) — Messages d'accès contrôlé
        # ══════════════════════════════════════════════════════════════════
        "subscription_expired": {
            "formal": [
                "Notre boutique est temporairement indisponible. Nous reviendrons très vite, merci de votre compréhension.",
                "Le service est actuellement suspendu. Veuillez nous recontacter prochainement, merci.",
                "Notre assistance est en pause le temps d'une mise à jour. Merci de revenir un peu plus tard."
            ],
            "casual": [
                "Oups, le service est en pause le temps d'une mise à jour ! On revient très vite 🙏",
                "La boutique est momentanément indisponible. Merci de repasser un peu plus tard 😊",
                "Petit break technique de notre côté. À très vite !"
            ]
        },
        "quota_reached": {
            "formal": [
                "Nous avons reçu un grand volume de demandes aujourd'hui. Veuillez réessayer plus tard, merci de votre patience.",
                "Notre service est très sollicité en ce moment. Merci de nous recontacter prochainement.",
                "Le traitement des demandes est temporairement saturé. Nous revenons vers vous dès que possible."
            ],
            "casual": [
                "Beaucoup de monde aujourd'hui ! Merci de revenir un peu plus tard 🙏",
                "On est un peu débordés ! Repasse-nous un petit coucou bientôt 😊",
                "Grosse affluence aujourd'hui, on t'attend avec plaisir un peu plus tard !"
            ]
        },
        "session_limit": {
            "formal": [
                "Nous avons bien pris note de vos messages. Un conseiller reviendra vers vous très vite.",
                "Merci pour votre patience. Un opérateur humain va prendre le relais sous peu.",
                "Vos demandes sont enregistrées. Un membre de l'équipe vous répondra dans les meilleurs délais."
            ],
            "casual": [
                "C'est bien noté ! Un humain de l'équipe reprend la suite avec vous 👌",
                "Merci beaucoup, je passe le relais à un collègue qui revient vers vous vite !",
                "Bien reçu tout ça ! Quelqu'un de l'équipe finalise avec vous sous peu 😊"
            ]
        }
    }
    
    # Fallback si la catégorie n'existe pas
    if category not in registry:
        return f"[ERREUR SYSTEME: {category}]"
    
    # Récupération de la liste des variantes pour le ton donné
    options = registry[category].get(tone, registry[category]["formal"])
    
    # Sélection aléatoire
    message = random.choice(options)
    
    # Formatage final avec les arguments passés
    try:
        return message.format(**kwargs)
    except Exception as e:
        # En cas d'erreur de formatage (ex: variable manquante), retourner un message brut ou de secours
        return message.split("{")[0].strip()

# Détection automatique du ton (à intégrer dans le futur si possible)
def get_company_tone(company_id: Optional[str] = None) -> str:
    # Pour l'instant, défaut formal (Elite style)
    return "formal"
