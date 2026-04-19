# 🧭 REGISTRE DU SYSTÈME PYTHON (ZETA AI)

Ce document cartographie l'architecture logicielle du backend Python et définit le rôle de chaque module pour la V2.0.

## 🏗️ Architecture Globale (Core)

| Module | Rôle | Statut |
| :--- | :--- | :--- |
| `botlive_prompts_supabase.py` | **Orchestrateur de Prompts**. Gère le chargement depuis Supabase, le cache et l'injection des variables boutique. | 🟢 Actif (V2) |
| `simplified_rag_engine.py` | **Moteur RAG Simplifié**. Gère le flux de discussion, l'extraction thinking/response et les outils (ex: Tarifs). | 🟢 Actif (Core) |
| `prompt_universel_v2.md` | **Mega-Prompt V2.0**. Définit les phases A/B/C et les règles de comportement universelles. | 🟢 Actif (V2) |
| `intelligent_fallback_system.py` | **Système de Repli**. Détecte les échecs de recherche ou de confiance et fournit des réponses de secours. | 🟡 Nécessite Dynamisation |
| `error_handler.py` | **Gestionnaire d'Erreurs**. Centralise les retours d'erreurs techniques (API, DB, Timeout). | 🟡 Nécessite Dynamisation |
| `botlive_engine.py` | **Moteur OCR/Vision**. Gère EasyOCR et BLIP-2 pour les preuves de paiement et produits. | 🟡 Partiellement Robotique |
| `botlive_prompts_hardcoded.py` | **Legacy Jessica**. Contient les anciens prompts V1. | 🔴 Obsolète (V1) |

## 🛠️ Outils et Intégrations

- **Outil 'Tarifs'** (`simplified_rag_engine.py`) : Génère dynamiquement la liste des prix formatée pour WhatsApp.
- **Système C (Prefix Caching)** : Optimisation Groq/DeepSeek via découpage en blocs statiques/dynamiques.
- **Thinking Parser** : Extraction de la balise `<thinking>` pour isoler le raisonnement du bot.

## 🔗 Liens avec la V2.0 et Supabase

- **Injection Boutique** : Le système extrait `shop_name`, `company_id`, et les configurations RAG depuis Supabase pour personnaliser la Phase C du prompt.
- **Filtres MeiliSearch** : Utilisés par le RAG pour limiter la recherche aux produits de l'entreprise active.
