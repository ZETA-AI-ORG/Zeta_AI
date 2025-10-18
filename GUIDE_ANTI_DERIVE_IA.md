# 🔥 GUIDE ANTI-DÉRIVE IA - CHATBOT2.0

## 🎯 Objectif
Protéger ton code contre les modifications IA non contrôlées (Windsurf, Cursor, etc.) et pouvoir restaurer instantanément une version stable.

---

## 📂 Structure du Projet

```
CHATBOT2.0/
├── /api                    → Code API
├── /core                   → Logique métier
├── /database               → Accès données
├── /routes                 → Routes Flask
├── /stable                 → 🔒 Versions verrouillées (NE PAS TOUCHER)
├── /backup                 → 💾 Sauvegardes automatiques
├── /scripts                → 🛠️ Scripts PowerShell
│   ├── auto_backup.ps1
│   ├── check_ia_changes.ps1
│   ├── create_stable_version.ps1
│   └── restore_stable_version.ps1
├── /.github/workflows      → 🤖 GitHub Actions
├── .gitignore
└── app.py
```

---

## 🔄 ROUTINE QUOTIDIENNE

### 🟢 AVANT SESSION IA (Windsurf/Cursor)

```powershell
# 1. Créer une sauvegarde automatique
powershell ./scripts/auto_backup.ps1

# 2. Basculer sur la branche 'ia'
git checkout ia

# 3. Lancer Windsurf/Cursor
# → L'IA travaille maintenant sur la branche 'ia'
```

### 🔍 PENDANT LA SESSION

- L'IA modifie le code sur la branche `ia`
- La branche `main` reste intacte
- Les sauvegardes sont dans `/backup`

### ✅ FIN DE SESSION (Vérification)

```powershell
# 1. Vérifier les modifications IA
powershell ./scripts/check_ia_changes.ps1

# 2a. Si les modifications sont BONNES:
git checkout main
git merge ia
git push origin main

# 2b. Si les modifications sont MAUVAISES:
git checkout ia
git reset --hard main
# → Annule TOUTES les modifications IA
```

---

## 🔒 CRÉER UNE VERSION STABLE

Quand ton code fonctionne parfaitement et que tu veux le "verrouiller":

```powershell
# 1. Être sur la branche main
git checkout main

# 2. Créer une version stable
powershell ./scripts/create_stable_version.ps1 -Description "Version après fix scoring MeiliSearch"

# 3. Résultat
# → Dossier créé: /stable/20250118_143000/
# → Métadonnées: VERSION_INFO.json
# → README avec instructions de restauration
```

---

## ♻️ RESTAURER UNE VERSION STABLE

Si l'IA a tout cassé et que tu veux revenir en arrière:

```powershell
# 1. Lister les versions disponibles
Get-ChildItem stable/

# 2. Restaurer une version spécifique
powershell ./scripts/restore_stable_version.ps1 20250118_143000

# 3. Vérifier que tout fonctionne
python app.py

# 4. Commit la restauration
git add .
git commit -m "Restauration version stable 20250118_143000"
git push origin main
```

---

## 🌳 SYSTÈME DE BRANCHES

### **main** (Production)
- ✅ Code validé et testé uniquement
- ✅ Déployé en production
- ❌ Jamais de modifications directes par l'IA

### **dev** (Développement)
- ✅ Développement manuel (toi)
- ✅ Tests et expérimentations
- ✅ Merge vers `main` après validation

### **ia** (Zone IA)
- ✅ Modifications par Windsurf/Cursor
- ✅ Isolée de `main`
- ✅ Vérification avant merge

---

## 🤖 GITHUB ACTIONS (Surveillance Automatique)

Quand tu push sur la branche `ia`, GitHub Actions:
1. ✅ Compare automatiquement avec `main`
2. ✅ Liste les fichiers modifiés
3. ✅ Détecte les possibles secrets
4. ✅ Affiche un résumé dans l'onglet "Actions"

**Voir les résultats**: https://github.com/TON_PSEUDO/CHATBOT2.0/actions

---

## 🛠️ COMMANDES RAPIDES (Alias)

Ajoute ces alias à ton PowerShell profile:

```powershell
# Ouvrir le profile
notepad $PROFILE

# Ajouter ces lignes:
function gs { git status }
function gd { git diff }
function ga { git add . }
function gc { param($msg) git commit -m $msg }
function gp { git push origin main }
function gb { param($branch) git checkout -b $branch }
function backup { powershell ./scripts/auto_backup.ps1 }
function check { powershell ./scripts/check_ia_changes.ps1 }
```

Ensuite:
```powershell
# Recharger le profile
. $PROFILE

# Utiliser les alias
gs              # git status
backup          # Sauvegarde automatique
check           # Vérifier modifications IA
```

---

## 📊 TABLEAU RÉCAPITULATIF

| Action | Commande | Quand |
|--------|----------|-------|
| 💾 Sauvegarde auto | `powershell ./scripts/auto_backup.ps1` | Avant session IA |
| 🔍 Vérifier modifs IA | `powershell ./scripts/check_ia_changes.ps1` | Après session IA |
| 🔒 Version stable | `powershell ./scripts/create_stable_version.ps1` | Code parfait |
| ♻️ Restaurer stable | `powershell ./scripts/restore_stable_version.ps1 TIMESTAMP` | Après dérive IA |
| 🌳 Branche IA | `git checkout ia` | Avant session IA |
| ✅ Fusionner IA → main | `git checkout main && git merge ia` | Si modifs OK |
| ❌ Annuler modifs IA | `git checkout ia && git reset --hard main` | Si modifs KO |

---

## 🚨 SCÉNARIOS D'URGENCE

### Scénario 1: L'IA a tout cassé
```powershell
# 1. Annuler les modifications IA
git checkout ia
git reset --hard main

# 2. Ou restaurer une version stable
powershell ./scripts/restore_stable_version.ps1 20250118_143000
```

### Scénario 2: J'ai oublié de faire une sauvegarde
```powershell
# Les sauvegardes automatiques sont dans /backup
Get-ChildItem backup/ | Sort-Object -Descending

# Restaurer manuellement depuis /backup
Copy-Item -Path "backup/20250118_120000/*" -Destination "./" -Recurse -Force
```

### Scénario 3: Je veux comparer 2 versions
```powershell
# Comparer branche ia avec main
git diff main..ia

# Comparer 2 commits
git diff COMMIT1 COMMIT2

# Comparer 2 versions stables
# → Utiliser un outil de diff (WinMerge, Beyond Compare, etc.)
```

---

## 🎓 BONNES PRATIQUES

### ✅ À FAIRE
1. **Toujours** créer une sauvegarde avant session IA
2. **Toujours** travailler sur la branche `ia` avec Windsurf
3. **Toujours** vérifier les modifications avant merge
4. Créer une version stable après chaque grosse feature
5. Commit régulièrement sur `main`

### ❌ À NE PAS FAIRE
1. Laisser l'IA modifier directement `main`
2. Supprimer les dossiers `/stable` ou `/backup`
3. Commit des secrets (API keys, passwords)
4. Merger sans vérifier les modifications
5. Travailler sans sauvegarde

---

## 🔗 INITIALISATION GIT & GITHUB

### Première fois (si pas encore fait):

```powershell
# 1. Initialiser Git
cd "c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0"
git init

# 2. Créer les branches
git checkout -b main
git add .
git commit -m "Version initiale stable"

git checkout -b dev
git checkout -b ia

# 3. Lier à GitHub
git remote add origin https://github.com/TON_PSEUDO/CHATBOT2.0.git
git push -u origin main
git push -u origin dev
git push -u origin ia
```

### Protection de la branche main (sur GitHub):
1. Va sur https://github.com/TON_PSEUDO/CHATBOT2.0/settings/branches
2. Clique sur "Add rule"
3. Branch name pattern: `main`
4. Coche:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
5. Save

---

## 📞 SUPPORT

Si tu rencontres un problème:
1. Vérifie les logs: `git log --oneline`
2. Vérifie les branches: `git branch -a`
3. Vérifie les modifications: `git status`
4. Restaure une version stable si nécessaire

---

## 🎯 RÉSUMÉ EN 3 ÉTAPES

```
🟢 AVANT IA:
   backup → git checkout ia

🔍 APRÈS IA:
   check → Si OK: merge → Si KO: reset

🔒 CODE PARFAIT:
   create_stable_version
```

**Tu es maintenant protégé contre toute dérive IA! 🛡️**
