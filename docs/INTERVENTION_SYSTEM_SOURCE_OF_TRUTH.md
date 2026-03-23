# Système d'intervention

## Ordre
1. Types
2. Critères
3. Signaux
4. Déclencheurs
5. Payload standard
6. Source de vérité
7. Statuts
8. BotLive + RAGBot
9. API
10. UI

## Essence des bots

### BotLive — Tunnel transactionnel
- Collecte 4 éléments (photo, paiement, zone, téléphone) pour créer une commande
- Flow linéaire strict, WhatsApp only
- Si ça plante : client en milieu d'achat = vente perdue immédiatement

### RAGBot — Assistant connaissance + vente conversationnelle
- Répond aux questions produits/prix/livraison, construit un panier
- Conversation libre, WhatsApp + Web
- Si ça plante : client sans réponse = départ silencieux

### Conséquence pour l'opérateur
L'opérateur veut être dérangé UNIQUEMENT quand le bot ne suffit plus.
Chaque notification doit valoir le dérangement sinon il les ignore toutes.

## Types (classés par urgence × impact business)

### CRITIQUE — répondre < 2 min
1. `system_error` : backend crash, client abandonné sans réponse (BotLive + RAGBot)
2. `explicit_handoff` : client demande un humain, attend activement (BotLive + RAGBot)
3. `customer_frustration` : colère, insultes, menaces, chaque minute aggrave (BotLive + RAGBot)

### HAUT — répondre < 10 min
4. `payment_issue` : argent en jeu, client pense être arnaqué si ignoré (BotLive)
5. `order_blocked` : client prêt à payer mais tunnel bloqué (BotLive)
6. `bot_confusion` : bot tourne en rond, expérience dégradée (BotLive + RAGBot)

### MOYEN — traiter dans l'heure
7. `sav_issue` : problème sur commande existante, seul l'humain peut résoudre (BotLive + RAGBot)
8. `post_order_followup` : message après commande, peut être modification ou merci (BotLive)

### BAS — consulter quand disponible
9. `technical_issue` : OCR/média/API raté, fallback système existe (BotLive + RAGBot)
10. `vip_or_sensitive_case` : cas commercial sensible, dépend des règles métier (BotLive + RAGBot)

## Critères
- `system_error` : exception backend, timeout fatal, client sans réponse.
- `explicit_handoff` : demande explicite d'un humain, agent, conseiller.
- `customer_frustration` : colère, agressivité, forte insatisfaction, majuscules.
- `payment_issue` : paiement ambigu, refusé, montant incohérent, OCR échoué.
- `order_blocked` : commande bloquée sans progression malgré plusieurs échanges.
- `bot_confusion` : réponses répétitives, incohérentes, hors sujet.
- `sav_issue` : suivi, réclamation, retour, remboursement, retard.
- `post_order_followup` : message après commande complétée ou récap final.
- `technical_issue` : bug OCR, média, API, parsing, timeout non fatal.
- `vip_or_sensitive_case` : priorité métier, client sensible, cas commercial.

## Signaux
- textuels : mots-clés, tonalité, insultes, majuscules
- conversationnels : répétition, absence de progression
- métier : SAV, paiement, commande bloquée, post-commande
- techniques : OCR, API, parsing, media, timeout, exception

## Déclencheurs
- couche 1 : règles dures
- couche 2 : règles métier
- couche 3 : Guardian LLM

Les règles dures priment. Le Guardian complète seulement les cas ambigus.

## Payload standard
- `requires_intervention`
- `type`
- `priority`
- `reason`
- `detected_by`
- `source_bot`
- `channel`
- `signals`

## Source de vérité
- décision : backend partagé
- orchestration : N8N
- affichage : frontend
- persistance cible : table métier dédiée `required_interventions`
- `conversation_logs` reste un journal, pas la source métier finale

## Statuts et cycle de vie
- `open`
- `acknowledged`
- `in_progress`
- `resolved`
- `dismissed`
- `reopened`

Une intervention doit pouvoir être créée, assignée, traitée, fermée, puis réouverte si un nouveau signal important apparaît.

## BotLive + RAGBot
- BotLive doit appeler le moteur partagé
- RAGBot doit appeler le même moteur via API
- le frontend ne doit afficher que les objets issus de cette source commune

## API minimale cible
- `POST /botliveandrag/check-intervention`
- `GET /interventions`
- `GET /interventions/:id`
- `PATCH /interventions/:id`
- `POST /interventions/:id/reply`

## UI minimale cible
- liste des interventions ouvertes
- priorité, type, raison courte
- derniers messages
- assignation
- réponse rapide
- résolution / fermeture

## Plan d'implémentation recommandé
1. figer la taxonomie des types
2. figer les critères et signaux
3. figer les déclencheurs
4. figer le payload standard
5. créer la vraie source de vérité métier
6. brancher BotLive et RAGBot sur le moteur partagé
7. brancher l'UI et les actions opérateur
