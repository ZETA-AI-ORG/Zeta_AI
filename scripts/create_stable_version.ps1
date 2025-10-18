# ========================================
# 🔒 CREATE STABLE VERSION - VERSION VERROUILLÉE
# ========================================
# Crée une version stable verrouillée du code actuel
# Usage: powershell ./scripts/create_stable_version.ps1 -Description "Version après fix scoring"

param(
    [string]$Description = "Version stable"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stableDir = Join-Path $projectRoot "stable\$timestamp"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔒 CRÉATION VERSION STABLE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier qu'on est sur la branche main
$currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
if ($currentBranch -ne "main") {
    Write-Host "⚠️ ATTENTION: Vous n'êtes pas sur la branche 'main'" -ForegroundColor Yellow
    Write-Host "   Branche actuelle: $currentBranch" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Voulez-vous continuer quand même? (o/n)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "o" -and $response -ne "O") {
        Write-Host "❌ Annulé" -ForegroundColor Red
        exit 1
    }
}

# Créer le dossier stable
Write-Host "📁 Création du dossier: $stableDir" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $stableDir | Out-Null

# Liste des dossiers à sauvegarder
$foldersToBackup = @(
    "api",
    "core",
    "database",
    "routes",
    "config",
    "models",
    "ingestion",
    "enrichment_system",
    "admin_ui",
    "templates",
    "tools"
)

# Copier les dossiers
Write-Host "📦 Copie des dossiers critiques..." -ForegroundColor Yellow
foreach ($folder in $foldersToBackup) {
    $sourcePath = Join-Path $projectRoot $folder
    if (Test-Path $sourcePath) {
        $destPath = Join-Path $stableDir $folder
        Write-Host "  → $folder" -ForegroundColor Gray
        Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
    }
}

# Copier les fichiers racine
Write-Host "📄 Copie des fichiers racine..." -ForegroundColor Yellow
$filesToBackup = @(
    "app.py",
    "app_optimized.py",
    "requirements.txt",
    ".env.production",
    "config.py",
    "utils.py"
)

foreach ($file in $filesToBackup) {
    $sourcePath = Join-Path $projectRoot $file
    if (Test-Path $sourcePath) {
        $destPath = Join-Path $stableDir $file
        Write-Host "  → $file" -ForegroundColor Gray
        Copy-Item -Path $sourcePath -Destination $destPath -Force
    }
}

# Créer métadonnées
$metadata = @{
    timestamp = $timestamp
    description = $Description
    git_branch = $currentBranch
    git_commit = (git rev-parse HEAD 2>$null)
    git_commit_short = (git rev-parse --short HEAD 2>$null)
    created_by = $env:USERNAME
    stable_size_mb = [math]::Round((Get-ChildItem -Path $stableDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
}

$metadata | ConvertTo-Json | Out-File -FilePath (Join-Path $stableDir "VERSION_INFO.json") -Encoding UTF8

# Créer un README pour cette version
$readmeContent = @"
# 🔒 VERSION STABLE - $timestamp

## 📋 Informations
- **Date**: $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")
- **Description**: $Description
- **Branche Git**: $currentBranch
- **Commit**: $($metadata.git_commit_short)
- **Créé par**: $($metadata.created_by)
- **Taille**: $($metadata.stable_size_mb) MB

## ⚠️ IMPORTANT
Cette version est **VERROUILLÉE** et ne doit **JAMAIS** être modifiée.
Pour restaurer cette version, utilisez:

``````powershell
powershell ./scripts/restore_stable_version.ps1 $timestamp
``````

## 📦 Contenu
$($foldersToBackup -join ", ")

## 🔐 Intégrité
Cette version a été créée depuis la branche '$currentBranch' et représente un état stable et testé du code.
"@

$readmeContent | Out-File -FilePath (Join-Path $stableDir "README.md") -Encoding UTF8

Write-Host ""
Write-Host "✅ VERSION STABLE CRÉÉE!" -ForegroundColor Green
Write-Host "📂 Emplacement: $stableDir" -ForegroundColor Green
Write-Host "📊 Taille: $($metadata.stable_size_mb) MB" -ForegroundColor Green
Write-Host "🔐 Commit: $($metadata.git_commit_short)" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "💡 Pour restaurer cette version:" -ForegroundColor Cyan
Write-Host "   powershell ./scripts/restore_stable_version.ps1 $timestamp" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
