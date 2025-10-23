#!/usr/bin/env python3
"""
🧠 THINKING PARSER - Extraction données structurées du <thinking>
Objectif: Parser le YAML généré par le LLM pour extraire les données collectées
Architecture: Robuste avec fallbacks multiples (regex, notepad, memory)
"""

import re
import yaml
from typing import Dict, List, Optional, Any, Tuple
from utils import log3


class ThinkingParser:
    """
    🧠 Parser du bloc <thinking> généré par le LLM
    Extrait les données structurées en YAML pour enrichir le contexte
    """
    
    def __init__(self):
        self.last_parsed_data = None
        self.parsing_errors = []
    
    def extract_thinking_block(self, llm_response: str) -> Optional[str]:
        """
        📦 Extrait le contenu du bloc <thinking>...</thinking>
        
        Args:
            llm_response: Réponse complète du LLM
            
        Returns:
            Contenu du thinking ou None si absent
        """
        try:
            # Regex pour extraire le contenu entre <thinking> et </thinking>
            match = re.search(r'<thinking>(.*?)</thinking>', llm_response, re.DOTALL | re.IGNORECASE)
            
            if match:
                thinking_content = match.group(1).strip()
                log3("[THINKING_PARSER]", f"✅ Bloc <thinking> extrait: {len(thinking_content)} chars")
                return thinking_content
            else:
                log3("[THINKING_PARSER]", "⚠️ Aucun bloc <thinking> trouvé")
                return None
                
        except Exception as e:
            log3("[THINKING_PARSER]", f"❌ Erreur extraction thinking: {e}")
            return None
    
    def _clean_yaml_content(self, content: str) -> str:
        """
        🧹 Nettoie le contenu YAML pour le rendre plus parsable
        
        Args:
            content: Contenu YAML brut
            
        Returns:
            Contenu nettoyé
        """
        # Supprimer les lignes vides multiples
        content = re.sub(r'\n\s*\n', '\n', content)
        
        # Supprimer les tirets de section (PHASE 1: EXTRACTION → PHASE 1 EXTRACTION)
        content = re.sub(r'(PHASE \d+):\s*([A-Z\s]+)', r'\1_\2', content)
        
        # Nettoyer les espaces en fin de ligne
        content = '\n'.join(line.rstrip() for line in content.split('\n'))
        
        return content
    
    def parse_yaml_section(self, thinking_content: str, section_name: str) -> Optional[Dict[str, Any]]:
        """
 Parse une section YAML spécifique du thinking (VERSION TOLÉRANTE)
        
Args:
            thinking_content: Contenu complet du bloc <thinking>
            section_name: Nom de la section (ex: "PHASE 2 COLLECTE" ou "PHASE 2: COLLECTE")
            
Returns:
            Dict parsé ou None si erreur
        """
        try:
            # Regex pour extraire la section (jusqu'à la prochaine PHASE ou fin)
            # Accepte PHASE X ou PHASE X: comme délimiteur
            section_pattern = rf'{section_name}(.*?)(?=PHASE \d+\s|PHASE \d+:|$)'
            section_match = re.search(section_pattern, thinking_content, re.DOTALL | re.IGNORECASE)
            
            if not section_match:
                log3("[THINKING_PARSER]", f"⚠️ Section '{section_name}' non trouvée")
                return None
            
            section_content = section_match.group(1).strip()
            
            # Nettoyer le contenu avant parsing
            cleaned_content = self._clean_yaml_content(section_content)
            
            # Tentative 1: Parser le YAML directement
            try:
                parsed = yaml.safe_load(cleaned_content)
                if parsed and isinstance(parsed, dict):
                    log3("[THINKING_PARSER]", f"✅ Section '{section_name}' parsée: {len(parsed)} clés")
                    return parsed
            except yaml.YAMLError:
                pass  # Passer au fallback regex
            
            # Tentative 2: Fallback regex pour extraire les données manuellement
            log3("[THINKING_PARSER]", f"⚠️ YAML échoué pour '{section_name}', fallback regex...")
            return self._parse_section_with_regex(section_content, section_name)
                
        except Exception as e:
            log3("[THINKING_PARSER]", f"❌ Erreur parsing '{section_name}': {e}")
            self.parsing_errors.append(f"{section_name}: {str(e)}")
            return None
    
    def _parse_section_with_regex(self, content: str, section_name: str) -> Optional[Dict[str, Any]]:
        """
        🔍 Parse une section avec regex comme fallback
        
        Args:
            content: Contenu de la section
            section_name: Nom de la section
            
        Returns:
            Dict parsé ou None
        """
        result = {}
        
        try:
            # Extraire les paires clé: valeur simples
            # Format: key: value ou key: "value"
            simple_pattern = r'(\w+):\s*(["\']?)([^"\'\n]+)\2'
            for match in re.finditer(simple_pattern, content):
                key = match.group(1)
                value = match.group(3).strip()
                
                # Convertir les types
                if value.lower() in ('true', 'false'):
                    result[key] = value.lower() == 'true'
                elif value.lower() == 'null':
                    result[key] = None
                elif value.isdigit():
                    result[key] = int(value)
                else:
                    result[key] = value
            
            # Extraire les listes
            # Format: - item1
            list_pattern = r'(\w+):\s*\n((?:\s*-\s*.+\n?)+)'
            for match in re.finditer(list_pattern, content):
                key = match.group(1)
                items_text = match.group(2)
                items = [item.strip('- \n') for item in items_text.split('\n') if item.strip()]
                result[key] = items
            
            if result:
                log3("[THINKING_PARSER]", f"✅ Regex fallback réussi pour '{section_name}': {len(result)} clés")
                return result
            else:
                log3("[THINKING_PARSER]", f"⚠️ Regex fallback vide pour '{section_name}'")
                return None
                
        except Exception as e:
            log3("[THINKING_PARSER]", f"❌ Erreur regex fallback '{section_name}': {e}")
            return None
    
    def extract_deja_collecte(self, thinking_content: str) -> Dict[str, Optional[str]]:
        """
 Extrait le dict 'deja_collecte' de PHASE 2
        
Returns:
            Dict avec clés: type_produit, quantite, zone, telephone, paiement
        """
        # Essayer plusieurs variantes de format
        phase2 = self.parse_yaml_section(thinking_content, "PHASE 2 COLLECTE")
        if not phase2:
            phase2 = self.parse_yaml_section(thinking_content, "PHASE 2: COLLECTE")
        if not phase2:
            phase2 = self.parse_yaml_section(thinking_content, "PHASE 2:")
        
        if phase2 and "deja_collecte" in phase2:
            deja_collecte = phase2["deja_collecte"]
            log3("[THINKING_PARSER]", f"✅ deja_collecte extrait: {deja_collecte}")
            return deja_collecte
        
        # Fallback: retourner structure vide
        log3("[THINKING_PARSER]", "⚠️ deja_collecte non trouvé, fallback structure vide")
        return {
            "type_produit": None,
            "quantite": None,
            "zone": None,
            "telephone": None,
            "paiement": None
        }
    
    def extract_nouvelles_donnees(self, thinking_content: str) -> List[Dict[str, str]]:
        """
        📋 Extrait la liste 'nouvelles_donnees' de PHASE 2
        
        Returns:
            Liste de dicts avec clés: cle, valeur, source, confiance
        """
        # Essayer plusieurs variantes de format
        phase2 = self.parse_yaml_section(thinking_content, "PHASE 2 COLLECTE")
        if not phase2:
            phase2 = self.parse_yaml_section(thinking_content, "PHASE 2: COLLECTE")
        if not phase2:
            phase2 = self.parse_yaml_section(thinking_content, "PHASE 2:")
        
        if phase2 and "nouvelles_donnees" in phase2:
            nouvelles_donnees = phase2["nouvelles_donnees"]
            
            # Valider que c'est bien une liste
            if isinstance(nouvelles_donnees, list):
                log3("[THINKING_PARSER]", f"✅ nouvelles_donnees extrait: {len(nouvelles_donnees)} items")
                return nouvelles_donnees
        
        # Fallback: liste vide
        log3("[THINKING_PARSER]", "⚠️ nouvelles_donnees non trouvé, fallback liste vide")
        return []
    
    def extract_confiance_globale(self, thinking_content: str) -> Tuple[int, str]:
        """
        🎯 Extrait le score de confiance globale de PHASE 3
        
        Returns:
            Tuple (score: int, raison: str)
        """
        # Essayer avec et sans deux-points
        phase3 = self.parse_yaml_section(thinking_content, "PHASE 3 VALIDATION")
        if not phase3:
            phase3 = self.parse_yaml_section(thinking_content, "PHASE 3: VALIDATION")
        
        if phase3 and "confiance_globale" in phase3:
            confiance = phase3["confiance_globale"]
            
            # Gérer les deux formats: int direct ou dict avec score/raison
            if isinstance(confiance, dict):
                # Format: {score: 90, raison: "..."}
                score_raw = confiance.get("score", "0%")
                raison = confiance.get("raison", "")
            else:
                # Format: 85 (int direct)
                score_raw = confiance
                raison = ""
            
            # Nettoyer le score
            if isinstance(score_raw, str):
                score = int(re.sub(r'[^\d]', '', score_raw))
            else:
                score = int(score_raw)
            
            log3("[THINKING_PARSER]", f"✅ confiance_globale: {score}% - {raison}")
            return (score, raison)
        
        # Fallback: confiance moyenne
        log3("[THINKING_PARSER]", "⚠️ confiance_globale non trouvé, fallback 50%")
        return (50, "Confiance par défaut (parsing échoué)")
    
    def extract_completude(self, thinking_content: str) -> str:
        """
        📊 Extrait la complétude de PHASE 5
        
        Returns:
            String format "X/5" (ex: "3/5")
        """
        # Essayer avec et sans deux-points
        phase5 = self.parse_yaml_section(thinking_content, "PHASE 5 DECISION")
        if not phase5:
            phase5 = self.parse_yaml_section(thinking_content, "PHASE 5: DÉCISION")
        
        if phase5 and "progression" in phase5:
            progression = phase5["progression"]
            completude = progression.get("completude", "0/5")
            
            log3("[THINKING_PARSER]", f"✅ completude: {completude}")
            return str(completude)
        
        # Fallback: 0/5
        log3("[THINKING_PARSER]", "⚠️ completude non trouvé, fallback 0/5")
        return "0/5"
    
    def extract_prochaine_etape(self, thinking_content: str) -> Dict[str, str]:
        """
        🎯 Extrait la prochaine étape recommandée de PHASE 5
        
        Returns:
            Dict avec clés: type, action
        """
        # Essayer avec et sans deux-points
        phase5 = self.parse_yaml_section(thinking_content, "PHASE 5 DECISION")
        if not phase5:
            phase5 = self.parse_yaml_section(thinking_content, "PHASE 5: DÉCISION")
        
        if phase5 and "progression" in phase5:
            progression = phase5["progression"]
            prochaine_etape = progression.get("prochaine_etape", {})
            
            if isinstance(prochaine_etape, dict):
                log3("[THINKING_PARSER]", f"✅ prochaine_etape: {prochaine_etape.get('type', 'N/A')}")
                return prochaine_etape
        
        # Fallback
        log3("[THINKING_PARSER]", "⚠️ prochaine_etape non trouvé, fallback")
        return {"type": "collecte", "action": "Continuer la collecte d'informations"}
    
    def extract_strategie_qualification(self, thinking_content: str) -> Dict[str, str]:
        """
        🎭 Extrait la stratégie de qualification de PHASE 5
        
        Returns:
            Dict avec clés: phase, objectif, technique
        """
        # Essayer avec et sans deux-points
        phase5 = self.parse_yaml_section(thinking_content, "PHASE 5 DECISION")
        if not phase5:
            phase5 = self.parse_yaml_section(thinking_content, "PHASE 5: DÉCISION")
        
        if phase5 and "strategie_qualification" in phase5:
            strategie = phase5["strategie_qualification"]
            
            if isinstance(strategie, dict):
                log3("[THINKING_PARSER]", f"✅ strategie: {strategie.get('phase', 'N/A')}")
                return strategie
        
        # Fallback
        log3("[THINKING_PARSER]", "⚠️ strategie_qualification non trouvé, fallback")
        return {
            "phase": "decouverte",
            "objectif": "Identifier le besoin",
            "technique": "clarification"
        }
    
    def parse_full_thinking(self, llm_response: str) -> Dict[str, Any]:
        """
        🎯 Parse complet du thinking avec toutes les données
        
        Args:
            llm_response: Réponse complète du LLM
            
        Returns:
            Dict avec toutes les données extraites
        """
        # Réinitialiser les erreurs
        self.parsing_errors = []
        
        # Extraire le bloc thinking
        thinking_content = self.extract_thinking_block(llm_response)
        
        if not thinking_content:
            log3("[THINKING_PARSER]", "❌ Impossible de parser: pas de bloc <thinking>")
            return self._get_empty_result()
        
        # Extraire toutes les données
        try:
            deja_collecte = self.extract_deja_collecte(thinking_content)
            nouvelles_donnees = self.extract_nouvelles_donnees(thinking_content)
            confiance_score, confiance_raison = self.extract_confiance_globale(thinking_content)
            completude = self.extract_completude(thinking_content)
            prochaine_etape = self.extract_prochaine_etape(thinking_content)
            strategie = self.extract_strategie_qualification(thinking_content)
            
            result = {
                "success": True,
                "deja_collecte": deja_collecte,
                "nouvelles_donnees": nouvelles_donnees,
                "confiance": {
                    "score": confiance_score,
                    "raison": confiance_raison
                },
                "progression": {
                    "completude": completude,
                    "prochaine_etape": prochaine_etape
                },
                "strategie_qualification": strategie,
                "parsing_errors": self.parsing_errors
            }
            
            # Sauvegarder pour debug
            self.last_parsed_data = result
            
            log3("[THINKING_PARSER]", f"✅ Parsing complet réussi: {len(self.parsing_errors)} erreurs")
            return result
            
        except Exception as e:
            log3("[THINKING_PARSER]", f"❌ Erreur parsing complet: {e}")
            return self._get_empty_result()
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """Retourne une structure vide en cas d'échec total"""
        return {
            "success": False,
            "deja_collecte": {
                "type_produit": None,
                "quantite": None,
                "zone": None,
                "telephone": None,
                "paiement": None
            },
            "nouvelles_donnees": [],
            "confiance": {
                "score": 50,
                "raison": "Parsing échoué"
            },
            "progression": {
                "completude": "0/5",
                "prochaine_etape": {
                    "type": "collecte",
                    "action": "Continuer"
                }
            },
            "strategie_qualification": {
                "phase": "decouverte",
                "objectif": "Identifier besoin",
                "technique": "clarification"
            },
            "parsing_errors": self.parsing_errors
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """📊 Statistiques du parser"""
        return {
            "last_parsed": self.last_parsed_data is not None,
            "errors_count": len(self.parsing_errors),
            "errors": self.parsing_errors
        }


# Instance globale singleton
_thinking_parser_instance = None

def get_thinking_parser() -> ThinkingParser:
    """🎯 Singleton pour le parser thinking"""
    global _thinking_parser_instance
    if _thinking_parser_instance is None:
        _thinking_parser_instance = ThinkingParser()
        log3("[THINKING_PARSER]", "🚀 ThinkingParser initialisé")
    return _thinking_parser_instance
