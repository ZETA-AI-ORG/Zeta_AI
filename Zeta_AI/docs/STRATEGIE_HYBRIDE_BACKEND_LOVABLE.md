# 🎯 STRATÉGIE HYBRIDE : Backend ↔ Lovable

## 📊 PRINCIPE

- ✅ **Ce qui FONCTIONNE déjà** → Lovable s'aligne sur Backend
- 🚧 **Ce qui N'EST PAS fonctionnel** → Backend s'aligne sur Lovable

---

## ✅ PARTIE 1 : CE QUI FONCTIONNE (Lovable s'aligne)

### **1. Configuration Entreprise** ✅ FONCTIONNEL
**Backend utilise** : `company_rag_configs` (company_id = TEXT)
**Statut** : ✅ Utilisé partout, stable, testé

**→ Lovable DOIT utiliser :**
```typescript
// Hook useCompany
const { data } = await supabase
  .from("company_rag_configs")
  .select("company_id, company_name, ai_name")
  .eq("user_id", user?.id)
  .single();

// company_id est TEXT, pas UUID
```

**Action Lovable** :
- ✅ Utiliser `company_rag_configs.company_id` (TEXT)
- ✅ Ignorer table `companies` (UUID)
- ✅ Ajouter colonne `user_id` dans `company_rag_configs` pour lier utilisateurs

---

### **2. Historique Conversations** ✅ FONCTIONNEL
**Backend utilise** : `conversation_memory`
**Statut** : ✅ Fonction `save_message()` existe dans `core/conversation.py`

**→ Lovable DOIT utiliser :**
```typescript
// Récupérer messages
const { data } = await supabase
  .from("conversation_memory")
  .select("*")
  .eq("company_id", companyId)
  .eq("user_id", userId)
  .order("timestamp", { ascending: true });
```

**Action Lovable** :
- ✅ Utiliser `conversation_memory` pour messages
- ✅ Ignorer tables `conversations` et `messages` (UUID)

---

### **3. Base de Connaissances RAG** ✅ FONCTIONNEL
**Backend utilise** : `documents` (avec embeddings)
**Statut** : ✅ Ingestion fonctionne, recherche sémantique OK

**→ Lovable PEUT lire (lecture seule) :**
```typescript
// Afficher documents ingérés (admin)
const { data } = await supabase
  .from("documents")
  .select("id, content, metadata, company_id")
  .eq("company_id", companyId)
  .limit(50);
```

**Action Lovable** :
- ✅ Lecture seule pour affichage admin
- ❌ NE PAS modifier (géré par backend ingestion)

---

### **4. Prompts Botlive** ✅ FONCTIONNEL
**Backend utilise** : `company_rag_configs.prompt_botlive_groq_70b` et `prompt_botlive_deepseek_v3`
**Statut** : ✅ Utilisé par Botlive, fonctionne

**→ Lovable PEUT afficher/éditer :**
```typescript
// Afficher prompt actuel
const { data } = await supabase
  .from("company_rag_configs")
  .select("prompt_botlive_groq_70b, prompt_botlive_deepseek_v3")
  .eq("company_id", companyId)
  .single();

// Mettre à jour (admin)
await supabase
  .from("company_rag_configs")
  .update({ prompt_botlive_groq_70b: newPrompt })
  .eq("company_id", companyId);
```

**Action Lovable** :
- ✅ Interface admin pour éditer prompts
- ✅ Utiliser colonnes existantes

---

## 🚧 PARTIE 2 : CE QUI N'EST PAS FONCTIONNEL (Backend s'aligne sur Lovable)

### **1. Gestion Commandes** 🚧 NON FONCTIONNEL
**Backend** : ❌ Pas de table `orders`, pas de CRUD
**Lovable** : ✅ Table `orders` créée avec structure complète

**→ Backend ADOPTE la structure Lovable :**
```sql
-- Table orders de Lovable (à garder)
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  conversation_id UUID REFERENCES conversations(id),
  customer_name TEXT,
  total_amount NUMERIC,
  status TEXT,
  items JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Action Backend** :
- ✅ Créer endpoints CRUD pour `orders`
- ✅ Utiliser structure Lovable
- ✅ Ajouter dans `core/botlive_dashboard_data.py`

**Code à ajouter au backend** :
```python
# core/orders_manager.py (NOUVEAU)
async def create_order(company_id: str, user_id: str, order_data: dict):
    """Créer une commande depuis Botlive"""
    # Utiliser table orders de Lovable
    pass

async def get_orders(company_id: str, status: str = None):
    """Récupérer commandes"""
    # SELECT depuis orders
    pass
```

---

### **2. Activités Temps Réel** 🚧 NON FONCTIONNEL
**Backend** : ❌ Pas de logging dans `activities`
**Lovable** : ✅ Table `activities` créée

**→ Backend ADOPTE la structure Lovable :**
```sql
-- Table activities de Lovable (à garder)
CREATE TABLE activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  conversation_id UUID,
  type TEXT,
  title TEXT,
  description TEXT,
  status TEXT DEFAULT 'info',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Action Backend** :
- ✅ Logger événements dans `activities`
- ✅ Modifier `core/botlive_dashboard_data.py` pour lire depuis `activities`

**Code à modifier** :
```python
# core/botlive_dashboard_data.py
async def get_realtime_activity(company_id: str, limit: int = 10):
    """Récupère activité depuis table activities de Lovable"""
    url = f"{SUPABASE_URL}/rest/v1/activities"
    params = {
        "company_id": f"eq.{company_id}",
        "select": "*",
        "order": "created_at.desc",
        "limit": limit
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            return response.json()
    return []
```

---

### **3. Sessions Bot (Mode LIVE/RAG)** 🚧 NON FONCTIONNEL
**Backend** : ❌ Pas de tracking sessions
**Lovable** : ✅ Table `bot_sessions` créée

**→ Backend ADOPTE la structure Lovable :**
```sql
-- Table bot_sessions de Lovable (à garder)
CREATE TABLE bot_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  mode TEXT, -- 'live' ou 'rag'
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Action Backend** :
- ✅ Créer/terminer sessions lors du toggle Mode LIVE
- ✅ Modifier endpoint `/toggle-live-mode` pour logger dans `bot_sessions`

---

### **4. Statistiques Usage** 🚧 NON FONCTIONNEL
**Backend** : ❌ Pas de tracking usage
**Lovable** : ✅ Table `bot_usage` créée

**→ Backend ADOPTE la structure Lovable :**
```sql
-- Table bot_usage de Lovable (à garder)
CREATE TABLE bot_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  date DATE,
  conversations_count INTEGER DEFAULT 0,
  messages_count INTEGER DEFAULT 0,
  orders_count INTEGER DEFAULT 0,
  revenue NUMERIC DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Action Backend** :
- ✅ Logger usage quotidien
- ✅ Utiliser pour calculs stats dashboard

---

## 🔗 PARTIE 3 : PONT ENTRE LES DEUX (Migration nécessaire)

### **Problème** : Backend utilise `company_id` (TEXT), Lovable utilise UUID

**Solution** : Créer table de mapping

```sql
-- Nouvelle table de mapping
CREATE TABLE company_mapping (
  uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT UNIQUE NOT NULL, -- ID backend (TEXT)
  user_id UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX idx_company_mapping_company_id ON company_mapping(company_id);
CREATE INDEX idx_company_mapping_user_id ON company_mapping(user_id);
```

**Utilisation** :
```typescript
// Lovable récupère UUID depuis mapping
const { data: mapping } = await supabase
  .from("company_mapping")
  .select("uuid, company_id")
  .eq("user_id", user?.id)
  .single();

// Utiliser mapping.company_id (TEXT) pour backend
// Utiliser mapping.uuid (UUID) pour tables Lovable
```

---

## 📋 CHECKLIST IMPLÉMENTATION

### **Lovable s'aligne (IMMÉDIAT)** :
- [ ] Utiliser `company_rag_configs.company_id` (TEXT)
- [ ] Utiliser `conversation_memory` pour messages
- [ ] Lire `documents` (lecture seule)
- [ ] Éditer prompts dans `company_rag_configs`

### **Backend s'aligne (À DÉVELOPPER)** :
- [ ] Créer `core/orders_manager.py` pour gérer `orders`
- [ ] Modifier `botlive_dashboard_data.py` pour lire `activities`
- [ ] Logger sessions dans `bot_sessions`
- [ ] Logger usage dans `bot_usage`
- [ ] Créer table `company_mapping` pour pont UUID ↔ TEXT

### **Migration SQL (URGENT)** :
- [ ] Créer `company_mapping`
- [ ] Ajouter `user_id` dans `company_rag_configs`
- [ ] Peupler `company_mapping` avec données existantes

---

## 🚀 ORDRE D'IMPLÉMENTATION

### **Phase 1 : Lovable s'aligne (1-2h)**
1. Modifier hooks pour utiliser tables backend
2. Tester connexion avec `company_rag_configs`
3. Afficher conversations depuis `conversation_memory`

### **Phase 2 : Migration SQL (30min)**
1. Créer `company_mapping`
2. Ajouter `user_id` dans `company_rag_configs`
3. Peupler avec données existantes

### **Phase 3 : Backend s'aligne (2-3h)**
1. Créer `orders_manager.py`
2. Logger dans `activities`
3. Logger dans `bot_sessions`
4. Modifier dashboard pour lire tables Lovable

---

## ✅ RÉSULTAT FINAL

**Architecture hybride optimale** :
- ✅ Backend stable conservé (RAG, Botlive, prompts)
- ✅ Tables Lovable utilisées (orders, activities, sessions)
- ✅ Pont UUID ↔ TEXT via `company_mapping`
- ✅ Meilleur des deux mondes

**Temps total** : ~4-5 heures
**Risque** : Minimal (pas de refactoring majeur)
