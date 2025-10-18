# ========================================
# 💾 AUTO-BACKUP - SAUVEGARDE AUTOMATIQUE
# ========================================
# Créé une sauvegarde complète avant session IA
# Usage: powershell ./scripts/auto_backup.ps1

param(
    [string]$Description = "Session IA"
)

$ErrorActionPreference = "Stop"

# Configuration
$projectRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $projectRoot "backup\$timestamp"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "💾 AUTO-BACKUP - SAUVEGARDE AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Créer le dossier de backup
Write-Host "📁 Création du dossier: $backupDir" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# Liste des dossiers à sauvegarder (EXCLUANT .venv, __pycache__, node_modules, etc.)
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

# Sauvegarder les dossiers critiques
Write-Host "📦 Sauvegarde des dossiers critiques..." -ForegroundColor Yellow
foreach ($folder in $foldersToBackup) {
    $sourcePath = Join-Path $projectRoot $folder
    if (Test-Path $sourcePath) {
        $destPath = Join-Path $backupDir $folder
        Write-Host "  → $folder" -ForegroundColor Gray
        Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
    }
}

# Sauvegarder les fichiers racine importants
Write-Host "📄 Sauvegarde des fichiers racine..." -ForegroundColor Yellow
$filesToBackup = @(
    "app.py",
    "app_optimized.py",
    "requirements.txt",
    ".env",
    ".env.production",
    "config.py",
    "utils.py"
)

foreach ($file in $filesToBackup) {
    $sourcePath = Join-Path $projectRoot $file
    if (Test-Path $sourcePath) {
        $destPath = Join-Path $backupDir $file
        Write-Host "  → $file" -ForegroundColor Gray
        Copy-Item -Path $sourcePath -Destination $destPath -Force
    }
}

# Créer un fichier de métadonnées
$metadata = @{
    timestamp = $timestamp
    description = $Description
    git_branch = (git rev-parse --abbrev-ref HEAD 2>$null)
    git_commit = (git rev-parse HEAD 2>$null)
    backup_size_mb = [math]::Round((Get-ChildItem -Path $backupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
}

$metadata | ConvertTo-Json | Out-File -FilePath (Join-Path $backupDir "metadata.json") -Encoding UTF8

Write-Host ""
Write-Host "✅ SAUVEGARDE CRÉÉE AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "📂 Emplacement: $backupDir" -ForegroundColor Green
Write-Host "📊 Taille: $($metadata.backup_size_mb) MB" -ForegroundColor Green
Write-Host "🕒 Timestamp: $timestamp" -ForegroundColor Green
Write-Host ""

# Nettoyage des anciennes sauvegardes (> 30 jours)
Write-Host "🧹 Nettoyage des anciennes sauvegardes (> 30 jours)..." -ForegroundColor Yellow
$backupRoot = Join-Path $projectRoot "backup"
$oldBackups = Get-ChildItem -Path $backupRoot -Directory | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) }

if ($oldBackups) {
    foreach ($oldBackup in $oldBackups) {
        Write-Host "  🗑️ Suppression: $($oldBackup.Name)" -ForegroundColor Gray
        Remove-Item -Path $oldBackup.FullName -Recurse -Force
    }
    Write-Host "✅ $($oldBackups.Count) anciennes sauvegardes supprimées" -ForegroundColor Green
} else {
    Write-Host "  ℹ️ Aucune sauvegarde à nettoyer" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🎯 PRÊT POUR SESSION IA!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
