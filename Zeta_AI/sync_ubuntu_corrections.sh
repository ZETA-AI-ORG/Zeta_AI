#!/bin/bash
# 🔄 SYNCHRONISATION CORRECTIONS SYSTÈME RAG DYNAMIQUE

echo "🔄 Synchronisation des corrections RAG dynamique..."

# Fichiers corrigés à synchroniser
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/universal_rag_engine.py" ~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_new_rag_system.py" ~/ZETA_APP/CHATBOT2.0/test_new_rag_system.py

echo "✅ Synchronisation terminée !"
echo "🧪 Pour tester : cd ~/ZETA_APP/CHATBOT2.0 && python test_new_rag_system.py"
