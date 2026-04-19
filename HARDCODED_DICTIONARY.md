# 📖 DICTIONNAIRE DES RÉPONSES ET VARIANTES (CORE)

Ce dictionnaire recense les réponses robotiques identifiées et propose des variantes utilisant l'algorithme de randomisation Python pour humaniser la communication tout en garantissant la disponibilité hors-ligne (sécurité).

## 🛠️ Section A : Fallbacks et Erreurs (Humanisation)

### 1. Erreurs Techniques (`error_handler.py`)
**Déclencheur** : Timeout API, limite de requêtes (429), erreur serveur.

| Version Actuelle (Robotique) | Variantes Proposées (Random) |
| :--- | :--- |
| "Je rencontre des difficultés techniques..." | - "Je rencontre une petite difficulté technique, un instant s'il vous plaît." |
| | - "Notre système est un peu ralenti, merci de patienter..." |
| | - "Oups, une erreur réseau m'empêche d'accéder au catalogue, je réessaie." |

### 2. Fallbacks de Recherche (`intelligent_fallback_system.py`)
**Déclencheur** : Aucun document trouvé dans le RAG, faible score de confiance.

| Version Actuelle (Robotique) | Variantes Proposées (Random) |
| :--- | :--- |
| "Je n'ai pas trouvé d'informations..." | - "Je n'arrive pas à mettre la main sur l'info exacte, pouvez-vous me donner plus de détails ?" |
| | - "Désolé, ma recherche n'a rien donné pour l'instant. Pouvez-vous reformuler ?" |
| | - "Je sèche un peu sur cette question. Vous parlez bien d'un produit du catalogue ?" |

## 🛒 Section B : Processus de Commande (Dynamisation)

### 1. Confirmations OCR (`botlive_engine.py`)
**Déclencheur** : Après analyse de l'image du produit ou du reçu.

| Version Actuelle (Robotique) | Variantes Proposées (Random) |
| :--- | :--- |
| "🛒 Produit détecté: {name}" | - "C'est bien noté ! J'ai reconnu : {name}. ✅" |
| | - "Parfait, je vois que c'est le produit {name}. On continue ?" |
| "💳 Paiement: {amount} {currency}" | - "Reçu 5/5 ! J'ai validé votre paiement de {amount} {currency}. 🎉" |
| | - "Merci ! Le virement de {amount} {currency} est bien arrivé dans mon système." |

### 2. Liste de Tarifs (`simplified_rag_engine.py`)
**Déclencheur** : Quand le LLM appelle l'outil de catalogue de prix.

| Version Actuelle (Robotique) | Variantes Proposées (Random) |
| :--- | :--- |
| "Bien reçu 😊 Voici nos formats disponibles :" | - "Bien sûr ! Voici ce que nous avons en stock actuellement :" |
| | - "Voici nos tarifs et formats disponibles pour ce produit :" |
| "👉 Dites-moi simplement le numéro de votre choix." | - "Quel numéro vous tente le plus ? Dites-le moi simplement." |
| | - "Vous n'avez plus qu'à me donner le numéro qui vous convient. 😊" |

---

## 🚦 Logique de Mise en Œuvre (Phase 2)

Pour chaque module, nous isolerons les chaînes dans une classe `MessageRegistry` ou des fonctions d'aide :

```python
import random

def get_system_response(category: str, **kwargs) -> str:
    registry = {
        "error_tech": [
            "Difficulté technique passagère, je reviens...",
            "Système saturé, je réessaie dans un instant."
        ],
        "ocr_product": [
            "J'ai bien détecté le produit {name}.",
            "Reconnaissance réussie : {name}."
        ]
    }
    msg = random.choice(registry.get(category, ["Une erreur est survenue."]))
    return msg.format(**kwargs)
```
