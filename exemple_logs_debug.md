# 📋 EXEMPLE DE LOGS DEBUG - NOUVEAU SYSTÈME RAG

## 🧪 Requête Test : "Bonjour, je veux des couches pour bébé de 10kg"

```
🌍 [DÉBUT] RAG Universel: 'Bonjour, je veux des couches pour bébé...'
🏢 Company: test_company... | User: test_user...

🧹 [ÉTAPE 0] Preprocessing: 'Bonjour, je veux des couches...'
📝 Stop words supprimés: 'couches bébé 10kg'
🔤 N-grammes: 6 combinaisons

🔍 [ÉTAPE 1] MeiliSearch prioritaire...
✅ MeiliSearch OK: 3 docs, 1247 chars

🎨 [ASSEMBLAGE] Formatage contexte MeiliSearch...
✅ Assemblage MeiliSearch: 3 docs formatés

🤖 [ÉTAPE 3] Génération LLM...
📄 Contexte: 1247 caractères
✅ Prompt dynamique récupéré
🧠 Prompt total: 1589 caractères
✅ LLM réponse: 156 caractères

📊 Confiance calculée: 0.90

✅ [FIN] RAG terminé: 1847ms | Méthode: meilisearch
```

## 🔄 Exemple avec Fallback Supabase :

```
🌍 [DÉBUT] RAG Universel: 'Question très spécifique...'
🏢 Company: test_company... | User: test_user...

🧹 [ÉTAPE 0] Preprocessing: 'Question très spécifique...'
📝 Stop words supprimés: 'question spécifique'
🔤 N-grammes: 3 combinaisons

🔍 [ÉTAPE 1] MeiliSearch prioritaire...
⚠️  MeiliSearch: 0 résultats → Fallback Supabase

🔄 [ÉTAPE 2] Supabase fallback...
✅ Supabase OK: 2 docs, 847 chars

🎨 [ASSEMBLAGE] Formatage contexte Supabase...
✅ Assemblage Supabase: 2 docs formatés

🤖 [ÉTAPE 3] Génération LLM...
📄 Contexte: 847 caractères
⚠️ Prompt par défaut: No module named 'database.s
🧠 Prompt total: 1203 caractères
✅ LLM réponse: 134 caractères

📊 Confiance calculée: 0.75

✅ [FIN] RAG terminé: 2156ms | Méthode: supabase_fallback
```

## ❌ Exemple d'Erreur :

```
🌍 [DÉBUT] RAG Universel: 'Test avec erreur...'
🏢 Company: invalid_comp... | User: test_user...

🧹 [ÉTAPE 0] Preprocessing: 'Test avec erreur...'
📝 Stop words supprimés: 'test erreur'
🔤 N-grammes: 3 combinaisons

🔍 [ÉTAPE 1] MeiliSearch prioritaire...
❌ MeiliSearch erreur: Connection refused port 7700 → Fallback

🔄 [ÉTAPE 2] Supabase fallback...
❌ Supabase erreur: Invalid company_id format

❌ [ERREUR] RAG échec: No valid search results found | 456ms
```

## 🎯 Caractéristiques des Logs :

### ✅ **AVANTAGES :**
- **Concis** : Une ligne par étape importante
- **Informatif** : Données essentielles (temps, tailles, scores)
- **Visuel** : Emojis pour identification rapide
- **Structuré** : Étapes numérotées et nommées
- **Mesurable** : Métriques de performance

### 📊 **INFORMATIONS TRACKÉES :**
- Temps de traitement par étape
- Taille des contextes (caractères)
- Nombre de documents trouvés
- Scores de confiance
- Méthode utilisée (meilisearch/supabase_fallback)
- Erreurs avec messages tronqués (50 chars max)

### 🔧 **CONTRÔLE :**
- Logs via `print()` pour visibilité immédiate
- Pas de logs verbeux ou redondants
- Focus sur les métriques critiques
- Format uniforme et prévisible
