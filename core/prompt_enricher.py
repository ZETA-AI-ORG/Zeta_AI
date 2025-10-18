#!/usr/bin/env python3
"""
🎯 ENRICHISSEUR DE PROMPTS INTELLIGENT
Enrichit les prompts LLM avec intentions, entités, contexte structuré et reasoning explicite
Optimisé pour la compréhension française et le e-commerce
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PromptTemplate(Enum):
    """Templates de prompts spécialisés"""
    PRODUCT_INQUIRY = "product_inquiry"
    PRICE_INQUIRY = "price_inquiry"
    ORDER_INTENT = "order_intent"
    DELIVERY_INQUIRY = "delivery_inquiry"
    PAYMENT_INQUIRY = "payment_inquiry"
    SIZE_INQUIRY = "size_inquiry"
    AVAILABILITY_INQUIRY = "availability_inquiry"
    SUPPORT_GENERAL = "support_general"
    MULTI_INTENT = "multi_intent"

@dataclass
class EnrichedPrompt:
    """Prompt enrichi avec métadonnées"""
    system_prompt: str
    user_prompt: str
    context_structured: str
    reasoning_chain: List[str]
    confidence: float
    template_used: str
    enrichment_metadata: Dict[str, Any]

class PromptEnricher:
    """
    🎯 ENRICHISSEUR DE PROMPTS INTELLIGENT
    
    Fonctionnalités :
    - Templates spécialisés par type d'intention
    - Injection intelligente d'entités extraites
    - Reasoning explicite pour le LLM
    - Contexte structuré et hiérarchisé
    - Adaptation dynamique selon la complexité
    """
    
    def __init__(self):
        self.templates = self._init_templates()
        self.reasoning_patterns = self._init_reasoning_patterns()
        
        # Entités critiques pour e-commerce
        self.critical_entities = {
            'PRODUCT_TYPE': ['couches', 'culottes', 'pression', 'adultes', 'bébé'],
            'QUANTITY': ['paquet', 'lot', 'pièce', 'unité', 'colis'],
            'SIZE': ['taille', 'pointure', 'dimension'],
            'LOCATION': ['cocody', 'yopougon', 'abidjan', 'plateau', 'adjamé'],
            'PRICE': ['fcfa', 'prix', 'coût', 'tarif'],
            'PHONE': ['+225', 'téléphone', 'numéro'],
            'PAYMENT': ['wave', 'mobile money', 'paiement', 'acompte']
        }
    
    def _init_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialise les templates de prompts spécialisés"""
        return {
            PromptTemplate.PRODUCT_INQUIRY.value: {
                "system": """Tu es {ai_name}, assistant IA spécialisé de {company_name} dans le secteur {business_sector}.

🎯 INTENTION DÉTECTÉE: Demande d'information produit
📊 ENTITÉS EXTRAITES: {entities_formatted}
🔍 CONTEXTE STRUCTURÉ DISPONIBLE

INSTRUCTIONS SPÉCIFIQUES:
1. Présente les produits disponibles de manière claire et organisée
2. Utilise les entités extraites pour personnaliser la réponse
3. Inclus les informations de stock si disponibles
4. Propose des alternatives si le produit exact n'est pas trouvé
5. Termine par une question d'engagement pour continuer la conversation

STYLE: Professionnel, informatif, orienté vente""",
                
                "user": """REQUÊTE CLIENT: "{original_query}"

ANALYSE AUTOMATIQUE:
- Type de question: {question_type}
- Intentions détectées: {intentions_list}
- Entités clés: {key_entities}
- Confiance NLP: {nlp_confidence}%

CONTEXTE PRODUITS:
{structured_context}

RAISONNEMENT REQUIS:
{reasoning_chain}

Réponds de manière précise en exploitant toutes les informations contextuelles."""
            },
            
            PromptTemplate.PRICE_INQUIRY.value: {
                "system": """Tu es {ai_name}, assistant IA de {company_name} spécialisé dans les tarifs et devis.

🎯 INTENTION DÉTECTÉE: Demande de prix/tarification
💰 ENTITÉS PRIX EXTRAITES: {price_entities}
📊 CALCULS AUTOMATIQUES REQUIS

INSTRUCTIONS SPÉCIFIQUES:
1. Fournis les prix exacts selon les quantités demandées
2. Calcule automatiquement les totaux et économies
3. Inclus les frais de livraison selon la zone
4. Propose des offres groupées avantageuses
5. Mentionne les modalités de paiement (Wave, acompte)
6. Termine par un récapitulatif clair du devis

STYLE: Précis, transparent, commercial""",
                
                "user": """DEMANDE DE PRIX: "{original_query}"

ANALYSE TARIFAIRE:
- Produits identifiés: {product_entities}
- Quantités: {quantity_entities}
- Zone livraison: {location_entities}
- Type de calcul: {calculation_type}

CONTEXTE PRIX:
{structured_context}

CALCULS À EFFECTUER:
{reasoning_chain}

Fournis un devis détaillé et précis."""
            },
            
            PromptTemplate.DELIVERY_INQUIRY.value: {
                "system": """Tu es {ai_name}, assistant IA de {company_name} expert en logistique et livraison.

🎯 INTENTION DÉTECTÉE: Question sur la livraison
🚚 ZONES ET TARIFS DE LIVRAISON DISPONIBLES
⏰ DÉLAIS ET CONDITIONS SPÉCIFIQUES

INSTRUCTIONS SPÉCIFIQUES:
1. Identifie précisément la zone de livraison demandée
2. Fournis les tarifs exacts selon la zone
3. Explique les délais (avant/après 11h)
4. Mentionne les conditions spéciales si applicable
5. Propose des alternatives si la zone est éloignée

STYLE: Informatif, rassurant, logistique""",
                
                "user": """QUESTION LIVRAISON: "{original_query}"

ANALYSE GÉOGRAPHIQUE:
- Zones mentionnées: {location_entities}
- Type de livraison: {delivery_type}
- Urgence détectée: {urgency_level}

CONTEXTE LIVRAISON:
{structured_context}

RAISONNEMENT LOGISTIQUE:
{reasoning_chain}

Réponds avec les informations de livraison précises."""
            },
            
            PromptTemplate.MULTI_INTENT.value: {
                "system": """Tu es {ai_name}, assistant IA polyvalent de {company_name}.

🎯 INTENTIONS MULTIPLES DÉTECTÉES: {intentions_count} intentions
🔀 TRAITEMENT SÉQUENTIEL REQUIS
📊 ENTITÉS COMPLEXES EXTRAITES

INSTRUCTIONS SPÉCIFIQUES:
1. Traite chaque intention dans l'ordre de priorité
2. Structure ta réponse en sections claires
3. Utilise les entités pour personnaliser chaque section
4. Assure la cohérence entre les différentes parties
5. Termine par une synthèse et prochaines étapes

STYLE: Structuré, complet, professionnel""",
                
                "user": """REQUÊTE COMPLEXE: "{original_query}"

ANALYSE MULTI-INTENTIONS:
- Intentions détectées: {intentions_detailed}
- Entités partagées: {shared_entities}
- Priorité de traitement: {processing_order}

CONTEXTE GLOBAL:
{structured_context}

PLAN DE RÉPONSE:
{reasoning_chain}

Traite toutes les intentions de manière structurée et cohérente."""
            }
        }
    
    def _init_reasoning_patterns(self) -> Dict[str, List[str]]:
        """Initialise les patterns de raisonnement"""
        return {
            'product_inquiry': [
                "1. Identifier les produits mentionnés dans la requête",
                "2. Vérifier la disponibilité en stock",
                "3. Présenter les caractéristiques principales",
                "4. Proposer des alternatives si nécessaire",
                "5. Engager pour la suite (prix, commande)"
            ],
            'price_inquiry': [
                "1. Extraire les quantités et produits demandés",
                "2. Calculer les prix unitaires et totaux",
                "3. Ajouter les frais de livraison selon la zone",
                "4. Calculer les économies sur les lots",
                "5. Présenter un devis clair et détaillé"
            ],
            'delivery_inquiry': [
                "1. Identifier la zone de livraison exacte",
                "2. Déterminer les tarifs selon la zone",
                "3. Calculer les délais selon l'heure de commande",
                "4. Expliquer les conditions de livraison",
                "5. Proposer des options si nécessaire"
            ],
            'multi_intent': [
                "1. Prioriser les intentions par importance",
                "2. Traiter chaque intention séquentiellement",
                "3. Maintenir la cohérence entre les réponses",
                "4. Synthétiser les informations communes",
                "5. Proposer une action globale"
            ]
        }
    
    def detect_prompt_template(self, intentions: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> str:
        """Détecte le template de prompt optimal"""
        if not intentions:
            return PromptTemplate.SUPPORT_GENERAL.value
        
        # Multi-intentions
        if len(intentions) > 1:
            return PromptTemplate.MULTI_INTENT.value
        
        # Intention principale
        main_intent = intentions[0]['intent']
        
        # Mapping direct
        template_mapping = {
            'product_inquiry': PromptTemplate.PRODUCT_INQUIRY.value,
            'price_inquiry': PromptTemplate.PRICE_INQUIRY.value,
            'order_intent': PromptTemplate.ORDER_INTENT.value,
            'delivery_inquiry': PromptTemplate.DELIVERY_INQUIRY.value,
            'payment_inquiry': PromptTemplate.PAYMENT_INQUIRY.value,
            'size_inquiry': PromptTemplate.SIZE_INQUIRY.value,
            'availability_inquiry': PromptTemplate.AVAILABILITY_INQUIRY.value
        }
        
        return template_mapping.get(main_intent, PromptTemplate.SUPPORT_GENERAL.value)
    
    def format_entities_for_prompt(self, entities: List[Dict[str, Any]]) -> Dict[str, str]:
        """Formate les entités pour injection dans les prompts"""
        formatted = {
            'entities_formatted': '',
            'price_entities': '',
            'product_entities': '',
            'quantity_entities': '',
            'location_entities': '',
            'key_entities': ''
        }
        
        if not entities:
            return formatted
        
        # Groupement par type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get('type', 'UNKNOWN')
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity.get('entity', ''))
        
        # Formatage général
        formatted_parts = []
        for entity_type, values in entities_by_type.items():
            unique_values = list(set(values))
            formatted_parts.append(f"{entity_type}: {', '.join(unique_values)}")
        
        formatted['entities_formatted'] = ' | '.join(formatted_parts)
        
        # Formatage spécialisé
        formatted['price_entities'] = ', '.join(entities_by_type.get('PRICE', []))
        formatted['product_entities'] = ', '.join(entities_by_type.get('PRODUCT_TYPE', []))
        formatted['quantity_entities'] = ', '.join(entities_by_type.get('QUANTITY', []))
        formatted['location_entities'] = ', '.join(entities_by_type.get('LOCATION', []))
        
        # Entités clés (les plus importantes)
        key_entities = []
        for entity_type in ['PRODUCT_TYPE', 'QUANTITY', 'PRICE', 'LOCATION']:
            if entity_type in entities_by_type:
                key_entities.extend(entities_by_type[entity_type][:2])  # Max 2 par type
        
        formatted['key_entities'] = ', '.join(key_entities[:5])  # Max 5 entités clés
        
        return formatted
    
    def format_intentions_for_prompt(self, intentions: List[Dict[str, Any]]) -> Dict[str, str]:
        """Formate les intentions pour injection dans les prompts"""
        formatted = {
            'intentions_list': '',
            'intentions_detailed': '',
            'intentions_count': '0',
            'processing_order': ''
        }
        
        if not intentions:
            return formatted
        
        # Liste simple
        intent_names = [intent.get('intent', 'unknown') for intent in intentions]
        formatted['intentions_list'] = ', '.join(intent_names)
        formatted['intentions_count'] = str(len(intentions))
        
        # Détails avec confiance
        detailed_parts = []
        for intent in intentions:
            name = intent.get('intent', 'unknown')
            confidence = intent.get('confidence', 0)
            detailed_parts.append(f"{name} ({confidence:.1%})")
        
        formatted['intentions_detailed'] = ' | '.join(detailed_parts)
        
        # Ordre de traitement (par confiance décroissante)
        sorted_intents = sorted(intentions, key=lambda x: x.get('confidence', 0), reverse=True)
        processing_order = [intent.get('intent', 'unknown') for intent in sorted_intents]
        formatted['processing_order'] = ' → '.join(processing_order)
        
        return formatted
    
    def build_reasoning_chain(self, template: str, intentions: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[str]:
        """Construit la chaîne de raisonnement"""
        base_reasoning = self.reasoning_patterns.get(template, [
            "1. Analyser la requête client",
            "2. Identifier les informations pertinentes",
            "3. Structurer la réponse",
            "4. Vérifier la cohérence",
            "5. Proposer une action"
        ])
        
        # Adaptation selon les entités
        enhanced_reasoning = base_reasoning.copy()
        
        # Ajouts spécifiques selon les entités présentes
        entity_types = [e.get('type') for e in entities]
        
        if 'PRICE' in entity_types and 'QUANTITY' in entity_types:
            enhanced_reasoning.append("6. Calculer les totaux et économies potentielles")
        
        if 'LOCATION' in entity_types:
            enhanced_reasoning.append("7. Adapter selon la zone géographique")
        
        if len(intentions) > 1:
            enhanced_reasoning.insert(1, "1.5. Prioriser les intentions multiples")
        
        return enhanced_reasoning
    
    def structure_context_hierarchical(self, context: str, intentions: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> str:
        """Structure le contexte de manière hiérarchique"""
        if not context:
            return "Aucun contexte spécifique disponible."
        
        # Détection des sections dans le contexte
        sections = []
        current_section = ""
        
        for line in context.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Détection d'en-têtes (lignes avec ===, ---, etc.)
            if any(marker in line for marker in ['===', '---', '###', '***']):
                if current_section:
                    sections.append(current_section)
                current_section = f"\n{line}\n"
            else:
                current_section += f"{line}\n"
        
        if current_section:
            sections.append(current_section)
        
        # Si pas de structure détectée, créer une structure basique
        if len(sections) <= 1:
            return f"📄 CONTEXTE DISPONIBLE:\n{context}"
        
        # Priorisation des sections selon les intentions
        prioritized_sections = []
        for section in sections:
            priority = self._calculate_section_priority(section, intentions, entities)
            prioritized_sections.append((priority, section))
        
        # Tri par priorité décroissante
        prioritized_sections.sort(key=lambda x: x[0], reverse=True)
        
        # Reconstruction hiérarchique
        structured = "📊 CONTEXTE STRUCTURÉ PAR PERTINENCE:\n\n"
        for i, (priority, section) in enumerate(prioritized_sections[:5], 1):  # Max 5 sections
            structured += f"🔹 SECTION {i} (Pertinence: {priority:.1f}):\n{section}\n"
        
        return structured
    
    def _calculate_section_priority(self, section: str, intentions: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> float:
        """Calcule la priorité d'une section selon les intentions/entités"""
        priority = 0.0
        section_lower = section.lower()
        
        # Bonus selon les intentions
        for intent in intentions:
            intent_name = intent.get('intent', '')
            confidence = intent.get('confidence', 0)
            
            if intent_name == 'product_inquiry' and any(word in section_lower for word in ['produit', 'article', 'stock']):
                priority += confidence * 2.0
            elif intent_name == 'price_inquiry' and any(word in section_lower for word in ['prix', 'fcfa', 'tarif']):
                priority += confidence * 2.0
            elif intent_name == 'delivery_inquiry' and any(word in section_lower for word in ['livraison', 'zone', 'délai']):
                priority += confidence * 2.0
        
        # Bonus selon les entités
        for entity in entities:
            entity_text = entity.get('entity', '').lower()
            if entity_text and entity_text in section_lower:
                priority += entity.get('confidence', 0.5)
        
        # Bonus pour longueur appropriée
        section_length = len(section)
        if 100 <= section_length <= 800:  # Longueur optimale
            priority += 0.5
        
        return priority
    
    def enrich_prompt(
        self, 
        original_query: str,
        base_context: str,
        intentions: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        company_info: Dict[str, Any]
    ) -> EnrichedPrompt:
        """
        🎯 ENRICHISSEMENT PRINCIPAL DU PROMPT
        
        Combine toutes les techniques d'enrichissement
        """
        logger.info(f"🎯 [PROMPT_ENRICH] Début enrichissement: '{original_query[:50]}...'")
        
        # 1. Détection du template optimal
        template = self.detect_prompt_template(intentions, entities)
        
        # 2. Formatage des entités et intentions
        entities_formatted = self.format_entities_for_prompt(entities)
        intentions_formatted = self.format_intentions_for_prompt(intentions)
        
        # 3. Construction de la chaîne de raisonnement
        reasoning_chain = self.build_reasoning_chain(template, intentions, entities)
        
        # 4. Structure hiérarchique du contexte
        structured_context = self.structure_context_hierarchical(base_context, intentions, entities)
        
        # 5. Variables pour injection
        template_vars = {
            'ai_name': company_info.get('ai_name', 'Assistant IA'),
            'company_name': company_info.get('company_name', 'Notre entreprise'),
            'business_sector': company_info.get('business_sector', 'Commerce'),
            'original_query': original_query,
            'structured_context': structured_context,
            'reasoning_chain': '\n'.join(f"   {step}" for step in reasoning_chain),
            'question_type': template.replace('_', ' ').title(),
            'nlp_confidence': int(sum(i.get('confidence', 0) for i in intentions) / len(intentions) * 100) if intentions else 50,
            **entities_formatted,
            **intentions_formatted
        }
        
        # 6. Génération des prompts
        template_data = self.templates.get(template, self.templates[PromptTemplate.SUPPORT_GENERAL.value])
        
        system_prompt = template_data.get('system', '').format(**template_vars)
        user_prompt = template_data.get('user', '').format(**template_vars)
        
        # 7. Calcul de confiance
        confidence = self._calculate_enrichment_confidence(intentions, entities, len(structured_context))
        
        # 8. Métadonnées d'enrichissement
        enrichment_metadata = {
            'template_used': template,
            'entities_count': len(entities),
            'intentions_count': len(intentions),
            'context_length': len(structured_context),
            'reasoning_steps': len(reasoning_chain),
            'variables_injected': len(template_vars)
        }
        
        logger.info(f"🎯 [PROMPT_ENRICH] Terminé: template={template}, confiance={confidence:.2f}")
        
        return EnrichedPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_structured=structured_context,
            reasoning_chain=reasoning_chain,
            confidence=confidence,
            template_used=template,
            enrichment_metadata=enrichment_metadata
        )
    
    def _calculate_enrichment_confidence(self, intentions: List[Dict[str, Any]], entities: List[Dict[str, Any]], context_length: int) -> float:
        """Calcule la confiance de l'enrichissement"""
        confidence = 0.5  # Base
        
        # Bonus intentions
        if intentions:
            avg_intent_confidence = sum(i.get('confidence', 0) for i in intentions) / len(intentions)
            confidence += avg_intent_confidence * 0.3
        
        # Bonus entités
        if entities:
            avg_entity_confidence = sum(e.get('confidence', 0) for e in entities) / len(entities)
            confidence += avg_entity_confidence * 0.2
        
        # Bonus contexte
        if context_length > 500:
            confidence += 0.1
        if context_length > 1500:
            confidence += 0.1
        
        return min(confidence, 1.0)

# Instance globale
prompt_enricher = PromptEnricher()

# Interface simple
def enrich_llm_prompt(
    query: str,
    context: str,
    intentions: List[Dict[str, Any]],
    entities: List[Dict[str, Any]],
    company_info: Dict[str, Any]
) -> EnrichedPrompt:
    """Interface simple pour enrichissement de prompt"""
    return prompt_enricher.enrich_prompt(query, context, intentions, entities, company_info)

if __name__ == "__main__":
    # Test d'enrichissement
    test_query = "Je veux commander 3 paquets de couches taille 2 et combien pour livraison à Cocody?"
    test_context = "=== PRODUITS ===\nCouches taille 2: 18.900 FCFA\n=== LIVRAISON ===\nCocody: 1500 FCFA"
    test_intentions = [
        {"intent": "order_intent", "confidence": 0.8},
        {"intent": "price_inquiry", "confidence": 0.7},
        {"intent": "delivery_inquiry", "confidence": 0.6}
    ]
    test_entities = [
        {"entity": "3 paquets", "type": "QUANTITY", "confidence": 0.9},
        {"entity": "taille 2", "type": "SIZE", "confidence": 0.8},
        {"entity": "Cocody", "type": "LOCATION", "confidence": 0.9}
    ]
    test_company = {
        "ai_name": "Jessica",
        "company_name": "Rue du Gros",
        "business_sector": "Bébé & Puériculture"
    }
    
    enriched = enrich_llm_prompt(test_query, test_context, test_intentions, test_entities, test_company)
    
    print(f"\n{'='*60}")
    print(f"TEST ENRICHISSEMENT PROMPT")
    print('='*60)
    print(f"Template: {enriched.template_used}")
    print(f"Confiance: {enriched.confidence:.2f}")
    print(f"Reasoning: {len(enriched.reasoning_chain)} étapes")
    print(f"\nSYSTEM PROMPT:\n{enriched.system_prompt[:200]}...")
    print(f"\nUSER PROMPT:\n{enriched.user_prompt[:200]}...")
