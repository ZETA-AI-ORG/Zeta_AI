# ========================================
# ♻️ RESTORE STABLE VERSION - RESTAURATION
# ========================================
# Restaure une version stable verrouillée
# Usage: powershell ./scripts/restore_stable_version.ps1 20250118_143000

param(
    [Parameter(Mandatory=$true)]
    [string]$Timestamp
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$stableDir = Join-Path $projectRoot "stable\$Timestamp"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "♻️ RESTAURATION VERSION STABLE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que la version existe
if (-not (Test-Path $stableDir)) {
    Write-Host "❌ ERREUR: Version stable '$Timestamp' introuvable!" -ForegroundColor Red
    Write-Host ""
    Write-Host "📂 Versions disponibles:" -ForegroundColor Yellow
    $stableRoot = Join-Path $projectRoot "stable"
    Get-ChildItem -Path $stableRoot -Directory | ForEach-Object {
        Write-Host "  → $($_.Name)" -ForegroundColor Gray
    }
    exit 1
}

# Lire les métadonnées
$metadataPath = Join-Path $stableDir "VERSION_INFO.json"
if (Test-Path $metadataPath) {
    $metadata = Get-Content $metadataPath | ConvertFrom-Json
    Write-Host "📋 VERSION À RESTAURER:" -ForegroundColor Yellow
    Write-Host "  Description: $($metadata.description)" -ForegroundColor Gray
    Write-Host "  Branche: $($metadata.git_branch)" -ForegroundColor Gray
    Write-Host "  Commit: $($metadata.git_commit_short)" -ForegroundColor Gray
    Write-Host "  Taille: $($metadata.stable_size_mb) MB" -ForegroundColor Gray
    Write-Host ""
}

# Confirmation
Write-Host "⚠️ ATTENTION: Cette opération va écraser le code actuel!" -ForegroundColor Red
Write-Host "   Voulez-vous créer une sauvegarde avant? (o/n)" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq "o" -or $response -eq "O") {
    Write-Host "💾 Création d'une sauvegarde..." -ForegroundColor Yellow
    & "$PSScriptRoot\auto_backup.ps1" -Description "Avant restauration $Timestamp"
    Write-Host ""
}

Write-Host "Confirmer la restauration? (o/n)" -ForegroundColor Yellow
$confirm = Read-Host

if ($confirm -ne "o" -and $confirm -ne "O") {
    Write-Host "❌ Restauration annulée" -ForegroundColor Red
    exit 1
}

# Restaurer les dossiers
Write-Host ""
Write-Host "📦 Restauration des dossiers..." -ForegroundColor Yellow
$folders = Get-ChildItem -Path $stableDir -Directory
foreach ($folder in $folders) {
    $destPath = Join-Path $projectRoot $folder.Name
    Write-Host "  → $($folder.Name)" -ForegroundColor Gray
    
    # Supprimer l'ancien dossier si existe
    if (Test-Path $destPath) {
        Remove-Item -Path $destPath -Recurse -Force
    }
    
    # Copier le nouveau
    Copy-Item -Path $folder.FullName -Destination $destPath -Recurse -Force
}

# Restaurer les fichiers racine
Write-Host "📄 Restauration des fichiers racine..." -ForegroundColor Yellow
$files = Get-ChildItem -Path $stableDir -File | Where-Object { $_.Name -ne "VERSION_INFO.json" -and $_.Name -ne "README.md" }
foreach ($file in $files) {
    $destPath = Join-Path $projectRoot $file.Name
    Write-Host "  → $($file.Name)" -ForegroundColor Gray
    Copy-Item -Path $file.FullName -Destination $destPath -Force
}

Write-Host ""
Write-Host "✅ RESTAURATION TERMINÉE!" -ForegroundColor Green
Write-Host "📂 Version restaurée: $Timestamp" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "💡 PROCHAINES ÉTAPES:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1️⃣  Vérifier que tout fonctionne" -ForegroundColor Gray
Write-Host "2️⃣  Redémarrer le serveur si nécessaire" -ForegroundColor Gray
Write-Host "3️⃣  Commit Git: git add . && git commit -m 'Restauration version $Timestamp'" -ForegroundColor Gray
Write-Host ""
