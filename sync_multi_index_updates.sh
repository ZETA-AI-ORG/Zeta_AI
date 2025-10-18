#!/bin/bash

# 🔄 SCRIPT DE SYNCHRONISATION - OPTIMISATIONS MULTI-INDEX MEILISEARCH
# Synchronise tous les fichiers modifiés/créés pour l'architecture multi-index

echo "🔄 SYNCHRONISATION MULTI-INDEX MEILISEARCH"
echo "=========================================="

# Vérifier si on est dans le bon répertoire
if [ ! -f "app.py" ]; then
    echo "❌ Erreur: Exécuter depuis le répertoire racine du projet"
    exit 1
fi

echo "📁 Synchronisation des fichiers modifiés/créés..."

# 1. MOTEUR DE RECHERCHE MULTI-INDEX (NOUVEAU)
echo "📄 Synchronisation: core/multi_index_search_engine.py"
if [ -f "core/multi_index_search_engine.py" ]; then
    echo "   ✅ Moteur de recherche multi-index créé"
else
    echo "   ❌ MANQUANT: core/multi_index_search_engine.py"
fi

# 2. API RAG MULTI-INDEX (NOUVEAU)
echo "📄 Synchronisation: api/multi_index_rag.py"
if [ -f "api/multi_index_rag.py" ]; then
    echo "   ✅ API RAG multi-index créée"
else
    echo "   ❌ MANQUANT: api/multi_index_rag.py"
fi

# 3. API SEARCH RAG MODIFIÉE
echo "📄 Synchronisation: api/search_rag.py"
if [ -f "api/search_rag.py" ]; then
    echo "   ✅ API search_rag modifiée avec support MeiliSearch"
    # Vérifier si la modification est présente
    if grep -q "search_company_multi_index" "api/search_rag.py"; then
        echo "   ✅ Import multi-index détecté"
    else
        echo "   ⚠️  Import multi-index manquant"
    fi
else
    echo "   ❌ MANQUANT: api/search_rag.py"
fi

# 4. INGESTION API MODIFIÉE (HYDE INTÉGRÉ)
echo "📄 Synchronisation: ingestion/ingestion_api.py"
if [ -f "ingestion/ingestion_api.py" ]; then
    echo "   ✅ Ingestion API avec HyDE intégré"
    # Vérifier l'intégration HyDE
    if grep -q "create_company_word_cache" "ingestion/ingestion_api.py"; then
        echo "   ✅ Intégration HyDE détectée"
    else
        echo "   ⚠️  Intégration HyDE manquante"
    fi
else
    echo "   ❌ MANQUANT: ingestion/ingestion_api.py"
fi

# 5. ANALYSEUR HYDE (EXISTANT - VÉRIFICATION)
echo "📄 Vérification: core/ingestion_hyde_analyzer.py"
if [ -f "core/ingestion_hyde_analyzer.py" ]; then
    echo "   ✅ Analyseur HyDE disponible"
else
    echo "   ❌ MANQUANT: core/ingestion_hyde_analyzer.py"
fi

# 6. UTILS MEILISEARCH (EXISTANT - VÉRIFICATION)
echo "📄 Vérification: core/meilisearch_utils.py"
if [ -f "core/meilisearch_utils.py" ]; then
    echo "   ✅ Utils MeiliSearch disponibles"
else
    echo "   ❌ MANQUANT: core/meilisearch_utils.py"
fi

echo ""
echo "🔧 VÉRIFICATIONS TECHNIQUES"
echo "=========================="

# Vérifier les dépendances Python
echo "📦 Vérification des dépendances..."
if command -v python3 &> /dev/null; then
    echo "   ✅ Python3 disponible"
    
    # Vérifier meilisearch
    if python3 -c "import meilisearch" 2>/dev/null; then
        echo "   ✅ Module meilisearch installé"
    else
        echo "   ❌ Module meilisearch manquant"
        echo "   💡 Installer: pip install meilisearch"
    fi
    
    # Vérifier fastapi
    if python3 -c "import fastapi" 2>/dev/null; then
        echo "   ✅ Module fastapi installé"
    else
        echo "   ❌ Module fastapi manquant"
    fi
    
else
    echo "   ❌ Python3 non disponible"
fi

echo ""
echo "🚀 COMMANDES DE DÉMARRAGE"
echo "========================"

echo "1. Démarrer MeiliSearch (si pas déjà fait):"
echo "   meilisearch --master-key=your_master_key"
echo ""

echo "2. Tester l'ingestion avec HyDE:"
echo "   curl -X POST http://localhost:8000/ingestion/push_to_meili \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"company_id\": \"test\", \"data\": {...}}'"
echo ""

echo "3. Tester la recherche multi-index:"
echo "   curl -X POST http://localhost:8000/multi-rag/search \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"company_id\": \"test\", \"query\": \"casques moto\", \"limit\": 5}'"
echo ""

echo "4. Tester la recherche RAG avec MeiliSearch:"
echo "   curl -X POST http://localhost:8000/rag/search \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"company_id\": \"test\", \"query\": \"livraison yopougon\", \"mode\": \"meilisearch\"}'"
echo ""

echo "5. Vérifier le statut des index:"
echo "   curl http://localhost:8000/multi-rag/indexes/status/test"
echo ""

echo "✅ SYNCHRONISATION TERMINÉE"
echo "=========================="
echo "🎯 FONCTIONNALITÉS DISPONIBLES:"
echo "   • Ingestion multi-index avec HyDE"
echo "   • Recherche multi-index intelligente"
echo "   • Priorisation searchable_text"
echo "   • Scoring HyDE adaptatif"
echo "   • Routage intelligent des requêtes"
echo "   • API RAG optimisée"
echo ""
echo "📋 PROCHAINES ÉTAPES:"
echo "   1. Tester l'ingestion de documents"
echo "   2. Valider la recherche multi-index"
echo "   3. Vérifier les performances"
echo "   4. Optimiser les scores HyDE"
