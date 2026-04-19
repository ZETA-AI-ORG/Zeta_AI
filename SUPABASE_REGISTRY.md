# 🛡️ SUPABASE ARCHITECTURE REGISTRY - ZETA AI

Ce document constitue la référence unique et fidèle de l'architecture de données Supabase pour le projet Zeta AI.

## 1. Vue d'ensemble de l'Architecture
La base de données Supabase sert de cerveau persistant pour l'écosystème Zeta AI. Elle est structurée autour de 4 piliers majeurs :
1.  **Core Business** : Gestion des entreprises (`companies`) et de leurs accès (`subscriptions`).
2.  **RAG Engine (V2)** : Configuration technique de l'intelligence artificielle (`company_rag_configs`) et catalogues produits (`company_catalogs_v2`).
3.  **Conversation & Mémoire** : Logs de streaming (`conversation_logs`) et mémoire vectorielle à court terme (`conversation_memory`).
4.  **Opérations E-commerce** : Gestion des commandes (`orders`) et de la logistique (`order_deliveries`).

---

## 2. Liste Exhaustive des Tables (Scan du 18/04/2026)
Voici la liste brute de toutes les tables détectées dans le schéma `public`, classées par volume de données.

| Table | Lignes | Status |
| :--- | :--- | :--- |
| `conversation_memory` | 298 | Active |
| `shop_events` | 244 | Active |
| `order_deliveries` | 176 | Active |
| `orders` | 174 | Active |
| `operator_notifications` | 138 | Active |
| `push_subscriptions` | 83 | Active |
| `cart_sessions` | 50 | Active |
| `verification_codes` | 41 | Active |
| `required_interventions` | 38 | Active |
| `company_catalogs_v2` | 23 | Active |
| `shop_product_scores` | 14 | Active |
| `profiles` | 13 | Active |
| `shop_customers` | 12 | Active |
| `company_rag_configs` | 9 | Active |
| `companies` | 9 | Active |
| `merchant_balances` | 8 | Active |
| `incoming_signals` | 8 | Active |
| `reset_tokens` | 6 | Active |
| `shop_reviews` | 4 | Active |
| `conversation_notepad` | 4 | Active |
| `company_settings` | 4 | Active |
| `company_mapping` | 3 | Active |
| `balance_transactions` | 3 | Active |
| `subscriptions` | 3 | Active |
| `order_commissions` | 1 | Active |
| `conversation_logs` | 1 | Active |
| `routing_events` | 1 | Active |
| `activities` | 0 | Fantôme |
| `auto_generated_faqs` | 0 | Fantôme |
| `auto_improvements` | 0 | Fantôme |
| `bot_sessions` | 0 | Fantôme |
| `bot_usage` | 0 | Fantôme |
| `company_boosters` | 0 | Fantôme |
| `company_prompt_history` | 0 | Fantôme |
| `company_vector_store` | 0 | Fantôme |
| `conversations` | 0 | Fantôme |
| `delivery_companies` | 0 | Fantôme |
| `deployed_rules` | 0 | Fantôme |
| `deposits` | 0 | Fantôme |
| `document_intelligence` | 0 | Fantôme |
| `documents` | 0 | Fantôme |
| `documents_backup` | 0 | Fantôme |
| `documents_backup_384` | 0 | Fantôme |
| `human_labels` | 0 | Fantôme |
| `integrations` | 0 | Fantôme |
| `learned_patterns` | 0 | Fantôme |
| `llm_performance` | 0 | Fantôme |
| `messages` | 0 | Fantôme |
| `partner_invite_codes` | 0 | Fantôme |
| `payment_attempts` | 0 | Fantôme |
| `payment_verifications` | 0 | Fantôme |
| `product_images` | 0 | Fantôme |
| `product_reviews` | 0 | Fantôme |
| `prompt_logs` | 0 | Fantôme |
| `rule_candidates` | 0 | Fantôme |
| `shop_customers_metadata` | 0 | Fantôme |
| `thinking_analytics` | 0 | Fantôme |
| `whatsapp_otps` | 0 | Fantôme |

---

## 3. Dictionnaire des Données (Tables Actives)

Ci-dessous la liste des tables essentielles ayant une utilité prouvée (données présentes + appels code).

| Table | Rôle Humain | Champs Clés | Relations |
| :--- | :--- | :--- | :--- |
| `companies` | Entités clientes (Boutiques) | `id`, `name`, `industry` | PK de l'écosystème |
| `company_rag_configs` | **Cerveau Technique** | `company_id`, `prompt_botlive_*`, `meili_config` | Config du RAG |
| `subscriptions` | Droits d'accès et limites | `company_id`, `plan_type`, `status` | Lié à `companies` |
| `orders` | Commandes générées par l'IA | `total_amount`, `status`, `customer_phone` | Lié à `companies` |
| `conversation_memory` | Contexte immédiat de l'IA | `content`, `role`, `user_id` | Historique récent |
| `conversation_logs` | Journal complet des interactions | `channel`, `direction`, `content` | Audit & Dashboard |
| `company_catalogs_v2` | Catalogues produits synchronisés | `catalog` (JSON), `version` | RAG Input |
| `order_deliveries` | Suivi logistique | `status`, `driver_phone` | Lié à `orders` |

---

## 3. Diagnostic de Santé & "Liste Rouge" (Dead Code)

Ce diagnostic identifie les structures qui alourdissent la base de données sans valeur ajoutée actuelle.

### 🔴 Tables Fantômes (À supprimer - 0 ligne + 0 appel code)
Ces tables sont des résidus d'architectures abandonnées ou de boilerplates inutilisés :
*   `activities` : Ancienne tentative de log d'activité générale.
*   `bot_sessions` / `bot_usage` : Probablement remplacées par un monitoring externe.
*   `conversations` / `messages` : **Critique** - Ces tables standards sont vides car le système utilise désormais `conversation_memory` et `conversation_logs`.
*   `document_intelligence` : Reste d'une v1 du moteur de recherche.
*   `learned_patterns` : Module d'apprentissage automatique non activé.
*   `thinking_analytics` : Analyseurs de "chaîne de pensée" obsolètes.

### 🟡 Doublons et Redondances (À fusionner/nettoyer)
*   `documents` / `documents_backup` / `documents_backup_384` : Trois versions d'une même structure de stockage de chunks RAG. Seul le stockage via MeiliSearch semble actif pour la production.
*   `company_vector_store` : Doublon potentiel avec le système de chunks intégré.

### 🔵 Incohérences Structurelles
*   **Foreign Keys Manquantes** : Plusieurs tables comme `conversation_memory` ou `conversation_logs` utilisent des identifiants (strings) sans contrainte `FOREIGN KEY` forte vers `companies`, ce qui risque de créer des données orphelines.
*   **has_boost** : Cette colonne a été ajoutée dans `company_rag_configs` pour corriger un crash, mais sa place logique reste dans `subscriptions`.

---

**Note finale de l'Architecte** : L'audit montre une base de données "en transition". Un nettoyage des 31 tables vides permettrait de réduire la complexité cognitive de 50%.
