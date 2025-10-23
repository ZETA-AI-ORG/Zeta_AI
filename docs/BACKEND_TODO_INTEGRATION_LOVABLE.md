# 🔧 TODO BACKEND - Intégration Tables Lovable

## ✅ FICHIERS CRÉÉS

### **1. Migration SQL**
- ✅ `database/migrations/create_company_mapping.sql`
  - Crée table `company_mapping` (pont UUID ↔ TEXT)
  - Ajoute colonne `user_id` dans `company_rag_configs`
  - Configure RLS (Row Level Security)
  - Peuple avec données existantes

### **2. Modules Python**
- ✅ `core/orders_manager.py` - Gestion commandes
- ✅ `core/activities_logger.py` - Logger activités
- ✅ `core/sessions_manager.py` - Gestion sessions

---

## 📋 ÉTAPES D'INTÉGRATION

### **ÉTAPE 1 : Exécuter Migration SQL** ⏱️ 5 min

```bash
# Se connecter à Supabase et exécuter le script
# Via Dashboard Supabase > SQL Editor > Nouveau query
# Copier-coller le contenu de create_company_mapping.sql
```

**Vérification** :
```sql
-- Vérifier que les tables existent
SELECT * FROM company_mapping LIMIT 5;
SELECT company_id, user_id FROM company_rag_configs WHERE user_id IS NOT NULL LIMIT 5;
```

---

### **ÉTAPE 2 : Modifier endpoint `/toggle-live-mode`** ⏱️ 10 min

**Fichier** : `app.py` (ligne ~2298)

**Remplacer** :
```python
@app.post("/toggle-live-mode")
def toggle_live_mode(req: ToggleLiveRequest):
    """Active/désactive le mode Live via LiveModeManager."""
    try:
        from core.live_mode_manager import LiveModeManager
        manager = LiveModeManager()
        if req.enable:
            manager.enable_live_mode()
            status = "enabled"
        else:
            manager.disable_live_mode()
            status = "disabled"
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"toggle-live-mode error: {e}")
```

**Par** :
```python
@app.post("/toggle-live-mode")
async def toggle_live_mode(req: ToggleLiveRequest):
    """Active/désactive le mode Live + logger dans bot_sessions."""
    try:
        from core.live_mode_manager import LiveModeManager
        from core.sessions_manager import start_session, end_session, get_active_session
        
        manager = LiveModeManager()
        
        if req.enable:
            # Activer mode LIVE
            manager.enable_live_mode()
            
            # Créer session dans bot_sessions
            session_id = await start_session(req.company_id, "live")
            
            return {
                "status": "enabled",
                "session_id": session_id
            }
        else:
            # Désactiver mode LIVE
            manager.disable_live_mode()
            
            # Terminer session active
            active_session = await get_active_session(req.company_id)
            if active_session:
                await end_session(active_session["id"], req.company_id)
            
            return {
                "status": "disabled"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"toggle-live-mode error: {e}")
```

---

### **ÉTAPE 3 : Logger activités dans Botlive** ⏱️ 15 min

**Fichier** : `core/botlive_rag_hybrid.py` (ou fichier principal Botlive)

**Ajouter après validation paiement** :
```python
# Après ligne où paiement est validé
if payment_validation.get('valid'):
    from core.activities_logger import log_payment_validated
    await log_payment_validated(
        company_id=company_id,
        user_id=user_id,
        amount=payment_validation.get('total_received', 0),
        reference=payment_validation.get('reference', '')
    )
```

**Ajouter après détection problème** :
```python
# Quand montant insuffisant détecté
if payment_validation.get('error') == 'MONTANT_INSUFFISANT':
    from core.activities_logger import log_payment_issue
    await log_payment_issue(
        company_id=company_id,
        user_id=user_id,
        issue_type="payment_insufficient",
        message=f"Montant insuffisant: {detected_amount} FCFA reçu, {required_amount} FCFA requis"
    )
```

**Ajouter après commande complétée** :
```python
# Quand commande est complète (4 étapes validées)
if order_state.is_complete():
    from core.orders_manager import create_order
    from core.activities_logger import log_order_created
    
    # Créer commande
    order = await create_order(
        company_id=company_id,
        user_id=user_id,
        customer_name=order_state.numero or user_id[-4:],
        total_amount=calculate_total_amount(order_state),
        items=[{
            "name": order_state.produit,
            "quantity": 1,
            "price": extract_price(order_state.produit)
        }]
    )
    
    if order:
        # Logger activité
        await log_order_created(
            company_id=company_id,
            customer_name=order_state.numero or user_id[-4:],
            order_id=order["id"],
            total_amount=order["total_amount"]
        )
```

---

### **ÉTAPE 4 : Modifier `botlive_dashboard_data.py`** ⏱️ 10 min

**Fichier** : `core/botlive_dashboard_data.py`

**Modifier fonction `get_realtime_activity`** :
```python
async def get_realtime_activity(company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupère l'activité en temps réel depuis table activities (Lovable)
    """
    try:
        # Récupérer UUID
        from core.orders_manager import get_company_uuid
        company_uuid = await get_company_uuid(company_id)
        
        if not company_uuid:
            return []
        
        # Récupérer activités depuis table Lovable
        url = f"{SUPABASE_URL}/rest/v1/activities"
        params = {
            "company_id": f"eq.{company_uuid}",
            "select": "*",
            "order": "created_at.desc",
            "limit": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)
            
            if response.status_code == 200:
                activities = response.json()
                
                # Formater pour le frontend
                formatted = []
                for activity in activities:
                    formatted.append({
                        "type": activity.get("type", "info"),
                        "client": activity.get("title", ""),
                        "produit": activity.get("description", ""),
                        "timestamp": _format_relative_time(activity.get("created_at", ""))
                    })
                
                return formatted
        
        return []
        
    except Exception as e:
        logger.error(f"[BOTLIVE_ACTIVITY] Erreur: {e}", exc_info=True)
        return []
```

---

### **ÉTAPE 5 : Modifier endpoint `/botlive/orders/active`** ⏱️ 5 min

**Fichier** : `routes/botlive.py`

**Remplacer** :
```python
@router.get("/orders/active/{company_id}")
async def get_active_orders_endpoint(company_id: str, limit: int = 50):
    try:
        from core.botlive_dashboard_data import get_active_orders
        
        active_orders = await get_active_orders(company_id, limit)
        
        return JSONResponse(content={
            "success": True,
            "orders": active_orders,
            "total": len(active_orders)
        })
```

**Par** :
```python
@router.get("/orders/active/{company_id}")
async def get_active_orders_endpoint(company_id: str, limit: int = 50):
    try:
        from core.orders_manager import get_orders
        
        # Récupérer depuis table orders (Lovable)
        orders = await get_orders(company_id, status="pending", limit=limit)
        
        # Formater pour le frontend
        formatted_orders = []
        for order in orders:
            formatted_orders.append({
                "user_id": order.get("customer_name", ""),
                "user_name": order.get("customer_name", "")[-4:],
                "produit": order.get("items", [{}])[0].get("name", "") if order.get("items") else "",
                "paiement": f"✅ {order.get('total_amount', 0)} FCFA",
                "zone": "✅" if order.get("status") == "pending" else "❌",
                "numero": "✅" if order.get("customer_name") else "❌",
                "completion_rate": 75,
                "created_at": order.get("created_at", "")
            })
        
        return JSONResponse(content={
            "success": True,
            "orders": formatted_orders,
            "total": len(formatted_orders)
        })
```

---

## ✅ CHECKLIST FINALE

### **Migration SQL** :
- [ ] Exécuter `create_company_mapping.sql` dans Supabase
- [ ] Vérifier que `company_mapping` existe
- [ ] Vérifier que `user_id` existe dans `company_rag_configs`
- [ ] Peupler `company_mapping` avec données existantes

### **Code Backend** :
- [ ] Modifier `/toggle-live-mode` pour logger sessions
- [ ] Ajouter logs activités dans Botlive (paiement, commande, erreurs)
- [ ] Modifier `get_realtime_activity` pour lire depuis `activities`
- [ ] Modifier `/botlive/orders/active` pour lire depuis `orders`

### **Tests** :
- [ ] Tester toggle Mode LIVE (vérifier session créée dans `bot_sessions`)
- [ ] Tester validation paiement (vérifier activité dans `activities`)
- [ ] Tester commande complète (vérifier ordre dans `orders`)
- [ ] Tester endpoint `/botlive/activity` (doit retourner activités)
- [ ] Tester endpoint `/botlive/orders/active` (doit retourner commandes)

---

## 🚀 ORDRE D'EXÉCUTION

1. **Migration SQL** (5 min) ← FAIRE EN PREMIER
2. **Modifier `/toggle-live-mode`** (10 min)
3. **Logger activités Botlive** (15 min)
4. **Modifier dashboard endpoints** (15 min)
5. **Tests complets** (20 min)

**Temps total** : ~1 heure

---

## 📞 SUPPORT

**Problèmes courants** :

1. **`company_mapping` vide** → Exécuter la partie "PEUPLER" du SQL
2. **UUID introuvable** → Vérifier que `company_id` existe dans `company_rag_configs`
3. **Erreur 401 Supabase** → Vérifier RLS policies
4. **Activités non affichées** → Vérifier que `company_uuid` est correct

**Logs à surveiller** :
```bash
# Vérifier logs backend
tail -f logs/server/*.json | grep -E "ORDERS|ACTIVITIES|SESSIONS"
```
