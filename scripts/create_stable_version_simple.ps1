# ========================================
# CREATE STABLE VERSION - VERSION VERROUILLEE
# ========================================
# Cree une version stable verrouillee du code actuel
# Usage: powershell ./scripts/create_stable_version_simple.ps1 -Description "Version apres fix scoring"

param(
    [string]$Description = "Version stable"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stableDir = Join-Path $projectRoot "stable\$timestamp"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CREATION VERSION STABLE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifier qu'on est sur la branche main
$currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
if ($currentBranch -ne "main") {
    Write-Host "[ATTENTION] Vous n'etes pas sur la branche 'main'" -ForegroundColor Yellow
    Write-Host "   Branche actuelle: $currentBranch" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Voulez-vous continuer quand meme? (o/n)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "o" -and $response -ne "O") {
        Write-Host "[ANNULE]" -ForegroundColor Red
        exit 1
    }
}

# Creer le dossier stable
Write-Host "[INFO] Creation du dossier: $stableDir" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $stableDir | Out-Null

# Liste des dossiers a sauvegarder
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
Write-Host "[INFO] Copie des dossiers critiques..." -ForegroundColor Yellow
foreach ($folder in $foldersToBackup) {
    $sourcePath = Join-Path $projectRoot $folder
    if (Test-Path $sourcePath) {
        $destPath = Join-Path $stableDir $folder
        Write-Host "  -> $folder" -ForegroundColor Gray
        Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
    }
}

# Copier les fichiers racine
Write-Host "[INFO] Copie des fichiers racine..." -ForegroundColor Yellow
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
        Write-Host "  -> $file" -ForegroundColor Gray
        Copy-Item -Path $sourcePath -Destination $destPath -Force
    }
}

# Creer metadonnees
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

# Creer un README pour cette version
$readmeContent = @"
# VERSION STABLE - $timestamp

## Informations
- **Date**: $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")
- **Description**: $Description
- **Branche Git**: $currentBranch
- **Commit**: $($metadata.git_commit_short)
- **Cree par**: $($metadata.created_by)
- **Taille**: $($metadata.stable_size_mb) MB

## IMPORTANT
Cette version est VERROUILLEE et ne doit JAMAIS etre modifiee.
Pour restaurer cette version, utilisez:

``````powershell
powershell ./scripts/restore_stable_version.ps1 $timestamp
``````

## Contenu
$($foldersToBackup -join ", ")

## Integrite
Cette version a ete creee depuis la branche '$currentBranch' et represente un etat stable et teste du code.
"@

$readmeContent | Out-File -FilePath (Join-Path $stableDir "README.md") -Encoding UTF8

Write-Host ""
Write-Host "[SUCCES] VERSION STABLE CREEE!" -ForegroundColor Green
Write-Host "Emplacement: $stableDir" -ForegroundColor Green
Write-Host "Taille: $($metadata.stable_size_mb) MB" -ForegroundColor Green
Write-Host "Commit: $($metadata.git_commit_short)" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pour restaurer cette version:" -ForegroundColor Cyan
Write-Host "   powershell ./scripts/restore_stable_version.ps1 $timestamp" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
