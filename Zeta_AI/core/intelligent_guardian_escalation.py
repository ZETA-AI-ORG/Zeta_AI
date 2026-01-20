"""
🛡️ SYSTÈME GUARDIAN INTELLIGENT AVEC ESCALADE PROGRESSIVE
Votre vision : Feedback loop intelligent qui guide l'utilisateur vers la précision
"""

import hashlib
import time
import json
import random
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from core.hybrid_guardian_system import HybridGuardianSystem, GuardianDecision

logger = logging.getLogger(__name__)

# --- Data Classes ---

@dataclass
class AttemptData:
    """Données d'une tentative utilisateur"""
    query: str
    timestamp: float
    rejection_reason: str
    attempt_number: int
    judge_explanation: str

@dataclass
class EscalationDecision:
    """Décision du système d'escalade"""
    action: str  # "DELIVER_RESPONSE", "REQUEST_CLARIFICATION", "ESCALATE_TO_HUMAN"
    response: str
    attempt_number: int
    requires_user_input: bool = False
    requires_human_intervention: bool = False
    failed_attempts: List[AttemptData] = field(default_factory=list)

# --- Helper Classes ---

class MessageGenerator:
    """
    💬 GÉNÉRATEUR DE MESSAGES CONTEXTUELS
    Adapte les messages selon la raison du rejet et le numéro de tentative
    """
    
    def __init__(self):
        self.clarification_templates = {
            "missing_context": [
                "Pouvez-vous être plus précis dans votre demande ?",
                "Pourriez-vous reformuler votre question avec plus de détails ?",
                "J'ai besoin de plus d'informations pour vous aider efficacement."
            ],
            "ambiguous_product": [
                "De quel produit spécifique parlez-vous exactement ?",
                "Pouvez-vous préciser le modèle ou la référence qui vous intéresse ?",
                "Quel produit en particulier vous intéresse ?"
            ],
            "unclear_intent": [
                "Que souhaitez-vous savoir exactement ?",
                "Pouvez-vous clarifier votre demande ?",
                "Quelle information recherchez-vous précisément ?"
            ],
            "complex_query": [
                "Votre question couvre plusieurs sujets. Pouvez-vous la diviser ou préciser votre priorité ?",
                "Concentrons-nous sur un aspect : que voulez-vous savoir en premier ?",
                "Votre demande est complexe. Pouvons-nous traiter un point à la fois ?"
            ],
            "default": [
                "Pouvez-vous reformuler votre question s'il vous plaît ?",
                "Je ne suis pas sûr de comprendre. Pouvez-vous être plus spécifique ?"
            ]
        }
    
    def categorize_rejection_reason(self, judge_explanation: str) -> str:
        explanation_lower = judge_explanation.lower()
        if any(word in explanation_lower for word in ['vague', 'précis', 'détail', 'contexte']):
            return "missing_context"
        if any(word in explanation_lower for word in ['produit', 'modèle', 'référence', 'article']):
            return "ambiguous_product"
        if any(word in explanation_lower for word in ['complexe', 'plusieurs', 'diviser']):
            return "complex_query"
        if any(word in explanation_lower for word in ['intention', 'but', 'objectif']):
            return "unclear_intent"
        return "default"

    def generate_clarification_request(self, judge_explanation: str, attempt_num: int) -> str:
        reason_category = self.categorize_rejection_reason(judge_explanation)
        templates = self.clarification_templates.get(reason_category, self.clarification_templates["default"])
        base_message = random.choice(templates)
        if attempt_num > 1:
            return f"{base_message} Cela m'aidera à vous donner une réponse plus précise."
        return base_message

    def generate_escalation_message(self) -> str:
        return ("J'ai du mal à vous comprendre malgré vos précisions. "
                "Je notifie mon superviseur qui prendra le relais - il devrait vous recontacter d'ici peu. "
                "Si c'est urgent, vous pouvez également contacter notre support client par téléphone.")

class AttemptTracker:
    """
    📊 SYSTÈME DE SUIVI INTELLIGENT DES TENTATIVES
    """
    def __init__(self):
        self.session_attempts: Dict[str, List[AttemptData]] = {}
        self.max_session_duration = 3600  # 1 heure

    def track_attempt(self, session_id: str, query: str, guardian_decision: GuardianDecision) -> AttemptData:
        if session_id not in self.session_attempts:
            self.session_attempts[session_id] = []
        
        attempt_data = AttemptData(
            query=query,
            timestamp=time.time(),
            rejection_reason=guardian_decision.method,
            attempt_number=len(self.session_attempts[session_id]) + 1,
            judge_explanation=guardian_decision.reason
        )
        self.session_attempts[session_id].append(attempt_data)
        self._cleanup_old_sessions()
        logger.info(f"[ATTEMPT_TRACKER] Session {session_id[:8]}: Tentative {attempt_data.attempt_number}")
        return attempt_data

    def get_attempts(self, session_id: str) -> List[AttemptData]:
        return self.session_attempts.get(session_id, [])

    def get_attempt_count(self, session_id: str) -> int:
        return len(self.get_attempts(session_id))

    def clear_session(self, session_id: str):
        if session_id in self.session_attempts:
            del self.session_attempts[session_id]
            logger.info(f"[ATTEMPT_TRACKER] Session {session_id[:8]} nettoyée (succès)")

    def _cleanup_old_sessions(self):
        current_time = time.time()
        sessions_to_remove = [sid for sid, att in self.session_attempts.items() if att and (current_time - att[-1].timestamp) > self.max_session_duration]
        for session_id in sessions_to_remove:
            del self.session_attempts[session_id]

class SupportNotificationSystem:
    """
    📧 SYSTÈME DE NOTIFICATION AUTOMATIQUE
    """
    def notify_human_support(self, session_id: str, failed_attempts: List[AttemptData]):
        notification = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "reason": "Multiple failed clarification attempts",
            "history": [{'query': fa.query, 'reason': fa.judge_explanation} for fa in failed_attempts]
        }
        logger.warning(f"[ESCALATION_TO_HUMAN] Détails: {json.dumps(notification, indent=2)}")
        # Ici, vous intégreriez un vrai système de ticketing (Jira, Zendesk) ou une alerte (Slack, email)

# --- Main Class ---

class IntelligentGuardianWithEscalation:
    """
    🎯 SYSTÈME DE SENTINELLE AVEC ESCALADE PROGRESSIVE
    """
    def __init__(self):
        self.hybrid_guardian = HybridGuardianSystem()
        self.attempt_tracker = AttemptTracker()
        self.message_generator = MessageGenerator()
        self.notification_system = SupportNotificationSystem()
        self.max_attempts = 2

    async def evaluate_with_escalation(
        self, 
        user_query: str, 
        ai_response: str, 
        session_id: str,
        **kwargs
    ) -> EscalationDecision:
        
        guardian_decision = await self.hybrid_guardian.evaluate_response(
            user_query=user_query, 
            ai_response=ai_response, 
            **kwargs
        )
        
        current_attempt_count = self.attempt_tracker.get_attempt_count(session_id)

        if guardian_decision.decision == "ACCEPT":
            self.attempt_tracker.clear_session(session_id)
            return EscalationDecision(
                action="DELIVER_RESPONSE",
                response=ai_response,
                attempt_number=current_attempt_count + 1
            )
        
        # Rejet
        self.attempt_tracker.track_attempt(session_id, user_query, guardian_decision)
        
        if current_attempt_count < self.max_attempts -1:
            clarification_msg = self.message_generator.generate_clarification_request(
                guardian_decision.reason, current_attempt_count + 1
            )
            return EscalationDecision(
                action="REQUEST_CLARIFICATION",
                response=clarification_msg,
                attempt_number=current_attempt_count + 1,
                requires_user_input=True
            )
        else:
            failed_attempts = self.attempt_tracker.get_attempts(session_id)
            self.notification_system.notify_human_support(session_id, failed_attempts)
            escalation_msg = self.message_generator.generate_escalation_message()
            self.attempt_tracker.clear_session(session_id) # Nettoyer après escalade
            return EscalationDecision(
                action="ESCALATE_TO_HUMAN",
                response=escalation_msg,
                attempt_number=current_attempt_count + 1,
                requires_human_intervention=True,
                failed_attempts=failed_attempts
            )
