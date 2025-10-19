"""
🔧 PATCH D'INTÉGRATION: SYSTÈME EXTRACTION CONTEXTE
Applique automatiquement les modifications nécessaires dans app.py
"""
import os
import re


def apply_context_extraction_patch():
    """Applique le patch d'extraction de contexte dans app.py"""
    
    app_file = "app.py"
    
    if not os.path.exists(app_file):
        print(f"❌ Fichier {app_file} introuvable!")
        return False
    
    print("=" * 80)
    print("🔧 APPLICATION DU PATCH EXTRACTION CONTEXTE")
    print("=" * 80)
    print()
    
    # Lire le fichier
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    modifications = []
    
    # ========== MODIFICATION 1: AJOUTER IMPORT ==========
    print("📦 Modification 1: Ajout import FIX_CONTEXT_LOSS_COMPLETE...")
    
    import_pattern = r'(from core\.models import ChatRequest)'
    import_addition = r'\1\nfrom FIX_CONTEXT_LOSS_COMPLETE import build_smart_context_summary, extract_from_last_exchanges'
    
    if 'from FIX_CONTEXT_LOSS_COMPLETE import' not in content:
        content = re.sub(import_pattern, import_addition, content)
        modifications.append("✅ Import ajouté")
        print("   ✅ Import ajouté après 'from core.models import ChatRequest'")
    else:
        print("   ⚠️ Import déjà présent, ignoré")
    
    # ========== MODIFICATION 2: CONSTRUIRE CONTEXTE INTELLIGENT ==========
    print("\n📦 Modification 2: Construction contexte intelligent...")
    
    # Chercher où injecter le contexte (avant l'appel RAG)
    # Pattern: juste avant "response = await safe_api_call"
    context_injection_pattern = r'(msg_for_rag = req\.message.*?\n\s+)(response = await safe_api_call)'
    
    context_code = r'''\1# ========== CONSTRUCTION CONTEXTE INTELLIGENT ==========
        print("🧠 [CONTEXT] Construction contexte intelligent...")
        try:
            context_summary = build_smart_context_summary(
                conversation_history=conversation_history,
                user_id=req.user_id,
                company_id=req.company_id
            )
            print(f"🧠 [CONTEXT] Résumé généré:\\n{context_summary}")
        except Exception as ctx_error:
            print(f"⚠️ [CONTEXT] Erreur construction contexte: {ctx_error}")
            context_summary = ""
        
        \2'''
    
    if 'build_smart_context_summary' not in content:
        content = re.sub(context_injection_pattern, context_code, content, flags=re.DOTALL)
        modifications.append("✅ Construction contexte ajoutée")
        print("   ✅ Construction contexte ajoutée avant appel RAG")
    else:
        print("   ⚠️ Construction contexte déjà présente, ignoré")
    
    # ========== MODIFICATION 3: EXTRACTION APRÈS RÉPONSE LLM ==========
    print("\n📦 Modification 3: Extraction et sauvegarde après réponse LLM...")
    
    # Pattern: après la sauvegarde de la réponse assistant
    extraction_pattern = r'(await save_message_supabase\(req\.company_id, req\.user_id, "assistant", \{"text": response_text\}\)\s+print\(f"🔍 \[CHAT_ENDPOINT\] Réponse assistant sauvegardée"\))'
    
    extraction_code = r'''\1
        
        # ========== EXTRACTION ET SAUVEGARDE CONTEXTE ==========
        print("🧠 [CONTEXT] Extraction contexte depuis historique...")
        try:
            # Construire historique complet avec nouveau message
            full_history = conversation_history + f"\\nClient: {req.message}\\nVous: {response_text}"
            
            # Extraire infos
            extracted = extract_from_last_exchanges(full_history)
            
            if extracted:
                print(f"✅ [CONTEXT] Infos extraites: {extracted}")
                
                # Sauvegarder dans notepad
                try:
                    from core.conversation_notepad import ConversationNotepad
                    notepad = ConversationNotepad.get_instance()
                    
                    for key, value in extracted.items():
                        if key == 'produit':
                            notepad.add_product(value, req.user_id, req.company_id)
                        elif key in ['zone', 'frais_livraison', 'telephone', 'paiement', 'acompte', 'prix_produit', 'total']:
                            notepad.add_info(key, value, req.user_id, req.company_id)
                    
                    print(f"✅ [CONTEXT] Contexte sauvegardé dans notepad")
                except Exception as notepad_error:
                    print(f"⚠️ [CONTEXT] Erreur sauvegarde notepad: {notepad_error}")
            else:
                print("⚠️ [CONTEXT] Aucune info extraite")
        
        except Exception as extract_error:
            print(f"⚠️ [CONTEXT] Erreur extraction: {extract_error}")'''
    
    if 'extract_from_last_exchanges' not in content:
        content = re.sub(extraction_pattern, extraction_code, content)
        modifications.append("✅ Extraction contexte ajoutée")
        print("   ✅ Extraction contexte ajoutée après sauvegarde réponse")
    else:
        print("   ⚠️ Extraction contexte déjà présente, ignoré")
    
    # ========== VÉRIFIER SI DES MODIFICATIONS ONT ÉTÉ FAITES ==========
    if content == original_content:
        print("\n" + "=" * 80)
        print("⚠️ AUCUNE MODIFICATION NÉCESSAIRE")
        print("Le patch semble déjà appliqué ou le fichier a une structure différente")
        print("=" * 80)
        return False
    
    # ========== SAUVEGARDER BACKUP ==========
    backup_file = "app.py.backup_context"
    print(f"\n💾 Sauvegarde backup: {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"   ✅ Backup créé: {backup_file}")
    
    # ========== ÉCRIRE FICHIER MODIFIÉ ==========
    print(f"\n✍️ Écriture fichier modifié: {app_file}...")
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   ✅ Fichier modifié écrit")
    
    # ========== RÉSUMÉ ==========
    print("\n" + "=" * 80)
    print("✅ PATCH APPLIQUÉ AVEC SUCCÈS!")
    print("=" * 80)
    print("\n📋 MODIFICATIONS APPLIQUÉES:")
    for i, mod in enumerate(modifications, 1):
        print(f"   {i}. {mod}")
    
    print("\n🚀 PROCHAINES ÉTAPES:")
    print("   1. Redémarrer le serveur: python app.py")
    print("   2. Tester avec curl ou l'interface")
    print("   3. Vérifier les logs: grep 'CONTEXT' logs/app.log")
    print()
    print("📝 NOTE: Un backup a été créé: app.py.backup_context")
    print("   Pour restaurer: mv app.py.backup_context app.py")
    print()
    
    return True


def verify_patch():
    """Vérifie que le patch a été correctement appliqué"""
    
    print("=" * 80)
    print("🔍 VÉRIFICATION DU PATCH")
    print("=" * 80)
    print()
    
    app_file = "app.py"
    
    if not os.path.exists(app_file):
        print(f"❌ Fichier {app_file} introuvable!")
        return False
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("Import FIX_CONTEXT_LOSS_COMPLETE", "from FIX_CONTEXT_LOSS_COMPLETE import"),
        ("Fonction build_smart_context_summary", "build_smart_context_summary"),
        ("Fonction extract_from_last_exchanges", "extract_from_last_exchanges"),
        ("Construction contexte intelligent", "Construction contexte intelligent"),
        ("Extraction et sauvegarde contexte", "EXTRACTION ET SAUVEGARDE CONTEXTE"),
    ]
    
    all_ok = True
    
    for check_name, check_pattern in checks:
        if check_pattern in content:
            print(f"   ✅ {check_name}")
        else:
            print(f"   ❌ {check_name} - MANQUANT!")
            all_ok = False
    
    print()
    
    if all_ok:
        print("=" * 80)
        print("✅ PATCH CORRECTEMENT APPLIQUÉ!")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ PATCH INCOMPLET - Vérifier les erreurs ci-dessus")
        print("=" * 80)
    
    return all_ok


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        # Mode vérification
        verify_patch()
    else:
        # Mode application
        success = apply_context_extraction_patch()
        
        if success:
            print("\n🔍 Vérification automatique...")
            verify_patch()
        else:
            print("\n⚠️ Patch non appliqué - Vérifier manuellement")
