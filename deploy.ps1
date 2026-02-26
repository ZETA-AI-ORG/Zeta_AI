param([string]$message = "update backend")

Write-Host "📦 Push backend vers GitHub..." -ForegroundColor Cyan
git add .
git commit -m $message
git push origin main

Write-Host "🚀 Déploiement sur VPS..." -ForegroundColor Cyan
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 @"
cd ~/CHATBOT2.0/app
git pull origin main
docker compose build zeta-backend
docker compose up -d
docker compose ps
echo '✅ Backend déployé !'
"@

Write-Host "✅ Déploiement terminé !" -ForegroundColor Green