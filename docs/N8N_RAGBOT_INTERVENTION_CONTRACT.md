# Contrat N8N — Branchement RAGBot sur le système d'intervention

## Contexte

RAGBot (`POST /chat`) ne détecte aucune intervention aujourd'hui.
BotLive a son propre moteur inline + Guardian.
Un endpoint partagé existe : `POST /botliveandrag/check-intervention`.

Ce document définit le contrat exact pour que N8N appelle cet endpoint
après chaque réponse RAGBot, unifiant ainsi la détection.

---

## Architecture cible

```
Client WhatsApp
    │
    ▼
N8N Workflow "ragbot-message"
    │
    ├─1─► POST /chat  (RAGBot)
    │     ← { status, response }
    │
    ├─2─► POST /botliveandrag/check-intervention
    │     ← { requires_intervention, type, priority, ... }
    │
    ├─3─► IF requires_intervention == true
    │     │
    │     ├── (optionnel) POST Supabase upsert_required_intervention
    │     └── Notifier opérateur (push / webhook)
    │
    └─4─► Envoyer response au client (WhatsApp Cloud API)
```

---

## Étape 1 — Appel RAGBot (déjà en place)

**Method:** `POST`
**URL:** `https://<BACKEND_URL>/chat`

### Request body
```json
{
  "company_id": "{{company_id}}",
  "user_id": "{{user_phone}}",
  "message": "{{user_message}}",
  "conversation_history": "",
  "images": []
}
```

### Response
```json
{
  "status": "success",
  "response": "Bonjour ! Comment puis-je vous aider ?"
}
```

Stocker `response` dans une variable N8N `{{rag_response}}`.

---

## Étape 2 — Appel check-intervention (NOUVEAU)

**Method:** `POST`
**URL:** `https://<BACKEND_URL>/botliveandrag/check-intervention`

### Request body
```json
{
  "company_id": "{{company_id}}",
  "user_id": "{{user_phone}}",
  "user_message": "{{user_message}}",
  "bot_response": "{{rag_response}}",
  "conversation_history": "",
  "order_state": {},
  "next_step": "",
  "source": "ragbot",
  "log_intervention": true,
  "channel": "whatsapp"
}
```

### Champs obligatoires
| Champ | Type | Description |
|-------|------|-------------|
| `company_id` | string | ID texte entreprise |
| `user_id` | string | Numéro WhatsApp client |
| `user_message` | string | Dernier message du client |

### Champs recommandés
| Champ | Type | Description |
|-------|------|-------------|
| `bot_response` | string | Réponse RAGBot (étape 1) |
| `source` | string | Toujours `"ragbot"` |
| `log_intervention` | bool | `true` pour persister |
| `channel` | string | `"whatsapp"` |

### Champs optionnels
| Champ | Type | Description |
|-------|------|-------------|
| `conversation_history` | string | Historique sérialisé |
| `order_state` | object | État commande (vide si RAG pur) |
| `next_step` | string | Étape courante (vide si RAG pur) |

### Response
```json
{
  "requires_intervention": true,
  "priority": "high",
  "category": "explicit_handoff",
  "reason": "explicit_handoff",
  "detected_by": "rule_based",
  "confidence": null,
  "caps_ratio": 0.0,
  "explicit_handoff": true,
  "is_frustrated": false,
  "source": "ragbot"
}
```

---

## Étape 3 — Branchement conditionnel

### Condition N8N (IF node)
```
{{$json.requires_intervention}} == true
```

### Branche TRUE — intervention détectée

Actions possibles (au choix selon maturité) :

**V1 simple** : ne rien faire de plus, le log est déjà persisté
dans `conversation_logs` par le backend (grâce à `log_intervention: true`).
Le frontend Interventions lit déjà cette table.

**V2 avec table dédiée** : appeler la RPC Supabase pour insérer
dans `required_interventions` :

```
POST https://<SUPABASE_URL>/rest/v1/rpc/upsert_required_intervention
Headers:
  apikey: <SUPABASE_SERVICE_KEY>
  Authorization: Bearer <SUPABASE_SERVICE_KEY>
  Content-Type: application/json

Body:
{
  "p_company_id": "{{company_id}}",
  "p_user_id": "{{user_phone}}",
  "p_channel": "whatsapp",
  "p_type": "{{$json.category}}",
  "p_priority": "{{$json.priority}}",
  "p_detected_by": "{{$json.detected_by}}",
  "p_source_bot": "ragbot",
  "p_confidence": {{$json.confidence}},
  "p_reason": "{{$json.reason}}",
  "p_signals": {
    "caps_ratio": {{$json.caps_ratio}},
    "explicit_handoff": {{$json.explicit_handoff}},
    "is_frustrated": {{$json.is_frustrated}}
  },
  "p_user_message": "{{user_message}}",
  "p_bot_response": "{{rag_response}}"
}
```

### Branche FALSE — pas d'intervention
Continuer normalement (envoyer la réponse au client).

---

## Étape 4 — Envoyer la réponse au client

Indépendant du résultat intervention : toujours envoyer
`{{rag_response}}` au client via WhatsApp Cloud API.

L'intervention ne bloque pas la réponse bot (sauf si
`explicit_handoff` et que la politique métier dit de stopper le bot).

---

## Résumé du workflow N8N

```
[Webhook WhatsApp entrant]
        │
        ▼
[HTTP Request: POST /chat]
        │
        ▼
[HTTP Request: POST /botliveandrag/check-intervention]
        │
        ▼
[IF: requires_intervention == true]
   ├── TRUE  → [Supabase RPC upsert_required_intervention] (V2)
   │          → [Push notification opérateur] (optionnel)
   └── FALSE → (rien)
        │
        ▼
[HTTP Request: WhatsApp Cloud API send_text]
```

---

## Variables N8N à configurer

| Variable | Valeur |
|----------|--------|
| `BACKEND_URL` | `http://194.60.201.228:8002` (VPS) |
| `SUPABASE_URL` | URL Supabase du projet |
| `SUPABASE_SERVICE_KEY` | Clé service Supabase |
| `WHATSAPP_TOKEN` | Token Meta WhatsApp Cloud API |
| `WHATSAPP_PHONE_NUMBER_ID` | ID numéro WhatsApp Business |

---

## Notes d'implémentation

1. L'appel check-intervention ajoute ~200-500ms de latence (rule-based instantané, Guardian LLM si activé ~300ms).
2. Pour minimiser la latence perçue, les étapes 2 et 4 peuvent être parallélisées dans N8N (envoyer la réponse en même temps que le check).
3. Le champ `log_intervention: true` fait que le backend persiste automatiquement dans `conversation_logs`. Pas besoin de double écriture en V1.
4. En V2 (table `required_interventions`), le backend pourra écrire directement dans la table, rendant l'étape Supabase RPC de N8N optionnelle.
