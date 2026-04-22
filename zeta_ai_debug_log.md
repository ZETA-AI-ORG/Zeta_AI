# ZETA AI — SPÉCIFICATION LOGS DEBUG SERVEUR
> Chaque log est positionné exactement dans le code.
> Python est l'orchestrateur — tous les points critiques sont tracés.
> Le LLM est une boîte noire surveillée en entrée et sortie uniquement.

---

## PHILOSOPHIE DES LOGS

```
PYTHON = orchestrateur → log TOUT (chaque décision, chaque calcul)
LLM    = boîte noire   → log entrée (tokens/chars) + sortie (response + thinking)
ERREUR = toujours log complet avec contexte (jamais juste le message)
TIMING = chaque phase chronométrée individuellement
```

**Niveaux :**
- `DEBUG`   → flux normal détaillé (désactivable en prod stable)
- `INFO`    → événements métier importants (toujours actif)
- `WARNING` → dégradation non bloquante (fallback utilisé, cache miss, etc.)
- `ERROR`   → échec avec contexte complet (jamais silencieux)

---

## FORMAT STANDARD

```python
import logging
import json
import time

logger = logging.getLogger("zeta")

# Format structuré JSON pour parsing facile
def zlog(level: str, phase: str, event: str, **kwargs):
    payload = {
        "phase": phase,
        "event": event,
        **kwargs
    }
    getattr(logger, level)(f"[{phase}] {event} | " +
                           json.dumps(payload, ensure_ascii=False, default=str))
```

---

## 1. AMANDA BOTLIVE — LOGS PAR ÉTAPE

### app.py — Endpoint /amandabotlive

```python
# ── RÉCEPTION ──────────────────────────────────────────────────────
# Ligne ~3994 — début fonction amanda_botlive_endpoint()
zlog("info", "AMANDA_IN", "requête reçue",
     request_id=request_id,
     company_id=req.company_id,
     user_id=req.user_id,
     message_len=len(req.message or ""),
     has_images=bool(req.images))

# ── GUARDIAN ────────────────────────────────────────────────────────
# Ligne ~4000 — après appel guardian.check_access()
zlog("info", "GUARDIAN", "verdict",
     company_id=req.company_id,
     allowed=verdict.allowed,
     reason=verdict.reason,
     plan=verdict.plan,
     elapsed_ms=round((time.time() - t0) * 1000, 2))

# Si bloqué :
zlog("warning", "GUARDIAN", "accès refusé — short-circuit",
     company_id=req.company_id,
     reason=verdict.reason,
     message_humanisee=response_text[:80])

# ── CHARGEMENT PROMPT ───────────────────────────────────────────────
# Ligne ~4026 — avant load_amanda_prompt()
t_prompt = time.time()

# Après chargement réussi :
zlog("info", "PROMPT_LOAD", "prompt chargé",
     company_id=req.company_id,
     source=_prompt_source,          # "redis" | "supabase" | "local_fallback"
     prompt_chars=len(system_prompt),
     static_chars=len(static_part),  # partie avant les variables dynamiques
     dynamic_chars=len(dynamic_part),
     elapsed_ms=round((time.time() - t_prompt) * 1000, 2))

# Si fallback local déclenché :
zlog("warning", "PROMPT_LOAD", "fallback local utilisé",
     company_id=req.company_id,
     original_error=str(e)[:200])

# Si get_company_info retourne string (bug plan_type) :
zlog("error", "PROMPT_LOAD", "company_info invalide — guard déclenché",
     company_id=req.company_id,
     info_type=type(info).__name__,
     info_preview=str(info)[:100])

# ── SUPABASE SUBSCRIPTIONS ──────────────────────────────────────────
# Ligne ~botlive_prompts_supabase.py get_company_info()
zlog("info", "SUBSCRIPTIONS", "plan résolu",
     company_id=company_id,
     plan_name=plan_name,
     has_boost=has_boost,
     status=sub_status,
     elapsed_ms=elapsed)

# Si erreur colonne :
zlog("error", "SUBSCRIPTIONS", "erreur SQL — vérifier nom colonne",
     company_id=company_id,
     sql_error=str(e)[:300],
     hint="plan_name PAS plan_type")

# ── HISTORIQUE ──────────────────────────────────────────────────────
# Ligne ~4066
zlog("debug", "HISTORY", "historique chargé",
     company_id=req.company_id,
     user_id=req.user_id,
     chars=len(conversation_history),
     truncated=len(conversation_history) >= 2000,
     elapsed_ms=round((time.time() - t_hist) * 1000, 2))

# ── VISION OCR ──────────────────────────────────────────────────────
# Ligne ~4079 — si image présente
zlog("info", "VISION_OCR", "analyse image",
     company_id=req.company_id,
     image_url=req.images[0][:80],
     ocr_type="produit",            # "produit" | "paiement"
     model=MODEL_VISION_OCR,
     elapsed_ms=round((time.time() - t_vision) * 1000, 2))

zlog("debug", "VISION_OCR", "résultat",
     ocr_chars=len(vision_ocr),
     preview=vision_ocr[:100])

# ── RÉSOLUTION MODÈLE ───────────────────────────────────────────────
# Ligne ~4115 — après get_amanda_config()
zlog("info", "MODEL_RESOLVE", "modèle Amanda résolu",
     company_id=req.company_id,
     plan=plan_name,
     has_boost=has_boost,
     model=model_name,
     boost_ignored=True,            # Amanda : boost toujours ignoré
     params=llm_params)

# Si garde-fou déclenché :
zlog("warning", "MODEL_GUARD", "modèle refusé — fallback",
     requested=requested_model,
     fallback=fallback_model,
     context="amandabotlive")

# ── APPEL LLM ───────────────────────────────────────────────────────
# Ligne ~4156 — avant llm_client.complete()
zlog("info", "LLM_CALL", "envoi au LLM",
     model=model_name,
     prompt_chars=len(full_prompt),
     estimated_tokens=len(full_prompt) // 4,   # estimation rapide
     temperature=llm_params["temperature"],
     max_tokens=llm_params["max_tokens"])

# Après réponse LLM :
zlog("info", "LLM_RESPONSE", "réponse reçue",
     model=model_name,
     prompt_tokens=prompt_tokens,
     completion_tokens=completion_tokens,
     cached_tokens=cached_tokens,
     cache_hit_rate=round(cached_tokens / max(prompt_tokens, 1) * 100, 1),
     cost_usd=cost_total,
     elapsed_ms=round((time.time() - t_llm) * 1000, 2))

# ── PARSING XML ─────────────────────────────────────────────────────
# Ligne ~4193
zlog("debug", "XML_PARSE", "parsing thinking",
     thinking_chars=len(thinking_raw),
     has_detection=bool(detection_slots.get("resume")),
     has_handoff=handoff_requested,
     priority=priority,
     slots=detection_slots)

# Si XML malformé :
zlog("warning", "XML_PARSE", "XML malformé — fuzzy parser utilisé",
     raw_preview=raw_response[:200],
     recovered=bool(response_text))

# Si parsing total échoue :
zlog("error", "XML_PARSE", "parsing impossible — réponse vide",
     raw_preview=raw_response[:300])

# ── INTERCEPTEUR §LIVRAISON ─────────────────────────────────────────
# Ligne ~4275
zlog("info", "LIVRAISON_INTERCEPT", "§LIVRAISON détecté",
     zone_raw=detection_slots.get("zone"),
     zone_resolved=zone_info.get("name"),
     cost=zone_info.get("cost"),
     action="replaced" if zone_info.get("cost") else "short_circuit")

# ── DOSSIER COMPLET ─────────────────────────────────────────────────
# Ligne ~4303
zlog("info", "DOSSIER", "évaluation dossier",
     has_article=has_article,
     has_zone=has_zone,
     has_phone=has_phone,
     dossier_complet=dossier_complet,
     will_notify=handoff_requested or dossier_complet)

# ── NOTIFICATION OPÉRATEUR ──────────────────────────────────────────
# Ligne ~4331
zlog("info", "NOTIF_OPERATOR", "notification envoyée",
     company_id=req.company_id,
     trigger="handoff" if handoff_requested else "dossier_complet",
     article_preview=amanda_summary.get("article", "")[:60],
     zone=amanda_summary.get("zone"),
     has_phone=bool(amanda_summary.get("telephone")))

# ── FINALISATION ────────────────────────────────────────────────────
# Ligne ~4380 — avant return
zlog("info", "AMANDA_OUT", "réponse finale",
     request_id=request_id,
     company_id=req.company_id,
     response_chars=len(response_text),
     dossier_complet=dossier_complet,
     handoff=handoff_requested,
     total_ms=round((time.time() - start_time) * 1000, 2),
     timings=_timings)
```

---

## 2. JESSICA RAG BOT — LOGS PAR ÉTAPE

### app.py — Endpoint /jessicaragbot

```python
# ── RÉCEPTION ──────────────────────────────────────────────────────
# Ligne ~3884
zlog("info", "JESSICA_IN", "requête reçue",
     request_id=request_id,
     company_id=req.company_id,
     user_id=req.user_id,
     message_len=len(req.message or ""),
     has_images=bool(req.images))

# ── PLAN + BOOST ────────────────────────────────────────────────────
# Ligne ~3910
zlog("info", "PLAN_RESOLVE", "plan Jessica résolu",
     company_id=req.company_id,
     plan_name=plan_name,
     has_boost=has_boost,
     source="subscriptions")

# ── RÉSOLUTION MODÈLE ───────────────────────────────────────────────
# Ligne ~3929
zlog("info", "MODEL_RESOLVE", "modèle Jessica résolu",
     company_id=req.company_id,
     plan=plan_name,
     has_boost=has_boost,
     model=resolved_model,
     rank=rank,
     multimodal=bool(images_for_rag))

# ── APPEL RAG ───────────────────────────────────────────────────────
# Ligne ~3956
zlog("info", "RAG_CALL", "appel simplified_rag_engine",
     company_id=req.company_id,
     user_id=req.user_id,
     model=resolved_model,
     has_images=bool(images_for_rag))
```

### core/simplified_rag_engine.py — Pipeline interne

```python
# ── SHORT-CIRCUITS ──────────────────────────────────────────────────
# Avant toute logique coûteuse

# Bot paused :
zlog("info", "SHORT_CIRCUIT", "bot pausé — réponse directe",
     user_id=user_id, reason="bot_paused")

# Post-confirmation (oui/non) :
zlog("info", "SHORT_CIRCUIT", "post-confirmation — sans LLM",
     user_id=user_id,
     affirmation=_is_affirmation(msg),
     negation=_is_negation(msg),
     awaiting_code=awaiting_code[:4] + "**" if awaiting_code else None)

# ── CATALOGUE ───────────────────────────────────────────────────────
# Chargement PRODUCT_INDEX
zlog("info", "CATALOG", "PRODUCT_INDEX chargé",
     company_id=company_id,
     nb_products=len(products),
     capped_at_5=len(products) == 5,
     source="redis" if cache_hit else "supabase",
     elapsed_ms=elapsed)

# Catalogue produit spécifique injecté
zlog("info", "CATALOG", "CATALOGUE produit injecté",
     company_id=company_id,
     product_id=product_id,
     product_name=product_name,
     catalogue_chars=len(catalogue_block))

# PRODUCT_INDEX vide :
zlog("warning", "CATALOG", "PRODUCT_INDEX vide — catalogue manquant",
     company_id=company_id)

# ── CONSTRUCTION PROMPT ─────────────────────────────────────────────
zlog("debug", "PROMPT_BUILD", "prompt Jessica construit",
     total_chars=len(full_prompt),
     system_chars=len(system_prompt),
     product_index_chars=len(product_index_block),
     catalogue_chars=len(catalogue_block) if catalogue_block else 0,
     history_chars=len(conversation_history),
     status_slots_chars=len(status_slots_block),
     price_calc_present=bool(price_calc_block))

# ── APPEL LLM ───────────────────────────────────────────────────────
zlog("info", "LLM_CALL", "envoi Jessica LLM",
     model=model_name,
     rank=rank,
     prompt_chars=len(final_prompt),
     temperature=_temp,
     max_tokens=_max_tok)

zlog("info", "LLM_RESPONSE", "réponse Jessica",
     model=model_name,
     prompt_tokens=prompt_tokens,
     completion_tokens=completion_tokens,
     cached_tokens=cached_tokens,
     cache_hit_rate=round(cached_tokens / max(prompt_tokens, 1) * 100, 1),
     cost_usd=cost,
     elapsed_ms=elapsed)

# ── PARSING XML + TOOL_CALL ─────────────────────────────────────────
zlog("debug", "XML_PARSE", "thinking Jessica parsé",
     thinking_chars=len(thinking_raw),
     action=action,
     nb_items=len(items),
     product_id=items[0].get("product_id") if items else None,
     variant=items[0].get("variant") if items else None,
     handoff=handoff)

# JSON malformé dans detected_items_json :
zlog("warning", "XML_PARSE", "JSON items malformé — items=[],
     raw_json_preview=raw_json[:100],
     recovered=True)

# ── ORCHESTRATION PANIER ────────────────────────────────────────────
# Après chaque action Python sur le panier
zlog("info", "CART_ACTION", f"action panier: {action}",
     user_id=user_id,
     action=action,
     items_before=nb_before,
     items_after=nb_after,
     cart_preview=str(order_tracker.get_items(user_id))[:150])

# ── CALCUL PRIX ─────────────────────────────────────────────────────
# PYTHON UNIQUEMENT — jamais délégué au LLM
zlog("info", "PRICE_CALC", "calcul prix Python",
     user_id=user_id,
     product=product_name,
     specs=specs,
     qty=qty,
     zone=zone,
     shipping_fee=shipping_fee,
     product_subtotal=product_subtotal,
     total=total,
     status="OK" if total else "PENDING")

# Prix bloqué (specs manquantes) :
zlog("info", "PRICE_GATE", "prix bloqué",
     user_id=user_id,
     missing_for_price=missing_fields)

# ── §LIVRAISON INTERCEPTEUR ─────────────────────────────────────────
zlog("info", "LIVRAISON_INTERCEPT", "traitement §LIVRAISON",
     zone=zone,
     cost=cost,
     action="replaced" if cost else "short_circuit_zone_floue")

# ── SWAP CATALOGUE ──────────────────────────────────────────────────
zlog("info", "CATALOG_SWAP", "swap catalogue déclenché",
     user_id=user_id,
     old_product_id=old_pid,
     new_product_id=new_pid,
     trigger="tool_call_product_id")

# ── COMPLETION RATE ─────────────────────────────────────────────────
zlog("info", "COMPLETION", "taux de complétion",
     user_id=user_id,
     rate=completion_rate,
     slots={
         "produit": has_product,
         "variante": has_variant,
         "quantite": has_quantity,
         "zone": has_zone,
         "telephone": has_phone,
         "paiement": has_payment
     },
     confirmation_code_generated=completion_rate >= 1.0)

# ── FINALISATION ────────────────────────────────────────────────────
zlog("info", "JESSICA_OUT", "réponse finale",
     request_id=request_id,
     model=model_name,
     rank=rank,
     response_chars=len(response_text),
     completion_rate=completion_rate,
     total_ms=round((time.time() - start_time) * 1000, 2))
```

---

## 3. COMPOSANTS PARTAGÉS — LOGS

### core/guardian.py

```python
# Début check_access()
zlog("debug", "GUARDIAN", "vérification accès",
     company_id=company_id,
     user_id=user_id)

# Résultat
zlog("info", "GUARDIAN", "verdict final",
     company_id=company_id,
     allowed=verdict.allowed,
     reason=verdict.reason,
     plan=plan,
     usage=current_usage,
     limit=usage_limit,
     expires=next_billing_date)

# Fail-open (Guardian crash)
zlog("error", "GUARDIAN", "crash Guardian — fail-open",
     error=str(e)[:200],
     action="continuer")
```

### core/bot_registry.py

```python
# Chaque résolution de modèle
zlog("info", "REGISTRY", "modèle résolu",
     bot_type=bot_type,
     plan=plan,
     has_boost=has_boost,
     model=model,
     rank=rank)

# Garde-fou
zlog("warning", "MODEL_GUARD", "modèle interdit remplacé",
     requested=model,
     fallback=DEFAULT_FALLBACK,
     context=context)
```

### core/cost_calculator.py

```python
# Après chaque calcul
zlog("info", "COST", "coût calculé",
     model=model,
     prompt_tokens=prompt_tokens,
     cached_tokens=cached_tokens,
     completion_tokens=completion_tokens,
     cache_hit_rate_pct=round(cached_tokens / max(prompt_tokens,1) * 100, 1),
     cost_usd=round(cost, 8),
     cost_fcfa=round(cost * 615, 4))

# Modèle inconnu dans COST_TABLE
zlog("warning", "COST", "modèle absent de COST_TABLE — tarif par défaut",
     model=model)
```

### core/conversation.py

```python
# Sauvegarde message
zlog("debug", "CONVERSATION", "message sauvegardé",
     company_id=company_id,
     user_id=user_id,
     role=role,
     content_len=len(str(content)))

# Erreur sauvegarde
zlog("error", "CONVERSATION", "échec sauvegarde Supabase",
     company_id=company_id,
     role=role,
     error=str(e)[:200])
```

### core/delivery_zone_extractor.py

```python
zlog("debug", "ZONE_EXTRACT", "extraction zone",
     input_text=text[:80],
     commune=zone_info.get("name"),
     quartier=zone_info.get("quartier"),
     cost=zone_info.get("cost"),
     confidence=zone_info.get("confidence"))
```

---

## 4. REDIS CACHE — LOGS

```python
# Dans tout composant qui utilise Redis

# HIT
zlog("debug", "CACHE", "Redis HIT",
     key=cache_key,
     ttl_remaining=ttl,
     size_bytes=len(cached_value))

# MISS
zlog("debug", "CACHE", "Redis MISS — chargement source",
     key=cache_key,
     source="supabase" | "local")

# SET
zlog("debug", "CACHE", "Redis SET",
     key=cache_key,
     ttl=ttl_set,
     size_bytes=len(value_to_cache))

# Erreur Redis (non bloquant)
zlog("warning", "CACHE", "Redis indisponible — mode dégradé",
     error=str(e)[:100])
```

---

## 5. TIMINGS — RÉCAPITULATIF PAR REQUÊTE

```python
# À la fin de chaque endpoint, logguer le récapitulatif complet
zlog("info", "TIMING_SUMMARY", "récapitulatif phases",
     request_id=request_id,
     bot_type="amanda" | "jessica",
     timings={
         "guardian_ms":     _timings.get("guardian_ms"),
         "prompt_load_ms":  _timings.get("prompt_load_ms"),
         "history_ms":      _timings.get("history_load_ms"),
         "vision_ocr_ms":   _timings.get("vision_ocr_ms"),
         "catalog_ms":      _timings.get("catalog_ms"),
         "prompt_build_ms": _timings.get("prompt_build_ms"),
         "llm_call_ms":     _timings.get("llm_call_ms"),
         "xml_parse_ms":    _timings.get("xml_parse_ms"),
         "cart_action_ms":  _timings.get("cart_action_ms"),
         "price_calc_ms":   _timings.get("price_calc_ms"),
         "save_ms":         _timings.get("save_ms"),
         "total_ms":        _timings.get("total_endpoint_ms"),
     },
     llm_pct=round(_timings.get("llm_call_ms", 0) /
                   max(_timings.get("total_endpoint_ms", 1), 1) * 100, 1))
```

---

## 6. RÈGLES OPÉRATIONNELLES

```
RÈGLE 1 — Jamais silencieux sur erreur
    try:
        ...
    except Exception as e:
        zlog("error", "PHASE", "description", error=str(e)[:300],
             company_id=company_id, traceback=traceback.format_exc()[-500:])
        # Puis gérer : fallback | reraise | réponse dégradée

RÈGLE 2 — Timing individuel sur chaque phase
    t0 = time.time()
    ... logique ...
    elapsed = round((time.time() - t0) * 1000, 2)
    _timings["phase_ms"] = elapsed

RÈGLE 3 — Preview sur gros contenus (jamais full en log)
    log(prompt_chars=len(prompt))       ← OK
    log(prompt_preview=prompt[:100])    ← OK debug
    log(prompt=prompt)                  ← INTERDIT (32000 chars dans les logs)

RÈGLE 4 — request_id propagé partout
    Chaque log d'une même requête porte le même request_id
    → permet de filtrer tous les logs d'un appel : grep request_id=f969034

RÈGLE 5 — Coût toujours en USD et FCFA
    log(cost_usd=0.000095, cost_fcfa=0.058)

RÈGLE 6 — Cache hit rate toujours loggué avec le LLM
    log(cached_tokens=1100, cache_hit_rate_pct=82.1)

RÈGLE 7 — Modèle réel confirmé par OpenRouter (pas celui demandé)
    Lire model dans usage response OpenRouter
    Si différent du modèle demandé → WARNING
```

---

## 7. COMMANDES DEBUG RAPIDES

```bash
# Voir toutes les erreurs Amanda en temps réel
docker compose logs -f zeta-backend | grep "AMANDA\|ERROR\|500"

# Voir le flux complet d'une requête (par request_id)
docker compose logs zeta-backend | grep "f969034"

# Voir tous les coûts LLM
docker compose logs zeta-backend | grep "COST\|cost_usd"

# Voir les cache hits/miss
docker compose logs zeta-backend | grep "CACHE\|cached_tokens"

# Voir les timings > 5s (lenteurs)
docker compose logs zeta-backend | grep "total_ms" | awk -F'total_ms' '{if($2+0>5000) print}'

# Voir les guard-fous modèle déclenchés
docker compose logs zeta-backend | grep "MODEL_GUARD"

# Voir les bugs XML parsing
docker compose logs zeta-backend | grep "XML_PARSE.*malformé\|XML_PARSE.*impossible"

# Voir les swap catalogue
docker compose logs zeta-backend | grep "CATALOG_SWAP"

# Stats Guardian (accès refusés)
docker compose logs zeta-backend | grep "GUARDIAN.*refus"
```