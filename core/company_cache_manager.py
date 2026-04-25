import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import redis
from database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class CompanyCacheManager:
    """
    Gestionnaire de cache Redis (Bloc 1).
    Mapping SÉCURISÉ basé sur l'audit réel du JSON rag_behavior.
    """
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Redis: {e}")
            self.redis_client = None
            
        self.supabase = get_supabase_client()
        self.key_prefix = "zeta:company_profile:"

    async def get_cached_company_profile(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère le profil avec mapping réel vérifié par SQL.
        """
        if not company_id:
            return {}

        redis_key = f"{self.key_prefix}{company_id}"
        
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(redis_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"⚠️ Erreur lecture Redis ({company_id}): {e}")

        try:
            # Audit SQL : On récupère rag_behavior et les colonnes de base
            resp = await asyncio.to_thread(
                self.supabase.table("company_rag_configs")
                .select("company_id, company_name, ai_name, whatsapp_phone, pro_phone, rag_behavior, secteur_activite")
                .eq("company_id", company_id)
                .execute
            )
            
            if resp.data and len(resp.data) > 0:
                raw = resp.data[0]
                
                # Parsing du rag_behavior (Contient l'adresse physique)
                rb = raw.get("rag_behavior") or {}
                if isinstance(rb, str):
                    try: rb = json.loads(rb)
                    except: rb = {}

                # Extraction des blocs métier du JSON (Vérifié par audit)
                support = rb.get("support", {})
                payment = rb.get("payment", {})
                expedition = rb.get("expedition", {})
                schedule = rb.get("schedule", {})

                # --- LOGIQUE BOUTIQUE PHYSIQUE (SANS THÉORIE) ---
                b_type = rb.get('boutique_type', 'online')
                b_sub = rb.get('subcategory') or raw.get('secteur_activite') or 'commerce'
                # L'adresse vient de rb['location']
                b_loc = rb.get('location') or 'Abidjan'
                
                if b_type == 'physique':
                    b_block = f"Boutique PHYSIQUE spécialisée en {b_sub}, située à : {b_loc}."
                else:
                    b_block = f"Boutique EN LIGNE spécialisée en {b_sub}, basée à {b_loc}. Livraison partout à Abidjan."

                # MAPPING FINAL
                profile = {
                    "company_id": company_id,
                    "shop_name": raw.get("company_name") or "Zeta Shop",
                    "bot_name": raw.get("ai_name") or "Jessica",
                    "boutique_block": b_block,
                    
                    # Contacts (Priorité Colonne SQL puis JSON)
                    "whatsapp_number": raw.get("whatsapp_phone") or support.get("whatsapp") or "non spécifié",
                    "sav_number": raw.get("pro_phone") or support.get("sav_number") or "non spécifié",
                    
                    # Paiement (Strictement depuis le JSON payment)
                    "wave_number": payment.get("wave_number") or raw.get("pro_phone") or "non spécifié",
                    "depot_amount": str(payment.get("deposit_amount") or "2000"),
                    
                    # Logistique
                    "expedition_base_fee": str(expedition.get("base_fee") or "3500"),
                    "delai_message": rb.get("delai_message") or "sous 24h à 48h",
                    
                    # Divers
                    "support_hours": schedule.get("support_hours") or raw.get("support_hours") or "Ouvert 24h/24 et 7j/7",
                    "return_policy": rb.get("return_policy") or "Contactez le support pour les retours.",
                    "faqs": rb.get("faqs", []),
                    "shop_url": f"myzeta.xyz/{company_id}"
                }
                
                if self.redis_client:
                    self.redis_client.setex(redis_key, 86400, json.dumps(profile))
                    logger.info(f"✅ [REDIS_SAVE] Profil REEL (Source JSON) synchronisé pour {company_id}")
                
                return profile
            return {}
        except Exception as e:
            logger.error(f"❌ Error syncing real profile: {e}")
            return {}

    async def invalidate_cached_profile(self, company_id: str):
        if self.redis_client:
            self.redis_client.delete(f"{self.key_prefix}{company_id}")

    async def sync_all_companies(self):
        try:
            resp = await asyncio.to_thread(self.supabase.table("company_rag_configs").select("company_id").execute)
            if resp.data:
                for row in resp.data:
                    await self.get_cached_company_profile(row['company_id'])
                return {"status": "ok", "count": len(resp.data)}
            return {"status": "empty"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Singleton
company_cache = CompanyCacheManager()
