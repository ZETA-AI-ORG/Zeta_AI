# 📋 Alignement Statuts Zeta AI ↔ Partner App

## ⚠️ PROBLÈME RÉSOLU (27/02/2026)

Les commandes créées par le chatbot n'apparaissaient **pas** dans l'app Partner car :

1. **Backend** (`core/orders_manager.py`) insérait `status: "pending"`
2. **Frontend** (`usePartnerOrders.ts`) filtre sur `status: "open"`
3. **Résultat** : aucune commande visible malgré données en base

---

## ✅ SOLUTION APPLIQUÉE

### Modification Backend
**Fichier** : `core/orders_manager.py` (ligne 86)

```python
# AVANT (❌ incompatible Partner)
"status": "pending",

# APRÈS (✅ aligné Partner)
"status": "open",  # ✅ Alignement Partner App (filtre sur "open")
```

### Vérification Frontend
**Fichier** : `zeta-ai-vercel/src/hooks/usePartnerOrders.ts` (ligne 33)

```typescript
.eq("status", "open")  // ✅ Filtre actif côté Partner
```

---

## 🔗 Comment les statuts sont liés (Backend ↔ Supabase ↔ Frontend)

Le **Backend** écrit les statuts dans Supabase.

- **Table `orders.status`**
  - Statut “global” de la commande.
  - C’est ce champ qui est filtré par certaines pages/hook côté Frontend (ex: Partner qui fait `.eq("status", "open")`).

- **Table `order_deliveries.status`**
  - Statut “livraison / tracking”.
  - C’est ce champ qui pilote généralement les colonnes “à prendre / en cours / terminées / annulées…”.

Conséquence:

- Si le Backend insère `orders.status = "pending"` mais le Frontend filtre sur `"open"`, la commande est **invisible**.
- Si un trigger crée `order_deliveries`, il doit créer une ligne cohérente (souvent en copiant le statut ou en mettant `"open"` au départ).

---

## 🧩 (Frontend) Modification de la page Catalogue — où modifier ?

Oui : si tu veux modifier la page **Catalogue**, tu modifies directement le fichier dédié :

- `zeta-ai-vercel/src/pages/ZetaFlowCatalogue.tsx`

Et c’est automatiquement pris en compte dans l’app `ZetaFlow` parce que `ZetaFlow.tsx` **importe** et **rend** ce composant tel quel :

- `import ZetaFlowCatalogue from "./ZetaFlowCatalogue";`
- puis `<ZetaFlowCatalogue />`

Notes pratiques :

- En **dev** (serveur Vite/React), tes changements sont généralement visibles immédiatement (hot reload).
- En **prod**, il faut re-build/redeploy le frontend (Vercel) pour que les changements soient visibles.

---

## 📊 MAPPING COMPLET DES STATUTS

### Table `orders` (commande globale)
| Statut | Signification | Utilisé par |
|--------|---------------|-------------|
| `open` | Commande créée, en attente d'acceptation | **Chatbot** (création) + **Partner** (affichage) |
| `accepted` | Acceptée par un livreur | Partner (après clic "Accepter") |
| `completed` | Livrée et terminée | Partner (après clic "Terminer") |
| `cancelled` | Annulée | Partner ou Admin |
| `postponed` | Reportée à une date ultérieure | Partner |

### Table `order_deliveries` (suivi livraison)
| Statut | Signification | Affichage Partner |
|--------|---------------|-------------------|
| `open` | Disponible pour acceptation | Page **Commandes** |
| `accepted` | Acceptée, pas encore prise en charge | Page **Status** → "À prendre" |
| `picked_up` | En cours de livraison | Page **Status** → "En cours" 🚴 |
| `delivered` | Livrée avec succès | Page **Status** → "Terminées" ✓ |
| `postponed` | Reportée | Page **Status** → "Reportées" 📅 |
| `cancelled` | Annulée | Page **Status** → "Annulées" ✕ |

---

## 🔧 TRIGGER SQL (À VÉRIFIER EN PROD)

Si un trigger automatique crée `order_deliveries` lors de l'insertion dans `orders`, il **doit** utiliser le même statut :

```sql
-- Trigger hypothétique (à confirmer dans Supabase Dashboard)
CREATE OR REPLACE FUNCTION create_order_delivery()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO order_deliveries (order_id, status, price, commission)
  VALUES (NEW.id, NEW.status, 2500, 50);  -- ⚠️ Doit copier NEW.status = "open"
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 🧪 COMMANDE CURL DE TEST (ALIGNÉE)

Pour injecter une commande de test **visible** dans Partner :

```bash
ORDER_ID="33333333-3333-3333-3333-333333333333"

# 1) Créer la commande avec status="open"
curl -X POST "$SUPABASE_URL/rest/v1/orders" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$ORDER_ID\",
    \"customer_name\": \"Koné Moussa\",
    \"customer_phone\": \"+2250777889900\",
    \"delivery_address\": \"Yopougon Niangon - Carrefour Sideci\",
    \"delivery_zone\": \"Yopougon\",
    \"pickup_location\": \"Plateau - Immeuble SCIAM\",
    \"requester_phone\": \"+2250101020304\",
    \"total_amount\": 3500,
    \"items\": [{\"name\": \"Ordinateur portable\", \"quantity\": 1, \"price\": 3500}],
    \"status\": \"open\",
    \"delivery_status\": \"pending_assignment\",
    \"company_id\": \"REMPLACER_PAR_UUID_ENTREPRISE\"
  }"

# 2) Créer la livraison associée avec status="open"
curl -X POST "$SUPABASE_URL/rest/v1/order_deliveries" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"status\": \"open\",
    \"price\": 3500,
    \"commission\": 350
  }"
```

---

## 🚨 CHECKLIST DÉPLOIEMENT

Avant de déployer en production :

- [x] ✅ Backend modifié (`orders_manager.py` ligne 86)
- [ ] ⏳ Vérifier trigger SQL `order_deliveries` (copie bien `status="open"`)
- [ ] ⏳ Tester avec `curl` sur VPS (commande doit apparaître dans Partner)
- [ ] ⏳ Vérifier que `company_id` est bien rempli (sinon RLS peut bloquer)
- [ ] ⏳ Déployer backend sur VPS avec `.\deploy.ps1 "Fix: statut open pour Partner"`
- [ ] ⏳ Vérifier logs VPS après déploiement

---

## 📞 CONTACT SI PROBLÈME PERSISTE

Si après déploiement les commandes restent invisibles :

1. **Vérifier RLS** : `SELECT * FROM order_deliveries WHERE status='open'` en tant qu'utilisateur Partner
2. **Vérifier company_id** : Toutes les commandes doivent avoir un `company_id` valide
3. **Vérifier trigger** : Inspecter le code du trigger dans Supabase Dashboard → Database → Triggers
4. **Logs backend** : `docker logs zeta-backend | grep ORDERS`

---

**Dernière mise à jour** : 27/02/2026 09:10 UTC+01  
**Auteur** : Cascade AI (alignement backend/frontend)
