#!/usr/bin/env python3
"""
Script pour afficher toutes les entités regex extraites des documents MeiliSearch
"""
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.vector_store_clean import get_all_documents_for_company

def show_extracted_entities(company_id: str, index_name: str = None):
    """Affiche toutes les entités extraites"""
    
    print(f"🔍 === ENTITÉS EXTRAITES POUR {company_id} ===\n")
    
    # Index à analyser
    if index_name:
        indexes_to_check = [index_name]
    else:
        indexes_to_check = [
            f"delivery_{company_id}",
            f"localisation_{company_id}",
            f"products_{company_id}",
            f"support_paiement_{company_id}"
        ]
    
    total_docs = 0
    total_entities = 0
    
    for idx_name in indexes_to_check:
        print(f"📋 INDEX: {idx_name}")
        print("=" * 80)
        
        try:
            docs = get_all_documents_for_company(company_id, idx_name)
            
            if not docs:
                print("❌ Aucun document trouvé\n")
                continue
            
            docs_with_entities = 0
            
            for i, doc in enumerate(docs, 1):
                doc_id = doc.get('id', f'doc_{i}')
                content_preview = doc.get('content', '')[:100] + '...'
                entities = doc.get('entities', {})
                
                print(f"📄 Document {i}/{len(docs)} - ID: {doc_id}")
                print(f"   Contenu: {content_preview}")
                
                if entities:
                    docs_with_entities += 1
                    print(f"   ✅ Entités extraites:")
                    for entity_type, values in entities.items():
                        if values:  # Seulement si des valeurs ont été trouvées
                            print(f"      🔸 {entity_type}: {values}")
                            total_entities += len(values)
                else:
                    print(f"   ⚠️  Aucune entité extraite")
                
                print()
            
            total_docs += len(docs)
            print(f"📊 Résumé {idx_name}:")
            print(f"   • Total documents: {len(docs)}")
            print(f"   • Documents avec entités: {docs_with_entities}")
            print(f"   • Taux d'extraction: {docs_with_entities/len(docs)*100:.1f}%")
            
        except Exception as e:
            print(f"❌ Erreur analyse {idx_name}: {e}")
        
        print("\n" + "-" * 80 + "\n")
    
    # Résumé global
    print("📊 RÉSUMÉ GLOBAL")
    print("=" * 50)
    print(f"📄 Total documents analysés: {total_docs}")
    print(f"🔸 Total entités extraites: {total_entities}")
    print(f"📈 Moyenne entités/document: {total_entities/total_docs:.1f}" if total_docs > 0 else "📈 Aucune donnée")
    
    # Affichage des types d'entités les plus fréquents
    entity_counts = {}
    for idx_name in indexes_to_check:
        try:
            docs = get_all_documents_for_company(company_id, idx_name)
            for doc in docs:
                entities = doc.get('entities', {})
                for entity_type, values in entities.items():
                    if values:
                        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + len(values)
        except:
            continue
    
    if entity_counts:
        print(f"\n🏆 TOP ENTITÉS EXTRAITES:")
        for entity_type, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {entity_type}: {count} occurrences")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python show_extracted_entities.py <company_id> [index_name]")
        sys.exit(1)
    
    company_id = sys.argv[1]
    index_name = sys.argv[2] if len(sys.argv) > 2 else None
    show_extracted_entities(company_id, index_name)
