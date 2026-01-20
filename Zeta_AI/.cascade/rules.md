# 🤖 RÈGLES AUTOMATIQUES POUR WINDSURF/CASCADE

## 🎯 WORKFLOW OBLIGATOIRE

### AVANT TOUTE MODIFICATION

```powershell
# 1. Créer une sauvegarde
powershell -ExecutionPolicy Bypass -File ./scripts/auto_backup.ps1

# 2. Basculer sur branche IA
git checkout ia

# 3. Vérifier qu'on est bien sur ia
git branch
```

### PENDANT LE TRAVAIL

- ✅ Travailler UNIQUEMENT sur la branche `ia`
- ✅ Faire des commits réguliers avec messages clairs
- ✅ Format commit: "🔧 [Composant] Description"
- ❌ JAMAIS modifier directement `main`

### APRÈS MES MODIFICATIONS

```powershell
# 1. Vérifier les changements
powershell -ExecutionPolicy Bypass -File ./scripts/check_ia_changes.ps1

# 2a. Si OK - Merger dans main
git add .
git commit -m "🔧 [Description]"
git checkout main
git merge ia
git push origin main
git checkout ia

# 2b. Si KO - Annuler
git reset --hard main
```

---

## 🚫 FICHIERS INTERDITS

### NE JAMAIS TOUCHER:
- `/stable/**` - Versions verrouillées
- `/backup/**` - Sauvegardes automatiques
- `/scripts/**` - Scripts PowerShell
- `.gitignore` - Configuration Git
- `.github/workflows/**` - GitHub Actions

### MODIFICATIONS AVEC CONFIRMATION:
- `.env` - Variables d'environnement
- `app.py` - Application principale
- `database/vector_store_clean_v2.py` - Système de recherche
- `core/rag_engine.py` - Pipeline RAG

---

## 📋 COMMANDES AUTOMATIQUES

### Début de session
```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/auto_backup.ps1
git checkout ia
```

### Vérification
```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/check_ia_changes.ps1
```

### Annulation
```powershell
git reset --hard main
```

### Version stable
```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/create_stable_version_simple.ps1 -Description "Description"
```

---

## 🎯 COMPORTEMENT ATTENDU

1. **Toujours proposer** une sauvegarde avant de commencer
2. **Toujours vérifier** qu'on est sur la branche `ia`
3. **Toujours demander confirmation** avant de merger dans `main`
4. **Toujours expliquer** ce qui a été modifié
5. **Toujours proposer** de créer une version stable si tout fonctionne

---

## 🆘 EN CAS D'ERREUR

Si quelque chose ne va pas:
1. Proposer: `git reset --hard main`
2. Proposer de restaurer une version stable
3. Ne JAMAIS forcer des modifications qui cassent le code

---

## 📊 EXEMPLE DE WORKFLOW

```
USER: "Ajoute une fonction pour calculer les prix"

MOI (WINDSURF):
1. "Je vais d'abord créer une sauvegarde et basculer sur ia"
   → powershell ./scripts/auto_backup.ps1
   → git checkout ia

2. "J'ajoute la fonction dans core/price_calculator.py"
   → Modifications du code

3. "Modifications terminées. Voulez-vous vérifier?"
   → powershell ./scripts/check_ia_changes.ps1

4. "Les modifications semblent bonnes. Voulez-vous merger dans main?"
   → Si oui: git checkout main && git merge ia && git push
   → Si non: git reset --hard main
```

---

## 🔒 SÉCURITÉ

- ❌ Ne JAMAIS commit de secrets (API keys, passwords)
- ❌ Ne JAMAIS supprimer /stable ou /backup
- ❌ Ne JAMAIS forcer un push sur main
- ✅ Toujours vérifier .env est dans .gitignore
- ✅ Toujours proposer des alternatives si incertain

---

## 📚 RESSOURCES

- Guide complet: GUIDE_ANTI_DERIVE_IA.md
- Démarrage rapide: DEMARRAGE_RAPIDE.md
- Instructions IA: PROMPT_WINDSURF_IA.txt
