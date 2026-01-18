import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class HumanNotificationService:
    """
    Notifie le vendeur humain en temps réel (WhatsApp, SMS, Push)
    """
    
    def __init__(self):
        # Pour l'instant, pas de clients réels WhatsApp/SMS injectés, on logue juste.
        self.pending_notifications = {}
    
    async def notify_vendor(
        self,
        company_id: str,
        user_id: str,
        user_name: str,
        question: str,
        reason: str,
        context: dict
    ):
        """
        Envoie notification immédiate au vendeur
        """
        
        # Simulation récupération config vendeur
        # Dans un cas réel, on irait chercher ça en DB via company_id
        vendor_name = context.get("vendor_name", "Vendeur")
        vendor_phone = context.get("vendor_phone", "Unknown")
        
        # Construire message notification
        notification_text = f"""
🔔 QUESTION CLIENT - {context.get('company_name', 'Boutique')}

👤 Client : {user_name}
📱 Tel : {context.get('phone', 'Non fourni')}
📍 Zone : {context.get('zone', 'Non fournie')}

❓ QUESTION :
"{question}"

🤖 Jessica a dit :
"Je préviens {vendor_name} qui va te répondre dans 30 secondes."

⏰ Reçu : {datetime.now().strftime('%H:%M:%S')}

➡️ Réponds via le tableau de bord ou directement par WhatsApp
"""
        
        # Envoi simulé (Log)
        logger.info(f"======== [NOTIFICATION HUMAIN] POUR {vendor_name} ({vendor_phone}) ========")
        logger.info(notification_text)
        logger.info("==========================================================================")
        
        # Marquer comme en attente
        self.pending_notifications[user_id] = {
            'notified_at': datetime.now(),
            'company_id': company_id,
            'reason': reason
        }
        
        return True
