# PRE-PROD TODO — ZETA AI CHATBOT
**Généré**: 9 Février 2026  
**Référence**: docs/AUDIT_PRE_PROD.md

---

## 🔴 PRE-PROD BLOCKERS (FIX AVANT DEPLOY)

- [ ] **CORS restrict origins** — `Zeta_AI/app.py:115` — Remplacer `allow_origins=["*"]` par whitelist
- [ ] **Admin endpoints auth** — `Zeta_AI/app.py:425-490` — Ajouter X-Admin-Key sur /admin/*
- [ ] **SQLite race condition** — `core/order_state_tracker.py` — Ajouter lock par user_id

## 🟠 POST-PROD URGENT (SEMAINE 1)

- [ ] **Screenshot hash anti-fraude** — `core/payment_validator.py` — Stocker hash image Redis TTL 90j
- [ ] **Timestamp paiement 48h** — `Zeta_AI/vision_gemini.py` — Valider date < 48h
- [ ] **Validate company_id** — `Zeta_AI/app.py:2198` — Vérifier existence dans Supabase
- [ ] **vision_gemini sync→async** — `Zeta_AI/vision_gemini.py:51-52` — Remplacer time.sleep + requests.get par async
- [ ] **Security validator faux positifs** — `core/security_validator.py:163` — Accepter MEDIUM, bloquer HIGH/CRITICAL
- [ ] **operator_notifications async** — `core/operator_notifications.py` — Convertir httpx sync → async
- [ ] **Input validation order_state** — `core/order_state_tracker.py:395-483` — Valider longueur/format des slots

## 🟡 IMPROVEMENTS (MOIS 1)

- [ ] **Remove debug_contexts from API response** — `Zeta_AI/app.py:3033` — Gater par env var
- [ ] **Reduce print() logs** — `Zeta_AI/app.py` — Convertir en logger.debug, tronquer messages
- [ ] **Cart items limit** — `core/cart_manager.py` — Max 20 items
- [ ] **Redis ping optimization** — `core/cart_manager.py:69-77` — Ping toutes les 30s, pas à chaque op
- [ ] **Image size limit** — `Zeta_AI/vision_gemini.py` — Max 5MB
- [ ] **Product keywords cache** — `core/short_circuit_engine.py:128` — Cache par company_id TTL 5min
- [ ] **LLM retry on 500/503** — `core/llm_client_openrouter.py` — Retry 2x avec backoff
- [ ] **LLM timeout reduce** — `core/llm_client_openrouter.py:19` — 65s → 45s
- [ ] **Move imports to top** — `Zeta_AI/app.py:2283,3144` — Regrouper imports

## 🟢 BACKLOG

- [ ] **Memory fallback TTL** — `core/cart_manager.py` — Ajouter expiration au fallback mémoire
- [ ] **httpx client cleanup** — `core/llm_client_openrouter.py` — Fermer proprement au shutdown
- [ ] **Notifications pagination** — `core/operator_notifications.py` — Limiter max limit
- [ ] **is_question false positives** — `core/short_circuit_engine.py` — Affiner détection "combien"
- [ ] **Split simplified_rag_engine.py** — Extraire modules (context, prompt, price, cart_sync)
