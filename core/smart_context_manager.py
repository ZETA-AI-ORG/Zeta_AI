"""
🧠 SMART CONTEXT MANAGER
Architecture hybride pour garantir 0% perte de contexte conversationnel

Combine 4 stratégies:
1. Extraction depuis <thinking> (Cerveau 1: Lecteur de Pensées)
2. Extraction depuis Enhanced Memory (Cerveau 2: Archiviste)
3. Validation anti-hallucination (Cerveau 3: Détecteur de Mensonges)
4. Persistance bloc-note (Cerveau 4: Mémoire Permanente)
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ContextState:
    """État complet du contexte conversationnel"""
    produit: Optional[str] = None
    prix_produit: Optional[str] = None
    zone: Optional[str] = None
    frais_livraison: Optional[str] = None
    telephone: Optional[str] = None
    paiement: Optional[str] = None
    acompte: Optional[str] = None
    total: Optional[str] = None
    confirmation: bool = False
    
    def to_dict(self) -> Dict:
        """Convertir en dictionnaire (exclut None)"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def completeness_score(self) -> float:
        """Calcule le taux de complétion (0-1)"""
        required = ['produit', 'zone', 'telephone', 'paiement']
        filled = sum(1 for field in required if getattr(self, field) is not None)
        return filled / len(required)


class SmartContextManager:
    """
    Gestionnaire intelligent de contexte conversationnel
    Combine 4 stratégies pour garantir 0% perte de contexte
    """
    
    def __init__(self, user_id: str, company_id: str):
        self.user_id = user_id
        self.company_id = company_id
        self.state = ContextState()
        
        # Charger état depuis bloc-note si existe
        self._load_from_notepad()
    
    # ═══════════════════════════════════════════════════════════════════
    # CERVEAU 1: EXTRACTION DEPUIS <thinking>
    # ═══════════════════════════════════════════════════════════════════
    
    def extract_from_thinking(self, thinking_text: str) -> Dict[str, str]:
        """
        Parse <thinking> pour extraire les actions bloc-note
        
        Cherche:
        - Bloc-note: ajouter info (clé, "valeur")
        - Bloc-note: ajouter info (clé, valeur)
        - Action : Bloc-note...
        """
        extracted = {}
        
        if not thinking_text:
            return extracted
        
        # Pattern 1: avec guillemets
        pattern1 = r'Bloc-note:\s*ajouter info\s*\(([^,]+),\s*["\']([^"\']+)["\']\)'
        matches1 = re.findall(pattern1, thinking_text, re.IGNORECASE)
        
        # Pattern 2: sans guillemets
        pattern2 = r'Bloc-note:\s*ajouter info\s*\(([^,]+),\s*([^\)]+)\)'
        matches2 = re.findall(pattern2, thinking_text, re.IGNORECASE)
        
        # Pattern 3: avec "Action :"
        pattern3 = r'Action\s*:\s*Bloc-note:\s*ajouter info\s*\(([^,]+),\s*["\']?([^"\']+)["\']?\)'
        matches3 = re.findall(pattern3, thinking_text, re.IGNORECASE)
        
        all_matches = matches1 + matches2 + matches3
        
        for key, value in all_matches:
            key = key.strip().strip('"').strip("'").lower()
            value = value.strip().strip('"').strip("'")
            
            # Normaliser les clés
            key_mapping = {
                'produit': 'produit',
                'product': 'produit',
                'lot': 'produit',
                'prix': 'prix_produit',
                'prix_produit': 'prix_produit',
                'price': 'prix_produit',
                'zone': 'zone',
                'commune': 'zone',
                'city': 'zone',
                'livraison': 'frais_livraison',
                'frais_livraison': 'frais_livraison',
                'delivery': 'frais_livraison',
                'telephone': 'telephone',
                'tel': 'telephone',
                'phone': 'telephone',
                'numero': 'telephone',
                'paiement': 'paiement',
                'payment': 'paiement',
                'methode_paiement': 'paiement',
                'acompte': 'acompte',
                'deposit': 'acompte',
                'total': 'total',
                'montant_total': 'total'
            }
            
            normalized_key = key_mapping.get(key, key)
            extracted[normalized_key] = value
            logger.info(f"✅ [THINKING] Extrait: {normalized_key}={value}")
        
        return extracted
    
    # ═══════════════════════════════════════════════════════════════════
    # CERVEAU 2: EXTRACTION DEPUIS ENHANCED MEMORY
    # ═══════════════════════════════════════════════════════════════════
    
    def extract_from_memory(self) -> Dict[str, str]:
        """
        Fallback: extraire depuis Enhanced Memory si thinking vide
        """
        try:
            from core.enhanced_memory import EnhancedMemory
            memory = EnhancedMemory(self.user_id)
            recent = memory.get_recent_interactions(limit=15)
            
            extracted = {}
            
            for interaction in recent:
                msg = interaction.get('user_message', '').lower()
                bot_response = interaction.get('bot_response', '').lower()
                combined = f"{msg} {bot_response}"
                
                # Extraire produit
                if not extracted.get('produit'):
                    if 'lot 150' in combined:
                        extracted['produit'] = 'lot 150'
                        extracted['prix_produit'] = '13500'
                    elif 'lot 300' in combined:
                        extracted['produit'] = 'lot 300'
                        extracted['prix_produit'] = '24000'
                    elif 'lot150' in combined.replace(' ', ''):
                        extracted['produit'] = 'lot 150'
                        extracted['prix_produit'] = '13500'
                    elif 'lot300' in combined.replace(' ', ''):
                        extracted['produit'] = 'lot 300'
                        extracted['prix_produit'] = '24000'
                
                # Extraire zone
                if not extracted.get('zone'):
                    zones = {
                        'cocody': '1500',
                        'yopougon': '1500',
                        'abobo': '2000',
                        'adjamé': '1500',
                        'adjame': '1500',
                        'plateau': '1500',
                        'marcory': '2000',
                        'koumassi': '2000',
                        'port-bouët': '2500',
                        'port-bouet': '2500',
                        'treichville': '1500'
                    }
                    for zone, frais in zones.items():
                        if zone in combined:
                            extracted['zone'] = zone.capitalize()
                            extracted['frais_livraison'] = frais
                            break
                
                # Extraire téléphone
                if not extracted.get('telephone'):
                    # Pattern: 10 chiffres commençant par 0
                    phone_match = re.search(r'\b(0\d{9})\b', msg)
                    if phone_match:
                        extracted['telephone'] = phone_match.group(1)
                    else:
                        # Pattern: avec espaces
                        phone_match = re.search(r'\b(0\d[\s\d]{8,})\b', msg)
                        if phone_match:
                            phone = phone_match.group(1).replace(' ', '')
                            if len(phone) == 10:
                                extracted['telephone'] = phone
                
                # Extraire paiement
                if not extracted.get('paiement'):
                    if 'wave' in combined:
                        extracted['paiement'] = 'Wave'
                        extracted['acompte'] = '2000'
                    elif 'orange money' in combined or 'orange' in combined:
                        extracted['paiement'] = 'Orange Money'
                        extracted['acompte'] = '2000'
                    elif 'mtn' in combined or 'momo' in combined:
                        extracted['paiement'] = 'MTN Mobile Money'
                        extracted['acompte'] = '2000'
                
                # Extraire total
                if not extracted.get('total'):
                    # Pattern: "total: 15000" ou "total = 15000"
                    total_match = re.search(r'total[:\s=]+(\d+[\s\d]*)', bot_response)
                    if total_match:
                        total = total_match.group(1).replace(' ', '')
                        extracted['total'] = total
            
            if extracted:
                logger.info(f"✅ [MEMORY] Extrait: {extracted}")
            else:
                logger.info("⚠️ [MEMORY] Aucune info trouvée")
            
            return extracted
            
        except Exception as e:
            logger.error(f"❌ [MEMORY] Erreur: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════════════
    # CERVEAU 3: VALIDATION ANTI-HALLUCINATION
    # ═══════════════════════════════════════════════════════════════════
    
    def validate_response(self, llm_response: str, source_documents: List[Dict] = None) -> Dict:
        """
        Vérifie que la réponse LLM correspond aux sources
        """
        discrepancies = []
        
        # Extraire prix depuis réponse
        llm_prices = re.findall(r'(\d+[\s\d]*)\s*F?CFA', llm_response)
        llm_prices = [p.replace(' ', '') for p in llm_prices]
        
        # Extraire prix depuis documents
        source_prices = []
        if source_documents:
            for doc in source_documents:
                content = doc.get('content', '')
                prices = re.findall(r'(\d+[\s\d]*)\s*F?CFA', content)
                source_prices.extend([p.replace(' ', '') for p in prices])
        
        # Comparer (ignorer petits nombres < 1000)
        for price in llm_prices:
            try:
                if int(price) > 1000 and source_documents:
                    if price not in source_prices:
                        discrepancies.append(f"Prix {price} FCFA non trouvé dans sources")
            except ValueError:
                pass
        
        # Vérifier cohérence avec état (questions répétées)
        response_lower = llm_response.lower()
        
        if self.state.produit and any(q in response_lower for q in ["quel lot", "quel produit", "quelle quantité"]):
            discrepancies.append("Bot redemande produit déjà connu")
        
        if self.state.zone and any(q in response_lower for q in ["quelle commune", "quelle zone", "où habitez"]):
            discrepancies.append("Bot redemande zone déjà connue")
        
        if self.state.telephone and any(q in response_lower for q in ["quel numéro", "votre téléphone", "votre contact"]):
            discrepancies.append("Bot redemande téléphone déjà connu")
        
        if self.state.paiement and any(q in response_lower for q in ["quel mode de paiement", "comment payer", "méthode de paiement"]):
            discrepancies.append("Bot redemande paiement déjà connu")
        
        is_valid = len(discrepancies) == 0
        confidence = max(0.0, 1.0 - (len(discrepancies) * 0.3))
        
        result = {
            'is_valid': is_valid,
            'confidence': confidence,
            'discrepancies': discrepancies,
            'hallucination_risk': 'LOW' if is_valid else 'MEDIUM' if confidence > 0.5 else 'HIGH'
        }
        
        if not is_valid:
            logger.warning(f"⚠️ [VALIDATION] {result}")
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════
    # CERVEAU 4: PERSISTANCE BLOC-NOTE
    # ═══════════════════════════════════════════════════════════════════
    
    def _load_from_notepad(self):
        """Charger l'état depuis le bloc-note"""
        try:
            from core.botlive_tools import blocnote_get_all
            notepad = blocnote_get_all(self.user_id, self.company_id)
            
            if notepad:
                self.state.produit = notepad.get('produit')
                self.state.prix_produit = notepad.get('prix_produit')
                self.state.zone = notepad.get('zone')
                self.state.frais_livraison = notepad.get('frais_livraison')
                self.state.telephone = notepad.get('telephone')
                self.state.paiement = notepad.get('paiement')
                self.state.acompte = notepad.get('acompte')
                self.state.total = notepad.get('total')
                
                logger.info(f"✅ [NOTEPAD] État chargé: {self.state.to_dict()}")
        
        except Exception as e:
            logger.error(f"❌ [NOTEPAD] Erreur chargement: {e}")
    
    def _save_to_notepad(self):
        """Sauvegarder l'état dans le bloc-note"""
        try:
            from core.botlive_tools import blocnote_add_info
            
            for key, value in self.state.to_dict().items():
                if value is not None:
                    blocnote_add_info(key, str(value), self.user_id, self.company_id)
            
            logger.info(f"✅ [NOTEPAD] État sauvegardé: {self.state.to_dict()}")
        
        except Exception as e:
            logger.error(f"❌ [NOTEPAD] Erreur sauvegarde: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # API PRINCIPALE
    # ═══════════════════════════════════════════════════════════════════
    
    def update_context(
        self, 
        thinking_text: str = "", 
        llm_response: str = "", 
        source_documents: List[Dict] = None
    ) -> Dict:
        """
        Met à jour le contexte en combinant toutes les stratégies
        
        Pipeline:
        1. Extraire depuis <thinking> (Cerveau 1)
        2. Si vide, extraire depuis Enhanced Memory (Cerveau 2)
        3. Valider contre sources (Cerveau 3)
        4. Mettre à jour état
        5. Sauvegarder dans bloc-note (Cerveau 4)
        
        Returns:
            Dict avec state, completeness, extracted, validation
        """
        logger.info("🧠 [SMART_CONTEXT] Mise à jour contexte...")
        
        # CERVEAU 1: Thinking
        extracted_thinking = self.extract_from_thinking(thinking_text)
        
        # CERVEAU 2: Memory (fallback)
        extracted_memory = {}
        if not extracted_thinking:
            logger.info("⚠️ [SMART_CONTEXT] Thinking vide, fallback Memory")
            extracted_memory = self.extract_from_memory()
        
        # Fusionner extractions (Thinking prioritaire)
        extracted = {**extracted_memory, **extracted_thinking}
        
        # CERVEAU 3: Validation
        validation = {'is_valid': True, 'confidence': 1.0, 'discrepancies': [], 'hallucination_risk': 'LOW'}
        if llm_response:
            validation = self.validate_response(llm_response, source_documents)
            if validation['hallucination_risk'] == 'HIGH':
                logger.error(f"🚨 [SMART_CONTEXT] Hallucination détectée: {validation['discrepancies']}")
        
        # Mettre à jour état
        if extracted:
            for key, value in extracted.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
                    logger.info(f"✅ [SMART_CONTEXT] {key} = {value}")
        
        # CERVEAU 4: Persistance
        self._save_to_notepad()
        
        # Calculer complétude
        completeness = self.state.completeness_score()
        logger.info(f"📊 [SMART_CONTEXT] Complétude: {completeness*100:.0f}%")
        
        return {
            'state': self.state.to_dict(),
            'completeness': completeness,
            'extracted': extracted,
            'validation': validation
        }
    
    def get_context_summary(self) -> str:
        """
        Génère un résumé formaté pour injection dans le prompt
        """
        state_dict = self.state.to_dict()
        
        if not state_dict:
            return ""
        
        summary = "\n📋 CONTEXTE COLLECTÉ (NE PAS REDEMANDER):\n"
        
        if self.state.produit:
            summary += f"   ✅ Produit: {self.state.produit}"
            if self.state.prix_produit:
                summary += f" ({self.state.prix_produit} FCFA)"
            summary += "\n"
        
        if self.state.zone:
            summary += f"   ✅ Zone: {self.state.zone}"
            if self.state.frais_livraison:
                summary += f" (livraison {self.state.frais_livraison} FCFA)"
            summary += "\n"
        
        if self.state.telephone:
            summary += f"   ✅ Téléphone: {self.state.telephone}\n"
        
        if self.state.paiement:
            summary += f"   ✅ Paiement: {self.state.paiement}"
            if self.state.acompte:
                summary += f" (acompte {self.state.acompte} FCFA)"
            summary += "\n"
        
        if self.state.total:
            summary += f"   💰 Total: {self.state.total} FCFA\n"
        
        # Ajouter infos manquantes
        missing = []
        if not self.state.produit:
            missing.append("produit")
        if not self.state.zone:
            missing.append("zone")
        if not self.state.telephone:
            missing.append("téléphone")
        if not self.state.paiement:
            missing.append("paiement")
        
        if missing:
            summary += f"\n⚠️ MANQUANT: {', '.join(missing)}\n"
        
        return summary
    
    def should_ask_recap(self) -> bool:
        """Détermine si on doit proposer un récapitulatif"""
        return self.state.completeness_score() >= 0.75  # 3/4 infos collectées
    
    def get_next_question(self) -> Optional[str]:
        """Suggère la prochaine question à poser"""
        if not self.state.produit:
            return "Quel lot souhaitez-vous commander ?"
        if not self.state.zone:
            return "Dans quelle commune habitez-vous ?"
        if not self.state.telephone:
            return "Quel est votre numéro de téléphone ?"
        if not self.state.paiement:
            return "Quel mode de paiement préférez-vous ?"
        return None  # Tout est collecté
