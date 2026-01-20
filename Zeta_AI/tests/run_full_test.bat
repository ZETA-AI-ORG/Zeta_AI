@echo off
REM ========================================
REM TEST COMPLET AVEC CAPTURE DE LOGS
REM ========================================

echo.
echo ========================================
echo 🧪 TEST COMPLET AVEC LOGS SERVEUR
echo ========================================
echo.

REM Créer le dossier logs
if not exist "logs" mkdir logs

REM Nom du fichier de log
set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=logs\server_%TIMESTAMP%.log

echo 📝 Fichier de logs: %LOG_FILE%
echo.

REM Lancer le serveur avec capture de logs en arrière-plan
echo 🎬 Lancement du serveur avec capture...
start /B python tests\capture_server_logs.py --output %LOG_FILE%

REM Attendre que le serveur démarre
echo ⏳ Attente démarrage serveur (10s)...
timeout /t 10 /nobreak > nul

REM Lancer le test
echo.
echo 🧪 Lancement du test %1...
python tests\run_test_with_logs.py --scenario %1 --log-file %LOG_FILE%

echo.
echo ✅ Test terminé!
echo 📄 Logs serveur: %LOG_FILE%
echo.

REM Arrêter le serveur
echo ⏹️  Arrêt du serveur...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq tests\capture_server_logs.py*" > nul 2>&1

pause
