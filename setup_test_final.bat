@echo off
echo ========================================
echo SETUP TEST FINAL BOTLIVE COMPLET
echo ========================================
echo.

echo 1. Activation environnement virtuel...
call .venv\Scripts\activate

echo.
echo 2. Variables d'environnement requises:
echo    - SUPABASE_URL
echo    - SUPABASE_SERVICE_KEY  
echo    - GROQ_API_KEY
echo    - OPENAI_API_KEY (optionnel)
echo.

echo 3. Démarrage du backend (port 8002)...
echo    Commande: python app.py
echo.

echo 4. Dans un autre terminal, lancer le test:
echo    Commande: python test_endpoint_final.py
echo.

echo ========================================
echo COMMANDE COMPLETE A EXECUTER:
echo ========================================
echo.

REM Créer le fichier .env s'il n'existe pas
if not exist .env (
    echo Création du fichier .env...
    echo # Variables Supabase > .env
    echo SUPABASE_URL=votre_url_supabase >> .env
    echo SUPABASE_SERVICE_KEY=votre_service_key >> .env
    echo. >> .env
    echo # API Keys LLM >> .env
    echo GROQ_API_KEY=votre_groq_key >> .env
    echo OPENAI_API_KEY=votre_openai_key >> .env
    echo. >> .env
    echo # Configuration >> .env
    echo PYTHONPATH=. >> .env
    echo.
    echo Fichier .env créé. Merci de le compléter avec vos vraies clés!
    echo.
)

echo Commande pour démarrer le backend:
echo   .venv\Scripts\activate ^&^& python app.py
echo.
echo Commande pour lancer le test (dans autre terminal):
echo   .venv\Scripts\activate ^&^& python test_endpoint_final.py
echo.

pause
