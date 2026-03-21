# CARTOGRAPHIE DU PIPELINE PYTHON — INJECTION PRIX & CATALOGUE DANS LE PROMPT

> **Version** : 1.0 — Juin 2025
> **Auteur** : Analyse automatique du code source backend
> **Objectif** : Documenter l'architecture complète du système Python qui injecte les données prix/catalogue dans le prompt du bot Jessica, identifier les modules, diagnostiquer les bugs connus (CATALOGUE_BLOCK vide, PRICE_GATE), et proposer des optimisations.

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble du pipeline](#1-vue-densemble-du-pipeline)
2. [Modules Python — Cartographie complète](#2-modules-python--cartographie-complète)
3. [Pipeline d'injection prix — Flux détaillé](#3-pipeline-dinjection-prix--flux-détaillé)
4. [PRICE_GATE — Pourquoi les prix sont bloqués](#4-price_gate--pourquoi-les-prix-sont-bloqués)
5. [CATALOGUE_BLOCK — Pourquoi il est vide](#5-catalogue_block--pourquoi-il-est-vide)
6. [Ce que le bot délègue à Python](#6-ce-que-le-bot-délègue-à-python)
7. [Ce que Python peut faire (capacités)](#7-ce-que-python-peut-faire-capacités)
8. [Points d'optimisation identifiés](#8-points-doptimisation-identifiés)
9. [Schéma d'architecture global](#9-schéma-darchitecture-global)
10. [Schéma exact attendu par le bot (`catalog_v2`)](#10-schéma-exact-attendu-par-le-bot-catalog_v2)
11. [Chaîne réelle d'écriture du catalogue avancé](#11-chaîne-réelle-décriture-du-catalogue-avancé)
12. [Dérivation fiable Catalogue AI → Catalogue Web](#12-dérivation-fiable-catalogue-ai--catalogue-web)
13. [Décision d'architecture à prendre : 1 page ou 2 pages](#13-décision-darchitecture-à-prendre--1-page-ou-2-pages)

---

## 1. Vue d'ensemble du pipeline

Le bot "Jessica" est un assistant WhatsApp de vente. Son intelligence repose sur **deux couches** :

| Couche | Rôle | Technologie |
|--------|------|-------------|
| **Python Backend** | Collecte les données, calcule les prix, construit le prompt, valide les verdicts | FastAPI + modules `core/` |
| **LLM (Gemini/DeepSeek)** | Génère la réponse WhatsApp naturelle à partir du prompt enrichi | Via OpenRouter |

**Principe clé** : Python pré-calcule TOUT (prix, frais, verdicts) et les injecte dans le prompt XML. Le LLM n'invente rien, il **recopie** les données fournies.

### Flux simplifié

```
Message WhatsApp client
    ↓
[routes/botlive.py] — Point d'entrée API
    ↓
[core/production_pipeline.py] — Routing intent + shadow logging
    ↓
[core/simplified_rag_engine.py] — ORCHESTRATEUR PRINCIPAL
    │
    ├── [1] PREMATCH : Détection produit/variant dans le message (regex + fuzzy)
    ├── [2] PRICE_LIST SHORT-CIRCUIT : Si intent=prix, renvoie liste sans LLM
    ├── [3] CONTEXT INJECTION : Zone, frais, historique, verdicts
    ├── [4] PRICE_GATE : Vérifie si SPECS sont collectés avant calcul prix
    ├── [5] PRICE_CALC : Calcule le prix via UniversalPriceCalculator
    ├── [6] CATALOGUE_REFERENCE : Construit le bloc catalogue pour le LLM
    ├── [7] PROACTIVE_HINTS : Injecte les montants à annoncer
    ├── [8] BUILD_PROMPT : Assemble prompt statique + dynamique
    ├── [9] LLM CALL : Envoie au modèle
    └── [10] POST-PROCESSING : Parse thinking/response, met à jour OrderState
    ↓
Réponse WhatsApp envoyée au client
```

---

## 2. Modules Python — Cartographie complète

### 2.1 Modules CRITIQUES (pipeline principal)

| Module | Fichier | Rôle |
|--------|---------|------|
| **SimplifiedRAGEngine** | `core/simplified_rag_engine.py` | Orchestrateur principal — gère tout le flux de A à Z |
| **SimplifiedPromptSystem** | `core/simplified_prompt_system.py` | Construction du prompt (statique + dynamique XML) |
| **UniversalPriceCalculator** | `core/price_calculator.py` | Calcul des prix depuis le catalogue v2 (vtree) |
| **DynamicContextInjector** | `core/dynamic_context_injector.py` | Collecte contexte dynamique (zone, frais, historique) |
| **OrderStateTracker** | `core/order_state_tracker.py` | Persistance SQLite des slots commande (produit, specs, zone, tel, paiement) |
| **CartManager** | `core/cart_manager.py` | Panier multi-produit Redis (TTL 72h) |
| **CatalogV2Loader** | `core/company_catalog_v2_loader.py` | Chargement catalogue depuis Supabase/local avec cache |
| **CatalogFormatter** | `core/catalog_formatter.py` | Formatage liste de prix WhatsApp (numérotée, avec emojis) |

### 2.2 Modules SUPPORT (enrichissement)

| Module | Fichier | Rôle |
|--------|---------|------|
| **PaymentValidator** | `core/payment_validator.py` | Validation cumulative des paiements (OCR + historique) |
| **DeliveryZoneExtractor** | `core/delivery_zone_extractor.py` | Extraction zone + frais de livraison |
| **CatalogV2ItemNormalizer** | `core/catalog_v2_item_normalizer.py` | Normalisation des items détectés par le LLM |
| **LLMResponseValidator** | `core/llm_response_validator.py` | Validation structurelle de la réponse LLM |
| **TimezoneHelper** | `core/timezone_helper.py` | Heure Côte d'Ivoire + logique "avant/après 13h" |

### 2.3 Modules ROUTING & INTENT

| Module | Fichier | Rôle |
|--------|---------|------|
| **ProductionPipeline** | `core/production_pipeline.py` | Pipeline de production avec routing intent + shadow Supabase |
| **SetfitIntentRouter** | `core/setfit_intent_router.py` | Classification d'intention (SetFit ML) |
| **BotliveRAGHybrid** | `core/botlive_rag_hybrid.py` | Système RAG hybride (ancien, Botlive) |
| **HydeSmartRouter** | `core/hyde_smart_router.py` | Routage HyDE (Hypothetical Document Embeddings) |
| **ModelRouter** | `core/model_router.py` | Sélection dynamique du modèle LLM |

### 2.4 Modules PROMPT & CONFIG

| Module | Fichier | Rôle |
|--------|---------|------|
| **BotlivePromptsSupabase** | `core/botlive_prompts_supabase.py` | Chargement prompt depuis Supabase |
| **BotlivePromptsHardcoded** | `core/botlive_prompts_hardcoded.py` | Prompt hardcodé (fallback) |
| **CompanyConfigManager** | `core/company_config_manager.py` | Configuration entreprise |
| **BusinessConfigManager** | `core/business_config_manager.py` | Config business |

### 2.5 Modules SECONDAIRES

| Module | Fichier | Rôle |
|--------|---------|------|
| **ActivitiesLogger** | `core/activities_logger.py` | Logging activités |
| **LoopBotliveEngine** | `core/loop_botlive_engine.py` | Détection boucles de réponse |
| **BotliveTools** | `core/botlive_tools.py` | Outils bot (calculatrice, notepad) |
| **SemanticCache** | `core/semantic_cache.py` | Cache sémantique des réponses |
| **CircuitBreaker** | `core/circuit_breaker.py` | Protection contre les pannes en cascade |

---

## 3. Pipeline d'injection prix — Flux détaillé

### Étape 1 : PREMATCH (détection produit)

**Fichier** : `simplified_rag_engine.py` lignes ~1000-1330

Avant même d'appeler le LLM, Python analyse le message client pour détecter :
- **product_id** : via 5 stratégies (A→E) de matching contre le catalogue
- **variant** : via fuzzy matching contre les clés vtree (ex: "Pression", "Culotte")

```
Stratégie A : Substring exact du product_name dans le message
Stratégie B : Token matching avec unicité (mots >= 4 chars)
Stratégie C : Variant-only + mono-product container
Stratégie D : Variant-only + multi-product (unique vtree match)
Stratégie E : Mono-product + variant dans vtree
```

**Résultat** : `active_product_id` et `active_product_label` persistés dans OrderState.

### Étape 2 : PRICE_LIST SHORT-CIRCUIT

**Fichier** : `simplified_rag_engine.py` lignes ~1329-1373

Si `_is_price_intent(query)` est True ET qu'un variant est détecté :
- Python génère directement la liste de prix via `catalog_formatter.format_price_list()`
- **Le LLM n'est PAS appelé** → réponse directe Python
- Le flag `awaiting_price_choice` est activé pour le prochain tour

### Étape 3 : COLLECTE CONTEXTE DYNAMIQUE

**Fichier** : `dynamic_context_injector.py`

```python
dynamic_context = await self.context_injector.collect_dynamic_context(
    query=query, user_id=user_id, company_id=company_id
)
```

Produit un dict avec :
- `detected_location` : zone extraite du message (regex)
- `shipping_fee` : frais de livraison calculés
- `delivery_time` : délai estimé
- `product_context` : contexte produit (verdicts, vision, catalogue)
- `conversation_history` : historique tronqué

### Étape 4 : PRICE_GATE (le verrou)

**Fichier** : `simplified_rag_engine.py` lignes 2893-2902

```python
_st_price_gate = order_tracker.get_state(user_id)
if not str(getattr(_st_price_gate, "produit_details", "") or "").strip():
    pre_llm_price_calc_allowed = False
    print("🛑 [PRICE_GATE] Prix bloqué: SPECS manquant (taille non collectée)")
```

**Logique** : Si `produit_details` (= taille/specs) est vide dans OrderState → **aucun calcul de prix n'est effectué**.

⚠️ **C'est ici que le bug se manifeste** : voir section 4.

### Étape 5 : CALCUL DE PRIX

**Fichier** : `price_calculator.py` → `build_price_calculation_block_from_detected_items()` ou `build_price_calculation_block_for_rue_du_grossiste()`

Deux chemins :

#### Chemin A : Cart-first (panier multi-items)
Si `detected_items` existe dans OrderState meta → calcul prix multi-items via `build_price_calculation_block_from_detected_items()`

#### Chemin B : Mono-produit (slots individuels)
Si pas de panier → calcul via `build_price_calculation_block_for_rue_du_grossiste()` avec :
- `produit` (slug produit)
- `specs` (taille)
- `quantite` (quantité)
- `zone` (zone livraison)
- `delivery_fee_fcfa` (frais)

**Sortie** : Bloc XML `<price_calculation>` avec `<status>OK</status>`, items, subtotal, delivery_fee, total, et `<ready_to_send>` (texte prêt à copier).

### Étape 6 : CATALOGUE_REFERENCE

**Fichier** : `simplified_rag_engine.py` lignes 2965-3075

Construit un bloc texte structuré :
```
CANONICAL_UNITS: lot_300 | paquet_50
FORMATS_DE_VENTE:
- type=lot | quantity=300 | unitLabel=Lot de 300 | enabled=true | canonical=lot_300
UNITS_PAR_PRODUIT:
- product=Pression | specs=T1 | units=lot_300
```

### Étape 7 : PROACTIVE_HINTS

**Fichier** : `simplified_rag_engine.py` lignes 3097-3168

Injecte des instructions XML directes au LLM :
- `<proactive_price>` : "Copie-colle ce récapitulatif tel quel : {ready_to_send}"
- `<proactive_delivery>` : "La livraison à {zone} coûte {fee} FCFA"
- `<proactive_price_already_shown>` : "NE RÉPÈTE PAS le récap prix"

### Étape 8 : BUILD_PROMPT

**Fichier** : `simplified_prompt_system.py` → `build_prompt()`

Assemble :
1. **Prompt statique** (Supabase / local file / hardcodé)
2. **PRODUCT_INDEX** injection dans `[[PRODUCT_INDEX]]`
3. **CATALOGUE_START/END** injection via `_inject_between_catalogue_markers()`
4. **Contexte dynamique XML** (DYNAMIC_TEMPLATE) avec :
   - `<catalogue_reference>` — formats de vente + unités
   - `<total_snapshot>` — dernier total calculé
   - `<status_slots>` — état de chaque slot (PRESENT/MISSING)
   - `<etat_collecte>` — checklist visuelle
   - `<livraison>` — zone + frais + délai
   - `<price_calculation>` — bloc prix calculé
   - `<verdicts_systeme>` — payment/phone/location verdicts
   - `<instruction_immediate>` — intention + must_ack + must_do
   - `<vision_gemini>` — résultat OCR image
   - `<catalogue_context>` — lignes catalogue
   - `<historique>` — conversation history
   - `<message_client>` — query + has_image
5. **Output schema** (force `<thinking>` + `<response>` + `<detected_items_json>`)

---

## 4. PRICE_GATE — Pourquoi les prix sont bloqués

### Diagnostic

Le PRICE_GATE bloque le calcul de prix quand `OrderState.produit_details` est vide.

**`produit_details`** = la taille/spec du produit (ex: "T3", "Taille 4").

### Scénario de blocage typique

```
Client: "C'est combien vos couches ?"
→ PREMATCH détecte le produit ("Couches bebe")
→ active_product_id = "prod_ml6dxg73"
→ MAIS produit_details = "" (pas de taille précisée)
→ PRICE_GATE bloque : "🛑 Prix bloqué: SPECS manquant"
→ price_calculation_block = "" (vide)
→ Le LLM n'a aucun prix à annoncer
```

### Cause racine

Le PRICE_GATE est **trop strict** pour les questions de type "liste de prix". Il a été conçu pour empêcher un prix erroné quand la taille n'est pas connue (car le prix dépend de la taille). Mais quand le client demande la grille tarifaire complète, le PRICE_GATE bloque inutilement.

### Contournement actuel

Le **short-circuit PRICE_LIST** (étape 2) contourne le PRICE_GATE en détectant les intents prix AVANT le calcul mono-produit. Si le short-circuit fonctionne (variant détecté + intent prix), la liste est envoyée sans passer par le PRICE_GATE.

### Quand ça ne marche pas

- Le variant n'est **pas détecté** (message trop vague : "vos prix ?")
- L'intent n'est **pas classé** comme prix (message ambigu)
- Le produit est multi-variant et aucun n'est sélectionné

---

## 5. CATALOGUE_BLOCK — Pourquoi il est vide

### Diagnostic

Le `<catalogue_context>` dans le prompt peut être vide pour plusieurs raisons :

### Cause 1 : `active_product_id` absent

Si PREMATCH n'a pas détecté de produit, `active_product_id` est vide → `_build_product_context_block()` retourne "" → CATALOGUE_START/END reste vide.

### Cause 2 : Catalogue v2 non chargé

Si `get_company_catalog_v2(company_id)` échoue (Supabase down, cache expiré, fichier local absent) → `catalog_v2 = None` → tout le pipeline catalogue est court-circuité.

**Bug historique** : La variable `debug_logs` n'était pas définie dans `get_company_catalog_v2()`, causant une exception silencieuse qui retournait `None`.

### Cause 3 : Multi-product sans sélection

Si le catalogue contient plusieurs produits (`products: [...]`) mais qu'aucun `active_product_id` n'est persisté, et que le message ne matche aucun produit → `mono = None` → catalogue vide.

### Cause 4 : `product_context` dans dynamic_context est vide

Si `collect_dynamic_context()` ne retourne rien dans `product_context`, les `catalogue_lines` sont vides → `<catalogue_context>` contient `<line>∅</line>`.

---

## 6. Ce que le bot délègue à Python

| Responsabilité | Délégation | Détail |
|---------------|------------|--------|
| **Détection produit** | Python (PREMATCH) | 5 stratégies regex + fuzzy avant LLM |
| **Calcul de prix** | Python (UniversalPriceCalculator) | Prix exact depuis vtree catalogue |
| **Frais de livraison** | Python (DeliveryZoneExtractor) | Regex zones + table frais |
| **Validation paiement** | Python (PaymentValidator) | OCR + accumulation + verdict |
| **Persistance slots** | Python (OrderStateTracker) | SQLite : produit, specs, zone, tel, paiement |
| **Panier multi-produit** | Python (CartManager) | Redis avec actions ADD/REPLACE/DELETE |
| **Formatage liste prix** | Python (CatalogFormatter) | Liste numérotée WhatsApp |
| **Détection intention** | Python (SetfitIntentRouter) | Classification ML SetFit |
| **Historique conversation** | Python (DynamicContextInjector) | Tronquage + injection |
| **Vision OCR** | Python → Gemini Vision | Analyse images (captures paiement) |
| **Anti-hallucination** | Python (proactive_hints) | Force le LLM à recopier les montants |

**Ce que le LLM fait seul** :
- Génère le message WhatsApp naturel (ton, style, emojis)
- Détecte les infos implicites (dans `<detection>` du thinking)
- Reformule les questions de relance
- Gère les conversations sociales/off-topic

---

## 7. Ce que Python peut faire (capacités)

### Capacités ACTIVES (en production)

- ✅ Calcul prix mono-produit et multi-items
- ✅ Frais de livraison par zone (50+ zones CI)
- ✅ Validation paiement par OCR + cumul
- ✅ Short-circuit prix (réponse sans LLM)
- ✅ Panier multi-produit avec pivot A/B
- ✅ Détection variant/spec/unit dans le message
- ✅ Cache sémantique des réponses
- ✅ Shadow logging Supabase
- ✅ Circuit breaker (protection pannes)

### Capacités PARTIELLES (code présent mais pas toujours actif)

- ⚠️ Chargement catalogue dynamique par company_id
- ⚠️ Multi-product container (sélection automatique)
- ⚠️ Fallback prix hardcodé (Rue du Gros uniquement)

### Capacités ABSENTES (à développer)

- ❌ Gestion de stock temps réel
- ❌ Calcul promo/remise automatique
- ❌ Notifications de suivi commande
- ❌ Gestion retours/SAV automatique

---

## 8. Points d'optimisation identifiés

### 🔴 CRITIQUE — PRICE_GATE trop restrictif

**Problème** : PRICE_GATE bloque les prix quand `produit_details` est vide, même pour les demandes de grille tarifaire.

**Solution proposée** : Ajouter une exception pour les intents `ASK_PRICE` / `ASK_PRODUCT_INFO` → si le client demande "vos prix", envoyer la grille complète même sans spec.

```python
# AVANT (actuel)
if not str(getattr(_st_price_gate, "produit_details", "") or "").strip():
    pre_llm_price_calc_allowed = False

# APRÈS (proposé)
if not str(getattr(_st_price_gate, "produit_details", "") or "").strip():
    if not _is_price_intent(query):  # Seulement bloquer si pas un intent prix
        pre_llm_price_calc_allowed = False
    else:
        # Intent prix → laisser passer pour grille tarifaire
        print("⚡ [PRICE_GATE] Bypass: intent prix détecté sans specs → grille tarifaire")
```

### 🔴 CRITIQUE — CATALOGUE_BLOCK vide au 1er tour

**Problème** : Au premier message, `active_product_id` n'est pas encore persisté → CATALOGUE_START/END vide → le LLM n'a pas de contexte catalogue.

**Solution proposée** : Dans `build_prompt()`, si aucun produit n'est sélectionné, injecter un **PRODUCT_INDEX** avec tous les produits disponibles pour guider le LLM.

### 🟡 MOYEN — Double calcul prix

**Problème** : Le prix est parfois calculé 2 fois (short-circuit + price_calc), ce qui gaspille du CPU.

**Solution** : Si short-circuit a déjà répondu, skip le price_calc dans le flux principal.

### 🟡 MOYEN — Fallback prix hardcodé

**Problème** : Les prix Rue du Gros sont hardcodés dans `price_calculator.py` comme fallback. Si le catalogue v2 change, le fallback est obsolète.

**Solution** : Supprimer le fallback hardcodé et s'appuyer uniquement sur le catalogue v2 dynamique.

### 🟢 MINEUR — Taille du prompt

**Problème** : Le prompt final peut atteindre 10-15K tokens avec tous les blocs XML, ce qui augmente le coût et la latence.

**Solution** : Compresser les blocs vides (ne pas injecter `<empty>∅</empty>`) et tronquer l'historique plus agressivement.

---

## 9. Schéma d'architecture global

```
┌─────────────────────────────────────────────────────────────────┐
│                     MESSAGE WHATSAPP CLIENT                      │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  routes/botlive.py                                               │
│  Point d'entrée API → valide le message → route vers le pipeline │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  core/production_pipeline.py                                     │
│  Intent routing (SetFit) → Shadow logging (Supabase)             │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌═════════════════════════════════════════════════════════════════┐
║  core/simplified_rag_engine.py  (ORCHESTRATEUR PRINCIPAL)       ║
║                                                                  ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  ║
║  │  PREMATCH     │  │  PRICE LIST  │  │  CONTEXT INJECTION   │  ║
║  │  Détection    │→ │  Short-circuit│→ │  Zone/Frais/History  │  ║
║  │  Produit/Var  │  │  (sans LLM)  │  │                      │  ║
║  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  ║
║         │                 │                      │               ║
║         ▼                 ▼                      ▼               ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │                    PRICE_GATE                             │   ║
║  │  Si SPECS manquant → bloque le calcul prix               │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             ▼                                    ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  ║
║  │  PRICE_CALC   │  │  CATALOGUE   │  │  PROACTIVE_HINTS    │  ║
║  │  Calculator   │  │  REFERENCE   │  │  Force LLM à citer  │  ║
║  │  → XML block  │  │  → units/fmt │  │  les montants       │  ║
║  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  ║
║         │                 │                      │               ║
║         ▼                 ▼                      ▼               ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │              BUILD_PROMPT (assemblage final)              │   ║
║  │  Statique (Supabase) + Dynamique (XML) + Output Schema   │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             ▼                                    ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │                      LLM CALL                             │   ║
║  │  Gemini / DeepSeek via OpenRouter                         │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             ▼                                    ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │                  POST-PROCESSING                          │   ║
║  │  Parse <thinking>/<response>                              │   ║
║  │  Extrait <detected_items_json>                            │   ║
║  │  Met à jour OrderState + CartManager                      │   ║
║  └──────────────────────────────────────────────────────────┘   ║
╚═════════════════════════════════════════════════════════════════╝
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Réponse WhatsApp envoyée au client via n8n / API directe        │
└─────────────────────────────────────────────────────────────────┘

┌─ MODULES DE SUPPORT ─────────────────────────────────────────────┐
│                                                                   │
│  OrderStateTracker (SQLite)  ←→  Persistance slots commande      │
│  CartManager (Redis)         ←→  Panier multi-produit             │
│  PaymentValidator            ←→  Validation paiement OCR          │
│  CatalogV2Loader             ←→  Catalogue depuis Supabase/local  │
│  CatalogFormatter            ←→  Formatage listes prix WhatsApp   │
│  DeliveryZoneExtractor       ←→  Zones + frais livraison          │
│  TimezoneHelper              ←→  Heure CI + délais                │
│  SemanticCache               ←→  Cache réponses similaires        │
│  LoopEngine                  ←→  Détection boucles réponse        │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Annexe : Structure du prompt XML injecté

```xml
<dynamic_input>
  <catalogue_reference>
    CANONICAL_UNITS: lot_300 | paquet_50
    FORMATS_DE_VENTE: ...
    UNITS_PAR_PRODUIT: ...
  </catalogue_reference>

  <total_snapshot>
    <total_fcfa>24400</total_fcfa>
    <product_subtotal_fcfa>22900</product_subtotal_fcfa>
    <delivery_fee_fcfa>1500</delivery_fee_fcfa>
    <zone>Cocody</zone>
  </total_snapshot>

  <status_slots>
    <PRODUIT status="PRESENT">prod_ml6dxg73</PRODUIT>
    <SPECS status="PRESENT">T3</SPECS>
    <QUANTITÉ status="PRESENT">1 lot</QUANTITÉ>
    <ZONE status="PRESENT">Cocody</ZONE>
    <TÉLÉPHONE status="MISSING"></TÉLÉPHONE>
    <PAIEMENT status="MISSING"></PAIEMENT>
  </status_slots>

  <price_calculation>
    <status>OK</status>
    <mode>MULTI_ITEMS</mode>
    <item>
      <product>PRESSION</product>
      <size>T3</size>
      <unit>lot_300</unit>
      <qty_lots>1</qty_lots>
      <unit_price_fcfa>22900</unit_price_fcfa>
      <subtotal_fcfa>22900</subtotal_fcfa>
    </item>
    <total_fcfa>24400</total_fcfa>
    <ready_to_send>Votre panier :
- PRESSION T3 x1 lot de 300 → 22 900F
Total : 24 400F (produits 22 900F + livraison 1 500F)</ready_to_send>
  </price_calculation>

  <instruction_immediate>
    <proactive_price>
      Python a calculé le prix. Tu DOIS annoncer ce montant...
    </proactive_price>
  </instruction_immediate>

  <message_client>
    <texte>Je veux 1 lot de pressions taille 3</texte>
    <has_image>NON</has_image>
  </message_client>
</dynamic_input>
```

---

## 10. Schéma exact attendu par le bot (`catalog_v2`)

### 10.1 Vérité terrain observée sur le VPS

Le fichier retrouvé sur le VPS pour la company `W27PwOPiblP8TlOrhPcjOtxd0cza` est :

```text
/home/zetaadmin/CHATBOT2.0/app/data/catalogs/W27PwOPiblP8TlOrhPcjOtxd0cza.json
```

Le produit inspecté est :

```text
product_id = prod_ml6dxg73_a0rloi
product_name = Couches bébés ( 0-25kg ) ⭐️⭐️⭐️
```

La structure réellement consommée par le bot n'est **pas** une simple fiche e-commerce (`name`, `price`, `promoPrice`, `imageUrls`).
Le backend attend un **catalogue métier bot-compatible** :

```json
{
  "product_id": "prod_ml6dxg73_a0rloi",
  "product_name": "Couches bébés ( 0-25kg ) ⭐️⭐️⭐️",
  "category": "Bébé & Puériculture",
  "subcategory": "Soins Bébé - Couches",
  "description": "...",
  "technical_specs": "...",
  "sales_constraints": "...",
  "images": ["..."],
  "canonical_units": ["lot_200", "lot_300", "lot_100"],
  "pricing_strategy": "UNIT_AS_ATOMIC",
  "v": {
    "Culotte": {
      "s": {
        "T5": {
          "u": {
            "lot_200": [16900, 500],
            "lot_300": [24000, 500],
            "lot_100": [9500, 500]
          }
        }
      }
    },
    "Pression": {
      "s": {
        "T5": {
          "u": {
            "lot_300": [24000, 500]
          }
        }
      }
    }
  },
  "ui_state": {
    "variants": ["Culotte", "Pression"],
    "subVariantsByIndex": [["T3", "T4", "T5", "T6"], ["T1", "T2", "T3", "T4", "T5", "T6"]],
    "customFormats": [
      {"type": "lot", "quantity": "200", "enabled": true, "unitLabel": "pièces"},
      {"type": "lot", "quantity": "300", "enabled": true, "unitLabel": "pièces"},
      {"type": "lot", "quantity": "100", "enabled": true, "unitLabel": "pièces"}
    ],
    "priceMatrix": {
      "Culotte T5_lot_100": "9500",
      "Culotte T5_lot_200": "16900",
      "Culotte T5_lot_300": "24000",
      "Pression T5_lot_300": "24000"
    }
  }
}
```

### 10.2 Signification métier des champs

| Champ | Rôle | Utilisé par |
|------|------|-------------|
| `product_id` | Identifiant stable du produit | Sélection mono-produit, logs, matching |
| `product_name` | Libellé humain | Prompt, index, affichage |
| `technical_specs` | Règles de lecture métier (poids → taille, contenu, jargon) | Normalisation, clarification, prompt |
| `sales_constraints` | Contraintes fortes de vente | Prompt, garde-fous LLM |
| `canonical_units` | Unités normalisées (`lot_100`, `lot_300`, etc.) | Calcul prix, catalogue reference |
| `pricing_strategy` | Stratégie de calcul | `UniversalPriceCalculator`, short-circuit prix |
| `v` | **Source de vérité des prix** (variant → spec → unit → prix) | Calcul prix, price list, prompt |
| `ui_state` | Mémoire de l'éditeur frontend | Reconstruction UI, formats, matrice visuelle |

### 10.3 Le vrai cœur du système : `v`

Le champ `v` est la matrice exploitable par Python.

Lecture :

```text
v = variantes
s = specs / tailles / sous-variantes
u = unités / formats de vente
[16900, 500] = prix principal + méta annexe (historique : frais/unité interne)
```

Exemple concret :

```text
variant = Culotte
spec = T5
unit = lot_200
prix = 16900
```

Donc, pour le bot, la fiche produit publique ne suffit jamais. Il faut une matrice exploitable par triplet :

```text
variant + spec + unit -> price
```

### 10.4 Rôle de `ui_state`

`ui_state` n'est pas décoratif. Il sert à mémoriser l'état de l'éditeur avancé :

- `variants`
- `subVariantsByIndex`
- `customFormats`
- `priceMatrix`
- `stockMatrix`
- `variantImagesByIndex`

Conclusion importante :

- `v` = structure **runtime bot**
- `ui_state` = structure **édition/reconstruction frontend**

La page Catalogue avancé doit donc être pensée comme un **builder de `catalog_v2`**, pas comme une simple page “produit public”.

---

## 11. Chaîne réelle d'écriture du catalogue avancé

### 11.1 Ce que le code montre réellement

Le backend trouvé dans `routes/catalog_v2.py` **ne construit pas** lui-même la logique métier complète du catalogue avancé.
Il reçoit un `catalog` déjà structuré, puis fait 4 choses :

1. **Ancre / stabilise** le `product_id`
2. **Enveloppe** le tout dans un container multi-produits
3. **Écrit localement** dans `data/catalogs/{company_id}.json`
4. **Upsert** dans Supabase `company_catalogs_v2`

### 11.2 Contrat d'entrée backend

Les endpoints montrent que le backend attend déjà un objet complet :

```python
class CatalogV2UpsertRequest(BaseModel):
    company_id: str
    catalog: Dict[str, Any]
```

et :

```python
class CatalogV2SyncLocalRequest(BaseModel):
    company_id: str
    catalog: Dict[str, Any]
    product_id: Optional[str] = None
```

Donc la fabrication du `catalog_v2` se fait **en amont** :

- soit dans la page Catalogue avancé ZetaFlow,
- soit dans un pipeline intermédiaire (n8n / service de transformation),
- soit dans une combinaison des deux.

### 11.3 Ce que fait `_write_local_catalog()`

`routes/catalog_v2.py` → `_write_local_catalog()` :

- valide `product_name`
- calcule/force un `product_id` stable si absent
- relit le container local existant
- convertit un ancien mono-produit en container multi-produits si besoin
- upsert le produit dans :

```json
{
  "company_id": "...",
  "version": 12,
  "updated_at": "...",
  "catalog": {
    "products": [
      {
        "product_id": "prod_ml6dxg73_a0rloi",
        "product_name": "...",
        "catalog_v2": { ... },
        "updated_at": "...",
        "version": 12
      }
    ]
  },
  "synced_at": 1234567890.0
}
```

### 11.4 Ce que fait l'upsert Supabase

`POST /catalog-v2/upsert` :

- écrit dans `company_catalogs_v2`
- `catalog = payload.catalog`
- `is_active = true`
- `version` incrémentée

### 11.5 Ce que charge ensuite Python

`core/company_catalog_v2_loader.py` lit :

```python
client.table("company_catalogs_v2")
  .select("catalog")
  .eq("company_id", cid)
  .eq("is_active", True)
  .order("updated_at", desc=True)
  .limit(1)
```

avec fallback local sur :

```text
data/catalogs/{company_id}.json
```

### 11.6 Conclusion pipeline d'écriture

La chaîne réelle est donc :

```text
Page Catalogue avancé / pipeline amont
    ↓
objet catalog_v2 complet
    ↓
routes/catalog_v2.py
    ├── ancre product_id
    ├── écrit cache local VPS
    └── upsert company_catalogs_v2
    ↓
core/company_catalog_v2_loader.py
    ↓
simplified_rag_engine.py / price_calculator.py / prompt_system.py
```

Donc si la page ZetaFlow “fusionnée” ne reconstruit plus correctement `v`, `ui_state`, `customFormats`, `canonical_units`, alors le bot n'a plus de base fiable.

---

## 12. Dérivation fiable Catalogue AI → Catalogue Web

### 12.1 Besoin produit

Un marchand qui utilise le bot ne doit **pas** remplir deux fois le même produit.

La règle métier souhaitable est donc :

```text
Catalogue AI (avancé) = source maîtresse
Catalogue Web (public) = projection dérivée automatique
```

L'inverse n'est pas obligatoire, car un utilisateur “mode lite” peut ne jamais utiliser le bot.

### 12.2 Ce qu'on peut déduire de manière parfaitement fiable

À partir du `catalog_v2`, on peut dériver sans ambiguïté les champs publics suivants :

| Champ public | Dérivable ? | Source |
|-------------|-------------|--------|
| `id` | Oui | `product_id` |
| `name` | Oui | `product_name` |
| `description` | Oui | `description` |
| `category` | Oui | `category` |
| `subcategory` | Oui | `subcategory` |
| `imageUrls` | Oui | `images` |
| `available` | Oui (par règle) | `stock` / absence d'override = true |
| `price` | Oui, si on définit une règle de projection | `v` / `priceMatrix` |
| `promoPrice` | Non, sauf champ dédié | absent du schéma bot actuel |
| `emoji` | Non, sauf champ dédié | absent du schéma bot actuel |

### 12.3 Règle de projection recommandée pour le prix public

Le catalogue web ne sait pas afficher une matrice complète variant/spec/unit comme le bot.
Il faut donc définir une **règle explicite et déterministe**.

Règle recommandée :

1. Chercher un champ futur `public_display` si présent
2. Sinon, choisir le **prix public minimal vendable** du produit
3. Sinon, choisir le format le plus mis en avant dans `customFormats`
4. Sinon, ne pas afficher de prix unique et afficher “Prix selon format”

Exemple de projection possible :

```json
{
  "id": "prod_ml6dxg73_a0rloi",
  "name": "Couches bébés ( 0-25kg ) ⭐️⭐️⭐️",
  "description": "Couches bébé absorbantes et confortables...",
  "category": "Bébé & Puériculture",
  "imageUrls": ["https://...jpeg"],
  "available": true,
  "price": 9500,
  "priceSource": "MIN_SELLABLE_UNIT",
  "publicVariantsSummary": "Culotte: lots 100/200/300, Pression: lot 300"
}
```

### 12.4 Champs à ajouter pour fiabiliser la projection publique

Si on veut une projection **parfaitement fiable** sans heuristique, il faut ajouter dans le schéma avancé des champs dédiés au web :

```json
{
  "public_display": {
    "enabled": true,
    "title": "Couches bébés (0-25kg)",
    "short_description": "Disponible en Culotte et Pression",
    "cover_image": "https://...",
    "display_price_mode": "FROM_PRICE",
    "display_price_value": 9500,
    "display_badge": "⭐️⭐️⭐️",
    "available": true
  }
}
```

Avec cette approche :

- le marchand remplit **une seule fois**
- le bot garde sa matrice riche
- le web reçoit une projection explicite sans ambiguïté

### 12.5 Règle d'architecture recommandée

La direction recommandée est :

```text
Catalogue AI = master
Catalogue Web = vue dérivée
```

et non l'inverse.

---

## 13. Décision d'architecture à prendre : 1 page ou 2 pages

### Option 1 — Une seule page fusionnée

Principe :

- une page unique “Catalogue”
- section publique simple
- section avancée bot
- sauvegarde dans un seul schéma enrichi
- projection automatique vers le catalogue public

#### Avantages

- une seule saisie
- cohérence maximale entre bot et web
- moins de risque de divergence produit

#### Inconvénients

- UI plus complexe
- risque de confusion pour les marchands lite
- plus difficile à maintenir si les usages web et bot divergent fortement

### Option 2 — Deux pages distinctes

Principe :

- `Catalogue Web`
- `Catalogue AI`

avec règle de dérivation automatique :

```text
si produit AI existe et bot activé -> projection automatique vers Web
sinon produit Web seul autorisé
```

#### Avantages

- séparation mentale claire
- UI plus simple pour chaque usage
- évite de polluer le web avec les champs métier bot

#### Inconvénients

- nécessite une synchronisation stricte
- risque de confusion si la projection est mal visible

### Option 3 — Recommandation pratique

La meilleure option fonctionnelle semble être :

#### Recommandation

- **2 pages distinctes en interface**
- **1 seule source de vérité pour les produits bot**
- **projection automatique AI → Web**

En pratique :

```text
Catalogue AI (avancé) = produit maître
Catalogue Web = vue simplifiée dérivée automatiquement
Mode lite = peut continuer à créer seulement des produits Web
Mode bot = remplit seulement Catalogue AI, sans double saisie
```

Cette option répond aux 2 contraintes :

- pas de double remplissage pour les marchands bot
- pas de complexité inutile pour les marchands lite

### 13.1 Décision cible recommandée

Décision recommandée à ce stade :

1. Revenir à une séparation **visuelle** en 2 pages :
   - `Catalogue Web`
   - `Catalogue AI`
2. Définir le `catalog_v2` comme **source maîtresse** pour le bot
3. Ajouter une couche de projection explicite `AI -> Web`
4. Ajouter, si besoin, un bloc `public_display` dans le schéma avancé pour supprimer toute ambiguïté de projection

### 13.2 Ce qu'il faut éviter

- reconstruire le bot à partir d'une fiche web simple
- forcer une double saisie complète du même produit
- faire dépendre la projection publique d'heuristiques implicites non traçables
- mélanger dans une seule UI non structurée les champs web et les champs bot sans séparation claire

---

## Synthèse finale

Les découvertes sur le VPS permettent désormais d'affirmer que :

1. Le bot attend un **`catalog_v2` riche**, pas un simple produit web
2. La matrice `v` est la **source de vérité des prix**
3. `ui_state` est la **mémoire de l'éditeur avancé**
4. `routes/catalog_v2.py` est une **couche d'écriture/persistance**, pas la logique métier de construction
5. Pour éviter la double saisie, il faut faire de **Catalogue AI la source maîtresse**, puis projeter automatiquement vers **Catalogue Web**
6. La meilleure architecture produit semble être : **2 pages distinctes en interface, 1 pipeline maître avancé derrière**
