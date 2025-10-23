# 🔍 ANALYSE COMPLÈTE : Tables Supabase Backend VS Frontend Lovable

## 📊 TABLES RÉELLEMENT UTILISÉES PAR LE BACKEND

### ✅ **Tables ACTIVES (utilisées dans le code)**

#### 1. **`company_rag_configs`** ⭐ TABLE PRINCIPALE
**Utilisation** : Configuration centrale de chaque entreprise
**Fichiers** : 
- `database/supabase_client.py` - Récupération prompts
- `update_rag_prompt.py`, `update_rag_prompt_v2.py`, `update_botlive_prompt.py`
- `test_supabase_schema.py`

**Colonnes utilisées** :
- `company_id` (TEXT, PK) ← **IDENTIFIANT UNIQUE ENTREPRISE**
- `company_name` (TEXT)
- `ai_name` (TEXT)
- `system_prompt_template` (TEXT)
- `prompt_botlive_groq_70b` (TEXT)
- `prompt_botlive_deepseek_v3` (TEXT)
- `delivery_zones` (JSONB)
- `rag_enabled` (BOOLEAN)
- `meili_config` (JSONB)
- `searchable_attributes`, `filterable_attributes`, `sortable_attributes` (JSONB)

**⚠️ IMPORTANT** : `company_id` est de type TEXT, pas UUID !

---

#### 2. **`documents`** ⭐ BASE DE CONNAISSANCES
**Utilisation** : Stockage embeddings pour RAG
**Fichiers** :
- `migrate_add_metadata.py`
- `test_supabase_schema.py`
- Tous les scripts d'ingestion

**Colonnes** :
- `id` (BIGINT, PK)
- `company_id` (TEXT)
- `content` (TEXT)
- `metadata` (JSONB)
- `embedding` (VECTOR(768))
- `embedding_half` (HALFVEC(768))
- `embedding_384` (VECTOR(384))
- `embedding_384_half` (HALFVEC(384))
- `chunk_id`, `chunk_index`, `macro_chunk_index`, `micro_chunk_index`

---

#### 3. **`company_boosters`** ⭐ OPTIMISATION RECHERCHE
**Utilisation** : Boosters de recherche extraits automatiquement
**Fichiers** :
- `ingestion/ingestion_api.py`

**Colonnes** :
- `id` (BIGSERIAL, PK)
- `company_id` (TEXT, UNIQUE)
- `keywords` (JSONB) - Mots-clés globaux
- `categories` (JSONB) - Données structurées par catégorie
- `filters` (JSONB) - Filtres pré-calculés

---

#### 4. **`company_prompt_history`** ⭐ VERSIONING PROMPTS
**Utilisation** : Historique des versions de prompts
**Fichiers** :
- `update_prompt.py`

**Colonnes** :
- `id` (UUID, PK)
- `company_id` (TEXT)
- `version` (INTEGER)
- `prompt_template` (TEXT)
- `is_active` (BOOLEAN)
- `created_by` (TEXT)
- `created_at` (TIMESTAMP)

---

#### 5. **`conversation_memory`** ⭐ MÉMOIRE CONVERSATIONS
**Utilisation** : Stockage messages avec embeddings
**Fichiers** :
- `core/conversation.py` - `save_message()`
- `utils.py` - `get_conversation()` (commenté mais existe)

**Colonnes** :
- `id` (UUID, PK)
- `user_id` (TEXT)
- `company_id` (TEXT)
- `role` (TEXT: "user"/"assistant")
- `content` (TEXT)
- `embedding` (VECTOR)
- `timestamp` (TIMESTAMP)
- `message_id` (TEXT)

---

#### 6. **`prompt_logs`** ⭐ LOGS DEBUGGING
**Utilisation** : Logger tous les prompts envoyés au LLM
**Fichiers** :
- `database/create_prompt_logs_table.sql`

**Colonnes** :
- `id` (UUID, PK)
- `company_id` (TEXT)
- `user_query` (TEXT)
- `full_prompt` (TEXT)
- `context_used` (TEXT)
- `conversation_history` (TEXT)
- `model_used` (TEXT)
- `response_generated` (TEXT)
- `response_time_ms` (INTEGER)

---

### ❌ **Tables CRÉÉES PAR LOVABLE (mais PAS utilisées par le backend)**

D'après le schéma Supabase, Lovable a créé ces tables :

1. **`companies`** (UUID) - ❌ Backend utilise `company_rag_configs.company_id` (TEXT)
2. **`conversations`** (UUID, FK → companies.id) - ❌ Backend utilise `conversation_memory`
3. **`messages`** (UUID, FK → conversations.id) - ❌ Backend utilise `conversation_memory`
4. **`orders`** (UUID) - ❌ Backend ne gère pas encore les commandes structurées
5. **`activities`** (UUID) - ❌ Backend ne log pas dans cette table
6. **`bot_sessions`** (UUID) - ❌ Backend ne track pas les sessions
7. **`bot_usage`** (UUID) - ❌ Backend ne track pas l'usage
8. **`subscriptions`** (UUID) - ❌ Backend ne gère pas les abonnements
9. **`auto_improvements`**, `auto_generated_faqs`, `learned_patterns` - ❌ Non utilisés

---

## 🎯 DÉCISION STRATÉGIQUE

### **Option 1 : Aligner Lovable sur le Backend (RECOMMANDÉ)**

**Avantages** :
- ✅ Pas de modification du backend (stable)
- ✅ Utilise les tables existantes et testées
- ✅ Compatibilité immédiate avec Botlive
- ✅ Pas de migration de données

**Inconvénients** :
- ❌ Lovable doit supprimer/ignorer ses tables
- ❌ Schéma moins "propre" (TEXT au lieu d'UUID)

**Actions Lovable** :
1. Utiliser `company_rag_configs.company_id` (TEXT) comme identifiant
2. Utiliser `conversation_memory` pour messages
3. Créer hooks pour Backend API (stats, orders, interventions)
4. Ignorer tables `companies`, `conversations`, `messages`, `orders`, `activities`

---

### **Option 2 : Aligner Backend sur Lovable (RISQUÉ)**

**Avantages** :
- ✅ Schéma plus "propre" avec UUIDs
- ✅ Relations FK claires
- ✅ Séparation companies/configs

**Inconvénients** :
- ❌ Refactoring massif du backend
- ❌ Migration de toutes les données existantes
- ❌ Risque de casser Botlive
- ❌ Tests complets à refaire
- ❌ Temps de développement important

---

## 📋 RECOMMANDATION FINALE

### **✅ OPTION 1 : Lovable s'aligne sur le Backend**

**Raisons** :
1. Le backend est **stable et testé**
2. Botlive fonctionne avec le schéma actuel
3. Migration backend = **trop risqué** avant production
4. `company_id` (TEXT) permet flexibilité (pas limité aux UUIDs)

---

## 🔧 DIRECTIVES POUR LOVABLE (Version Finale)

### **1. Hook `useCompany` - VERSION CORRECTE**

```typescript
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "./useAuth";

export const useCompany = () => {
  const { user } = useAuth();

  const { data: company, isLoading } = useQuery({
    queryKey: ["company", user?.id],
    queryFn: async () => {
      // ✅ Utiliser company_rag_configs directement
      const { data, error } = await supabase
        .from("company_rag_configs")
        .select("company_id, company_name, ai_name")
        .eq("user_id", user?.id) // ⚠️ Ajouter colonne user_id si manquante
        .single();

      if (error) throw error;
      
      return {
        companyId: data.company_id, // TEXT, pas UUID
        companyName: data.company_name,
        aiName: data.ai_name,
      };
    },
    enabled: !!user?.id,
  });

  return {
    companyId: company?.companyId,
    companyName: company?.companyName,
    aiName: company?.aiName,
    isLoading,
  };
};
```

---

### **2. Hook `useConversations` - UTILISER conversation_memory**

```typescript
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useCompany } from "./useCompany";

export const useConversations = (userId: string) => {
  const { companyId } = useCompany();

  const { data: messages = [], isLoading } = useQuery({
    queryKey: ["conversations", companyId, userId],
    queryFn: async () => {
      if (!companyId || !userId) throw new Error("IDs manquants");

      const { data, error } = await supabase
        .from("conversation_memory")
        .select("*")
        .eq("company_id", companyId)
        .eq("user_id", userId)
        .order("timestamp", { ascending: true });

      if (error) throw error;
      return data || [];
    },
    enabled: !!companyId && !!userId,
  });

  return {
    messages,
    isLoading,
  };
};
```

---

### **3. Données Dashboard - BACKEND API OBLIGATOIRE**

```typescript
// ❌ NE PAS utiliser tables Supabase pour ces données
// ✅ UTILISER Backend API

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCompany } from "./useCompany";

export const useStats = () => {
  const { companyId } = useCompany();

  return useQuery({
    queryKey: ["stats", companyId],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");
      return await api.fetch(`/botlive/stats/${companyId}?time_range=today`);
    },
    enabled: !!companyId,
    refetchInterval: 10000,
  });
};

export const useOrders = () => {
  const { companyId } = useCompany();

  return useQuery({
    queryKey: ["orders", companyId],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");
      return await api.fetch(`/botlive/orders/active/${companyId}`);
    },
    enabled: !!companyId,
    refetchInterval: 10000,
  });
};
```

---

## ✅ CHECKLIST FINALE LOVABLE

- [ ] Utiliser `company_rag_configs.company_id` (TEXT) comme identifiant
- [ ] Utiliser `conversation_memory` pour historique messages
- [ ] Ignorer tables `companies`, `conversations`, `messages` (UUID)
- [ ] Créer `useStats`, `useOrders`, `useInterventions` avec Backend API
- [ ] Ajouter colonne `user_id` dans `company_rag_configs` si manquante
- [ ] Tester avec company_id réel (ex: "4OS4yFcf2LZwxhKojbAVbKuVuSdb")

---

## 🚨 MIGRATION NÉCESSAIRE

**Ajouter colonne `user_id` dans `company_rag_configs` :**

```sql
ALTER TABLE company_rag_configs 
ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Créer index pour performance
CREATE INDEX idx_company_rag_configs_user_id 
ON company_rag_configs(user_id);

-- RLS (Row Level Security)
ALTER TABLE company_rag_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their company config"
ON company_rag_configs
FOR ALL
USING (user_id = auth.uid());
```

---

**FIN DE L'ANALYSE - Lovable doit suivre ces directives exactes**
