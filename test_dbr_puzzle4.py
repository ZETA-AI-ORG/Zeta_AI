#!/usr/bin/env python3
"""
🧩 PUZZLE 4 : Test DBR (TOP 3 par index matché)

Objectif :
- Prendre des docs scorés en entrée
- Regrouper par index
- Garder TOP 3 par index (ou moins si < 3 docs)
- Retourner les docs finaux

Usage:
    python test_dbr_puzzle4.py
"""

from collections import defaultdict

# ========== DONNÉES DE TEST (docs scorés depuis PUZZLE 3) ==========

test_scored_docs = [
    {
        'id': 'couches_a_pression_taille_4_9_a_14_kg_300_couches_24000_f_cfa_txt',
        'content': 'PRODUIT: Couches à pression VARIANTE: Taille 4...',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 100.0
    },
    {
        'id': 'couches_a_pression_taille_1_0_a_4_kg_300_couches_17900_f_cfa_txt',
        'content': 'PRODUIT: Couches à pression VARIANTE: Taille 1...',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 100.0
    },
    {
        'id': 'couches_a_pression_taille_2_3_a_8_kg_300_couches_18900_f_cfa_txt',
        'content': 'PRODUIT: Couches à pression VARIANTE: Taille 2...',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 98.5
    },
    {
        'id': 'couches_a_pression_taille_3_6_a_11_kg_300_couches_22900_f_cfa_txt',
        'content': 'PRODUIT: Couches à pression VARIANTE: Taille 3...',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 97.0
    },
    {
        'id': 'couches_a_pression_taille_5_12_a_17_kg_300_couches_24900_f_cfa_txt',
        'content': 'PRODUIT: Couches à pression VARIANTE: Taille 5...',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 96.0
    },
    {
        'id': 'livraison_zones_peripheriques_txt',
        'content': 'LIVRAISON - ZONES PÉRIPHÉRIQUES ABIDJAN...',
        'source_index': 'delivery_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 90.74
    },
    {
        'id': 'livraison_zones_centrales_txt',
        'content': 'LIVRAISON - ZONES CENTRALES ABIDJAN...',
        'source_index': 'delivery_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 70.06
    },
    {
        'id': 'livraison_hors_abidjan_txt',
        'content': 'LIVRAISON - HORS ABIDJAN (TOUTE CÔTE D\'IVOIRE)...',
        'source_index': 'delivery_4OS4yFcf2LZwxhKojbAVbKuVuSdb',
        'final_score': 65.0
    }
]


# ========== FONCTION DBR ==========

def apply_dbr_top3_per_index(scored_docs: list) -> list:
    """
    Regroupe les docs par index et garde TOP 3 par index (ou moins si < 3)
    """
    docs_by_index = defaultdict(list)
    
    # Regrouper par index
    for doc in scored_docs:
        docs_by_index[doc['source_index']].append(doc)
    
    # Garder TOP 3 par index
    final_docs = []
    for index_name, docs in docs_by_index.items():
        # Trier par score décroissant
        sorted_docs = sorted(docs, key=lambda x: x['final_score'], reverse=True)
        # Garder top 3 (ou moins si < 3)
        top_3 = sorted_docs[:3]
        final_docs.extend(top_3)
        print(f"📦 [DBR] {index_name}: {len(top_3)}/{len(docs)} docs gardés (scores: {[round(d['final_score'], 2) for d in top_3]})")
    
    # Trier globalement par score pour l'affichage final
    final_docs = sorted(final_docs, key=lambda x: x['final_score'], reverse=True)
    
    return final_docs


# ========== PIPELINE DE TEST ==========

def test_dbr_pipeline():
    """Test du DBR inter-index"""
    
    print("=" * 80)
    print("🧩 PUZZLE 4 : Test DBR (TOP 3 par index)")
    print("=" * 80)
    print()
    
    print(f"📊 Docs en entrée: {len(test_scored_docs)}")
    print()
    
    # Afficher les docs par index AVANT DBR
    print("=" * 80)
    print("📋 DOCS PAR INDEX (AVANT DBR)")
    print("=" * 80)
    print()
    
    by_index = defaultdict(list)
    for doc in test_scored_docs:
        by_index[doc['source_index']].append(doc)
    
    for idx, docs in by_index.items():
        print(f"🔹 {idx}: {len(docs)} docs")
        for d in sorted(docs, key=lambda x: x['final_score'], reverse=True):
            print(f"   - Score: {d['final_score']:.2f} | ID: {d['id']}")
        print()
    
    # Appliquer DBR
    print("=" * 80)
    print("🔧 APPLICATION DBR (TOP 3 par index)")
    print("=" * 80)
    print()
    
    final_docs = apply_dbr_top3_per_index(test_scored_docs)
    
    print()
    print("=" * 80)
    print("📈 RÉSUMÉ FINAL (Tri par score décroissant)")
    print("=" * 80)
    print()
    
    print(f"✅ Total docs retenus: {len(final_docs)}/{len(test_scored_docs)}")
    print()
    
    for i, doc in enumerate(final_docs, 1):
        print(f"{i}. [{doc['source_index']}] Score: {doc['final_score']:.2f}/100")
        print(f"   ID: {doc['id']}")
        print()
    
    print("=" * 80)
    print("✅ Test terminé")
    print("=" * 80)


if __name__ == "__main__":
    test_dbr_pipeline()
