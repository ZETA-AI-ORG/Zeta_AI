"""
📊 BOTLIVE DASHBOARD DATA - Récupération données réelles depuis Supabase
Gère les 4 endpoints dashboard prioritaires
"""

import httpx
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from core.intervention_logger import log_intervention_in_conversation_logs

logger = logging.getLogger(__name__)

# Credentials Supabase (hardcodées pour robustesse)
SUPABASE_URL = "https://ilbihprkxcgsigvueeme.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


async def _get_company_uuid(company_id: str) -> Optional[str]:
    """Mappe un company_id texte vers son UUID via company_mapping.

    Si aucun mapping n'est trouvé, on retourne None et l'appelant peut
    utiliser directement company_id (utile si c'est déjà un UUID).
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/company_mapping"
        params = [
            ("company_id_text", f"eq.{company_id}"),
            ("select", "company_id_uuid"),
            ("limit", "1"),
        ]

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=HEADERS, params=params, timeout=5.0)

        if resp.status_code == 200:
            data = resp.json() or []
            if data and data[0].get("company_id_uuid"):
                return data[0]["company_id_uuid"]

        logger.warning(f"[BOTLIVE_STATS] Mapping UUID introuvable pour company_id_text={company_id}")
        return None

    except Exception as e:
        logger.error(f"[BOTLIVE_STATS] Erreur _get_company_uuid: {e}")
        return None


async def _fetch_active_conversation_logs(
    company_id_text: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Récupère les logs de conversation actifs depuis conversation_logs.

    Utilisé pour calculer le nombre de conversations en ligne
    (clients_actifs = COUNT DISTINCT user_id avec status = 'active').
    """
    try:
        if end_date is None:
            end_date = datetime.utcnow()

        url = f"{SUPABASE_URL}/rest/v1/conversation_logs"
        params = [
            ("company_id_text", f"eq.{company_id_text}"),
            ("status", "eq.active"),
            ("created_at", f"gte.{start_date.isoformat()}"),
            ("created_at", f"lte.{end_date.isoformat()}"),
            ("select", "user_id,conversation_id,created_at,status"),
            ("order", "created_at.desc"),
            ("limit", "2000"),
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)

        if response.status_code == 200:
            data = response.json() or []
            return data
        else:
            logger.error(
                f"[SUPABASE] Erreur fetch conversation_logs actifs: {response.status_code}"
            )
            return []

    except Exception as e:
        logger.error(f"[SUPABASE] Exception fetch conversation_logs actifs: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ENDPOINT 1: GET /botlive/stats/{company_id}
# ═══════════════════════════════════════════════════════════════════════════════

async def get_live_stats(company_id: str, time_range: str = "today") -> Dict[str, Any]:
    """
    Calcule les statistiques du dashboard depuis les données réelles
    
    Returns:
        {
            "ca_live_session": 1247.0,
            "ca_variation": "+23%",
            "commandes_total": 34,
            "commandes_variation": "+12",
            "clients_actifs": 156,
            "conversations_actives": 12,
            "interventions_requises": 2
        }
    """
    try:
        # Mapper éventuellement company_id texte -> UUID
        company_uuid = company_id
        try:
            mapped = await _get_company_uuid(company_id)
            if mapped:
                company_uuid = mapped
        except Exception:
            # En cas d'erreur de mapping, continuer avec la valeur brute
            company_uuid = company_id

        # Calculer la période
        now = datetime.utcnow()
        if time_range == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "week":
            start_date = now - timedelta(days=7)
        elif time_range == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Récupérer les conversations de la période (pour commandes, interventions)
        conversations = await _fetch_conversations(company_uuid, start_date)

        # Calculer le CA à partir de la table 'orders' (total_amount)
        orders_current = await _fetch_orders(company_uuid, start_date, now)
        ca_live_session = sum(float(o.get("total_amount") or 0) for o in orders_current)

        # Calculer variation de CA par rapport à la période précédente
        prev_start = start_date - (now - start_date)
        prev_orders = await _fetch_orders(company_uuid, prev_start, start_date)
        ca_previous = sum(float(o.get("total_amount") or 0) for o in prev_orders)

        if ca_previous > 0:
            variation_pct = int(((ca_live_session - ca_previous) / ca_previous) * 100)
            ca_variation = f"+{variation_pct}%" if variation_pct > 0 else f"{variation_pct}%"
        else:
            ca_variation = "+100%" if ca_live_session > 0 else "0%"
        
        # Compter commandes totales (complétées + en cours)
        prev_conversations = await _fetch_conversations(company_uuid, prev_start, start_date)
        commandes_total = len(conversations)
        commandes_variation = f"+{commandes_total - len(prev_conversations)}"
        
        # Clients actifs & conversations actives = statut temps réel basé sur conversation_logs
        # - clients_actifs: COUNT DISTINCT user_id avec status = 'active'
        # - conversations_actives: COUNT DISTINCT conversation_id avec status = 'active'
        conversation_logs = await _fetch_active_conversation_logs(
            company_id,
            start_date,
            now,
        )

        active_user_ids = {
            log.get("user_id") for log in conversation_logs if log.get("user_id")
        }
        active_conversation_ids = {
            log.get("conversation_id")
            for log in conversation_logs
            if log.get("conversation_id")
        }

        clients_actifs = len(active_user_ids)
        conversations_actives = len(active_conversation_ids)
        
        # Interventions requises (commandes avec problèmes)
        interventions_requises = await _count_interventions(conversations)
        
        return {
            "ca_live_session": ca_live_session,
            "ca_variation": ca_variation,
            "commandes_total": commandes_total,
            "commandes_variation": commandes_variation,
            "clients_actifs": clients_actifs,
            "conversations_actives": conversations_actives,
            "interventions_requises": interventions_requises,
            "time_range": time_range,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[BOTLIVE_STATS] Erreur: {e}", exc_info=True)
        # Retourner données par défaut en cas d'erreur
        return {
            "ca_live_session": 0,
            "ca_variation": "0%",
            "commandes_total": 0,
            "commandes_variation": "+0",
            "clients_actifs": 0,
            "conversations_actives": 0,
            "interventions_requises": 0,
            "time_range": time_range,
            "updated_at": datetime.utcnow().isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ENDPOINT 2: GET /botlive/orders/active/{company_id}
# ═══════════════════════════════════════════════════════════════════════════════

async def get_active_orders(company_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Récupère les commandes EN COURS (pas encore complétées)
    
    Returns:
        [
            {
                "user_id": "+225XXXXXXXXX",
                "user_name": "Jean Martin",
                "produit": "✅ Lingettes",
                "paiement": "❌ En attente",
                "zone": "❌",
                "numero": "❌",
                "completion_rate": 25,
                "created_at": "2025-10-22T08:45:00Z"
            }
        ]
    """
    try:
        # Récupérer toutes les conversations récentes
        start_date = datetime.utcnow() - timedelta(hours=24)  # Dernières 24h
        conversations = await _fetch_conversations(company_id, start_date)
        
        # Filtrer les commandes actives (non complétées)
        active_orders = []
        
        # Grouper par user_id (dernière conversation par utilisateur)
        user_conversations = defaultdict(list)
        for conv in conversations:
            user_id = conv.get('user_id')
            if user_id:
                user_conversations[user_id].append(conv)
        
        # Pour chaque utilisateur, prendre la conversation la plus récente
        for user_id, convs in user_conversations.items():
            latest_conv = max(convs, key=lambda x: x.get('created_at', ''))
            
            # Vérifier si commande complétée
            if _is_order_completed(latest_conv):
                continue  # Ignorer les commandes complétées
            
            # Extraire l'état de la commande depuis order_state_tracker
            order_state = await _get_order_state_from_tracker(user_id)
            
            # Calculer taux de complétion
            completion_rate = _calculate_completion_rate(order_state)
            
            # Extraire nom utilisateur (si disponible dans les messages)
            user_name = _extract_user_name(latest_conv) or user_id[-4:]  # 4 derniers chiffres
            
            active_orders.append({
                "user_id": user_id,
                "user_name": user_name,
                "produit": order_state.get('produit', '❌ En attente'),
                "paiement": order_state.get('paiement', '❌ En attente'),
                "zone": order_state.get('zone', '❌'),
                "numero": order_state.get('numero', '❌'),
                "completion_rate": completion_rate,
                "created_at": latest_conv.get('created_at', datetime.utcnow().isoformat())
            })
        
        # Trier par date (plus récent en premier) et limiter
        active_orders.sort(key=lambda x: x['created_at'], reverse=True)
        return active_orders[:limit]
        
    except Exception as e:
        logger.error(f"[BOTLIVE_ACTIVE_ORDERS] Erreur: {e}", exc_info=True)
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# ⚠️ ENDPOINT 3: GET /botlive/interventions/{company_id}
# ═══════════════════════════════════════════════════════════════════════════════

async def get_interventions_required(company_id: str) -> List[Dict[str, Any]]:
    """
    Détecte les commandes nécessitant une intervention humaine
    
    Returns:
        [
            {
                "user_id": "+225XXXXXXXXX",
                "type": "payment_issue",
                "message": "Montant insuffisant: 1500 FCFA reçu, 2000 FCFA requis",
                "order_status": {...},
                "created_at": "2025-10-22T08:50:00Z"
            }
        ]
    """
    try:
        interventions = []
        
        # Récupérer commandes actives
        active_orders = await get_active_orders(company_id, limit=100)
        
        for order in active_orders:
            # Détecter problèmes
            issues = _detect_order_issues(order)

            for issue in issues:
                interventions.append({
                    "user_id": order["user_id"],
                    "type": issue["type"],
                    "message": issue["message"],
                    "order_status": {
                        "produit": order["produit"],
                        "paiement": order["paiement"],
                        "zone": order["zone"],
                        "numero": order["numero"],
                    },
                    "created_at": order["created_at"],
                })

                try:
                    await log_intervention_in_conversation_logs(
                        company_id_text=company_id,
                        user_id=order["user_id"],
                        message=issue["message"],
                        metadata={
                            "needs_intervention": True,
                            "reason": issue["type"],
                            "priority": "high",
                            "source": "order_issues_v1",
                            "completion_rate": order.get("completion_rate"),
                        },
                        channel="botlive",
                        direction="system",
                    )
                except Exception as log_err:
                    logger.error("[BOTLIVE_INTERVENTIONS] Failed to log intervention in conversation_logs: %s", log_err)
        
        return interventions
        
    except Exception as e:
        logger.error(f"[BOTLIVE_INTERVENTIONS] Erreur: {e}", exc_info=True)
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# ⚡ ENDPOINT 4: GET /botlive/activity/{company_id}
# ═══════════════════════════════════════════════════════════════════════════════

async def get_realtime_activity(company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupère l'activité en temps réel
    
    Returns:
        [
            {
                "type": "commande_enregistree",
                "client": "Sophie Laurent",
                "produit": "1x Produit A",
                "timestamp": "il y a 2 min"
            }
        ]
    """
    try:
        # Récupérer conversations récentes (dernière heure)
        start_date = datetime.utcnow() - timedelta(hours=1)
        conversations = await _fetch_conversations(company_id, start_date)
        
        activities = []
        
        for conv in conversations:
            # Déterminer le type d'activité
            activity_type, details = _classify_activity(conv)
            
            if activity_type:
                user_name = _extract_user_name(conv) or conv.get('user_id', 'Client')[-4:]
                timestamp = _format_relative_time(conv.get('created_at'))
                
                activities.append({
                    "type": activity_type,
                    "client": user_name,
                    "produit": details.get('produit', ''),
                    "timestamp": timestamp
                })
        
        # Trier par date (plus récent en premier) et limiter
        activities.sort(key=lambda x: x['timestamp'], reverse=False)
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"[BOTLIVE_ACTIVITY] Erreur: {e}", exc_info=True)
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# 🛠️ HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _fetch_conversations(company_id: str, start_date: datetime, end_date: datetime = None) -> List[Dict]:
    """Récupère les conversations depuis Supabase"""
    try:
        if end_date is None:
            end_date = datetime.utcnow()
        
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        params = [
            ("company_id", f"eq.{company_id}"),
            ("created_at", f"gte.{start_date.isoformat()}"),
            ("created_at", f"lte.{end_date.isoformat()}"),
            ("select", "*"),
            ("order", "created_at.desc"),
            ("limit", "1000"),
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[SUPABASE] Erreur fetch conversations: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"[SUPABASE] Exception fetch conversations: {e}")
        return []

async def _fetch_deposits(company_id: str, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
    """Récupère les acomptes validés depuis la table 'deposits'."""
    try:
        if end_date is None:
            end_date = datetime.utcnow()

        url = f"{SUPABASE_URL}/rest/v1/deposits"
        params = [
            ("company_id", f"eq.{company_id}"),
            ("validated_at", f"gte.{start_date.isoformat()}"),
            ("validated_at", f"lte.{end_date.isoformat()}"),
            ("select", "*"),
            ("order", "validated_at.desc"),
            ("limit", "1000"),
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"[SUPABASE] Erreur fetch deposits: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"[SUPABASE] Exception fetch deposits: {e}")
        return []

async def _fetch_orders(company_id: str, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
    """Récupère les commandes depuis la table 'orders'."""
    try:
        if end_date is None:
            end_date = datetime.utcnow()

        url = f"{SUPABASE_URL}/rest/v1/orders"
        params = [
            ("company_id", f"eq.{company_id}"),
            ("created_at", f"gte.{start_date.isoformat()}"),
            ("created_at", f"lte.{end_date.isoformat()}"),
            ("select", "*"),
            ("order", "created_at.desc"),
            ("limit", "1000"),
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"[SUPABASE] Erreur fetch orders: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"[SUPABASE] Exception fetch orders: {e}")
        return []

def _is_order_completed(conversation: Dict) -> bool:
    """Vérifie si une commande est complétée"""
    # Chercher dans le contenu de la conversation
    content = str(conversation.get('content', '')).lower()
    
    # Indicateurs de complétion
    completion_markers = [
        'commande validée',
        'commande ok',
        'on vous reviens pour la livraison',
        'merci pour votre commande',
        '✅✅✅✅'  # 4 checkmarks = tout complété
    ]
    
    return any(marker in content for marker in completion_markers)

async def _count_interventions(conversations: List[Dict]) -> int:
    """Compte le nombre d'interventions requises"""
    count = 0
    
    for conv in conversations:
        content = str(conv.get('content', '')).lower()
        
        # Indicateurs de problèmes
        if any(issue in content for issue in [
            'montant insuffisant',
            'image floue',
            'erreur',
            'problème',
            'intervention requise'
        ]):
            count += 1
    
    return count

async def _get_order_state_from_tracker(user_id: str) -> Dict[str, str]:
    """Récupère l'état depuis order_state_tracker"""
    try:
        from core.order_state_tracker import order_tracker
        state = order_tracker.get_state(user_id)
        
        return {
            'produit': f"✅ {state.produit}" if state.produit else "❌ En attente",
            'paiement': f"✅ {state.paiement}" if state.paiement else "❌ En attente",
            'zone': f"✅ {state.zone}" if state.zone else "❌",
            'numero': f"✅ {state.numero}" if state.numero else "❌"
        }
    except Exception as e:
        logger.error(f"[ORDER_STATE] Erreur: {e}")
        return {
            'produit': '❌ En attente',
            'paiement': '❌ En attente',
            'zone': '❌',
            'numero': '❌'
        }

def _calculate_completion_rate(order_state: Dict[str, str]) -> int:
    """Calcule le taux de complétion (0-100%)"""
    completed = sum(1 for v in order_state.values() if '✅' in v)
    total = len(order_state)
    return int((completed / total) * 100) if total > 0 else 0

def _extract_user_name(conversation: Dict) -> str:
    """Extrait le nom de l'utilisateur depuis la conversation.

    Préférence:
      1) metadata.user_display_name (nom complet si fourni par intégration)
      2) Sinon, identifiant utilisateur (4 derniers chiffres comme avant)
    """

    metadata = conversation.get("metadata") or {}
    # metadata peut être stocké comme JSON ou comme chaîne JSON
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    display_name = metadata.get("user_display_name")
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()

    # Fallback: on retrouve un identifiant pour conserver le comportement existant
    user_identifier = (
        metadata.get("user_id")
        or conversation.get("user_id")
        or conversation.get("customer_name")
        or "Client"
    )

    if isinstance(user_identifier, str) and len(user_identifier) >= 4:
        return user_identifier[-4:]

    return "Client"

def _detect_order_issues(order: Dict) -> List[Dict[str, str]]:
    """Détecte les problèmes dans une commande"""
    issues = []
    
    # Commande bloquée depuis trop longtemps (>30 min)
    created_at = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
    if datetime.utcnow().replace(tzinfo=created_at.tzinfo) - created_at > timedelta(minutes=30):
        if order['completion_rate'] < 100:
            issues.append({
                'type': 'stuck_order',
                'message': f"Commande bloquée à {order['completion_rate']}% depuis >30 min"
            })
    
    # Paiement manquant
    if '❌' in order['paiement'] and '✅' in order['produit']:
        issues.append({
            'type': 'payment_missing',
            'message': "Produit reçu mais paiement manquant"
        })
    
    return issues

def _classify_activity(conversation: Dict) -> tuple:
    """Classifie le type d'activité"""
    content = str(conversation.get('content', '')).lower()
    
    if 'commande validée' in content or 'commande ok' in content:
        return 'commande_enregistree', {'produit': 'Produit'}
    elif 'paiement' in content and 'reçu' in content:
        return 'paiement_en_cours', {}
    elif 'nouvelle requête' in content or 'bonjour' in content:
        return 'nouvelle_requete_client', {}
    else:
        return None, {}

def _format_relative_time(timestamp_str: str) -> str:
    """Formate un timestamp en temps relatif"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.utcnow().replace(tzinfo=timestamp.tzinfo)
        delta = now - timestamp
        
        if delta.total_seconds() < 60:
            return "il y a quelques secondes"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"il y a {minutes} min"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"il y a {hours}h"
        else:
            days = int(delta.total_seconds() / 86400)
            return f"il y a {days}j"
    except Exception:
        return "récemment"
