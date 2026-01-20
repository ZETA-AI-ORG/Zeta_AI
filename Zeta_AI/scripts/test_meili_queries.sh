#!/usr/bin/env bash
set -euo pipefail

# Script de tests Meilisearch pour "Rue du grossiste"
# - Exécute une batterie de requêtes (produits/livraison/support/company/combined)
# - Écrit les réponses JSON dans ./out/tests/
#
# Prérequis:
#   - bash + curl
#   - (optionnel) export MEILI_URL et MEILI_API_KEY dans l'environnement
#     Par défaut, on utilisera le domaine Cloudflare configuré

CID="XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
MEILI_URL="${MEILI_URL:-https://meili.zetaapp.xyz}"
if [[ -z "${MEILI_API_KEY:-}" ]]; then
  echo "[ERROR] MEILI_API_KEY n'est pas défini. Exportez la clé puis relancez." >&2
  echo "        Exemple: export MEILI_API_KEY=\"votre_cle\"" >&2
  exit 1
fi
AUTH_HEADER=(
  -H "Authorization: Bearer ${MEILI_API_KEY}"
  -H "X-Meili-API-Key: ${MEILI_API_KEY}"
)

OUT_DIR="out/tests"
mkdir -p "$OUT_DIR"

echo "[INFO] Target Meili: ${MEILI_URL} (company_id=${CID})"

call_search() {
  local index_uid="$1"; shift
  local payload="$1"; shift
  local outfile="$1"; shift

  echo "[RUN] ${index_uid} -> ${outfile}"
  local status
  status=$(curl -sS -w "%{http_code}" -X POST "${MEILI_URL}/indexes/${index_uid}/search" \
    -H "Content-Type: application/json" \
    "${AUTH_HEADER[@]}" \
    -d "${payload}" \
    -o "${outfile}")
  if [[ "$status" != "200" ]]; then
    echo "[ERROR] HTTP ${status} pour ${index_uid}. Extrait de la réponse:" >&2
    head -c 400 "$outfile" >&2 || true
    echo -e "\n" >&2
  fi
}

# --------------------
# PRODUITS
# --------------------
call_search \
  "products_${CID}" \
  '{
     "q": "casque noir",
     "filter": "category = \"Auto & Moto\" AND subcategory = \"Casques & Équipement Moto\" AND color = \"NOIR\"",
     "sort": ["stock:desc"],
     "limit": 5
   }' \
  "${OUT_DIR}/products_casque_noir.json"

call_search \
  "products_${CID}" \
  '{
     "q": "",
     "facets": ["category","subcategory","color","facet_tags"],
     "limit": 0
   }' \
  "${OUT_DIR}/products_facets.json"

call_search \
  "products_${CID}" \
  '{
     "q": "casque",
     "sort": ["min_price:asc"],
     "limit": 5
   }' \
  "${OUT_DIR}/products_sort_price.json"

# --------------------
# LIVRAISON
# --------------------
call_search \
  "delivery_${CID}" \
  '{
     "q": "Yopougon",
     "filter": "zone = \"Yopougon\"",
     "sort": ["min_price:asc"],
     "limit": 3
   }' \
  "${OUT_DIR}/delivery_yopougon.json"

call_search \
  "delivery_${CID}" \
  '{
     "q": "",
     "filter": "zone = \"Cocody\" OR zone = \"Riviera\"",
     "facets": ["zone","zone_group","city"],
     "sort": ["min_price:asc"],
     "limit": 5
   }' \
  "${OUT_DIR}/delivery_abidjan_groups.json"

call_search \
  "delivery_${CID}" \
  '{
     "q": "",
     "filter": "zone_group = \"Hors Abidjan\"",
     "limit": 3
   }' \
  "${OUT_DIR}/delivery_hors_abidjan.json"

# --------------------
# SUPPORT
# --------------------
call_search \
  "support_${CID}" \
  '{
     "q": "",
     "filter": "channels = \"whatsapp\"",
     "limit": 5
   }' \
  "${OUT_DIR}/support_whatsapp.json"

call_search \
  "support_${CID}" \
  '{
     "q": "toujours ouvert +2250787",
     "limit": 5
   }' \
  "${OUT_DIR}/support_text_query.json"

# --------------------
# COMPANY
# --------------------
call_search \
  "company_${CID}" \
  '{
     "q": "meilleurs produits meilleurs prix",
     "limit": 3
   }' \
  "${OUT_DIR}/company_identity.json"

# --------------------
# COMBINED
# --------------------
call_search \
  "company_docs_${CID}" \
  '{
     "q": "casque",
     "filter": "category = \"Auto & Moto\" AND subcategory = \"Casques & Équipement Moto\" AND color = \"ROUGE\"",
     "sort": ["stock:desc"],
     "facets": ["category","subcategory","color","zone","zone_group","channels"],
     "limit": 5
   }' \
  "${OUT_DIR}/combined_products_rouge.json"

call_search \
  "company_docs_${CID}" \
  '{
    "q": "Abidjan Cocody Riviera",
    "filter": "store_type = \"delivery\"",
    "sort": ["min_price:asc"],
    "limit": 5
  }' \
  "${OUT_DIR}/combined_delivery_abidjan.json"

call_search \
  "company_docs_${CID}" \
  '{
     "q": "Wave +2250787360757",
     "limit": 5
   }' \
  "${OUT_DIR}/combined_payment_wave.json"

echo "[DONE] Résultats écrits dans ${OUT_DIR}/"
