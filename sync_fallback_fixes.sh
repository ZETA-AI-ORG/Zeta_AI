#!/bin/bash
# Script de synchronisation des corrections fallback LLM
# Exécuter depuis Windows WSL ou copier manuellement

echo "🔄 SYNCHRONISATION CORRECTIONS FALLBACK LLM"
echo "============================================"

# Répertoire source (Windows)
WIN_PATH="/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0"
# Répertoire destination (Ubuntu)
UBUNTU_PATH="~/ZETA_APP/CHATBOT2.0"

echo "📂 Source: $WIN_PATH"
echo "📂 Destination: $UBUNTU_PATH"
echo ""

# 1. Synchroniser le fichier LLM client corrigé
echo "🛠️ Synchronisation core/llm_client.py (FALLBACK CORRIGÉ)"
cp -v "$WIN_PATH/core/llm_client.py" "$UBUNTU_PATH/core/llm_client.py"

# 2. Synchroniser le test de validation fallback
echo "🧪 Synchronisation test_fallback_validation.py (NOUVEAU)"
cp -v "$WIN_PATH/test_fallback_validation.py" "$UBUNTU_PATH/test_fallback_validation.py"

# 3. Vérifier les permissions d'exécution
echo "🔐 Attribution des permissions d'exécution"
chmod +x "$UBUNTU_PATH/test_fallback_validation.py"

echo ""
echo "✅ SYNCHRONISATION TERMINÉE"
echo ""
echo "🚀 COMMANDES DE TEST:"
echo "cd ~/ZETA_APP/CHATBOT2.0"
echo "python test_fallback_validation.py"
echo ""
echo "📊 ALTERNATIVE - Test de charge optimisé:"
echo "python test_load_performance.py"
