# 🎯 DIRECTIVES COMPLÈTES LOVABLE - Stratégie Hybride

## 📍 CONFIGURATION DE BASE

### **1. Variables d'environnement (`.env`)**
```env
VITE_API_URL=http://localhost:8002
```

### **2. Fichier de configuration API (`src/lib/api.ts`)**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8002";

export const api = {
  baseUrl: API_BASE_URL,
  
  async fetch(endpoint: string, options?: RequestInit) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  },
};
```

---

## ✅ PARTIE 1 : UTILISER LES TABLES BACKEND (Lovable s'aligne)

### **Hook 1 : `useCompany` - Configuration Entreprise**

```typescript
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "./useAuth";

export const useCompany = () => {
  const { user } = useAuth();

  const { data: company, isLoading } = useQuery({
    queryKey: ["company", user?.id],
    queryFn: async () => {
      // ✅ Utiliser company_rag_configs (table backend)
      const { data, error } = await supabase
        .from("company_rag_configs")
        .select("company_id, company_name, ai_name, delivery_zones")
        .eq("user_id", user?.id) // Colonne à ajouter par migration SQL
        .single();

      if (error) throw error;
      
      return {
        companyId: data.company_id, // ⚠️ TEXT, pas UUID
        companyName: data.company_name,
        aiName: data.ai_name,
        deliveryZones: data.delivery_zones,
      };
    },
    enabled: !!user?.id,
  });

  return {
    companyId: company?.companyId,
    companyName: company?.companyName,
    aiName: company?.aiName,
    deliveryZones: company?.deliveryZones,
    isLoading,
  };
};
```

**⚠️ IMPORTANT** : `company_id` est de type **TEXT**, pas UUID !

---

### **Hook 2 : `useConversations` - Historique Messages**

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

      // ✅ Utiliser conversation_memory (table backend)
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
    refetchInterval: 10000, // Refresh toutes les 10s
  });

  return {
    messages,
    isLoading,
  };
};
```

**❌ NE PAS utiliser** : Tables `conversations` et `messages` (UUID)

---

### **Hook 3 : `useDocuments` - Base de Connaissances (Lecture seule)**

```typescript
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useCompany } from "./useCompany";

export const useDocuments = (limit: number = 50) => {
  const { companyId } = useCompany();

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents", companyId, limit],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");

      // ✅ Lecture seule depuis documents (table backend)
      const { data, error } = await supabase
        .from("documents")
        .select("id, content, metadata, created_at")
        .eq("company_id", companyId)
        .order("created_at", { ascending: false })
        .limit(limit);

      if (error) throw error;
      return data || [];
    },
    enabled: !!companyId,
  });

  return {
    documents,
    isLoading,
  };
};
```

**⚠️ LECTURE SEULE** : Ne pas modifier, géré par backend ingestion

---

### **Hook 4 : `usePrompts` - Édition Prompts Botlive (Admin)**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useCompany } from "./useCompany";

export const usePrompts = () => {
  const { companyId } = useCompany();
  const queryClient = useQueryClient();

  // Récupérer prompts
  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts", companyId],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");

      const { data, error } = await supabase
        .from("company_rag_configs")
        .select("prompt_botlive_groq_70b, prompt_botlive_deepseek_v3")
        .eq("company_id", companyId)
        .single();

      if (error) throw error;
      return data;
    },
    enabled: !!companyId,
  });

  // Mettre à jour prompt
  const updatePrompt = useMutation({
    mutationFn: async ({ type, prompt }: { type: "groq" | "deepseek"; prompt: string }) => {
      if (!companyId) throw new Error("Company ID manquant");

      const column = type === "groq" ? "prompt_botlive_groq_70b" : "prompt_botlive_deepseek_v3";

      const { error } = await supabase
        .from("company_rag_configs")
        .update({ [column]: prompt })
        .eq("company_id", companyId);

      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
    },
  });

  return {
    prompts,
    isLoading,
    updatePrompt: updatePrompt.mutate,
  };
};
```

---

## 🚧 PARTIE 2 : UTILISER VOS TABLES (Backend s'alignera)

### **Hook 5 : `useOrders` - Gestion Commandes**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useCompany } from "./useCompany";

export const useOrders = (limit: number = 50) => {
  const { companyId } = useCompany();
  const queryClient = useQueryClient();

  // ✅ Utiliser VOTRE table orders (UUID)
  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders", companyId, limit],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");

      // Récupérer UUID depuis mapping
      const { data: mapping } = await supabase
        .from("company_mapping")
        .select("uuid")
        .eq("company_id", companyId)
        .single();

      if (!mapping) throw new Error("Mapping introuvable");

      const { data, error } = await supabase
        .from("orders")
        .select("*")
        .eq("company_id", mapping.uuid) // UUID
        .order("created_at", { ascending: false })
        .limit(limit);

      if (error) throw error;
      return data || [];
    },
    enabled: !!companyId,
    refetchInterval: 10000,
  });

  // Créer commande
  const createOrder = useMutation({
    mutationFn: async (orderData: any) => {
      if (!companyId) throw new Error("Company ID manquant");

      const { data: mapping } = await supabase
        .from("company_mapping")
        .select("uuid")
        .eq("company_id", companyId)
        .single();

      const { data, error } = await supabase
        .from("orders")
        .insert({
          ...orderData,
          company_id: mapping.uuid,
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  return {
    orders,
    isLoading,
    createOrder: createOrder.mutate,
  };
};
```

---

### **Hook 6 : `useActivities` - Activités Temps Réel**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useCompany } from "./useCompany";

export const useActivities = () => {
  const { companyId } = useCompany();
  const queryClient = useQueryClient();

  // ✅ Utiliser VOTRE table activities (UUID)
  const { data: activities = [], isLoading } = useQuery({
    queryKey: ["activities", companyId],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");

      const { data: mapping } = await supabase
        .from("company_mapping")
        .select("uuid")
        .eq("company_id", companyId)
        .single();

      const { data, error } = await supabase
        .from("activities")
        .select("*")
        .eq("company_id", mapping.uuid)
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) throw error;
      return data || [];
    },
    enabled: !!companyId,
    refetchInterval: 10000,
  });

  // Créer activité
  const createActivity = useMutation({
    mutationFn: async (activity: {
      type: string;
      title: string;
      description?: string;
      status?: string;
      metadata?: any;
    }) => {
      if (!companyId) throw new Error("Company ID manquant");

      const { data: mapping } = await supabase
        .from("company_mapping")
        .select("uuid")
        .eq("company_id", companyId)
        .single();

      const { data, error } = await supabase
        .from("activities")
        .insert({
          ...activity,
          company_id: mapping.uuid,
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });

  return {
    activities,
    isLoading,
    createActivity: createActivity.mutate,
  };
};
```

---

### **Hook 7 : `useBotSessions` - Sessions Mode LIVE**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useCompany } from "./useCompany";

export const useBotSessions = () => {
  const { companyId } = useCompany();
  const queryClient = useQueryClient();

  // ✅ Utiliser VOTRE table bot_sessions (UUID)
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["bot_sessions", companyId],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");

      const { data: mapping } = await supabase
        .from("company_mapping")
        .select("uuid")
        .eq("company_id", companyId)
        .single();

      const { data, error } = await supabase
        .from("bot_sessions")
        .select("*")
        .eq("company_id", mapping.uuid)
        .order("started_at", { ascending: false })
        .limit(10);

      if (error) throw error;
      return data || [];
    },
    enabled: !!companyId,
  });

  // Session active
  const activeSession = sessions.find(s => !s.ended_at);

  // Démarrer session
  const startSession = useMutation({
    mutationFn: async (mode: "live" | "rag") => {
      if (!companyId) throw new Error("Company ID manquant");

      const { data: mapping } = await supabase
        .from("company_mapping")
        .select("uuid")
        .eq("company_id", companyId)
        .single();

      const { data, error } = await supabase
        .from("bot_sessions")
        .insert({
          company_id: mapping.uuid,
          mode,
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bot_sessions"] });
    },
  });

  // Terminer session
  const endSession = useMutation({
    mutationFn: async (sessionId: string) => {
      const { error } = await supabase
        .from("bot_sessions")
        .update({ ended_at: new Date().toISOString() })
        .eq("id", sessionId);

      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bot_sessions"] });
    },
  });

  return {
    sessions,
    activeSession,
    isLoading,
    startSession: startSession.mutate,
    endSession: endSession.mutate,
  };
};
```

---

## 🔥 PARTIE 3 : UTILISER BACKEND API (Calculs complexes)

### **Hook 8 : `useStats` - Statistiques Dashboard**

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCompany } from "./useCompany";

export const useStats = (timeRange: "today" | "week" | "month" = "today") => {
  const { companyId } = useCompany();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats", companyId, timeRange],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");
      
      // ✅ Backend API (calculs CA, variations, etc.)
      return await api.fetch(`/botlive/stats/${companyId}?time_range=${timeRange}`);
    },
    enabled: !!companyId,
    refetchInterval: 10000,
  });

  return {
    stats: stats || {
      ca_live_session: 0,
      ca_variation: "0%",
      commandes_total: 0,
      commandes_variation: "+0",
      clients_actifs: 0,
      interventions_requises: 0,
    },
    isLoading,
  };
};
```

---

### **Hook 9 : `useInterventions` - Alertes**

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCompany } from "./useCompany";

export const useInterventions = () => {
  const { companyId } = useCompany();

  const { data: interventionsData, isLoading } = useQuery({
    queryKey: ["interventions", companyId],
    queryFn: async () => {
      if (!companyId) throw new Error("Company ID manquant");
      
      // ✅ Backend API (détection automatique problèmes)
      return await api.fetch(`/botlive/interventions/${companyId}`);
    },
    enabled: !!companyId,
    refetchInterval: 10000,
  });

  return {
    interventions: interventionsData?.interventions || [],
    count: interventionsData?.count || 0,
    isLoading,
  };
};
```

---

### **Hook 10 : `useBotliveMessage` - Envoyer Message au Bot**

```typescript
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCompany } from "./useCompany";

export const useBotliveMessage = () => {
  const { companyId } = useCompany();

  const sendMessage = useMutation({
    mutationFn: async ({
      userId,
      message,
      images = [],
      conversationHistory = "",
    }: {
      userId: string;
      message: string;
      images?: string[];
      conversationHistory?: string;
    }) => {
      if (!companyId) throw new Error("Company ID manquant");

      // ✅ Backend API (traitement BLIP-2, OCR, validation)
      return await api.fetch(`/botlive/message`, {
        method: "POST",
        body: JSON.stringify({
          company_id: companyId,
          user_id: userId,
          message,
          images,
          conversation_history: conversationHistory,
        }),
      });
    },
  });

  return {
    sendMessage: sendMessage.mutate,
    isLoading: sendMessage.isPending,
  };
};
```

---

## 📋 COMPOSANT DASHBOARD - Exemple Complet

```typescript
import { useStats } from "@/hooks/useStats";
import { useOrders } from "@/hooks/useOrders";
import { useInterventions } from "@/hooks/useInterventions";
import { useActivities } from "@/hooks/useActivities";
import { useCompany } from "@/hooks/useCompany";
import { useBotSessions } from "@/hooks/useBotSessions";

export const Dashboard = () => {
  const { companyId, companyName, isLoading: companyLoading } = useCompany();
  const { stats } = useStats("today");
  const { orders } = useOrders(50);
  const { interventions, count: interventionsCount } = useInterventions();
  const { activities } = useActivities();
  const { activeSession, startSession, endSession } = useBotSessions();

  if (companyLoading || !companyId) {
    return <div>Chargement...</div>;
  }

  return (
    <div>
      {/* Header */}
      <header>
        <h1>Dashboard - {companyName}</h1>
        <p>ID: {companyId}</p>
        
        {/* Toggle Mode LIVE */}
        <button
          onClick={() => {
            if (activeSession) {
              endSession(activeSession.id);
            } else {
              startSession("live");
            }
          }}
        >
          {activeSession ? "Désactiver Mode LIVE" : "Activer Mode LIVE"}
        </button>
      </header>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="CA Live Session"
          value={`${stats.ca_live_session}€`}
          variation={stats.ca_variation}
        />
        <StatCard
          title="Commandes"
          value={stats.commandes_total}
          variation={stats.commandes_variation}
        />
        <StatCard
          title="Clients Actifs"
          value={stats.clients_actifs}
        />
        <StatCard
          title="Interventions"
          value={interventionsCount}
          alert={interventionsCount > 0}
        />
      </div>

      {/* Commandes actives */}
      <OrdersTable orders={orders} />

      {/* Activité temps réel */}
      <ActivityFeed activities={activities} />

      {/* Alertes */}
      {interventionsCount > 0 && (
        <AlertBanner interventions={interventions} />
      )}
    </div>
  );
};
```

---

## ✅ CHECKLIST FINALE

### **Hooks à créer/modifier** :
- [ ] `useCompany` - Utiliser `company_rag_configs` (TEXT)
- [ ] `useConversations` - Utiliser `conversation_memory`
- [ ] `useDocuments` - Lecture seule `documents`
- [ ] `usePrompts` - Éditer prompts Botlive
- [ ] `useOrders` - Utiliser VOTRE table `orders` (UUID)
- [ ] `useActivities` - Utiliser VOTRE table `activities` (UUID)
- [ ] `useBotSessions` - Utiliser VOTRE table `bot_sessions` (UUID)
- [ ] `useStats` - Backend API
- [ ] `useInterventions` - Backend API
- [ ] `useBotliveMessage` - Backend API

### **Configuration** :
- [ ] `.env` avec `VITE_API_URL=http://localhost:8002`
- [ ] `src/lib/api.ts` créé
- [ ] Attendre migration SQL `company_mapping` (backend)

### **Tables à utiliser** :
- ✅ `company_rag_configs` (Backend - TEXT)
- ✅ `conversation_memory` (Backend)
- ✅ `documents` (Backend - lecture seule)
- ✅ `orders` (Lovable - UUID)
- ✅ `activities` (Lovable - UUID)
- ✅ `bot_sessions` (Lovable - UUID)

### **Tables à IGNORER** :
- ❌ `companies` (UUID) - Remplacé par `company_rag_configs`
- ❌ `conversations` (UUID) - Remplacé par `conversation_memory`
- ❌ `messages` (UUID) - Remplacé par `conversation_memory`

---

## 🚀 ORDRE D'IMPLÉMENTATION

1. **Créer `src/lib/api.ts`** (5 min)
2. **Créer `useCompany`** (10 min)
3. **Tester connexion avec `company_rag_configs`** (5 min)
4. **Créer hooks Supabase** (`useConversations`, `useOrders`, `useActivities`) (30 min)
5. **Créer hooks Backend API** (`useStats`, `useInterventions`, `useBotliveMessage`) (20 min)
6. **Intégrer dans Dashboard** (30 min)
7. **Tester avec backend démarré** (20 min)

**Temps total** : ~2 heures

---

## ⚠️ NOTES IMPORTANTES

1. **`company_id` est TEXT** : Ne pas essayer de convertir en UUID
2. **`company_mapping`** : Sera créé par le backend (attendre migration)
3. **Port 8002** : Backend tourne sur port 8002, pas 8000
4. **Refresh 10s** : Toutes les données temps réel se rafraîchissent toutes les 10 secondes
5. **Backend API obligatoire** : Stats, interventions, et traitement messages DOIVENT passer par Backend API

---

**Questions ? Problèmes ? Partage les erreurs console et on t'aide !**
