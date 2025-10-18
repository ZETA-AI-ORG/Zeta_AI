#!/bin/bash
# 🔍 TEST DIRECT CURL POUR DIAGNOSTIC

echo "🔍 TEST DIRECT CURL - DIAGNOSTIC RAG"
echo "=" * 50

echo ""
echo "🧪 TEST 1: Prix taille 3 (question qui échoue)"
echo "curl -X POST http://127.0.0.1:8001/chat \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\":\"Quel est le prix exact de la taille 3 couches à pression?\",\"company_id\":\"MpfnlSbqwaZ6F4HvxQLRL9du0yG3\",\"user_id\":\"testuser135\"}'"

curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Quel est le prix exact de la taille 3 couches à pression?","company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"testuser135"}'

echo ""
echo ""
echo "🧪 TEST 2: Question simple (pour comparaison)"
echo "curl -X POST http://127.0.0.1:8001/chat \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\":\"bonjour\",\"company_id\":\"MpfnlSbqwaZ6F4HvxQLRL9du0yG3\",\"user_id\":\"testuser135\"}'"

curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"bonjour","company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"testuser135"}'

echo ""
echo ""
echo "🔍 VÉRIFIER LES LOGS SERVEUR MAINTENANT !"
echo "Regarder les logs pour voir:"
echo "1. Si MeiliSearch trouve des documents"
echo "2. Si Supabase fallback se déclenche"
echo "3. Quel contexte est fourni au LLM"
echo "4. Pourquoi method_used = 'unknown'"
