#!/bin/bash
# 🔄 SCRIPT RESTAURATION BOTLIVE - EN CAS DE PROBLÈME

echo "🔄 RESTAURATION BOTLIVE"
echo "======================="
echo ""

# Lister les backups disponibles
echo "📁 Backups disponibles:"
ls -dt backups/botlive_* 2>/dev/null | head -5

echo ""
echo "Quel backup voulez-vous restaurer ?"
echo "Format: botlive_YYYYMMDD_HHMMSS"
read -p "Nom du backup (ou 'latest' pour le plus récent): " BACKUP_NAME

# Si "latest", prendre le plus récent
if [ "$BACKUP_NAME" = "latest" ]; then
    BACKUP_DIR=$(ls -dt backups/botlive_* 2>/dev/null | head -1)
else
    BACKUP_DIR="backups/$BACKUP_NAME"
fi

# Vérifier que le backup existe
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup non trouvé: $BACKUP_DIR"
    exit 1
fi

echo ""
echo "📦 Restauration depuis: $BACKUP_DIR"
echo ""
read -p "⚠️ Confirmer la restauration ? (oui/non): " CONFIRM

if [ "$CONFIRM" != "oui" ]; then
    echo "❌ Restauration annulée"
    exit 0
fi

# Restaurer les fichiers
echo ""
echo "🔄 Restauration en cours..."

cp -v "$BACKUP_DIR/botlive_rag_hybrid.py" core/
cp -v "$BACKUP_DIR/order_state_tracker.py" core/
cp -v "$BACKUP_DIR/botlive_prompt.txt" prompts/
cp -v "$BACKUP_DIR/order_states.db" ./ 2>/dev/null || echo "⚠️ order_states.db non restauré"
cp -v "$BACKUP_DIR/app.py" ./
cp -v "$BACKUP_DIR/test_auto_detect_validation.py" ./
cp -v "$BACKUP_DIR/test_ordre_melange.py" ./
cp -v "$BACKUP_DIR/check_state.py" ./
cp -v "$BACKUP_DIR/AUTO_DETECT_SPEC.md" ./

echo ""
echo "✅ RESTAURATION TERMINÉE !"
echo ""
echo "🧪 Vérification recommandée:"
echo "  python3 test_auto_detect_validation.py"
echo ""
cat "$BACKUP_DIR/BACKUP_INFO.txt"
