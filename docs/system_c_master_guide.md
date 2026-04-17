# Guide Maître : Système C (Phase Loading & Optimization)

Ce document consigne la logique complète du Système C pour l'optimisation des prompts et des coûts de Zeta AI.

---

## ✅ État du Système
Le Système C est conçu pour segmenter le prompt universel et adapter les paramètres LLM en fonction de l'avancement de la vente.

### Fonctionnalités Clés :
1.  **Extraction Dynamique** : Les phases sont extraites de `prompt_universel_v2.md` via les balises `[[PHASE_X_START/END]]`.
2.  **Détection Automatique** : La phase (A, B ou C) est déterminée par `state.get_missing_fields()`.
3.  **Injection Conditionnelle** : Le `PHASE_MODULE` est injecté entre le BLOC 1 (Core) et le BLOC 2 (Identité/Catalogue).
4.  **Paramètres Adaptatifs** : `max_tokens` et `temperature` varient selon la phase pour maximiser la fiabilité et minimiser les coûts.
5.  **Override LLM** : Possibilité pour l'IA de forcer une phase via `<maj>next_phase:X</maj>`.
6.  **Kill-Switch** : Variable `PHASE_LOADING_ENABLED` pour désactiver le système instantanément.

---

## 🎚️ Configuration ENV VARS

### 1. Variables de Contrôle
| Variable | Défaut | Recommandation | Rôle |
| :--- | :--- | :--- | :--- |
| `PHASE_LOADING_ENABLED` | `true` | `true` | Activation globale du lazy-loading. |

### 2. Tuning des Phases
| Phase | Max Tokens | Température | Usage / Justification |
| :--- | :--- | :--- | :--- |
| **A (Recrutement)** | 800 | 0.5 | **Accueil & Qualification**. Besoin de créativité et de place pour présenter le catalogue. |
| **B (Coordination)** | 500 | 0.3 | **Logistique**. Rigueur sur les zones (Côte d'Ivoire) et formats de numéros. |
| **C (Closing)** | 350 | 0.1 | **Paiement Wave**. Quasi-déterministe pour éviter toute erreur de montant ou de numéro. |

---

## 📈 Impact Économique (Simulation)
Sur une session de 15 messages :
- **Avant Système C** : ~5 400 tokens output.
- **Après Système C** : ~3 510 tokens output.
- **Gain** : **~35% d'économie** sur les coûts de sortie (~1.14 USD / ~690 FCFA par client par mois).

---

## 🛠️ Maintenance & Rollback

### Modifier les paramètres sur le VPS :
```bash
ssh contabo -t "cd ~/CHATBOT2.0/app && nano .env"
# Appliquer les modifs puis :
ssh contabo "cd ~/CHATBOT2.0/app && docker compose restart zeta-backend"
```

### Rollback d'urgence :
Si un bug de segmentation est détecté, passer `PHASE_LOADING_ENABLED=false` dans le `.env`. Le système reviendra au prompt V2 monolithique sans nécessiter de modification de code.

---

## 💡 Recommandation de Production
**Ne rien mettre dans le `.env` par défaut.** Les valeurs codées en dur dans le `PhaseManager` (Python) sont déjà optimales. Utilisez les variables d'environnement uniquement pour l'ajustement fin (tuning) ou le débogage.
