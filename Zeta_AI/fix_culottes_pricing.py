#!/usr/bin/env python3
"""
🔧 CORRECTIF : Clarifier pricing culottes (même prix toutes tailles)
"""
import os
from meilisearch import Client

# Configuration MeiliSearch
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://127.0.0.1:7700")
MEILISEARCH_KEY = os.getenv("MEILISEARCH_KEY", "N80w8LbzObzK18rZk7zwiHNpJLA_YFSvYGt2XzGLP_4")
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

def fix_culottes_documents():
    """Corrige les documents culottes pour clarifier le pricing unique"""
    
    client = Client(MEILISEARCH_HOST, MEILISEARCH_KEY)
    index_name = f"products_{COMPANY_ID}"
    index = client.index(index_name)
    
    print(f"🔍 Recherche documents 'Couches culottes'...")
    
    # Chercher tous les documents culottes
    results = index.search("Couches culottes", {
        "filter": "product = 'Couches culottes'",
        "limit": 10
    })
    
    print(f"📦 Trouvé {len(results['hits'])} documents")
    
    documents_to_update = []
    
    for doc in results['hits']:
        # IMPORTANT : Utiliser 'id' (clé primaire MeiliSearch) et non 'document_id'
        doc_id = doc.get('id')  # ← CORRECTION ICI
        document_id = doc.get('document_id')
        variant = doc.get('variant', '')
        price = doc.get('price', 0)
        quantity = doc.get('quantity', 0)
        
        # Nouveau searchable_text ULTRA CLAIR
        new_searchable_text = f"""Couches culottes {variant}
Prix UNIQUE pour TOUTES les tailles (5kg à 30kg): {price:,} FCFA
Lot de {quantity} pièces
Disponibles en toutes les tailles entre 5 et 30kg
IMPORTANT: Peu importe la taille demandée (taille 2, 3, 4, 5, 6), le prix reste {price:,} FCFA pour {quantity} pièces
Taille 2 (5-8kg): {price:,} FCFA
Taille 3 (8-11kg): {price:,} FCFA
Taille 4 (11-14kg): {price:,} FCFA
Taille 5 (14-18kg): {price:,} FCFA
Taille 6 (18-30kg): {price:,} FCFA
Vendu uniquement par lot de 150 ou 300 couches
Chaque paquet contient 50 couches
Poids minimum: 5kg (sinon préférer couches à pression)
baby_care Couches & Lingettes Couches culottes"""
        
        # Nouvelle description enrichie
        new_description = f"Lot de {quantity} Couches culottes. Prix UNIQUE {price:,} FCFA valable pour TOUTES les tailles de 5kg à 30kg (taille 2 à 6)."
        
        # Document à mettre à jour (UTILISER 'id' comme clé primaire)
        updated_doc = {
            'id': doc_id,  # ← CORRECTION : Clé primaire
            'searchable_text': new_searchable_text,
            'description': new_description,
            'content': f"{quantity} pièces de Couches culottes: {price:,} F CFA (TOUTES TAILLES 5-30kg)"
        }
        
        documents_to_update.append(updated_doc)
        
        print(f"\n✏️  Document ID: {doc_id}")
        print(f"   Document_ID: {document_id}")
        print(f"   Variant: {variant}")
        print(f"   Prix: {price:,} FCFA")
        print(f"   ✅ Enrichi avec mentions explicites tailles")
    
    if documents_to_update:
        print(f"\n🚀 Mise à jour de {len(documents_to_update)} documents...")
        task = index.update_documents(documents_to_update)
        print(f"✅ Task ID: {task.task_uid}")
        print(f"✅ Terminé ! Les documents culottes sont maintenant ultra-clairs sur le pricing unique.")
    else:
        print("⚠️  Aucun document à mettre à jour")

if __name__ == "__main__":
    print("="*80)
    print("🔧 CORRECTIF PRICING CULOTTES")
    print("="*80)
    fix_culottes_documents()
    print("\n" + "="*80)
