# 📡 API BOTLIVE - Documentation pour N8N & Frontend

## 🎯 Vue d'ensemble

L'API Botlive permet d'intégrer le système de commandes en direct avec :
- **Frontend** : Interface utilisateur temps réel
- **N8N** : Orchestration WhatsApp/Messenger/autres canaux
- **Webhooks** : Notifications événements temps réel

**Base URL** : `http://localhost:8000/botlive`

---

## 🔥 Endpoints Principaux

### 1. POST `/botlive/message`
**Traiter un message utilisateur (texte + images)**

#### Request Body
```json
{
  "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb",
  "user_id": "+225XXXXXXXXX",
  "message": "Je veux commander",
  "images": [
    "https://example.com/image1.jpg"
  ],
  "conversation_history": "User: Bonjour\nBot: Bonjour! ..."
}
```

#### Response
```json
{
  "success": true,
  "response": "Photo reçue ! Dépôt: 2000 FCFA",
  "order_status": {
    "produit": "✅PRODUIT:lingettes[VISION]",
    "paiement": "",
    "zone": "",
    "numero": "",
    "completion_rate": 25,
    "is_complete": false
  },
  "next_step": "paiement",
  "duration_ms": 1234,
  "request_id": "abc123"
}
```

#### Utilisation N8N
```javascript
// Node HTTP Request
{
  "method": "POST",
  "url": "http://localhost:8000/botlive/message",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "company_id": "{{$json.company_id}}",
    "user_id": "{{$json.from}}",
    "message": "{{$json.text}}",
    "images": "{{$json.media_urls}}"
  }
}
```

---

### 2. POST `/botlive/message/stream`
**Réponse en streaming (SSE) pour UX temps réel**

#### Request Body
Identique à `/botlive/message`

#### Response (Server-Sent Events)
```
data: {"event": "start", "request_id": "abc123"}

data: {"event": "token", "content": "Photo "}
data: {"event": "token", "content": "reçue "}
data: {"event": "token", "content": "! "}

data: {"event": "done", "order_status": {...}, "next_step": "paiement"}
```

#### Utilisation Frontend (JavaScript)
```javascript
const eventSource = new EventSource('/botlive/message/stream', {
  method: 'POST',
  body: JSON.stringify({
    company_id: 'xxx',
    user_id: '+225xxx',
    message: 'Bonjour'
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'token') {
    // Afficher progressivement
    appendToChat(data.content);
  } else if (data.event === 'done') {
    // Mise à jour UI finale
    updateOrderStatus(data.order_status);
  }
};
```

---

## 📊 Endpoints Statistiques

### 3. GET `/botlive/stats/{company_id}`
**Statistiques Mode LIVE**

#### Query Parameters
- `time_range` : `today` | `week` | `month` (défaut: `today`)

#### Response
```json
{
  "ca_live_session": 1247.0,
  "ca_variation": "+23%",
  "commandes_total": 34,
  "commandes_variation": "+12",
  "clients_actifs": 156,
  "interventions_requises": 2,
  "time_range": "today",
  "updated_at": "2025-10-22T09:00:00Z"
}
```

#### Utilisation Frontend
```javascript
// Polling toutes les 10 secondes
setInterval(async () => {
  const stats = await fetch('/botlive/stats/4OS4yFcf2LZwxhKojbAVbKuVuSdb?time_range=today')
    .then(r => r.json());
  
  updateDashboard(stats);
}, 10000);
```

---

### 4. GET `/botlive/orders/active/{company_id}`
**Liste des commandes actives**

#### Query Parameters
- `limit` : Nombre max de commandes (défaut: 50)

#### Response
```json
{
  "success": true,
  "orders": [
    {
      "user_id": "+225XXXXXXXXX",
      "user_name": "Sophie Laurent",
      "produit": "1x Produit A",
      "paiement": "2020 FCFA",
      "zone": "Yopougon",
      "numero": "07XXXXXXXX",
      "completion_rate": 75,
      "created_at": "2025-10-22T08:45:00Z"
    }
  ],
  "total": 1
}
```

---

### 5. GET `/botlive/interventions/{company_id}`
**Interventions requises (alertes)**

#### Response
```json
{
  "success": true,
  "interventions": [
    {
      "user_id": "+225XXXXXXXXX",
      "type": "payment_issue",
      "message": "Montant insuffisant détecté",
      "order_status": {...},
      "created_at": "2025-10-22T08:50:00Z"
    }
  ],
  "count": 1
}
```

---

### 6. GET `/botlive/activity/{company_id}`
**Activité temps réel**

#### Query Parameters
- `limit` : Nombre max d'événements (défaut: 10)

#### Response
```json
{
  "success": true,
  "activities": [
    {
      "type": "commande_enregistree",
      "client": "Sophie Laurent",
      "produit": "1x Produit A",
      "timestamp": "il y a 2 min"
    },
    {
      "type": "paiement_en_cours",
      "client": "Thomas Petit",
      "timestamp": "il y a 5 min"
    }
  ]
}
```

---

## 🔗 Endpoints Webhooks N8N

### 7. POST `/botlive/webhook/register`
**Enregistrer un webhook**

#### Request Body
```json
{
  "webhook_url": "https://n8n.example.com/webhook/botlive",
  "events": [
    "order_completed",
    "payment_validated",
    "intervention_required"
  ],
  "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
}
```

#### Response
```json
{
  "success": true,
  "message": "Webhook enregistré",
  "config": {...}
}
```

---

### 8. POST `/botlive/webhook/test`
**Tester un webhook**

#### Query Parameters
- `webhook_url` : URL du webhook à tester

#### Response
```json
{
  "success": true,
  "status_code": 200,
  "response": "OK"
}
```

---

## 🔧 Endpoints Admin

### 9. POST `/botlive/admin/clear-state/{user_id}`
**Réinitialiser l'état d'une commande**

#### Response
```json
{
  "success": true,
  "message": "État réinitialisé pour +225XXXXXXXXX"
}
```

---

### 10. GET `/botlive/health`
**Health check**

#### Response
```json
{
  "status": "healthy",
  "engine": "initialized",
  "timestamp": "2025-10-22T09:00:00Z"
}
```

---

## 🌊 Événements Webhook

Lorsqu'un événement se produit, le backend envoie une requête POST au webhook enregistré :

### Event: `order_completed`
```json
{
  "event": "order_completed",
  "timestamp": "2025-10-22T09:00:00Z",
  "data": {
    "user_id": "+225XXXXXXXXX",
    "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb",
    "order_status": {
      "produit": "✅PRODUIT:lingettes[VISION]",
      "paiement": "✅PAIEMENT:2020 FCFA[TRANSACTIONS]",
      "zone": "✅ZONE:Yopougon-1500 FCFA[MESSAGE]",
      "numero": "✅NUMÉRO:0709876543[MESSAGE]",
      "completion_rate": 100,
      "is_complete": true
    }
  }
}
```

### Event: `payment_validated`
```json
{
  "event": "payment_validated",
  "timestamp": "2025-10-22T08:55:00Z",
  "data": {
    "user_id": "+225XXXXXXXXX",
    "amount": 2020,
    "currency": "FCFA",
    "reference": "WAVE-ABC123"
  }
}
```

### Event: `intervention_required`
```json
{
  "event": "intervention_required",
  "timestamp": "2025-10-22T08:50:00Z",
  "data": {
    "user_id": "+225XXXXXXXXX",
    "type": "payment_issue",
    "message": "Montant insuffisant: 1500 FCFA reçu, 2000 FCFA requis"
  }
}
```

---

## 🛠️ Configuration N8N

### Workflow Type 1: WhatsApp → Botlive → WhatsApp

```
[WhatsApp Trigger]
    ↓
[HTTP Request: /botlive/message]
    ↓
[IF: next_step == "completed"]
    ↓ YES
    [Envoyer confirmation WhatsApp]
    ↓ NO
    [Envoyer réponse bot WhatsApp]
```

### Workflow Type 2: Webhook Listener

```
[Webhook Trigger: /webhook/botlive]
    ↓
[Switch: event type]
    ├─ order_completed → [Notifier admin]
    ├─ payment_validated → [Mettre à jour CRM]
    └─ intervention_required → [Alerte Slack]
```

---

## 🔐 Sécurité

### Rate Limiting
- `/botlive/message` : 300 req/min par IP
- `/botlive/stats` : 60 req/min par IP

### CORS
- Autorisé pour tous les domaines en développement
- À restreindre en production

### Authentification
- **TODO** : Ajouter API Key dans headers
- **TODO** : JWT pour webhooks

---

## 📈 Monitoring

### Logs
Tous les appels sont loggés dans `logs/server/` avec :
- Request ID unique
- Durée de traitement
- Erreurs détaillées

### Métriques Prometheus
- `botlive_requests_total`
- `botlive_response_time_seconds`
- `botlive_errors_total`

---

## 🧪 Tests

### Test avec cURL

```bash
# Test message simple
curl -X POST http://localhost:8000/botlive/message \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb",
    "user_id": "+225XXXXXXXXX",
    "message": "Bonjour"
  }'

# Test avec image
curl -X POST http://localhost:8000/botlive/message \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "4OS4yFcf2LZwxhKojbAVbKuVuSdb",
    "user_id": "+225XXXXXXXXX",
    "message": "",
    "images": ["https://example.com/product.jpg"]
  }'

# Test stats
curl http://localhost:8000/botlive/stats/4OS4yFcf2LZwxhKojbAVbKuVuSdb?time_range=today

# Test health
curl http://localhost:8000/botlive/health
```

---

## 🚀 Démarrage Rapide

### 1. Démarrer le serveur
```bash
cd "c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0"
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Vérifier le health check
```bash
curl http://localhost:8000/botlive/health
```

### 3. Tester un message
```bash
curl -X POST http://localhost:8000/botlive/message \
  -H "Content-Type: application/json" \
  -d '{"company_id":"4OS4yFcf2LZwxhKojbAVbKuVuSdb","user_id":"test","message":"Bonjour"}'
```

---

## 📞 Support

Pour toute question ou problème :
- **Logs** : `logs/server/`
- **Monitoring** : `http://localhost:8000/dashboard`
- **Docs API** : `http://localhost:8000/docs` (Swagger UI)

---

**Version** : 1.0.0  
**Dernière mise à jour** : 22 octobre 2025
