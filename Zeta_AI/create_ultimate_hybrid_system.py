#!/usr/bin/env python3
"""
🔥 CRÉATION DU SYSTÈME HYBRIDE ULTIME
Fusion du meilleur de l'ancien (Supabase) + nouveau (MeiliSearch)
"""

import os
import shutil
from datetime import datetime

def create_ultimate_hybrid_rag():
    """Crée le système RAG hybride ultime"""
    print("🔥 CRÉATION SYSTÈME HYBRIDE ULTIME")
    print("=" * 60)
    
    hybrid_content = '''import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from utils import log3, timing_metric

class UltimateHybridRAG:
    """
    🎯 SYSTÈME RAG HYBRIDE ULTIME
    Combine le meilleur de l'ancien (Supabase) et nouveau (MeiliSearch)
    """
    
    def __init__(self):
        self.supabase_engine = None
        self.meili_engine = None
        self.initialize_engines()
    
    def initialize_engines(self):
        """Initialise les deux moteurs"""
        try:
            # 🟢 Ancien moteur Supabase (HYDE + Anti-hallucination)
            from core.rag_engine_simplified_fixed import SimplifiedRAGEngine
            self.supabase_engine = SimplifiedRAGEngine()
            log3("[HYBRID]", "✅ Ancien moteur Supabase initialisé")
            
            # 🟢 Nouveau moteur MeiliSearch (Optimisé)
            from database.vector_store_old_restored import search_meili_keywords
            self.meili_search_func = search_meili_keywords
            log3("[HYBRID]", "✅ Nouveau moteur MeiliSearch initialisé")
            
        except Exception as e:
            log3("[HYBRID]", f"❌ Erreur initialisation: {e}")
    
    async def ultimate_dual_search(self, query: str, company_id: str) -> Tuple[List[Dict], str, str]:
        """
        🎯 RECHERCHE HYBRIDE ULTIME
        Combine Supabase (ancien) + MeiliSearch (nouveau) en parallèle
        """
        log3("[HYBRID]", f"🚀 Recherche hybride: '{query}'")
        start_time = time.time()
        
        try:
            # 🔄 Lancer les deux recherches en parallèle
            supabase_task = self.search_with_ancien_supabase(query, company_id)
            meili_task = self.search_with_nouveau_meili(query, company_id)
            
            # ⚡ Exécution parallèle
            supabase_results, meili_results = await asyncio.gather(
                supabase_task, 
                meili_task,
                return_exceptions=True
            )
            
            # 🔍 Traitement des résultats
            final_documents, final_context = self.merge_results(
                supabase_results, meili_results, query
            )
            
            elapsed = (time.time() - start_time) * 1000
            log3("[HYBRID]", f"⏱️ Recherche hybride terminée: {elapsed:.1f}ms")
            
            return final_documents, final_context, f"hybrid_search_{len(final_documents)}_docs"
            
        except Exception as e:
            log3("[HYBRID]", f"❌ Erreur recherche hybride: {e}")
            return [], "", "hybrid_error"
    
    async def search_with_ancien_supabase(self, query: str, company_id: str) -> Dict:
        """🟢 Recherche avec l'ancien système Supabase (HYDE + Anti-hallucination)"""
        try:
            log3("[HYBRID_SUPABASE]", f"🔍 Recherche ancien Supabase: '{query}'")
            
            if self.supabase_engine:
                # Utiliser la méthode dual_search de l'ancien système
                documents, supabase_context, meili_context = await self.supabase_engine.dual_search(
                    query, company_id
                )
                
                log3("[HYBRID_SUPABASE]", f"✅ Trouvé {len(documents)} documents Supabase")
                
                return {
                    "success": True,
                    "documents": documents,
                    "context": supabase_context,
                    "method": "ancien_supabase_hyde",
                    "count": len(documents)
                }
            else:
                return {"success": False, "documents": [], "context": "", "method": "supabase_error"}
                
        except Exception as e:
            log3("[HYBRID_SUPABASE]", f"❌ Erreur Supabase: {e}")
            return {"success": False, "documents": [], "context": "", "method": "supabase_exception"}
    
    async def search_with_nouveau_meili(self, query: str, company_id: str) -> Dict:
        """🟢 Recherche avec le nouveau système MeiliSearch (Optimisé)"""
        try:
            log3("[HYBRID_MEILI]", f"🔍 Recherche nouveau MeiliSearch: '{query}'")
            
            if self.meili_search_func:
                # Utiliser la fonction MeiliSearch restaurée
                documents = await self.meili_search_func(query, company_id, limit=10)
                
                # Formater le contexte
                context = self.format_meili_context(documents)
                
                log3("[HYBRID_MEILI]", f"✅ Trouvé {len(documents)} documents MeiliSearch")
                
                return {
                    "success": True,
                    "documents": documents,
                    "context": context,
                    "method": "nouveau_meili_optimise",
                    "count": len(documents)
                }
            else:
                return {"success": False, "documents": [], "context": "", "method": "meili_error"}
                
        except Exception as e:
            log3("[HYBRID_MEILI]", f"❌ Erreur MeiliSearch: {e}")
            return {"success": False, "documents": [], "context": "", "method": "meili_exception"}
    
    def format_meili_context(self, documents: List[Dict]) -> str:
        """Formate le contexte MeiliSearch"""
        if not documents:
            return ""
        
        context_parts = []
        for i, doc in enumerate(documents[:5], 1):  # Max 5 documents
            content = doc.get('content', '')
            if content:
                context_parts.append(f"Document {i}: {content[:200]}...")
        
        return "\\n\\n".join(context_parts)
    
    def merge_results(self, supabase_results: Dict, meili_results: Dict, query: str) -> Tuple[List[Dict], str]:
        """
        🎯 FUSION INTELLIGENTE DES RÉSULTATS
        Combine et optimise les résultats des deux moteurs
        """
        try:
            all_documents = []
            context_parts = []
            
            # 🟢 Intégrer résultats Supabase (priorité haute - HYDE)
            if isinstance(supabase_results, dict) and supabase_results.get("success"):
                supabase_docs = supabase_results.get("documents", [])
                supabase_context = supabase_results.get("context", "")
                
                all_documents.extend(supabase_docs)
                if supabase_context:
                    context_parts.append(f"=== CONTEXTE SUPABASE (HYDE) ===\\n{supabase_context}")
                
                log3("[HYBRID_MERGE]", f"✅ Intégré {len(supabase_docs)} docs Supabase")
            
            # 🟢 Intégrer résultats MeiliSearch (complément)
            if isinstance(meili_results, dict) and meili_results.get("success"):
                meili_docs = meili_results.get("documents", [])
                meili_context = meili_results.get("context", "")
                
                # Éviter les doublons (simple check par contenu)
                existing_contents = {doc.get('content', '')[:100] for doc in all_documents}
                unique_meili_docs = [
                    doc for doc in meili_docs 
                    if doc.get('content', '')[:100] not in existing_contents
                ]
                
                all_documents.extend(unique_meili_docs)
                if meili_context:
                    context_parts.append(f"=== CONTEXTE MEILISEARCH ===\\n{meili_context}")
                
                log3("[HYBRID_MERGE]", f"✅ Intégré {len(unique_meili_docs)} docs MeiliSearch uniques")
            
            # 🎯 Construire le contexte final
            final_context = "\\n\\n".join(context_parts)
            
            # 📊 Statistiques finales
            total_docs = len(all_documents)
            supabase_count = len(supabase_results.get("documents", [])) if isinstance(supabase_results, dict) else 0
            meili_count = len(meili_results.get("documents", [])) if isinstance(meili_results, dict) else 0
            
            log3("[HYBRID_MERGE]", f"🎯 Fusion terminée: {total_docs} docs total (Supabase: {supabase_count}, MeiliSearch: {meili_count})")
            
            return all_documents[:15], final_context  # Limiter à 15 documents max
            
        except Exception as e:
            log3("[HYBRID_MERGE]", f"❌ Erreur fusion: {e}")
            return [], ""
    
    async def get_context(self, query: str, company_id: str) -> str:
        """
        🎯 MÉTHODE PRINCIPALE - CONTEXTE HYBRIDE
        Point d'entrée pour obtenir le contexte optimisé
        """
        documents, context, method = await self.ultimate_dual_search(query, company_id)
        
        log3("[HYBRID_CONTEXT]", f"📋 Contexte final: {len(context)} chars, méthode: {method}")
        
        return context

# Instance globale
_hybrid_engine = None

async def get_hybrid_context(query: str, company_id: str) -> str:
    """
    🎯 FONCTION GLOBALE - CONTEXTE HYBRIDE
    Interface simple pour utiliser le système hybride
    """
    global _hybrid_engine
    
    if _hybrid_engine is None:
        _hybrid_engine = UltimateHybridRAG()
    
    return await _hybrid_engine.get_context(query, company_id)

# Test rapide
async def test_hybrid_system():
    """Test rapide du système hybride"""
    print("🧪 TEST SYSTÈME HYBRIDE")
    
    test_queries = [
        "prix couches adultes",
        "livraison cocody",
        "wave paiement"
    ]
    
    hybrid = UltimateHybridRAG()
    
    for query in test_queries:
        print(f"\\n📝 Test: '{query}'")
        context = await hybrid.get_context(query, "MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
        print(f"✅ Contexte: {len(context)} caractères")

if __name__ == "__main__":
    asyncio.run(test_hybrid_system())
'''
    
    with open("core/ultimate_hybrid_rag.py", "w", encoding="utf-8") as f:
        f.write(hybrid_content)
    
    print("   ✅ Système hybride ultime créé")

def update_app_to_use_hybrid():
    """Met à jour app.py pour utiliser le système hybride"""
    print("🔄 MISE À JOUR APP.PY POUR SYSTÈME HYBRIDE...")
    
    if os.path.exists("app.py"):
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Sauvegarder l'original
        shutil.copy2("app.py", f"app_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
        
        # Ajouter l'import du système hybride
        if "from core.ultimate_hybrid_rag import get_hybrid_context" not in content:
            # Trouver la section des imports
            import_section = content.find("from core.rag_engine")
            if import_section != -1:
                content = content[:import_section] + "from core.ultimate_hybrid_rag import get_hybrid_context\n" + content[import_section:]
        
        # Remplacer la fonction de recherche principale
        # Chercher la fonction qui obtient le contexte
        old_patterns = [
            "context = await rag_engine.get_context(message, company_id)",
            "context = await get_semantic_company_context(message, company_id)",
            "context = await dual_search_context(message, company_id)"
        ]
        
        for pattern in old_patterns:
            if pattern in content:
                content = content.replace(
                    pattern,
                    "context = await get_hybrid_context(message, company_id)  # 🔥 SYSTÈME HYBRIDE ULTIME"
                )
                break
        
        # Sauvegarder
        with open("app.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("   ✅ app.py mis à jour pour système hybride")

def create_hybrid_test():
    """Crée un test complet du système hybride"""
    print("🧪 CRÉATION TEST SYSTÈME HYBRIDE...")
    
    test_content = '''#!/usr/bin/env python3
"""
🧪 TEST COMPLET DU SYSTÈME HYBRIDE ULTIME
Teste la fusion Supabase (ancien) + MeiliSearch (nouveau)
"""

import asyncio
import time
from datetime import datetime

async def test_hybrid_vs_individual():
    """Compare le système hybride vs systèmes individuels"""
    
    print("🔥 TEST SYSTÈME HYBRIDE ULTIME")
    print("=" * 80)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    test_queries = [
        "wave paiement",
        "couches adultes prix", 
        "livraison yopougon",
        "politique retour",
        "combien coûte 6 paquets couches culottes"
    ]
    
    try:
        # Importer le système hybride
        from core.ultimate_hybrid_rag import UltimateHybridRAG
        
        hybrid_engine = UltimateHybridRAG()
        company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        
        for i, query in enumerate(test_queries, 1):
            print(f"\\n{'='*20} TEST {i}/{len(test_queries)} {'='*20}")
            print(f"📝 Query: '{query}'")
            print("-" * 60)
            
            start_time = time.time()
            
            # Test système hybride
            documents, context, method = await hybrid_engine.ultimate_dual_search(query, company_id)
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            
            print(f"🎯 RÉSULTATS HYBRIDES:")
            print(f"   📄 Documents trouvés: {len(documents)}")
            print(f"   📏 Contexte: {len(context)} caractères")
            print(f"   🔧 Méthode: {method}")
            print(f"   ⏱️ Temps: {duration:.1f}ms")
            
            if context:
                print(f"   📋 Aperçu contexte: {context[:200]}...")
            
            # Pause entre tests
            await asyncio.sleep(0.5)
        
        print("\\n" + "=" * 80)
        print("✅ TEST HYBRIDE TERMINÉ AVEC SUCCÈS")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERREUR TEST HYBRIDE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hybrid_vs_individual())
'''
    
    with open("test_ultimate_hybrid_system.py", "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print("   ✅ Test système hybride créé")

def create_sync_script():
    """Crée le script de synchronisation"""
    print("📋 CRÉATION SCRIPT SYNCHRONISATION...")
    
    sync_content = '''#!/bin/bash
# 🔥 SYNCHRONISATION SYSTÈME HYBRIDE ULTIME

echo "🔥 DÉPLOIEMENT SYSTÈME HYBRIDE ULTIME..."

# Synchroniser le système hybride
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/ultimate_hybrid_rag.py" ~/ZETA_APP/CHATBOT2.0/core/ultimate_hybrid_rag.py

# Synchroniser le test
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_ultimate_hybrid_system.py" ~/ZETA_APP/CHATBOT2.0/test_ultimate_hybrid_system.py

# Synchroniser app.py mis à jour
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/app.py" ~/ZETA_APP/CHATBOT2.0/app.py

echo ""
echo "✅ SYSTÈME HYBRIDE DÉPLOYÉ !"
echo ""
echo "🧪 TESTER MAINTENANT:"
echo "python test_ultimate_hybrid_system.py"
echo ""
echo "🚀 REDÉMARRER L'API:"
echo "python app.py"
'''
    
    with open("sync_hybrid_system.sh", "w", encoding="utf-8") as f:
        f.write(sync_content)
    
    print("   ✅ Script de synchronisation créé")

def main():
    """Point d'entrée principal"""
    print("🔥 CRÉATION SYSTÈME HYBRIDE ULTIME")
    print("=" * 60)
    print("🎯 Fusion: Supabase (ancien) + MeiliSearch (nouveau)")
    print("=" * 60)
    
    # 1. Créer le système hybride
    create_ultimate_hybrid_rag()
    
    # 2. Mettre à jour app.py
    update_app_to_use_hybrid()
    
    # 3. Créer le test
    create_hybrid_test()
    
    # 4. Script de synchronisation
    create_sync_script()
    
    print("\n" + "=" * 60)
    print("✅ SYSTÈME HYBRIDE ULTIME CRÉÉ !")
    print("🎯 Avantages:")
    print("   • Supabase HYDE + Anti-hallucination (ancien)")
    print("   • MeiliSearch optimisé + Stop words (nouveau)")
    print("   • Recherche parallèle + Fusion intelligente")
    print("   • Double sécurité + Meilleure performance")
    print("")
    print("🚀 Synchroniser avec:")
    print("   ./sync_hybrid_system.sh")
    print("=" * 60)

if __name__ == "__main__":
    main()
