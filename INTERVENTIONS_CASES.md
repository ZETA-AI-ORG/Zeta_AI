# Cas d'interventions requises (backend Botlive → conversation_logs)

Ce fichier documente **tous les cas** où le backend Botlive doit marquer une conversation
comme nécessitant une intervention humaine, en écrivant dans `conversation_logs`
avec un `metadata` du type :

```json
{
  "needs_intervention": true,
  "priority": "high",
  "reason": "…",
  "detected_by": "…",
  "detected_at": "2025-11-21T18:50:00Z"
}
```

Le frontend (`useConversationLogsInterventions`) affiche ensuite ces conversations
sur la page **Interventions requises**.

---

## 1. Escalade Guardian (qualité / compliance)

**Source code :** `core/intelligent_guardian_escalation.py`

- Classe : `IntelligentGuardianWithEscalation`
- Méthode : `evaluate_with_escalation(...)`
- Signal :
  - `decision.action == "ESCALATE_TO_HUMAN"` **ou**
  - `decision.requires_human_intervention == True`

**Quand déclencher :**

- L'IA n'arrive plus à répondre de façon acceptable malgré plusieurs tentatives
- Question hors périmètre / à risque pour l'entreprise

**Écriture recommandée dans `conversation_logs` :**

- `direction` : `"system"`
- `channel` : `"botlive"`
- `message` : texte court expliquant l'escalade (optionnel)
- `metadata` :

```json
{
  "needs_intervention": true,
  "priority": "high",
  "reason": "guardian_escalation",
  "guardian_reason": "<guardian_decision.reason>",
  "detected_by": "guardian_escalation_v1",
  "detected_at": "<timestamp ISO>"
}
```

À brancher **là où** on traite la décision Guardian, en passant `company_id_text`
+ `user_id` à un helper d'écriture dans `conversation_logs`.

---

## 2. Commande bloquée / paiement manquant

**Source code :** `core/botlive_dashboard_data.py`

- Fonctions :
  - `get_active_orders(company_id, limit)`
  - `get_interventions_required(company_id)`
  - `_detect_order_issues(order)`

`_detect_order_issues(order)` renvoie actuellement des issues de type :

- `"stuck_order"` : commande bloquée > 30 min avec `completion_rate < 100`.
- `"payment_missing"` : produit ✅ mais paiement ❌.

**Quand déclencher :**

- Dans `get_interventions_required`, juste après :

```py
issues = _detect_order_issues(order)
for issue in issues:
    ...
```

**Écriture recommandée dans `conversation_logs` :**

- `direction` : `"system"`
- `channel` : `"botlive"`
- `user_id` : `order["user_id"]`
- `message` : par ex. `"[INTERVENTION_REQUISE] " + issue["message"]`
- `metadata` :

```json
{
  "needs_intervention": true,
  "priority": "high",
  "reason": "stuck_order" | "payment_missing",
  "completion_rate": 42,
  "detected_by": "order_issues_v1",
  "detected_at": "<timestamp ISO>"
}
```

**Remarque :** ici il faudra résoudre correctement `company_id_text` à partir
de l'UUID stocké dans `orders`/`conversations` (mapping via `company_mapping`).

---

## 3. Boucle Botlive bloquée (4/4 jamais collecté)

**Source code :** `core/loop_botlive_engine.py`

- Classe : `LoopBotliveEngine`
- Méthode principale : `process_message(...)`
- Méthodes internes : `_check_completion(state)`, `_detect_trigger(...)`.

Dans les logs de test (`tests/botlive_micro.py`) on a observé :

- Plusieurs tours consécutifs pour le même `user_id`.
- Images Facebook retournant 403 (vision/OCR cassé).
- `_check_completion` loggue toujours `0/4 collectés`.
- LLM continue de guider (`source="llm_guide"`), mais la checklist reste bloquée.

**Heuristique proposée :**

- Maintenir un compteur interne par `user_id` de "tours sans progrès"
  (par ex. nombre de messages consécutifs où `photo/paiement/zone/tel` ne bougent pas).
- Si `tours_sans_progres >= 2 ou 3` **ET** au moins une erreur technique a été
  rencontrée (ex: erreurs 403 vision/ocr loggées) **ET** `0/4 collectés` ou
  `1/4 collecté` depuis un certain temps → lever une intervention.

**Écriture recommandée dans `conversation_logs` :**

- `direction` : `"system"`
- `channel` : `"botlive"`
- `message` : par ex. `"[INTERVENTION_REQUISE] Flux bloqué (vision/OCR)"`
- `metadata` :

```json
{
  "needs_intervention": true,
  "priority": "high",
  "reason": "technical_block",
  "missing": {
    "photo": true,
    "paiement": true,
    "zone": true,
    "tel": true
  },
  "detected_by": "loop_botlive_engine_v1",
  "detected_at": "<timestamp ISO>",
  "attempts_without_progress": 3
}
```

À brancher juste après l'appel à `_check_completion(state)`
dans `process_message(...)`, en ajoutant une condition sur l'état + compteur.

---

## 4. (Placeholder) Prise en charge manuelle (take-over)

**Endpoints existants :** `routes/botlive.py`

- `POST /botlive/interventions/{conversation_id}/take-over`
- `POST /botlive/interventions/{conversation_id}/resolve`

Ces endpoints mettent à jour la table `conversations` (`priority`, `status`).

**Évolution possible :**

- Lorsqu'un opérateur clique "Prendre en charge" dans le dashboard,
  en plus de mettre `priority="high"` dans `conversations`,
  on pourrait aussi écrire un `conversation_logs` avec :

```json
{
  "needs_intervention": true,
  "priority": "high",
  "reason": "manual_takeover",
  "taken_by": "<operator_id>",
  "detected_by": "human_dashboard",
  "detected_at": "<timestamp ISO>"
}
```

Ce cas reste à préciser et pourra être enrichi lors de futurs tests.

---

## 5. Cas succès 4/4 (aucune intervention requise)

**Source de test :** `tests/botlive_client_direct.py`

Scénario observé dans les logs :

- 6 étapes, client direct (salutation → produit → paiement → zone → téléphone → confirmation).
- Collecte progressive des 4 éléments :
  - Étape 1 : `0/4` → LLM guide.
  - Étape 2 : `1/4` (photo=True).
  - Étape 3 : `2/4` (photo+paiement=True, paiement OCR=2020F).
  - Étape 4 : `3/4` (zone=Cocody, frais=1500F, délai=demain).
  - Étape 5 : `4/4` (téléphone valide, 10 chiffres).
- `_check_completion` déclenche alors le récapitulatif final Python automatique :

```text
✅PARFAIT Commande confirmée 😊
Livraison prévue demain, acompte de 2020 F déjà versé.
Nous vous rappellerons bientôt pour les détails et le coût total.
Veuillez ne pas répondre à ce message.
```

À **ne pas** marquer comme intervention requise, car :

- Tous les signaux de collecte sont au vert (`photo`, `paiement`, `zone`, `tel`).
- La commande est confirmée automatiquement par le moteur Python.
- Le client reçoit un message de clôture clair.

**Règle métier :**

- Si `_check_completion` retourne `SEND_FINAL_RECAP` → **aucune écriture** `needs_intervention:true`
  dans `conversation_logs` pour ce message final.
- Ces cas doivent apparaître dans le dashboard comme **commandes terminées**, pas comme interventions.

---

## TODO / À enrichir par les tests

- [ ] Ajouter les cas déclenchés par le système Guardian dans les logs réels.
- [ ] Observer des scénarios de commandes réellement bloquées (paiement manquant, délais).
- [ ] Définir un seuil précis pour les "tours sans progrès" dans LoopBotliveEngine.
- [ ] Documenter l'intégration avec `conversation_logs` côté N8N (complément possible).
