#!/bin/bash
# 🔍 SYNCHRONISATION VÉRIFICATEUR MEILISEARCH

echo "🔍 Synchronisation du vérificateur MeiliSearch..."

# Synchronisation du script de vérification
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/verify_meili_config.py" ~/ZETA_APP/CHATBOT2.0/verify_meili_config.py

echo "✅ Synchronisation terminée !"
echo ""
echo "🧪 COMMANDES DE VÉRIFICATION :"
echo ""
echo "# 1. Vérification complète MeiliSearch :"
echo "python verify_meili_config.py"
echo ""
echo "# 2. Démarrer MeiliSearch si nécessaire :"
echo "sudo systemctl start meilisearch"
echo "sudo systemctl status meilisearch"
echo ""
echo "# 3. Vérifier les logs MeiliSearch :"
echo "sudo journalctl -u meilisearch -f"
