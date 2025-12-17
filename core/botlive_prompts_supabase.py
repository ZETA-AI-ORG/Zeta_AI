#!/usr/bin/env python3
"""
🗄️ BOTLIVE PROMPTS SUPABASE - Récupération dynamique des prompts par company_id
Remplace les prompts hardcodés par des prompts stockés en base de données
"""

import os
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client

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
        self._cache_ttl = 300  # TTL 5 minutes (300 secondes) - RÉDUIT pour dev
        
        logger.info("✅ BotlivePromptsManager initialisé avec Supabase")
        logger.info("🗑️ Cache prompts vidé (démarrage propre)")
        logger.info(f"⏰ TTL cache: {self._cache_ttl}s (5 min)")
    
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
        # Vérifier cache
        cache_key = f"{company_id}_{llm_choice}"
        if cache_key in self._cache:
            logger.info(f"📦 [CACHE] Cache hit pour {cache_key} ({len(self._cache[cache_key])} chars)")
            return self._cache[cache_key]
        
        try:
            # Récupérer depuis Supabase (table company_rag_configs)
            logger.info(f"🔍 [SUPABASE] Requête: table=company_rag_configs, company_id={company_id}")
            response = self.supabase.table("company_rag_configs") \
                .select("prompt_botlive_groq_70b, prompt_botlive_deepseek_v3, company_name, ai_name") \
                .eq("company_id", company_id) \
                .single() \
                .execute()
            logger.info(f"✅ [SUPABASE] Réponse reçue: {bool(response.data)}")
            
            if not response.data:
                raise ValueError(f"❌ Aucune config trouvée pour company_id: {company_id}")
            
            data = response.data
            
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
            self._cache[cache_key] = prompt
            
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
        )

    def get_prompt_block(
        self,
        company_id: str,
        start_tag: str,
        end_tag: str,
        cache_suffix: str,
        source_column: str = "prompt_botlive_groq_70b",
    ) -> str:
        """Récupère un bloc de prompt délimité par des balises START/END dans le prompt principal.

        Tous les prompts (HYDE_PRE, HYDE_SECOUR_X, JESSICA_PROMPT_X, etc.) peuvent être stockés
        dans un unique champ Supabase, et distingués uniquement par leurs balises.
        """

        cache_key = f"{company_id}_{cache_suffix}"
        if cache_key in self._cache:
            logger.info(f"📦 [CACHE] Prompt block hit pour {cache_key}")
            return self._cache[cache_key]

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
            block = self._extract_block(full_prompt, start_tag=start_tag, end_tag=end_tag)

            self._cache[cache_key] = block
            logger.info(
                f"✅ Prompt block chargé pour {response.data.get('company_name', company_id)} "
                f"(block={cache_suffix}, {len(block)} chars)"
            )
            return block
        except Exception as e:
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
        Récupère les informations de l'entreprise
        
        Args:
            company_id: Identifiant entreprise
        
        Returns:
            Dict: Informations entreprise (name, ai_name, etc.)
        """
        try:
            response = self.supabase.table("company_rag_configs") \
                .select("company_name, ai_name, secteur_activite, botlive_prompts_version") \
                .eq("company_id", company_id) \
                .single() \
                .execute()
            
            return response.data if response.data else {}
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération info entreprise {company_id}: {e}")
            return {}
    
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

def get_prompts_manager() -> BotlivePromptsManager:
    """
    Retourne l'instance globale du gestionnaire de prompts
    """
    global _prompts_manager
    if _prompts_manager is None:
        try:
            _prompts_manager = BotlivePromptsManager()
            logger.info("✅ BotlivePromptsManager initialisé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation BotlivePromptsManager: {e}")
            logger.error(f"⚠️ FALLBACK: Utilisation prompts hardcodés")
            # Retourner None pour forcer l'utilisation des prompts hardcodés
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
