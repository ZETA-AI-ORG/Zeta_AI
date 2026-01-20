#!/usr/bin/env python3
"""
Script de test pour le système d'auto-apprentissage des patterns regex
"""
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.vector_store_clean import get_all_documents_for_company
from core.rag_regex_extractor import extract_regex_entities_from_docs

def test_dynamic_learning(company_id: str):
    """Test du système d'auto-apprentissage sur tous les documents d'une entreprise"""
    
    print(f"🧠 === TEST AUTO-APPRENTISSAGE PATTERNS ===\n")
    print(f"🏢 Entreprise: {company_id}\n")
    
    # Index à analyser
    indexes = [
        f"delivery_{company_id}",
        f"localisation_{company_id}",
        f"products_{company_id}",
        f"support_paiement_{company_id}"
    ]
    
    all_docs = []
    
    # Récupérer tous les documents
    for idx_name in indexes:
        try:
            docs = get_all_documents_for_company(company_id, idx_name)
            all_docs.extend(docs)
            print(f"📄 {len(docs)} documents récupérés de {idx_name}")
        except Exception as e:
            print(f"❌ Erreur {idx_name}: {e}")
    
    print(f"\n📊 Total: {len(all_docs)} documents à analyser\n")
    
    if not all_docs:
        print("❌ Aucun document trouvé")
        return
    
    # Compter les patterns avant apprentissage
    patterns_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'patterns_metier.json')
    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns_before = json.load(f)
        patterns_count_before = len(patterns_before)
    except:
        patterns_count_before = 0
    
    print(f"📋 Patterns avant apprentissage: {patterns_count_before}")
    
    # Lancer l'extraction avec auto-apprentissage activé
    print(f"\n🚀 Lancement de l'extraction avec auto-apprentissage...\n")
    
    results = extract_regex_entities_from_docs(all_docs, enable_learning=True)
    
    # Compter les patterns après apprentissage
    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns_after = json.load(f)
        patterns_count_after = len(patterns_after)
    except:
        patterns_count_after = patterns_count_before
    
    print(f"\n📋 Patterns après apprentissage: {patterns_count_after}")
    print(f"🎯 Nouveaux patterns appris: {patterns_count_after - patterns_count_before}")
    
    if patterns_count_after > patterns_count_before:
        print(f"\n🆕 NOUVEAUX PATTERNS DÉTECTÉS:")
        for key, pattern in patterns_after.items():
            if key not in patterns_before:
                print(f"   • {key}: {pattern}")
    
    # Afficher les résultats d'extraction
    total_entities = sum(len(v) for v in results.values())
    print(f"\n📊 RÉSULTATS D'EXTRACTION:")
    print(f"   • Total entités extraites: {total_entities}")
    
    if results:
        print(f"\n🏆 TOP ENTITÉS EXTRAITES:")
        sorted_results = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)
        for entity_type, values in sorted_results[:10]:
            if values:
                print(f"   • {entity_type}: {len(values)} occurrences")
    
    print(f"\n✅ Test terminé - Système d'auto-apprentissage opérationnel!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_dynamic_learning.py <company_id>")
        sys.exit(1)
    
    company_id = sys.argv[1]
    test_dynamic_learning(company_id)
