#!/usr/bin/env python3
"""
🔍 AUDIT COMPLET MEILI + SUPABASE - VÉRIFICATION INTÉGRITÉ DONNÉES
Company ID: 4OS4yFcf2LZwxhKojbAVbKuVuSdb
"""

import os
import sys
import json
from typing import Dict, List, Any
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"

# Meilisearch
MEILI_URL = "http://localhost:7700"
MEILI_API_KEY = "Bac2018mado@2066"

# Supabase (à configurer)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ilbihprkxcgsigvueeme.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ═══════════════════════════════════════════════════════════════════════════════
# 📦 IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    import meilisearch
    print("✅ Module meilisearch importé")
except ImportError:
    print("❌ Module meilisearch manquant. Installation...")
    os.system("pip install meilisearch")
    import meilisearch

try:
    from supabase import create_client, Client
    print("✅ Module supabase importé")
except ImportError:
    print("❌ Module supabase manquant. Installation...")
    os.system("pip install supabase")
    from supabase import create_client, Client

# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 AUDIT MEILISEARCH
# ═══════════════════════════════════════════════════════════════════════════════

def audit_meilisearch(company_id: str) -> Dict[str, Any]:
    """
    Audit complet des index Meilisearch pour une company
    """
    print("\n" + "="*80)
    print("🔍 AUDIT MEILISEARCH")
    print("="*80)
    
    client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)
    
    results = {
        "company_id": company_id,
        "timestamp": datetime.now().isoformat(),
        "indexes": {},
        "total_documents": 0,
        "errors": []
    }
    
    # Types d'index attendus
    index_types = ["products", "delivery", "support", "location", "company_docs"]
    
    for index_type in index_types:
        index_uid = f"{index_type}_{company_id}"
        
        try:
            print(f"\n📂 Index: {index_uid}")
            index = client.get_index(index_uid)
            
            # Récupérer tous les documents
            docs = index.get_documents(limit=1000)
            doc_count = len(docs.results)
            
            results["indexes"][index_type] = {
                "uid": index_uid,
                "document_count": doc_count,
                "documents": []
            }
            
            results["total_documents"] += doc_count
            
            print(f"   📊 Documents trouvés: {doc_count}")
            
            # Lister les documents
            for i, doc in enumerate(docs.results, 1):
                doc_info = {
                    "index": i,
                    "id": doc.get("id", "N/A"),
                    "content_preview": doc.get("content", "")[:100] + "..." if doc.get("content") else "N/A",
                    "metadata": doc.get("metadata", {}),
                    "content_length": len(doc.get("content", ""))
                }
                
                results["indexes"][index_type]["documents"].append(doc_info)
                
                print(f"   {i}. ID: {doc_info['id']}")
                print(f"      Contenu: {doc_info['content_preview']}")
                print(f"      Longueur: {doc_info['content_length']} chars")
                
                # Vérifier métadonnées
                metadata = doc.get("metadata", {})
                if metadata:
                    print(f"      Métadonnées: {list(metadata.keys())}")
                
        except Exception as e:
            error_msg = f"Erreur index {index_uid}: {str(e)}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
            results["indexes"][index_type] = {
                "uid": index_uid,
                "error": str(e)
            }
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 AUDIT SUPABASE
# ═══════════════════════════════════════════════════════════════════════════════

def audit_supabase(company_id: str) -> Dict[str, Any]:
    """
    Audit complet des documents Supabase pour une company
    """
    print("\n" + "="*80)
    print("🔍 AUDIT SUPABASE")
    print("="*80)
    
    if not SUPABASE_KEY:
        print("❌ SUPABASE_SERVICE_KEY non configurée")
        return {"error": "SUPABASE_SERVICE_KEY manquante"}
    
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    results = {
        "company_id": company_id,
        "timestamp": datetime.now().isoformat(),
        "documents": [],
        "total_documents": 0,
        "errors": []
    }
    
    try:
        # Récupérer tous les documents de la company
        response = client.table("documents") \
            .select("*") \
            .eq("company_id", company_id) \
            .execute()
        
        docs = response.data
        results["total_documents"] = len(docs)
        
        print(f"\n📊 Documents trouvés: {len(docs)}")
        
        for i, doc in enumerate(docs, 1):
            doc_info = {
                "index": i,
                "id": doc.get("id", "N/A"),
                "document_id": doc.get("document_id", "N/A"),
                "file_name": doc.get("file_name", "N/A"),
                "content_preview": doc.get("content", "")[:100] + "..." if doc.get("content") else "N/A",
                "metadata": doc.get("metadata", {}),
                "content_length": len(doc.get("content", "")),
                "created_at": doc.get("created_at", "N/A")
            }
            
            results["documents"].append(doc_info)
            
            print(f"\n{i}. Document ID: {doc_info['document_id']}")
            print(f"   Fichier: {doc_info['file_name']}")
            print(f"   Contenu: {doc_info['content_preview']}")
            print(f"   Longueur: {doc_info['content_length']} chars")
            print(f"   Créé: {doc_info['created_at']}")
            
            # Vérifier métadonnées
            metadata = doc.get("metadata", {})
            if metadata:
                print(f"   Métadonnées: {list(metadata.keys())}")
        
    except Exception as e:
        error_msg = f"Erreur Supabase: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 COMPARAISON & RAPPORT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(meili_results: Dict, supabase_results: Dict):
    """
    Génère un rapport comparatif
    """
    print("\n" + "="*80)
    print("📊 RAPPORT COMPARATIF")
    print("="*80)
    
    print(f"\n🔹 MEILISEARCH:")
    print(f"   Total documents: {meili_results['total_documents']}")
    print(f"   Index actifs: {len([k for k, v in meili_results['indexes'].items() if 'error' not in v])}")
    print(f"   Erreurs: {len(meili_results['errors'])}")
    
    print(f"\n🔹 SUPABASE:")
    print(f"   Total documents: {supabase_results.get('total_documents', 0)}")
    print(f"   Erreurs: {len(supabase_results.get('errors', []))}")
    
    # Vérifier cohérence
    print(f"\n🔍 VÉRIFICATION COHÉRENCE:")
    
    meili_total = meili_results['total_documents']
    supabase_total = supabase_results.get('total_documents', 0)
    
    if meili_total == supabase_total:
        print(f"   ✅ Nombre de documents identique: {meili_total}")
    else:
        print(f"   ⚠️ Différence détectée:")
        print(f"      Meili: {meili_total} docs")
        print(f"      Supabase: {supabase_total} docs")
        print(f"      Écart: {abs(meili_total - supabase_total)} docs")
    
    # Sauvegarder rapport JSON
    report = {
        "meilisearch": meili_results,
        "supabase": supabase_results,
        "summary": {
            "meili_total": meili_total,
            "supabase_total": supabase_total,
            "difference": abs(meili_total - supabase_total),
            "coherent": meili_total == supabase_total
        }
    }
    
    report_file = f"audit_report_{COMPANY_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Rapport sauvegardé: {report_file}")
    
    return report

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*80)
    print("🔍 AUDIT COMPLET MEILI + SUPABASE")
    print("="*80)
    print(f"Company ID: {COMPANY_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Audit Meilisearch
    meili_results = audit_meilisearch(COMPANY_ID)
    
    # Audit Supabase
    supabase_results = audit_supabase(COMPANY_ID)
    
    # Rapport comparatif
    report = generate_report(meili_results, supabase_results)
    
    print("\n" + "="*80)
    print("✅ AUDIT TERMINÉ")
    print("="*80)
    
    return report

if __name__ == "__main__":
    try:
        report = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️ Audit interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
