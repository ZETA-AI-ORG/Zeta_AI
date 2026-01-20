#!/usr/bin/env python3
"""
📊 SYSTÈME DE LOGGING DÉTAILLÉ RAG 2024
Logging complet de chaque étape du pipeline RAG
"""

import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import traceback

@dataclass
class LogEntry:
    """Structure d'une entrée de log détaillée"""
    timestamp: str
    request_id: str
    stage: str
    step: str
    level: str
    message: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    error: Optional[str] = None

class DetailedRAGLogger:
    """
    📊 LOGGER DÉTAILLÉ POUR RAG
    
    Trace chaque étape du pipeline RAG :
    1. Réception de la requête
    2. Classification d'intention
    3. Recherche de documents
    4. Génération de réponse
    5. Validation anti-hallucination
    6. Scoring de confiance
    7. Fallback si nécessaire
    8. Envoi de la réponse
    """
    
    def __init__(self, log_level: str = "INFO"):
        self.request_id = None
        self.start_time = None
        self.stage_times = {}
        
        # Configuration du logger
        self.logger = logging.getLogger("detailed_rag")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Handler pour console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler pour fichier
        file_handler = logging.FileHandler("rag_detailed.log", encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Format détaillé
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f'
        )
        
        console_handler.setFormatter(detailed_formatter)
        file_handler.setFormatter(detailed_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        # Logs structurés
        self.structured_logs = []
        
    def start_request(self, request_data: Dict[str, Any]) -> str:
        """Démarre le logging d'une nouvelle requête"""
        self.request_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.stage_times = {}
        self.structured_logs = []
        
        self._log_entry(
            stage="REQUEST_RECEIVED",
            step="INIT",
            level="INFO",
            message="🚀 NOUVELLE REQUÊTE RAG REÇUE",
            data={
                "request_id": self.request_id,
                "user_id": request_data.get("user_id", "unknown"),
                "company_id": request_data.get("company_id", "unknown"),
                "message": request_data.get("message", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return self.request_id
    
    def log_intent_classification(self, query: str, intent_result: Any):
        """Log de la classification d'intention"""
        stage_start = time.time()
        
        self._log_entry(
            stage="INTENT_CLASSIFICATION",
            step="START",
            level="INFO",
            message="🎯 DÉBUT CLASSIFICATION D'INTENTION",
            data={
                "query": query,
                "query_length": len(query),
                "query_words": len(query.split())
            }
        )
        
        # Log du résultat de classification
        self._log_entry(
            stage="INTENT_CLASSIFICATION",
            step="RESULT",
            level="INFO",
            message=f"✅ INTENTION CLASSIFIÉE: {intent_result.primary_intent.value}",
            data={
                "primary_intent": intent_result.primary_intent.value,
                "confidence": intent_result.confidence,
                "requires_documents": intent_result.requires_documents,
                "is_critical": intent_result.is_critical,
                "fallback_required": intent_result.fallback_required,
                "context_hints": intent_result.context_hints,
                "all_intents": {k.value: v for k, v in intent_result.all_intents.items()},
                "processing_time_ms": intent_result.processing_time_ms
            }
        )
        
        self.stage_times["intent_classification"] = (time.time() - stage_start) * 1000
    
    def log_document_search(self, search_type: str, search_params: Dict[str, Any], results: List[Dict], context: str = ""):
        """Log de la recherche de documents"""
        stage_start = time.time()
        
        self._log_entry(
            stage="DOCUMENT_SEARCH",
            step="START",
            level="INFO",
            message=f"🔍 DÉBUT RECHERCHE DOCUMENTS ({search_type.upper()})",
            data={
                "search_type": search_type,
                "search_params": search_params,
                "context_length": len(context)
            }
        )
        
        # Log des résultats
        self._log_entry(
            stage="DOCUMENT_SEARCH",
            step="RESULTS",
            level="INFO",
            message=f"📄 RÉSULTATS RECHERCHE: {len(results)} documents trouvés",
            data={
                "search_type": search_type,
                "results_count": len(results),
                "context_length": len(context),
                "context_preview": context,
                "results_preview": [str(r) for r in results] if results else []
            }
        )
        
        self.stage_times["document_search"] = (time.time() - stage_start) * 1000
    
    def log_llm_generation(self, prompt: str, response: str, model: str, temperature: float, max_tokens: int):
        """Log de la génération LLM"""
        stage_start = time.time()
        
        self._log_entry(
            stage="LLM_GENERATION",
            step="START",
            level="INFO",
            message="🤖 DÉBUT GÉNÉRATION LLM",
            data={
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "prompt_length": len(prompt),
                "prompt_preview": prompt
            }
        )
        
        # Log de la réponse
        self._log_entry(
            stage="LLM_GENERATION",
            step="RESPONSE",
            level="INFO",
            message=f"💬 RÉPONSE LLM GÉNÉRÉE: {len(response)} caractères",
            data={
                "model": model,
                "response_length": len(response),
                "response_preview": response,
                "response_words": len(response.split()),
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        
        self.stage_times["llm_generation"] = (time.time() - stage_start) * 1000
    
    def log_validation(self, validation_result: Any):
        """Log de la validation anti-hallucination"""
        stage_start = time.time()
        
        self._log_entry(
            stage="HALLUCINATION_VALIDATION",
            step="START",
            level="INFO",
            message="🛡️ DÉBUT VALIDATION ANTI-HALLUCINATION",
            data={
                "validation_level": validation_result.validation_level.value,
                "intent_detected": validation_result.intent_detected.value,
                "requires_documents": validation_result.requires_documents
            }
        )
        
        # Log du résultat de validation
        self._log_entry(
            stage="HALLUCINATION_VALIDATION",
            step="RESULT",
            level="INFO" if validation_result.is_safe else "WARNING",
            message=f"✅ VALIDATION: {'SÛRE' if validation_result.is_safe else 'REJETÉE'}",
            data={
                "is_safe": validation_result.is_safe,
                "confidence_score": validation_result.confidence_score,
                "validation_level": validation_result.validation_level.value,
                "intent_detected": validation_result.intent_detected.value,
                "requires_documents": validation_result.requires_documents,
                "documents_found": validation_result.documents_found,
                "context_relevance": validation_result.context_relevance,
                "factual_accuracy": validation_result.factual_accuracy,
                "safety_score": validation_result.safety_score,
                "rejection_reason": validation_result.rejection_reason,
                "processing_time_ms": validation_result.processing_time_ms,
                "validation_details": validation_result.validation_details
            }
        )
        
        self.stage_times["validation"] = (time.time() - stage_start) * 1000
    
    def log_confidence_scoring(self, confidence_score: Any):
        """Log du scoring de confiance"""
        stage_start = time.time()
        
        self._log_entry(
            stage="CONFIDENCE_SCORING",
            step="START",
            level="INFO",
            message="📊 DÉBUT SCORING DE CONFIANCE",
            data={
            }
        )
        
        # Log du score de confiance
        self._log_entry(
            stage="CONFIDENCE_SCORING",
            step="RESULT",
            level="INFO",
            message=f"📈 SCORE CONFIANCE: {confidence_score.overall_confidence:.3f} ({confidence_score.confidence_level.value})",
            data={
                "overall_confidence": confidence_score.overall_confidence,
                "confidence_level": confidence_score.confidence_level.value,
                "intent_confidence": confidence_score.intent_confidence,
                "document_confidence": confidence_score.document_confidence,
                "context_confidence": confidence_score.context_confidence,
                "factual_confidence": confidence_score.factual_confidence,
                "safety_confidence": confidence_score.safety_confidence,
                "reliability_score": confidence_score.reliability_score,
                "risk_level": confidence_score.risk_level,
                "recommendations": confidence_score.recommendations,
                "processing_time_ms": confidence_score.processing_time_ms
            }
        )
        
        self.stage_times["confidence_scoring"] = (time.time() - stage_start) * 1000
    
    def log_fallback(self, fallback_result: Any, reason: str):
        """Log du système de fallback"""
        stage_start = time.time()
        
        self._log_entry(
            stage="FALLBACK_SYSTEM",
            step="TRIGGERED",
            level="WARNING",
            message=f"🔄 FALLBACK DÉCLENCHÉ: {reason}",
            data={
                "reason": reason,
                "fallback_type": fallback_result.fallback_type.value,
                "confidence": fallback_result.confidence,
                "is_helpful": fallback_result.is_helpful,
                "escalation_required": fallback_result.escalation_required,
                "suggested_actions": fallback_result.suggested_actions
            }
        )
        
        # Log de la réponse de fallback
        self._log_entry(
            stage="FALLBACK_SYSTEM",
            step="RESPONSE",
            level="INFO",
            message=f"💬 RÉPONSE FALLBACK: {len(fallback_result.response)} caractères",
            data={
                "response": fallback_result.response,
                "fallback_type": fallback_result.fallback_type.value,
                "confidence": fallback_result.confidence,
                "is_helpful": fallback_result.is_helpful,
                "escalation_required": fallback_result.escalation_required,
                "suggested_actions": fallback_result.suggested_actions,
                "processing_time_ms": fallback_result.processing_time_ms
            }
        )
        
        self.stage_times["fallback"] = (time.time() - stage_start) * 1000
    
    def log_response_sent(self, final_response: str, response_metadata: Dict[str, Any]):
        """Log de l'envoi de la réponse finale"""
        total_time = (time.time() - self.start_time) * 1000
        
        self._log_entry(
            stage="RESPONSE_SENT",
            step="FINAL",
            level="INFO",
            message="✅ RÉPONSE FINALE ENVOYÉE",
            data={
                "response_length": len(final_response),
                "response_preview": final_response,
                "total_processing_time_ms": total_time,
                "stage_times": self.stage_times,
                "metadata": response_metadata
            }
        )
        
        # Log de synthèse
        self._log_entry(
            stage="REQUEST_COMPLETE",
            step="SUMMARY",
            level="INFO",
            message="🎉 REQUÊTE RAG TERMINÉE",
            data={
                "request_id": self.request_id,
                "total_time_ms": total_time,
                "stage_breakdown": self.stage_times,
                "final_response_length": len(final_response),
                "success": True
            }
        )
    
    def log_error(self, stage: str, step: str, error: Exception, context: Dict[str, Any] = None):
        """Log d'une erreur"""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        self._log_entry(
            stage=stage,
            step=step,
            level="ERROR",
            message=f"❌ ERREUR: {str(error)}",
            data=error_data,
            error=str(error)
        )
    
    def _log_entry(self, stage: str, step: str, level: str, message: str, data: Dict[str, Any], error: str = None):
        """Crée et enregistre une entrée de log"""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            request_id=self.request_id or "unknown",
            stage=stage,
            step=step,
            level=level,
            message=message,
            data=data,
            error=error
        )
        
        # Log structuré
        self.structured_logs.append(asdict(entry))
        
        # Log console/fichier
        log_message = f"[{self.request_id}] {stage}.{step} | {message}"
        if data:
            log_message += f" | Data: {json.dumps(data, ensure_ascii=False, indent=2)}"
        
        if level == "ERROR":
            self.logger.error(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        elif level == "DEBUG":
            self.logger.debug(log_message)
        else:
            self.logger.info(log_message)
    
    def get_structured_logs(self) -> List[Dict[str, Any]]:
        """Retourne les logs structurés"""
        return self.structured_logs
    
    def save_logs_to_file(self, filename: str = "rag_latest_detailed_log.json"):
        """Sauvegarde les logs dans un fichier JSON (écrasement automatique)"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "request_id": self.request_id,
                    "start_time": self.start_time,
                    "total_duration_ms": (time.time() - self.start_time) * 1000 if self.start_time else 0,
                    "stage_times": self.stage_times,
                    "logs": self.structured_logs
                }, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📁 Logs sauvegardés et mis à jour dans: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"❌ Erreur sauvegarde logs: {e}")
            return None

# Instance globale
detailed_logger = DetailedRAGLogger()

# Fonctions d'interface pour compatibilité
def start_detailed_logging(request_data: Dict[str, Any]) -> str:
    """Démarre le logging détaillé"""
    return detailed_logger.start_request(request_data)

def log_intent_classification(query: str, intent_result: Any):
    """Log de la classification d'intention"""
    detailed_logger.log_intent_classification(query, intent_result)

def log_document_search(search_type: str, search_params: Dict[str, Any], results: List[Dict], context: str = ""):
    """Log de la recherche de documents"""
    detailed_logger.log_document_search(search_type, search_params, results, context)

def log_llm_generation(prompt: str, response: str, model: str, temperature: float, max_tokens: int):
    """Log de la génération LLM"""
    detailed_logger.log_llm_generation(prompt, response, model, temperature, max_tokens)

def log_validation(validation_result: Any):
    """Log de la validation anti-hallucination"""
    detailed_logger.log_validation(validation_result)

def log_confidence_scoring(confidence_score: Any):
    """Log du scoring de confiance"""
    detailed_logger.log_confidence_scoring(confidence_score)

def log_fallback(fallback_result: Any, reason: str):
    """Log du système de fallback"""
    detailed_logger.log_fallback(fallback_result, reason)

def log_response_sent(final_response: str, response_metadata: Dict[str, Any]):
    """Log de l'envoi de la réponse finale"""
    detailed_logger.log_response_sent(final_response, response_metadata)

def log_error(stage: str, step: str, error: Exception, context: Dict[str, Any] = None):
    """Log d'une erreur"""
    detailed_logger.log_error(stage, step, error, context)

def get_structured_logs() -> List[Dict[str, Any]]:
    """Retourne les logs structurés"""
    return detailed_logger.get_structured_logs()

def save_logs_to_file(filename: str = None):
    """Sauvegarde les logs dans un fichier"""
    detailed_logger.save_logs_to_file(filename)

if __name__ == "__main__":
    # Test du système de logging
    logger = DetailedRAGLogger()
    
    # Simulation d'une requête
    request_data = {
        "user_id": "test_user",
        "company_id": "test_company",
        "message": "Comment tu t'appelles ?"
    }
    
    request_id = logger.start_request(request_data)
    print(f"Request ID: {request_id}")
    
    # Simulation d'étapes
    logger.log_intent_classification("Test query", type('obj', (object,), {
        'primary_intent': type('obj', (object,), {'value': 'social_greeting'}),
        'confidence': 0.9,
        'requires_documents': False,
        'is_critical': False,
        'fallback_required': False,
        'context_hints': [],
        'all_intents': {},
        'processing_time_ms': 50.0
    })())
    
    logger.log_response_sent("Réponse de test", {"test": True})
    
    print("Logs générés avec succès !")
