# 🔄 COMMANDES DE SYNCHRONISATION - Botlive Supabase

## 📦 Fichiers à synchroniser vers Ubuntu

---

## 🚀 **COMMANDES CP (WSL → Ubuntu)**

```bash
# 1. Nouveau gestionnaire Supabase
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/botlive_prompts_supabase.py" ~/ZETA_APP/CHATBOT2.0/core/botlive_prompts_supabase.py

# 2. Système hybride modifié (utilise Supabase)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/botlive_rag_hybrid.py" ~/ZETA_APP/CHATBOT2.0/core/botlive_rag_hybrid.py

# 3. Documentation intégration Supabase
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/BOTLIVE_SUPABASE_INTEGRATION.md" ~/ZETA_APP/CHATBOT2.0/BOTLIVE_SUPABASE_INTEGRATION.md

# 4. Documentation valeurs hardcodées (référence)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/BOTLIVE_HARDCODED_VALUES.md" ~/ZETA_APP/CHATBOT2.0/BOTLIVE_HARDCODED_VALUES.md

# 5. Templates universels (pour N8N)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/BOTLIVE_PROMPT_TEMPLATES.md" ~/ZETA_APP/CHATBOT2.0/BOTLIVE_PROMPT_TEMPLATES.md

# 6. Script filler Python (référence pour N8N)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/prompt_template_filler.py" ~/ZETA_APP/CHATBOT2.0/prompt_template_filler.py

# 7. Script de test valeurs hardcodées
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_hardcoded_values.py" ~/ZETA_APP/CHATBOT2.0/test_hardcoded_values.py

# 8. Prompts hardcodés (backup/référence)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/botlive_prompts_hardcoded.py" ~/ZETA_APP/CHATBOT2.0/core/botlive_prompts_hardcoded.py
```

---

## ⚡ **COMMANDE GROUPÉE (tout en une fois)**

```bash
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/botlive_prompts_supabase.py" ~/ZETA_APP/CHATBOT2.0/core/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/botlive_rag_hybrid.py" ~/ZETA_APP/CHATBOT2.0/core/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/botlive_prompts_hardcoded.py" ~/ZETA_APP/CHATBOT2.0/core/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/BOTLIVE_SUPABASE_INTEGRATION.md" ~/ZETA_APP/CHATBOT2.0/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/BOTLIVE_HARDCODED_VALUES.md" ~/ZETA_APP/CHATBOT2.0/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/BOTLIVE_PROMPT_TEMPLATES.md" ~/ZETA_APP/CHATBOT2.0/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/prompt_template_filler.py" ~/ZETA_APP/CHATBOT2.0/ && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_hardcoded_values.py" ~/ZETA_APP/CHATBOT2.0/ && \
echo "✅ Synchronisation terminée!"
```

---

## 🧪 **TESTS APRÈS SYNCHRO**

### **Test 1: Vérifier imports**
```bash
cd ~/ZETA_APP/CHATBOT2.0
source .venv/bin/activate
python -c "from core.botlive_prompts_supabase import get_prompts_manager; print('✅ Import OK')"
```

### **Test 2: Tester connexion Supabase**
```bash
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

### **Test 3: Tester valeurs hardcodées (référence)**
```bash
python test_hardcoded_values.py
```

---

## 📝 **VÉRIFICATIONS POST-SYNCHRO**

```bash
# Vérifier que les fichiers existent
ls -lh ~/ZETA_APP/CHATBOT2.0/core/botlive_prompts_supabase.py
ls -lh ~/ZETA_APP/CHATBOT2.0/core/botlive_rag_hybrid.py

# Vérifier les imports Python
cd ~/ZETA_APP/CHATBOT2.0
source .venv/bin/activate
python -c "
from core.botlive_prompts_supabase import get_prompts_manager
from core.botlive_rag_hybrid import BotliveRAGHybrid
print('✅ Tous les imports fonctionnent')
"

# Vérifier variables d'environnement
python -c "
import os
print('SUPABASE_URL:', os.getenv('SUPABASE_URL')[:30] + '...' if os.getenv('SUPABASE_URL') else '❌ MANQUANT')
print('SUPABASE_SERVICE_KEY:', '✅ Défini' if os.getenv('SUPABASE_SERVICE_KEY') else '❌ MANQUANT')
"
```

---

## ⚠️ **IMPORTANT: Variables d'environnement**

Assure-toi que `.env` contient:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

---

## 📊 **RÉSUMÉ DES FICHIERS**

| Fichier | Taille | Rôle |
|---------|--------|------|
| `core/botlive_prompts_supabase.py` | ~10 KB | **Gestionnaire Supabase** (PRINCIPAL) |
| `core/botlive_rag_hybrid.py` | ~25 KB | Système hybride modifié |
| `core/botlive_prompts_hardcoded.py` | ~15 KB | Backup/référence |
| `BOTLIVE_SUPABASE_INTEGRATION.md` | ~8 KB | Documentation intégration |
| `BOTLIVE_PROMPT_TEMPLATES.md` | ~12 KB | Templates pour N8N |
| `prompt_template_filler.py` | ~8 KB | Filler Python (référence) |
| `test_hardcoded_values.py` | ~6 KB | Tests validation |

---

## 🎯 **PROCHAINES ÉTAPES**

1. ✅ **Synchro terminée** → Tester connexion Supabase
2. ⏳ **N8N** → Créer workflow onboarding
3. ⏳ **API** → Modifier endpoint pour passer company_id
4. ⏳ **Tests** → Valider avec plusieurs entreprises

---

**Copie-colle la commande groupée dans ton terminal WSL!** 🚀
