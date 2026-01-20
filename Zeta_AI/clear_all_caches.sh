#!/bin/bash
################################################################################
# 🧹 SCRIPT NETTOYAGE COMPLET CACHES CHATBOT
# Vide TOUS les caches: Redis, Python, Embeddings, FAQ, Sessions, LLM
################################################################################

echo "🧹 NETTOYAGE COMPLET CACHES CHATBOT"
echo "===================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Compteurs
TOTAL_STEPS=8
CURRENT_STEP=0

# Fonction pour afficher progression
progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo -e "${BLUE}[$CURRENT_STEP/$TOTAL_STEPS]${NC} $1"
}

# Aller dans le répertoire du projet
cd ~/ZETA_APP/CHATBOT2.0 || {
    echo -e "${RED}❌ Erreur: Répertoire ~/ZETA_APP/CHATBOT2.0 introuvable${NC}"
    exit 1
}

echo -e "${YELLOW}📂 Répertoire: $(pwd)${NC}"
echo ""

# ========== 1. REDIS ==========
progress "🔴 Nettoyage Redis..."
if command -v redis-cli &> /dev/null; then
    redis-cli FLUSHALL > /dev/null 2>&1
    REDIS_SIZE=$(redis-cli DBSIZE 2>/dev/null | grep -o '[0-9]*')
    if [ "$REDIS_SIZE" = "0" ]; then
        echo -e "   ${GREEN}✅ Redis vidé (0 clés)${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Redis: $REDIS_SIZE clés restantes${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  Redis CLI non disponible${NC}"
fi
echo ""

# ========== 2. PYTHON CACHE ==========
progress "🐍 Nettoyage cache Python..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo -e "   ${GREEN}✅ $PYCACHE_COUNT dossiers __pycache__ supprimés${NC}"
echo ""

# ========== 3. EMBEDDINGS CACHE ==========
progress "💾 Nettoyage cache embeddings..."
EMBED_COUNT=0
if [ -d "data/embedding_cache" ]; then
    EMBED_COUNT=$(find data/embedding_cache -type f 2>/dev/null | wc -l)
    rm -rf data/embedding_cache/* 2>/dev/null
fi
if [ -d ".embedding_cache" ]; then
    EMBED_COUNT=$((EMBED_COUNT + $(find .embedding_cache -type f 2>/dev/null | wc -l)))
    rm -rf .embedding_cache/* 2>/dev/null
fi
echo -e "   ${GREEN}✅ $EMBED_COUNT fichiers embeddings supprimés${NC}"
echo ""

# ========== 4. FAQ CACHE ==========
progress "❓ Nettoyage cache FAQ..."
FAQ_COUNT=0
if [ -f "data/faq_cache.db" ]; then
    rm -f data/faq_cache.db
    FAQ_COUNT=$((FAQ_COUNT + 1))
fi
if [ -d "data/faq_cache" ]; then
    FAQ_COUNT=$((FAQ_COUNT + $(find data/faq_cache -type f 2>/dev/null | wc -l)))
    rm -rf data/faq_cache/* 2>/dev/null
fi
echo -e "   ${GREEN}✅ $FAQ_COUNT fichiers FAQ supprimés${NC}"
echo ""

# ========== 5. SESSIONS NOTEPAD ==========
progress "📋 Nettoyage sessions notepad..."
SESSION_COUNT=0
if [ -f "data/notepad_sessions.db" ]; then
    rm -f data/notepad_sessions.db
    SESSION_COUNT=$((SESSION_COUNT + 1))
fi
if [ -f "data/order_states.db" ]; then
    rm -f data/order_states.db
    SESSION_COUNT=$((SESSION_COUNT + 1))
fi
echo -e "   ${GREEN}✅ $SESSION_COUNT fichiers sessions supprimés${NC}"
echo ""

# ========== 6. LLM CACHE ==========
progress "🤖 Nettoyage cache LLM..."
LLM_COUNT=0
if [ -d "data/llm_cache" ]; then
    LLM_COUNT=$(find data/llm_cache -type f 2>/dev/null | wc -l)
    rm -rf data/llm_cache/* 2>/dev/null
fi
echo -e "   ${GREEN}✅ $LLM_COUNT fichiers LLM supprimés${NC}"
echo ""

# ========== 7. LOGS TEMPORAIRES ==========
progress "📝 Nettoyage logs temporaires..."
LOG_COUNT=0
if [ -d "logs/temp" ]; then
    LOG_COUNT=$(find logs/temp -type f 2>/dev/null | wc -l)
    rm -rf logs/temp/* 2>/dev/null
fi
# Supprimer logs > 7 jours
OLD_LOGS=$(find logs/ -name "*.log.*" -mtime +7 2>/dev/null | wc -l)
find logs/ -name "*.log.*" -mtime +7 -delete 2>/dev/null
LOG_COUNT=$((LOG_COUNT + OLD_LOGS))
echo -e "   ${GREEN}✅ $LOG_COUNT fichiers logs supprimés${NC}"
echo ""

# ========== 8. VÉRIFICATION ==========
progress "🔍 Vérification finale..."
echo ""

# Redis
REDIS_FINAL=$(redis-cli DBSIZE 2>/dev/null | grep -o '[0-9]*' || echo "N/A")
echo -e "   ${BLUE}Redis:${NC} $REDIS_FINAL clés"

# Python cache
PYCACHE_FINAL=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
echo -e "   ${BLUE}Python cache:${NC} $PYCACHE_FINAL dossiers"

# Embeddings
EMBED_FINAL=0
[ -d "data/embedding_cache" ] && EMBED_FINAL=$(find data/embedding_cache -type f 2>/dev/null | wc -l)
echo -e "   ${BLUE}Embeddings:${NC} $EMBED_FINAL fichiers"

# Sessions
SESSION_FINAL=0
[ -f "data/notepad_sessions.db" ] && SESSION_FINAL=$((SESSION_FINAL + 1))
[ -f "data/order_states.db" ] && SESSION_FINAL=$((SESSION_FINAL + 1))
echo -e "   ${BLUE}Sessions:${NC} $SESSION_FINAL fichiers"

echo ""
echo "===================================="
echo -e "${GREEN}✅ NETTOYAGE TERMINÉ${NC}"
echo "===================================="
echo ""
echo "📊 Résumé:"
echo "  - Redis: Vidé"
echo "  - Python cache: $PYCACHE_COUNT dossiers supprimés"
echo "  - Embeddings: $EMBED_COUNT fichiers supprimés"
echo "  - FAQ: $FAQ_COUNT fichiers supprimés"
echo "  - Sessions: $SESSION_COUNT fichiers supprimés"
echo "  - LLM: $LLM_COUNT fichiers supprimés"
echo "  - Logs: $LOG_COUNT fichiers supprimés"
echo ""
echo "🎯 Système prêt pour tests propres! (Serveur en cours avec reload)"
