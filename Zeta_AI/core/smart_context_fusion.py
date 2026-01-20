#!/usr/bin/env python3
"""
🔗 FUSION INTELLIGENTE DES CONTEXTES
Combine Supabase + MeiliSearch + Mémoire Conversationnelle pour un contexte optimal
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from .conversation_memory import conversation_memory

@dataclass
class ContextSource:
    """Source de contexte avec métadonnées"""
    source_type: str  # 'supabase', 'meilisearch', 'conversation', 'calculation'
    content: str
    relevance_score: float
    metadata: Dict[str, Any]

class SmartContextFusion:
    """
    🔗 Gestionnaire de fusion intelligente des contextes
    """
    
    def __init__(self):
        self.max_context_length = 4000
        self.context_priorities = {
            'conversation': 1.0,    # Priorité maximale au contexte conversationnel
            'calculation': 0.9,     # Calculs automatiques
            'meilisearch': 0.8,     # Recherche textuelle
            'supabase': 0.7         # Recherche vectorielle
        }
        
        # Patterns pour détecter les types d'informations
        self.info_patterns = {
            'product': r'(casque|produit|article).*?(rouge|bleu|noir|blanc)',
            'price': r'(\d+)\s*(?:fcfa|cfa|f)',
            'delivery': r'(livraison|yopougon|cocody|abidjan)',
            'payment': r'(wave|paiement|cod|\+225)',
            'total': r'(total|ensemble|combien)'
        }

    def fuse_contexts(self, supabase_results: List[Dict], meilisearch_results: List[Dict],
                     user_message: str, user_id: str, company_id: str) -> str:
        """
        🔗 Fusionne intelligemment tous les contextes disponibles
        """
        context_sources = []
        
        # 1. Récupérer le contexte conversationnel
        conversation_context = conversation_memory.generate_context_summary(user_id, company_id)
        if conversation_context:
            context_sources.append(ContextSource(
                source_type='conversation',
                content=conversation_context,
                relevance_score=1.0,
                metadata={'length': len(conversation_context)}
            ))
        
        # 2. Vérifier si calcul automatique nécessaire
        context = conversation_memory.get_or_create_context(user_id, company_id)
        if conversation_memory.should_auto_calculate_total(user_message, context):
            auto_calc = conversation_memory.get_auto_calculation_response(context)
            if auto_calc:
                context_sources.append(ContextSource(
                    source_type='calculation',
                    content=f"=== CALCUL AUTOMATIQUE ===\n{auto_calc}",
                    relevance_score=0.9,
                    metadata={'auto_generated': True}
                ))
        
        # 3. Traiter résultats MeiliSearch
        for i, result in enumerate(meilisearch_results[:3]):  # Top 3 seulement
            content = self._format_meilisearch_result(result, i+1)
            relevance = self._calculate_relevance(content, user_message)
            
            context_sources.append(ContextSource(
                source_type='meilisearch',
                content=content,
                relevance_score=relevance * 0.8,
                metadata={'index': i+1, 'result_type': result.get('type', 'unknown')}
            ))
        
        # 4. Traiter résultats Supabase
        for i, result in enumerate(supabase_results[:2]):  # Top 2 seulement
            content = self._format_supabase_result(result, i+1)
            relevance = self._calculate_relevance(content, user_message)
            
            context_sources.append(ContextSource(
                source_type='supabase',
                content=content,
                relevance_score=relevance * 0.7,
                metadata={'index': i+1, 'score': result.get('score', 0)}
            ))
        
        # 5. Trier par priorité et pertinence
        context_sources.sort(key=lambda x: (
            self.context_priorities.get(x.source_type, 0.5) * x.relevance_score
        ), reverse=True)
        
        # 6. Construire le contexte final
        final_context = self._build_final_context(context_sources, user_message)
        
        return final_context

    def _format_meilisearch_result(self, result: Dict, index: int) -> str:
        """Formate un résultat MeiliSearch"""
        result_type = result.get('type', 'document')
        content = result.get('content', result.get('searchable_text', ''))
        
        if result_type == 'product':
            return f"=== PRODUIT {index} ===\n{content}"
        elif result_type == 'delivery':
            return f"=== LIVRAISON {index} ===\n{content}"
        elif result_type == 'payment':
            return f"=== PAIEMENT {index} ===\n{content}"
        else:
            return f"=== DOCUMENT {index} ===\n{content}"

    def _format_supabase_result(self, result: Dict, index: int) -> str:
        """Formate un résultat Supabase"""
        content = result.get('content', '')
        score = result.get('score', 0)
        
        return f"=== CONTEXTE SÉMANTIQUE {index} (Score: {score}) ===\n{content}"

    def _calculate_relevance(self, content: str, user_message: str) -> float:
        """
        🎯 Calcule la pertinence d'un contenu par rapport au message utilisateur
        """
        content_lower = content.lower()
        message_lower = user_message.lower()
        
        relevance_score = 0.0
        
        # Vérifier correspondance directe des mots-clés
        message_words = set(re.findall(r'\b\w+\b', message_lower))
        content_words = set(re.findall(r'\b\w+\b', content_lower))
        
        # Score basé sur intersection des mots
        common_words = message_words.intersection(content_words)
        if message_words:
            word_overlap = len(common_words) / len(message_words)
            relevance_score += word_overlap * 0.4
        
        # Bonus pour types d'informations spécifiques
        for info_type, pattern in self.info_patterns.items():
            if re.search(pattern, message_lower) and re.search(pattern, content_lower):
                relevance_score += 0.3
        
        # Bonus pour informations critiques avec pondération
        critical_terms = {
            'prix': 0.15,
            'total': 0.15, 
            'livraison': 0.12,
            'casque': 0.10,
            'rouge': 0.08,
            'paiement': 0.10,
            'yopougon': 0.12
        }
        
        for term, weight in critical_terms.items():
            if term in message_lower and term in content_lower:
                relevance_score += weight
        
        # Pénalité pour contenu trop générique
        if len(content_lower) < 50:
            relevance_score *= 0.8
        
        return min(relevance_score, 1.0)

    def _build_final_context(self, context_sources: List[ContextSource], user_message: str) -> str:
        """
        🏗️ Construit le contexte final optimisé
        """
        final_parts = []
        current_length = 0
        
        # Ajouter un en-tête contextuel
        final_parts.append("=== CONTEXTE ENRICHI ===")
        current_length += len(final_parts[-1])
        
        # Ajouter les sources par ordre de priorité
        for source in context_sources:
            if current_length + len(source.content) > self.max_context_length:
                # Tronquer si nécessaire
                remaining_space = self.max_context_length - current_length - 50
                if remaining_space > 100:  # Seulement si assez d'espace
                    truncated_content = source.content[:remaining_space] + "..."
                    final_parts.append(truncated_content)
                break
            
            final_parts.append(source.content)
            current_length += len(source.content)
        
        # Ajouter métadonnées de débogage si nécessaire
        if len(context_sources) > 0:
            sources_used = [s.source_type for s in context_sources if any(s.content in part for part in final_parts)]
            final_parts.append(f"\n=== SOURCES UTILISÉES: {', '.join(set(sources_used))} ===")
        
        return "\n\n".join(final_parts)

    def enhance_with_smart_suggestions(self, context: str, user_message: str, 
                                     user_id: str, company_id: str) -> str:
        """
        💡 Enrichit le contexte avec des suggestions intelligentes et validation de cohérence
        """
        enhanced_context = context
        
        # Récupérer le contexte conversationnel
        conv_context = conversation_memory.get_or_create_context(user_id, company_id)
        
        suggestions = []
        
        # Validation de cohérence des prix
        product_price = conv_context.product_info.get('price')
        delivery_cost = conv_context.delivery_info.get('cost')
        
        # Suggestion de calcul automatique avec validation
        if (product_price and delivery_cost and 'total' in user_message.lower()):
            # Vérifier cohérence avec référence client si elle existe
            client_ref = conv_context.calculations.get('client_total_reference')
            calculated_total = product_price + delivery_cost
            
            if client_ref and abs(calculated_total - client_ref) < 100:  # Tolérance de 100 FCFA
                suggestions.append(f"✅ CALCUL COHÉRENT: {product_price} + {delivery_cost} = {calculated_total} FCFA (correspond à votre référence de {client_ref} FCFA)")
            else:
                suggestions.append(f"💡 CALCUL AUTOMATIQUE: {product_price} + {delivery_cost} = {calculated_total} FCFA")
        
        # Détection d'incohérences
        if conv_context.calculations.get('total') and conv_context.calculations.get('client_total_reference'):
            calc_total = conv_context.calculations['total']
            ref_total = conv_context.calculations['client_total_reference']
            if abs(calc_total - ref_total) > 100:
                suggestions.append(f"⚠️ INCOHÉRENCE DÉTECTÉE: Calcul automatique ({calc_total} FCFA) ≠ Référence client ({ref_total} FCFA)")
        
        # Suggestion d'informations manquantes
        if 'prix' in user_message.lower() and not product_price:
            suggestions.append("💡 INFO MANQUANTE: Prix du produit non encore communiqué")
        
        if 'livraison' in user_message.lower() and not conv_context.delivery_info.get('zone'):
            suggestions.append("💡 INFO MANQUANTE: Zone de livraison non précisée")
        
        # Ajouter suggestions au contexte
        if suggestions:
            enhanced_context += "\n\n=== SUGGESTIONS INTELLIGENTES ===\n" + "\n".join(suggestions)
        
        return enhanced_context

# Instance globale
smart_fusion = SmartContextFusion()

def fuse_all_contexts(supabase_results: List[Dict], meilisearch_results: List[Dict],
                     user_message: str, user_id: str, company_id: str) -> str:
    """
    🔗 Fonction utilitaire pour fusionner tous les contextes
    """
    return smart_fusion.fuse_contexts(
        supabase_results, meilisearch_results, user_message, user_id, company_id
    )

def enhance_context_with_suggestions(context: str, user_message: str, 
                                   user_id: str, company_id: str) -> str:
    """
    💡 Fonction utilitaire pour enrichir le contexte avec des suggestions
    """
    return smart_fusion.enhance_with_smart_suggestions(
        context, user_message, user_id, company_id
    )

if __name__ == "__main__":
    print("🔗 FUSION INTELLIGENTE DES CONTEXTES")
    print("=" * 50)
    print("Utilisation: from core.smart_context_fusion import fuse_all_contexts")
