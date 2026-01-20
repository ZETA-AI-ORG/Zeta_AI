#!/bin/bash
# 🔍 SYNCHRONISATION TEST CURL DIRECT

echo "🔍 Synchronisation test CURL direct..."

# Synchroniser le test CURL
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_direct_curl.sh" ~/ZETA_APP/CHATBOT2.0/test_direct_curl.sh
chmod +x ~/ZETA_APP/CHATBOT2.0/test_direct_curl.sh

# Synchroniser le script diagnostic corrigé
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_document_analysis.py" ~/ZETA_APP/CHATBOT2.0/test_document_analysis.py

echo "✅ Synchronisation terminée !"
echo ""
echo "🔍 DIAGNOSTIC ÉTAPE PAR ÉTAPE:"
echo ""
echo "1. 🧪 TESTER CURL DIRECT:"
echo "   ./test_direct_curl.sh"
echo ""
echo "2. 👀 ANALYSER LES LOGS SERVEUR:"
echo "   Regarder les logs en temps réel pendant le curl"
echo "   Identifier où ça casse dans le RAG"
echo ""
echo "3. 🔧 CORRIGER LE PROBLÈME IDENTIFIÉ"
echo ""
echo "4. 🧪 RELANCER LE TEST DIAGNOSTIC:"
echo "   python test_document_analysis.py"
echo ""
echo "🎯 OBJECTIF: Comprendre pourquoi 0 documents trouvés"
