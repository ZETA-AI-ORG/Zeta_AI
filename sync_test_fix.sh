#!/bin/bash
# 🔧 SYNCHRONISATION CORRECTION TEST ULTIME

echo "🔧 Synchronisation des corrections du test ultime..."

# Synchronisation du test corrigé
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_ultimate_coherence.py" ~/ZETA_APP/CHATBOT2.0/test_ultimate_coherence.py

echo "✅ Corrections synchronisées !"
echo ""
echo "🔧 CORRECTIONS APPLIQUÉES:"
echo "1. ✅ Timeout API: 30s → 60s"
echo "2. ✅ Bug validation: Gestion dict/string"
echo "3. ✅ User ID: testuser135"
echo ""
echo "🧪 RELANCER LE TEST:"
echo "python test_ultimate_coherence.py"
echo ""
echo "⚠️ VÉRIFIER AVANT LE TEST:"
echo "# API fonctionne ?"
echo "curl -X POST http://127.0.0.1:8001/chat -H \"Content-Type: application/json\" -d '{\"message\":\"test\",\"company_id\":\"MpfnlSbqwaZ6F4HvxQLRL9du0yG3\",\"user_id\":\"testuser135\"}'"
