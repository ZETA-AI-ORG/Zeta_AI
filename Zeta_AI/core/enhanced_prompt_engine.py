#!/usr/bin/env python3
"""
🚀 ENHANCED PROMPT ENGINE - SYSTÈME DE TEMPLATES SCALABLE
=========================================================

Architecture multi-niveaux pour exploitation optimale des entités extraites :
1. Détection automatique du type de question
2. Sélection du template approprié
3. Injection des entités structurées
4. Génération de réponse formatée

Scalable pour toutes entreprises e-commerce.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class QuestionType(Enum):
    """Types de questions e-commerce identifiés"""
    PRODUIT = "produit"
    PRIX = "prix" 
    LIVRAISON = "livraison"
    LOCALISATION = "localisation"
    PAIEMENT = "paiement"
    SAV = "sav"
    FAQ = "faq"
    CALCUL = "calcul"
    UNKNOWN = "unknown"

@dataclass
class EntityContext:
    """Contexte d'entités extraites structuré"""
    montants: List[str] = None
    zones: List[str] = None
    delais: List[str] = None
    produits: List[str] = None
    conditions: List[str] = None
    contacts: List[str] = None
    
    def __post_init__(self):
        # Initialiser les listes vides si None
        for field in ['montants', 'zones', 'delais', 'produits', 'conditions', 'contacts']:
            if getattr(self, field) is None:
                setattr(self, field, [])

class EnhancedPromptEngine:
    """
    🧠 MOTEUR DE PROMPTS ENHANCED
    
    Fonctionnalités :
    - Détection automatique du type de question
    - Templates spécialisés par catégorie
    - Injection intelligente des entités
    - Validation des réponses
    """
    
    def __init__(self):
        self.question_patterns = self._init_question_patterns()
        self.response_templates = self._init_response_templates()
        self.validation_rules = self._init_validation_rules()
    
    def _init_question_patterns(self) -> Dict[QuestionType, List[str]]:
        """🔍 Patterns de détection des types de questions"""
        return {
            QuestionType.PRIX: [
                r'\b(prix|coût|coûte|tarif|montant)\b',
                r'\b(combien|quel.*prix)\b',
                r'\b(\d+.*fcfa|fcfa)\b',
                r'\b(économie|remise|promotion)\b'
            ],
            QuestionType.LIVRAISON: [
                r'\b(livraison|livrer|expédition|délai)\b',
                r'\b(quand.*livré|combien.*temps)\b',
                r'\b(zone.*livraison|livraison.*possible)\b',
                r'\b(frais.*livraison|coût.*livraison)\b'
            ],
            QuestionType.PRODUIT: [
                r'\b(produit|article|couches|taille)\b',
                r'\b(disponible|stock|catalogue)\b',
                r'\b(recommandez|conseiller|adapter|meilleur|préféré|recommande|conseil|top|plus adapté|plus vendu|best seller)\b',
                r'\b(caractéristique|spécification)\b'
            ],
            QuestionType.LOCALISATION: [
                r'\b(adresse|localisation|boutique|magasin)\b',
                r'\b(où.*situé|où.*trouver)\b',
                r'\b(horaires|ouvert|fermé)\b',
                r'\b(zone.*service|secteur)\b'
            ],
            QuestionType.PAIEMENT: [
                r'\b(paiement|payer|acompte|wave)\b',
                r'\b(mode.*paiement|comment.*payer)\b',
                r'\b(facture|reçu|transaction)\b',
                r'\b(sécurisé|sécurité)\b'
            ],
            QuestionType.SAV: [
                r'\b(retour|échange|garantie|réclamation)\b',
                r'\b(problème|défaut|cassé)\b',
                r'\b(support|aide|assistance)\b',
                r'\b(remboursement|annulation)\b'
            ],
            QuestionType.CALCUL: [
                r'\b(total|calculer|somme)\b',
                r'\b(\d+.*paquet.*\+.*livraison)\b',
                r'\b(économie.*réalisée|différence)\b',
                r'\b(comparaison|vs|versus)\b'
            ]
        }
    
    def _init_response_templates(self) -> Dict[QuestionType, str]:
        """📋 Templates de réponse par type de question"""
        return {
            QuestionType.PRIX: """
🏷️ **INFORMATIONS TARIFAIRES**

{prix_details}

{calculs_automatiques}

{conditions_speciales}

📞 **Contact** : {contact_info}
""",
            
            QuestionType.LIVRAISON: """
🚚 **INFORMATIONS LIVRAISON**

📍 **Votre zone** : {zone_client}
💰 **Tarif** : {tarif_livraison}
⏰ **Délai** : {delai_livraison}

{conditions_livraison}

📞 **Suivi** : {contact_info}
""",
            
            QuestionType.PRODUIT: """
🛍️ **INFORMATIONS PRODUIT**

{produit_details}

{recommandations}

{disponibilite}

📞 **Conseil** : {contact_info}
""",
            
            QuestionType.CALCUL: """
🧮 **CALCUL DÉTAILLÉ**

{breakdown_calcul}

💰 **Total** : {montant_total}
{economie_info}

📞 **Confirmation** : {contact_info}
""",
            
            QuestionType.LOCALISATION: """
📍 **INFORMATIONS BOUTIQUE**

{adresse_info}
{horaires_info}
{zones_service}

📞 **Contact** : {contact_info}
""",
            
            QuestionType.PAIEMENT: """
💳 **INFORMATIONS PAIEMENT**

{modes_paiement}
{conditions_acompte}
{securite_info}

📞 **Support** : {contact_info}
""",
            
            QuestionType.SAV: """
🔄 **SERVICE APRÈS-VENTE**

{politique_retour}
{garanties}
{procedure_reclamation}

📞 **Support** : {contact_info}
"""
        }
    
    def _init_validation_rules(self) -> Dict[QuestionType, List[str]]:
        """✅ Règles de validation par type"""
        return {
            QuestionType.PRIX: [
                "Montant en FCFA mentionné",
                "Source des données indiquée",
                "Conditions tarifaires précisées"
            ],
            QuestionType.LIVRAISON: [
                "Zone géographique identifiée", 
                "Tarif de livraison précisé",
                "Délai de livraison indiqué"
            ],
            QuestionType.CALCUL: [
                "Calcul détaillé fourni",
                "Total final correct",
                "Économies calculées si applicable"
            ]
        }
    
    def detect_question_type(self, query: str) -> Tuple[QuestionType, float]:
        """🔍 Détecte le type de question avec score de confiance"""
        query_lower = query.lower()
        scores = {}
        
        for question_type, patterns in self.question_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query_lower))
                score += matches
            
            if score > 0:
                scores[question_type] = score
        
        if not scores:
            return QuestionType.UNKNOWN, 0.0
        
        # Type avec le meilleur score
        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]
        confidence = min(max_score / 3.0, 1.0)  # Normalisation
        
        return best_type, confidence
    
    def extract_entities_from_context(self, context: str) -> EntityContext:
        """🧠 Extrait et structure les entités du contexte"""
        entity_context = EntityContext()
        
        # Extraction des montants FCFA
        montant_pattern = r'(\d+(?:\.\d+)?)\s*F?\s*CFA'
        entity_context.montants = re.findall(montant_pattern, context)
        
        # Extraction des zones géographiques
        zone_pattern = r'\b(yopougon|cocody|plateau|adjamé|abobo|marcory|koumassi|treichville|angré|riviera|bingerville|port-bouët|attécoubé|songon|anyama|grand-bassam|dabou)\b'
        entity_context.zones = re.findall(zone_pattern, context, re.IGNORECASE)
        
        # Extraction des délais
        delai_pattern = r'\b(jour même|lendemain|\d+h?|\d+\s*jours?|24h|48h|72h)\b'
        entity_context.delais = re.findall(delai_pattern, context, re.IGNORECASE)
        
        # Extraction des produits
        produit_pattern = r'\b(couches?|paquet|taille \d+|adultes?|culottes?|pression)\b'
        entity_context.produits = re.findall(produit_pattern, context, re.IGNORECASE)
        
        # Extraction des contacts
        contact_pattern = r'(\+225\d{8,10}|wave|whatsapp)'
        entity_context.contacts = re.findall(contact_pattern, context, re.IGNORECASE)
        
        return entity_context
    
    def generate_enhanced_prompt(
        self, 
        query: str, 
        context: str, 
        base_prompt: str,
        company_name: str = "Notre entreprise"
    ) -> str:
        """🚀 Génère le prompt enhanced avec templates et entités"""
        
        # 1. Détection du type de question
        question_type, confidence = self.detect_question_type(query)
        
        # 2. Extraction des entités
        entities = self.extract_entities_from_context(context)
        
        # 3. Sélection du template
        if question_type in self.response_templates:
            response_template = self.response_templates[question_type]
        else:
            response_template = self._get_default_template()
        
        # 4. Préparation des variables de template
        template_vars = self._prepare_template_variables(
            question_type, entities, context, company_name
        )
        
        # 5. Construction du prompt enhanced
        enhanced_prompt = f"""{base_prompt}

🎯 **TYPE DE QUESTION DÉTECTÉ** : {question_type.value.upper()} (Confiance: {confidence:.2f})

🧠 **ENTITÉS EXTRAITES** :
{self._format_entities(entities)}

📋 **TEMPLATE DE RÉPONSE À UTILISER** :
{response_template}

🔧 **VARIABLES DISPONIBLES** :
{self._format_template_vars(template_vars)}

⚠️ **RÈGLES STRICTES** :
1. Utilise UNIQUEMENT les entités extraites ci-dessus
2. Respecte EXACTEMENT le template de réponse
3. Remplace les variables {{variable}} par les valeurs extraites
4. Si une information manque, indique "Information non disponible"
5. Mentionne toujours la source : "Selon nos informations..."

QUESTION: {query}

CONTEXTE BRUT:
{context}

RÉPONSE STRUCTURÉE:"""
        
        return enhanced_prompt
    
    def _get_default_template(self) -> str:
        """📋 Template par défaut pour questions non catégorisées"""
        return """
ℹ️ **INFORMATIONS DISPONIBLES**

{informations_pertinentes}

📞 **Contact** : {contact_info}

💡 **Suggestion** : Pour une réponse plus précise, n'hésitez pas à reformuler votre question.
"""
    
    def _prepare_template_variables(
        self, 
        question_type: QuestionType, 
        entities: EntityContext, 
        context: str,
        company_name: str
    ) -> Dict[str, str]:
        """🔧 Prépare les variables pour le template"""
        
        base_vars = {
            "company_name": company_name,
            "contact_info": self._format_contact_info(entities.contacts),
            "informations_pertinentes": self._extract_relevant_info(context)
        }
        
        if question_type == QuestionType.PRIX:
            base_vars.update({
                "prix_details": self._format_prix_details(entities.montants),
                "calculs_automatiques": self._generate_calculs(entities.montants),
                "conditions_speciales": "Acompte de 2000 FCFA requis"
            })
        
        elif question_type == QuestionType.LIVRAISON:
            base_vars.update({
                "zone_client": ", ".join(entities.zones) if entities.zones else "À préciser",
                "tarif_livraison": self._get_tarif_livraison(entities.zones, entities.montants),
                "delai_livraison": ", ".join(entities.delais) if entities.delais else "À confirmer",
                "conditions_livraison": self._get_conditions_livraison(entities.zones)
            })
        
        elif question_type == QuestionType.CALCUL:
            base_vars.update({
                "breakdown_calcul": self._generate_breakdown(entities.montants),
                "montant_total": self._calculate_total(entities.montants),
                "economie_info": self._calculate_economies(entities.montants)
            })
        
        return base_vars
    
    def _format_entities(self, entities: EntityContext) -> str:
        """📊 Formate les entités pour affichage"""
        formatted = []
        
        if entities.montants:
            formatted.append(f"💰 Montants: {', '.join(entities.montants)} FCFA")
        if entities.zones:
            formatted.append(f"📍 Zones: {', '.join(set(entities.zones))}")
        if entities.delais:
            formatted.append(f"⏰ Délais: {', '.join(set(entities.delais))}")
        if entities.produits:
            formatted.append(f"🛍️ Produits: {', '.join(set(entities.produits))}")
        if entities.contacts:
            formatted.append(f"📞 Contacts: {', '.join(set(entities.contacts))}")
        
        return "\n".join(formatted) if formatted else "Aucune entité spécifique extraite"
    
    def _format_template_vars(self, template_vars: Dict[str, str]) -> str:
        """🔧 Formate les variables de template"""
        formatted = []
        for key, value in template_vars.items():
            formatted.append(f"• {{{key}}} = {value}")
        return "\n".join(formatted)
    
    def _format_contact_info(self, contacts: List[str]) -> str:
        """📞 Formate les informations de contact"""
        if not contacts:
            return "Contactez notre service client"
        
        formatted_contacts = []
        for contact in contacts:
            if contact.startswith('+225'):
                formatted_contacts.append(f"📱 {contact}")
            elif 'wave' in contact.lower():
                formatted_contacts.append(f"💳 Wave: +2250787360757")
            elif 'whatsapp' in contact.lower():
                formatted_contacts.append(f"💬 WhatsApp: +2250160924560")
        
        return " | ".join(formatted_contacts) if formatted_contacts else "Service client disponible"
    
    def _format_prix_details(self, montants: List[str]) -> str:
        """💰 Formate les détails de prix"""
        if not montants:
            return "Prix à confirmer selon le produit sélectionné"
        
        prix_info = []
        for montant in montants:
            prix_info.append(f"• {montant} FCFA")
        
        return "\n".join(prix_info)
    
    def _get_tarif_livraison(self, zones: List[str], montants: List[str]) -> str:
        """🚚 Détermine le tarif de livraison selon la zone"""
        if not zones:
            return "Tarif à confirmer selon votre localisation"
        
        zone = zones[0].lower()
        
        # Zones centrales
        zones_centrales = ['yopougon', 'cocody', 'plateau', 'adjamé', 'abobo', 'marcory', 'koumassi', 'treichville', 'angré', 'riviera']
        if zone in zones_centrales:
            return "1500 FCFA"
        
        # Zones périphériques  
        zones_peripheriques = ['bingerville', 'port-bouët', 'attécoubé', 'songon', 'anyama', 'grand-bassam', 'dabou']
        if zone in zones_peripheriques:
            return "2000-2500 FCFA"
        
        return "3500-5000 FCFA (hors Abidjan)"
    
    def _get_conditions_livraison(self, zones: List[str]) -> str:
        """📋 Conditions de livraison selon la zone"""
        if not zones:
            return "Conditions à préciser selon votre zone"
        
        return """
• Commande avant 11h → Livraison jour même
• Commande après 11h → Livraison lendemain (jour ouvré)
• Suivi par SMS/WhatsApp inclus
"""
    
    def _generate_calculs(self, montants: List[str]) -> str:
        """🧮 Génère des calculs automatiques"""
        if len(montants) < 2:
            return "Calculs disponibles sur demande"
        
        try:
            # Exemple de calcul simple
            values = [float(m.replace(',', '.')) for m in montants if m.replace(',', '.').replace('.', '').isdigit()]
            if len(values) >= 2:
                total = sum(values)
                return f"Calcul automatique: {' + '.join(montants)} = {total:,.0f} FCFA"
        except:
            pass
        
        return "Calculs personnalisés disponibles"
    
    def _generate_breakdown(self, montants: List[str]) -> str:
        """📊 Génère un breakdown détaillé"""
        if not montants:
            return "Détail du calcul à préciser"
        
        breakdown = []
        for i, montant in enumerate(montants, 1):
            breakdown.append(f"Élément {i}: {montant} FCFA")
        
        return "\n".join(breakdown)
    
    def _calculate_total(self, montants: List[str]) -> str:
        """💰 Calcule le total"""
        try:
            values = [float(m.replace(',', '.')) for m in montants if m.replace(',', '.').replace('.', '').isdigit()]
            if values:
                total = sum(values)
                return f"{total:,.0f} FCFA"
        except:
            pass
        
        return "Total à calculer"
    
    def _calculate_economies(self, montants: List[str]) -> str:
        """💡 Calcule les économies potentielles"""
        if len(montants) >= 2:
            return "\n💡 **Économie possible** : Consultez nos offres en gros pour des tarifs préférentiels"
        return ""
    
    def _extract_relevant_info(self, context: str) -> str:
        """ℹ️ Extrait les informations les plus pertinentes"""
        # Extraction des phrases contenant des informations clés
        sentences = context.split('.')
        relevant = []
        
        keywords = ['prix', 'livraison', 'zone', 'tarif', 'délai', 'fcfa', 'paquet', 'couches']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                relevant.append(sentence.strip())
        
        return "\n".join(relevant[:3]) if relevant else "Informations détaillées disponibles sur demande"

# Instance globale pour utilisation
enhanced_prompt_engine = EnhancedPromptEngine()
