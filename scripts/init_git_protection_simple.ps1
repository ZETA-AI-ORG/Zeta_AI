# ========================================
# INITIALISATION GIT + PROTECTION IA
# ========================================
# Script d'initialisation complete du systeme de protection
# Usage: powershell ./scripts/init_git_protection_simple.ps1

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INITIALISATION SYSTEME ANTI-DERIVE IA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifier si Git est installe
try {
    $gitVersion = git --version
    Write-Host "[OK] Git detecte: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERREUR] Git n'est pas installe!" -ForegroundColor Red
    Write-Host "   Telechargez Git: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Verifier si deja initialise
if (Test-Path (Join-Path $projectRoot ".git")) {
    Write-Host "[ATTENTION] Git deja initialise dans ce projet" -ForegroundColor Yellow
    Write-Host "   Voulez-vous reinitialiser? (o/n)" -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -ne "o" -and $response -ne "O") {
        Write-Host "[ANNULE]" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[INFO] Suppression de l'ancien depot Git..." -ForegroundColor Yellow
    Remove-Item -Path (Join-Path $projectRoot ".git") -Recurse -Force
}

# Initialiser Git
Write-Host "[ETAPE 1] Initialisation de Git..." -ForegroundColor Yellow
Set-Location $projectRoot
git init
Write-Host "[OK] Git initialise" -ForegroundColor Green
Write-Host ""

# Creer .gitignore si n'existe pas
if (-not (Test-Path (Join-Path $projectRoot ".gitignore"))) {
    Write-Host "[ATTENTION] .gitignore manquant" -ForegroundColor Yellow
}

# Premier commit sur main
Write-Host "[ETAPE 2] Creation du commit initial..." -ForegroundColor Yellow
git checkout -b main
git add .
git commit -m "Version initiale stable - Systeme anti-derive IA active"
Write-Host "[OK] Commit initial cree sur 'main'" -ForegroundColor Green
Write-Host ""

# Creer les branches de securite
Write-Host "[ETAPE 3] Creation des branches de securite..." -ForegroundColor Yellow

git checkout -b dev
Write-Host "  [OK] Branche 'dev' creee" -ForegroundColor Gray

git checkout -b ia
Write-Host "  [OK] Branche 'ia' creee" -ForegroundColor Gray

git checkout main
Write-Host "  [OK] Retour sur 'main'" -ForegroundColor Gray
Write-Host ""

# Afficher les branches
Write-Host "[INFO] Branches creees:" -ForegroundColor Yellow
git branch -a
Write-Host ""

# Creer la premiere version stable
Write-Host "[ETAPE 4] Creation de la premiere version stable..." -ForegroundColor Yellow
& "$PSScriptRoot\create_stable_version.ps1" -Description "Version initiale - Systeme anti-derive active"
Write-Host ""

# Instructions pour GitHub
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROCHAINES ETAPES - GITHUB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Creer un nouveau depot sur GitHub:" -ForegroundColor Yellow
Write-Host "    https://github.com/new" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Nom suggere: CHATBOT2.0 ou zeta-chatbot" -ForegroundColor Yellow
Write-Host "    [ATTENTION] NE PAS cocher 'Initialize with README'" -ForegroundColor Red
Write-Host ""
Write-Host "3. Lier le depot local a GitHub:" -ForegroundColor Yellow
Write-Host "    git remote add origin https://github.com/TON_PSEUDO/CHATBOT2.0.git" -ForegroundColor Gray
Write-Host "    git push -u origin main" -ForegroundColor Gray
Write-Host "    git push -u origin dev" -ForegroundColor Gray
Write-Host "    git push -u origin ia" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Proteger la branche main (sur GitHub):" -ForegroundColor Yellow
Write-Host "    Settings -> Branches -> Add rule" -ForegroundColor Gray
Write-Host "    Branch name: main" -ForegroundColor Gray
Write-Host "    [X] Require pull request reviews" -ForegroundColor Gray
Write-Host ""

# Resume final
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYSTEME ANTI-DERIVE ACTIVE!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Structure creee:" -ForegroundColor Yellow
Write-Host "  [OK] /stable      -> Versions verrouillees" -ForegroundColor Gray
Write-Host "  [OK] /backup      -> Sauvegardes automatiques" -ForegroundColor Gray
Write-Host "  [OK] /scripts     -> Scripts PowerShell" -ForegroundColor Gray
Write-Host "  [OK] /.github     -> GitHub Actions" -ForegroundColor Gray
Write-Host ""
Write-Host "Branches creees:" -ForegroundColor Yellow
Write-Host "  [OK] main         -> Production (protegee)" -ForegroundColor Gray
Write-Host "  [OK] dev          -> Developpement" -ForegroundColor Gray
Write-Host "  [OK] ia           -> Zone IA (Windsurf/Cursor)" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  Lire: GUIDE_ANTI_DERIVE_IA.md" -ForegroundColor Gray
Write-Host ""
Write-Host "ROUTINE QUOTIDIENNE:" -ForegroundColor Yellow
Write-Host "  1. Avant IA: powershell ./scripts/auto_backup.ps1" -ForegroundColor Gray
Write-Host "  2. Travailler: git checkout ia" -ForegroundColor Gray
Write-Host "  3. Apres IA: powershell ./scripts/check_ia_changes.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "[SUCCES] Tu es maintenant protege contre toute derive IA!" -ForegroundColor Green
Write-Host ""
