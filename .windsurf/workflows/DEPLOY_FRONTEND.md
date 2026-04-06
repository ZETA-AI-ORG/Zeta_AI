# 🚀 Procédure de déploiement Frontend (Vercel) — ZETA AI

## 📌 Architecture
- **Source locale** : `c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0\zeta-ai-vercel` (C'est là que tu travailles)
- **Clone de déploiement** : `c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0\zeta-ai-vercel-deploy` (C'est ce dossier qui est relié à GitHub/Vercel)

## 🛠️ Étapes pour mettre à jour la prod
Pour que la version en production soit **100% identique** à ta version locale, sans conflits Git (rebase/cherry-pick), utilise cette procédure :

### 1. Synchronisation Miroir (Local ➔ Clone Deploy)
Exécute cette commande depuis la racine `CHATBOT2.0` pour copier tes fichiers modifiés vers le dossier de déploiement :
```powershell
robocopy ".\zeta-ai-vercel" ".\zeta-ai-vercel-deploy" /MIR /XD ".git" "node_modules" "dist" ".vercel" /XF ".env" ".env.*"
```
*Note : `/MIR` rend la cible identique à la source. Les dossiers sensibles (git, modules) sont exclus.*

### 2. Commit & Push (Clone Deploy ➔ GitHub)
Va dans le dossier de déploiement et envoie les modifications :
```powershell
cd ".\zeta-ai-vercel-deploy"
git add .
git commit -m "feat/fix: description des changements"
git push origin main --force
```
*Note : Le `--force` garantit que GitHub (et donc Vercel) s'aligne exactement sur ce que tu as en local, en écrasant les divergences potentielles.*

## ⚠️ Règles d'or
- **NE JAMAIS** faire de `git rebase` ou `git cherry-pick` sur le repo de prod.
- **TOUJOURS** passer par `robocopy` pour garantir l'identité des fichiers.
- **VÉRIFIER** que `zeta-ai-vercel-deploy` a bien le remote `https://github.com/kazakV3/zeta-ai.git`.

---
*Document généré le 6 avril 2026 par Cascade.*
