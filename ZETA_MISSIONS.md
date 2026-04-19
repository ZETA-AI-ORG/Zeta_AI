# 🚀 MISSIONS D'OPTIMISATION ZETA AI (CORE PYTHON)

Ce document répertorie les 3 missions critiques pour l'humanisation du bot et l'optimisation des flux de tarifs, à exécuter strictement en Python (Niveau 1).

## 🛡️ RÈGLE D'OR
**Zéro appel LLM pour les fallbacks.** Les messages doivent rester en Python pour garantir le fonctionnement même en cas de panne des services externes (Supabase/Groq).

---

## MISSION 1 : Refonte de la fonction `get_system_response`
**Objectif** : Créer un moteur de randomisation supportant le ton (formal/casual).

### Spécifications techniques
- **Nouveau fichier** : `core/message_registry.py`.
- **Fonction** : `get_system_response(category: str, tone: str = "formal", **kwargs) -> str`.
- **Tâches** :
    1. Implémenter le dictionnaire avec des variantes 'formal' et 'casual'.
    2. Retourner un `random.choice()`.
    3. Remplacer les appels statiques dans :
        - `error_handler.py`
        - `intelligent_fallback_system.py`
        - `botlive_engine.py`

---

## MISSION 2 : Correction "Numéro Unique" & "Spinning" Tarifs
**Objectif** : Améliorer l'UX des listes de prix dans `simplified_rag_engine.py`.

### Cas A : Un seul produit (`len(items) == 1`)
- **Affichage** : Pas de liste numérotée.
- **Contexte LLM** : Injecter une balise invisible `[PRODUIT_UNIQUE_PROPOSÉ: {name}]` pour que l'IA sache de quoi on parle au tour suivant.

### Cas B : Plusieurs produits (`len(items) > 1`)
- **Affichage** : Liste numérotée sobre (utiliser `1.` au lieu de `1️⃣`).
- **Enrobage** : Utiliser `get_system_response()` pour l'introduction et la conclusion (Spinning).

---

## MISSION 3 : Nettoyage du Code Mort
**Objectif** : Alléger la base de code pour réduire les bugs potentiels.

### Actions
- Supprimer définitivement `core/botlive_prompts_hardcoded.py`.
- Vérifier et supprimer les imports orphelins liés à ce fichier dans toute l'application.

---

*Directives validées par l'utilisateur le 19/04/2026.*
