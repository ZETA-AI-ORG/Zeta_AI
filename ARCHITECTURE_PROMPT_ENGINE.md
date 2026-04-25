# 🧠 Zeta Prompt Engine : Architecture & Flux de Données

Ce document détaille le fonctionnement du pipeline de génération de prompts pour le bot **Jessica** et **Amanda**. L'objectif est d'assurer une latence minimale, une fraîcheur des données absolue et une stabilité totale.

---

## 🏗️ 1. Les 3 Couches de Stockage

### A. La Source de Vérité (Supabase)
Toute modification "humaine" se fait ici.
- **Table** : `prompt_bots`
- **Contenu** : Les textes bruts pour **Jessica** (Ventes/RAG) et **Amanda** (Précommandes/Prise d'infos).
- **Rôle** : Persistance à long terme.

### B. Le Cache Haute Performance (Redis)
- **Clés** : `zeta:prompts:jessica` et `zeta:prompts:amanda`.
- **TTL (Time To Live)** : 24 heures.
- **Vitesse** : < 1ms.
- **Rôle** : Éviter les appels réseau vers Supabase à chaque message client.

### C. L'Index Produit Dynamique (Redis Hash)
- **Clé** : `zeta:product_index:{company_id}`
- **Structure** : Hash (clé: `product_id`, valeur: `index_line`).
- **Rôle** : (Jessica Uniquement) Stocker la liste des produits pour injection dynamique.

---

## 🔄 2. Le Cycle de Vie d'une Requête

1.  **Récupération du Prompt** : Interrogation Redis. Si Cache Miss, recharge depuis Supabase.
2.  **Assemblage** : Injection de l'index produit (pour Jessica) et des placeholders `{shop_name}`, etc.
3.  **Finalisation** : Envoi au LLM.

---

## ⚡ 3. Mécanisme de Mise à Jour (Invalidation Directe)

Pour garantir que Jessica ou Amanda changent de personnalité instantanément dès que tu modifies Supabase, sans dépendre de n8n :

### Configuration dans le Dashboard Supabase (Database -> Webhooks)
1.  **General** :
    - **Name** : `invalidate_prompt_cache`
    - **Table** : `public.prompt_bots`
    - **Events** : Cocher `INSERT`, `UPDATE`, `DELETE`.
2.  **Webhook Configuration** :
    - **Method** : `POST`
    - **URL** : `https://api.zetaapp.xyz/api/webhook/invalidate-prompt/{{record.bot_type}}`
    - **Timeout** : `5000 ms` (Patience de Supabase).
3.  **HTTP Headers** :
    - **Name** : `X-ZETA-AUTH`
    - **Value** : `zeta_diagnostic_default_secret`.

### 💡 Distinction Cruciale : Timeout vs TTL
- **Le Timeout (5000 ms)** : C'est le temps que Supabase accorde au serveur Python pour répondre "OK".
- **Le TTL (24 heures)** : Défini dans le code Python (`setex`). C'est la durée de vie du prompt dans Redis si aucune modification n'intervient.

---

## 🎭 4. Jessica vs Amanda : La Stratégie "Fission"

### 🔴 Jessica (The Sales Engine)
- **Injection Catalog** : Active.
- **Product Index** : Injecté depuis Redis.

### 🟣 Amanda (The Information Capture)
- **Injection Catalog** : **DÉSACTIVÉE**.
- **Product Index** : Ignoré (économie de tokens).

---

## 🛠️ 5. Maintenance & Debug

- **Vérifier le cache Redis** : `redis-cli get zeta:prompts:jessica`
- **Vérifier l'index produit** : `redis-cli hgetall zeta:product_index:{company_id}`
- **Tester l'invalidation** : `curl -X POST -H "X-ZETA-AUTH: zeta_diagnostic_default_secret" https://api.zetaapp.xyz/api/webhook/invalidate-prompt/jessica`
