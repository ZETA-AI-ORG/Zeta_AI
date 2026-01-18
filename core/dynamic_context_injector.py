"""
🎯 INJECTEUR DE CONTEXTE DYNAMIQUE - ARCHITECTURE SIMPLIFIÉE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Responsabilité : Collecter UNIQUEMENT les infos dynamiques essentielles
- ✅ Regex livraison : Zone + frais + délai
- ✅ Cache Gemini : Descriptions produits
- ✅ Meili : Coûts temps réel + stock UNIQUEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from typing import Dict, Any, Optional, Tuple
import asyncio


class DynamicContextInjector:
    """Injecteur de contexte dynamique minimal"""
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # REGEX LIVRAISON (ZONES ABIDJAN + FRAIS)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    DELIVERY_ZONES = {
        # Macro-zone (ne pas inventer de frais/délai: nécessite commune/quartier)
        "abidjan": {"fee": None, "delay": None},
        # Zones centrales Abidjan (1500F)
        "cocody": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        "plateau": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        "marcory": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        "treichville": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        "adjamé": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        
        # Zones périphériques Abidjan (2000F)
        "yopougon": {"fee": 2000, "delay": "Jour même si commande avant 11h"},
        "abobo": {"fee": 2000, "delay": "Jour même si commande avant 11h"},
        "koumassi": {"fee": 2000, "delay": "Jour même si commande avant 11h"},
        "port-bouët": {"fee": 2000, "delay": "Jour même si commande avant 11h"},
        "bingerville": {"fee": 2000, "delay": "Lendemain"},
        "anyama": {"fee": 2000, "delay": "Lendemain"},

        # Sous-zones / quartiers (souvent cités en premier)
        "angré": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        "angre": {"fee": 1500, "delay": "Jour même si commande avant 11h"},
        
        # Villes intérieur (à confirmer)
        "bouaké": {"fee": "3500-5000", "delay": "24-48h"},
        "yamoussoukro": {"fee": "3500-5000", "delay": "24-48h"},
        "daloa": {"fee": "3500-5000", "delay": "48-72h"},
        "san-pedro": {"fee": "3500-5000", "delay": "48-72h"},
        "korhogo": {"fee": "3500-5000", "delay": "48-72h"},
        "man": {"fee": "3500-5000", "delay": "48-72h"},
    }

    def resolve_zone_info(self, zone_text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Résout une zone (ex: issue du state tracker) vers (zone_name, zone_info)."""
        z = str(zone_text or "").strip()
        if not z:
            return None, None

        try:
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost

            z_info = extract_delivery_zone_and_cost(z)
            if z_info and z_info.get("name") and z_info.get("cost") is not None:
                return str(z_info.get("name")), {"fee": z_info.get("cost"), "delay": z_info.get("delais")}
        except Exception:
            pass
        z_lower = z.lower()

        # Match exact sur les clés connues
        if z_lower in self.DELIVERY_ZONES:
            return z.title(), self.DELIVERY_ZONES[z_lower]

        # Match par inclusion (ex: "Angré - Cité des Arts" -> "angré")
        for key, info in self.DELIVERY_ZONES.items():
            if key in z_lower:
                return key.title(), info

        return z, None
    
    def detect_delivery_zone(self, query: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Détecte la zone de livraison dans le message
        
        Returns:
            (zone_name, zone_info) ou (None, None)
        """
        try:
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost

            z_info = extract_delivery_zone_and_cost(str(query or ""))
            if z_info and z_info.get("name") and z_info.get("cost") is not None:
                return str(z_info.get("name")), {"fee": z_info.get("cost"), "delay": z_info.get("delais")}
        except Exception:
            pass

        query_lower = query.lower()
        
        # IMPORTANT: éviter les faux positifs par inclusion (ex: "man" dans "maintenant").
        # On matche uniquement sur des mots complets.
        for zone, info in self.DELIVERY_ZONES.items():
            try:
                if re.search(r"\b" + re.escape(zone) + r"\b", query_lower):
                    return zone.title(), info
            except Exception:
                # Fallback ultra-safe: si regex plante, ne pas matcher.
                continue
        
        return None, None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CACHE GEMINI (DESCRIPTIONS PRODUITS)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_product_descriptions_from_gemini(self, query: str, company_id: str) -> str:
        """
        Récupère les descriptions produits depuis le cache Gemini
        
        Args:
            query: Requête utilisateur
            company_id: ID entreprise
        
        Returns:
            Descriptions produits formatées
        """
        try:
            from core.catalog_cache_manager import get_catalog_cache_manager
            
            cache_manager = get_catalog_cache_manager()
            
            # Extraire les produits mentionnés dans la requête
            products = await cache_manager.extract_products_from_query(query, company_id)
            
            if not products:
                return "Aucun produit spécifique détecté"
            
            # Formater les descriptions
            descriptions = []
            for product in products[:3]:  # Max 3 produits pour éviter surcharge
                desc = f"• {product.get('name', 'Produit')}"
                if product.get('description'):
                    desc += f": {product['description'][:100]}"
                descriptions.append(desc)
            
            return "\n".join(descriptions)
            
        except Exception as e:
            print(f"⚠️ [GEMINI CACHE] Erreur: {e}")
            return "Descriptions produits non disponibles"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MEILI (COÛTS TEMPS RÉEL + STOCK UNIQUEMENT)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_realtime_pricing_from_meili(self, query: str, company_id: str) -> str:
        """
        Récupère UNIQUEMENT les coûts temps réel et stock depuis Meili
        
        Args:
            query: Requête utilisateur
            company_id: ID entreprise
        
        Returns:
            Infos coûts/stock formatées
        """
        try:
            from database.vector_store_clean_v2 import search_all_indexes_parallel
            
            # Recherche ciblée sur les index produits uniquement
            results = await search_all_indexes_parallel(
                query=query,
                company_id=company_id,
                limit=5,
            )
            
            if not results or len(results.strip()) == 0:
                return "Aucune info coût/stock disponible"
            
            # Extraire UNIQUEMENT prix et stock
            pricing_info = []
            lines = results.split('\n')
            
            for line in lines:
                # Chercher patterns de prix
                price_match = re.search(r'(\d+[\s\u202f]?\d{3})\s*(?:FCFA|F)', line)
                if price_match:
                    pricing_info.append(f"• Prix: {price_match.group(1)} FCFA")
                
                # Chercher patterns de stock
                stock_match = re.search(r'stock[:\s]*(\d+)', line, re.IGNORECASE)
                if stock_match:
                    pricing_info.append(f"• Stock: {stock_match.group(1)} unités")
            
            if not pricing_info:
                return "Coûts/stock non trouvés dans Meili"
            
            return "\n".join(pricing_info[:5])  # Max 5 lignes
            
        except Exception as e:
            print(f"⚠️ [MEILI PRICING] Erreur: {e}")
            return "Coûts temps réel non disponibles"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # HISTORIQUE CONVERSATION (OPTIMISÉ)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_conversation_history(self, user_id: str, company_id: str, max_messages: int = 5) -> str:
        """
        Récupère l'historique de conversation optimisé
        
        Args:
            user_id: ID utilisateur
            company_id: ID entreprise
            max_messages: Nombre max de messages
        
        Returns:
            Historique formaté
        """
        try:
            from core.optimized_conversation_memory import get_optimized_conversation_context
            
            history = get_optimized_conversation_context(user_id, company_id)
            
            if not history or len(history.strip()) == 0:
                return "Première interaction"
            
            # Tronquer si trop long
            if len(history) > 500:
                history = history[:500] + "..."
            
            return history
            
        except Exception as e:
            print(f"⚠️ [HISTORY] Erreur: {e}")
            return "Historique non disponible"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # COLLECTEUR PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def collect_dynamic_context(
        self,
        query: str,
        user_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Collecte TOUS les contextes dynamiques en parallèle
        
        Args:
            query: Requête utilisateur
            user_id: ID utilisateur
            company_id: ID entreprise
        
        Returns:
            Dict avec tous les contextes dynamiques
        """
        detected_zone, zone_info = self.detect_delivery_zone(query)

        async def history_from_supabase() -> str:
            try:
                from core.conversation import get_history

                return await get_history(company_id=company_id, user_id=user_id)
            except Exception as e:
                print(f"⚠️ [HISTORY] Erreur: {e}")
                return "Historique non disponible"

        # Prompt-only: on garde uniquement
        # - historique conversation (Supabase conversation_memory)
        # - descriptions produits depuis le Catalog Cache (Gemini)
        product_desc_task = self.get_product_descriptions_from_gemini(query, company_id)
        history_task = history_from_supabase()

        product_desc, history = await asyncio.gather(
            product_desc_task,
            history_task,
            return_exceptions=True
        )

        if isinstance(product_desc, Exception):
            product_desc = "Descriptions produits non disponibles"
        if isinstance(history, Exception):
            history = "Historique non disponible"

        if not history or not str(history).strip():
            history = "Première interaction"

        fee_val = None
        delay_val = None
        if zone_info:
            try:
                fee_val = zone_info.get("fee")
            except Exception:
                fee_val = None
            try:
                delay_val = zone_info.get("delay")
            except Exception:
                delay_val = None

        shipping_fee_out = None
        if isinstance(fee_val, int):
            shipping_fee_out = f"{fee_val} FCFA"
        elif isinstance(fee_val, str) and fee_val.strip():
            shipping_fee_out = fee_val.strip()

        delivery_time_out = None
        if isinstance(delay_val, str) and delay_val.strip():
            delivery_time_out = delay_val.strip()

        return {
            "detected_location": detected_zone,
            "shipping_fee": shipping_fee_out,
            "delivery_time": delivery_time_out,
            "product_context": str(product_desc or ""),
            "pricing_context": "",
            "conversation_history": history
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_dynamic_context_injector: Optional[DynamicContextInjector] = None

def get_dynamic_context_injector() -> DynamicContextInjector:
    """Retourne le singleton de l'injecteur de contexte"""
    global _dynamic_context_injector
    if _dynamic_context_injector is None:
        _dynamic_context_injector = DynamicContextInjector()
    return _dynamic_context_injector
