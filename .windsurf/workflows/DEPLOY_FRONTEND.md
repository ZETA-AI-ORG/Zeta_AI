# 🚀 Procédure de déploiement Frontend (Vercel) — ZETA AI

## 📌 Architecture
```
┌─────────────────────────┐     ┌──────────────────────────┐     ┌─────────────┐     ┌─────────┐
│  zeta-ai-vercel/        │ ──► │  zeta-ai-vercel-deploy/  │ ──► │   GitHub    │ ──► │  Vercel │
│  (Workspace source)     │     │  (Clone miroir + .git)   │     │  (Remote)   │     │  (Prod) │
└─────────────────────────┘     └──────────────────────────┘     └─────────────┘     └─────────┘
         ↑                              ↓
    Tu modifies ici              Robocopy /MIR
```

- **Source locale** : `c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0\zeta-ai-vercel` — C'est là que tu codes
- **Clone de déploiement** : `c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0\zeta-ai-vercel-deploy` — Relié à GitHub/Vercel
- **Remote** : `https://github.com/kazakV3/zeta-ai.git`

---

## 🚀 Déploiement Rapide (ONE-LINER)

### Commande unique — Copier/Coller depuis la racine CHATBOT2.0 :

```powershell
robocopy ".\zeta-ai-vercel" ".\zeta-ai-vercel-deploy" /MIR /XD ".git" "node_modules" "dist" ".vercel" /XF ".env" ".env.*" /W:1 /R:1 >$null; cd ".\zeta-ai-vercel-deploy"; git add .; git commit -m "$(Read-Host 'Message commit')" --quiet; git push origin main --force; cd ".."; Write-Host "✅ DEPLOY LANCÉ" -ForegroundColor Green
```

**Ce que ça fait :**
1. `robocopy /MIR` — Synchro miroir (exclut .git, node_modules, dist, .env)
2. `cd` + `git add/commit/push --force` — Commit + push en 1 commande
3. Retour racine + confirmation verte

---

## 📝 Schéma de commit recommandé

```
<type>(<scope>): <description courte>

[optional body]
```

**Types :**
- `feat` — Nouvelle fonctionnalité
- `fix` — Correction de bug
- `ui` — Changement visuel/CSS
- `refactor` — Refactoring code
- `chore` — Maintenance, dépendances

**Scopes courants :**
- `pages/settings` — Page Settings
- `pages/balance` — Pages Solde/Recharge
- `components/header` — Composants header
- `dashboard` — Section dashboard
- `catalogue` — Pages catalogue

**Exemples :**
```
fix(ui/pages): gaps header — reduce padding 16px→4px
feat(dashboard): real-time metrics with Supabase channels
fix(pages/balance): Wave payment flow + external browser
ui(components): BotSelector overlay dropdown
```

---

## 🛠️ Étapes détaillées (si besoin de debug)

### 1. Synchronisation Miroir (Local ➔ Clone Deploy)
```powershell
robocopy ".\zeta-ai-vercel" ".\zeta-ai-vercel-deploy" /MIR /XD ".git" "node_modules" "dist" ".vercel" /XF ".env" ".env.*" /W:1 /R:1
```
*Note : `/MIR` rend la cible **identique** à la source. Les dossiers sensibles sont exclus.*

### 2. Commit & Push (Clone Deploy ➔ GitHub)
```powershell
cd ".\zeta-ai-vercel-deploy"
git add .
git status --short  # Vérifier ce qui part en prod
git commit -m "type(scope): description"
git push origin main --force
```
*Le `--force` garantit que GitHub/Vercel s'aligne exactement sur ton local.*

### 3. Vérification Vercel
- Dashboard : https://vercel.com/dashboard
- Build logs : ~30-60s pour le build
- Preview URL : générée automatiquement

---

## ⚠️ Règles d'or

| ❌ INTERDIT | ✅ OBLIGATOIRE |
|-------------|----------------|
| `git rebase` sur le repo de prod | Toujours passer par `robocopy /MIR` |
| `git cherry-pick` | `--force` sur le push |
| Modifier directement dans `zeta-ai-vercel-deploy` | Modifier uniquement dans `zeta-ai-vercel` |
| Commit partiel/incomplet | Vérifier `git status` avant push |

---

## 🔧 Alias PowerShell (Optionnel)

Ajoute dans ton `$PROFILE` pour un raccourci permanent :

```powershell
function Deploy-Frontend {
    param([string]$msg = "update: frontend sync")
    robocopy ".\zeta-ai-vercel" ".\zeta-ai-vercel-deploy" /MIR /XD ".git" "node_modules" "dist" ".vercel" /XF ".env" ".env.*" /W:1 /R:1 >$null
    cd ".\zeta-ai-vercel-deploy"
    git add .
    git commit -m "$msg" --quiet
    git push origin main --force
    cd ".."
    Write-Host "🚀 DEPLOYÉ → Vercel build en cours..." -ForegroundColor Green
}
Set-Alias deployfe Deploy-Frontend
```

**Usage après :**
```powershell
deployfe "fix(ui): gaps header padding"
```

---

## 🆘 Rollback rapide

Si problème en production :
```powershell
cd ".\zeta-ai-vercel-deploy"
git log --oneline -5  # Voir les commits
git reset --hard HEAD~1  # Annuler dernier commit
git push origin main --force  # Rollback Vercel
```

---

*Document mis à jour le 16 avril 2026 — Procédure optimisée one-liner*
