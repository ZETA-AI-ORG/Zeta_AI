#!/bin/bash
# 🔄 SYNCHRONISATION AVEC AJUSTEMENTS SCHÉMA SUPABASE

echo "🔄 Synchronisation avec ajustements schéma Supabase..."

# Fichiers modifiés pour correspondre au schéma
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/universal_rag_engine.py" ~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/supabase_simple.py" ~/ZETA_APP/CHATBOT2.0/core/supabase_simple.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_supabase_schema.py" ~/ZETA_APP/CHATBOT2.0/test_supabase_schema.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_new_rag_system.py" ~/ZETA_APP/CHATBOT2.0/test_new_rag_system.py

echo "✅ Synchronisation terminée !"
echo ""
echo "🧪 TESTS RECOMMANDÉS :"
echo "# 1. Vérifier le schéma Supabase :"
echo "python test_supabase_schema.py"
echo ""
echo "# 2. Test Supabase simple :"
echo "python -m core.supabase_simple"
echo ""
echo "# 3. Test RAG complet :"
echo "python test_new_rag_system.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3 testuser129"
