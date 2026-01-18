#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script pour corriger la syntaxe du fichier setfit_intent_router.py"""

file_path = r"c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0\core\setfit_intent_router.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Ligne 1520 (index 1519): ajouter ) à la fin
if '→ mode={mode}' in lines[1519] and not lines[1519].rstrip().endswith(')'):
    lines[1519] = lines[1519].rstrip().rstrip(')') + ')\n'

# Ligne 1522 (index 1521): corriger l'indentation (doit être 4 espaces, pas 8)
if 'if not (state_compact or {}).get("zone_collected"' in lines[1521]:
    lines[1521] = '    if not (state_compact or {}).get("zone_collected", False):\n'

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Syntaxe corrigée avec succès")
