#!/bin/bash
# Commandes CURL pour vérifier tous les index MeiliSearch

COMPANY_ID="MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
MEILI_URL="http://127.0.0.1:7700"

echo "================================================================"
echo "🔍 VÉRIFICATION MEILI - TOUS LES INDEX"
echo "================================================================"

# 1. INDEX PRODUCTS (19 produits splittés)
echo ""
echo "1️⃣  INDEX PRODUCTS (attendu: 19 docs)"
echo "================================================================"
curl -s "${MEILI_URL}/indexes/products_${COMPANY_ID}/documents?limit=1000" | \
  python -m json.tool | \
  grep -E '"product"|"variant"|"price"|"results"' | \
  head -50

echo ""
echo "   📊 Compte total:"
curl -s "${MEILI_URL}/indexes/products_${COMPANY_ID}/stats" | \
  python -m json.tool | \
  grep numberOfDocuments

# 2. INDEX DELIVERY (3 zones)
echo ""
echo "2️⃣  INDEX DELIVERY (attendu: 3 docs)"
echo "================================================================"
curl -s "${MEILI_URL}/indexes/delivery_${COMPANY_ID}/documents?limit=10" | \
  python -m json.tool | \
  grep -E '"type"|"content"' | \
  head -20

echo ""
echo "   📊 Compte total:"
curl -s "${MEILI_URL}/indexes/delivery_${COMPANY_ID}/stats" | \
  python -m json.tool | \
  grep numberOfDocuments

# 3. INDEX SUPPORT_PAIEMENT (2 docs)
echo ""
echo "3️⃣  INDEX SUPPORT_PAIEMENT (attendu: 2 docs)"
echo "================================================================"
curl -s "${MEILI_URL}/indexes/support_paiement_${COMPANY_ID}/documents?limit=10" | \
  python -m json.tool | \
  grep -E '"type"|"content"' | \
  head -20

echo ""
echo "   📊 Compte total:"
curl -s "${MEILI_URL}/indexes/support_paiement_${COMPANY_ID}/stats" | \
  python -m json.tool | \
  grep numberOfDocuments

# 4. INDEX LOCALISATION (1 doc)
echo ""
echo "4️⃣  INDEX LOCALISATION (attendu: 1 doc)"
echo "================================================================"
curl -s "${MEILI_URL}/indexes/localisation_${COMPANY_ID}/documents?limit=10" | \
  python -m json.tool | \
  grep -E '"content"' | \
  head -10

echo ""
echo "   📊 Compte total:"
curl -s "${MEILI_URL}/indexes/localisation_${COMPANY_ID}/stats" | \
  python -m json.tool | \
  grep numberOfDocuments

# 5. INDEX COMPANY_DOCS (29 docs backup)
echo ""
echo "5️⃣  INDEX COMPANY_DOCS (attendu: 29 docs)"
echo "================================================================"
curl -s "${MEILI_URL}/indexes/company_docs_${COMPANY_ID}/documents?limit=1000" | \
  python -m json.tool | \
  grep -E '"type"' | \
  sort | uniq -c

echo ""
echo "   📊 Compte total:"
curl -s "${MEILI_URL}/indexes/company_docs_${COMPANY_ID}/stats" | \
  python -m json.tool | \
  grep numberOfDocuments

# RÉSUMÉ GLOBAL
echo ""
echo "================================================================"
echo "📊 RÉSUMÉ GLOBAL"
echo "================================================================"
echo ""
echo "INDEX                    | DOCS | ATTENDU"
echo "-------------------------|------|--------"
printf "products                 | %4s | 19\n" \
  "$(curl -s "${MEILI_URL}/indexes/products_${COMPANY_ID}/stats" | python -c 'import sys,json; print(json.load(sys.stdin)["numberOfDocuments"])')"
printf "delivery                 | %4s | 3\n" \
  "$(curl -s "${MEILI_URL}/indexes/delivery_${COMPANY_ID}/stats" | python -c 'import sys,json; print(json.load(sys.stdin)["numberOfDocuments"])')"
printf "support_paiement         | %4s | 2\n" \
  "$(curl -s "${MEILI_URL}/indexes/support_paiement_${COMPANY_ID}/stats" | python -c 'import sys,json; print(json.load(sys.stdin)["numberOfDocuments"])')"
printf "localisation             | %4s | 1\n" \
  "$(curl -s "${MEILI_URL}/indexes/localisation_${COMPANY_ID}/stats" | python -c 'import sys,json; print(json.load(sys.stdin)["numberOfDocuments"])')"
printf "company_docs (backup)    | %4s | 29\n" \
  "$(curl -s "${MEILI_URL}/indexes/company_docs_${COMPANY_ID}/stats" | python -c 'import sys,json; print(json.load(sys.stdin)["numberOfDocuments"])')"
echo ""
echo "================================================================"
