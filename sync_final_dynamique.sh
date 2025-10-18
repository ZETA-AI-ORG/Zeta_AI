#!/bin/bash
# 🚀 SYNCHRONISATION FINALE - SYSTÈME 100% DYNAMIQUE

echo "🚀 Synchronisation système RAG 100% dynamique..."

# Fichiers principaux du système RAG
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/universal_rag_engine.py" ~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_new_rag_system.py" ~/ZETA_APP/CHATBOT2.0/test_new_rag_system.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/exemple_utilisation_dynamique.md" ~/ZETA_APP/CHATBOT2.0/exemple_utilisation_dynamique.md

echo "✅ Synchronisation terminée !"
echo ""
echo "🧪 TESTS DISPONIBLES :"
echo "# Test complet avec tes IDs :"
echo "python test_new_rag_system.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3 testuser129 'Rue du Gros'"
echo ""
echo "# Test simple du moteur RAG :"
echo "python -m core.universal_rag_engine MpfnlSbqwaZ6F4HvxQLRL9du0yG3 testuser129 'Rue du Gros' 'Que vendez-vous?'"
echo ""
echo "# Avec valeurs par défaut :"
echo "python test_new_rag_system.py"
