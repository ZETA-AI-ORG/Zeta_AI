"""
Gestionnaire d'état conversationnel pour le mode Botlive.
Stocke les images et détections par utilisateur pendant le processus de commande.
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict


class LiveConversationState:
    """Gère l'état de la conversation Live par utilisateur"""
    
    def __init__(self, storage_path: str = "./data/live_sessions.json"):
        self.storage_path = storage_path
        self.sessions: Dict[str, dict] = {}
        self._ensure_dir()
        self._load()
    
    def _ensure_dir(self):
        """Crée le dossier data/ si nécessaire"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
    
    def _load(self):
        """Charge les sessions depuis le disque"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.sessions = json.load(f)
            except Exception:
                self.sessions = {}
        else:
            self.sessions = {}
    
    def _save(self):
        """Sauvegarde les sessions sur disque"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            print(f"[LiveState] Erreur sauvegarde: {e}")
    
    def add_detection(self, user_id: str, company_id: str, image_url: str, 
                     detection_result: dict, detection_type: str) -> str:
        """
        Ajoute une détection d'image pour un utilisateur.
        
        Args:
            user_id: ID utilisateur Messenger
            company_id: ID entreprise
            image_url: URL de l'image
            detection_result: résultat YOLO ou OCR
            detection_type: 'product' ou 'payment'
        
        Returns:
            'ready' si les 2 images sont complètes, 'collecting' sinon
        """
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "company_id": company_id,
                "product_img": None,
                "product_detection": None,
                "payment_img": None,
                "payment_detection": None,
                "delivery_zone": None,
                "status": "collecting",
                "created_at": datetime.utcnow().isoformat()
            }
        
        session = self.sessions[user_id]
        
        if detection_type == "product":
            session["product_img"] = image_url
            session["product_detection"] = detection_result
        elif detection_type == "payment":
            session["payment_img"] = image_url
            session["payment_detection"] = detection_result
        
        # Vérifier si complet
        if session["product_img"] and session["payment_img"]:
            session["status"] = "ready"
            self._save()
            return "ready"
        
        self._save()
        return "collecting"
    
    def get_missing(self, user_id: str) -> Optional[str]:
        """
        Retourne ce qui manque pour finaliser la commande.
        
        Returns:
            'product': image produit manquante
            'payment': image paiement manquante
            'both': les 2 manquent
            None: commande complète
        """
        if user_id not in self.sessions:
            return "both"
        
        session = self.sessions[user_id]
        has_product = session.get("product_img") is not None
        has_payment = session.get("payment_img") is not None
        
        if not has_product and not has_payment:
            return "both"
        elif not has_product:
            return "product"
        elif not has_payment:
            return "payment"
        else:
            return None
    
    def get_session(self, user_id: str) -> Optional[dict]:
        """Récupère la session complète d'un utilisateur"""
        return self.sessions.get(user_id)
    
    def get_context_for_llm(self, user_id: str) -> str:
        """
        Génère un contexte textuel pour le LLM avec les détections actuelles.
        
        Returns:
            Texte formaté décrivant l'état actuel de la commande
        """
        if user_id not in self.sessions:
            return "[Aucune image reçue pour le moment]"
        
        session = self.sessions[user_id]
        parts = []
        
        if session.get("product_detection"):
            det = session["product_detection"]
            parts.append(f"📦 IMAGE PRODUIT DÉTECTÉE: {det.get('name', 'inconnu')} (confiance: {det.get('confidence', 0)*100:.1f}%)")
        else:
            parts.append("📦 IMAGE PRODUIT: non reçue")
        
        if session.get("payment_detection"):
            det = session["payment_detection"]
            amount = det.get("amount", "")
            currency = det.get("currency", "")
            ref = det.get("reference", "")
            if amount and currency:
                parts.append(f"💳 PAIEMENT DÉTECTÉ: {amount} {currency}" + (f" | Réf: {ref}" if ref else ""))
            else:
                parts.append("💳 IMAGE PAIEMENT: reçue mais montant non lisible")
        else:
            parts.append("💳 IMAGE PAIEMENT: non reçue")

        # Zone de livraison si connue
        zone = session.get("delivery_zone")
        if zone:
            parts.append(f"🚚 ZONE LIVRAISON: {zone}")
        
        return "\n".join(parts)
    
    def clear(self, user_id: str):
        """Supprime la session d'un utilisateur après validation"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            self._save()
    
    def reset(self, user_id: str):
        """Alias pour clear (compatibilité)"""
        self.clear(user_id)

    # --- Métadonnées supplémentaires ---
    def set_delivery_zone(self, user_id: str, zone: str):
        if not user_id:
            return
        if user_id not in self.sessions:
            self.sessions[user_id] = {"company_id": "", "product_img": None, "product_detection": None,
                                     "payment_img": None, "payment_detection": None, "delivery_zone": None,
                                     "status": "collecting", "created_at": datetime.utcnow().isoformat()}
        self.sessions[user_id]["delivery_zone"] = zone
        self._save()


# Singleton global
_live_state_instance = None

def get_live_conversation_state() -> LiveConversationState:
    """Retourne l'instance singleton du gestionnaire d'état Live"""
    global _live_state_instance
    if _live_state_instance is None:
        _live_state_instance = LiveConversationState()
    return _live_state_instance
