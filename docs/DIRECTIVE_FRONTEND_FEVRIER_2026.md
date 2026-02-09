# DIRECTIVE FRONTEND — Février 2026

> Ce document est destiné à l'IA qui code le frontend (PWA opérateur + page Catalogue Premium).
> Il décrit **3 blocs de travail** à implémenter côté frontend.

---

## BLOC 1 : Système "Bot OFF" + Notifications Opérateur

### Contexte

Quand une commande est **validée + payée**, le bot Jessica se désactive automatiquement (`bot_disabled = true`).  
Tous les messages suivants du client **bypasse le LLM** (0 token consommé) et sont **routés vers l'opérateur humain** via une table Supabase `operator_notifications`.

Le client reçoit : *"Un conseiller va vous répondre sous peu. Merci de patienter 🙏"*

### Table Supabase (déjà créée)

```
operator_notifications
├── id             UUID (auto)
├── company_id     TEXT
├── user_id        TEXT
├── message        TEXT        — le message du client
├── message_type   TEXT        — "post_order"
├── order_summary  JSONB       — {produit, produit_details, quantite, zone, numero, paiement}
├── read           BOOLEAN     — false = non lu
└── created_at     TIMESTAMPTZ
```

### Endpoints Backend (déjà implémentés)

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/notifications/{company_id}?unread_only=true&limit=50` | Récupérer les notifications non lues |
| `POST` | `/api/notifications/{company_id}/read_all` | Marquer toutes les notifs d'un user comme lues. Body: `{"user_id": "..."}` |
| `PATCH` | `/api/notifications/read` | Marquer UNE notif comme lue. Body: `{"notification_id": "uuid"}` |
| `POST` | `/api/bot/reactivate` | Réactiver Jessica pour un user. Body: `{"company_id": "...", "user_id": "..."}` |

### Réponse type GET /api/notifications

```json
{
  "notifications": [
    {
      "id": "a1b2c3d4-...",
      "company_id": "W27PwOPi...",
      "user_id": "client_225_0787360757",
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

### Détection côté réponse /chat

Quand le frontend envoie un message via `POST /chat` et reçoit la réponse, il peut détecter le mode bot OFF :

```typescript
const chatResponse = await sendMessage(userMessage);

if (chatResponse.bot_disabled === true || chatResponse.next_step === "OPERATOR") {
  // Le bot est OFF → afficher un badge/indicateur "Opérateur prend le relais"
  // Optionnel: basculer l'UI en mode "attente opérateur"
}
```

### Ce que le frontend doit implémenter

1. **Badge de notification** dans la sidebar/header de la PWA opérateur
   - Polling `GET /api/notifications/{company_id}?unread_only=true` toutes les **10 secondes**
   - Afficher un badge rouge avec le nombre de notifications non lues
   - Son/vibration optionnel quand un nouveau message arrive

2. **Liste de notifications** (page ou panneau)
   - Afficher chaque notification avec : user_id, message, date, résumé commande
   - Bouton **"Marquer lu"** → `POST /api/notifications/{company_id}/read_all` avec le `user_id`
   - Bouton **"Réactiver le bot"** → `POST /api/bot/reactivate` (pour relancer Jessica si le client veut passer une nouvelle commande)

3. **Conversation post-bot** : quand l'opérateur clique sur une notification, ouvrir la conversation du client pour qu'il puisse répondre manuellement

### Hook React suggéré

```typescript
import { useState, useEffect, useCallback } from "react";

export function useOperatorNotifications(companyId: string, pollInterval = 10000) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifs = useCallback(async () => {
    const res = await fetch(
      `${import.meta.env.VITE_API_URL}/api/notifications/${companyId}?unread_only=true`
    );
    if (!res.ok) return;
    const data = await res.json();
    setNotifications(data.notifications || []);
    setUnreadCount(data.count || 0);
  }, [companyId]);

  useEffect(() => {
    fetchNotifs();
    const interval = setInterval(fetchNotifs, pollInterval);
    return () => clearInterval(interval);
  }, [fetchNotifs, pollInterval]);

  const markAllRead = async (userId: string) => {
    await fetch(`${import.meta.env.VITE_API_URL}/api/notifications/${companyId}/read_all`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
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

---

## BLOC 2 : Modifications Page Catalogue Premium

### 2A — Champ "Nom sous-variante" (variant_label)

**Objectif :** Permettre à l'entreprise de donner un **nom** au groupe de sous-variantes.  
Exemple : si les sous-variantes sont `T1, T2, T3, T4`, le nom serait **"Taille"**.

**Où l'ajouter dans l'UI :**
- Dans la section où l'utilisateur crée/édite les variantes d'un produit
- Un champ texte **au-dessus** de la liste des sous-variantes
- Label : `"Nom de la sous-variante"` ou `"Catégorie de sous-variante"`
- Placeholder : `"Ex: Taille, Couleur, Modèle..."`

**Stockage dans le catalog JSON :**
```json
{
  "v": {
    "Culotte": {
      "variant_label": "Taille",
      "s": {
        "T1": { "u": { "lot_50": 7500 } },
        "T2": { "u": { "lot_50": 8000 } }
      }
    }
  }
}
```

Le champ `variant_label` est **optionnel**. S'il est absent, le backend continue de fonctionner normalement.

### 2B — Champ "Prix unique" (single_price)

**Objectif :** Permettre de définir un **prix unique** pour un produit qui n'a qu'un seul format de vente et pas de variation de prix.

**Où l'ajouter dans l'UI :**
- Un toggle ou checkbox : `"Ce produit a un prix unique"` 
- Si activé : afficher un seul champ prix (ex: `"Prix : ___ FCFA"`)
- Si désactivé : afficher la grille de prix par format/sous-variante (comportement actuel)

**Stockage dans le catalog JSON :**
```json
{
  "single_price": 5000,
  "v": {
    "MonProduit": {
      "u": { "piece_1": 5000 }
    }
  }
}
```

Quand `single_price` est défini, le backend sait qu'il n'y a qu'un seul prix, pas besoin de table de prix complexe.

### 2C — Sous-variantes avec ou sans prix différents

**Objectif :** Permettre d'enregistrer des sous-variantes qui **n'impactent pas le prix** (ex: Taille T1/T2/T3 au même prix) ET des sous-variantes qui **impactent le prix** (ex: T1=7500F, T2=8000F).

**Comportement UI :**
1. Quand l'utilisateur ajoute des sous-variantes, proposer un toggle :
   - `"Prix identique pour toutes les sous-variantes"` → un seul champ prix
   - `"Prix différent par sous-variante"` → un champ prix par sous-variante

2. **Prix identique** : l'utilisateur entre UN prix, toutes les sous-variantes héritent ce prix
   ```json
   "s": {
     "T1": { "u": { "lot_50": 7500 } },
     "T2": { "u": { "lot_50": 7500 } },
     "T3": { "u": { "lot_50": 7500 } }
   }
   ```

3. **Prix différent** : l'utilisateur entre un prix par sous-variante
   ```json
   "s": {
     "T1": { "u": { "lot_50": 7500 } },
     "T2": { "u": { "lot_50": 8000 } },
     "T3": { "u": { "lot_50": 8500 } }
   }
   ```

**Le JSON envoyé au backend reste le même format** — c'est juste l'UI qui simplifie la saisie.

---

## BLOC 3 : Nom Produit Immutable + Product ID Fixe

### Règle

Une fois qu'un produit est **créé** dans le catalogue, son **nom ne peut plus être modifié**.  
Cela garantit que le `product_id` (généré à partir du nom via hash SHA1) reste **toujours le même**.

### Pourquoi ?

Le `product_id` est utilisé dans :
- Le prompt LLM (bloc `[[PRODUCT_INDEX_START]]`)
- L'historique des commandes
- Le panier (CartManager)
- Les notifications opérateur

Si le nom change → le `product_id` change → tout casse.

### Ce que le frontend doit faire

1. **À la création** d'un produit :
   - Le champ "Nom du produit" est **éditable** normalement
   - Le `product_id` est généré automatiquement par le backend (hash du nom)

2. **Après la création** (édition d'un produit existant) :
   - Le champ "Nom du produit" est **en lecture seule** (disabled/readonly)
   - Afficher un petit texte : *"Le nom du produit ne peut pas être modifié après création"*
   - Le `product_id` reste fixe

3. **Si l'entreprise veut changer le nom** :
   - Elle doit **supprimer** le produit et en **recréer** un nouveau
   - Afficher un message d'avertissement si elle tente de supprimer un produit qui a des commandes en cours

### Auto-sync PRODUCT_INDEX dans le prompt

Quand le frontend appelle l'endpoint de sauvegarde catalogue :
```
POST /catalog-v2/sync-local-and-upsert-botlive-catalogue-block-deepseek
```

Le backend **met automatiquement à jour** le bloc `[[PRODUCT_INDEX_START]]...[[PRODUCT_INDEX_END]]` dans le prompt Supabase avec :
- Le nom du produit
- Son `product_id` (fixe)
- Les variantes (clés du vtree)

Exemple de résultat dans le prompt :
```
[[PRODUCT_INDEX_START]]
- COUCHES BÉBÉS ( 0-25KG ) [ID: prod_ml6dxg73_a0rloi]
  - VARIANTS: Culotte | Pression
[[PRODUCT_INDEX_END]]
```

**Le frontend n'a rien de spécial à faire pour ça** — c'est automatique côté backend lors de chaque sauvegarde/MAJ du catalogue. Il suffit de continuer à appeler le même endpoint qu'avant.

Quand un produit est **supprimé**, le frontend doit aussi appeler un endpoint pour retirer l'entrée du PRODUCT_INDEX. *(À implémenter si un endpoint de suppression existe déjà, sinon me le signaler.)*

---

## Résumé des actions frontend

| # | Action | Priorité | Bloc |
|---|--------|----------|------|
| 1 | Badge notification + polling 10s | Haute | 1 |
| 2 | Page/panneau liste notifications | Haute | 1 |
| 3 | Bouton "Marquer lu" + "Réactiver bot" | Haute | 1 |
| 4 | Détection `bot_disabled` dans réponse /chat | Moyenne | 1 |
| 5 | Champ "Nom sous-variante" (variant_label) | Haute | 2A |
| 6 | Champ "Prix unique" (single_price) | Haute | 2B |
| 7 | Toggle "Prix identique / différent" par sous-variante | Haute | 2C |
| 8 | Nom produit readonly après création | Haute | 3 |
| 9 | Message info "nom non modifiable" | Moyenne | 3 |

---

## Notes techniques

- **Backend URL** : `import.meta.env.VITE_API_URL` (variable d'environnement)
- **Table Supabase notifications** : `operator_notifications` (déjà créée, SQL exécuté avec succès)
- **Polling** : 10s suffisant pour usage normal. Pour du temps réel, utiliser Supabase Realtime sur `operator_notifications`
- **Le format JSON du catalogue ne change pas** — les nouveaux champs (`variant_label`, `single_price`) sont optionnels et additifs
- **L'endpoint backend de sync catalogue gère déjà automatiquement** la mise à jour du PRODUCT_INDEX avec les variantes
