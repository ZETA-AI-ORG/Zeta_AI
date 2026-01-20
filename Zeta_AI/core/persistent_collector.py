"""
💾 COLLECTEUR PERSISTANT - Garde les données en mémoire
Évite de redemander les mêmes infos en boucle

PRINCIPE:
- Python collecte les données (BLIP-2, OCR, Regex)
- Sauvegarde dans notepad Supabase (persistant)
- Vérifie TOUJOURS avant de redemander
- Génère checklist dynamique pour LLM
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PersistentCollector:
    """
    Collecteur persistant : garde les données collectées
    """
    
    def __init__(self):
        self.enabled = True
    
    def collect_and_persist(
        self,
        notepad: Dict[str, Any],
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        message: str
    ) -> Dict[str, Any]:
        """
        Collecte les données et les persiste dans notepad
        
        Returns:
            {
                "state": dict (état complet),
                "missing": list (ce qui manque),
                "checklist": str (pour LLM),
                "updated": bool (données mises à jour?)
            }
        """
        
        updated = False
        
        # 1. COLLECTER PHOTO (BLIP-2)
        if vision_result and not (notepad.get("photo_produit") or notepad.get("photo_produit_description")):
            desc = vision_result.get("description", "")
            if desc and any(kw in desc.lower() for kw in ["bag", "diaper", "couche", "paquet", "pack"]):
                notepad["photo_produit"] = desc
                notepad["photo_produit_date"] = datetime.now().isoformat()
                updated = True
                logger.info(f"📸 [PERSIST] Photo collectée: {desc}")
        
        # 2. COLLECTER PAIEMENT (OCR)
        if ocr_result and ocr_result.get("valid") and not notepad.get("paiement"):
            montant = ocr_result.get("amount")
            notepad["paiement"] = {
                "montant": montant,
                "validé": True,
                "date": datetime.now().isoformat()
            }
            updated = True
            logger.info(f"💳 [PERSIST] Paiement collecté: {montant}F")
        
        # 3. COLLECTER ZONE (Regex)
        if not notepad.get("delivery_zone"):
            zone = self._extract_zone(message)
            if zone:
                notepad["delivery_zone"] = zone["name"]
                notepad["delivery_cost"] = zone["cost"]
                notepad["delivery_zone_date"] = datetime.now().isoformat()
                updated = True
                logger.info(f"📍 [PERSIST] Zone collectée: {zone['name']} ({zone['cost']}F)")
        
        # 4. COLLECTER TÉLÉPHONE (Regex)
        if not notepad.get("phone_number"):
            tel = self._extract_phone(message)
            if tel and tel["valid"]:
                notepad["phone_number"] = tel["normalized"]
                notepad["phone_number_date"] = datetime.now().isoformat()
                updated = True
                logger.info(f"📞 [PERSIST] Téléphone collecté: {tel['normalized']}")
        
        # 5. GÉNÉRER ÉTAT COMPLET (avec BLIP-2 pour photo)
        state = self._generate_state(notepad, vision_result)
        
        # 6. DÉTECTER CE QUI MANQUE
        missing = self._get_missing(state)
        
        # 7. GÉNÉRER CHECKLIST POUR LLM
        checklist = self._generate_checklist(state)
        
        return {
            "state": state,
            "missing": missing,
            "checklist": checklist,
            "updated": updated,
            "notepad": notepad
        }
    
    def _extract_zone(self, message: str) -> Optional[Dict[str, Any]]:
        """Extrait zone depuis message (regex)"""
        
        message_lower = message.lower()
        
        zones_abidjan = {
            "abobo": 1500, "adjamé": 1500, "attécoubé": 1500,
            "cocody": 1500, "koumassi": 1500, "marcory": 1500,
            "plateau": 1500, "port-bouët": 2000, "port bouet": 2000,
            "treichville": 1500, "yopougon": 1500,
            "bingerville": 2000, "songon": 2000, "anyama": 2000
        }
        
        for zone, cost in zones_abidjan.items():
            if zone in message_lower:
                return {
                    "name": zone.capitalize(),
                    "cost": cost
                }
        
        return None
    
    def _validate_phone(self, phone: Optional[str]) -> bool:
        """Valide format téléphone (10 chiffres)"""
        if not phone:
            return False
        try:
            digits = ''.join(filter(str.isdigit, str(phone)))
            return len(digits) == 10
        except Exception:
            return False
    
    def _extract_phone(self, message: str) -> Optional[Dict[str, Any]]:
        """Extrait téléphone depuis message (regex)"""
        
        import re
        
        # Pattern: 10 chiffres (0XXXXXXXXX)
        phone_pattern = r'\b(0[0-9]{9})\b'
        match = re.search(phone_pattern, message)
        
        if match:
            phone = match.group(1)
            
            # Valider préfixe CI
            prefixes_valides = ['07', '05', '01']  # Orange, MTN, Moov
            if phone[:2] in prefixes_valides:
                return {
                    "normalized": phone,
                    "valid": True
                }
        
        return None
    
    def _generate_state(self, notepad: Dict[str, Any], vision_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Génère l'état complet depuis notepad + BLIP-2 pour photo"""
        
        # PHOTO: Écouter BLIP-2 directement (plus fiable)
        photo_collected = False
        photo_data = None
        
        if vision_result and vision_result.get("description"):
            # BLIP-2 a détecté quelque chose
            desc = vision_result["description"]
            if any(kw in desc.lower() for kw in ["bag", "diaper", "couche", "paquet", "pack", "wipe", "lingette"]):
                photo_collected = True
                photo_data = desc
        elif notepad.get("photo_produit") or notepad.get("photo_produit_description"):
            # Fallback: données persistées
            photo_collected = True
            photo_data = notepad.get("photo_produit") or notepad.get("photo_produit_description")
        
        return {
            "photo": {
                "collected": photo_collected,
                "data": photo_data
            },
            "paiement": {
                "collected": bool(notepad.get("paiement")),
                "data": notepad.get("paiement", {}).get("montant") if notepad.get("paiement") else None
            },
            "zone": {
                "collected": bool(notepad.get("delivery_zone")),
                "data": notepad.get("delivery_zone"),
                "cost": notepad.get("delivery_cost", 1500)
            },
            "tel": {
                "collected": bool(notepad.get("phone_number")),
                "data": notepad.get("phone_number"),
                "valid": self._validate_phone(notepad.get("phone_number"))
            }
        }
    
    def _get_missing(self, state: Dict[str, Any]) -> List[str]:
        """Retourne la liste des éléments manquants"""
        
        missing = []
        
        if not state["photo"]["collected"]:
            missing.append("photo")
        if not state["paiement"]["collected"]:
            missing.append("paiement")
        if not state["zone"]["collected"]:
            missing.append("zone")
        if not state["tel"]["collected"]:
            missing.append("tel")
        elif not state["tel"]["valid"]:
            missing.append("tel_invalid")
        
        return missing
    
    def _generate_checklist(self, state: Dict[str, Any]) -> str:
        """
        Génère checklist dynamique pour LLM
        
        Format:
        ✅ Photo reçue
        ✅ Paiement validé (2020F)
        ❌ Zone manquante
        ❌ Téléphone manquant
        """
        
        lines = []
        
        # Photo
        if state["photo"]["collected"]:
            lines.append("✅ Photo reçue")
        else:
            lines.append("❌ Photo manquante")
        
        # Paiement
        if state["paiement"]["collected"]:
            montant = state["paiement"]["data"]
            lines.append(f"✅ Paiement validé ({montant}F)")
        else:
            lines.append("❌ Paiement manquant")
        
        # Zone
        if state["zone"]["collected"]:
            zone = state["zone"]["data"]
            frais = state["zone"]["cost"]
            lines.append(f"✅ Zone: {zone} ({frais}F)")
        else:
            lines.append("❌ Zone manquante")
        
        # Téléphone
        if state["tel"]["collected"] and state["tel"]["valid"]:
            tel = state["tel"]["data"]
            lines.append(f"✅ Téléphone: {tel}")
        elif state["tel"]["collected"] and not state["tel"]["valid"]:
            lines.append("⚠️ Téléphone invalide")
        else:
            lines.append("❌ Téléphone manquant")
        
        return "\n".join(lines)


# Instance globale
_collector = None

def get_collector() -> PersistentCollector:
    """Retourne l'instance singleton"""
    global _collector
    if _collector is None:
        _collector = PersistentCollector()
    return _collector
