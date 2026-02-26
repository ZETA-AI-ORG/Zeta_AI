param([string]$message = "update backend")

Write-Host "📦 Push backend vers GitHub..." -ForegroundColor Cyan
git add .
git commit -m $message
git push origin main

Write-Host "🔄 Mise à jour du code sur VPS (git pull uniquement)..." -ForegroundColor Yellow
ssh -i "$HOME\.ssh\deploy_key" zetaadmin@194.60.201.228 "cd ~/CHATBOT2.0/app && git pull origin main && echo '✅ Code mis à jour ! Docker NON rebuilé.'"

Write-Host "✅ Code déployé sur VPS !" -ForegroundColor Green
Write-Host "⚠️  Si tu as modifié requirements.txt ou Dockerfile → rebuild manuel requis" -ForegroundColor Yellow