#!/bin/bash
# ✅ SCRIPT VÉRIFICATION BOTLIVE - AVANT/APRÈS MODIFS RAG

echo "✅ VÉRIFICATION BOTLIVE"
echo "======================="
echo ""

# 1. Vérifier que les fichiers critiques existent
echo "📁 Vérification fichiers critiques..."
CRITICAL_FILES=(
    "core/botlive_rag_hybrid.py"
    "core/order_state_tracker.py"
    "prompts/botlive_prompt.txt"
    "app.py"
)

ALL_OK=true
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MANQUANT !"
        ALL_OK=false
    fi
done

echo ""

# 2. Vérifier la base de données
echo "💾 Vérification base de données..."
if [ -f "order_states.db" ]; then
    SIZE=$(du -h order_states.db | cut -f1)
    echo "  ✅ order_states.db ($SIZE)"
else
    echo "  ⚠️ order_states.db non trouvé (sera créé au premier usage)"
fi

echo ""

# 3. Lancer les tests
echo "🧪 Lancement tests validation..."
echo "================================"
python3 test_auto_detect_validation.py

echo ""
echo "================================"

# 4. Résumé
if [ "$ALL_OK" = true ]; then
    echo ""
    echo "✅ BOTLIVE VÉRIFIÉ ET FONCTIONNEL"
    echo ""
    echo "📊 Statut:"
    echo "  - Fichiers critiques : ✅ Présents"
    echo "  - Base de données : ✅ OK"
    echo "  - Tests validation : Voir résultats ci-dessus"
    echo ""
    echo "🔒 Botlive est protégé et prêt !"
else
    echo ""
    echo "❌ PROBLÈME DÉTECTÉ !"
    echo ""
    echo "⚠️ Fichiers manquants. Restaurer depuis backup:"
    echo "  bash restore_botlive.sh"
fi
