"""
Agent de Clôture Intelligente de Conversation
Gère la fin automatique des conversations après confirmation commande
"""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ConversationState:
    """État de la conversation"""
    is_closed: bool = False
    closure_message_sent: bool = False
    final_acknowledgment_sent: bool = False
    company_name: str = ""

class ConversationClosureAgent:
    def __init__(self, redis_cache=None):
        self.cache = redis_cache
        
        # Patterns de confirmation de commande
        self.confirmation_patterns = [
            r"oui\s+je\s+confirme",
            r"je\s+confirme",
            r"c'est\s+bon",
            r"je\s+valide",
            r"je\s+suis\s+d'accord",
            r"je\s+confirme\s+la\s+commande",
            r"d'accord\s+pour\s+la\s+commande",
            r"oui\s+c'est\s+parfait",
            r"parfait\s+je\s+confirme"
        ]
        
        # Messages de clôture finale (après instruction "envoyez OK")
        self.closure_messages = [
            "ok", "okay", "d'accord", "merci", "c'est compris", 
            "parfait", "bien reçu", "je comprends", "entendu", 
            "merci beaucoup", "très bien", "compris", "reçu"
        ]
        
        # Patterns qui indiquent une VRAIE nouvelle question (réouverture)
        self.reopening_patterns = [
            r"j'ai\s+une\s+question",
            r"je\s+voudrais",
            r"pouvez-vous",
            r"est-ce\s+que",
            r"combien",
            r"quand",
            r"comment",
            r"où",
            r"quel",
            r"quelle",
            r"pourquoi",
            r"nouveau\s+produit",
            r"autre\s+commande",
            r"problème",
            r"annuler"
        ]

    def _get_conversation_state(self, company_id: str, user_id: str) -> ConversationState:
        """Récupère l'état de conversation depuis le cache"""
        if not self.cache:
            return ConversationState()
        
        try:
            cache_key = f"conversation_state:{company_id}:{user_id}"
            cached_state = self.cache.generic_get(cache_key)
            
            if cached_state:
                return ConversationState(
                    is_closed=cached_state.get('is_closed', False),
                    closure_message_sent=cached_state.get('closure_message_sent', False),
                    final_acknowledgment_sent=cached_state.get('final_acknowledgment_sent', False),
                    company_name=cached_state.get('company_name', '')
                )
        except Exception as e:
            print(f"[CLOSURE] Erreur lecture état: {e}")
        
        return ConversationState()

    def _save_conversation_state(self, company_id: str, user_id: str, state: ConversationState):
        """Sauvegarde l'état de conversation dans le cache"""
        if not self.cache:
            return
        
        try:
            cache_key = f"conversation_state:{company_id}:{user_id}"
            state_dict = {
                'is_closed': state.is_closed,
                'closure_message_sent': state.closure_message_sent,
                'final_acknowledgment_sent': state.final_acknowledgment_sent,
                'company_name': state.company_name
            }
            self.cache.generic_set(cache_key, state_dict, ttl=86400)  # 24h
        except Exception as e:
            print(f"[CLOSURE] Erreur sauvegarde état: {e}")

    def is_confirmation_message(self, message: str) -> bool:
        """Détecte si le message est une confirmation de commande"""
        message_clean = message.lower().strip()
        
        # Vérification par patterns regex
        for pattern in self.confirmation_patterns:
            if re.search(pattern, message_clean):
                return True
        
        return False

    def is_closure_message(self, message: str) -> bool:
        """Détecte si le message est un message de clôture (OK, merci, etc.)"""
        message_clean = message.lower().strip()
        
        # Messages courts et simples de politesse/clôture
        return any(closure in message_clean for closure in self.closure_messages)

    def is_reopening_message(self, message: str) -> bool:
        """Détecte si le message indique une vraie nouvelle question"""
        message_clean = message.lower().strip()
        
        # Patterns qui indiquent clairement une nouvelle demande
        for pattern in self.reopening_patterns:
            if re.search(pattern, message_clean):
                return True
        
        # Message long (>20 mots) = probablement une vraie question
        if len(message.split()) > 20:
            return True
        
        return False

    def process_message(
        self, 
        message: str, 
        company_id: str, 
        user_id: str,
        company_name: str = ""
    ) -> Optional[str]:
        """
        Traite le message et retourne une réponse de clôture si nécessaire
        
        Returns:
            str: Réponse de clôture à envoyer
            None: Continuer le traitement normal
            "": Silence (ne pas répondre)
        """
        
        # Récupération de l'état actuel
        state = self._get_conversation_state(company_id, user_id)
        state.company_name = company_name or state.company_name
        
        print(f"[CLOSURE] État actuel: closed={state.is_closed}, closure_sent={state.closure_message_sent}")
        
        # 1. Si conversation déjà fermée
        if state.is_closed:
            if self.is_closure_message(message):
                # Message de politesse après clôture → Silence ou accusé final
                if not state.final_acknowledgment_sent:
                    state.final_acknowledgment_sent = True
                    self._save_conversation_state(company_id, user_id, state)
                    return "Avec plaisir ! 😊"
                else:
                    # Déjà répondu une fois, maintenant silence total
                    return ""
            
            elif self.is_reopening_message(message):
                # Vraie nouvelle question → Réouverture
                print("[CLOSURE] Réouverture détectée")
                state.is_closed = False
                state.closure_message_sent = False  
                state.final_acknowledgment_sent = False
                self._save_conversation_state(company_id, user_id, state)
                return None  # Continuer traitement normal
            
            else:
                # Autre message en conversation fermée → Silence
                return ""
        
        # 2. Détection de confirmation de commande
        if self.is_confirmation_message(message):
            print("[CLOSURE] Confirmation détectée")
            
            # Marquer conversation comme fermée
            state.is_closed = True
            state.closure_message_sent = True
            self._save_conversation_state(company_id, user_id, state)
            
            # Message de clôture avec instruction (délai flexible)
            company_display = company_name if company_name else "Notre équipe"
            
            return (
                f"Merci pour votre commande ! Notre équipe va traiter votre demande et vous contactera pour organiser la livraison. "
                f"Pour clôturer la conversation, répondez \"OK\". "
                f"Bonne journée ! - {company_display}"
            )
        
        # 3. Aucune action spéciale → Continuer traitement normal
        return None

    def reset_conversation(self, company_id: str, user_id: str):
        """Remet à zéro l'état de conversation (pour debug/admin)"""
        if self.cache:
            try:
                cache_key = f"conversation_state:{company_id}:{user_id}"
                self.cache.generic_delete(cache_key)
                print(f"[CLOSURE] État conversation réinitialisé pour {user_id}")
            except Exception as e:
                print(f"[CLOSURE] Erreur reset: {e}")

    def get_stats(self, company_id: str) -> Dict[str, int]:
        """Statistiques des conversations fermées (optionnel)"""
        # Implémentation simplifiée - peut être étendue
        return {
            "conversations_fermees_aujourd_hui": 0,  # À implémenter
            "confirmations_detectees": 0,
            "reouvertures": 0
        }

# Instance globale
closure_agent = ConversationClosureAgent()

# Fonction d'intégration pour rag_engine.py
def integrate_closure_agent(
    message: str,
    company_id: str, 
    user_id: str,
    company_name: str = "",
    redis_cache=None
) -> Optional[str]:
    """
    Fonction principale à intégrer dans rag_engine.py
    
    Usage:
    closure_response = integrate_closure_agent(message, company_id, user_id, company_name, redis_cache)
    if closure_response is not None:
        if closure_response == "":
            return ""  # Silence
        else:
            return closure_response  # Réponse de clôture
    # Sinon, continuer traitement RAG normal
    """
    
    if redis_cache:
        closure_agent.cache = redis_cache
    
    return closure_agent.process_message(message, company_id, user_id, company_name)
