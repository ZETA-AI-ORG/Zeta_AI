param(
    [string]$message = "deploy: update"
)

$VPS      = "contabo"
$VPS_PATH = "~/CHATBOT2.0/app"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ZETA AI  DEPLOY BACKEND" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host " [1/4] Commit & Push Git..." -ForegroundColor Yellow
git add .
git commit -m $message
git push vps main

if ($LASTEXITCODE -ne 0) {
    Write-Host " Push Git échoué." -ForegroundColor Red
    exit 1
}

Write-Host " Push OK" -ForegroundColor Green
Write-Host ""

Write-Host " [2/4] Docker down..." -ForegroundColor Yellow
ssh $VPS "cd ${VPS_PATH} && docker compose down"
Write-Host " Down OK" -ForegroundColor Green
Write-Host ""

Write-Host " [3/4] Docker build & up..." -ForegroundColor Yellow
ssh $VPS "cd ${VPS_PATH} && docker compose build && docker compose up -d zeta-backend"

if ($LASTEXITCODE -ne 0) {
    Write-Host " Docker build/up échoué." -ForegroundColor Red
    exit 1
}

Write-Host " Build & Up OK" -ForegroundColor Green
Write-Host ""

Write-Host " [4/4] Vérification..." -ForegroundColor Yellow
ssh $VPS "cd ${VPS_PATH} && docker compose ps && docker compose logs -n 50 zeta-backend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   DEPLOY TERMINÉ : $message" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

param(
    [string]$message = "update backend",
    [switch]$rollback
)

$excludedPatterns = @(
    "zeta-ai-vercel/*",
    "zeta-ai-vercel-deploy/*",
    "frontend/*",
    "results/*",
    "tests/reports/*",
    ".venv/*",
    "*.tar.gz",
    "*.pt",
    "*.pkl",
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
    ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 @"
cd ~/CHATBOT2.0/app
git log --oneline -5
git revert HEAD --no-edit
git push origin main 2>/dev/null || true
echo '✅ Rollback effectué !'
"@
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
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 @"
cd ~/CHATBOT2.0/app
git pull origin main

echo ''
echo '📊 ÉTAT DU VPS :'
docker compose ps
curl -s http://localhost:8002/ingestion/health
echo ''
"@

Write-Host ""
Write-Host "✅ Déploiement terminé !" -ForegroundColor Green
Write-Host "⚠️  Si tu as modifié requirements.txt ou Dockerfile → rebuild manuel requis" -ForegroundColor Yellow