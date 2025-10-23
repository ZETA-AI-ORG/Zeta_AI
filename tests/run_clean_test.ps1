# ========================================
# 🧪 TEST PROPRE AVEC NETTOYAGE COMPLET
# ========================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("light", "hardcore")]
    [string]$Scenario = "light"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🧪 TEST COMPLET: $Scenario" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que le serveur tourne
Write-Host "🔍 Vérification du serveur..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8002/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Serveur actif" -ForegroundColor Green
} catch {
    Write-Host "❌ Serveur non accessible sur http://127.0.0.1:8002" -ForegroundColor Red
    Write-Host "   Lancez d'abord: uvicorn app:app --reload --host 0.0.0.0 --port 8002" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Lancer le test avec nettoyage automatique
Write-Host "🚀 Lancement du test $Scenario..." -ForegroundColor Green
Write-Host ""

python tests/run_test_with_logs.py --scenario $Scenario --log-file "logs/server_manual.log"

Write-Host ""
Write-Host "✅ Test terminé!" -ForegroundColor Green
Write-Host ""
