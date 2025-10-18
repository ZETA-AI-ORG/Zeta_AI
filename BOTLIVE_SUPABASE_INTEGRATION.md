# 🗄️ BOTLIVE - INTÉGRATION SUPABASE (Multi-entreprises)

## 📋 Résumé des modifications

Le système Botlive utilise maintenant **Supabase** pour stocker et récupérer les prompts dynamiquement par `company_id`, permettant un système **multi-entreprises**.

---

## ✅ Modifications effectuées

### **1️⃣ Structure Supabase**

**Table**: `company_rag_configs`

**Nouvelles colonnes ajoutées**:
```sql
- prompt_botlive_groq_70b (TEXT)
- prompt_botlive_deepseek_v3 (TEXT)
- botlive_prompts_updated_at (TIMESTAMPTZ)
- botlive_prompts_version (TEXT, default: '1.0')
```

**Contrainte importante**:
- `rag_behavior` doit être: `'always'`, `'on_demand'`, ou `'never'`

---

### **2️⃣ Nouveau fichier: `botlive_prompts_supabase.py`**

**Classe principale**: `BotlivePromptsManager`

**Fonctionnalités**:
- ✅ Connexion Supabase automatique
- ✅ Récupération prompts par `company_id`
- ✅ Cache en mémoire pour performance
- ✅ Formatage avec variables dynamiques
- ✅ Gestion erreurs robuste

**Méthodes clés**:
```python
# Récupérer un prompt
prompt = manager.get_prompt(company_id, "groq-70b")

# Formater avec variables
formatted = manager.format_prompt(
    company_id="MpfnlSbq...",
    llm_choice="groq-70b",
    conversation_history="...",
    question="...",
    detected_objects="...",
    filtered_transactions="...",
    expected_deposit="2000"
)

# Infos entreprise
info = manager.get_company_info(company_id)

# Vider cache
manager.clear_cache(company_id)
```

---

### **3️⃣ Modifications: `botlive_rag_hybrid.py`**

**Changements**:

1. **Import modifié**:
```python
# AVANT
from .botlive_prompts_hardcoded import format_prompt, get_prompt_info

# APRÈS
from .botlive_prompts_supabase import get_prompts_manager
```

2. **Constructeur modifié**:
```python
# AVANT
def __init__(self):
    self.router = hyde_router

# APRÈS
def __init__(self, company_id: str = None):
    self.router = hyde_router
    self.company_id = company_id  # ← Stocker company_id
    self.prompts_manager = get_prompts_manager()  # ← Gestionnaire Supabase
```

3. **Récupération prompt modifiée**:
```python
# AVANT
prompt = format_prompt(
    llm_choice,
    conversation_history=...,
    question=...,
    ...
)

# APRÈS
prompt = self.prompts_manager.format_prompt(
    company_id=self.company_id,  # ← Ajout company_id
    llm_choice=llm_choice,
    conversation_history=...,
    question=...,
    ...
)
```

---

## 🔄 Workflow complet

### **1️⃣ ONBOARDING (N8N)**

```
Frontend (React)
    ↓ Données formulaire
N8N Webhook
    ↓
1. Récupérer données entreprise
2. Charger templates (BOTLIVE_PROMPT_TEMPLATES.md)
3. Remplir placeholders:
   - {{COMPANY_NAME}} → "Rue du Grossiste"
   - {{BOT_NAME}} → "Jessica"
   - {{SUPPORT_PHONE}} → "+225 07 87 36 07 57"
   - etc...
4. INSERT/UPDATE Supabase:
   INSERT INTO company_rag_configs (
       company_id,
       rag_behavior,
       prompt_botlive_groq_70b,
       prompt_botlive_deepseek_v3,
       botlive_prompts_version
   ) VALUES (
       'MpfnlSbq...',
       'always',
       '[PROMPT GROQ REMPLI]',
       '[PROMPT DEEPSEEK REMPLI]',
       '1.0'
   )
```

---

### **2️⃣ RUNTIME (Botlive)**

```python
# À chaque requête Botlive
async def handle_botlive_request(company_id, user_id, message, context):
    # 1. Initialiser avec company_id
    botlive = BotliveRAGHybrid(company_id=company_id)
    
    # 2. Traiter requête (prompts récupérés automatiquement depuis Supabase)
    response = await botlive.process_request(
        user_id=user_id,
        message=message,
        context=context
    )
    
    return response
```

**Flux interne**:
```
1. Routage intelligent (DeepSeek vs Groq)
2. Récupération prompt depuis Supabase (avec cache)
3. Formatage avec variables dynamiques
4. Appel LLM
5. Retour réponse
```

---

## 📊 Avantages du système

### ✅ **Multi-entreprises**
- Chaque entreprise a ses propres prompts
- Isolation par `company_id`
- Scalable à l'infini

### ✅ **Performance**
- Cache en mémoire (pas de requête Supabase à chaque fois)
- Lecture ultra-rapide (index sur `company_id`)
- Pas de traitement runtime

### ✅ **Maintenance**
- Modifier un prompt = UPDATE SQL (pas de redéploiement)
- Versionning des prompts (`botlive_prompts_version`)
- Historique des MAJ (`botlive_prompts_updated_at`)

### ✅ **Flexibilité**
- Chaque entreprise peut avoir des prompts différents
- Facile d'ajouter de nouvelles entreprises
- Templates réutilisables

---

## 🧪 Tests

### **Test 1: Récupération depuis Supabase**

```bash
cd ~/ZETA_APP/CHATBOT2.0
source .venv/bin/activate
python -m core.botlive_prompts_supabase
```

**Résultat attendu**:
```
🧪 TEST BOTLIVE PROMPTS SUPABASE
================================================================================
📊 Informations entreprise:
   - Nom: Rue du Grossiste
   - IA: Jessica
   - Secteur: produits bébés

📝 Test récupération prompts:
   ✅ Groq 70B: 8339 caractères (~2084 tokens)
   ✅ DeepSeek V3: 5797 caractères (~1449 tokens)

✅ TOUS LES TESTS RÉUSSIS!
```

---

### **Test 2: Intégration complète**

```python
# Test dans un script Python
from core.botlive_rag_hybrid import BotliveRAGHybrid

async def test():
    # Initialiser avec company_id
    botlive = BotliveRAGHybrid(company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
    
    # Test requête
    response = await botlive.process_request(
        user_id="test_user",
        message="Bonjour",
        context={}
    )
    
    print(response)

# Exécuter
import asyncio
asyncio.run(test())
```

---

## 📝 Variables d'environnement requises

Dans `.env`:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

---

## 🔧 Commandes SQL utiles

### **Voir tous les prompts**:
```sql
SELECT 
    company_id,
    company_name,
    ai_name,
    LENGTH(prompt_botlive_groq_70b) as groq_length,
    LENGTH(prompt_botlive_deepseek_v3) as deepseek_length,
    botlive_prompts_version,
    botlive_prompts_updated_at
FROM company_rag_configs
WHERE prompt_botlive_groq_70b IS NOT NULL;
```

### **Mettre à jour un prompt**:
```sql
UPDATE company_rag_configs
SET 
    prompt_botlive_groq_70b = '[NOUVEAU PROMPT]',
    botlive_prompts_updated_at = NOW(),
    botlive_prompts_version = '1.1'
WHERE company_id = 'MpfnlSbqwaZ6F4HvxQLRL9du0yG3';
```

### **Vider le cache Python après MAJ**:
```python
from core.botlive_prompts_supabase import get_prompts_manager

manager = get_prompts_manager()
manager.clear_cache('MpfnlSbqwaZ6F4HvxQLRL9du0yG3')
```

---

## 📂 Fichiers modifiés/créés

| Fichier | Type | Description |
|---------|------|-------------|
| `core/botlive_prompts_supabase.py` | **NOUVEAU** | Gestionnaire prompts Supabase |
| `core/botlive_rag_hybrid.py` | **MODIFIÉ** | Utilise Supabase au lieu de hardcodé |
| `BOTLIVE_SUPABASE_INTEGRATION.md` | **NOUVEAU** | Cette documentation |
| `BOTLIVE_PROMPT_TEMPLATES.md` | Existant | Templates pour N8N |
| `prompt_template_filler.py` | Existant | Filler Python (référence) |

---

## 🚀 Prochaines étapes

### **1. N8N Onboarding**
- Créer workflow N8N pour remplir templates
- Insérer dans Supabase lors de l'onboarding

### **2. Endpoint API**
- Modifier endpoint Botlive pour passer `company_id`
- Initialiser `BotliveRAGHybrid(company_id=...)`

### **3. Tests production**
- Tester avec plusieurs company_id
- Vérifier cache et performance
- Monitorer logs Supabase

---

**Version**: 1.0  
**Date**: 2025-10-14  
**Statut**: ✅ Prêt pour intégration N8N  
**Architecture**: Multi-entreprises avec Supabase
