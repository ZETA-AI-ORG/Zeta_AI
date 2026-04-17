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
import time

# Chemin vers le prompt universel V2.0 (BLOC 1 statique)
_PROMPT_UNIVERSEL_V2_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompt_universel_v2.md")
# Cache global BLOC 1 / BLOC 2 template (partagé entre toutes les instances)
_ZETA_CORE_CACHE: Dict[str, str] = {}

logger = logging.getLogger(__name__)

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
        self._cache = {}  # Cache en mémoire pour performance
        self._cache_timestamps = {}  # Timestamps pour TTL

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
    
    def get_prompt(self, company_id: str, llm_choice: str) -> str:
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
            response = self.supabase.table("company_rag_configs") \
                .select("prompt_botlive_groq_70b, prompt_botlive_deepseek_v3, company_name, ai_name, botlive_prompts_updated_at") \
                .eq("company_id", company_id) \
                .single() \
                .execute()
            logger.info(f"✅ [SUPABASE] Réponse reçue: {bool(response.data)}")
            
            if not response.data:
                raise ValueError(f"❌ Aucune config trouvée pour company_id: {company_id}")
            
            data = response.data

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

    def get_hyde_pre_routing_prompt(self, company_id: str) -> str:
        """Récupère le bloc de prompt HYDE pré-routage depuis prompt_botlive_groq_70b.

        Le bloc est délimité par [[HYDE_PRE_ROUTING_START]] et [[HYDE_PRE_ROUTING_END]]
        dans le prompt principal stocké en base.
        """

        return self.get_prompt_block(
            company_id=company_id,
            start_tag="[[HYDE_PRE_ROUTING_START]]",
            end_tag="[[HYDE_PRE_ROUTING_END]]",
            cache_suffix="hyde_pre_routing",
            required=False,
        )

    def get_prompt_block(
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

        cache_key = f"{company_id}_{cache_suffix}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info(f"📦 [CACHE] Prompt block hit pour {cache_key}")
            return cached

        try:
            logger.info(
                f"🔍 [SUPABASE] Requête prompt block: company_id={company_id}, column={source_column}, block={cache_suffix}"
            )
            response = (
                self.supabase.table("company_rag_configs")
                .select(f"{source_column}, company_name")
                .eq("company_id", company_id)
                .single()
                .execute()
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

    def get_hyde_secour_x_prompt(self, company_id: str) -> str:
        """Prompt clarification (Gemini) via bloc [[HYDE_SECOUR_X_START]]/[[HYDE_SECOUR_X_END]]."""

        return self.get_prompt_block(
            company_id=company_id,
            start_tag="[[HYDE_SECOUR_X_START]]",
            end_tag="[[HYDE_SECOUR_X_END]]",
            cache_suffix="hyde_secour_x",
        )

    def get_jessica_prompt_x(self, company_id: str) -> str:
        """Prompt Jessica complexe (70B) via bloc [[JESSICA_PROMPT_X_START]]/[[JESSICA_PROMPT_X_END]]."""

        return self.get_prompt_block(
            company_id=company_id,
            start_tag="[[JESSICA_PROMPT_X_START]]",
            end_tag="[[JESSICA_PROMPT_X_END]]",
            cache_suffix="jessica_prompt_x",
        )

    def format_prompt(self, 
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
        prompt_template = self.get_prompt(company_id, llm_choice)
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
            info = self.get_company_info(company_id)
            rag = info.get("rag_behavior", {}) or {}
            
            # Mapping des variables de base
            format_vars['shop_name'] = info.get("company_name") or "Notre Boutique"
            format_vars['bot_name'] = info.get("ai_name") or "Jessica"
            
            # Mapping récursif du rag_behavior
            # On aplatit les champs essentiels pour le prompt
            payment = rag.get("payment", {}) or {}
            support = rag.get("support", {}) or {}
            expedition = rag.get("expedition", {}) or {}
            
            format_vars['wave_number'] = payment.get("wave_number") or info.get("whatsapp_phone") or "à demander"
            format_vars['depot_amount'] = payment.get("deposit_amount") or expected_deposit or "2000 FCFA"
            format_vars['expedition_base_fee'] = expedition.get("base_fee") or "3000-5000 FCFA"
            format_vars['whatsapp_number'] = support.get("whatsapp") or info.get("whatsapp_phone") or ""
            format_vars['sav_number'] = support.get("sav_number") or support.get("phone") or ""
            format_vars['support_hours'] = rag.get("support_hours") or "08:00 - 20:00"
            format_vars['return_policy'] = rag.get("return_policy") or "Échange possible sous 48h (voir conditions)"
            format_vars['delai_message'] = rag.get("delai_message") or "" # Souvent vide, géré par fallback dans le prompt
            
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
    
    def get_company_info(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère les informations de l'entreprise (nom, IA, plan, etc.)
        Jointure avec subscriptions pour le routage élastique.
        
        Args:
            company_id: Identifiant entreprise
        
        Returns:
            Dict: Informations entreprise (name, ai_name, plan_name, has_boost, etc.)
        """
        try:
            # 1. Récupérer les infos de la boutique
            response = self.supabase.table("company_rag_configs") \
                .select("company_name, ai_name, secteur_activite, whatsapp_phone, boutique_type, rag_behavior, description, botlive_prompts_version, has_boost") \
                .eq("company_id", company_id) \
                .limit(1) \
                .execute()
            
            if not response.data or len(response.data) == 0:
                return {}
            
            data = response.data[0]
            
            # 2. Récupérer le plan d'abonnement séparément (pour éviter l'erreur de jointure)
            plan_name = "none"
            try:
                sub_res = self.supabase.table("subscriptions") \
                    .select("plan_name") \
                    .eq("company_id", company_id) \
                    .limit(1) \
                    .execute()
                if sub_res.data and len(sub_res.data) > 0:
                    plan_name = sub_res.data[0].get("plan_name", "none")
            except Exception as sub_e:
                logger.warning(f"⚠️ Impossible de récupérer le plan pour {company_id}: {sub_e}")
            
            return {
                "company_name": data.get("company_name"),
                "ai_name": data.get("ai_name"),
                "secteur_activite": data.get("secteur_activite"),
                "whatsapp_phone": data.get("whatsapp_phone"),
                "boutique_type": data.get("boutique_type"),
                "rag_behavior": data.get("rag_behavior"),
                "description": data.get("description"),
                "has_boost": data.get("has_boost", False),
                "plan_name": subscription.get("plan_name", "none") if isinstance(subscription, dict) else "none"
            }
            
        except Exception as e:
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
            def _extract_phase(letter: str) -> str:
                pattern = rf"\[\[PHASE_{letter}_START\]\](.*?)\[\[PHASE_{letter}_END\]\]"
                match = re.search(pattern, raw, re.DOTALL)
                return match.group(1).strip() if match else ""

            phase_a = _extract_phase("A")
            phase_b = _extract_phase("B")
            phase_c = _extract_phase("C")

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
                "bloc2_template": bloc2,
            }
            logger.info(
                f"✅ [V2] Zeta Core chargé: BLOC1={len(bloc1)} chars, "
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

    def get_v2_base_prompt(
        self,
        company_id: str,
        company_info: Optional[Dict[str, Any]] = None,
        phase: Optional[str] = None,
    ) -> str:
        """
        Construit le prompt V2.0 unifié pour OpenRouter (prefix caching).
        BLOC 1 identique pour toutes les boutiques → cache hit maximal.
        Si `phase` in {"A","B","C"} : injecte le PHASE_MODULE correspondant entre BLOC1 et BLOC2.
        BLOC 2 rempli avec les variables boutique (wave_number, shop_name, etc.).

        Structure retournée (Système C) :
          BLOC1 + PHASE_MODULE (si phase fournie) + '# 📊 DONNÉES DYNAMIQUES' + BLOC2_rempli
        """
        core = self._load_zeta_core()
        bloc1 = core.get("bloc1", "")
        bloc2_template = core.get("bloc2_template", "")
        if not bloc1:
            return ""

        info = company_info if isinstance(company_info, dict) and company_info else {}
        if not info and company_id:
            try:
                info = self.get_company_info(company_id)
            except Exception:
                info = {}

        rag = (info.get("rag_behavior") or {}) if isinstance(info, dict) else {}
        payment = (rag.get("payment") or {}) if isinstance(rag, dict) else {}
        support = (rag.get("support") or {}) if isinstance(rag, dict) else {}
        expedition = (rag.get("expedition") or {}) if isinstance(rag, dict) else {}

        bloc2_vars = {
            "bot_name": info.get("ai_name") or "Jessica",
            "shop_name": info.get("company_name") or "Notre Boutique",
            "wave_number": payment.get("wave_number") or info.get("whatsapp_phone") or "\u00e0 demander",
            "depot_amount": payment.get("deposit_amount") or "2000 FCFA",
            "delai_message": rag.get("delai_message") or "",
            "expedition_base_fee": expedition.get("base_fee") or "3000-5000 FCFA",
            "sav_number": support.get("sav_number") or support.get("phone") or "",
            "whatsapp_number": support.get("whatsapp") or info.get("whatsapp_phone") or "",
            "support_hours": rag.get("support_hours") or "08:00 - 20:00",
            "return_policy": rag.get("return_policy") or "\u00c9change possible sous 48h",
        }

        bloc2_filled = bloc2_template
        for k, v in bloc2_vars.items():
            bloc2_filled = bloc2_filled.replace(f"{{{k}}}", str(v or ""))

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

        if phase_module:
            full_prompt = (
                f"{bloc1}\n\n"
                f"{phase_module}\n\n"
                f"# \U0001f4ca DONN\u00c9ES DYNAMIQUES\n\n"
                f"{bloc2_filled}"
            )
            logger.info(
                f"\u2705 [V2] Prompt V2 construit pour company={company_id} "
                f"phase={phase_normalized}: {len(full_prompt)} chars "
                f"(phase_module={len(phase_module)} chars)"
            )
        else:
            full_prompt = f"{bloc1}\n\n# \U0001f4ca DONN\u00c9ES DYNAMIQUES\n\n{bloc2_filled}"
            logger.info(f"\u2705 [V2] Prompt V2 construit pour company={company_id} (no phase): {len(full_prompt)} chars")
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
    
    def get_prompt_metadata(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère les métadonnées des prompts (version, date MAJ, etc.)
        
        Args:
            company_id: Identifiant entreprise
        
        Returns:
            Dict: Métadonnées
        """
        try:
            response = self.supabase.table("company_rag_configs") \
                .select("botlive_prompts_version, botlive_prompts_updated_at") \
                .eq("company_id", company_id) \
                .single() \
                .execute()
            
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


def get_prompt_info(company_id: str, llm_choice: str) -> dict:
    """
    Retourne les métadonnées du prompt (compatibilité)
    
    Args:
        company_id: Identifiant entreprise
        llm_choice: "groq-70b" ou "deepseek-v3"
    
    Returns:
        dict: Métadonnées
    """
    manager = get_prompts_manager()
    metadata = manager.get_prompt_metadata(company_id)
    
    # Estimer tokens
    prompt = manager.get_prompt(company_id, llm_choice)
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
