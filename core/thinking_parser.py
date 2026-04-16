#!/usr/bin/env python3
"""
🧠 THINKING PARSER - Extraction données structurées du <thinking>
Objectif: Parser le YAML généré par le LLM pour extraire les données collectées
Architecture: Robuste avec fallbacks multiples (regex, notepad, memory)
"""

import json as _json
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
        self._logged_minimal_detected = False
    
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

    def extract_tag_text(self, content: str, tag: str) -> Optional[str]:
        try:
            if not content or not tag:
                return None
            t = str(tag).strip()
            if not t:
                return None
            m = re.search(rf"<{re.escape(t)}>(.*?)</{re.escape(t)}>", content, re.DOTALL | re.IGNORECASE)
            if not m:
                return None
            return (m.group(1) or "").strip()
        except Exception:
            return None

    def _is_minimal_thinking(self, thinking_content: str) -> bool:
        try:
            return self._parse_minimal_thinking(thinking_content) is not None
        except Exception:
            return False

    def extract_extracted_details(self, thinking_content: str, max_len: int = 140) -> str:
        try:
            raw = self.extract_tag_text(thinking_content or "", "extracted_details")
            if not raw:
                return ""

            val = re.sub(r"\s+", " ", raw).strip()
            if not val or val in {"∅", "Ø", "NONE", "none", "null", "NULL"}:
                return ""

            val = re.sub(r"[\r\n\t]+", " ", val).strip()
            if len(val) > max_len:
                val = val[:max_len].rstrip() + "…"
            return val
        except Exception:
            return ""
    
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
            # Si le LLM renvoie un <thinking> minimal (intent/checklist/next/action)
            # on évite de chercher des sections PHASE* et de polluer les logs.
            if section_name and str(section_name).strip().upper().startswith("PHASE"):
                minimal = self._parse_minimal_thinking(thinking_content)
                if minimal is not None:
                    return None

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
        # Mode minimal: <intent>/<checklist>/<next>/<action>
        minimal = self._parse_minimal_thinking(thinking_content)
        if minimal is not None:
            return {
                "type_produit": None,
                "quantite": None,
                "zone": None,
                "telephone": None,
                "paiement": None,
            }

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

    def _parse_minimal_thinking(self, thinking_content: str) -> Optional[Dict[str, str]]:
        """Parse le <thinking> minimal (intent/checklist/next/action).

        Si ce format est détecté, on évite de lancer le parsing PHASE* (bruyant) et on renvoie
        un dict non vide.
        """
        try:
            if not thinking_content:
                return None

            intent = self.extract_tag_text(thinking_content, "intent")
            checklist = self.extract_tag_text(thinking_content, "checklist")
            next_step = self.extract_tag_text(thinking_content, "next")
            action = self.extract_tag_text(thinking_content, "action")

            is_minimal = any([(intent or "").strip(), (checklist or "").strip(), (next_step or "").strip(), (action or "").strip()])
            has_phase_markers = bool(re.search(r"\bPHASE\s*\d+", thinking_content, re.IGNORECASE))

            if is_minimal and not has_phase_markers:
                return {
                    "intent": (intent or "").strip(),
                    "checklist": (checklist or "").strip(),
                    "next": (next_step or "").strip(),
                    "action": (action or "").strip(),
                }

            return None
        except Exception:
            return None
    
    def extract_nouvelles_donnees(self, thinking_content: str) -> List[Dict[str, str]]:
        """
        📋 Extrait la liste 'nouvelles_donnees' de PHASE 2
        
        Returns:
            Liste de dicts avec clés: cle, valeur, source, confiance
        """
        if self._is_minimal_thinking(thinking_content):
            return []

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
        if self._is_minimal_thinking(thinking_content):
            return (50, "Confiance par défaut (format minimal)")

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
        if self._is_minimal_thinking(thinking_content):
            return "0/5"

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
        if self._is_minimal_thinking(thinking_content):
            return {"type": "collecte", "action": "Continuer la collecte d'informations"}

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
        if self._is_minimal_thinking(thinking_content):
            return {
                "phase": "decouverte",
                "objectif": "Identifier le besoin",
                "technique": "clarification",
            }

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
    
    # ══════════════════════════════════════════════════════════════════════════
    # V2 XML-TAG PARSER  (q_exact / catalogue_match / detected_items_json /
    #                      tool_call / maj / detection / priority / handoff)
    # ══════════════════════════════════════════════════════════════════════════

    def _is_v2_thinking(self, thinking_content: str) -> bool:
        """Return True when thinking uses V2 XML-tag structure."""
        if not thinking_content:
            return False
        v2_markers = ("<q_exact>", "<detected_items_json>", "<catalogue_match>", "<priority>")
        return any(m in thinking_content for m in v2_markers)

    def _parse_detection_slots(self, detection_text: str) -> Dict[str, Optional[str]]:
        """Parse the <detection> block to extract RÉSUMÉ/ZONE/TÉLÉPHONE/PAIEMENT."""
        slots: Dict[str, Optional[str]] = {
            "resume": None, "zone": None, "telephone": None, "paiement": None,
        }
        if not detection_text:
            return slots
        for line in detection_text.splitlines():
            line = line.strip().lstrip("- ").strip()
            if not line:
                continue
            lc = line.lower()
            if lc.startswith("résumé:") or lc.startswith("resume:"):
                val = line.split(":", 1)[1].strip()
                slots["resume"] = val if val and val not in {"∅", "Ø", "null"} else None
            elif lc.startswith("zone:"):
                val = line.split(":", 1)[1].strip()
                slots["zone"] = val if val and val not in {"∅", "Ø", "null"} else None
            elif lc.startswith("téléphone:") or lc.startswith("telephone:"):
                val = line.split(":", 1)[1].strip()
                slots["telephone"] = val if val and val not in {"∅", "Ø", "null"} else None
            elif lc.startswith("paiement:"):
                val = line.split(":", 1)[1].strip()
                slots["paiement"] = val if val and val not in {"∅", "Ø", "null"} else None
        return slots

    def parse_full_thinking_v2(self, thinking_content: str) -> Dict[str, Any]:
        """Parse V2 XML-tag thinking. Returns backward-compatible dict."""
        self.parsing_errors = []

        q_exact = self.extract_tag_text(thinking_content, "q_exact") or ""
        catalogue_match = self.extract_tag_text(thinking_content, "catalogue_match") or ""
        detected_product = self.extract_tag_text(thinking_content, "detected_product") or ""

        # detected_items_json → list[dict]
        items_raw = self.extract_tag_text(thinking_content, "detected_items_json") or ""
        detected_items: List[Dict[str, Any]] = []
        try:
            parsed = _json.loads(items_raw)
            if isinstance(parsed, list):
                detected_items = [i for i in parsed if isinstance(i, dict)]
        except Exception:
            if items_raw.strip():
                self.parsing_errors.append(f"detected_items_json parse error: {items_raw[:120]}")

        # tool_call → dict
        tool_call_raw = self.extract_tag_text(thinking_content, "tool_call") or ""
        tool_call: Dict[str, Any] = {"action": "NONE"}
        try:
            tc = _json.loads(tool_call_raw.strip())
            if isinstance(tc, dict):
                tool_call = tc
        except Exception:
            pass

        # <maj> → action + reason
        maj_raw = self.extract_tag_text(thinking_content, "maj") or ""
        maj_action = (self.extract_tag_text(maj_raw, "action") or "NONE").strip().upper()
        maj_reason = self.extract_tag_text(maj_raw, "reason") or ""

        # <detection>
        detection_raw = self.extract_tag_text(thinking_content, "detection") or ""
        slots = self._parse_detection_slots(detection_raw)

        # <priority> / <handoff>
        priority = (self.extract_tag_text(thinking_content, "priority") or "FOLLOW_NEXT").strip()
        handoff_raw = (self.extract_tag_text(thinking_content, "handoff") or "false").strip().lower()
        handoff = handoff_raw in {"true", "1", "yes", "oui"}

        # Confidence heuristic from catalogue_match
        conf_score = 80
        conf_raison = "V2 XML parse"
        cm_lower = catalogue_match.lower()
        if "incompatible" in cm_lower:
            conf_score = 30
            conf_raison = "catalogue_match INCOMPATIBLE"
        elif "ambigu" in cm_lower:
            conf_score = 55
            conf_raison = "catalogue_match AMBIGU"
        elif "compatible" in cm_lower:
            conf_score = 90
            conf_raison = "catalogue_match COMPATIBLE"

        # Completude heuristic: count non-null slots
        filled = sum(1 for v in [slots["zone"], slots["telephone"], slots["paiement"]] if v)
        total_slots = 5
        completude = f"{filled + (2 if detected_items else 0)}/{total_slots}"

        result: Dict[str, Any] = {
            "success": True,
            "deja_collecte": {
                "type_produit": slots.get("resume"),
                "quantite": None,
                "zone": slots.get("zone"),
                "telephone": slots.get("telephone"),
                "paiement": slots.get("paiement"),
            },
            "nouvelles_donnees": detected_items,
            "confiance": {"score": conf_score, "raison": conf_raison},
            "progression": {
                "completude": completude,
                "prochaine_etape": {"type": "collecte", "action": priority},
            },
            "strategie_qualification": {
                "phase": "v2_xml",
                "objectif": q_exact[:80] if q_exact else "",
                "technique": priority,
            },
            "parsing_errors": self.parsing_errors,
            # V2-specific extras (callers can optionally use)
            "v2": {
                "q_exact": q_exact,
                "catalogue_match": catalogue_match,
                "detected_product": detected_product,
                "detected_items": detected_items,
                "tool_call": tool_call,
                "maj_action": maj_action,
                "maj_reason": maj_reason,
                "detection_slots": slots,
                "priority": priority,
                "handoff": handoff,
            },
        }

        self.last_parsed_data = result
        log3("[THINKING_PARSER]", f"✅ V2 parse OK | items={len(detected_items)} action={maj_action} priority={priority} handoff={handoff}")
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT (auto-detects V1 YAML vs V2 XML)
    # ══════════════════════════════════════════════════════════════════════════

    def parse_full_thinking(self, llm_response: str) -> Dict[str, Any]:
        """
        🎯 Parse complet du thinking avec toutes les données.
        Auto-détecte V2 XML tags et délègue si approprié.
        
        Args:
            llm_response: Réponse complète du LLM
            
        Returns:
            Dict avec toutes les données extraites
        """
        self.parsing_errors = []
        
        thinking_content = self.extract_thinking_block(llm_response)
        
        if not thinking_content:
            log3("[THINKING_PARSER]", "❌ Impossible de parser: pas de bloc <thinking>")
            return self._get_empty_result()

        # V2 auto-detection: XML tags present → delegate to V2 parser
        if self._is_v2_thinking(thinking_content):
            return self.parse_full_thinking_v2(thinking_content)

        # Mode minimal: ne pas tenter les extractions PHASE* (évite warnings)
        minimal = self._parse_minimal_thinking(thinking_content)
        if minimal is not None:
            if not self._logged_minimal_detected:
                log3("[THINKING_PARSER]", "✅ Format <thinking> minimal détecté (intent/checklist/next/action)")
                self._logged_minimal_detected = True
            result = {
                "success": True,
                "deja_collecte": {
                    "type_produit": None,
                    "quantite": None,
                    "zone": None,
                    "telephone": None,
                    "paiement": None,
                },
                "nouvelles_donnees": [],
                "confiance": {
                    "score": 50,
                    "raison": "Format minimal",
                },
                "progression": {
                    "completude": "0/5",
                    "prochaine_etape": {"type": "collecte", "action": "Continuer"},
                },
                "strategie_qualification": {
                    "phase": "decouverte",
                    "objectif": "Identifier le besoin",
                    "technique": "clarification",
                },
                "parsing_errors": self.parsing_errors,
            }
            self.last_parsed_data = result
            return result
        
        # V1 YAML PHASE-based parsing (legacy)
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
            
            self.last_parsed_data = result
            
            log3("[THINKING_PARSER]", f"✅ V1 Parsing complet réussi: {len(self.parsing_errors)} erreurs")
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
