# ========================================
# 🔍 CHECK IA CHANGES - DÉTECTION MODIFICATIONS
# ========================================
# Compare la branche 'ia' avec 'main' pour voir les changements
# Usage: powershell ./scripts/check_ia_changes.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔍 DÉTECTION DES MODIFICATIONS IA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier qu'on est dans un repo Git
if (-not (Test-Path ".git")) {
    Write-Host "❌ ERREUR: Pas de dépôt Git trouvé!" -ForegroundColor Red
    Write-Host "   Exécutez d'abord: git init" -ForegroundColor Yellow
    exit 1
}

# Récupérer la branche actuelle
$currentBranch = git rev-parse --abbrev-ref HEAD

Write-Host "📍 Branche actuelle: $currentBranch" -ForegroundColor Yellow
Write-Host ""

# Vérifier si les branches existent
$branches = git branch --list
if ($branches -notmatch "main") {
    Write-Host "⚠️ Branche 'main' non trouvée" -ForegroundColor Yellow
}
if ($branches -notmatch "ia") {
    Write-Host "⚠️ Branche 'ia' non trouvée" -ForegroundColor Yellow
    Write-Host "   Créez-la avec: git checkout -b ia" -ForegroundColor Gray
    exit 0
}

Write-Host "🔍 Comparaison: main ↔ ia" -ForegroundColor Cyan
Write-Host ""

# Statistiques des changements
Write-Host "📊 STATISTIQUES DES CHANGEMENTS:" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow
git diff --stat main..ia
Write-Host ""

# Fichiers modifiés
Write-Host "📝 FICHIERS MODIFIÉS:" -ForegroundColor Yellow
Write-Host "====================" -ForegroundColor Yellow
$modifiedFiles = git diff --name-only main..ia
if ($modifiedFiles) {
    $modifiedFiles | ForEach-Object {
        Write-Host "  📄 $_" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Total: $($modifiedFiles.Count) fichiers modifiés" -ForegroundColor Cyan
} else {
    Write-Host "  ✅ Aucune modification détectée" -ForegroundColor Green
}
Write-Host ""

# Demander si on veut voir les détails
Write-Host "🔎 Voulez-vous voir les DÉTAILS des modifications? (o/n)" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq "o" -or $response -eq "O") {
    Write-Host ""
    Write-Host "📋 DÉTAILS DES MODIFICATIONS:" -ForegroundColor Yellow
    Write-Host "=============================" -ForegroundColor Yellow
    git diff main..ia
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "💡 ACTIONS POSSIBLES:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1️⃣  Fusionner les changements: git checkout main && git merge ia" -ForegroundColor Gray
Write-Host "2️⃣  Annuler les changements IA: git checkout ia && git reset --hard main" -ForegroundColor Gray
Write-Host "3️⃣  Créer une sauvegarde: powershell ./scripts/auto_backup.ps1" -ForegroundColor Gray
Write-Host ""
