#!/bin/bash
# 🚨 CORRECTION URGENTE - COLONNE EMBEDDING

echo "🚨 Correction urgente: utilisation colonne 'embedding' au lieu de 'embedding_dense'"

# Synchronisation de la correction
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/supabase_simple.py" ~/ZETA_APP/CHATBOT2.0/core/supabase_simple.py && \
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_supabase_fix.py" ~/ZETA_APP/CHATBOT2.0/test_supabase_fix.py

echo "✅ Correction synchronisée !"
echo ""
echo "🧪 TESTS RECOMMANDÉS :"
echo "# Test correction rapide :"
echo "python test_supabase_fix.py"
echo ""
echo "# Test Supabase complet :"
echo "python -m core.supabase_simple"
echo ""
echo "# Test RAG complet :"
echo "python test_new_rag_system.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3 testuser129"
