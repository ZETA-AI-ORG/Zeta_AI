# 🚀 DÉMARRAGE RAPIDE - SYSTÈME ANTI-DÉRIVE IA

## ⚡ INSTALLATION EN 3 COMMANDES

```powershell
# 1. Initialiser le système de protection
cd "c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0"
powershell ./scripts/init_git_protection.ps1

# 2. Lier à GitHub (remplacer TON_PSEUDO)
git remote add origin https://github.com/TON_PSEUDO/CHATBOT2.0.git
git push -u origin main dev ia

# 3. C'est prêt! 🎉
```

---

## 📋 CHECKLIST POST-INSTALLATION

### ✅ Vérifications Locales

```powershell
# Vérifier les branches
git branch -a
# Devrait afficher: main, dev, ia

# Vérifier la structure
Get-ChildItem
# Devrait contenir: /stable, /backup, /scripts, /.github
```

### ✅ Configuration GitHub

1. **Créer le dépôt**: https://github.com/new
   - Nom: `CHATBOT2.0`
   - Visibilité: Private (recommandé)
   - ❌ NE PAS cocher "Initialize with README"

2. **Protéger la branche main**:
   - Aller sur: `Settings → Branches → Add rule`
   - Branch name pattern: `main`
   - Cocher:
     - ✅ Require pull request reviews before merging
     - ✅ Require status checks to pass before merging
   - Cliquer "Create"

3. **Vérifier GitHub Actions**:
   - Aller sur: `Actions`
   - Devrait afficher: "🔍 Vérification Modifications IA"

---

## 🎯 UTILISATION QUOTIDIENNE

### 🟢 AVANT SESSION WINDSURF

```powershell
# 1. Sauvegarde automatique
powershell ./scripts/auto_backup.ps1

# 2. Basculer sur branche IA
git checkout ia

# 3. Lancer Windsurf
# → Maintenant l'IA travaille sur 'ia', pas sur 'main'
```

### 🔍 APRÈS SESSION WINDSURF

```powershell
# 1. Vérifier les modifications
powershell ./scripts/check_ia_changes.ps1

# 2a. Si les modifications sont BONNES:
git checkout main
git merge ia
git push origin main

# 2b. Si les modifications sont MAUVAISES:
git checkout ia
git reset --hard main
# → Annule TOUT ce que l'IA a fait
```

---

## 🔒 CRÉER UNE VERSION STABLE

Quand ton code fonctionne parfaitement:

```powershell
# 1. Être sur main
git checkout main

# 2. Créer version stable
powershell ./scripts/create_stable_version.ps1 -Description "Version après fix scoring"

# 3. Résultat
# → /stable/20250118_143000/ créé
# → Métadonnées + README inclus
```

---

## ♻️ RESTAURER UNE VERSION STABLE

Si l'IA a tout cassé:

```powershell
# 1. Lister les versions
Get-ChildItem stable/

# 2. Restaurer
powershell ./scripts/restore_stable_version.ps1 20250118_143000

# 3. Tester
python app.py

# 4. Commit
git add .
git commit -m "Restauration version stable"
git push origin main
```

---

## 🆘 AIDE RAPIDE

### Commandes Essentielles

| Commande | Action |
|----------|--------|
| `git status` | Voir l'état actuel |
| `git branch` | Voir les branches |
| `git checkout ia` | Basculer sur branche IA |
| `git checkout main` | Basculer sur branche main |
| `git diff main..ia` | Comparer main et ia |
| `git reset --hard main` | Annuler modifications IA |

### Scripts PowerShell

| Script | Usage |
|--------|-------|
| `auto_backup.ps1` | Sauvegarde avant session IA |
| `check_ia_changes.ps1` | Vérifier modifications IA |
| `create_stable_version.ps1` | Créer version verrouillée |
| `restore_stable_version.ps1` | Restaurer version stable |
| `init_git_protection.ps1` | Initialiser système (1× seulement) |

---

## 🎓 SCÉNARIOS COURANTS

### Scénario 1: "J'ai oublié de faire une sauvegarde"

```powershell
# Les sauvegardes automatiques sont dans /backup
Get-ChildItem backup/ | Sort-Object -Descending

# Restaurer manuellement
Copy-Item -Path "backup/20250118_120000/*" -Destination "./" -Recurse -Force
```

### Scénario 2: "L'IA a cassé le code"

```powershell
# Option 1: Annuler modifications IA
git checkout ia
git reset --hard main

# Option 2: Restaurer version stable
powershell ./scripts/restore_stable_version.ps1 20250118_143000
```

### Scénario 3: "Je veux comparer 2 versions"

```powershell
# Comparer branche ia avec main
git diff main..ia

# Voir les fichiers modifiés
git diff --name-only main..ia

# Voir les stats
git diff --stat main..ia
```

### Scénario 4: "Je veux annuler UN SEUL fichier"

```powershell
# Restaurer un fichier depuis main
git checkout main -- database/vector_store_clean_v2.py

# Vérifier
git status
```

---

## 📊 TABLEAU RÉCAPITULATIF

| Situation | Commande |
|-----------|----------|
| 🟢 Avant IA | `backup → git checkout ia` |
| 🔍 Après IA | `check → merge OU reset` |
| 🔒 Code parfait | `create_stable_version` |
| ♻️ Restaurer | `restore_stable_version` |
| 🆘 Tout annuler | `git reset --hard main` |

---

## 🔗 RESSOURCES

- 📚 **Guide complet**: [GUIDE_ANTI_DERIVE_IA.md](./GUIDE_ANTI_DERIVE_IA.md)
- 🤖 **Instructions IA**: [PROMPT_WINDSURF_IA.txt](./PROMPT_WINDSURF_IA.txt)
- 📖 **Documentation Git**: https://git-scm.com/doc
- 🐙 **Documentation GitHub**: https://docs.github.com

---

## ✅ VÉRIFICATION FINALE

Tout est OK si:

```powershell
# 1. Git initialisé
Test-Path .git
# → True

# 2. Branches créées
git branch -a
# → main, dev, ia

# 3. Structure présente
Test-Path stable, backup, scripts, .github
# → True, True, True, True

# 4. Scripts exécutables
Get-ChildItem scripts/*.ps1
# → 5 fichiers .ps1

# 5. GitHub lié
git remote -v
# → origin https://github.com/TON_PSEUDO/CHATBOT2.0.git
```

---

## 🎉 FÉLICITATIONS!

Ton projet est maintenant **100% protégé** contre les dérives IA!

**Prochaines étapes**:
1. ✅ Lire le [GUIDE_ANTI_DERIVE_IA.md](./GUIDE_ANTI_DERIVE_IA.md)
2. ✅ Configurer les protections GitHub
3. ✅ Commencer à coder en toute sécurité!

**Besoin d'aide?** Consulte le guide complet ou les scripts PowerShell.
