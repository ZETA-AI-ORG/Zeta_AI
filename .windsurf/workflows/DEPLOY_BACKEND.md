---
description: Déploiement backend ZETA AI sur VPS Contabo (reproductible à la chaîne)
---

# 🚀 DÉPLOIEMENT BACKEND VPS — Processus reproductible

## 📌 Principes de base (à ne jamais oublier)

- **Backend** → VPS Contabo `194.60.201.228` via Docker (`zeta-backend` + `zeta-redis`)
- **Frontend** → Vercel (passe par `zeta-ai-vercel-deploy/` et `robocopy`) — **JAMAIS** dans un commit backend
- **Source de vérité** = VPS en prod. En cas de doute local vs VPS, on s'aligne sur le VPS.
- **Branche** : `main` uniquement pour le backend
- **SSH key** : `$HOME\.ssh\deploy_key`
- **Utilisateur VPS** : `zetaadmin`
- **Path VPS** : `~/CHATBOT2.0/app`

---

## ⚠️ Pourquoi on bypasse `deploy.ps1`

Le script `deploy.ps1` a plusieurs défauts connus qui peuvent casser le déploiement :

### Problèmes du script
1. **Ligne 172** : `git add -- $deployableFiles` — PowerShell peut interpréter mal les chemins avec espaces ou caractères spéciaux, certains fichiers sont silencieusement ignorés.
2. **Ligne 173** : `(git diff --cached --name-only).Count` — bug PowerShell : si un seul fichier est stagé, `.Count` renvoie la longueur du string (ex: 42) au lieu de 1.
3. **Ligne 181** : `git pull` direct **sans `git stash` préalable**. Si un fichier a été modifié manuellement sur le VPS (ce qui est interdit mais arrive), le pull échoue avec un merge conflict et le backend reste sur l'ancien code.
4. **Pattern d'exclusion `prompt_universel*.md`** (ligne 95) : exclut `prompt_universel_v2.md`, **MAIS ce fichier est requis au runtime** par `core/botlive_prompts_supabase.py::_load_zeta_core()`. Si on passe par le script, le V2 prompt n'arrive JAMAIS en prod.
5. **CRLF/LF** : PowerShell ajoute parfois `\r\n` dans les commandes SSH, corrompant les commandes bash côté VPS.

### Conclusion
**On bypasse complètement le script** et on fait du `git add` + `git push` + SSH manuel, plus court et plus sûr.

---

## ✅ CE QUI VA SUR LE VPS (backend uniquement)

### Fichiers runtime obligatoires
- **Code Python** : `config.py`, `core/*.py`, `routes/*.py`, `api/*.py`, `services/*.py`, `intents/*.py`, `database/*.py`, `ingestion/*.py`, `tools/*.py`
- **Prompts runtime** : `prompt_universel_v2.md` (lu par `_load_zeta_core()`)
- **Configuration Docker** : `Dockerfile`, `docker-compose.yml`, `requirements.txt` — ⚠️ **nécessitent un rebuild manuel** (voir plus bas)
- **Templates** : `templates/*.html` (si utilisé par Flask/FastAPI)
- **Scripts d'init** : `start.py`, `app.py` (si utilisé)
- **Migrations SQL** : `migrations/*.sql`, `sql/*.sql`

### Fichiers interdits (à exclure systématiquement)
- ❌ `zeta-ai-vercel/` et `zeta-ai-vercel-deploy/` → frontend Vercel
- ❌ `frontend/` → archive frontend
- ❌ `.windsurf/` → config IDE local
- ❌ `scratch/` → fichiers de travail temporaires
- ❌ `tests/reports/`, `results/` → rapports de tests
- ❌ `.venv/`, `__pycache__/`, `.pytest_cache/` → env local
- ❌ `*.tar.gz`, `*.pt`, `*.pkl` → gros binaires
- ❌ `*.txt` (sauf `requirements.txt`) → fichiers parasites (S.txt, Sans titre.txt, etc.)
- ❌ `.env`, `.env.*` → secrets
- ❌ `docs/*.md` optionnel — pas critique runtime, OK si présents (pas de risque), mais pas obligatoire
- ❌ `*.md` de référence (READMEs, guides) — pas runtime
- ❌ Fichiers vides ou sans contenu

### Règle absolue : **ne JAMAIS envoyer de fichier vide ou sans intérêt**
Avant commit, vérifier la taille de chaque fichier :
```powershell
Get-Item <fichier> | Select Name, Length
```
Si `Length == 0` → ne pas ajouter.

---

## 🔨 PROCESSUS DE DÉPLOIEMENT (étapes reproductibles)

### Étape 1 — Identifier les fichiers backend modifiés

```powershell
cd "C:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0"
git status --short 2>&1 | Select-String -NotMatch "zeta-ai-vercel"
```

**Lire attentivement** la sortie :
- ` M <fichier>` = modifié non-stagé
- `M  <fichier>` = modifié stagé
- `??` = nouveau fichier non tracké
- `A  <fichier>` = ajouté au staging

### Étape 2 — Vérifier qu'aucun fichier n'est vide

```powershell
Get-Item <liste-des-fichiers> | Select-Object Name, Length | Format-Table -AutoSize
```

Tout fichier avec `Length == 0` → **ne pas l'inclure**.

### Étape 3 — Add ciblé (jamais `git add .` ou `git add -A`)

Toujours lister explicitement chaque fichier :

```powershell
git add <fichier1> <fichier2> ... <prompt_universel_v2.md>
```

**Ne pas utiliser de glob** (`core/*.py`) — trop risqué, peut inclure des fichiers non désirés.

### Étape 4 — Vérifier ce qui est stagé (avant commit)

```powershell
git status --short config.py core/<fichier>.py prompt_universel_v2.md
```

Confirmer que **seuls les fichiers voulus** ont un `M ` ou `A ` en début de ligne.

**Astuce CRLF** : si Git a auto-corrigé les line endings (`LF will be replaced by CRLF`), certains fichiers stagés peuvent "disparaître" du diff — c'est normal, ils sont juste nettoyés.

### Étape 5 — Commit avec message explicite

Format recommandé :
```
feat(backend): <description courte>
```

Exemples :
- `feat(backend): V2 unified prompt + session msg barrier (15-25) + fix double get_company_info`
- `fix(backend): rollback simplified_prompt_system.py to working version`
- `perf(backend): elastic routing + phase-adaptive max_tokens`

```powershell
git commit -m "feat(backend): <description>"
```

### Étape 6 — Push vers GitHub (`origin/main`)

```powershell
git push origin main 2>&1
```

**Vérifier la sortie** : doit afficher `<hash>..<hash>  main -> main`.

### Étape 7 — Pull côté VPS (avec stash de sécurité)

Commande SSH **inline** (pas de heredoc, pas de `\r\n`) :

```powershell
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; git stash; git pull origin main; echo '---ETAT---'; docker compose ps; echo '---HEALTH---'; curl -fsS http://localhost:8002/ingestion/health; echo ''"
```

**Décomposition** :
- `git stash` → met de côté toute modif locale non commitée sur le VPS (sécurité contre merge conflict)
- `git pull origin main` → récupère le nouveau code
- `docker compose ps` → confirme que `zeta-backend` et `zeta-redis` sont `Up (healthy)`
- `curl http://localhost:8002/ingestion/health` → doit retourner `{"status":"healthy"}`

### Étape 8 — Restart du container (CRUCIAL)

**Le `git pull` ne suffit PAS** : Docker a chargé l'ancien code Python en mémoire à l'init du container. Pour activer les nouvelles modifs :

```powershell
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; docker compose restart zeta-backend; sleep 8; docker compose ps; curl -fsS http://localhost:8002/ingestion/health"
```

**Downtime** : ~8-12 secondes (restart simple, pas de rebuild).

### Étape 9 — Vérification post-déploiement

```powershell
# Logs du container (voir les 50 dernières lignes)
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "docker compose -f ~/CHATBOT2.0/app/docker-compose.yml logs --tail=50 zeta-backend"

# Vérifier un log spécifique (ex: V2 activé)
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "docker compose -f ~/CHATBOT2.0/app/docker-compose.yml logs --tail=200 zeta-backend | grep -E 'V2|BARRIERE|PHASE'"
```

---

## 🔥 CAS PARTICULIER : Dockerfile / requirements.txt modifié

**Si tu modifies** `Dockerfile`, `requirements.txt`, ou `docker-compose.yml` :
- Un simple restart **NE SUFFIT PAS**
- Il faut un **rebuild complet** du container

```powershell
# Build + restart (downtime ~3-5 min selon la taille de requirements.txt)
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; docker compose build zeta-backend; docker compose up -d; sleep 10; docker compose ps; curl -fsS http://localhost:8002/ingestion/health"
```

⚠️ **Toujours demander validation humaine** avant un rebuild (règle utilisateur stricte).

---

## 🆘 ROLLBACK EN CAS DE PROBLÈME

### Si le backend ne répond plus après déploiement

```powershell
# 1. Voir les derniers commits sur le VPS
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; git log --oneline -5"

# 2. Revenir au commit précédent (le backend en prod avant ton push)
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; git reset --hard HEAD~1; docker compose restart zeta-backend; sleep 8; curl -fsS http://localhost:8002/ingestion/health"
```

### Si le rollback ne suffit pas

Rollback plus profond (ex: 3 commits en arrière) :
```powershell
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; git reset --hard HEAD~3; docker compose restart zeta-backend"
```

---

## 📋 CHECKLIST AVANT CHAQUE DÉPLOIEMENT

- [ ] Je suis dans `CHATBOT2.0/` (pas dans un sous-dossier)
- [ ] `git status --short` ne montre **aucun** fichier frontend (zeta-ai-vercel*)
- [ ] Tous les fichiers que je vais push ont une taille > 0
- [ ] Je liste explicitement chaque fichier dans `git add` (pas de `.` ou `-A`)
- [ ] Le message de commit est explicite (`feat(backend): ...`)
- [ ] Après push, je vérifie que GitHub a bien reçu (`main -> main` dans la sortie)
- [ ] Le SSH pull a affiché `Fast-forward` et pas de conflit
- [ ] `docker compose ps` montre `Up (healthy)` pour `zeta-backend`
- [ ] `curl /ingestion/health` retourne `{"status":"healthy"}`
- [ ] Restart du container effectué pour activer les modifs Python
- [ ] Logs vérifiés pour confirmer que les nouvelles features tournent (ex: `V2`, `BARRIERE`, `PHASE`)

---

## 🎯 RÉSUMÉ ULTRA-COMPACT (à mémoriser)

```powershell
# 1. Statut local (filtré sans frontend)
cd "C:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0"
git status --short 2>&1 | Select-String -NotMatch "zeta-ai-vercel"

# 2. Add explicite des fichiers backend voulus
git add <fichiers-backend>

# 3. Commit + push
git commit -m "feat(backend): <description>"
git push origin main

# 4. Pull VPS + health
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; git stash; git pull origin main; docker compose ps; curl -fsS http://localhost:8002/ingestion/health; echo ''"

# 5. Restart container pour activer
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app; docker compose restart zeta-backend; sleep 8; curl -fsS http://localhost:8002/ingestion/health"
```

---

## 📞 CONTACTS / RÉFÉRENCES

- **VPS IP** : `194.60.201.228`
- **SSH user** : `zetaadmin`
- **SSH key** : `$HOME\.ssh\deploy_key`
- **Backend path** : `~/CHATBOT2.0/app`
- **Backend port** : `8002`
- **Redis port** : `6379`
- **wa-bridge** (hors Docker) : `127.0.0.1:3001` (service systemd, **ne pas toucher** via docker compose)
- **GitHub** : `https://github.com/ZETA-AI-ORG/Zeta_AI.git`

---

**Dernière mise à jour** : 17 avril 2026 (après succès déploiement V2 + barrière conversion)
