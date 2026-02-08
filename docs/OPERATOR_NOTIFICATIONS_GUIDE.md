# Guide d'intégration Frontend — Notifications Opérateur

## Contexte

Quand une commande est **validée + payée**, Jessica (le bot) se désactive automatiquement pour cet utilisateur.  
Tous les messages suivants du client sont **routés vers l'opérateur humain** via un système de notifications.

---

## Architecture

```
Client envoie message
       │
       ▼
  POST /chat
       │
       ├── bot_disabled = true ?
       │       │
       │       ▼  OUI
       │   ┌──────────────────────────────┐
       │   │ 1. Sauvegarde message (conv)  │
       │   │ 2. INSERT operator_notifications│
       │   │ 3. Retourne réponse courte    │
       │   └──────────────────────────────┘
       │
       └── bot_disabled = false ?
               │
               ▼  NON → Jessica LLM normal
```

---

## Table Supabase

```sql
-- Exécuter dans Supabase SQL Editor
-- Fichier: migrations/create_operator_notifications.sql
```

| Colonne        | Type        | Description                                |
|----------------|-------------|--------------------------------------------|
| id             | UUID        | Identifiant unique (auto-généré)           |
| company_id     | TEXT        | ID de l'entreprise                         |
| user_id        | TEXT        | ID du client                               |
| message        | TEXT        | Message du client                          |
| message_type   | TEXT        | `post_order` (défaut)                      |
| order_summary  | JSONB       | Résumé commande (produit, qty, zone, etc.) |
| read           | BOOLEAN     | `false` = non lu par l'opérateur           |
| created_at     | TIMESTAMPTZ | Horodatage                                 |

---

## Endpoints Backend

### 1. `GET /api/notifications/{company_id}`

Récupère les notifications non lues pour l'entreprise.

```typescript
// Polling toutes les 10s
const fetchNotifications = async () => {
  const res = await fetch(
    `${API_URL}/api/notifications/${companyId}?unread_only=true&limit=50`
  );
  const data = await res.json();
  // data = { notifications: [...], count: 5 }
  return data;
};
```

**Réponse type :**
```json
{
  "notifications": [
    {
      "id": "a1b2c3d4-...",
      "company_id": "W27PwOPi...",
      "user_id": "client_phone_123",
      "message": "Bonjour, ma livraison arrive quand ?",
      "message_type": "post_order",
      "order_summary": {
        "produit": "Pression",
        "produit_details": "T1",
        "quantite": "1 lot",
        "zone": "Yopougon",
        "numero": "0787360757",
        "paiement": "validé_2000F"
      },
      "read": false,
      "created_at": "2026-02-08T15:30:00Z"
    }
  ],
  "count": 1
}
```

---

### 2. `POST /api/notifications/{company_id}/read_all`

Marquer toutes les notifications d'un client comme lues (quand l'opérateur ouvre la conversation).

```typescript
const markAllRead = async (userId: string) => {
  await fetch(`${API_URL}/api/notifications/${companyId}/read_all`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
};
```

---

### 3. `PATCH /api/notifications/read`

Marquer une seule notification comme lue.

```typescript
const markOneRead = async (notificationId: string) => {
  await fetch(`${API_URL}/api/notifications/read`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notification_id: notificationId }),
  });
};
```

---

### 4. `POST /api/bot/reactivate`

Réactiver Jessica pour un client (ex: nouvelle commande).

```typescript
const reactivateBot = async (userId: string) => {
  const res = await fetch(`${API_URL}/api/bot/reactivate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId, user_id: userId }),
  });
  // { success: true, user_id: "...", bot_disabled: false }
};
```

---

## Intégration React (exemple)

### Hook `useOperatorNotifications`

```typescript
import { useState, useEffect, useCallback } from "react";

interface Notification {
  id: string;
  company_id: string;
  user_id: string;
  message: string;
  message_type: string;
  order_summary: Record<string, string>;
  read: boolean;
  created_at: string;
}

export function useOperatorNotifications(companyId: string, pollInterval = 10000) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifs = useCallback(async () => {
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/api/notifications/${companyId}?unread_only=true`
      );
      if (!res.ok) return;
      const data = await res.json();
      setNotifications(data.notifications || []);
      setUnreadCount(data.count || 0);
    } catch (err) {
      console.error("Notification fetch error:", err);
    }
  }, [companyId]);

  useEffect(() => {
    fetchNotifs();
    const interval = setInterval(fetchNotifs, pollInterval);
    return () => clearInterval(interval);
  }, [fetchNotifs, pollInterval]);

  const markAllRead = async (userId: string) => {
    await fetch(
      `${import.meta.env.VITE_API_URL}/api/notifications/${companyId}/read_all`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      }
    );
    fetchNotifs();
  };

  const reactivateBot = async (userId: string) => {
    await fetch(`${import.meta.env.VITE_API_URL}/api/bot/reactivate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: companyId, user_id: userId }),
    });
  };

  return { notifications, unreadCount, markAllRead, reactivateBot, refresh: fetchNotifs };
}
```

### Composant Badge de notification

```tsx
function NotificationBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
      {count > 99 ? "99+" : count}
    </span>
  );
}
```

### Composant Liste de notifications

```tsx
function NotificationList({ companyId }: { companyId: string }) {
  const { notifications, markAllRead, reactivateBot } =
    useOperatorNotifications(companyId);

  return (
    <div className="space-y-3">
      {notifications.map((n) => (
        <div key={n.id} className="p-4 bg-white rounded-lg shadow border-l-4 border-orange-500">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm text-gray-500">Client: {n.user_id}</p>
              <p className="mt-1 font-medium">{n.message}</p>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(n.created_at).toLocaleString("fr-FR")}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => markAllRead(n.user_id)}
                className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded"
              >
                Marquer lu
              </button>
              <button
                onClick={() => reactivateBot(n.user_id)}
                className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded"
              >
                Réactiver bot
              </button>
            </div>
          </div>
          {n.order_summary && Object.keys(n.order_summary).length > 0 && (
            <div className="mt-2 text-xs bg-gray-50 p-2 rounded">
              <strong>Commande:</strong>{" "}
              {Object.entries(n.order_summary)
                .filter(([, v]) => v)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" | ")}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## Détection côté `/chat` response

Quand le frontend reçoit la réponse de `/chat`, il peut détecter le mode bot OFF :

```typescript
const chatResponse = await sendMessage(userMessage);

if (chatResponse.bot_disabled === true) {
  // Afficher un badge "Opérateur prend le relais"
  // Optionnel: basculer l'UI en mode "attente opérateur"
}

if (chatResponse.next_step === "OPERATOR") {
  // Le bot est OFF, l'opérateur va répondre
}
```

---

## Flux complet

1. **Client passe commande** → Jessica collecte infos → paiement validé
2. **AUTO_CLOTURE** → récap envoyé → `bot_disabled = true`
3. **Client envoie un nouveau message** (ex: "ma livraison ?")
4. **Backend** → détecte `bot_disabled` → skip LLM → INSERT notification → retourne "Un conseiller va vous répondre"
5. **PWA opérateur** → poll GET `/api/notifications/{company_id}` → affiche badge 🔴
6. **Opérateur** → ouvre conversation → POST `read_all` → répond manuellement
7. **Si nouvelle commande** → POST `/api/bot/reactivate` → Jessica reprend

---

## Notes importantes

- **0 token LLM** consommé quand bot OFF → économie maximale
- Le message du client est **toujours sauvegardé** dans l'historique conversation (Supabase)
- L'opérateur peut **réactiver le bot** à tout moment via `/api/bot/reactivate`
- Le polling à 10s est suffisant pour un usage normal ; pour du temps réel, utiliser Supabase Realtime sur la table `operator_notifications`
