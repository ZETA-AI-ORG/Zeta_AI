# 🚨 PLAN B : MODE MINIMAL

## Si le serveur ne démarre TOUJOURS PAS après le dernier fix

### Étape 1 : Activer le mode minimal

```bash
# Remplacer le Procfile par la version minimale
cp Procfile.minimal Procfile

# Commit et push
git add Procfile app_minimal.py debug_start_minimal.py Procfile.minimal PLAN_B_MINIMAL.md
git commit -m "emergency: activate minimal mode to guarantee startup"
git push origin main
```

### Étape 2 : Vérifier que ça démarre

Le serveur devrait démarrer en **moins de 30 secondes** avec seulement 3 endpoints :
- `GET /` - Status
- `GET /health` - Health check
- `GET /test` - Test endpoint

### Étape 3 : Réactiver les imports progressivement

Une fois que le mode minimal fonctionne, on réactive les imports un par un dans `app.py` :

1. ✅ Imports de base (FastAPI, CORS)
2. ✅ Config et logging
3. ✅ Models (ChatRequest, etc.)
4. ✅ Database (Supabase)
5. ⚠️ RAG Engine (lazy init)
6. ⚠️ Routes (auth, messenger)
7. ❌ Image search (bloque)
8. ❌ Botlive (à tester)

### Étape 4 : Identifier le coupable exact

Pour chaque import qui bloque, on applique le fix :
- **Lazy initialization** pour les instances globales
- **Property** pour les clients async
- **Import conditionnel** dans les fonctions

## 🎯 Commandes rapides

### Activer mode minimal
```bash
cp Procfile.minimal Procfile
git add Procfile
git commit -m "emergency: minimal mode"
git push
```

### Revenir au mode normal
```bash
git checkout Procfile
git commit -m "restore: normal mode"
git push
```

## 📊 Diagnostic

Si même le mode minimal ne démarre pas, le problème vient de :
- ❌ Variables d'environnement manquantes sur Render
- ❌ Dépendances manquantes dans requirements.txt
- ❌ Problème de port binding (doit être 0.0.0.0:$PORT)
- ❌ Timeout trop court sur Render (augmenter à 10 min)
