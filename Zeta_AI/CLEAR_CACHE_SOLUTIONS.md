# 🧹 SOLUTIONS POUR VIDER LE CACHE PROMPT

## 🎯 **PROBLÈME IDENTIFIÉ**
Le cache prompt empêche l'utilisation du nouveau prompt avec les règles de tarification. Le système continue d'utiliser l'ancien prompt mis en cache.

## 🚀 **SOLUTIONS IMPLÉMENTÉES**

### **1. 📜 Script Python : `clear_prompt_cache.py`**

#### **Usage Global**
```bash
python clear_prompt_cache.py
```

#### **Usage Entreprise Spécifique**
```bash
python clear_prompt_cache.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3
```

#### **Fonctionnalités**
- ✅ Vide le cache unifié (unified_cache_system)
- ✅ Vide le cache Supabase
- ✅ Vide les clés Redis
- ✅ Mode global ou par entreprise
- ✅ Confirmation du succès

### **2. 🌐 Endpoints API : `routes/cache_monitoring.py`**

#### **Vider Cache Prompt Global**
```bash
curl -X POST http://127.0.0.1:8001/cache/clear-prompt-cache
```

**Réponse :**
```json
{
  "status": "success",
  "message": "Cache prompt vidé avec succès",
  "details": {
    "unified_cache_cleared": true,
    "redis_keys_cleared": 3,
    "next_call_will_reload": true
  }
}
```

#### **Vider Cache Prompt Entreprise**
```bash
curl -X POST http://127.0.0.1:8001/cache/clear-prompt-cache/MpfnlSbqwaZ6F4HvxQLRL9du0yG3
```

**Réponse :**
```json
{
  "status": "success",
  "message": "Cache prompt vidé pour l'entreprise MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
  "details": {
    "company_cache_cleared": true,
    "redis_keys_cleared": 5,
    "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
  }
}
```

## 🔄 **PROCESSUS RECOMMANDÉ**

### **Après Modification du Prompt**

1. **Vider le cache prompt :**
   ```bash
   python clear_prompt_cache.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3
   ```

2. **Tester une requête :**
   ```bash
   curl -X POST http://127.0.0.1:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"je veux 2 paquets de couche culottes 13kg","company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"testuser123"}'
   ```

3. **Vérifier les logs :**
   - Chercher `[PROMPT_CACHE] ❌ Miss` (cache vidé)
   - Puis `[PROMPT_CACHE] 📥 DB fetch` (rechargement)
   - Enfin vérifier que la réponse utilise les prix explicites

## 🎯 **VALIDATION DU NOUVEAU PROMPT**

### **Ancien Comportement (avec cache)**
```
Réponse: "3 × 5.500 = 16.500 FCFA"  ❌ INCORRECT
```

### **Nouveau Comportement (après clear cache)**
```
Réponse: "Selon nos tarifs: 13.500 FCFA pour 3 paquets"  ✅ CORRECT
```

## 📊 **LOGS À SURVEILLER**

### **Cache Miss (Bon Signe)**
```
[TRACE][PROMPT_CACHE]: ❌ Miss: MpfnlSbq...
[TRACE][PROMPT_CACHE]: 📥 DB fetch: MpfnlSbq... | 813ms | 3686 chars
```

### **Cache Hit (Mauvais Signe si prompt modifié)**
```
[TRACE][PROMPT_CACHE]: ✅ Hit: MpfnlSbq... | 2949 chars
```

## 🚀 **COMMANDES DE SYNCHRONISATION**

```bash
# 1. Script de nettoyage cache
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/clear_prompt_cache.py" ~/ZETA_APP/CHATBOT2.0/clear_prompt_cache.py

# 2. Endpoints API modifiés
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/routes/cache_monitoring.py" ~/ZETA_APP/CHATBOT2.0/routes/cache_monitoring.py

# 3. Logs détaillés (si pas encore fait)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/diagnostic_logger.py" ~/ZETA_APP/CHATBOT2.0/core/diagnostic_logger.py
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/database/vector_store_clean.py" ~/ZETA_APP/CHATBOT2.0/database/vector_store_clean.py
```

## 🔧 **WORKFLOW COMPLET**

### **1. Synchroniser les fichiers**
```bash
# Copier tous les fichiers modifiés
```

### **2. Vider le cache prompt**
```bash
cd ~/ZETA_APP/CHATBOT2.0
python clear_prompt_cache.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3
```

### **3. Tester avec logs détaillés**
```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"je veux 2 paquets de couche culottes 13kg","company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"testuser123"}'
```

### **4. Vérifier les résultats**
- ✅ Cache prompt rechargé depuis DB
- ✅ Nouveau prompt avec règles tarification utilisé
- ✅ Prix explicites utilisés (9.800 FCFA pour 2 paquets)
- ✅ Logs détaillés montrent contenu documents
- ✅ Analyse routing identifie problèmes

## 🎯 **RÉSULTAT ATTENDU**

Après nettoyage du cache, le système devrait :
1. **Recharger le prompt** depuis la base de données
2. **Appliquer les nouvelles règles** de tarification
3. **Utiliser les prix explicites** au lieu des calculs linéaires
4. **Afficher les logs détaillés** pour diagnostic

**Le prochain test montrera si les corrections fonctionnent !** 🚀
