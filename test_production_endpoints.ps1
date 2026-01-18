# Script de test des endpoints de production
# Exécuter dans PowerShell avec: .\test_production_endpoints.ps1

$prod_url = "https://api.zeta-ai.com/v1/botlive/message"
$api_key = "YOUR_PROD_API_KEY"  # Remplacer par la vraie clé

# 1. Tester endpoint Botlive
$body = @{
    company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
    user_id    = "test_user"
    message    = "Bonne continuation à vous"
} | ConvertTo-Json

$headers = @{
    "Authorization" = "Bearer $api_key"
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod -Uri $prod_url -Method Post -Headers $headers -Body $body
Write-Output "[TEST] Response du endpoint Botlive:"
$response | Format-List

# 2. Vérifier les logs côté serveur
Write-Output "✓ Vérifiez les logs serveur pour le message orange 'ZETA-AI v6.5 active'"
