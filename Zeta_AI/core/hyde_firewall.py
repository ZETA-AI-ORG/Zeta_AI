"""
HyDE Pare-feu (Firewall Anti-Hallucination)
Module de contrôle et validation de la cohérence des réponses LLM.
Analyse la question utilisateur, l'historique et la réponse pour détecter les hallucinations.
"""

import re
from typing import Dict, Any, Tuple, Optional
from utils import log3, timing_metric
from core.llm_client import complete


class HyDEFirewall:
    """
    Pare-feu intelligent qui analyse la cohérence des réponses LLM
    et décide de les intercepter ou de les laisser passer.
    """
    
    def __init__(self):
        # Seuils de cohérence (0-100)
        self.coherence_threshold = 70  # Seuil minimum pour laisser passer
        self.critical_threshold = 40   # Seuil critique (blocage automatique)
        
        # Patterns d'hallucination courantes
        self.hallucination_patterns = [
            r"je ne sais pas|je n'ai pas d'information|désolé, je ne peux pas",
            r"selon mes données|d'après mes informations|dans ma base de données",
            r"il semblerait que|il est possible que|probablement",
            r"contactez directement|veuillez contacter|je vous recommande de contacter",
            r"information non disponible|données manquantes|pas d'information précise"
        ]
        
        # Patterns de réponses cohérentes
        self.coherent_patterns = [
            r"voici|nous proposons|notre entreprise|nos produits",
            r"prix|tarif|coût|montant|€|franc",
            r"livraison|délai|zone|transport",
            r"contact|téléphone|whatsapp|email",
            r"horaires|ouvert|disponible|heures"
        ]
        
        # Messages de fallback sécurisés
        self.fallback_messages = [
            "Je vais vérifier cette information pour vous donner une réponse précise. Un instant...",
            "Permettez-moi de consulter nos données pour vous fournir l'information exacte.",
            "Je transmets votre question à notre équipe pour une réponse personnalisée.",
            "Pour cette demande spécifique, je vous mets en relation avec un conseiller."
        ]

    @timing_metric("firewall_analysis")
    async def analyze_response_coherence(
        self, 
        user_question: str, 
        llm_response: str, 
        conversation_history: str = "",
        context_used: str = ""
    ) -> Tuple[bool, int, str]:
        """
        Analyse la cohérence d'une réponse LLM.
        
        Returns:
            Tuple[bool, int, str]: (should_pass, coherence_score, reason)
        """
        
        # 1. Analyse des patterns d'hallucination
        hallucination_score = self._detect_hallucination_patterns(llm_response)
        
        # 2. Analyse de la cohérence contextuelle
        context_score = await self._analyze_contextual_coherence(
            user_question, llm_response, context_used
        )
        
        # 3. Analyse de la cohérence conversationnelle
        conversation_score = self._analyze_conversation_coherence(
            llm_response, conversation_history
        )
        
        # 4. Analyse de la spécificité de la réponse
        specificity_score = self._analyze_response_specificity(llm_response)
        
        # Affichage du schéma de pensée du pare-feu
        print("\n--- [FIREWALL] Schéma de Pensée ---")
        print(f"- Score d'hallucination...: {hallucination_score}/100")
        print(f"- Score de contexte.........: {context_score}/100")
        print(f"- Score conversationnel...: {conversation_score}/100")
        print(f"- Score de spécificité......: {specificity_score}/100")
        
        # Score global pondéré
        coherence_score = int(
            (context_score * 0.4) +           # 40% - Cohérence avec le contexte
            (conversation_score * 0.25) +     # 25% - Cohérence conversationnelle  
            (specificity_score * 0.25) +      # 25% - Spécificité de la réponse
            (hallucination_score * 0.1)       # 10% - Absence d'hallucination
        )
        
        print(f"- Calcul pondéré............: ({context_score}*0.4) + ({conversation_score}*0.25) + ({specificity_score}*0.25) + ({hallucination_score}*0.1)")
        print(f"- Score de cohérence final..: {coherence_score}/100")
        print(f"- Seuil de passage..........: {self.coherence_threshold}/100")
        
        # Décision de passage
        should_pass = coherence_score >= self.coherence_threshold
        decision = "PASS" if should_pass else "BLOCK"
        print(f"- Décision..................: {decision}")
        print("------------------------------------\n")
        
        # Raison de la décision
        if coherence_score < self.critical_threshold:
            reason = f"Réponse critique (score: {coherence_score}) - Hallucination détectée"
        elif coherence_score < self.coherence_threshold:
            reason = f"Cohérence insuffisante (score: {coherence_score}) - Réponse bloquée"
        else:
            reason = f"Réponse cohérente (score: {coherence_score}) - Passage autorisé"
        
        log3(label="[FIREWALL] Analyse", content=f"{reason} | Question: {user_question[:50]}... | Réponse: {llm_response[:50]}...")
        
        return should_pass, coherence_score, reason

    def _detect_hallucination_patterns(self, response: str) -> int:
        """Détecte les patterns d'hallucination dans la réponse."""
        response_lower = response.lower()
        
        # Pénalité pour patterns d'hallucination
        hallucination_count = 0
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response_lower):
                hallucination_count += 1
        
        # Bonus pour patterns cohérents
        coherent_count = 0
        for pattern in self.coherent_patterns:
            if re.search(pattern, response_lower):
                coherent_count += 1
        
        # Score basé sur le ratio cohérent/hallucination
        if hallucination_count == 0 and coherent_count > 0:
            return 90  # Excellente réponse
        elif hallucination_count == 0:
            return 70  # Réponse neutre
        elif coherent_count > hallucination_count:
            return 50  # Réponse mitigée
        else:
            return 20  # Réponse problématique

    async def _analyze_contextual_coherence(
        self, 
        question: str, 
        response: str, 
        context: str
    ) -> int:
        """Analyse la cohérence entre question, contexte et réponse via LLM."""
        
        if not context.strip():
            return 30  # Pas de contexte = score faible
        
        analysis_prompt = f"""
Analyse la cohérence entre cette question, le contexte disponible et la réponse donnée.

QUESTION: {question}

CONTEXTE DISPONIBLE: {context[:500]}...

RÉPONSE: {response}

Évalue sur 100 la cohérence de la réponse par rapport au contexte et à la question.
Critères:
- La réponse utilise-t-elle les informations du contexte?
- La réponse répond-elle directement à la question?
- Y a-t-il des informations inventées non présentes dans le contexte?

Retourne uniquement un score numérique entre 0 et 100.
"""
        
        try:
            score_text = await complete(analysis_prompt, model_name="llama3-8b-8192", temperature=0)
            # Extraction du score numérique
            score_match = re.search(r'\b(\d{1,3})\b', score_text)
            if score_match:
                score = int(score_match.group(1))
                return min(100, max(0, score))  # Clamp entre 0-100
            return 50  # Score par défaut si parsing échoue
        except Exception as e:
            log3(label="[FIREWALL] Erreur analyse contextuelle", content=str(e))
            return 50

    def _analyze_conversation_coherence(self, response: str, history: str) -> int:
        """Analyse la cohérence avec l'historique conversationnel."""
        
        if not history.strip():
            return 70  # Pas d'historique = score neutre
        
        # Extraction des sujets de l'historique
        history_topics = self._extract_topics(history)
        response_topics = self._extract_topics(response)
        
        # Calcul de l'overlap thématique
        if not history_topics:
            return 70
        
        common_topics = set(history_topics) & set(response_topics)
        overlap_ratio = len(common_topics) / len(history_topics)
        
        # Score basé sur la cohérence thématique
        if overlap_ratio > 0.5:
            return 85  # Forte cohérence
        elif overlap_ratio > 0.2:
            return 65  # Cohérence modérée
        else:
            return 45  # Faible cohérence

    def _extract_topics(self, text: str) -> list:
        """Extrait les sujets principaux d'un texte."""
        topics = []
        text_lower = text.lower()
        
        # Mots-clés thématiques business
        topic_keywords = {
            'produits': ['produit', 'couche', 'article', 'gamme'],
            'prix': ['prix', 'tarif', 'coût', 'montant'],
            'livraison': ['livraison', 'délai', 'transport', 'expédition'],
            'contact': ['contact', 'téléphone', 'whatsapp', 'email'],
            'horaires': ['horaire', 'ouvert', 'ferme', 'disponible'],
            'entreprise': ['entreprise', 'société', 'mission', 'activité']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics

    def _analyze_response_specificity(self, response: str) -> int:
        """Analyse la spécificité et la précision de la réponse."""
        
        # Indicateurs de spécificité
        specific_indicators = [
            r'\d+',  # Nombres
            r'€|franc|cfa',  # Devises
            r'\d+h\d+|\d+:\d+',  # Heures
            r'lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche',  # Jours
            r'abidjan|cocody|yopougon|adjamé',  # Lieux spécifiques
            r'whatsapp|email|téléphone',  # Moyens de contact précis
        ]
        
        specificity_count = 0
        for pattern in specific_indicators:
            if re.search(pattern, response.lower()):
                specificity_count += 1
        
        # Score basé sur le nombre d'éléments spécifiques
        if specificity_count >= 3:
            return 90  # Très spécifique
        elif specificity_count >= 2:
            return 75  # Assez spécifique
        elif specificity_count >= 1:
            return 60  # Peu spécifique
        else:
            return 40  # Très générique

    def get_fallback_message(self, question_type: str = "general") -> str:
        """Retourne un message de fallback sécurisé."""
        import random
        return random.choice(self.fallback_messages)

    async def process_response(
        self, 
        user_question: str, 
        llm_response: str, 
        conversation_history: str = "",
        context_used: str = ""
    ) -> Dict[str, Any]:
        """
        Traite une réponse LLM à travers le pare-feu.
        
        Returns:
            Dict avec 'response', 'blocked', 'score', 'reason'
        """
        
        should_pass, score, reason = await self.analyze_response_coherence(
            user_question, llm_response, conversation_history, context_used
        )
        
        if should_pass:
            return {
                'response': llm_response,
                'blocked': False,
                'score': score,
                'reason': reason
            }
        else:
            fallback = self.get_fallback_message()
            return {
                'response': fallback,
                'blocked': True,
                'score': score,
                'reason': reason,
                'original_response': llm_response
            }
