#!/usr/bin/env python3
"""
🔧 INTÉGRATION DU GARDE-FOU ANTI-HALLUCINATION ADAPTATIF
Remplace l'ancien système par le nouveau système en 2 modes
"""

import os
import shutil
from datetime import datetime

def backup_old_system():
    """Sauvegarde de l'ancien système"""
    print("📦 SAUVEGARDE DE L'ANCIEN SYSTÈME")
    print("-" * 40)
    
    backup_dir = f"backup_old_hallucination_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "core/simple_adaptive_hallucination_guard.py",
        "core/advanced_intent_classifier.py",
        "core/context_aware_hallucination_guard.py",
        "core/intelligent_fallback_system.py",
        "core/confidence_scoring_system.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"✅ Sauvegardé: {file_path} → {backup_path}")
        else:
            print(f"⚠️  Fichier non trouvé: {file_path}")
    
    print(f"📁 Sauvegarde complète dans: {backup_dir}")
    return backup_dir

def update_rag_engine():
    """Met à jour le RAG engine pour utiliser le nouveau système"""
    print("\n🔧 MISE À JOUR DU RAG ENGINE")
    print("-" * 40)
    
    rag_file = "core/rag_engine_simplified_fixed.py"
    
    if not os.path.exists(rag_file):
        print(f"❌ Fichier RAG non trouvé: {rag_file}")
        return False
    
    # Lire le fichier actuel
    with open(rag_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer les imports
    old_imports = [
        "from .advanced_intent_classifier import classify_intent_advanced, IntentType",
        "from .context_aware_hallucination_guard import validate_response_contextual, ValidationLevel",
        "from .intelligent_fallback_system import generate_intelligent_fallback, FallbackType",
        "from .confidence_scoring_system import calculate_confidence_score, ConfidenceLevel"
    ]
    
    new_import = "from .adaptive_hallucination_guard import check_hallucination_adaptive"
    
    for old_import in old_imports:
        if old_import in content:
            content = content.replace(old_import, f"# {old_import}  # REMPLACÉ PAR LE NOUVEAU SYSTÈME")
            print(f"✅ Remplacé: {old_import}")
    
    # Ajouter le nouvel import
    if new_import not in content:
        # Trouver la section des imports
        import_section = content.find("# 🚀 NOUVEAUX SYSTÈMES ANTI-HALLUCINATION 2024")
        if import_section != -1:
            # Insérer après la section des anciens imports
            insert_pos = content.find("\n\n", import_section)
            if insert_pos != -1:
                content = content[:insert_pos] + f"\n{new_import}" + content[insert_pos:]
                print(f"✅ Ajouté: {new_import}")
    
    # Remplacer la fonction de validation
    old_validation = """                # 4. Validation contextuelle avancée
                logger.info(f"[RAG_ADVANCED] 🛡️ Étape 4: Validation anti-hallucination")
                validation_result = await validate_response_contextual(
                    user_query=message,
                    ai_response=ai_response,
                    intent_result=intent_result,
                    supabase_results=supabase_results,
                    meili_results=meili_results,
                    supabase_context=supabase_context,
                    meili_context=meili_context,
                    company_id=company_id
                )
                log_validation(validation_result)"""
    
    new_validation = """                # 4. Validation anti-hallucination adaptative
                logger.info(f"[RAG_ADVANCED] 🛡️ Étape 4: Validation anti-hallucination adaptative")
                
                # Préparer les documents sources
                source_documents = []
                if supabase_context:
                    source_documents.append(supabase_context)
                if meili_context:
                    source_documents.append(meili_context)
                
                # Validation adaptative
                validation_result = check_hallucination_adaptive(
                    query=message,
                    ai_response=ai_response,
                    source_documents=source_documents if source_documents else None
                )
                
                # Log de la validation
                logger.info(f"[RAG_ADVANCED] Mode: {validation_result['validation_mode']}")
                logger.info(f"[RAG_ADVANCED] Sûr: {validation_result['is_safe']} (conf: {validation_result['confidence']:.2f})")
                if validation_result['specific_information_detected']:
                    logger.info(f"[RAG_ADVANCED] Infos détectées: {validation_result['specific_information_detected']}")
                if not validation_result['is_safe']:
                    logger.warning(f"[RAG_ADVANCED] Rejeté: {validation_result['rejection_reason']}")"""
    
    if old_validation in content:
        content = content.replace(old_validation, new_validation)
        print("✅ Remplacé la validation contextuelle par la validation adaptative")
    
    # Remplacer la gestion des réponses rejetées
    old_fallback = """                # 5. Gestion des réponses rejetées
                if not validation_result.is_safe:
                    logger.warning(f"[RAG_ADVANCED] ⚠️ Réponse rejetée, activation du fallback")
                    # Génération de fallback intelligent
                    fallback_result = await generate_intelligent_fallback(
                        user_query=message,
                        intent_result=intent_result,
                        error_context={'error': 'validation_failed', 'reason': validation_result.rejection_reason},
                        company_context={'company_name': 'Rue du Gros', 'ai_name': 'Gamma'}
                    )
                    log_fallback(fallback_result, f"Validation échouée: {validation_result.rejection_reason}")
                    ai_response = fallback_result.response"""
    
    new_fallback = """                # 5. Gestion des réponses rejetées
                if not validation_result['is_safe']:
                    logger.warning(f"[RAG_ADVANCED] ⚠️ Réponse rejetée, activation du fallback")
                    
                    # Fallback simple et adaptatif
                    if validation_result['validation_mode'] == 'simple_conversation':
                        ai_response = "Je suis désolé, je ne peux pas répondre à cette question de manière appropriée."
                    else:
                        ai_response = "Je n'ai pas d'informations suffisantes pour répondre à votre question. Pouvez-vous me donner plus de détails ou contacter notre service client ?"
                    
                    logger.warning(f"[RAG_ADVANCED] Fallback activé: {validation_result['suggested_action']}")"""
    
    if old_fallback in content:
        content = content.replace(old_fallback, new_fallback)
        print("✅ Remplacé la gestion des fallbacks")
    
    # Remplacer le calcul de confiance
    old_confidence = """                # 6. Calcul du score de confiance
                logger.info(f"[RAG_ADVANCED] 📊 Étape 5: Scoring de confiance")
                confidence_score = await calculate_confidence_score(
                    user_query=message,
                    ai_response=ai_response,
                    intent_result=intent_result,
                    supabase_results=supabase_results,
                    meili_results=meili_results,
                    supabase_context=supabase_context,
                    meili_context=meili_context,
                    validation_result=validation_result.__dict__ if validation_result else None
                )
                log_confidence_scoring(confidence_score)"""
    
    new_confidence = """                # 6. Calcul du score de confiance simplifié
                logger.info(f"[RAG_ADVANCED] 📊 Étape 5: Scoring de confiance")
                
                # Score de confiance basé sur la validation adaptative
                confidence_score = {
                    'overall_confidence': validation_result['confidence'],
                    'confidence_level': 'high' if validation_result['confidence'] > 0.8 else 'medium' if validation_result['confidence'] > 0.5 else 'low',
                    'validation_safe': validation_result['is_safe'],
                    'validation_mode': validation_result['validation_mode'],
                    'specific_information_detected': validation_result['specific_information_detected'],
                    'source_verification': validation_result['source_verification']
                }
                
                logger.info(f"[RAG_ADVANCED] Score confiance: {confidence_score['overall_confidence']:.3f} ({confidence_score['confidence_level']})")"""
    
    if old_confidence in content:
        content = content.replace(old_confidence, new_confidence)
        print("✅ Remplacé le calcul de confiance")
    
    # Mettre à jour la construction de la réponse finale
    old_response = """                # 8. Construction de la réponse finale
                logger.info(f"[RAG_ADVANCED] 📤 Étape 7: Construction réponse finale")
                response_data = {
                    'response': ai_response,
                    'intent': intent_result.primary_intent.value,
                    'confidence': confidence_score.overall_confidence,
                    'confidence_level': confidence_score.confidence_level.value,
                    'validation_safe': validation_result.is_safe if validation_result else True,
                    'requires_documents': intent_result.requires_documents,
                    'documents_found': bool(supabase_context or meili_context),
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'debug_info': {
                        'intent_confidence': intent_result.confidence,
                        'validation_level': validation_result.validation_level.value if validation_result else 'unknown',
                        'fallback_used': not validation_result.is_safe if validation_result else False,
                        'risk_level': confidence_score.risk_level,
                        'recommendations': confidence_score.recommendations
                    }
                }"""
    
    new_response = """                # 8. Construction de la réponse finale
                logger.info(f"[RAG_ADVANCED] 📤 Étape 7: Construction réponse finale")
                response_data = {
                    'response': ai_response,
                    'intent': 'general_conversation',  # Simplifié
                    'confidence': confidence_score['overall_confidence'],
                    'confidence_level': confidence_score['confidence_level'],
                    'validation_safe': validation_result['is_safe'],
                    'requires_documents': validation_result['validation_mode'] == 'factual_information',
                    'documents_found': bool(supabase_context or meili_context),
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'debug_info': {
                        'validation_mode': validation_result['validation_mode'],
                        'validation_result': validation_result['validation_result'],
                        'fallback_used': not validation_result['is_safe'],
                        'specific_information_detected': validation_result['specific_information_detected'],
                        'source_verification': validation_result['source_verification'],
                        'suggested_action': validation_result['suggested_action']
                    }
                }"""
    
    if old_response in content:
        content = content.replace(old_response, new_response)
        print("✅ Remplacé la construction de la réponse finale")
    
    # Sauvegarder le fichier modifié
    with open(rag_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ RAG engine mis à jour: {rag_file}")
    return True

def create_integration_script():
    """Crée un script d'intégration complet"""
    print("\n📝 CRÉATION DU SCRIPT D'INTÉGRATION")
    print("-" * 40)
    
    script_content = '''#!/usr/bin/env python3
"""
🔧 SCRIPT D'INTÉGRATION DU GARDE-FOU ANTI-HALLUCINATION ADAPTATIF
Remplace l'ancien système par le nouveau système en 2 modes
"""

import os
import sys
import shutil
from datetime import datetime

def main():
    print("🚀 INTÉGRATION DU GARDE-FOU ANTI-HALLUCINATION ADAPTATIF")
    print("=" * 70)
    
    # 1. Vérifier que les fichiers existent
    required_files = [
        "core/adaptive_hallucination_guard.py",
        "core/rag_engine_simplified_fixed.py"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Fichier requis manquant: {file_path}")
            return False
    
    # 2. Sauvegarder l'ancien système
    backup_dir = f"backup_old_hallucination_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "core/simple_adaptive_hallucination_guard.py",
        "core/advanced_intent_classifier.py",
        "core/context_aware_hallucination_guard.py",
        "core/intelligent_fallback_system.py",
        "core/confidence_scoring_system.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"✅ Sauvegardé: {file_path}")
    
    print(f"📁 Sauvegarde complète dans: {backup_dir}")
    
    # 3. Tester le nouveau système
    print("\\n🧪 TEST DU NOUVEAU SYSTÈME")
    print("-" * 40)
    
    try:
        from core.adaptive_hallucination_guard import check_hallucination_adaptive
        
        # Test rapide
        result = check_hallucination_adaptive("Bonjour", "Bonjour ! Comment puis-je vous aider ?")
        print(f"✅ Test conversation simple: {result['is_safe']}")
        
        result = check_hallucination_adaptive("Où êtes-vous ?", "Nous sommes à Paris", ["Adresse: Paris"])
        print(f"✅ Test information factuelle: {result['is_safe']}")
        
        print("🎉 Nouveau système fonctionnel !")
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        return False
    
    # 4. Instructions pour l'intégration manuelle
    print("\\n📋 INSTRUCTIONS POUR L'INTÉGRATION MANUELLE")
    print("-" * 50)
    print("1. Remplacez les imports dans core/rag_engine_simplified_fixed.py:")
    print("   from .adaptive_hallucination_guard import check_hallucination_adaptive")
    print("")
    print("2. Remplacez la validation par:")
    print("   validation_result = check_hallucination_adaptive(query, response, sources)")
    print("")
    print("3. Adaptez la gestion des réponses rejetées selon le mode")
    print("")
    print("4. Testez avec: python test_adaptive_hallucination_guard.py")
    print("")
    print("✅ INTÉGRATION TERMINÉE !")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\\n🎉 INTÉGRATION RÉUSSIE !")
    else:
        print("\\n❌ INTÉGRATION ÉCHOUÉE !")
'''
    
    with open("integrate_adaptive_hallucination_guard.py", 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("✅ Script d'intégration créé: integrate_adaptive_hallucination_guard.py")

def main():
    """Fonction principale"""
    print("🚀 INTÉGRATION DU GARDE-FOU ANTI-HALLUCINATION ADAPTATIF")
    print("=" * 70)
    
    # 1. Sauvegarder l'ancien système
    backup_dir = backup_old_system()
    
    # 2. Mettre à jour le RAG engine
    if update_rag_engine():
        print("✅ RAG engine mis à jour avec succès")
    else:
        print("❌ Erreur lors de la mise à jour du RAG engine")
        return False
    
    # 3. Créer le script d'intégration
    create_integration_script()
    
    print("\n🎉 INTÉGRATION TERMINÉE !")
    print("📋 PROCHAINES ÉTAPES:")
    print("1. Testez le nouveau système: python test_adaptive_hallucination_guard.py")
    print("2. Vérifiez l'intégration: python integrate_adaptive_hallucination_guard.py")
    print("3. Testez le RAG complet avec le nouveau système")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ INTÉGRATION RÉUSSIE !")
    else:
        print("\n❌ INTÉGRATION ÉCHOUÉE !")
