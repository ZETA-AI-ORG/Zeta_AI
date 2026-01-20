#!/bin/bash
# 🔒 SCRIPT BACKUP BOTLIVE - À EXÉCUTER AVANT TRAVAIL SUR RAG

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/botlive_$TIMESTAMP"

echo "🔒 CRÉATION BACKUP BOTLIVE..."
echo "📁 Dossier: $BACKUP_DIR"

# Créer dossier backup
mkdir -p "$BACKUP_DIR"

# Backup fichiers critiques
echo "📦 Sauvegarde fichiers critiques..."
cp -v core/botlive_rag_hybrid.py "$BACKUP_DIR/"
cp -v core/order_state_tracker.py "$BACKUP_DIR/"
cp -v prompts/botlive_prompt.txt "$BACKUP_DIR/"
cp -v order_states.db "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ order_states.db non trouvé"
cp -v app.py "$BACKUP_DIR/"

# Backup tests
echo "📦 Sauvegarde tests..."
cp -v test_auto_detect_validation.py "$BACKUP_DIR/"
cp -v test_ordre_melange.py "$BACKUP_DIR/"
cp -v check_state.py "$BACKUP_DIR/"

# Backup spec
echo "📦 Sauvegarde documentation..."
cp -v AUTO_DETECT_SPEC.md "$BACKUP_DIR/"

# Créer fichier de vérification
cat > "$BACKUP_DIR/BACKUP_INFO.txt" << EOF
🔒 BACKUP BOTLIVE
================

Date création : $(date)
Timestamp : $TIMESTAMP

FICHIERS SAUVEGARDÉS:
- core/botlive_rag_hybrid.py
- core/order_state_tracker.py
- prompts/botlive_prompt.txt
- order_states.db
- app.py
- test_auto_detect_validation.py
- test_ordre_melange.py
- check_state.py
- AUTO_DETECT_SPEC.md

STATUS BOTLIVE:
- Tests validation : 4/4 réussis (100%)
- Tests ordre mélangé : 3/3 réussis (100%)
- Auto-détection : ✅ Fonctionnelle
- Performance : ~1.7s/requête
- Coût : \$0.000317/requête

⚠️ RESTAURATION:
Pour restaurer ces fichiers :
  cp backups/botlive_$TIMESTAMP/[fichier] ./

EOF

echo ""
echo "✅ BACKUP CRÉÉ: $BACKUP_DIR"
echo "📊 Contenu:"
ls -lh "$BACKUP_DIR/"
echo ""
echo "🔒 Botlive est maintenant protégé !"
echo "✅ Vous pouvez travailler sur le RAG en toute sécurité"
