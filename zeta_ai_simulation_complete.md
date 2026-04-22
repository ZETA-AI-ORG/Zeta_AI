# ZETA AI — SIMULATION COMPLÈTE CLIENT → RÉPONSE
# Arborescence exhaustive avec logs attendus à chaque étape
# Valable pour comparaison avec système en test

---

## LÉGENDE

```
👤 CLIENT        : message entrant
🤖 BOT           : réponse attendue
🐍 PYTHON        : action orchestrateur (jamais le LLM)
🧠 LLM           : raisonnement + génération texte
📋 LOG ATTENDU   : ce qu'on doit voir dans docker logs
✅ ATTENDU       : comportement correct
❌ PROBLÈME      : si ce log n'apparaît pas
⚠️  ALERTE        : comportement dégradé toléré
```

---

# ═══════════════════════════════════════════════
# SECTION A — AMANDA BOTLIVE (Live TikTok)
# ═══════════════════════════════════════════════

## PLAN × MODÈLE (rappel)
```
Découverte / Starter / Pro / Elite → qwen/qwen3-235b-a22b-2507 (boost ignoré)
Fallback                           → google/gemma-4-26b-a4b-it
```

---

## A0 — AVANT TOUT MESSAGE : VÉRIFICATIONS SYSTÈME

```
📋 LOG ATTENDU (au démarrage de l'endpoint) :
[AMANDA_IN] requête reçue | company_id=XXX | user_id=YYY | message_len=N | has_images=false

✅ ATTENDU : request_id unique généré (8 chars)
❌ PROBLÈME : si "500 Internal Server Error" → aller à A0-ERR
```

### A0-ERR — Crash immédiat (bug plan_type)
```
📋 LOG ATTENDU :
[SUBSCRIPTIONS] erreur SQL — vérifier nom colonne | sql_error="column plan_type does not exist" | hint="plan_name PAS plan_type"
[PROMPT_LOAD] company_info invalide — guard déclenché | info_type=str

✅ FIX : remplacer plan_type → plan_name dans botlive_prompts_supabase.py
❌ SI NON FIXÉ : Amanda 500 à chaque requête, zéro client servi
```

---

## A1 — GUARDIAN : VÉRIFICATION ABONNEMENT

### A1.1 — Plan actif, quota OK
```
🐍 PYTHON : vérifie subscriptions (plan_name, status, current_usage, usage_limit)

📋 LOG ATTENDU :
[GUARDIAN] verdict | company_id=XXX | allowed=true | reason=OK | plan=starter | elapsed_ms=45

✅ ATTENDU : pipeline continue normalement
```

### A1.2 — Abonnement Découverte expiré (15 jours)
```
🐍 PYTHON : compare now() > pro_trial_ends_at

📋 LOG ATTENDU :
[GUARDIAN] verdict | allowed=false | reason=ABONNEMENT_EXPIRE | plan=decouverte

🤖 BOT ATTENDU (humanisé via message_registry) :
"Bonjour ! Notre service est temporairement suspendu.
 Contactez-nous pour renouveler votre accès 🙏"

✅ ATTENDU : réponse humanisée, pas de crash, pas d'appel LLM
❌ PROBLÈME : si LLM appelé quand même → Guardian non branché
```

### A1.3 — Quota épuisé (ex: Starter 1500 msgs atteints)
```
📋 LOG ATTENDU :
[GUARDIAN] verdict | allowed=false | reason=QUOTA_EPUISE | plan=starter | usage=1500 | limit=1500

🤖 BOT ATTENDU :
"Votre volume mensuel est atteint. Rechargez pour continuer : 5F/msg (0-1000), 3F/msg (1001-6000) 😊"

✅ ATTENDU : message avec info recharge, pas d'appel LLM
```

### A1.4 — Session limit atteinte (25 req/client)
```
📋 LOG ATTENDU :
[GUARDIAN] verdict | allowed=false | reason=SESSION_LIMIT | plan=pro

🤖 BOT ATTENDU :
"Je passe le relais à notre équipe pour finaliser avec vous 🙏"
##HANDOFF## (déclenché automatiquement)

✅ ATTENDU : notification opérateur envoyée
```

### A1.5 — Guardian crash (fail-open)
```
📋 LOG ATTENDU :
[GUARDIAN] crash Guardian — fail-open | error="connection refused" | action="continuer"

⚠️ ALERTE : pipeline continue sans Guardian — surveiller
✅ ATTENDU : client servi malgré l'erreur (jamais bloquer)
```

---

## A2 — CHARGEMENT PROMPT

### A2.1 — Cache Redis HIT (tours 2+)
```
🐍 PYTHON : vérifie Redis clé prompt_bots:amanda:{company_id}

📋 LOG ATTENDU :
[CACHE] Redis HIT | key=prompt_bots:amanda:XXX | ttl_remaining=3245s | size_bytes=5420
[PROMPT_LOAD] prompt chargé | source=redis | prompt_chars=1340 | elapsed_ms=8

✅ ATTENDU : < 10ms, économie Supabase
❌ PROBLÈME : si toujours MISS → Redis déconnecté ou TTL mal configuré
```

### A2.2 — Cache Redis MISS (premier appel)
```
📋 LOG ATTENDU :
[CACHE] Redis MISS — chargement source | key=prompt_bots:amanda:XXX | source=supabase
[PROMPT_LOAD] prompt chargé | source=supabase | prompt_chars=1340 | elapsed_ms=280
[CACHE] Redis SET | key=prompt_bots:amanda:XXX | ttl=3600 | size_bytes=5420

✅ ATTENDU : ~300ms acceptable pour premier appel
```

### A2.3 — Fallback fichier local
```
📋 LOG ATTENDU :
[PROMPT_LOAD] fallback local utilisé | original_error="connection timeout" | source=local_fallback

⚠️ ALERTE : Supabase indisponible, prompt par défaut utilisé
✅ ATTENDU : client servi avec prompt générique (variables non remplacées = valeurs par défaut)
```

---

## A3 — SIMULATION CONVERSATIONS AMANDA

---

### 🔵 CAS A3.1 — CLIENT SIMPLE (Découverte/Starter)
**Contexte :** boutique vêtements, Live TikTok en cours, plan Starter

#### Tour 1 — Salutation
```
👤 CLIENT : "Bonjour"

🐍 PYTHON ATTENDU :
  - Guardian : OK (plan=starter, usage=1/1500)
  - Prompt : Redis MISS → Supabase → SET cache
  - Historique : 0 messages
  - Vision OCR : skip (pas d'image)
  - Modèle résolu : qwen/qwen3-235b-a22b-2507

📋 LOGS ATTENDUS :
[AMANDA_IN] requête reçue | message_len=7 | has_images=false
[GUARDIAN] verdict | allowed=true | reason=OK | plan=starter
[CACHE] Redis MISS
[PROMPT_LOAD] prompt chargé | source=supabase | elapsed_ms=~280
[HISTORY] historique chargé | chars=0
[MODEL_RESOLVE] modèle Amanda résolu | plan=starter | model=qwen/qwen3-235b-a22b-2507 | boost_ignored=true
[LLM_CALL] envoi au LLM | model=qwen/qwen3-235b-a22b-2507 | prompt_chars=~1800 | temperature=0.72
[LLM_RESPONSE] réponse reçue | prompt_tokens=~450 | completion_tokens=~60 | cached_tokens=0 | cost_usd=~0.000038
[XML_PARSE] thinking parsé | has_detection=false | priority=DEMANDER_ARTICLE
[DOSSIER] évaluation | has_article=false | has_zone=false | has_phone=false | dossier_complet=false
[AMANDA_OUT] réponse finale | total_ms=~1200

🧠 LLM THINKING ATTENDU :
<thinking>
  <q_exact>Bonjour</q_exact>
  <catalogue_match>Statut: COMPATIBLE | Action: Mode SOCIAL</catalogue_match>
  <detected_items_json>[{"product_id":"live_item","variant":"","qty":1}]</detected_items_json>
  <tool_call>{"action":"NONE"}</tool_call>
  <maj><action>UPDATE</action><reason>Accueil client — aucune info encore</reason></maj>
  <detection>
    - RÉSUMÉ: Preuve Image: NON + Salutation initiale
    - ZONE: ∅
    - TÉLÉPHONE: ∅
    - PAIEMENT: ∅
  </detection>
  <priority>DEMANDER_ARTICLE</priority>
  <handoff>false</handoff>
</thinking>

🤖 BOT ATTENDU :
"Bonjour ! Bienvenue sur l'inbox de [shop_name] 😊 
 Vous avez vu un article sur le Live qui vous intéresse ? Envoyez-moi une capture !"

✅ CONTRÔLES :
- Pas de prix mentionné ✓
- Vouvoiement ✓
- Max 2 phrases ✓
- §LIVRAISON absent (zone pas encore connue) ✓
- ##HANDOFF## absent ✓
```

#### Tour 2 — Client décrit l'article sans image
```
👤 CLIENT : "La robe rouge que la patronne vient de montrer"

🐍 PYTHON ATTENDU :
  - Guardian : OK (usage=2/1500)
  - Prompt : Redis HIT (cache)
  - Historique : 1 message précédent

📋 LOGS ATTENDUS :
[CACHE] Redis HIT | key=prompt_bots:amanda:XXX | elapsed_ms=8
[HISTORY] historique chargé | chars=~120
[LLM_CALL] envoi au LLM | prompt_chars=~2100
[LLM_RESPONSE] cached_tokens=~350 | cache_hit_rate_pct=~75 | elapsed_ms=~900

🧠 LLM THINKING ATTENDU :
<detection>
  - RÉSUMÉ: Preuve Image: NON + Robe rouge (vue sur Live)
  - ZONE: ∅
  - TÉLÉPHONE: ∅
  - PAIEMENT: ∅
</detection>
<priority>DEMANDER_QUARTIER</priority>

🤖 BOT ATTENDU (proactif — zone + contact en une phrase) :
"Super, la robe rouge est notée pour vous ! 🎉
 Donnez-moi votre quartier et un numéro joignable, je bloque votre place tout de suite."

✅ CONTRÔLES :
- Demande les 2 infos manquantes ensemble (proactivité) ✓
- Article noté dans RÉSUMÉ ✓
- Pas de §LIVRAISON (zone inconnue) ✓
```

#### Tour 3 — Client donne zone et téléphone
```
👤 CLIENT : "Cocody Angré, 0707070707"

🐍 PYTHON ATTENDU :
  - XML parse : ZONE="Cocody Angré", TÉLÉPHONE="0707070707"
  - §LIVRAISON check : "§LIVRAISON" dans réponse LLM ? → remplacer

📋 LOGS ATTENDUS :
[XML_PARSE] thinking parsé | slots={zone:"Cocody Angré", telephone:"0707070707"}
[LIVRAISON_INTERCEPT] §LIVRAISON détecté | zone_resolved="Cocody Angré" | cost=1500 | action=replaced
[DOSSIER] évaluation | has_article=true | has_zone=true | has_phone=true | dossier_complet=true
[NOTIF_OPERATOR] notification envoyée | trigger=dossier_complet | article="Robe rouge" | zone="Cocody Angré"

🤖 BOT ATTENDU :
"C'est parfaitement noté ! Votre robe rouge est réservée en priorité 🎉
 La livraison pour Cocody Angré c'est 1500F. [shop_name] vous appellera dès la fin du Live pour confirmer le total !"
##HANDOFF##

✅ CONTRÔLES :
- §LIVRAISON remplacé par Python (1500F) ✓
- ##HANDOFF## présent (dossier complet) ✓
- Notification opérateur envoyée ✓
- Pas de prix article inventé ✓
```

---

### 🔵 CAS A3.2 — CLIENT AVEC IMAGE (VISION_OCR)

#### Tour 1 — Client envoie capture écran du Live
```
👤 CLIENT : "Je veux ça" + [image_url: capture_live_robe.jpg]

🐍 PYTHON ATTENDU :
  - Vision OCR déclenché (image présente)
  - Modèle OCR : google/gemini-3.1-flash-lite-preview

📋 LOGS ATTENDUS :
[VISION_OCR] analyse image | ocr_type=produit | model=google/gemini-3.1-flash-lite-preview | elapsed_ms=~800
[VISION_OCR] résultat | ocr_chars=~120 | preview="Robe fleurie bleue taille M prix affiché 15000F"

🧠 LLM REÇOIT : [VISION_OCR: Robe fleurie bleue taille M prix affiché 15000F]

🤖 BOT ATTENDU :
"Parfait, la robe fleurie bleue taille M est bien notée pour vous 🙏
 Vous êtes dans quel quartier et quel numéro pour le livreur ?"

✅ CONTRÔLES :
- Amanda ne mentionne PAS le prix 15000F (vu dans OCR mais non confirmé par boutique) ✓
- Article extrait via OCR dans RÉSUMÉ ✓
```

---

### 🔵 CAS A3.3 — CLIENT ENVOIE PREUVE DE DÉPÔT WAVE

```
👤 CLIENT : "J'ai payé" + [image_url: recu_wave.jpg]

🐍 PYTHON ATTENDU :
  - Vision OCR paiement : google/gemini-3.1-pro-preview (modèle critique)
  - Extraction : montant, numéro transaction, date, destinataire

📋 LOGS ATTENDUS :
[VISION_OCR] analyse image | ocr_type=paiement | model=google/gemini-3.1-pro-preview | elapsed_ms=~2000
[VISION_OCR] résultat | montant=2000 | transaction_id=WAVE-2026-XXXXX | destinataire=+22507XXXXXX

🤖 BOT ATTENDU :
"Merci beaucoup, c'est bien reçu ! 🙏
 Le blocage définitif sera confirmé par [shop_name] après vérification — vous serez appelé(e) très vite !"

✅ CONTRÔLES :
- Modèle Pro utilisé pour paiement (critique) ✓
- Pas de confirmation définitive par Amanda (réservé à la boutique) ✓
```

---

### 🔵 CAS A3.4 — CLIENT ENVOIE UN AUDIO

```
👤 CLIENT : [message audio WhatsApp]

📋 LOG ATTENDU :
[XML_PARSE] thinking parsé | priority=CAS_LIMITE_AUDIO

🤖 BOT ATTENDU :
"Je ne peux pas écouter les audios ici, écrivez-moi directement 😊
 Quel article vous intéresse sur le Live ?"

✅ CONTRÔLES :
- Pas d'appel Vision OCR sur audio ✓
- Redirection naturelle vers texte ✓
```

---

### 🔵 CAS A3.5 — CLIENT DONNE ZONE FLOUE

```
👤 CLIENT : "Je suis à Abidjan"

🐍 PYTHON ATTENDU :
  - §LIVRAISON dans réponse LLM → zone floue → court-circuit Python direct

📋 LOGS ATTENDUS :
[LIVRAISON_INTERCEPT] §LIVRAISON détecté | zone_raw="Abidjan" | cost=null | action=short_circuit

🤖 BOT (généré par Python, pas LLM) :
"C'est noté ! Pour calculer les frais exacts, j'ai besoin de votre commune et quartier précis 😊"

✅ CONTRÔLES :
- Court-circuit Python (pas re-appel LLM) ✓
- Zone floue non acceptée ✓
```

---

### 🔵 CAS A3.6 — CLIENT HÉSITE (objections)

#### Sous-cas : "C'est combien ?"
```
👤 CLIENT : "C'est combien la robe ?"

🧠 LLM ATTENDU :
→ idée appliquée : prix gérés en direct par la boutique, son rôle = bloquer l'article

🤖 BOT ATTENDU :
"Les prix promos sont validés par [shop_name] en direct sur le Live 🎯
 Moi je suis là pour bloquer votre article — donnez-moi vos infos et elle vous rappelle avec le tarif exact !"

✅ CONTRÔLES :
- Aucun prix inventé ✓
- Transformation objection → levier réservation ✓
```

#### Sous-cas : "J'attends la fin du Live"
```
👤 CLIENT : "Je vais attendre que le Live finisse"

🤖 BOT ATTENDU :
"Attention, les articles partent à toute vitesse pendant le direct ! 😬
 Laissez-moi juste votre numéro et la photo, je vous mets de côté sans engagement — zéro risque."

✅ CONTRÔLES :
- Urgence réelle (pas manipulation) ✓
- Sans engagement / zéro risque mentionné ✓
```

#### Sous-cas : "J'ai déjà été arnaqué"
```
👤 CLIENT : "J'ai peur c'est pour ça"

🤖 BOT ATTENDU :
"Je vous comprends totalement, et c'est normal d'être prudent 🙏
 Pas de paiement maintenant — juste bloquer votre article. [shop_name] vous appelle pour tout valider ensemble."

✅ CONTRÔLES :
- Empathie ✓
- Pas de paiement demandé ✓
```

---

### 🔵 CAS A3.7 — CLIENT HORS ABIDJAN

```
👤 CLIENT : "Je suis à Bouaké"

🐍 PYTHON ATTENDU :
  - §LIVRAISON : zone hors Abidjan détectée → mode EXPÉDITION

📋 LOG ATTENDU :
[LIVRAISON_INTERCEPT] zone=Bouaké | type=expedition | cost=variable | action=inform_protocol

🤖 BOT ATTENDU :
"Pas de souci pour Bouaké ! 😊
 Pour l'expédition, [shop_name] vous appelle directement pour confirmer le coût et le délai — donnez-moi votre gare préférée et votre numéro !"

✅ CONTRÔLES :
- Pas de coût inventé pour expédition ✓
- Collecte ville + gare demandée ✓
- Protocole paiement 100% avance mentionné si approprié ✓
```

---

### 🔵 CAS A3.8 — CLIENT AGRESSIF

```
👤 CLIENT : "C'est des escrocs ! Je veux parler à un humain maintenant !"

📋 LOG ATTENDU :
[XML_PARSE] handoff=true | priority=CLOTURER | reason=client_agressif
[NOTIF_OPERATOR] trigger=handoff | reason=escalade_humaine

🤖 BOT ATTENDU :
"Je vous passe immédiatement quelqu'un de l'équipe 🙏
 Vous serez contacté(e) très rapidement, promis."
##HANDOFF##

✅ CONTRÔLES :
- ##HANDOFF## présent ✓
- Notification opérateur envoyée ✓
- Amanda ne continue pas la collecte ✓
```

---

### 🔵 CAS A3.9 — PLAN PRO / BOOST (Amanda inchangée)

```
📋 LOG ATTENDU :
[MODEL_RESOLVE] model=qwen/qwen3-235b-a22b-2507 | plan=pro | has_boost=true | boost_ignored=true

✅ ATTENDU : même modèle que Starter
⚠️ ALERTE si boost impacte Amanda : bug registry
```

---

# ═══════════════════════════════════════════════
# SECTION B — JESSICA RAG BOT (Vente Catalogue)
# ═══════════════════════════════════════════════

## PLAN × MODÈLE (rappel)
```
Découverte / Starter     → google/gemma-4-26b-a4b-it  (Rang A, temp 0.45)
Pro / Elite (sans boost) → deepseek/deepseek-v3.2      (Rang S, temp 0.40)
Tout plan + boost        → gemini-3.1-flash-lite        (Rang Boost, temp 0.38)
Image présente           → gemini-3.1-pro-preview       (multimodal)
```

---

## B0 — AVANT TOUT MESSAGE : VÉRIFICATIONS

```
📋 LOG ATTENDU :
[JESSICA_IN] requête reçue | company_id=XXX | user_id=YYY | message_len=N
[PLAN_RESOLVE] plan=starter | has_boost=false | source=subscriptions
[MODEL_RESOLVE] model=google/gemma-4-26b-a4b-it | rank=RANG_A
```

---

## B1 — IDENTIFICATION PRODUIT (PRODUCT_INDEX)

### Tour 1 — Salutation générique
```
👤 CLIENT : "Bonjour"

🐍 PYTHON ATTENDU :
  - PRODUCT_INDEX injecté (max 5 produits de la boutique)
  - CATALOGUE_START/END vide (produit pas encore identifié)

📋 LOGS ATTENDUS :
[CATALOG] PRODUCT_INDEX chargé | nb_products=3 | capped_at_5=false | source=redis
[CATALOG] CATALOGUE produit injecté → NON (pas encore identifié)
[PROMPT_BUILD] product_index_chars=~300 | catalogue_chars=0

🧠 LLM THINKING ATTENDU :
<catalogue_match>
  Client demande: Salutation
  Catalogue propose: [produits listés dans PRODUCT_INDEX]
  Statut: AMBIGU
  Action: Accueillir et demander quel produit
</catalogue_match>
<detected_product>null</detected_product>
<tool_call>{"action":"NONE"}</tool_call>

🤖 BOT ATTENDU (plan Découverte/Starter) :
"Bonjour, bienvenue ! 😊
 Quel article vous intéresse aujourd'hui ?"

✅ CONTRÔLES :
- Pas de catalogue injecté (produit non identifié) ✓
- PRODUCT_INDEX présent dans prompt ✓
```

### Tour 2 — Client indique son intérêt
```
👤 CLIENT : "Je cherche des couches pour bébé"

🐍 PYTHON ATTENDU :
  - LLM identifie product_id dans <detected_product>
  - Python intercepte → charge CATALOGUE complet du produit
  - RELANCE Jessica avec CATALOGUE injecté

📋 LOGS ATTENDUS :
[XML_PARSE] product_id=prod_couches_001 détecté dans thinking
[CATALOG_SWAP] swap catalogue déclenché | old=null | new=prod_couches_001
[CATALOG] CATALOGUE produit injecté | product_id=prod_couches_001 | catalogue_chars=~800
[PROMPT_BUILD] catalogue_chars=~800 (maintenant injecté)

🧠 LLM (second appel avec catalogue) :
<catalogue_match>
  Client: couches bébé
  Catalogue: Pression T1-T6 | Culotte T3-T6
  Statut: AMBIGU (2 variantes disponibles)
  Action: Demander variante Pression ou Culotte
</catalogue_match>

🤖 BOT ATTENDU :
"Super, on a les couches en stock ! 😊
 Vous préférez les couches Pression ou les couches Culotte ?"

✅ CONTRÔLES :
- Catalogue injecté pour second appel ✓
- Question sur variante (AMBIGU) ✓
- Pas de prix encore (specs manquantes) ✓
```

---

## B2 — COLLECTE PROGRESSIVE (Jessica plan Starter / Gemma 26B)

### Tour 3 — Variante choisie
```
👤 CLIENT : "Pression"

📋 LOGS ATTENDUS :
[XML_PARSE] variant=Pression | action=UPDATE
[CART_ACTION] action=UPDATE | items_after=1

🧠 LLM ATTENDU :
<detected_items_json>[{"product_id":"prod_couches_001","variant":"Pression","spec":null,"unit":null,"qty":null}]</detected_items_json>
<tool_call>{"action":"NONE"}</tool_call>

🤖 BOT ATTENDU :
"Ok pour Pression ! 👍
 C'est pour quelle taille bébé — T1, T2, T3 ou autre ?"

✅ CONTRÔLES :
- variant=Pression enregistré ✓
- spec manquante → question taille ✓
- Pas de prix (spec manquante) ✓
```

### Tour 4 — Taille donnée
```
👤 CLIENT : "Mon bébé fait 8 kg"

🐍 PYTHON ATTENDU :
  - TECHNICAL_SPECS consulté : 7-9kg → T3
  - Auto-fill spec=T3 (1 candidate)

📋 LOG ATTENDU :
[XML_PARSE] spec=T3 | confidence=0.95 | reasoning="8kg → plage 7-9kg → T3"
[CART_ACTION] action=UPDATE | spec=T3 ajoutée

🤖 BOT ATTENDU :
"8 kg c'est la taille T3, c'est noté ! 
 Vous voulez combien de paquets ?"

✅ CONTRÔLES :
- Python déduit T3 depuis poids (pas question au client) ✓
- Une seule question : quantité ✓
```

### Tour 5 — Quantité
```
👤 CLIENT : "3 paquets"

📋 LOGS ATTENDUS :
[CART_ACTION] action=UPDATE | qty=3
[PRICE_GATE] vérification prix | specs=T3 | qty=3 | zone=null → PENDING (zone manquante)
[PRICE_CALC] EMPTY | zone manquante

🤖 BOT ATTENDU (proactif — zone + tel ensemble) :
"3 paquets T3 Pression, c'est noté ! 🎉
 Donnez-moi votre quartier et un numéro joignable, je vous envoie le total tout de suite."

✅ CONTRÔLES :
- Pas de prix inventé (zone manquante) ✓
- Zone + tel demandés ensemble (proactivité) ✓
```

### Tour 6 — Zone donnée
```
👤 CLIENT : "Yopougon Selmer, 0505050505"

🐍 PYTHON ATTENDU :
  - Zone=Yopougon Selmer → frais=1500F
  - Calcul prix Python : 3 paquets T3 × prix_unitaire + 1500F
  - <price_calculation><status>OK</status><ready_to_send>...</ready_to_send>
  - Injecté dans prompt prochain tour (ou réponse directe si <proactive_price>)

📋 LOGS ATTENDUS :
[ZONE_EXTRACT] commune=Yopougon | quartier=Selmer | cost=1500 | confidence=0.95
[PRICE_CALC] status=OK | product_subtotal=16500 | shipping=1500 | total=18000
[CART_ACTION] SET_ZONE | zone=Yopougon Selmer | tel=0505050505
[COMPLETION] rate=5/6 | manque=PAIEMENT

🤖 BOT ATTENDU (copie exacte <ready_to_send>) :
"3 paquets Couches Pression T3 → 16 500F
 + Livraison Yopougon Selmer → 1 500F
 TOTAL : 18 000F 🧾
 Comment souhaitez-vous payer : Wave ou espèces à la livraison ?"

✅ CONTRÔLES :
- Prix calculé par Python (pas LLM) ✓
- ready_to_send copié exactement ✓
- Dépôt Wave mentionné si applicable ✓
```

### Tour 7 — Paiement confirmé
```
👤 CLIENT : "Wave"

📋 LOGS ATTENDUS :
[CART_ACTION] SET_PAYMENT | method=Wave
[COMPLETION] rate=6/6 → dossier complet
[PRICE_CALC] code_confirmation=483921 généré

🤖 BOT ATTENDU (##RECAP## généré par Python) :
"Bien noté ! Voici le point de votre commande :
##RECAP##
C'est bien ça ? Répondez juste 'OUI' pour confirmer 😊"

✅ CONTRÔLES :
- ##RECAP## tag présent (Python remplace par récap complet) ✓
- Pas de montant réécrit par Jessica ✓
- Attente OUI/NON uniquement ✓
```

### Tour 8 — Confirmation OUI (sans LLM)
```
👤 CLIENT : "OUI"

🐍 PYTHON ATTENDU (short-circuit, pas de LLM) :
  - Détecte affirmation → confirme commande
  - Génère notification opérateur
  - Pas d'appel LLM

📋 LOGS ATTENDUS :
[SHORT_CIRCUIT] post-confirmation — sans LLM | affirmation=true | code=483921
[NOTIF_OPERATOR] commande confirmée | company_id=XXX

🤖 BOT ATTENDU :
"Commande confirmée ✅ Votre numéro de commande est #483921.
 Notre livreur vous contactera sur le 0505050505 pour la livraison à Yopougon Selmer. Merci ! 🙏"

✅ CONTRÔLES :
- Pas d'appel LLM (économie tokens) ✓
- Commande sauvegardée Supabase ✓
- Notification opérateur envoyée ✓
```

---

## B3 — PLAN PRO / ELITE (DeepSeek V3.2)

```
📋 LOG ATTENDU :
[MODEL_RESOLVE] model=deepseek/deepseek-v3.2 | rank=RANG_S | plan=pro | has_boost=false

✅ ATTENDU : même flux que B2 mais avec DeepSeek
⚠️ SURVEILLANCE : XML malformé possible → fuzzy parser doit récupérer
```

### B3.1 — XML malformé DeepSeek (cas réel)
```
📋 LOG ATTENDU :
[XML_PARSE] XML malformé — fuzzy parser utilisé | raw_preview="<detected_items..." | recovered=true

✅ ATTENDU : réponse correcte malgré malformation ✓
❌ PROBLÈME : si recovered=false → crash → ajouter fallback
```

### B3.2 — Gestion objection complexe (avantage Rang S)
```
👤 CLIENT : "C'est moins cher ailleurs"

🤖 BOT ATTENDU (DeepSeek Rang S — raisonnement avancé) :
"Je comprends ! Chez nous, la qualité est garantie et la livraison se fait le jour même avant 13h 😊
 Et avec 3 paquets vous bénéficiez du tarif groupé — c'est 16 500F au lieu de 19 500F à l'unité."

✅ CONTRÔLES :
- Cross-selling / argument qualité ✓
- Prix calculé par Python (pas inventé) ✓
```

---

## B4 — BOOST ACTIVÉ (Gemini 3.1 Flash Lite)

```
📋 LOG ATTENDU :
[MODEL_RESOLVE] model=google/gemini-3.1-flash-lite-preview | rank=RANG_BOOST | plan=pro | has_boost=true

✅ ATTENDU :
- Réponse < 5s (vs ~20s sans boost)
- Même qualité XML parsing
- Coût légèrement plus élevé (0.10/M input)
```

---

## B5 — PIVOT PRODUIT (swap catalogue)

```
👤 CLIENT : "Finalement je veux des couches Culotte pas Pression"

🐍 PYTHON ATTENDU :
  - LLM détecte nouveau variant dans thinking
  - Python : CLARIFY_PIVOT ou REPLACE selon intention

📋 LOG ATTENDU :
[CATALOG_SWAP] swap catalogue | old=prod_couches_001/Pression | new=prod_couches_001/Culotte
[CART_ACTION] action=REPLACE | items_before=Pression T3 x3 | items_after=Culotte (spec à confirmer)

🤖 BOT ATTENDU :
"Ok pour les Culotte ! 😊
 C'est pour quelle taille — T3 ou T4 pour 8 kg ?"

✅ CONTRÔLES :
- Ancien choix remplacé (pas cumulé) ✓
- Nouveau catalogue injecté ✓
- Question spec du nouveau produit ✓
```

---

## B6 — MULTI-PRODUITS (panier)

```
👤 CLIENT : "Je prends aussi 2 paquets T2 en plus"

🐍 PYTHON ATTENDU :
  - Intention ADD détectée (pas REPLACE)

📋 LOG ATTENDU :
[CART_ACTION] action=ADD | items_before=1 | items_after=2
[PRICE_CALC] recalcul total | items=[Pression T3 x3, Pression T2 x2]

🤖 BOT ATTENDU :
"2 paquets T2 ajoutés à votre commande 👍
 Je recalcule le total avec les deux tailles, un instant !"

✅ CONTRÔLES :
- ADD pas REPLACE ✓
- Recalcul prix Python ✓
```

---

## B7 — CLIENT AVEC IMAGE PRODUIT (multimodal)

```
👤 CLIENT : "C'est quoi ce produit ?" + [image]

🐍 PYTHON ATTENDU :
  - Image détectée → modèle override : gemini-3.1-pro-preview

📋 LOG ATTENDU :
[MODEL_RESOLVE] model=google/gemini-3.1-pro-preview | multimodal=true (override)
[LLM_CALL] modèle multimodal | image incluse dans prompt

✅ CONTRÔLES :
- Override multimodal indépendant du plan ✓
- Coût plus élevé logué ✓
```

---

# ═══════════════════════════════════════════════
# SECTION C — TIMINGS ATTENDUS PAR PLAN
# ═══════════════════════════════════════════════

```
AMANDA (tous plans — Qwen3 235B) :
  Tour 1 (cache MISS) : ~1500ms
  Tour 2+ (cache HIT) : ~800ms
  Avec image OCR      : +800ms

JESSICA Rang A (Gemma 26B) :
  Tour 1 (cache MISS) : ~8000ms
  Tour 2+ (cache HIT) : ~4000ms
  ❌ > 10s : problème provider → changer DeepInfra → Parasail

JESSICA Rang S (DeepSeek V3.2) :
  Tour 1              : ~5000ms  (cache miss Supabase)
  Tour 2+ (cache HIT) : ~3500ms  (79% cache hit DeepSeek direct)
  ✅ < 5s objectif boost

JESSICA Rang Boost (Gemini Flash Lite) :
  Tous tours          : ~2000ms
  ✅ < 5s garanti
```

---

# ═══════════════════════════════════════════════
# SECTION D — TABLEAU DE BORD VÉRIFICATION RAPIDE
# ═══════════════════════════════════════════════

```bash
# 1. Amanda répond ?
curl -X POST http://localhost:8002/amandabotlive \
  -H "Content-Type: application/json" \
  -d '{"company_id":"XXX","user_id":"test_001","message":"Bonjour","images":[]}'
# ATTENDU : {"response":"...","model":"qwen/qwen3-235b-a22b-2507","plan":"starter"}

# 2. Jessica répond avec bon modèle ?
curl -X POST http://localhost:8002/jessicaragbot \
  -d '{"company_id":"XXX","user_id":"test_002","message":"Bonjour"}'
# ATTENDU Starter : {"model":"google/gemma-4-26b-a4b-it","rank":"RANG_A"}
# ATTENDU Pro     : {"model":"deepseek/deepseek-v3.2","rank":"RANG_S"}
# ATTENDU Boost   : {"model":"google/gemini-3.1-flash-lite-preview","rank":"RANG_BOOST"}

# 3. Coût non nul ?
docker compose logs zeta-backend | grep "cost_usd" | tail -5
# ATTENDU : cost_usd=0.00XXXX (pas 0.000000)

# 4. Cache tokens non nuls après tour 2 ?
docker compose logs zeta-backend | grep "cached_tokens" | tail -5
# ATTENDU tour 2+ : cached_tokens=XXXX (pas 0)

# 5. Guardian actif ?
docker compose logs zeta-backend | grep "GUARDIAN.*verdict" | tail -5

# 6. Dossier Amanda complet déclenche notification ?
docker compose logs zeta-backend | grep "NOTIF_OPERATOR"
```

---

# ═══════════════════════════════════════════════
# SECTION E — MATRICE COMPLÈTE CAS × PLANS
# ═══════════════════════════════════════════════

| Cas | Découverte | Starter | Pro | Elite | Boost |
|---|---|---|---|---|---|
| Amanda actif | ✅ | ✅ | ✅ | ✅ | = |
| Jessica actif | ✅ (1 bot au choix) | ✅ | ✅ | ✅ | = |
| Les deux bots | ❌ | ✅ | ✅ | ✅ | = |
| Modèle Amanda | Qwen3 | Qwen3 | Qwen3 | Qwen3 | Qwen3 |
| Modèle Jessica | Gemma 26B | Gemma 26B | DeepSeek | DeepSeek | Flash Lite |
| Vision OCR | Flash Lite | Flash Lite | Flash Lite | Flash Lite | Flash Lite |
| Vision Paiement | Gemini Pro | Gemini Pro | Gemini Pro | Gemini Pro | Gemini Pro |
| Quota msgs | 300 | 1500 | 5000 | 10000 | +quota |
| Recharge | Non | 5F/msg | 3F/msg | 2F/msg | = |
| Vitesse | < 12s | < 12s | ~20s base | ~20s base | < 5s |
| Zeta Insight | ❌ | Basique | PRO mensuel | ELITE 15j | = |
| Commission | 0% | 1.5% | 1.0% | 0% | = |