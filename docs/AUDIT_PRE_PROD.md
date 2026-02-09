# AUDIT PRE-PRODUCTION — CHATBOT ZETA AI
**Date**: 9 Février 2026  
**Auditeur**: Cascade AI  
**Périmètre**: /chat endpoint + toutes dépendances core/  
**Verdict global**: 3 CRITIQUES, 7 IMPORTANTS, 9 MODÉRÉS, 5 MINEURS

---

## 📊 RÉSUMÉ EXÉCUTIF

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 CRITIQUE | 3 | **FIX AVANT PROD** |
| 🟠 IMPORTANT | 7 | FIX SEMAINE 1 |
| 🟡 MODÉRÉ | 9 | FIX MOIS 1 |
| 🟢 MINEUR | 5 | Backlog |

---

## 1. Fichier: `Zeta_AI/app.py` (3649 lignes)

### ✅ Points Forts
- Rate limiting actif (slowapi 300/min)
- Security validator sur tous les inputs
- Bot_disabled silent mode bien implémenté
- Parallel I/O (get_history + save_message)
- Error handling avec fallback sur chaque section
- JSON request logging pour audit trail
- Performance tracker intégré

### ⚠️ Risques Identifiés

#### 🔴 1. CRITIQUE — CORS allow_origins=["*"] en production
**Ligne 115-121**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
```
**Problème**: `allow_origins=["*"]` avec `allow_credentials=True` est une faille de sécurité. N'importe quel site peut faire des requêtes authentifiées.

**Impact**: Un site malveillant peut envoyer des requêtes au nom d'un utilisateur connecté.

**Solution**: Restreindre aux origines connues.
```python
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "https://zetaapp.xyz,https://www.zetaapp.xyz").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)
```

#### 🔴 2. CRITIQUE — Admin endpoints sans authentification
**Lignes 425-490**
```python
@admin_router.post("/admin/cache/flush")
def flush_cache():
    redis_cache.flush_all()
    return {"success": True}

@app.post("/admin/cache/prompt/clear")
async def clear_prompt_cache_endpoint(request: dict):
```
**Problème**: Les endpoints `/admin/*` n'ont AUCUNE protection (pas d'API key, pas d'auth). N'importe qui peut vider le cache Redis, vider les prompts, etc.

**Impact**: DoS facile — un attaquant vide le cache en boucle, forçant des appels LLM coûteux à chaque requête.

**Solution**: Ajouter un middleware d'authentification admin.
```python
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

async def verify_admin(request: Request):
    key = request.headers.get("X-Admin-Key", "")
    if not ADMIN_API_KEY or key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

@admin_router.post("/admin/cache/flush", dependencies=[Depends(verify_admin)])
```

#### 🟠 3. IMPORTANT — Pas de validation company_id/user_id
**Ligne 2198-2211**
```python
async def chat_endpoint(req: ChatRequest, request: Request):
    # Aucune validation que company_id existe dans Supabase
    # Aucune validation format user_id
```
**Problème**: Un attaquant peut envoyer n'importe quel `company_id` et accéder aux prompts/catalogues d'autres entreprises.

**Solution**: Valider company_id contre une whitelist ou table Supabase.

#### 🟠 4. IMPORTANT — `import asyncio` au milieu du endpoint
**Ligne 2283**
```python
import asyncio
```
**Problème**: Import au milieu d'une fonction (mauvaise pratique, micro-overhead à chaque requête).

**Solution**: Déplacer en haut du fichier.

#### 🟠 5. IMPORTANT — `save_message_supabase` importé APRÈS la définition du endpoint
**Ligne 3144**
```python
from core.conversation import save_message as save_message_supabase, get_history
```
**Problème**: L'import est en bas du fichier mais utilisé dans le chat endpoint (ligne 2233). Python résout cela car l'import est au module-level, mais c'est fragile et confus.

**Solution**: Regrouper tous les imports en haut du fichier.

#### 🟡 6. MODÉRÉ — Logs excessifs en production
**Lignes 2214-2218, 2500-2507, etc.**
```python
print(f"🔍 [CHAT_ENDPOINT] Message: '{req.message}'")
print(f"🔍 [CHAT_ENDPOINT] Company: {req.company_id}")
print(f"🔍 [CHAT_ENDPOINT] User: {req.user_id}")
```
**Problème**: Des dizaines de `print()` avec le message complet du client. En production, cela (1) ralentit l'I/O, (2) expose des données personnelles dans les logs.

**Solution**: Utiliser `logger.debug()` et tronquer les messages.

#### 🟡 7. MODÉRÉ — `debug_contexts` expose des données internes dans la réponse API
**Ligne 3033**
```python
"debug_contexts": debug_contexts  # ✅ TOUS LES CONTEXTES SYSTÈME
```
**Problème**: La réponse API contient `debug_contexts` avec state_tracker, enhanced_memory, security_score, etc. Un client peut voir l'état interne du système.

**Solution**: Ne renvoyer `debug_contexts` qu'en mode debug.
```python
if os.getenv("DEBUG_CONTEXTS_IN_RESPONSE", "false").lower() == "true":
    final_response["debug_contexts"] = debug_contexts
```

#### 🟡 8. MODÉRÉ — `security_check.risk_level` MEDIUM bloque les requêtes légitimes
**Ligne 2448-2457**
Le security validator bloque tout ce qui n'est pas `LOW`. Le mot "database" dans un message client légitime (ex: "vous avez une base de données de produits?") sera bloqué.

**Solution**: Ne bloquer que `HIGH`/`CRITICAL`, logger les `MEDIUM`.

### 📊 Métriques Code
- **Lignes**: 3649
- **Complexité**: Élevée (endpoint monolithique ~900 lignes)
- **Type hints**: ~40%
- **Docstrings**: Partielles

---

## 2. Fichier: `core/order_state_tracker.py` (650 lignes)

### ✅ Points Forts
- Persistance SQLite avec auto-nettoyage 7 jours
- Parameterized queries (pas de SQL injection)
- Fallback `/tmp/` si le path principal échoue
- Protection paiement validé (ne jamais écraser par valeur plus faible)
- Cooldown anti-répétition sur les questions

### ⚠️ Risques Identifiés

#### 🔴 3. CRITIQUE — Race condition SQLite multi-workers
**Lignes 141, 224, 350, 376**
```python
conn = sqlite3.connect(self.db_path)
cursor = conn.cursor()
cursor.execute(...)
conn.commit()
conn.close()
```
**Problème**: Chaque méthode ouvre/ferme sa propre connexion SQLite. Avec uvicorn multi-workers (ou même async), deux requêtes simultanées pour le même user_id peuvent lire le même état, modifier indépendamment, et la dernière écriture écrase la première.

**Impact**: Perte de données collectées (ex: zone écrasée par une écriture concurrente qui ne la connaît pas).

**Solution**: Utiliser un lock par user_id ou passer à Redis pour le state.
```python
import threading
_user_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()

def _get_user_lock(self, user_id: str) -> threading.Lock:
    with _global_lock:
        if user_id not in _user_locks:
            _user_locks[user_id] = threading.Lock()
        return _user_locks[user_id]

def update_produit(self, user_id, produit, ...):
    with self._get_user_lock(user_id):
        state = self.get_state(user_id)
        state.produit = produit
        self._save_state(state)
```

#### 🟠 6. IMPORTANT — Pas de validation des données entrantes
**Lignes 395-483**
```python
def update_produit(self, user_id: str, produit: str, ...):
    state.produit = produit  # Aucune validation/sanitization
```
**Problème**: Les valeurs sont stockées telles quelles. Un produit_id malformé ou une zone avec des caractères spéciaux pourrait corrompre l'état.

**Solution**: Ajouter une validation minimale (longueur max, caractères autorisés).

#### 🟡 9. MODÉRÉ — Connexion SQLite non poolée
Chaque appel crée une nouvelle connexion SQLite. Pour un endpoint async à fort trafic, cela peut devenir un goulot.

**Solution**: Utiliser un pool de connexions ou un singleton avec WAL mode.

### 📊 Métriques Code
- **Lignes**: 650
- **Complexité**: Modérée
- **Type hints**: 80%
- **SQL injection**: ✅ Protégé (parameterized queries)

---

## 3. Fichier: `core/payment_validator.py` (282 lignes)

### ✅ Points Forts
- Validation cumulative (supporte paiements fragmentés)
- Protection anti-fraude (max 3 paiements, montant 50-100000F)
- Exclusion des montants "manquants" de l'historique
- Tests unitaires intégrés
- Format compact pour injection LLM

### ⚠️ Risques Identifiés

#### 🟠 7. IMPORTANT — Pas de hash screenshot (réutilisation possible)
**Problème**: Aucun mécanisme pour détecter si une capture de paiement a déjà été utilisée. Un client peut envoyer la même capture Wave pour 2 commandes différentes.

**Impact**: Fraude directe — 1 paiement = N commandes.

**Solution**: Stocker un hash de l'image + montant + date dans Redis avec TTL 90 jours.
```python
def check_screenshot_reuse(image_hash: str, redis_client) -> bool:
    key = f"payment_screenshot:{image_hash}"
    if redis_client.exists(key):
        return True  # DÉJÀ UTILISÉ
    redis_client.setex(key, 90 * 24 * 3600, "used")
    return False
```

#### 🟠 8. IMPORTANT — Pas de validation timestamp paiement
**Problème**: Un client peut envoyer une capture de paiement vieille de 6 mois. Le système accepte si le montant est correct.

**Impact**: Fraude — réutilisation d'anciennes captures.

**Solution**: Vérifier que la date du paiement est < 48h (déjà parsée dans `vision_gemini.py`).

#### 🟡 10. MODÉRÉ — Regex fragiles pour extraction paiements historique
**Lignes 159-166**: Les patterns regex pour extraire les paiements de l'historique sont sensibles au format exact. Un changement de formulation dans les réponses du LLM pourrait casser l'extraction.

### 📊 Métriques Code
- **Lignes**: 282
- **Complexité**: Faible
- **Type hints**: 90%
- **Tests**: ✅ Intégrés

---

## 4. Fichier: `core/cart_manager.py` (326 lignes)

### ✅ Points Forts
- Redis avec fallback mémoire
- TTL 72h sur les paniers
- Dédoublonnage par signature (product_id|variant|spec|unit)
- Pending pivot pour clarification A/B
- Toutes les opérations CRUD couvertes

### ⚠️ Risques Identifiés

#### 🟡 11. MODÉRÉ — Pas de limite sur le nombre d'items
**Problème**: Aucune limite sur `cart["items"]`. Un attaquant pourrait ajouter des milliers d'items.

**Solution**: Limiter à 20 items max.
```python
MAX_CART_ITEMS = 20
def add_item(self, user_id, item):
    cart = self._load(user_id)
    if len(cart["items"]) >= MAX_CART_ITEMS:
        logger.warning("⚠️ Cart limit reached for %s", user_id[:12])
        return cart
```

#### 🟡 12. MODÉRÉ — `_redis_ok()` fait un PING à chaque opération
**Ligne 69-77**: Chaque `_load`/`_save` fait un `self._redis.ping()`. Sous charge, cela double le nombre de commandes Redis.

**Solution**: Vérifier le ping uniquement toutes les N secondes ou sur erreur.

#### 🟢 1. MINEUR — `_memory` fallback ne respecte pas le TTL
Le fallback mémoire n'a pas de mécanisme d'expiration. Les paniers restent en mémoire indéfiniment.

### 📊 Métriques Code
- **Lignes**: 326
- **Complexité**: Faible
- **Type hints**: 85%

---

## 5. Fichier: `Zeta_AI/vision_gemini.py` (496 lignes)

### ✅ Points Forts
- Téléchargement robuste avec retry (3 tentatives, URL alternatives)
- Parsing JSON avec fallback regex
- Normalisation téléphone (10 derniers chiffres)
- Parsing date multi-format (français)
- Codes erreur OCR stricts (NUMERO_ABSENT, TRANSACTION_ABSENTE, etc.)
- Retry avec max_tokens augmenté si JSON incomplet

### ⚠️ Risques Identifiés

#### 🟠 9. IMPORTANT — `time.sleep(2)` bloque l'event loop
**Ligne 51**
```python
if delay > 0:
    time.sleep(delay)
```
**Problème**: `time.sleep()` dans une fonction appelée depuis un contexte async bloque l'event loop pendant 2 secondes.

**Solution**: Utiliser `await asyncio.sleep(delay)` ou déplacer le download dans un thread.

#### 🟠 10. IMPORTANT — `requests.get` synchrone pour téléchargement image
**Ligne 52**
```python
resp = requests.get(attempt_url, headers=headers, timeout=15, stream=True)
```
**Problème**: Appel synchrone bloquant dans un contexte async. Bloque l'event loop pendant le téléchargement (jusqu'à 15s).

**Solution**: Utiliser `httpx.AsyncClient` comme pour les autres appels.

#### 🟡 13. MODÉRÉ — Pas de limite taille image
**Problème**: Aucune vérification de la taille de l'image téléchargée. Une image de 50MB serait encodée en base64 et envoyée à Gemini.

**Solution**: Limiter à 5MB.
```python
if len(img_bytes) > 5 * 1024 * 1024:
    print("⚠️ [VISION] Image too large, skipping")
    continue
```

### 📊 Métriques Code
- **Lignes**: 496
- **Complexité**: Modérée
- **Type hints**: 75%

---

## 6. Fichier: `core/short_circuit_engine.py` (602 lignes)

### ✅ Points Forts
- Garde-fous robustes (questions, produits, cart vide, images)
- Détection phone+zone combo en un seul message
- Templates scalables (aucun nom produit hardcodé)
- Persistance immédiate des données détectées
- Extraction phone inline (ex: "angre 0160924560")

### ⚠️ Risques Identifiés

#### 🟡 14. MODÉRÉ — `_build_product_keywords` appelé à chaque message
**Ligne 128-170**: Le catalogue est rechargé à chaque appel de `check_short_circuit`. Pour un catalogue statique, c'est du gaspillage.

**Solution**: Cacher les keywords par company_id avec TTL 5 min.

#### 🟢 2. MINEUR — `is_question` détecte "combien" même dans "j'en veux combien tu veux"
Le mot "combien" dans `_QUESTION_PATTERNS_ANYWHERE` matche même quand ce n'est pas une question.

### 📊 Métriques Code
- **Lignes**: 602
- **Complexité**: Modérée
- **Type hints**: 80%

---

## 7. Fichier: `core/llm_client_openrouter.py` (240 lignes)

### ✅ Points Forts
- Async httpx avec connection pooling global
- Retry automatique sur modèle invalide (fallback candidates)
- Retry avec max_tokens réduit sur erreur 402 (crédits)
- Normalisation des alias modèles

### ⚠️ Risques Identifiés

#### 🟡 15. MODÉRÉ — Pas de retry sur erreurs transitoires (500, 503, timeout)
**Problème**: Si OpenRouter renvoie une 500 ou timeout, l'erreur est propagée directement. Pas de retry avec backoff.

**Solution**: Ajouter retry (max 2) avec backoff exponentiel pour 500/502/503/timeout.

#### 🟡 16. MODÉRÉ — Timeout global 65s trop long
**Ligne 19**: Un timeout de 65s signifie qu'un client attend potentiellement plus d'une minute.

**Solution**: Réduire à 45s et ajouter un timeout global au niveau du endpoint.

#### 🟢 3. MINEUR — `_openrouter_client` global sans cleanup
Le client httpx global n'est jamais fermé proprement. Pas critique mais peut causer des warnings.

### 📊 Métriques Code
- **Lignes**: 240
- **Complexité**: Faible
- **Type hints**: 70%

---

## 8. Fichier: `core/operator_notifications.py` (153 lignes)

### ✅ Points Forts
- Code simple et focalisé
- Timeout 5s sur tous les appels Supabase
- Error handling complet

### ⚠️ Risques Identifiés

#### 🟡 17. MODÉRÉ — Appels synchrones httpx dans un contexte async
**Lignes 54, 106, 122, 143**: Tous les appels utilisent `httpx.post/get/patch` synchrones. Bloque l'event loop.

**Impact**: Faible car appelé uniquement dans le path bot_disabled (rapide), mais devrait être async pour cohérence.

#### 🟢 4. MINEUR — Pas de pagination sur GET notifications
Si une entreprise a 10000 notifications, le `limit=50` par défaut est OK mais le endpoint permet `limit=999999`.

### 📊 Métriques Code
- **Lignes**: 153
- **Complexité**: Très faible
- **Type hints**: 80%

---

## 9. Fichier: `core/security_validator.py` (257 lignes)

### ✅ Points Forts
- Patterns d'injection de prompt complets (FR + EN)
- Détection fausse autorité
- Détection données personnelles
- Sanitisation des prompts dangereux
- URL masquées avant détection (évite faux positifs base64)

### ⚠️ Risques Identifiés

#### 🟠 11. IMPORTANT — Faux positifs sur mots courants
**Problème**: Le mot "database" dans `sensitive_keywords` bloque des questions légitimes. "password" aussi (ex: "j'ai oublié mon password Wave").

**Solution**: Ne bloquer que si combiné avec un pattern d'injection, pas seul.

#### 🟡 18. MODÉRÉ — `risk_level == "LOW"` trop strict
**Ligne 163**: Seuls les prompts `LOW` passent. Un simple mot comme "admin" dans "l'admin de ma page" bloque la requête.

**Solution**: Accepter `LOW` et `MEDIUM`, bloquer uniquement `HIGH`/`CRITICAL`.

---

## 10. Fichier: `core/simplified_rag_engine.py` (~6700 lignes)

### ✅ Points Forts (audité sessions précédentes)
- Catalog-driven (scalable, pas de hardcoded)
- Price calculator universel
- Cart sync automatique
- Proactive hints injection
- Auto-clôture sur paiement validé
- Bot_disabled flag

### ⚠️ Risques Identifiés

#### 🟡 19. MODÉRÉ — Fichier trop volumineux (~6700 lignes)
**Problème**: Maintenabilité difficile. Une seule classe fait tout (context, prompt, LLM, parsing, price calc, cart sync).

**Solution** (post-prod): Extraire en modules séparés.

---

## 🎯 POINTS CRITIQUES SPÉCIFIQUES

### A. Gestion Paiement

| Check | Status | Détail |
|-------|--------|--------|
| Screenshot déjà utilisé → REJET | ❌ **MANQUANT** | Pas de hash image stocké |
| Timestamp paiement > 48h → REJET | ❌ **MANQUANT** | Date parsée mais non validée |
| Numéro destinataire incorrect → REJET | ✅ OK | Gemini vérifie via error_code NUMERO_ABSENT |
| Montant insuffisant → SIGNALEMENT | ✅ OK | MONTANT_INSUFFISANT error_code |
| Double paiement → DÉTECTION | ❌ **MANQUANT** | Pas de check historique |
| OCR échoue → FALLBACK HUMAIN | ✅ OK | CAPTURE_INVALIDE + retry max_tokens |

### B. State Management

| Check | Status | Détail |
|-------|--------|--------|
| Race conditions | ❌ **CRITIQUE** | SQLite sans lock par user |
| Data loss | ⚠️ PARTIEL | Persist immédiat mais pas de backup si SQLite fail |
| Incohérences | ✅ OK | Validation paiement hiérarchique |
| Memory leaks | ✅ OK | Cleanup 7 jours |

### C. LLM Calls

| Check | Status | Détail |
|-------|--------|--------|
| Token usage | ✅ OK | Historique tronqué, URLs raccourcies |
| Retry logic | ⚠️ PARTIEL | Retry modèle/crédits, pas timeout/500 |
| Parallel calls | ✅ OK | HYDE + prompt_version parallèles |
| Error handling | ✅ OK | Fallback response sur échec total |

### D. Database Operations

| Check | Status | Détail |
|-------|--------|--------|
| Supabase RLS | ✅ OK | Configuré |
| Prepared statements | ✅ OK | Parameterized queries partout |
| Connection pool | ✅ OK | httpx.AsyncClient global |
| Redis TTL | ✅ OK | TTL sur cart (72h), cache (30min/1h) |

---
