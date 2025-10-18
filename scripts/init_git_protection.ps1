# ========================================
# 🚀 INITIALISATION GIT + PROTECTION IA
# ========================================
# Script d'initialisation complète du système de protection
# Usage: powershell ./scripts/init_git_protection.ps1

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 INITIALISATION SYSTÈME ANTI-DÉRIVE IA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Git est installé
try {
    $gitVersion = git --version
    Write-Host "✅ Git détecté: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERREUR: Git n'est pas installé!" -ForegroundColor Red
    Write-Host "   Téléchargez Git: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Vérifier si déjà initialisé
if (Test-Path (Join-Path $projectRoot ".git")) {
    Write-Host "⚠️ Git déjà initialisé dans ce projet" -ForegroundColor Yellow
    Write-Host "   Voulez-vous réinitialiser? (o/n)" -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -ne "o" -and $response -ne "O") {
        Write-Host "❌ Annulé" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🗑️ Suppression de l'ancien dépôt Git..." -ForegroundColor Yellow
    Remove-Item -Path (Join-Path $projectRoot ".git") -Recurse -Force
}

# Initialiser Git
Write-Host "🎬 Initialisation de Git..." -ForegroundColor Yellow
Set-Location $projectRoot
git init
Write-Host "✅ Git initialisé" -ForegroundColor Green
Write-Host ""

# Créer .gitignore si n'existe pas
if (-not (Test-Path (Join-Path $projectRoot ".gitignore"))) {
    Write-Host "⚠️ .gitignore manquant (devrait être créé par le script principal)" -ForegroundColor Yellow
}

# Premier commit sur main
Write-Host "📝 Création du commit initial..." -ForegroundColor Yellow
git checkout -b main
git add .
git commit -m "🎉 Version initiale stable - Système anti-dérive IA activé"
Write-Host "✅ Commit initial créé sur 'main'" -ForegroundColor Green
Write-Host ""

# Créer les branches de sécurité
Write-Host "🌳 Création des branches de sécurité..." -ForegroundColor Yellow

git checkout -b dev
Write-Host "  ✅ Branche 'dev' créée" -ForegroundColor Gray

git checkout -b ia
Write-Host "  ✅ Branche 'ia' créée" -ForegroundColor Gray

git checkout main
Write-Host "  ✅ Retour sur 'main'" -ForegroundColor Gray
Write-Host ""

# Afficher les branches
Write-Host "📊 Branches créées:" -ForegroundColor Yellow
git branch -a
Write-Host ""

# Créer la première version stable
Write-Host "🔒 Création de la première version stable..." -ForegroundColor Yellow
& "$PSScriptRoot\create_stable_version.ps1" -Description "Version initiale - Système anti-dérive activé"
Write-Host ""

# Instructions pour GitHub
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🌐 PROCHAINES ÉTAPES - GITHUB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣  Créer un nouveau dépôt sur GitHub:" -ForegroundColor Yellow
Write-Host "    https://github.com/new" -ForegroundColor Gray
Write-Host ""
Write-Host "2️⃣  Nom suggéré: CHATBOT2.0 ou zeta-chatbot" -ForegroundColor Yellow
Write-Host "    ⚠️ NE PAS cocher 'Initialize with README'" -ForegroundColor Red
Write-Host ""
Write-Host "3️⃣  Lier le dépôt local à GitHub:" -ForegroundColor Yellow
Write-Host "    git remote add origin https://github.com/TON_PSEUDO/CHATBOT2.0.git" -ForegroundColor Gray
Write-Host "    git push -u origin main" -ForegroundColor Gray
Write-Host "    git push -u origin dev" -ForegroundColor Gray
Write-Host "    git push -u origin ia" -ForegroundColor Gray
Write-Host ""
Write-Host "4️⃣  Protéger la branche main (sur GitHub):" -ForegroundColor Yellow
Write-Host "    Settings → Branches → Add rule" -ForegroundColor Gray
Write-Host "    Branch name: main" -ForegroundColor Gray
Write-Host "    ✅ Require pull request reviews" -ForegroundColor Gray
Write-Host ""

# Résumé final
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ SYSTÈME ANTI-DÉRIVE ACTIVÉ!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📂 Structure créée:" -ForegroundColor Yellow
Write-Host "  ✅ /stable      → Versions verrouillées" -ForegroundColor Gray
Write-Host "  ✅ /backup      → Sauvegardes automatiques" -ForegroundColor Gray
Write-Host "  ✅ /scripts     → Scripts PowerShell" -ForegroundColor Gray
Write-Host "  ✅ /.github     → GitHub Actions" -ForegroundColor Gray
Write-Host ""
Write-Host "🌳 Branches créées:" -ForegroundColor Yellow
Write-Host "  ✅ main         → Production (protégée)" -ForegroundColor Gray
Write-Host "  ✅ dev          → Développement" -ForegroundColor Gray
Write-Host "  ✅ ia           → Zone IA (Windsurf/Cursor)" -ForegroundColor Gray
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "  📖 Lire: GUIDE_ANTI_DERIVE_IA.md" -ForegroundColor Gray
Write-Host ""
Write-Host "🎯 ROUTINE QUOTIDIENNE:" -ForegroundColor Yellow
Write-Host "  1. Avant IA: powershell ./scripts/auto_backup.ps1" -ForegroundColor Gray
Write-Host "  2. Travailler: git checkout ia" -ForegroundColor Gray
Write-Host "  3. Après IA: powershell ./scripts/check_ia_changes.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "🛡️ Tu es maintenant protégé contre toute dérive IA!" -ForegroundColor Green
Write-Host ""
