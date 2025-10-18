#!/usr/bin/env python3
"""
Script pour appliquer rétroactivement l'extraction/tagging regex automatisé sur tous les documents déjà ingérés d'une entreprise.
- Met à jour le champ 'entities' dans chaque document (et/ou Redis)
"""
import sys
import os
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.vector_store_clean import get_all_documents_for_company, update_document_entities
from core.rag_regex_extractor import extract_regex_entities_from_docs

import redis
r = redis.Redis(host='localhost', port=6379, db=0)

if len(sys.argv) < 2:
    print("Usage: python retro_regex_tagging.py <company_id> [index_name]")
    sys.exit(1)

company_id = sys.argv[1]
index_name = sys.argv[2] if len(sys.argv) > 2 else None

# 1. Récupérer tous les documents de l'entreprise
print(f"[INFO] Récupération des docs pour {company_id} ...")
docs = get_all_documents_for_company(company_id, index_name=index_name, limit=10000)
print(f"[INFO] {len(docs)} documents trouvés.")

# 2. Appliquer l'extraction regex sur chaque doc
for i, doc in enumerate(docs, 1):
    content = doc.get('content', '')
    doc_id = doc.get('id') or doc.get('doc_id')
    regex_entities = extract_regex_entities_from_docs([doc])
    # Format simple : {label: [valeurs]}
    doc['entities'] = {k: v for k, v in regex_entities.items() if v}
    # Mettre à jour en base (Meili ou SQL)
    update_document_entities(doc_id, doc['entities'], index_name)
    # Mettre à jour en Redis
    if doc_id:
        r.set(f"entities:{doc_id}", json.dumps(doc['entities'], ensure_ascii=False))
    if i % 100 == 0:
        print(f"[PROGRESS] {i}/{len(docs)} docs traités...")
print("[DONE] Tagging regex rétroactif terminé.")
