# core/prompt_manager.py
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from utils import log3

class PromptManager:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def get_active_prompt(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le prompt actif pour une entreprise"""
        try:
            result = await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .select("*")
                .eq("company_id", company_id)
                .eq("is_active", True)
                .order("version", desc=True)
                .limit(1)
                .execute
            )
            
            if result.data:
                prompt_data = result.data[0]
                log3("[PROMPT] Active prompt", f"v{prompt_data['version']} for company {company_id}")
                return prompt_data
            else:
                # Fallback vers l'ancienne table si pas de prompt versionné
                legacy_result = await asyncio.to_thread(
                    self.supabase.table("company_rag_configs")
                    .select("system_prompt_template")
                    .eq("company_id", company_id)
                    .execute
                )
                
                if legacy_result.data:
                    # Migrer automatiquement vers le nouveau système
                    legacy_prompt = legacy_result.data[0]["system_prompt_template"]
                    return await self.create_prompt_version(
                        company_id, legacy_prompt, "system_migration", migrate_from_legacy=True
                    )
                
                log3("[PROMPT] No prompt found for company", str(company_id))
                return None
                
        except Exception as e:
            log3("[ERROR] Failed to get active prompt", str(e))
            return None
    
    async def create_prompt_version(
        self, 
        company_id: str, 
        prompt_template: str, 
        created_by: str,
        migrate_from_legacy: bool = False
    ) -> Dict[str, Any]:
        """Crée une nouvelle version de prompt"""
        try:
            # Désactiver l'ancien prompt actif
            if not migrate_from_legacy:
                await asyncio.to_thread(
                    self.supabase.table("company_prompt_history")
                    .update({"is_active": False})
                    .eq("company_id", company_id)
                    .eq("is_active", True)
                    .execute
                )
            
            # Obtenir le prochain numéro de version
            version_result = await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .select("version")
                .eq("company_id", company_id)
                .order("version", desc=True)
                .limit(1)
                .execute
            )
            
            next_version = 1
            if version_result.data:
                next_version = version_result.data[0]["version"] + 1
            
            # Créer la nouvelle version
            new_prompt = {
                "company_id": company_id,
                "prompt_template": prompt_template,
                "version": next_version,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": created_by,
                "is_active": True
            }
            
            result = await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .insert(new_prompt)
                .execute
            )
            
            log3("[PROMPT] Created", f"v{next_version} for company {company_id} by {created_by}")
            return result.data[0]
            
        except Exception as e:
            log3("[ERROR] Failed to create prompt version", str(e))
            raise
    
    async def rollback_to_version(self, company_id: str, target_version: int, created_by: str) -> bool:
        """Rollback vers une version spécifique"""
        try:
            # Vérifier que la version existe
            version_check = await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .select("*")
                .eq("company_id", company_id)
                .eq("version", target_version)
                .execute
            )
            
            if not version_check.data:
                log3("[PROMPT] Version not found for company", f"{target_version} / {company_id}")
                return False
            
            # Désactiver toutes les versions
            await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .update({"is_active": False})
                .eq("company_id", company_id)
                .execute
            )
            
            # Activer la version cible
            await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .update({"is_active": True})
                .eq("company_id", company_id)
                .eq("version", target_version)
                .execute
            )
            
            log3("[PROMPT] Rolled back", f"to v{target_version} for company {company_id} by {created_by}")
            return True
            
        except Exception as e:
            log3("[ERROR] Failed to rollback prompt", str(e))
            return False
    
    async def get_prompt_history(self, company_id: str) -> List[Dict[str, Any]]:
        """Récupère l'historique des prompts pour une entreprise"""
        try:
            result = await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .select("version, created_at, created_by, is_active")
                .eq("company_id", company_id)
                .order("version", desc=True)
                .execute
            )
            
            return result.data or []
            
        except Exception as e:
            log3("[ERROR] Failed to get prompt history", str(e))
            return []

    async def ab_test_prompt(self, company_id: str, user_id: str) -> Dict[str, Any]:
        """Sélectionne un prompt pour A/B testing basé sur user_id"""
        try:
            # Récupérer les 2 dernières versions actives (si A/B test en cours)
            result = await asyncio.to_thread(
                self.supabase.table("company_prompt_history")
                .select("*")
                .eq("company_id", company_id)
                .eq("is_active", True)
                .order("version", desc=True)
                .limit(2)
                .execute
            )
            
            if not result.data:
                return await self.get_active_prompt(company_id)
            
            # Si une seule version active, l'utiliser
            if len(result.data) == 1:
                return result.data[0]
            
            # A/B test basé sur le hash du user_id
            import hashlib
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            version_index = user_hash % 2  # 50/50 split
            
            selected_prompt = result.data[version_index]
            log3("[A/B] User", f"{user_id} -> prompt v{selected_prompt['version']}")
            
            return selected_prompt
            
        except Exception as e:
            log3("[ERROR] A/B test prompt selection failed", str(e))
            return await self.get_active_prompt(company_id)
