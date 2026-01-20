#!/bin/bash
# Script de synchronisation des fichiers modifiés vers Ubuntu

echo "🔄 Synchronisation des fichiers modifiés..."

# 1. Fichier de test corrigé
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_rag_extreme_stress.py" ~/ZETA_APP/CHATBOT2.0/test_rag_extreme_stress.py

# 2. Universal RAG Engine (filtrage amélioré)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/universal_rag_engine.py" ~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py

# 3. Ingestion API (auto-config)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/ingestion/ingestion_api.py" ~/ZETA_APP/CHATBOT2.0/ingestion/ingestion_api.py

# 4. Configuration MeiliSearch (optionnel)
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/configure_meili_complete.py" ~/ZETA_APP/CHATBOT2.0/configure_meili_complete.py

echo ""
echo "✅ Synchronisation terminée !"
echo ""
echo "📋 Prochaines étapes :"
echo "   1. Redémarrer l'API : pm2 restart chatbot-api"
echo "   2. Lancer les tests : python test_rag_extreme_stress.py"
