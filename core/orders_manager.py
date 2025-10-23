"""
📦 ORDERS MANAGER - Gestion des commandes via tables Lovable
Utilise la table orders (UUID) créée par Lovable
"""

import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Credentials Supabase
SUPABASE_URL = "https://ilbihprkxcgsigvueeme.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

async def get_company_uuid(company_id: str) -> Optional[str]:
    """Récupère l'UUID depuis company_mapping"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/company_mapping"
        params = {
            "company_id": f"eq.{company_id}",
            "select": "uuid"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]["uuid"]
        
        logger.warning(f"[ORDERS] Mapping introuvable pour company_id={company_id}")
        return None
        
    except Exception as e:
        logger.error(f"[ORDERS] Erreur get_company_uuid: {e}")
        return None

async def create_order(
    company_id: str,
    user_id: str,
    customer_name: str,
    total_amount: float,
    items: List[Dict],
    conversation_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Crée une commande dans la table orders (Lovable)
    
    Args:
        company_id: ID entreprise (TEXT)
        user_id: ID utilisateur
        customer_name: Nom client
        total_amount: Montant total
        items: Liste produits [{"name": "...", "quantity": 1, "price": 1000}]
        conversation_id: ID conversation (optionnel)
    
    Returns:
        Dict avec données commande créée ou None si erreur
    """
    try:
        # Récupérer UUID
        company_uuid = await get_company_uuid(company_id)
        if not company_uuid:
            logger.error(f"[ORDERS] Impossible de créer commande: UUID introuvable")
            return None
        
        # Créer commande
        url = f"{SUPABASE_URL}/rest/v1/orders"
        payload = {
            "company_id": company_uuid,
            "conversation_id": conversation_id,
            "customer_name": customer_name,
            "total_amount": total_amount,
            "status": "pending",
            "items": items
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers={**HEADERS, "Prefer": "return=representation"},
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 201:
                order = response.json()
                if isinstance(order, list) and len(order) > 0:
                    order = order[0]
                
                logger.info(f"[ORDERS] ✅ Commande créée: {order.get('id')}")
                return order
            else:
                logger.error(f"[ORDERS] Erreur création: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"[ORDERS] Exception create_order: {e}", exc_info=True)
        return None

async def get_orders(
    company_id: str,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Récupère les commandes d'une entreprise
    
    Args:
        company_id: ID entreprise (TEXT)
        status: Filtrer par statut (pending, completed, cancelled)
        limit: Nombre max de commandes
    
    Returns:
        Liste des commandes
    """
    try:
        # Récupérer UUID
        company_uuid = await get_company_uuid(company_id)
        if not company_uuid:
            return []
        
        # Récupérer commandes
        url = f"{SUPABASE_URL}/rest/v1/orders"
        params = {
            "company_id": f"eq.{company_uuid}",
            "select": "*",
            "order": "created_at.desc",
            "limit": limit
        }
        
        if status:
            params["status"] = f"eq.{status}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)
            
            if response.status_code == 200:
                orders = response.json()
                logger.info(f"[ORDERS] {len(orders)} commandes récupérées")
                return orders
            else:
                logger.error(f"[ORDERS] Erreur récupération: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"[ORDERS] Exception get_orders: {e}")
        return []

async def update_order_status(
    order_id: str,
    status: str
) -> bool:
    """
    Met à jour le statut d'une commande
    
    Args:
        order_id: UUID de la commande
        status: Nouveau statut (pending, completed, cancelled)
    
    Returns:
        True si succès, False sinon
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/orders"
        params = {
            "id": f"eq.{order_id}"
        }
        payload = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers=HEADERS,
                params=params,
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 204:
                logger.info(f"[ORDERS] ✅ Statut mis à jour: {order_id} → {status}")
                return True
            else:
                logger.error(f"[ORDERS] Erreur update: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"[ORDERS] Exception update_order_status: {e}")
        return False

async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Récupère une commande par son ID"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/orders"
        params = {
            "id": f"eq.{order_id}",
            "select": "*"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"[ORDERS] Exception get_order_by_id: {e}")
        return None
