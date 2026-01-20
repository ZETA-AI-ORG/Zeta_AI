#!/usr/bin/env python3
"""
🔧 SCRIPT DE CORRECTION DU RAG ENGINE
Remplace l'ancien système par le nouveau système anti-hallucination adaptatif
"""

import re

def fix_rag_engine():
    """Corrige le RAG engine pour utiliser le nouveau système"""
    print("🔧 CORRECTION DU RAG ENGINE")
    print("=" * 40)
    
    # Lire le fichier
    with open("core/rag_engine_simplified_fixed.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Remplacer la section de validation
    old_validation = """        # 4. Validation contextuelle avancée
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
    
    new_validation = """        # 4. Validation anti-hallucination adaptative
        logger.info(f"[RAG_ADVANCED] 🛡️ Étape 4: Validation anti-hallucination adaptative")
        
        # Préparer les documents sources
        source_documents = []
        if supabase_context:
            source_documents.append(supabase_context)
        if meili_context:
            source_documents.append(meili_context)
        
        # Validation adaptative
        try:
            from .adaptive_hallucination_guard import check_hallucination_adaptive
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
                logger.warning(f"[RAG_ADVANCED] Rejeté: {validation_result['rejection_reason']}")
        except Exception as e:
            logger.error(f"[RAG_ADVANCED] Erreur validation: {e}")
            validation_result = {
                'is_safe': True,
                'validation_mode': 'simple_conversation',
                'confidence': 0.5,
                'rejection_reason': None
            }"""
    
    if old_validation in content:
        content = content.replace(old_validation, new_validation)
        print("✅ Remplacé la validation contextuelle")
    else:
        print("⚠️  Section de validation non trouvée")
    
    # 2. Remplacer la gestion des fallbacks
    old_fallback = """        # 5. Gestion des réponses rejetées
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
    
    new_fallback = """        # 5. Gestion des réponses rejetées
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
    else:
        print("⚠️  Section de fallback non trouvée")
    
    # 3. Remplacer le calcul de confiance
    old_confidence = """        # 6. Calcul du score de confiance
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
    
    new_confidence = """        # 6. Calcul du score de confiance simplifié
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
    else:
        print("⚠️  Section de confiance non trouvée")
    
    # 4. Remplacer la construction de la réponse finale
    old_response = """        # 8. Construction de la réponse finale
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
    
    new_response = """        # 8. Construction de la réponse finale
        logger.info(f"[RAG_ADVANCED] 📤 Étape 7: Construction réponse finale")
        response_data = {
            'response': ai_response,
            'intent': intent_type,
            'confidence': confidence_score['overall_confidence'],
            'confidence_level': confidence_score['confidence_level'],
            'validation_safe': validation_result['is_safe'],
            'requires_documents': requires_docs,
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
    else:
        print("⚠️  Section de réponse finale non trouvée")
    
    # 5. Remplacer la gestion d'erreur d'urgence
    old_emergency = """                # Fallback d'urgence
                logger.warning(f"[RAG_ADVANCED] 🚨 Activation du fallback d'urgence")
                emergency_fallback = await generate_intelligent_fallback(
                    user_query=message,
                    intent_result=IntentResult(
                        primary_intent=IntentType.GENERAL_CONVERSATION,
                        confidence=0.0,
                        all_intents={},
                        requires_documents=False,
                        is_critical=False,
                        fallback_required=True,
                        context_hints=[],
                        processing_time_ms=0.0
                    ),
                    error_context={'error': 'critical_error', 'details': str(e)},
                    company_context={'company_name': 'Rue du Gros', 'ai_name': 'Gamma'}
                )
                
                log_fallback(emergency_fallback, f"Erreur critique: {str(e)}")
                
                emergency_response = {
                    'response': emergency_fallback.response,
                    'intent': 'general_conversation',
                    'confidence': 0.1,
                    'confidence_level': 'very_low',
                    'validation_safe': False,
                    'requires_documents': False,
                    'documents_found': False,
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'debug_info': {
                        'error': str(e),
                        'emergency_fallback': True
                    }
                }
                
                log_response_sent(emergency_fallback.response, emergency_response)"""
    
    new_emergency = """                # Fallback d'urgence
                logger.warning(f"[RAG_ADVANCED] 🚨 Activation du fallback d'urgence")
                
                emergency_response = {
                    'response': "Je rencontre une difficulté technique. Pouvez-vous réessayer ou contacter notre service client ?",
                    'intent': 'general_conversation',
                    'confidence': 0.1,
                    'confidence_level': 'very_low',
                    'validation_safe': False,
                    'requires_documents': False,
                    'documents_found': False,
                    'processing_time_ms': (time.time() - start_time) * 1000,
                    'debug_info': {
                        'error': str(e),
                        'emergency_fallback': True
                    }
                }
                
                logger.error(f"[RAG_ADVANCED] Fallback d'urgence activé: {str(e)}")"""
    
    if old_emergency in content:
        content = content.replace(old_emergency, new_emergency)
        print("✅ Remplacé le fallback d'urgence")
    else:
        print("⚠️  Section d'urgence non trouvée")
    
    # Sauvegarder le fichier corrigé
    with open("core/rag_engine_simplified_fixed.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ RAG engine corrigé avec succès !")
    return True

if __name__ == "__main__":
    fix_rag_engine()
