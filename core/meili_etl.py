#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meili_etl.py

ETL autonome pour transformer un texte structuré (identité, catalogue, livraison, support)
en documents plats prêts pour Meilisearch, avec 3 index thématiques:
- products: 1 document par variante produit
- delivery: 1 document par zone/groupe de zones
- support: informations de contact et paiement
+ company: identité (facultatif)

Usage (exemples):
    python CHATBOT2.0/ingestion/meili_etl.py --input rue-du-grossiste-doc.txt --outdir out/
    # pour pousser vers Meili directement (variables MEILI_URL/MEILI_API_KEY)
    python CHATBOT2.0/ingestion/meili_etl.py --input rue-du-grossiste-doc.txt --push-meili --company-id Xxxx

Sorties:
- out/products.json
- out/delivery.json
- out/support.json
- out/company.json
- out/combined_meili.json (tous types confondus)

"""
import argparse
import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional

# ------------- Helpers -------------

def _norm(s: str) -> str:
    return (s or "").strip()

# ------------- Parsing du texte source -------------

PRODUCT_HEADER_RE = re.compile(r"^\s*Produit\s*:\s*(.+?)\s*$", re.IGNORECASE)
DESC_RE = re.compile(r"^\s*Description\s*:\s*(.+?)\s*$", re.IGNORECASE)
CATEGORY_RE = re.compile(r"^\s*Catégorie\s*:\s*(.+?)\s*$", re.IGNORECASE)
SUBCATEGORY_RE = re.compile(r"^\s*Sous-catégorie\s*:\s*(.+?)\s*$", re.IGNORECASE)
VARIANT_HEADER_RE = re.compile(r"^\s*Variante\s*\(\s*Couleur\s*:\s*(.+?)\s*\)\s*:\s*$", re.IGNORECASE)
KV_RE = re.compile(r"^\s*([A-Za-zÀ-ÖØ-öø-ÿ'’`\-\s]+?)\s*:\s*(.+?)\s*$")
DELIVERY_INFO_RE = re.compile(r"^\s*Informations de livraison.*:\s*$", re.IGNORECASE)
DELIVERY_ZONES_RE = re.compile(r"^\s*Zones et Frais\s*:\s*(.*?)\s*$", re.IGNORECASE)
DELIVERY_ZONES_HEADER_ONLY_RE = re.compile(r"^\s*Zones et Frais\s*:\s*$", re.IGNORECASE)
DELAIS_RE = re.compile(r"^\s*Délais\s*:\s*(.+?)\s*$", re.IGNORECASE)
PAYMENT_HEADER_RE = re.compile(r"^\s*Modes de paiement acceptés\s*:\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*[-•]\s+(.+)$")
SUPPORT_CONTACT_RE = re.compile(r"^\s*Contact du support\s*:\s*(.+?)\s*$", re.IGNORECASE)
HOURS_RE = re.compile(r"^\s*Horaires d'ouverture\s*:\s*(.+?)\s*$", re.IGNORECASE)
STORE_TYPE_RE = re.compile(r"^\s*Type de boutique\s*:\s*(.+?)\s*$", re.IGNORECASE)
FAQ_RE = re.compile(r"^\s*FAQ\s*:\s*(.+?)\s*$", re.IGNORECASE)

COMPANY_NAME_RE = re.compile(r"^\s*Nom de l'Entreprise\s*:\s*(.+?)\s*$", re.IGNORECASE)
AI_NAME_RE = re.compile(r"^\s*Nom de l'IA\s*:\s*(.+?)\s*$", re.IGNORECASE)
SECTOR_RE = re.compile(r"^\s*Secteur d'activité\s*:\s*(.+?)\s*$", re.IGNORECASE)
COMPANY_DESC_RE = re.compile(r"^\s*Description de l'Entreprise\s*:\s*(.+?)\s*$", re.IGNORECASE)
MISSION_RE = re.compile(r"^\s*Mission\s*:\s*(.+?)\s*$", re.IGNORECASE)
OBJECTIVE_RE = re.compile(r"^\s*Objectif de l'IA\s*:\s*(.+?)\s*$", re.IGNORECASE)
ZONE_ACT_RE = re.compile(r"^\s*Zone d[’']activité\s*:\s*(.+?)\s*$", re.IGNORECASE)
DEPOSIT_RE = re.compile(r"^\s*Acompte requis\s*:\s*(.+?)\s*$", re.IGNORECASE)
RETURN_POLICY_RE = re.compile(r"^\s*Politique de retour/garantie\s*:\s*(.+?)\s*$", re.IGNORECASE)
ORDER_PROCESS_RE = re.compile(r"^\s*Processus de commande\s*:\s*(.+?)\s*$", re.IGNORECASE)

def parse_company(block_lines: List[str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {"type": "company"}
    for line in block_lines:
        m = COMPANY_NAME_RE.match(line)
        if m:
            data["name"] = _norm(m.group(1))
            continue
        m = AI_NAME_RE.match(line)
        if m:
            data["ai_name"] = _norm(m.group(1))
            continue
        m = SECTOR_RE.match(line)
        if m:
            data["sector"] = _norm(m.group(1))
            continue
        m = COMPANY_DESC_RE.match(line)
        if m:
            data["description"] = _norm(m.group(1))
            continue
        m = MISSION_RE.match(line)
        if m:
            data["mission"] = _norm(m.group(1))
            continue
        m = OBJECTIVE_RE.match(line)
        if m:
            data["objective"] = _norm(m.group(1))
            continue
        m = ZONE_ACT_RE.match(line)
        if m:
            data["zone"] = _norm(m.group(1))
            continue
        m = DEPOSIT_RE.match(line)
        if m:
            val = _norm(m.group(1))
            data["deposit_required"] = (val.lower().startswith("o") or val.lower() == "oui") if val else None
            continue
        m = RETURN_POLICY_RE.match(line)
        if m:
            data["return_policy"] = _norm(m.group(1))
            continue
        m = ORDER_PROCESS_RE.match(line)
        if m:
            data["order_process"] = _norm(m.group(1))
            continue
    data["id"] = "business_identity"
    return data

# --- Ajout d'un auto-patch settings Meili pour robustesse ingestion ---
from core.meilisearch_utils import ensure_meili_index_settings

def robust_index_products(meili_client, index_name, docs):
    # Attributs à rendre filterable pour éviter erreurs facettes
    filterable = ["category", "color", "subcategory", "ai_name", "company_id", "content", "created_at", "description", "document_id", "id", "id_raw", "id_slug", "mission", "name", "objective", "sector", "type", "updated_at", "zone"]
    ensure_meili_index_settings(meili_client, index_name, filterable=filterable)
    # Indexation classique
    meili_client.index(index_name).add_documents(docs)

{{ ... }}
