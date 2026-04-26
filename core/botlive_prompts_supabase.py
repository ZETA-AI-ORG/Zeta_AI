#!/usr/bin/env python3
"""
🗄️ BOTLIVE PROMPTS SUPABASE - Récupération dynamique des prompts par company_id
Remplace les prompts hardcodés par des prompts stockés en base de données
"""

import os
import re
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client
import asyncio
import time
import redis
import json

try:
    from .zlog import zlog, zlog_error
except ImportError:
    try:
        from core.zlog import zlog, zlog_error
    except ImportError:
        def zlog(*a, **kw): pass
        def zlog_error(*a, **kw): pass

# Chemin vers le prompt universel V2.0 (BLOC 1 statique)
_LOCAL_PATH_ENV = os.getenv("LOCAL_PROMPT_PATH")
if _LOCAL_PATH_ENV and os.path.isfile(_LOCAL_PATH_ENV):
    _PROMPT_UNIVERSEL_V2_PATH = os.path.abspath(_LOCAL_PATH_ENV)
else:
    _PROMPT_UNIVERSEL_V2_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompt_universel_v2.md")
# Cache global BLOC 1 / BLOC 2 template (partagé entre toutes les instances)
_ZETA_CORE_CACHE: Dict[str, str] = {}

logger = logging.getLogger(__name__)


def _normalize_company_id(company_id: Any) -> str:
    return str(company_id or "").strip()

class BotlivePromptsManager:
    """
    Gestionnaire de prompts Botlive depuis Supabase
    """
    
    def __init__(self):
        """Initialise la connexion Supabase"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL et SUPABASE_SERVICE_KEY requis dans .env")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self._cache = {}  # Cache en mémoire pour performance (legacy)
        self._cache_timestamps = {}  # Timestamps pour TTL (legacy)
        
        # Initialisation Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            logger.info(f"✅ Redis initialisé pour le cache des prompts ({redis_url})")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Redis: {e}")
            self.redis_client = None

        enabled_raw = (os.getenv("PROMPT_LOCAL_CACHE_ENABLED", "true") or "true").strip().lower()
        self._cache_enabled = enabled_raw in {"1", "true", "yes", "y", "on"}
        try:
            self._cache_ttl = int(os.getenv("PROMPT_CACHE_TTL", "3600") or 3600)
        except Exception:
            self._cache_ttl = 3600
        if self._cache_ttl < 0:
            self._cache_ttl = 0
        
        logger.info("✅ BotlivePromptsManager initialisé avec Supabase")
        logger.info("🗑️ Cache prompts vidé (démarrage propre)")
        logger.info(
            "📦 [PROMPT_CACHE] local_cache=%s ttl=%ss",
            "on" if self._cache_enabled else "off",
            self._cache_ttl,
        )

    def _cache_get(self, cache_key: str) -> Optional[str]:
        try:
            if not getattr(self, "_cache_enabled", True):
                return None
            if cache_key not in self._cache:
                return None
            ts = float(self._cache_timestamps.get(cache_key) or 0.0)
            if ts <= 0.0:
                return None
            age = time.time() - ts
            ttl = float(getattr(self, "_cache_ttl", 0) or 0)
            if ttl <= 0:
                return None
            if age > ttl:
                # TTL expired
                try:
                    self._cache.pop(cache_key, None)
                    self._cache_timestamps.pop(cache_key, None)
                except Exception:
                    pass
                return None
            return self._cache.get(cache_key)
        except Exception:
            return None

    def _cache_set(self, cache_key: str, value: str) -> None:
        try:
            if not getattr(self, "_cache_enabled", True):
                return
            self._cache[cache_key] = value
            self._cache_timestamps[cache_key] = time.time()
        except Exception:
            pass
    
    async def get_prompt(self, company_id: str = None, llm_choice: str = "groq", bot_type: str = "jessica") -> str:
        """
        Récupère le prompt depuis Redis (cache) ou Supabase (fallback table prompt_bots)
        """
        redis_key = f"zeta:prompts:{bot_type}"
        
        # 1. Vérifier Redis
        if self.redis_client:
            try:
                cached = self.redis_client.get(redis_key)
                if cached:
                    # logger.info(f"🚀 [REDIS_HIT] Prompt {bot_type} récupéré depuis le cache")
                    return cached
            except Exception as e:
                logger.warning(f"⚠️ Erreur lecture Redis: {e}")

        # 2. Fallback Supabase (table prompt_bots)
        logger.info(f"📡 [REDIS_MISS] Récupération prompt {bot_type} depuis Supabase (table prompt_bots)...")
        try:
            # Note: on utilise asyncio.to_thread car le client supabase-py est synchrone
            response = await asyncio.to_thread(
                self.supabase.table("prompt_bots")
                .select("prompt_content")
                .eq("bot_type", bot_type)
                .eq("is_active", True)
                .execute
            )
            
            if response.data and len(response.data) > 0:
                prompt = response.data[0]["prompt_content"]
                # Stocker dans Redis (24h)
                if self.redis_client:
                    try:
                        self.redis_client.setex(redis_key, 86400, prompt)
                        logger.info(f"💾 [REDIS_SAVE] Prompt {bot_type} mis en cache pour 24h")
                    except Exception as ree:
                        logger.warning(f"⚠️ Erreur écriture Redis: {ree}")
                return prompt
        except Exception as e:
            logger.error(f"❌ Erreur critique Supabase prompt_bots: {e}")

        # 3. Fallback ultime : ancien système V1 (par entreprise)
        return await self.get_prompt_v1_fallback(company_id, llm_choice)

    async def get_company_profile(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère les données de configuration d'une entreprise.
        Priorité Redis (company_profile:{id}) -> Fallback Supabase (company_rag_configs).
        """
        company_id = _normalize_company_id(company_id)
        if not company_id:
            return {}

        redis_key = f"company_profile:{company_id}"
        
        # 1. Tenter Redis
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(redis_key)
                if cached_data:
                    # logger.info(f"🚀 [REDIS_HIT] Profile chargé pour {company_id}")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"⚠️ Erreur lecture profil Redis: {e}")

        # 2. Fallback Supabase
        logger.info(f"🔍 [SUPABASE_FALLBACK] Chargement profil pour {company_id}")
        try:
            # On utilise asyncio.to_thread car le client supabase-py est synchrone
            resp = await asyncio.to_thread(
                self.supabase.table("company_rag_configs")
                .select("*")
                .eq("company_id", company_id)
                .execute
            )
            
            if resp.data and len(resp.data) > 0:
                profile = resp.data[0]
                # Mise en cache Redis (TTL 24h)
                if self.redis_client:
                    try:
                        self.redis_client.setex(redis_key, 86400, json.dumps(profile))
                        logger.info(f"✅ [REDIS_SAVE] Profile mis en cache pour {company_id}")
                    except Exception as e:
                        logger.error(f"⚠️ Erreur sauvegarde profil Redis: {e}")
                return profile
        except Exception as e:
            logger.error(f"❌ Erreur Supabase Profile {company_id}: {e}")
        
        return {}

    def safe_inject_variables(self, prompt: str, company_data: Dict[str, Any]) -> str:
        """
        Remplacement sécurisé des balises par .replace() pour éviter les crashs .format().
        """
        if not prompt:
            return ""
            
        # Valeurs par défaut sécurisées
        replacements = {
            "{bot_name}": company_data.get("bot_name") or company_data.get("ai_name") or "Assistante",
            "{shop_name}": company_data.get("shop_name") or company_data.get("company_name") or "notre boutique",
            "{whatsapp_number}": company_data.get("whatsapp_number") or "non spécifié",
            "{sav_number}": company_data.get("sav_number") or company_data.get("whatsapp_number") or "non spécifié",
            "{return_policy}": company_data.get("return_policy") or "Veuillez nous contacter pour les retours.",
            "{boutique_block}": company_data.get("boutique_block") or "",
            "{expedition_base_fee}": str(company_data.get("expedition_base_fee") or "selon zone"),
            "{delai_message}": company_data.get("delai_message") or "quelques minutes",
            "{support_hours}": company_data.get("support_hours") or "24h/7j",
            "{wave_number}": company_data.get("wave_number") or "disponible sur demande",
            "{depot_amount}": str(company_data.get("depot_amount") or "0"),
        }

        # Remplacement en chaîne
        final_prompt = prompt
        for tag, value in replacements.items():
            final_prompt = final_prompt.replace(tag, str(value or ""))
            
        return final_prompt

    async def get_prompt_v1_fallback(self, company_id: str, llm_choice: str) -> str:
        """
        Récupère le prompt Botlive depuis Supabase
        
        Args:
            company_id: Identifiant unique de l'entreprise
            llm_choice: "groq-70b" ou "deepseek-v3"
        
        Returns:
            str: Prompt formaté pour le LLM
        
        Raises:
            ValueError: Si company_id invalide ou prompts manquants
        """
        # ✅ PRIORITÉ SUPRÊME : Fichier local si LOCAL_PROMPT_PATH est défini
        local_override_path = os.getenv("LOCAL_PROMPT_PATH")
        if local_override_path:
            try:
                if os.path.isfile(local_override_path):
                    with open(local_override_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        logger.info(f"🚀 [PROMPT_OVERRIDE] Utilisation du fichier local: {local_override_path} ({len(content)} chars)")
                        # On simule un tag pour le cache si besoin, mais on retourne direct
                        return content
                else:
                    logger.warning(f"⚠️ [PROMPT_OVERRIDE] LOCAL_PROMPT_PATH défini mais fichier introuvable: {local_override_path}")
            except Exception as e:
                logger.error(f"❌ [PROMPT_OVERRIDE] Erreur lecture fichier local: {e}")

        company_id = _normalize_company_id(company_id)
        print(f"[DEBUG] Appel get_prompt avec company_id={company_id}, llm_choice={llm_choice}")

        original_llm_choice = llm_choice
        # IMPORTANT: pour OpenRouter on force le prompt Supabase DeepSeek (champ prompt_botlive_deepseek_v3).
        # C'est là que le prompt "global + catalogue" est stocké.
        if llm_choice == "openrouter":
            llm_choice = "deepseek-v3"

        logger.info(
            "🧩 [PROMPT_SOURCE] runtime_llm_choice=%s resolved_prompt_source=%s",
            original_llm_choice,
            llm_choice,
        )

        # NOTE: le cache est versionné après lecture Supabase via botlive_prompts_updated_at.
        # Ici on ne peut donc pas faire de cache-hit avant d'avoir l'info de version.
        if not getattr(self, "_cache_enabled", True):
            logger.info("📦 [CACHE] Cache désactivé (PROMPT_LOCAL_CACHE_ENABLED=false)")
        
        try:
            # Récupérer depuis Supabase (table company_rag_configs)
            logger.info(f"🔍 [SUPABASE] Requête: table=company_rag_configs, company_id={company_id}")
            response = await asyncio.to_thread(
                self.supabase.table("company_rag_configs") \
                .select("prompt_botlive_groq_70b, prompt_botlive_deepseek_v3, company_name, ai_name, botlive_prompts_updated_at") \
                .eq("company_id", company_id) \
                .execute
            )
            
            if not response.data or len(response.data) == 0:
                raise ValueError(f"❌ Aucune config trouvée pour company_id: {company_id}")
            
            data = response.data[0] if isinstance(response.data, list) else response.data

            # Version pour invalidation automatique du cache local.
            version_tag = str(data.get("botlive_prompts_updated_at") or "").strip() or "noversion"
            cache_key = f"{company_id}_{original_llm_choice}_{version_tag}"
            cached = self._cache_get(cache_key)
            if cached is not None:
                logger.info(f"📦 [CACHE] Cache hit pour {cache_key} ({len(cached)} chars)")
                return cached
            
            # Sélectionner le bon prompt
            if llm_choice == "groq-70b":
                prompt = data.get("prompt_botlive_groq_70b")
                if not prompt:
                    raise ValueError(f"❌ Prompt Groq 70B manquant pour {company_id}")
            elif llm_choice == "deepseek-v3":
                prompt = data.get("prompt_botlive_deepseek_v3")
                if not prompt:
                    raise ValueError(f"❌ Prompt DeepSeek V3 manquant pour {company_id}")
            else:
                raise ValueError(f"❌ llm_choice invalide: {llm_choice}")
            
            # Mettre en cache
            self._cache_set(cache_key, prompt)
            
            print(f"[DEBUG SUPABASE] Prompt récupéré: {len(prompt)} chars")
            print(f"[DEBUG SUPABASE] Début du prompt: {prompt[:200]}...")
            logger.info(f"✅ Prompt {llm_choice} récupéré pour {data.get('company_name', company_id)} ({len(prompt)} chars)")
            
            return prompt
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Erreur récupération prompt pour {company_id}: {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            logger.error(f"Traceback complet:\n{traceback.format_exc()}")
            raise

    async def get_hyde_pre_routing_prompt(self, company_id: str) -> str:
        """Récupère le bloc de prompt HYDE pré-routage depuis prompt_botlive_groq_70b.

        Le bloc est délimité par [[HYDE_PRE_ROUTING_START]] et [[HYDE_PRE_ROUTING_END]]
        dans le prompt principal stocké en base.
        """

        return await self.get_prompt_block(
            company_id=company_id,
            start_tag="[[HYDE_PRE_ROUTING_START]]",
            end_tag="[[HYDE_PRE_ROUTING_END]]",
            cache_suffix="hyde_pre_routing",
            required=False,
        )

    async def get_prompt_block(
        self,
        company_id: str,
        start_tag: str,
        end_tag: str,
        cache_suffix: str,
        source_column: str = "prompt_botlive_groq_70b",
        required: bool = True,
    ) -> str:
        """Récupère un bloc de prompt délimité par des balises START/END dans le prompt principal.

        Tous les prompts (HYDE_PRE, HYDE_SECOUR_X, JESSICA_PROMPT_X, etc.) peuvent être stockés
        dans un unique champ Supabase, et distingués uniquement par leurs balises.
        """

        company_id = _normalize_company_id(company_id)
        cache_key = f"{company_id}_{cache_suffix}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info(f"📦 [CACHE] Prompt block hit pour {cache_key}")
            return cached

        try:
            logger.info(
                f"🔍 [SUPABASE] Requête prompt block: company_id={company_id}, column={source_column}, block={cache_suffix}"
            )
            response = await asyncio.to_thread(
                self.supabase.table("company_rag_configs")
                .select(f"{source_column}, company_name")
                .eq("company_id", company_id)
                .single()
                .execute
            )

            if not response.data:
                raise ValueError(f"❌ Aucune config trouvée pour company_id: {company_id}")

            full_prompt = response.data.get(source_column) or ""
            try:
                block = self._extract_block(full_prompt, start_tag=start_tag, end_tag=end_tag)
            except Exception as e:
                if not required:
                    logger.warning(
                        f"⚠️ Prompt block optionnel manquant: {cache_suffix} pour {company_id} ({e})"
                    )
                    block = ""
                else:
                    raise

            self._cache_set(cache_key, block)
            logger.info(
                f"✅ Prompt block chargé pour {response.data.get('company_name', company_id)} "
                f"(block={cache_suffix}, {len(block)} chars)"
            )
            return block
        except Exception as e:
            if not required:
                logger.warning(
                    f"⚠️ Prompt block optionnel indisponible: {cache_suffix} pour {company_id} ({e})"
                )
                try:
                    self._cache_set(cache_key, "")
                except Exception:
                    pass
                return ""

            import traceback

            logger.error(
                f"❌ Erreur récupération prompt block {cache_suffix} pour {company_id}: {e}"
            )
            logger.error(f"Traceback complet:\n{traceback.format_exc()}")
            raise

    @staticmethod
    def _extract_block(full_prompt: str, start_tag: str, end_tag: str) -> str:
        start_idx = full_prompt.find(start_tag)
        end_idx = full_prompt.find(end_tag)

        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            raise ValueError(
                f"❌ Bloc introuvable: start_tag={start_tag} end_tag={end_tag}"
            )

        block = full_prompt[start_idx + len(start_tag) : end_idx].strip()
        if not block:
            raise ValueError(f"❌ Bloc vide: start_tag={start_tag} end_tag={end_tag}")

        return block

    async def get_hyde_secour_x_prompt(self, company_id: str) -> str:
        """Prompt clarification (Gemini) via bloc [[HYDE_SECOUR_X_START]]/[[HYDE_SECOUR_X_END]]."""

        return await self.get_prompt_block(
            company_id=company_id,
            start_tag="[[HYDE_SECOUR_X_START]]",
            end_tag="[[HYDE_SECOUR_X_END]]",
            cache_suffix="hyde_secour_x",
        )

    async def get_jessica_prompt_x(self, company_id: str) -> str:
        """Prompt Jessica complexe (70B) via bloc [[JESSICA_PROMPT_X_START]]/[[JESSICA_PROMPT_X_END]]."""

        return await self.get_prompt_block(
            company_id=company_id,
            start_tag="[[JESSICA_PROMPT_X_START]]",
            end_tag="[[JESSICA_PROMPT_X_END]]",
            cache_suffix="jessica_prompt_x",
        )

    async def format_prompt(self, 
                     company_id: str,
                     llm_choice: str,
                     conversation_history: str = "",
                     question: str = "",
                     detected_objects: str = "[AUCUN OBJET DÉTECTÉ]",
                     filtered_transactions: str = "[AUCUNE TRANSACTION VALIDE]",
                     expected_deposit: str = "2000",
                     order_state: str = "") -> str:
        """
        Récupère et formate le prompt avec les variables dynamiques
        
        Args:
            company_id: Identifiant entreprise
            llm_choice: "groq-70b" ou "deepseek-v3"
            conversation_history: Historique conversation
            question: Question utilisateur
            detected_objects: Objets détectés (vision)
            filtered_transactions: Transactions filtrées
            expected_deposit: Montant acompte attendu
            order_state: État de la commande (mémoire)
        
        Returns:
            str: Prompt complet formaté
        """
        # Récupérer le template depuis Supabase
        logger.info(f"🔍 [PROMPTS_MANAGER] Récupération prompt: company_id={company_id}, llm={llm_choice}")
        prompt_template = await self.get_prompt(company_id, llm_choice)
        logger.info(f"✅ [PROMPTS_MANAGER] Template récupéré: {len(prompt_template)} chars")
        
        # Variables par défaut
        format_vars = {
            'conversation_history': conversation_history,
            'question': question,
            'detected_objects': detected_objects,
            'filtered_transactions': filtered_transactions,
            'expected_deposit': expected_deposit
        }

        # --- ENRICHISSEMENT DYNAMIQUE (V2.0 SCALABLE) ---
        try:
            info = await self.get_company_info(company_id) or {}
            # 🛡️ GARDE-FOU : rag_behavior peut être une string legacy → forcer dict
            _raw_rag = info.get("rag_behavior") if isinstance(info, dict) else None
            rag = _raw_rag if isinstance(_raw_rag, dict) else {}

            # Mapping des variables de base
            format_vars['company_name'] = info.get("company_name") or "Notre Boutique"
            format_vars['ai_name'] = info.get("ai_name") or "Jessica"

            # Mapping récursif du rag_behavior (guardé dict)
            payment = rag.get("payment") if isinstance(rag.get("payment"), dict) else {}
            support = rag.get("support") if isinstance(rag.get("support"), dict) else {}
            expedition = rag.get("expedition") if isinstance(rag.get("expedition"), dict) else {}
            
            format_vars['wave_number'] = payment.get("wave_number") or info.get("whatsapp_phone") or "à demander"
            format_vars['depot_amount'] = payment.get("deposit_amount") or expected_deposit or "2000 FCFA"
            format_vars['expedition_base_fee'] = expedition.get("base_fee") or "3000-5000 FCFA"
            format_vars['whatsapp_number'] = support.get("whatsapp") or info.get("whatsapp_phone") or ""
            format_vars['sav_number'] = support.get("sav_number") or support.get("phone") or ""
            format_vars['support_hours'] = rag.get("support_hours") or "08:00 - 20:00"
            format_vars['return_policy'] = rag.get("return_policy") or "Échange possible sous 48h (voir conditions)"
            format_vars['delai_message'] = rag.get("delai_message") or "" # Souvent vide, géré par fallback dans le prompt

            # 🏪 Section BOUTIQUE dynamique (online / physical / hybrid)
            try:
                from core.boutique_block import build_boutique_block
                format_vars['boutique_block'] = build_boutique_block(info)
            except Exception as blk_err:
                logger.warning(f"⚠️ Fallback boutique_block pour {company_id}: {blk_err}")
                format_vars['boutique_block'] = (
                    "Type : Exclusivement en ligne.\n"
                    "Accès : Aucune visite en magasin n'est possible.\n"
                    "Service : Nous fonctionnons uniquement par Livraison (Abidjan) "
                    "ou Expédition (Intérieur) en cas de commande."
                )
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de l'enrichissement dynamique pour {company_id}: {e}")
        
        # Ajouter l'état de la commande si fourni (MÉMOIRE CONTEXTE)
        if order_state:
            # Injecter l'état AVANT le message client
            prompt_template = prompt_template.replace(
                "HISTORIQUE: {conversation_history}",
                f"HISTORIQUE: {{conversation_history}}\n\n{order_state}"
            )
        
        # Formatage sécurisé
        try:
            formatted_prompt = prompt_template.format(**format_vars)
            logger.info(f"✅ [PROMPTS_MANAGER] Prompt formaté: {len(formatted_prompt)} chars")
            return formatted_prompt
        except KeyError as e:
            logger.error(f"⚠️ Variable manquante dans prompt {llm_choice}: {e}")
            # Remplacer les variables manquantes par des valeurs par défaut
            safe_prompt = prompt_template
            for key, value in format_vars.items():
                safe_prompt = safe_prompt.replace(f"{{{key}}}", str(value))
            logger.warning(f"⚠️ [PROMPTS_MANAGER] Fallback formatage: {len(safe_prompt)} chars")
            return safe_prompt
    
    async def get_company_info(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère les informations de l'entreprise + sa souscription en PARALLÈLE (V3 Performance).
        Gère le mapping hybride Firebase ID (Text) -> Supabase ID (UUID).
        """
        try:
            # 🎯 0) RÉSOLUTION ID (HYBRID)
            # Détecter si c'est déjà un UUID
            company_id = _normalize_company_id(company_id)
            is_uuid = bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', str(company_id).lower()))
            
            firebase_id = company_id
            internal_uuid = company_id if is_uuid else None

            # Si on a un ID Firebase, on récupère le vrai UUID depuis la table 'companies'
            if not internal_uuid:
                try:
                    res_comp = await asyncio.to_thread(
                        self.supabase.table("companies")
                        .select("id")
                        .eq("company_id_text", firebase_id)
                        .execute
                    )
                    if res_comp.data:
                        internal_uuid = res_comp.data[0]['id']
                        zlog("info", "ID_RESOLVE", "Firebase -> UUID mapping trouvé",
                             firebase_id=firebase_id, uuid=internal_uuid)
                except Exception as res_err:
                    logger.warning(f"⚠️ [GET_COMPANY] Résolution UUID échouée pour {firebase_id}: {res_err}")

            # 🎯 1) RÉCUPÉRATION PARALLÈLE (L'accélérateur V3)
            # On lance les deux requêtes simultanément via asyncio.gather
            tasks = [
                asyncio.to_thread(
                    self.supabase.table("company_rag_configs")
                    .select("company_name, ai_name, secteur_activite, whatsapp_phone, boutique_type, rag_behavior, description, botlive_prompts_version, shop_slug")
                    .eq("company_id", firebase_id)
                    .execute
                )
            ]
            
            # On n'ajoute la tâche subscription que si on a un UUID valide (pour éviter 22P02)
            if internal_uuid:
                tasks.append(
                    asyncio.to_thread(
                        self.supabase.table("subscriptions")
                        .select("plan_name, has_boost, status, next_billing_date, pro_trial_ends_at, current_usage, usage_limit, created_at, updated_at")
                        .eq("company_id", internal_uuid)
                        .order("updated_at", desc=True)
                        .limit(1)
                        .execute
                    )
                )
            
            # Exécution parallèle
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyse des résultats
            config_res = results[0]
            sub_res = results[1] if len(results) > 1 else None

            if isinstance(config_res, Exception) or not config_res.data:
                logger.warning(f"⚠️ [GET_COMPANY] Aucune config trouvée pour {firebase_id}")
                return None
            
            data = config_res.data[0]

            # Traitement Subscription
            subscription: Dict[str, Any] = {}
            plan_name = None
            has_boost = False
            
            if sub_res and not isinstance(sub_res, Exception) and sub_res.data:
                subscription = sub_res.data[0] or {}
                plan_name = str(subscription.get("plan_name") or "").strip().lower() or None
                has_boost = bool(subscription.get("has_boost") or False)
                zlog("info", "SUBSCRIPTIONS", "plan résolu (parallel)",
                     company_id=firebase_id, plan_name=plan_name, has_boost=has_boost)
            else:
                zlog("info", "SUBSCRIPTIONS", "pas de subscription ou erreur — fallback starter",
                     company_id=firebase_id)

            return {
                "company_name": data.get("company_name"),
                "ai_name": data.get("ai_name"),
                "secteur_activite": data.get("secteur_activite"),
                "whatsapp_phone": data.get("whatsapp_phone"),
                "boutique_type": data.get("boutique_type"),
                "rag_behavior": data.get("rag_behavior"),
                "description": data.get("description"),
                "shop_slug": data.get("shop_slug"),
                "plan_name": plan_name,
                "has_boost": has_boost,
                "subscription": subscription,
                "uuid_resolved": internal_uuid
            }

        except Exception as e:
            zlog_error("SUBSCRIPTIONS", "erreur critique récupération info entreprise", e,
                       company_id=company_id)
            logger.error(f"❌ Erreur critique info entreprise {company_id}: {e}")
            return {}

        except Exception as e:
            zlog_error("SUBSCRIPTIONS", "erreur récupération info entreprise", e,
                       company_id=company_id)
            logger.error(f"❌ Erreur récupération info entreprise {company_id}: {e}")
            return {}
    
    # ══════════════════════════════════════════════
    # V2.0 — PROMPT UNIVERSEL (PREFIX CACHING)
    # ══════════════════════════════════════════════

    def _load_zeta_core(self) -> Dict[str, str]:
        """Charge et met en cache BLOC 1 (statique), PHASE_A/B/C et BLOC 2 template depuis prompt_universel_v2.md.

        Système C — Lazy Loading Phase-Driven :
        - BLOC 1 (CORE) : immuable, cache HIT permanent
        - PHASE_A/B/C : modules variables selon état de la commande
        - BLOC 2 : données dynamiques (wave_number, shop_name...)
        """
        global _ZETA_CORE_CACHE
        if _ZETA_CORE_CACHE:
            return _ZETA_CORE_CACHE
        try:
            with open(_PROMPT_UNIVERSEL_V2_PATH, "r", encoding="utf-8") as f:
                raw = f.read()
            m1 = re.search(r"\[\[ZETA_CORE_START\]\](.*?)\[\[ZETA_CORE_END\]\]", raw, re.DOTALL)
            bloc1 = m1.group(1).strip() if m1 else raw

            # Extraction des phases A/B/C (Système C)
            def _extract_marker(tag_prefix: str) -> str:
                pattern = rf"\[\[{tag_prefix}_START\]\](.*?)\[\[{tag_prefix}_END\]\]"
                match = re.search(pattern, raw, re.DOTALL)
                return match.group(1).strip() if match else ""

            phase_a = _extract_marker("PHASE_A")
            phase_b = _extract_marker("PHASE_B")
            phase_c = _extract_marker("PHASE_C")

            # Extraction des identités
            identity_jessica = _extract_marker("IDENTITY_JESSICA")
            identity_amanda = _extract_marker("IDENTITY_AMANDA")

            # BLOC 2 : priorité au marker [[BLOC2_START]]...[[BLOC2_END]]
            # Fallback : tout ce qui est après le dernier [[PHASE_C_END]] ou [[ZETA_CORE_END]]
            m_bloc2 = re.search(r"\[\[BLOC2_START\]\](.*?)\[\[BLOC2_END\]\]", raw, re.DOTALL)
            if m_bloc2:
                bloc2 = m_bloc2.group(1).strip()
            else:
                m_fallback = re.search(r"\[\[PHASE_C_END\]\](.*?)$", raw, re.DOTALL)
                if not m_fallback:
                    m_fallback = re.search(r"\[\[ZETA_CORE_END\]\](.*?)$", raw, re.DOTALL)
                bloc2 = m_fallback.group(1).strip() if m_fallback else ""

            _ZETA_CORE_CACHE = {
                "bloc1": bloc1,
                "phase_a": phase_a,
                "phase_b": phase_b,
                "phase_c": phase_c,
                "identity_jessica": identity_jessica,
                "identity_amanda": identity_amanda,
                "bloc2_template": bloc2,
            }
            logger.info(
                f"✅ [V2] Zeta Core chargé: BLOC1={len(bloc1)} chars, "
                f"ID_JESSICA={len(identity_jessica)}, ID_AMANDA={len(identity_amanda)}, "
                f"PHASE_A={len(phase_a)}, PHASE_B={len(phase_b)}, PHASE_C={len(phase_c)}, "
                f"BLOC2={len(bloc2)} chars"
            )
        except Exception as e:
            logger.error(f"❌ [V2] Erreur chargement prompt_universel_v2.md: {e}")
            _ZETA_CORE_CACHE = {
                "bloc1": "",
                "phase_a": "",
                "phase_b": "",
                "phase_c": "",
                "bloc2_template": "",
            }
        return _ZETA_CORE_CACHE

    async def get_v2_base_prompt(
        self,
        company_id: str,
        company_info: Optional[Dict[str, Any]] = None,
        phase: Optional[str] = None,
        identity: Optional[str] = None,
    ) -> str:
        """
        Construit le prompt V2.1 unifié pour OpenRouter (prefix caching).
        BLOC 1 identique pour toutes les boutiques → cache hit maximal.
        
        Nouveauté V2.1 (FISSION):
        - `identity`: "jessica" ou "amanda". Injecte le bloc d'identité correspondant.
        - Si identity="amanda", on vide les blocs CATALOGUE et PRODUCT_INDEX pour économiser 
          énormément de tokens et forcer le focus sur la prise de photo/infos.
          
        Structure retournée (Système C) :
          BLOC1 + IDENTITY + PHASE_MODULE + '# 📊 DONNÉES DYNAMIQUES' + BLOC2_rempli
        """
        core = self._load_zeta_core()
        bloc1 = core.get("bloc1", "")
        bloc2_template = core.get("bloc2_template", "")
        if not bloc1:
            return ""

        company_id = _normalize_company_id(company_id)
        info = company_info if isinstance(company_info, dict) and company_info else {}
        if not info and company_id:
            try:
                info = await self.get_company_info(company_id)
            except Exception:
                info = {}

        rag = (info.get("rag_behavior") or {}) if isinstance(info, dict) else {}
        payment = (rag.get("payment") or {}) if isinstance(rag, dict) else {}
        support = (rag.get("support") or {}) if isinstance(rag, dict) else {}
        expedition = (rag.get("expedition") or {}) if isinstance(rag, dict) else {}

        # 🏪 Section BOUTIQUE dynamique (online / physical / hybrid)
        try:
            from core.boutique_block import build_boutique_block
            _boutique_block = build_boutique_block(info)
        except Exception as blk_err:
            logger.warning(f"⚠️ [V2] Fallback boutique_block: {blk_err}")
            _boutique_block = (
                "Type : Exclusivement en ligne.\n"
                "Accès : Aucune visite en magasin n'est possible.\n"
                "Service : Nous fonctionnons uniquement par Livraison (Abidjan) "
                "ou Expédition (Intérieur) en cas de commande."
            )

        _shop_slug = str(info.get("shop_slug") or "").strip()
        from core.cart_manager import CartManager
        _catalogue_url = CartManager.get_catalogue_url(_shop_slug) if _shop_slug else ""
        _shop_url = f"https://{_shop_slug}.zeta-ai.io" if _shop_slug else ""

        bloc2_vars = {
            "ai_name": info.get("ai_name") or "Jessica",
            "company_name": info.get("company_name") or "Notre Boutique",
            "catalogue_url": _catalogue_url,
            "shop_url": _shop_url,
            "wave_number": payment.get("wave_number") or info.get("whatsapp_phone") or "\u00e0 demander",
            "depot_amount": payment.get("deposit_amount") or "2000 FCFA",
            "delai_message": rag.get("delai_message") or "",
            "expedition_base_fee": expedition.get("base_fee") or "3000-5000 FCFA",
            "sav_number": support.get("sav_number") or support.get("phone") or "",
            "whatsapp_number": support.get("whatsapp") or info.get("whatsapp_phone") or "",
            "support_hours": rag.get("support_hours") or "08:00 - 20:00",
            "return_policy": rag.get("return_policy") or "\u00c9change possible sous 48h",
            "boutique_block": _boutique_block,
        }

        bloc2_filled = bloc2_template
        for k, v in bloc2_vars.items():
            bloc2_filled = bloc2_filled.replace(f"{{{k}}}", str(v or ""))

        # Remplacer aussi les variables dans le BLOC 1 (CORE) pour assurer l'identité
        for k, v in bloc2_vars.items():
            bloc1 = bloc1.replace(f"{{{k}}}", str(v or ""))

        # Injection de l'IDENTITÉ (V2.1 Fission)
        identity_module = ""
        if identity == "jessica":
            identity_module = core.get("identity_jessica", "")
        elif identity == "amanda":
            identity_module = core.get("identity_amanda", "")
        
        if identity_module:
            for k, v in bloc2_vars.items():
                identity_module = identity_module.replace(f"{{{k}}}", str(v or ""))

        # Système C — Injection du PHASE_MODULE entre BLOC 1 et BLOC 2
        phase_module = ""
        phase_normalized = (phase or "").strip().upper() if phase else ""
        if phase_normalized in {"A", "B", "C"}:
            phase_key = f"phase_{phase_normalized.lower()}"
            phase_module = core.get(phase_key, "") or ""
            # Remplacer aussi les variables dans le phase module (ex: {wave_number})
            if phase_module:
                for k, v in bloc2_vars.items():
                    phase_module = phase_module.replace(f"{{{k}}}", str(v or ""))

        # --- OPTIMISATION AMANDA: Suppression du catalogue si Amanda ---
        if identity == "amanda":
            # On vide le bloc2_filled des marqueurs catalogue pour alléger radicalement le prompt
            bloc2_filled = bloc2_filled.replace("[[PRODUCT_INDEX_START]]", "[BLOC PRODUCT_INDEX DÉSACTIVÉ POUR AMANDA]")
            bloc2_filled = re.sub(r"\[\[PRODUCT_INDEX_START\]\].*?\[\[PRODUCT_INDEX_END\]\]", "[INDEX PRODUIT DÉSACTIVÉ]", bloc2_filled, flags=re.DOTALL)
            bloc2_filled = bloc2_filled.replace("[CATALOGUE_START]", "[BLOC CATALOGUE DÉSACTIVÉ POUR AMANDA]")
            bloc2_filled = re.sub(r"\[CATALOGUE_START\].*?\[CATALOGUE_END\]", "[CATALOGUE DÉSACTIVÉ]", bloc2_filled, flags=re.DOTALL)

        header_dynamics = "# 📊 DONNÉES DYNAMIQUES\n\n"
        
        full_sections = [bloc1]
        if identity_module:
            full_sections.append(identity_module)
        if phase_module:
            full_sections.append(phase_module)
        
        full_sections.append(header_dynamics + bloc2_filled)
        
        full_prompt = "\n\n".join(full_sections)
        
        if identity or phase:
            logger.info(
                f"✅ [V2.1] Prompt construit pour company={company_id} "
                f"identity={identity} phase={phase_normalized}: {len(full_prompt)} chars"
            )
        else:
            logger.info(f"✅ [V2.1] Prompt construit pour company={company_id} (standard): {len(full_prompt)} chars")
        return full_prompt

    def clear_cache(self, company_id: Optional[str] = None):
        """
        Vide le cache des prompts
        
        Args:
            company_id: Si fourni, vide uniquement le cache de cette entreprise
        """
        if company_id:
            # Vider cache spécifique
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(company_id)]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"🗑️ Cache vidé pour {company_id}")
        else:
            # Vider tout le cache
            self._cache.clear()
            logger.info("🗑️ Cache complet vidé")

    def invalidate_cache(self, company_id: Optional[str] = None):
        """Alias pour compatibilité webhook"""
        return self.clear_cache(company_id)
    
    async def get_prompt_metadata(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère les métadonnées des prompts (version, date MAJ, etc.)
        
        Args:
            company_id: Identifiant entreprise
        
        Returns:
            Dict: Métadonnées
        """
        try:
            response = await asyncio.to_thread(
                self.supabase.table("company_rag_configs") \
                .select("botlive_prompts_version, botlive_prompts_updated_at") \
                .eq("company_id", company_id) \
                .single() \
                .execute
            )
            
            return response.data if response.data else {}
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération métadonnées {company_id}: {e}")
            return {}


# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 INSTANCE GLOBALE (SINGLETON)
# ═══════════════════════════════════════════════════════════════════════════════

# Instance globale réutilisable
_prompts_manager = None

# Sentinel: si l'initialisation Supabase a échoué, on ne réessaie pas en boucle.
_prompts_manager_init_failed = False

def get_prompts_manager() -> BotlivePromptsManager:
    """
    Retourne l'instance globale du gestionnaire de prompts
    """
    global _prompts_manager
    global _prompts_manager_init_failed

    if _prompts_manager_init_failed:
        return None

    if _prompts_manager is None:
        try:
            _prompts_manager = BotlivePromptsManager()
            logger.info("✅ BotlivePromptsManager initialisé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation BotlivePromptsManager: {e}")
            logger.error(f"⚠️ FALLBACK: Utilisation prompts hardcodés")
            # Retourner None pour forcer l'utilisation des prompts hardcodés
            _prompts_manager_init_failed = True
            return None
    return _prompts_manager

# Export pour compatibilité routes
prompts_manager = get_prompts_manager()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 FONCTIONS UTILITAIRES (COMPATIBILITÉ AVEC ANCIEN SYSTÈME)
# ═══════════════════════════════════════════════════════════════════════════════

def format_prompt(company_id: str, llm_choice: str, **kwargs) -> str:
    """
    Fonction wrapper pour compatibilité avec l'ancien système
    
    Args:
        company_id: Identifiant entreprise
        llm_choice: "groq-70b" ou "deepseek-v3"
        **kwargs: Variables à injecter dans le prompt
    
    Returns:
        str: Prompt formaté
    """
    manager = get_prompts_manager()
    return manager.format_prompt(company_id, llm_choice, **kwargs)


async def get_prompt_info(company_id: str, llm_choice: str) -> dict:
    """
    Retourne les métadonnées du prompt (compatibilité)
    """
    manager = get_prompts_manager()
    metadata = await manager.get_prompt_metadata(company_id)
    
    # Estimer tokens
    prompt = await manager.get_prompt(company_id, llm_choice)
    tokens_approx = len(prompt) // 4
    
    return {
        "name": f"{llm_choice} - {manager.get_company_info(company_id).get('company_name', 'Unknown')}",
        "tokens_approx": tokens_approx,
        "version": metadata.get("botlive_prompts_version", "unknown"),
        "updated_at": metadata.get("botlive_prompts_updated_at")
    }


if __name__ == "__main__":
    # Test du système
    import sys
    
    print("🧪 TEST BOTLIVE PROMPTS SUPABASE\n")
    print("=" * 80)
    
    try:
        # Initialiser
        manager = BotlivePromptsManager()
        
        # Test company_id
        test_company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        
        # Test récupération info
        print(f"\n📊 Informations entreprise:")
        info = manager.get_company_info(test_company_id)
        print(f"   - Nom: {info.get('company_name')}")
        print(f"   - IA: {info.get('ai_name')}")
        print(f"   - Secteur: {info.get('secteur_activite')}")
        
        # Test récupération prompts
        print(f"\n📝 Test récupération prompts:")
        
        groq_prompt = manager.get_prompt(test_company_id, "groq-70b")
        print(f"   ✅ Groq 70B: {len(groq_prompt)} caractères (~{len(groq_prompt)//4} tokens)")
        
        deepseek_prompt = manager.get_prompt(test_company_id, "deepseek-v3")
        print(f"   ✅ DeepSeek V3: {len(deepseek_prompt)} caractères (~{len(deepseek_prompt)//4} tokens)")
        
        # Test formatage
        print(f"\n🔧 Test formatage avec variables:")
        formatted = manager.format_prompt(
            test_company_id,
            "groq-70b",
            conversation_history="Client: Bonjour",
            question="Je veux commander",
            detected_objects="[produit détecté]",
            filtered_transactions="[2000 FCFA]",
            expected_deposit="2000"
        )
        print(f"   ✅ Prompt formaté: {len(formatted)} caractères")
        
        # Test cache
        print(f"\n📦 Test cache:")
        groq_prompt_2 = manager.get_prompt(test_company_id, "groq-70b")
        print(f"   ✅ Cache hit: {groq_prompt == groq_prompt_2}")
        
        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS RÉUSSIS!")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        sys.exit(1)
