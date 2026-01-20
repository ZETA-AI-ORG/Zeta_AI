#!/usr/bin/env python3
"""
🧠 SYNTHÈSE CONVERSATIONNELLE UNIVERSELLE
Basé sur les meilleures pratiques d'OpenAI, Anthropic et LangChain
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

@dataclass
class ConversationExchange:
    """Un échange dans la conversation"""
    timestamp: datetime
    user_message: str
    assistant_response: str
    extracted_entities: Dict[str, Any]
    importance_score: float  # 0-1, calculé automatiquement

@dataclass
class ConversationSynthesis:
    """Synthèse d'une conversation"""
    user_id: str
    company_id: str
    session_start: datetime
    last_update: datetime
    
    # Synthèse progressive
    current_summary: str
    key_facts: Dict[str, Any]  # Faits importants extraits
    user_preferences: Dict[str, Any]  # Préférences détectées
    pending_actions: List[str]  # Actions en attente
    
    # Échanges récents (gardés intégralement)
    recent_exchanges: List[ConversationExchange]
    
    # Métriques
    total_exchanges: int
    synthesis_version: int

class UniversalConversationSynthesis:
    """
    🌍 SYNTHÈSE CONVERSATIONNELLE UNIVERSELLE
    
    Principe : Comme les grands acteurs du domaine
    - Garde les échanges récents intégralement
    - Synthétise progressivement les anciens
    - Extrait automatiquement les entités importantes
    - S'adapte à n'importe quel domaine métier
    """
    
    def __init__(self, max_recent_exchanges: int = 5, synthesis_threshold: int = 10):
        self.max_recent_exchanges = max_recent_exchanges
        self.synthesis_threshold = synthesis_threshold
        self.active_syntheses: Dict[str, ConversationSynthesis] = {}
        
        # Prompts universels pour synthèse
        self.synthesis_prompt_template = """
Tu es un expert en synthèse conversationnelle. Analyse cette conversation et crée un résumé CONCIS et FACTUEL.

CONVERSATION PRÉCÉDENTE:
{previous_summary}

NOUVEAUX ÉCHANGES:
{new_exchanges}

INSTRUCTIONS:
1. Garde UNIQUEMENT les informations critiques pour la suite de la conversation
2. Extrait les faits importants (prix, quantités, préférences, décisions)
3. Note les actions en attente ou promesses faites
4. Ignore les politesses et répétitions
5. Reste neutre et factuel

SYNTHÈSE MISE À JOUR:
"""

        self.entity_extraction_prompt = """
Extrait les entités importantes de cet échange commercial:

USER: {user_message}
ASSISTANT: {assistant_response}

Identifie et structure:
- Produits/services mentionnés
- Quantités, prix, tailles
- Lieux, adresses, zones
- Préférences exprimées
- Décisions prises
- Actions promises

Format JSON:
{{"entities": {{"products": [], "quantities": [], "prices": [], "locations": [], "preferences": [], "decisions": [], "actions": []}}}}
"""

    def get_synthesis_key(self, user_id: str, company_id: str) -> str:
        """Génère la clé unique pour une synthèse"""
        return f"{company_id}_{user_id}"

    async def add_exchange(self, user_id: str, company_id: str, 
                          user_message: str, assistant_response: str,
                          llm_client) -> ConversationSynthesis:
        """
        🔄 Ajoute un nouvel échange et met à jour la synthèse
        """
        synthesis_key = self.get_synthesis_key(user_id, company_id)
        
        # Récupérer ou créer la synthèse
        if synthesis_key not in self.active_syntheses:
            self.active_syntheses[synthesis_key] = ConversationSynthesis(
                user_id=user_id,
                company_id=company_id,
                session_start=datetime.now(),
                last_update=datetime.now(),
                current_summary="",
                key_facts={},
                user_preferences={},
                pending_actions=[],
                recent_exchanges=[],
                total_exchanges=0,
                synthesis_version=1
            )
        
        synthesis = self.active_syntheses[synthesis_key]
        
        # Extraire les entités de l'échange
        entities = await self._extract_entities(user_message, assistant_response, llm_client)
        importance = self._calculate_importance(user_message, assistant_response, entities)
        
        # Créer l'échange
        exchange = ConversationExchange(
            timestamp=datetime.now(),
            user_message=user_message,
            assistant_response=assistant_response,
            extracted_entities=entities,
            importance_score=importance
        )
        
        # Ajouter aux échanges récents
        synthesis.recent_exchanges.append(exchange)
        synthesis.total_exchanges += 1
        synthesis.last_update = datetime.now()
        
        # Déclencher synthèse si nécessaire
        if len(synthesis.recent_exchanges) > self.max_recent_exchanges:
            await self._perform_synthesis(synthesis, llm_client)
        
        # Mettre à jour les faits clés
        self._update_key_facts(synthesis, entities)
        
        return synthesis

    async def _extract_entities(self, user_message: str, assistant_response: str, 
                               llm_client) -> Dict[str, Any]:
        """
        🎯 Extraction universelle d'entités (sans hardcodage)
        """
        try:
            prompt = self.entity_extraction_prompt.format(
                user_message=user_message,
                assistant_response=assistant_response
            )
            
            response = await llm_client.complete(prompt, temperature=0.1, max_tokens=300)
            
            # Gérer dict, tuple ou string
            if isinstance(response, dict):
                response_text = response.get("response", "")
            elif isinstance(response, tuple):
                response_text = response[0]
            else:
                response_text = response
            
            # Parser la réponse JSON
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"[ENTITY EXTRACTION] Erreur: {e}")
        
        return {"entities": {}}

    def _calculate_importance(self, user_message: str, assistant_response: str, 
                            entities: Dict[str, Any]) -> float:
        """
        📊 Calcule l'importance d'un échange (0-1)
        """
        importance = 0.0
        
        # Facteurs d'importance
        user_lower = user_message.lower()
        assistant_lower = assistant_response.lower()
        
        # Mots-clés critiques
        critical_keywords = [
            'prix', 'coût', 'total', 'commande', 'confirme', 'achète',
            'livraison', 'adresse', 'paiement', 'acompte', 'wave'
        ]
        
        for keyword in critical_keywords:
            if keyword in user_lower or keyword in assistant_lower:
                importance += 0.15
        
        # Présence d'entités
        entity_count = sum(len(v) if isinstance(v, list) else 1 
                          for v in entities.get('entities', {}).values())
        importance += min(entity_count * 0.1, 0.4)
        
        # Longueur des messages (plus long = plus important)
        length_factor = min((len(user_message) + len(assistant_response)) / 1000, 0.2)
        importance += length_factor
        
        return min(importance, 1.0)

    async def _perform_synthesis(self, synthesis: ConversationSynthesis, llm_client):
        """
        🧠 Effectue la synthèse des échanges anciens
        """
        if len(synthesis.recent_exchanges) <= self.max_recent_exchanges:
            return
        
        # Prendre les échanges à synthétiser (les plus anciens)
        exchanges_to_synthesize = synthesis.recent_exchanges[:-self.max_recent_exchanges]
        synthesis.recent_exchanges = synthesis.recent_exchanges[-self.max_recent_exchanges:]
        
        # Formater les échanges pour synthèse
        exchanges_text = ""
        for exchange in exchanges_to_synthesize:
            exchanges_text += f"USER: {exchange.user_message}\n"
            exchanges_text += f"ASSISTANT: {exchange.assistant_response}\n"
            exchanges_text += f"ENTITÉS: {exchange.extracted_entities}\n\n"
        
        # Générer la nouvelle synthèse
        try:
            prompt = self.synthesis_prompt_template.format(
                previous_summary=synthesis.current_summary,
                new_exchanges=exchanges_text
            )
            
            response = await llm_client.complete(prompt, temperature=0.2, max_tokens=500)
            
            # Gérer dict, tuple ou string
            if isinstance(response, dict):
                new_summary = response.get("response", "").strip()
            elif isinstance(response, tuple):
                new_summary = response[0].strip()
            else:
                new_summary = response.strip()
            
            synthesis.current_summary = new_summary
            synthesis.synthesis_version += 1
            
            print(f"[SYNTHESIS] Nouvelle synthèse v{synthesis.synthesis_version} générée")
            
        except Exception as e:
            print(f"[SYNTHESIS] Erreur synthèse: {e}")

    def _update_key_facts(self, synthesis: ConversationSynthesis, entities: Dict[str, Any]):
        """
        📝 Met à jour les faits clés avec les nouvelles entités
        """
        entity_data = entities.get('entities', {})
        
        for category, values in entity_data.items():
            if values:  # Si la liste n'est pas vide
                if category not in synthesis.key_facts:
                    synthesis.key_facts[category] = []
                
                # Ajouter les nouvelles valeurs (éviter doublons)
                for value in values:
                    if value not in synthesis.key_facts[category]:
                        synthesis.key_facts[category].append(value)

    def get_context_for_llm(self, user_id: str, company_id: str) -> str:
        """
        📋 Génère le contexte conversationnel pour le LLM
        """
        synthesis_key = self.get_synthesis_key(user_id, company_id)
        
        if synthesis_key not in self.active_syntheses:
            return ""
        
        synthesis = self.active_syntheses[synthesis_key]
        
        context_parts = []
        
        # Synthèse des échanges anciens
        if synthesis.current_summary:
            context_parts.append(f"=== HISTORIQUE SYNTHÉTISÉ ===\n{synthesis.current_summary}")
        
        # Faits clés extraits
        if synthesis.key_facts:
            facts_text = []
            for category, values in synthesis.key_facts.items():
                if values:
                    facts_text.append(f"{category.upper()}: {', '.join(map(str, values))}")
            
            if facts_text:
                context_parts.append(f"=== FAITS CLÉS ===\n" + "\n".join(facts_text))
        
        # Échanges récents (intégraux)
        if synthesis.recent_exchanges:
            recent_text = "=== ÉCHANGES RÉCENTS ==="
            for exchange in synthesis.recent_exchanges[-3:]:  # 3 derniers
                recent_text += f"\nUSER: {exchange.user_message}"
                recent_text += f"\nASSISTANT: {exchange.assistant_response}\n"
            
            context_parts.append(recent_text)
        
        return "\n\n".join(context_parts)

    def cleanup_expired_syntheses(self, max_age_hours: int = 24):
        """
        🧹 Nettoie les synthèses expirées
        """
        now = datetime.now()
        expired_keys = []
        
        for key, synthesis in self.active_syntheses.items():
            age = now - synthesis.last_update
            if age > timedelta(hours=max_age_hours):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.active_syntheses[key]
        
        return len(expired_keys)

    def get_synthesis_stats(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """
        📊 Statistiques de la synthèse
        """
        synthesis_key = self.get_synthesis_key(user_id, company_id)
        
        if synthesis_key not in self.active_syntheses:
            return {}
        
        synthesis = self.active_syntheses[synthesis_key]
        
        return {
            "total_exchanges": synthesis.total_exchanges,
            "recent_exchanges_count": len(synthesis.recent_exchanges),
            "synthesis_version": synthesis.synthesis_version,
            "key_facts_categories": len(synthesis.key_facts),
            "session_duration_minutes": (datetime.now() - synthesis.session_start).total_seconds() / 60,
            "last_update": synthesis.last_update.isoformat()
        }

# Instance globale
universal_synthesis = UniversalConversationSynthesis()

async def add_conversation_exchange(user_id: str, company_id: str, 
                                  user_message: str, assistant_response: str, 
                                  llm_client) -> str:
    """
    🔄 Fonction utilitaire pour ajouter un échange et récupérer le contexte
    """
    await universal_synthesis.add_exchange(
        user_id, company_id, user_message, assistant_response, llm_client
    )
    
    return universal_synthesis.get_context_for_llm(user_id, company_id)

def get_conversation_synthesis_context(user_id: str, company_id: str) -> str:
    """
    📋 Fonction utilitaire pour récupérer le contexte conversationnel
    """
    return universal_synthesis.get_context_for_llm(user_id, company_id)

if __name__ == "__main__":
    print("🧠 SYNTHÈSE CONVERSATIONNELLE UNIVERSELLE")
    print("Basée sur les meilleures pratiques d'OpenAI, Anthropic et LangChain")
    print("=" * 70)
    print("Usage:")
    print("from core.universal_conversation_synthesis import add_conversation_exchange")
