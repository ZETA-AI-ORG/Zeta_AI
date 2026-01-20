#!/bin/bash
# 🔥 SYNCHRONISATION TEST ULTIME RAG - LIMITES ABSOLUES

echo "🔥 DÉPLOIEMENT TEST ULTIME RAG..."

# Synchroniser le test ultime
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_rag_extreme_limits.py" ~/ZETA_APP/CHATBOT2.0/test_rag_extreme_limits.py

echo ""
echo "✅ TEST ULTIME DÉPLOYÉ !"
echo ""
echo "🔥 POUSSER LE RAG DANS SES LIMITES ABSOLUES:"
echo "python test_rag_extreme_limits.py"
echo ""
echo "⚠️ ATTENTION: Ce test va stresser le système au maximum !"
echo "   • Queries de 100KB"
echo "   • 15 requêtes simultanées"
echo "   • Cas extrêmes et edge cases"
echo "   • Test d'injection et sécurité"
echo ""
echo "🚀 Assurez-vous que l'API tourne:"
echo "python app.py"
