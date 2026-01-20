#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗒️ NOTEPAD SUPABASE - Persistance sécurisée avec auto-cleanup
Stocke les données de commande dans Supabase avec expiration automatique 7 jours
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta
import logging
import os
import httpx

logger = logging.getLogger(__name__)

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ilbihprkxcgsigvueeme.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA")

# Durée de rétention (7 jours)
RETENTION_DAYS = 7


class SupabaseNotepad:
    """
    Notepad persistant dans Supabase avec auto-cleanup
    
    Table: conversation_notepad
    Colonnes:
    - id (UUID, PK)
    - user_id (TEXT)
    - company_id (TEXT)
    - data (JSONB) - Contient tous les champs du notepad
    - created_at (TIMESTAMP)
    - updated_at (TIMESTAMP)
    - expires_at (TIMESTAMP) - Auto-calculé: created_at + 7 jours
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Retourne l'instance singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        logger.info("📋 SupabaseNotepad initialisé (persistance Supabase)")
    
    async def get_notepad(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """
        Récupère ou crée un notepad depuis Supabase
        
        Args:
            user_id: ID utilisateur (lié à auth.users si authentifié)
            company_id: ID entreprise
            
        Returns:
            Dict contenant les données du notepad
        """
        try:
            # 1. Chercher notepad existant
            url = f"{SUPABASE_URL}/rest/v1/conversation_notepad"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            params = {
                "user_id": f"eq.{user_id}",
                "company_id": f"eq.{company_id}",
                "select": "*",
                "order": "updated_at.desc",
                "limit": "1"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if results and len(results) > 0:
                        notepad_row = results[0]
                        
                        # Vérifier expiration
                        expires_at = datetime.fromisoformat(notepad_row['expires_at'].replace('Z', '+00:00'))
                        if expires_at < datetime.now(expires_at.tzinfo):
                            logger.info(f"🗑️ Notepad expiré pour {user_id}, suppression...")
                            await self._delete_notepad(notepad_row['id'])
                            return await self._create_new_notepad(user_id, company_id)
                        
                        # Notepad valide
                        logger.info(f"📋 Notepad chargé depuis Supabase: {user_id}")
                        return notepad_row['data']
                    else:
                        # Pas de notepad existant
                        return await self._create_new_notepad(user_id, company_id)
                else:
                    logger.error(f"❌ Erreur Supabase get_notepad: {response.status_code}")
                    return self._get_empty_notepad()
                    
        except Exception as e:
            logger.error(f"❌ Erreur get_notepad: {e}")
            return self._get_empty_notepad()
    
    async def _create_new_notepad(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Crée un nouveau notepad dans Supabase"""
        try:
            now = datetime.now()
            expires_at = now + timedelta(days=RETENTION_DAYS)
            
            empty_data = self._get_empty_notepad()
            empty_data['created_at'] = now.isoformat()
            empty_data['last_updated'] = now.isoformat()
            
            url = f"{SUPABASE_URL}/rest/v1/conversation_notepad"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            payload = {
                "user_id": user_id,
                "company_id": company_id,
                "data": empty_data,
                "expires_at": expires_at.isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 201:
                    logger.info(f"✅ Nouveau notepad créé: {user_id} (expire: {expires_at.strftime('%Y-%m-%d')})")
                    return empty_data
                else:
                    logger.error(f"❌ Erreur création notepad: {response.status_code}")
                    return empty_data
                    
        except Exception as e:
            logger.error(f"❌ Erreur _create_new_notepad: {e}")
            return self._get_empty_notepad()
    
    async def update_notepad(self, user_id: str, company_id: str, data: Dict[str, Any]) -> bool:
        """
        Met à jour le notepad dans Supabase
        
        Args:
            user_id: ID utilisateur
            company_id: ID entreprise
            data: Nouvelles données à sauvegarder
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Ajouter timestamp de mise à jour
            data['last_updated'] = datetime.now().isoformat()
            
            url = f"{SUPABASE_URL}/rest/v1/conversation_notepad"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            params = {
                "user_id": f"eq.{user_id}",
                "company_id": f"eq.{company_id}"
            }
            payload = {"data": data}
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, headers=headers, params=params, json=payload)
                
                if response.status_code in [200, 204]:
                    logger.info(f"✅ Notepad mis à jour: {user_id}")
                    return True
                else:
                    logger.error(f"❌ Erreur update notepad: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Erreur update_notepad: {e}")
            return False
    
    async def clear_notepad(self, user_id: str, company_id: str) -> bool:
        """
        Vide complètement un notepad (pour nouvelle conversation)
        
        Args:
            user_id: ID utilisateur
            company_id: ID entreprise
            
        Returns:
            True si succès, False sinon
        """
        try:
            url = f"{SUPABASE_URL}/rest/v1/conversation_notepad"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            params = {
                "user_id": f"eq.{user_id}",
                "company_id": f"eq.{company_id}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, params=params)
                
                if response.status_code in [200, 204]:
                    logger.info(f"🔄 Notepad vidé: {user_id}")
                    return True
                else:
                    logger.error(f"❌ Erreur clear notepad: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Erreur clear_notepad: {e}")
            return False
    
    async def _delete_notepad(self, notepad_id: str) -> bool:
        """Supprime un notepad expiré"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/conversation_notepad"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            params = {"id": f"eq.{notepad_id}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, params=params)
                
                if response.status_code in [200, 204]:
                    logger.info(f"🗑️ Notepad supprimé: {notepad_id}")
                    return True
                else:
                    logger.error(f"❌ Erreur suppression notepad: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Erreur _delete_notepad: {e}")
            return False
    
    async def cleanup_expired_notepads(self) -> int:
        """
        Nettoie tous les notepads expirés (> 7 jours)
        À appeler périodiquement (cron job)
        
        Returns:
            Nombre de notepads supprimés
        """
        try:
            now = datetime.now().isoformat()
            
            url = f"{SUPABASE_URL}/rest/v1/conversation_notepad"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            params = {
                "expires_at": f"lt.{now}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, params=params)
                
                if response.status_code in [200, 204]:
                    # Supabase ne retourne pas le nombre de lignes supprimées
                    logger.info(f"🧹 Cleanup notepads expirés effectué")
                    return 0  # Impossible de savoir combien sans SELECT avant
                else:
                    logger.error(f"❌ Erreur cleanup: {response.status_code}")
                    return 0
                    
        except Exception as e:
            logger.error(f"❌ Erreur cleanup_expired_notepads: {e}")
            return 0
    
    def _get_empty_notepad(self) -> Dict[str, Any]:
        """Retourne un notepad vide"""
        return {
            "created_at": None,
            "products": [],
            "quantities": [],
            "delivery_zone": None,
            "delivery_cost": None,
            "payment_method": None,
            "payment_number": None,
            "phone_number": None,
            "photo_produit": None,
            "paiement": None,
            "calculated_totals": {},
            "last_updated": None,
            "conversation_count": 0,
            "last_product_mentioned": None
        }


# Instance globale
_supabase_notepad_instance = None

def get_supabase_notepad() -> SupabaseNotepad:
    """Retourne l'instance singleton du notepad Supabase"""
    global _supabase_notepad_instance
    if _supabase_notepad_instance is None:
        _supabase_notepad_instance = SupabaseNotepad()
    return _supabase_notepad_instance
