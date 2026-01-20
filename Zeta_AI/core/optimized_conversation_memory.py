#!/usr/bin/env python3
"""
🧠 MÉMOIRE CONVERSATIONNELLE OPTIMISÉE
Basée sur les techniques réelles d'OpenAI, Anthropic et recherches académiques

PRINCIPE:
- Sliding Window: 5 derniers messages UTILISATEUR uniquement
- Progressive Synthesis: Synthèse évolutive des anciens échanges
- User-Centric: Focus sur les intentions/préférences utilisateur
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

@dataclass
class UserMessage:
    """Message utilisateur avec métadonnées"""
    timestamp: datetime
    content: str
    extracted_intent: str
    importance_score: float

@dataclass
class ConversationMemory:
    """Mémoire conversationnelle optimisée"""
    user_id: str
    company_id: str
    session_start: datetime
    last_update: datetime
    
    # Sliding Window: 5 derniers messages utilisateur
    recent_user_messages: List[UserMessage]
    
    # Progressive Synthesis: Résumé évolutif
    progressive_summary: str
    
    # Métriques
    total_user_messages: int
    synthesis_version: int

class OptimizedConversationMemory:
    """
    🎯 MÉMOIRE CONVERSATIONNELLE OPTIMISÉE
    
    Techniques confirmées par recherche:
    1. Sliding Window (k=5) - Messages utilisateur uniquement
    2. Progressive Summarization - Synthèse évolutive
    3. Intent Extraction - Focus sur les intentions utilisateur
    """
    
    def __init__(self, max_recent_messages: int = 5, synthesis_threshold: int = 8):
        self.max_recent_messages = max_recent_messages
        self.synthesis_threshold = synthesis_threshold
        self.active_memories: Dict[str, ConversationMemory] = {}
        
        # Prompt de synthèse progressive (technique OpenAI)
        self.synthesis_prompt = """
Analyse ces messages utilisateur et mets à jour le résumé:

RÉSUMÉ ACTUEL:
{current_summary}

NOUVEAUX MESSAGES UTILISATEUR:
{new_user_messages}

INSTRUCTIONS:
1. Garde UNIQUEMENT les informations sur l'utilisateur:
   - Ses préférences exprimées
   - Ses besoins/demandes
   - Ses décisions/choix
   - Ses contraintes (budget, délais, etc.)

2. IGNORE complètement:
   - Les réponses de l'assistant
   - Les informations produit données par l'assistant
   - Les calculs faits par l'assistant

3. Sois CONCIS et FACTUEL

RÉSUMÉ MIS À JOUR:
"""

        # Prompt d'extraction d'intention
        self.intent_extraction_prompt = """
Analyse ce message utilisateur et identifie son intention principale:

MESSAGE: {user_message}

Catégories possibles:
- product_inquiry (recherche produit)
- price_inquiry (demande prix)
- order_intent (intention commande)
- delivery_inquiry (question livraison)
- payment_inquiry (question paiement)
- modification_request (modification)
- confirmation_request (confirmation)
- complaint (réclamation)
- general_question (question générale)

Intention détectée:
"""

    def get_memory_key(self, user_id: str, company_id: str) -> str:
        """Génère la clé unique pour une mémoire"""
        return f"{company_id}_{user_id}"

    async def add_user_message(self, user_id: str, company_id: str, 
                              user_message: str, llm_client) -> ConversationMemory:
        """
        🔄 Ajoute un nouveau message utilisateur et met à jour la mémoire
        """
        memory_key = self.get_memory_key(user_id, company_id)
        
        # Récupérer ou créer la mémoire
        if memory_key not in self.active_memories:
            self.active_memories[memory_key] = ConversationMemory(
                user_id=user_id,
                company_id=company_id,
                session_start=datetime.now(),
                last_update=datetime.now(),
                recent_user_messages=[],
                progressive_summary="",
                total_user_messages=0,
                synthesis_version=1
            )
        
        memory = self.active_memories[memory_key]
        
        # Extraire l'intention du message
        intent = await self._extract_intent(user_message, llm_client)
        importance = self._calculate_importance(user_message, intent)
        
        # Créer l'objet message utilisateur
        user_msg = UserMessage(
            timestamp=datetime.now(),
            content=user_message,
            extracted_intent=intent,
            importance_score=importance
        )
        
        # Ajouter au sliding window
        memory.recent_user_messages.append(user_msg)
        memory.total_user_messages += 1
        memory.last_update = datetime.now()
        
        # Déclencher synthèse si nécessaire
        if len(memory.recent_user_messages) > self.max_recent_messages:
            await self._perform_progressive_synthesis(memory, llm_client)
        
        return memory

    async def _extract_intent(self, user_message: str, llm_client) -> str:
        """
        🎯 Extrait l'intention du message utilisateur
        """
        try:
            prompt = self.intent_extraction_prompt.format(user_message=user_message)
            response = await llm_client.complete(prompt, temperature=0.1, max_tokens=50)
            
            # Gérer dict, tuple ou string
            if isinstance(response, dict):
                intent = response.get("response", "").strip().lower()
            elif isinstance(response, tuple):
                intent = response[0].strip().lower()
            else:
                intent = response.strip().lower()
            
            # Valider l'intention
            valid_intents = [
                'product_inquiry', 'price_inquiry', 'order_intent', 
                'delivery_inquiry', 'payment_inquiry', 'modification_request',
                'confirmation_request', 'complaint', 'general_question'
            ]
            
            for valid_intent in valid_intents:
                if valid_intent in intent:
                    return valid_intent
            
            return 'general_question'
            
        except Exception as e:
            print(f"[INTENT EXTRACTION] Erreur: {e}")
            return 'general_question'

    def _calculate_importance(self, user_message: str, intent: str) -> float:
        """
        📊 Calcule l'importance d'un message utilisateur (0-1)
        """
        importance = 0.0
        message_lower = user_message.lower()
        
        # Score basé sur l'intention
        intent_scores = {
            'order_intent': 0.9,
            'confirmation_request': 0.8,
            'payment_inquiry': 0.7,
            'price_inquiry': 0.6,
            'delivery_inquiry': 0.6,
            'modification_request': 0.7,
            'product_inquiry': 0.5,
            'complaint': 0.8,
            'general_question': 0.3
        }
        
        importance += intent_scores.get(intent, 0.3)
        
        # Mots-clés critiques
        critical_keywords = [
            'commande', 'achète', 'confirme', 'total', 'prix',
            'livraison', 'adresse', 'paiement', 'urgent', 'problème'
        ]
        
        for keyword in critical_keywords:
            if keyword in message_lower:
                importance += 0.1
        
        # Longueur du message (plus long = potentiellement plus important)
        if len(user_message) > 100:
            importance += 0.1
        
        return min(importance, 1.0)

    async def _perform_progressive_synthesis(self, memory: ConversationMemory, llm_client):
        """
        🧠 Effectue la synthèse progressive des anciens messages
        """
        if len(memory.recent_user_messages) <= self.max_recent_messages:
            return
        
        # Messages à synthétiser (les plus anciens)
        messages_to_synthesize = memory.recent_user_messages[:-self.max_recent_messages]
        memory.recent_user_messages = memory.recent_user_messages[-self.max_recent_messages:]
        
        # Formater les messages pour synthèse
        new_messages_text = ""
        for msg in messages_to_synthesize:
            new_messages_text += f"[{msg.extracted_intent}] {msg.content}\n"
        
        # Générer la synthèse progressive
        try:
            prompt = self.synthesis_prompt.format(
                current_summary=memory.progressive_summary,
                new_user_messages=new_messages_text
            )
            
            response = await llm_client.complete(prompt, temperature=0.2, max_tokens=300)
            
            # Gérer dict, tuple ou string
            if isinstance(response, dict):
                new_summary = response.get("response", "").strip()
            elif isinstance(response, tuple):
                new_summary = response[0].strip()
            else:
                new_summary = response.strip()
            
            memory.progressive_summary = new_summary
            memory.synthesis_version += 1
            
            print(f"[SYNTHESIS] Synthèse progressive v{memory.synthesis_version} mise à jour")
            
        except Exception as e:
            print(f"[SYNTHESIS] Erreur synthèse progressive: {e}")

    def get_context_for_llm(self, user_id: str, company_id: str) -> str:
        """
        📋 Génère le contexte conversationnel pour le LLM
        """
        memory_key = self.get_memory_key(user_id, company_id)
        
        if memory_key not in self.active_memories:
            return ""
        
        memory = self.active_memories[memory_key]
        context_parts = []
        
        # Synthèse progressive des anciens échanges
        if memory.progressive_summary:
            context_parts.append(f"=== HISTORIQUE UTILISATEUR ===\n{memory.progressive_summary}")
        
        # 5 derniers messages utilisateur
        if memory.recent_user_messages:
            recent_text = "=== MESSAGES RÉCENTS UTILISATEUR ==="
            for msg in memory.recent_user_messages:
                recent_text += f"\n[{msg.extracted_intent}] USER: {msg.content}"
            
            context_parts.append(recent_text)
        
        return "\n\n".join(context_parts)

    def get_user_intent_history(self, user_id: str, company_id: str) -> List[str]:
        """
        📊 Récupère l'historique des intentions utilisateur
        """
        memory_key = self.get_memory_key(user_id, company_id)
        
        if memory_key not in self.active_memories:
            return []
        
        memory = self.active_memories[memory_key]
        return [msg.extracted_intent for msg in memory.recent_user_messages]

    def cleanup_expired_memories(self, max_age_hours: int = 24) -> int:
        """
        🧹 Nettoie les mémoires expirées
        """
        now = datetime.now()
        expired_keys = []
        
        for key, memory in self.active_memories.items():
            age = now - memory.last_update
            if age > timedelta(hours=max_age_hours):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.active_memories[key]
        
        return len(expired_keys)

    def get_memory_stats(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """
        📊 Statistiques de la mémoire
        """
        memory_key = self.get_memory_key(user_id, company_id)
        
        if memory_key not in self.active_memories:
            return {}
        
        memory = self.active_memories[memory_key]
        
        return {
            "total_user_messages": memory.total_user_messages,
            "recent_messages_count": len(memory.recent_user_messages),
            "synthesis_version": memory.synthesis_version,
            "has_progressive_summary": bool(memory.progressive_summary),
            "session_duration_minutes": (datetime.now() - memory.session_start).total_seconds() / 60,
            "last_update": memory.last_update.isoformat(),
            "recent_intents": [msg.extracted_intent for msg in memory.recent_user_messages]
        }

# Instance globale
optimized_memory = OptimizedConversationMemory()

async def add_user_conversation_message(user_id: str, company_id: str, 
                                       user_message: str, llm_client) -> str:
    """
    🔄 Fonction utilitaire pour ajouter un message utilisateur
    """
    await optimized_memory.add_user_message(user_id, company_id, user_message, llm_client)
    return optimized_memory.get_context_for_llm(user_id, company_id)

def get_optimized_conversation_context(user_id: str, company_id: str) -> str:
    """
    📋 Fonction utilitaire pour récupérer le contexte optimisé
    """
    return optimized_memory.get_context_for_llm(user_id, company_id)

if __name__ == "__main__":
    print("🧠 MÉMOIRE CONVERSATIONNELLE OPTIMISÉE")
    print("Techniques confirmées: Sliding Window + Progressive Synthesis")
    print("=" * 70)
    print("Usage:")
    print("from core.optimized_conversation_memory import add_user_conversation_message")
