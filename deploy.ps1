# ============================================================
# deploy.ps1 — Script de déploiement backend ZETA AI
# VPS : 194.60.201.228 | user : zetaadmin | app : ~/CHATBOT2.0/app
# ============================================================
#
# ARCHITECTURE VPS (ne pas oublier) :
#   - zeta-backend  → container Docker, port 8002, géré par docker-compose.yml
#   - zeta-redis    → container Docker, port 6379, géré par docker-compose.yml
#   - zeta-wa-bridge → process NODE DIRECT (/opt/zeta-wa-bridge/server.js, pid variable)
#                      PAS dans docker-compose — tourne comme service systemd indépendant
#                      Port 3001 (loopback 127.0.0.1 uniquement)
#
# ============================================================
# PROBLÈMES RENCONTRÉS LE 16/04/2026 ET LEURS SOLUTIONS
# ============================================================
#
# PROBLÈME 1 — Fichiers parasites embarqués dans le commit backend
#   Cause    : $excludedPatterns trop permissif — n'excluait pas .windsurf/,
#              scratch/, *.txt, prompt_universel*.md
#   Symptôme : .windsurf/rules.md, S.txt, Sans titre.txt, prompt_universel.md
#              se sont retrouvés dans le commit de prod
#   Solution : Ajout des patterns d'exclusion manquants dans ce script
#
# PROBLÈME 2 — Le VPS bloquait sur git pull (merge conflict)
#   Cause    : core/simplified_prompt_system.py avait des modifs locales
#              non commitées sur le VPS (modif manuelle directe sur le serveur)
#   Symptôme : "Please commit your changes or stash them before you merge. Aborting"
#   Solution : ssh + "git stash" avant "git pull" pour mettre de côté les modifs locales
#   Commande : ssh ... "git stash; git pull origin main"
#   ATTENTION : Ne JAMAIS modifier des fichiers directement sur le VPS —
#               toujours passer par GitHub pour garder la cohérence
#
# PROBLÈME 3 — Script affichait "✅ Déploiement terminé !" même en cas d'échec VPS
#   Cause    : Le heredoc PowerShell @'...'@ injectait des \r\n (CRLF Windows)
#              dans la commande SSH bash, corrompant toutes les commandes :
#              "cd: $'/home/zetaadmin/CHATBOT2.0/app\r': No such file or directory"
#              "unknown docker command: compose ps\r"
#   Symptôme : Toutes les commandes SSH échouaient silencieusement
#   Solution : Remplacer le heredoc par une seule string inline SSH avec ";"
#              comme séparateur. Ne JAMAIS utiliser @'...'@ pour du SSH.
#   Bonne pratique : ssh ... "cmd1; cmd2; cmd3" — pas de saut de ligne
#
# PROBLÈME 4 — Disque VPS à 100% (72G/72G, 145M restants)
#   Cause    : Accumulation d'images Docker inutilisées (35.76GB) et de
#              cache de build (1.72GB) sur 2+ mois
#   Symptôme : docker build échoue avec "No space left on device" à pip install numpy
#   Solution : docker image prune -af + docker builder prune -af → 36.5GB libérés
#   Commande : ssh ... "docker image prune -af; docker builder prune -af"
#   ATTENTION : Ce prune ne touche PAS les containers/images actifs
#
# PROBLÈME 5 — zeta-wa-bridge absent de docker-compose mais signalé "cassé"
#   Cause    : Le wa-bridge n'est PAS un service Docker Compose — c'est un
#              process Node.js direct dans /opt/zeta-wa-bridge/server.js
#              Il avait été tué par "docker compose down" puis oublié lors du "up -d"
#   Symptôme : QR code WhatsApp absent côté frontend, container introuvable dans compose
#   Solution : Le wa-bridge était en réalité toujours actif (PID persistent, systemd).
#              Son statut "idle" = session WA déconnectée, pas le bridge lui-même.
#              Pour vérifier : ss -tlnp | grep 3001 et curl http://localhost:3001/status
#   JAMAIS faire : docker compose down (tue tout y compris redis) sans "up -d" complet ensuite
#
# ============================================================
# COMMANDES DE DIAGNOSTIC VPS (sans risque, lecture seule)
# ============================================================
#   ssh ... "cd ~/CHATBOT2.0/app; git log --oneline -3"           → commit actuel VPS
#   ssh ... "docker compose ps"                                    → état containers
#   ssh ... "curl -s http://localhost:8002/ingestion/health"       → health backend
#   ssh ... "curl -s http://localhost:3001/status"                 → health wa-bridge
#   ssh ... "df -h /"                                              → espace disque
#   ssh ... "docker system df"                                     → espace Docker
#   ssh ... "ss -tlnp | grep 3001"                                 → wa-bridge process
#
# ============================================================

param(
    [string]$message = "update backend",
    [switch]$rollback
)

# Fichiers exclus du déploiement backend
# RÈGLE : Seuls les fichiers Python runtime et config backend sont déployables
# Tout le reste (frontend, docs, fichiers temporaires, outils dev) est exclu
$excludedPatterns = @(
    "zeta-ai-vercel/*",      # Frontend Vercel — déployer via robocopy + zeta-ai-vercel-deploy
    "zeta-ai-vercel-deploy/*",
    "frontend/*",
    ".windsurf/*",           # Config IDE local — ne doit jamais aller en prod
    "scratch/*",             # Fichiers de travail temporaires
    "results/*",
    "tests/reports/*",
    ".venv/*",
    "*.tar.gz",
    "*.pt",
    "*.pkl",
    "*.txt",                 # S.txt, Sans titre.txt, etc. — fichiers parasites
    "prompt_universel*.md",  # Docs de référence — pas du code runtime
    "config.js"
)

function Test-IsExcluded {
    param([string]$path)

    foreach ($pattern in $excludedPatterns) {
        if ($path -like $pattern) {
            return $true
        }
    }

    return $false
}

# ========================================
# ROLLBACK
# ========================================
if ($rollback) {
    Write-Host "⏪ ROLLBACK en cours..." -ForegroundColor Red
    ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app && git log --oneline -5 && git revert HEAD --no-edit && git push origin main 2>/dev/null || true && echo '✅ Rollback effectué !'"
    exit
}

# ========================================
# VÉRIFICATION FICHIERS DANGEREUX
# ========================================
Write-Host "🔍 Vérification des fichiers modifiés..." -ForegroundColor Yellow

$dangerous = @("Dockerfile", "docker-compose.yml", "requirements.txt", ".env")
$modified = git diff --name-only HEAD
$staged = git diff --cached --name-only
$untracked = git ls-files --others --exclude-standard

$allModified = ($modified + $staged + $untracked) | Sort-Object -Unique
$deployableFiles = @($allModified | Where-Object { $_ -and -not (Test-IsExcluded $_) })

$warnings = @()
foreach ($file in $deployableFiles) {
    foreach ($d in $dangerous) {
        if ($file -like "*$d*") {
            $warnings += $file
        }
    }
}

if ($warnings.Count -gt 0) {
    Write-Host "" 
    Write-Host "⚠️  ATTENTION - Fichiers sensibles détectés :" -ForegroundColor Red
    foreach ($w in $warnings) {
        Write-Host "   🚨 $w" -ForegroundColor Red
    }
    Write-Host ""
    $confirm = Read-Host "Ces fichiers nécessitent un rebuild Docker manuel. Continuer ? (oui/non)"
    if ($confirm -ne "oui") {
        Write-Host "❌ Déploiement annulé." -ForegroundColor Red
        exit
    }
}

# ========================================
# DÉPLOIEMENT
# ========================================
Write-Host ""
Write-Host "📦 Fichiers qui seront déployés :" -ForegroundColor Cyan
foreach ($file in $deployableFiles) {
    Write-Host $file
}
Write-Host ""

if ($deployableFiles.Count -eq 0) {
    Write-Host "❌ Aucun fichier backend déployable détecté." -ForegroundColor Red
    exit
}

Write-Host "📦 Push backend vers GitHub..." -ForegroundColor Cyan
git add -- $deployableFiles
if ((git diff --cached --name-only).Count -eq 0) {
    Write-Host "❌ Aucun fichier n'a pu être ajouté à l'index pour le déploiement." -ForegroundColor Red
    exit
}
git commit -m $message
git push origin main

Write-Host "🔄 Mise à jour du code sur VPS..." -ForegroundColor Yellow
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "set -e; cd ~/CHATBOT2.0/app; git pull origin main; echo ''; echo 'ETAT DU VPS :'; docker compose ps; curl -fsS http://localhost:8002/ingestion/health; echo ''"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Échec de mise à jour sur le VPS. Le déploiement n'est pas valide." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Déploiement terminé !" -ForegroundColor Green
Write-Host "⚠️  Si tu as modifié requirements.txt ou Dockerfile → rebuild manuel requis" -ForegroundColor Yellow