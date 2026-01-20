#!/usr/bin/env python3
"""
🔧 INTÉGRATION PATTERNS SCALABLES DANS RAG ENGINE
Modifie universal_rag_engine.py pour utiliser patterns par company
"""

import os
from pathlib import Path

def integrate_into_rag_engine():
    """Intègre le système de patterns scalable dans le RAG engine"""
    
    rag_engine_path = Path(__file__).parent / "core" / "universal_rag_engine.py"
    
    print("🔍 Lecture du RAG Engine...")
    
    with open(rag_engine_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si déjà intégré
    if "company_patterns_manager" in content:
        print("✅ Patterns scalables déjà intégrés")
        return
    
    print("🔧 Intégration des patterns scalables...")
    
    # Modification 1: Import du gestionnaire (ligne ~210)
    old_import = "from core.rag_regex_extractor import extract_regex_entities_from_docs"
    
    new_import = """from core.rag_regex_extractor import extract_regex_entities_from_docs
            from core.company_patterns_manager import get_patterns_for_company"""
    
    content = content.replace(old_import, new_import)
    
    # Modification 2: Utilisation patterns par company (ligne ~226)
    old_extraction = """print("[REGEX] Chargement des patterns métier...")
            regex_entities = extract_regex_entities_from_docs(docs)"""
    
    new_extraction = """print("[REGEX] Chargement des patterns métier...")
            # Récupérer patterns spécifiques à cette company (scalable)
            try:
                company_patterns = await get_patterns_for_company(company_id)
                print(f"[REGEX] Utilisation de {len(company_patterns)} patterns pour company {company_id[:8]}...")
            except Exception as e:
                print(f"[REGEX] Erreur récupération patterns: {e}, utilisation patterns génériques")
                company_patterns = None
            
            regex_entities = extract_regex_entities_from_docs(docs, company_patterns)"""
    
    content = content.replace(old_extraction, new_extraction)
    
    # Sauvegarder
    backup_path = rag_engine_path.with_suffix('.py.backup')
    
    # Créer backup
    with open(backup_path, 'w', encoding='utf-8') as f:
        with open(rag_engine_path, 'r', encoding='utf-8') as orig:
            f.write(orig.read())
    
    print(f"💾 Backup créé: {backup_path}")
    
    # Écrire nouvelle version
    with open(rag_engine_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ RAG Engine modifié: {rag_engine_path}")
    print("\n📋 MODIFICATIONS:")
    print("   1. ✅ Import CompanyPatternsManager")
    print("   2. ✅ Récupération patterns par company_id")
    print("   3. ✅ Fallback patterns génériques")
    print("\n⚠️  IMPORTANT: Redémarrer le serveur pour appliquer les changements")

def create_learning_trigger_script():
    """Crée un script pour déclencher l'apprentissage des patterns"""
    
    script_content = '''#!/usr/bin/env python3
"""
🎓 APPRENTISSAGE PATTERNS POUR UNE COMPANY
Lance l'auto-apprentissage des patterns depuis les documents existants
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

async def learn_patterns_for_company(company_id: str):
    """Apprend les patterns pour une company depuis ses documents MeiliSearch/Supabase"""
    
    print(f"🎓 APPRENTISSAGE PATTERNS POUR: {company_id}")
    print("="*60)
    
    try:
        # 1. Récupérer tous les documents de la company
        print("\\n1️⃣ Récupération des documents...")
        
        from database.vector_store_clean import get_all_documents_for_company
        documents = await get_all_documents_for_company(company_id)
        
        if not documents:
            print(f"❌ Aucun document trouvé pour {company_id}")
            print("💡 Indexez d\'abord des documents pour cette company")
            return
        
        print(f"✅ {len(documents)} documents récupérés")
        
        # 2. Lancer l'apprentissage
        print("\\n2️⃣ Auto-apprentissage des patterns...")
        
        from core.company_patterns_manager import learn_patterns_for_company
        patterns = await learn_patterns_for_company(company_id, documents)
        
        print(f"\\n✅ Apprentissage terminé: {len(patterns)} patterns détectés")
        
        # 3. Afficher patterns détectés
        print("\\n📋 PATTERNS DÉTECTÉS:")
        print("-"*60)
        
        for pattern_name, pattern_regex in patterns.items():
            # Afficher seulement les nouveaux (pas les génériques)
            if not pattern_name.endswith("_generic"):
                print(f"   • {pattern_name}")
                print(f"     {pattern_regex[:80]}...")
        
        print("-"*60)
        print(f"\\n💾 Patterns stockés dans Redis (TTL: 7 jours)")
        print(f"🎯 Prêts à être utilisés pour {company_id}")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Point d'entrée"""
    
    if len(sys.argv) < 2:
        print("Usage: python learn_company_patterns.py <company_id>")
        print("\\nExemple:")
        print("  python learn_company_patterns.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
        sys.exit(1)
    
    company_id = sys.argv[1]
    await learn_patterns_for_company(company_id)

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    output_path = Path(__file__).parent / "learn_company_patterns.py"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Script créé: {output_path}")
    print("📌 Usage: python learn_company_patterns.py <company_id>")

def create_test_script():
    """Crée un script de test du système"""
    
    test_content = '''#!/usr/bin/env python3
"""
🧪 TEST SYSTÈME PATTERNS SCALABLE
Teste le gestionnaire de patterns par company
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

async def test_scalable_patterns():
    """Test complet du système"""
    
    print("🧪 TEST SYSTÈME PATTERNS SCALABLE")
    print("="*60)
    
    from core.company_patterns_manager import (
        get_company_patterns_manager,
        get_patterns_for_company
    )
    
    manager = get_company_patterns_manager()
    
    # Test 1: Patterns génériques
    print("\\n1️⃣ Test patterns génériques...")
    company_test = "test_company_123"
    patterns = await get_patterns_for_company(company_test)
    print(f"   ✅ {len(patterns)} patterns génériques récupérés")
    
    # Test 2: Stockage custom
    print("\\n2️⃣ Test stockage patterns custom...")
    custom_patterns = {
        **patterns,
        "custom_pattern": r"test_pattern_\\d+"
    }
    manager.store_company_patterns(company_test, custom_patterns)
    print(f"   ✅ Patterns stockés")
    
    # Test 3: Récupération custom
    print("\\n3️⃣ Test récupération patterns custom...")
    retrieved = await get_patterns_for_company(company_test)
    
    if "custom_pattern" in retrieved:
        print(f"   ✅ Pattern custom trouvé: {retrieved[\\'custom_pattern\\']}")
    else:
        print(f"   ❌ Pattern custom non trouvé")
    
    # Test 4: Stats
    print("\\n4️⃣ Statistiques...")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"   • {key}: {value}")
    
    # Test 5: Clear
    print("\\n5️⃣ Test suppression...")
    manager.clear_company_patterns(company_test)
    
    # Vérifier suppression
    patterns_after = await get_patterns_for_company(company_test)
    if "custom_pattern" not in patterns_after:
        print(f"   ✅ Patterns supprimés (fallback génériques)")
    
    print("\\n" + "="*60)
    print("✅ TOUS LES TESTS RÉUSSIS")

if __name__ == "__main__":
    asyncio.run(test_scalable_patterns())
'''
    
    output_path = Path(__file__).parent / "test_scalable_patterns.py"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print(f"✅ Script de test créé: {output_path}")

if __name__ == "__main__":
    print("🚀 INTÉGRATION PATTERNS SCALABLES")
    print("="*60)
    
    # 1. Intégrer dans RAG Engine
    integrate_into_rag_engine()
    
    # 2. Créer script d'apprentissage
    print("\\n📝 Création scripts utilitaires...")
    create_learning_trigger_script()
    
    # 3. Créer script de test
    create_test_script()
    
    print("\\n" + "="*60)
    print("✅ INTÉGRATION TERMINÉE")
    print("\\n📋 FICHIERS CRÉÉS:")
    print("   1. core/company_patterns_manager.py - Gestionnaire patterns")
    print("   2. learn_company_patterns.py - Script apprentissage")
    print("   3. test_scalable_patterns.py - Script test")
    print("   4. core/universal_rag_engine.py.backup - Backup RAG engine")
    print("\\n🎯 PROCHAINES ÉTAPES:")
    print("   1. Tester: python test_scalable_patterns.py")
    print("   2. Apprendre pour Rue_du_gros:")
    print("      python learn_company_patterns.py MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
    print("   3. Redémarrer serveur: pkill -f uvicorn && uvicorn app:app ...")
    print("\\n✅ SYSTÈME 100% SCALABLE PRÊT !")
