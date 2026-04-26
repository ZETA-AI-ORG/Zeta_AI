"""
🎯 SYSTÈME DE PROMPT SIMPLIFIÉ - ARCHITECTURE RADICALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Philosophie : Prompt statique enrichi avec SEULEMENT les infos dynamiques essentielles
- ✅ Prompt statique : Infos entreprise, règles, style
- ✅ Regex livraison : Détection zone + frais en temps réel
- ✅ Cache Gemini : Descriptions produits
- ✅ Meili : UNIQUEMENT coûts temps réel + stock
- ✅ Checklist commande : P[photo] S[specs] Z[zone] T[tel] $[pay]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from core.order_state_tracker import order_tracker
from core.company_catalog_v2_loader import get_company_catalog_v2, get_company_product_catalog_v2
from core.catalogue_block_builder import build_catalogue_block_from_catalog_v2
from database.supabase_client import get_supabase_client
from core.company_cache_manager import company_cache
from core.prompt_bots_loader import get_prompt_template
from core.botlive_prompts_supabase import get_prompts_manager


def _env_flag(name: str, default: bool = False) -> bool:
    try:
        raw = os.getenv(name)
        if raw is None:
            return bool(default)
        return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}
    except Exception:
        return bool(default)

@dataclass
class OrderChecklistState:
    """État de la checklist de commande"""
    model: bool = False     # Modèle/nom produit (prioritaire pour recherche catalogue)
    details: bool = False   # Détails produit (taille/type/variante)
    quantity: bool = False  # Quantité
    zone: bool = False
    telephone: bool = False
    payment: bool = False
    photo: bool = False  # Optionnelle
    
    def to_string(self) -> str:
        """Format: P[✓] S[✓] Z[✓] T[✓] $[✓]"""
        return (
            f"M[{'✓' if self.model else '○'}] "
            f"D[{'✓' if self.details else '○'}] "
            f"Q[{'✓' if self.quantity else '○'}] "
            f"Z[{'✓' if self.zone else '○'}] "
            f"T[{'✓' if self.telephone else '○'}] "
            f"$[{'✓' if self.payment else '○'}] "
            f"P[{'✓' if self.photo else '○'}]"
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "model": bool(self.model),
                "details": bool(self.details),
                "quantity": bool(self.quantity),
                "zone": bool(self.zone),
                "telephone": bool(self.telephone),
                "payment": bool(self.payment),
                "photo": bool(self.photo)
            }
        )

    def completion(self):
        fields = [self.model, self.details, self.quantity, self.zone, self.telephone, self.payment]
        done = sum(1 for f in fields if f)
        return done, len(fields)

    def get_next_step(self) -> str:
        """Détermine le prochain champ manquant à collecter."""
        fields = [
            ("model", self.model),
            ("details", self.details),
            ("quantity", self.quantity),
            ("zone", self.zone),
            ("telephone", self.telephone),
            ("payment", self.payment)
        ]
        for name, status in fields:
            if not status:
                return name
        return "completed"

class SimplifiedPromptSystem:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.prompt_cache = {} # Cache local mémoire (optionnel si Redis utilisé)

    async def get_static_prompt(self, company_id: str, *, phase: Optional[str] = None) -> str:
        """Récupère le prompt statique depuis Supabase ou cache local."""
        cache_key = f"{company_id}:{str(phase or '').strip().upper() or 'NONE'}"
        if cache_key in self.prompt_cache:
            return self.prompt_cache[cache_key]
        
        try:
            # 1. On récupère la config (status et mode)
            resp = self.supabase.table("company_rag_configs").select("bot_status, mode, system_prompt_template, prompt_botlive_deepseek_v3").eq("company_id", company_id).execute()
            
            if resp.data:
                config = resp.data[0]
                status = (config.get("bot_status") or "").lower()
                mode = (config.get("mode") or "").lower()
                
                # 2. Vérification de l'activation globale du bot
                if status != "active":
                    print(f"🛑 [PROMPT_SYSTEM] Bot désactivé pour {company_id} (status={status})")
                    # On retourne un prompt vide ou une instruction de désactivation
                    return "Désolé, l'assistant est actuellement désactivé pour cette boutique."
                
                # 3. Détermination du bot_type selon le mode
                # live -> amanda, rag -> jessica
                bot_type = "amanda" if mode == "live" else "jessica"
                
                print(f"📡 [PROMPT_SYSTEM] Routage : company={company_id} | mode={mode} -> bot={bot_type}")
                
                # 4. Chargement V2.1 phase-driven pour Jessica
                if bot_type == "jessica":
                    try:
                        manager = get_prompts_manager()
                        unified_prompt = await manager.get_v2_base_prompt(
                            company_id=company_id,
                            phase=str(phase or "").strip().upper() or None,
                            identity="jessica",
                        )
                        if unified_prompt:
                            print(f"✅ [PROMPT_SYSTEM] Source: V2.1 ({bot_type}, phase={str(phase or '').strip().upper() or 'NONE'}) pour {company_id}")
                            self.prompt_cache[cache_key] = unified_prompt
                            return unified_prompt
                    except Exception as e:
                        logger.warning("⚠️ [PROMPT_SYSTEM] fallback prompt_bots after V2.1 error: %s", e)

                # 5. Chargement du template unifié depuis prompt_bots
                unified_prompt = get_prompt_template(bot_type)
                if unified_prompt:
                    print(f"✅ [PROMPT_SYSTEM] Source: UNIFIÉ ({bot_type}) pour {company_id}")
                    self.prompt_cache[cache_key] = unified_prompt
                    return unified_prompt
                
                # 6. Fallback sur les colonnes legacy
                prompt = config.get("prompt_botlive_deepseek_v3") or config.get("system_prompt_template")
                if prompt:
                    print(f"⚠️ [PROMPT_SYSTEM] Source: LEGACY (colonne DB) pour {company_id}")
                    self.prompt_cache[cache_key] = prompt
                    return prompt
                    
        except Exception as e:
            print(f"⚠️ Erreur récupération prompt: {e}")
            # Fallback local ultime si Supabase est down
            return "Tu es un assistant de vente intelligent. Aide le client avec courtoisie."
            
        # Fallback local file if exists
        try:
            local_path = Path("prompt_universel_v2.md")
            if local_path.exists():
                return local_path.read_text(encoding="utf-8")
        except:
            pass
            
        return "Tu es Jessica, une assistante de vente chaleureuse."

    @staticmethod
    def _safe_format(template: str, **kwargs) -> str:
        """
        Remplacement SÉCURISÉ (Bloc 2).
        Utilise .replace() au lieu de .format() pour éviter de crasher sur les accolades JSON {}.
        """
        if not template:
            return ""
        
        final_text = str(template)
        # On ne remplace que les clés explicitement fournies
        for key, value in kwargs.items():
            val_str = str(value if value is not None else "")
            
            # Remplacement standard {key}
            placeholder = "{" + str(key) + "}"
            if placeholder in final_text:
                final_text = final_text.replace(placeholder, val_str)
        
        return final_text

    def _infer_mode(self, query: str, checklist: OrderChecklistState) -> str:
        """Détermine le mode (ACCUEIL, COLLECTE, CLÔTURE)"""
        done, total = checklist.completion()
        if done == 0: return "ACCUEIL"
        if done == total: return "CLÔTURE"
        return "COLLECTE"

    def _build_compact_context(self, **kwargs) -> str:
        """Construit un bloc de contexte minimaliste."""
        ctx = []
        for k, v in kwargs.items():
            if v: ctx.append(f"{k.upper()}: {v}")
        return "\n".join(ctx)

    def _compute_phase(self, state) -> str:
        try:
            missing = state.get_missing_fields() if state else []
        except Exception:
            missing = []
        missing_set = {str(f).upper().strip() for f in (missing or [])}
        if "PRODUIT" in missing_set or "SPECS" in missing_set:
            return "A"
        if "ZONE" in missing_set or "NUMÉRO" in missing_set or "NUMERO" in missing_set or "QUANTITÉ" in missing_set or "QUANTITE" in missing_set:
            return "B"
        return "C"

    def update_checklist_from_message(self, user_id: str, company_id: str, query: str, has_image: bool) -> OrderChecklistState:
        """Simule la mise à jour de la checklist (Logique réelle dans OrderStateTracker)"""
        # Ici on récupère l'état depuis le tracker réel
        state = order_tracker.get_state(user_id)
        
        checklist = OrderChecklistState()
        checklist.model = bool(str(state.produit or "").strip())
        checklist.details = bool(getattr(state, "selected_options", {}) or str(getattr(state, "produit_details_display", "") or state.produit_details or "").strip())
        checklist.quantity = bool(str(state.quantite or "").strip())
        checklist.zone = bool(str(state.zone or "").strip())
        checklist.telephone = bool(str(state.numero or "").strip())
        checklist.payment = state._is_paiement_valid()
        checklist.photo = has_image
        
        return checklist

    def _inject_between_markers(self, text: str, marker_start: str, marker_end: str, content: str) -> str:
        """Injecte du contenu entre deux balises."""
        pattern = f"{re.escape(marker_start)}.*?{re.escape(marker_end)}"
        replacement = f"{marker_start}\n{content}\n{marker_end}"
        if re.search(pattern, text, re.DOTALL):
            return re.sub(pattern, replacement, text, flags=re.DOTALL)
        return text + f"\n\n{replacement}"

    def _inject_between_product_index_markers(self, text: str, content: str) -> str:
        # On utilise les marqueurs attendus par le regex de debug du SimplifiedRAGEngine (ligne 3389)
        marker_start = "## PRODUCT_INDEX ##"
        marker_end = "## END_PRODUCT_INDEX ##"
        
        logger.info(f"💉 [INJECTION] Tentative d'injection PRODUCT_INDEX ({len(content)} chars)")
        
        if "[[PRODUCT_INDEX]]" in text:
            logger.info("✅ [INJECTION] Balise [[PRODUCT_INDEX]] trouvée. Remplacement...")
            return text.replace("[[PRODUCT_INDEX]]", f"{marker_start}\n{content}\n{marker_end}")
            
        # Sinon injection standard entre balises
        logger.info(f"🧭 [INJECTION] Utilisation _inject_between_markers pour {marker_start}")
        return self._inject_between_markers(text, marker_start, marker_end, content)

    def _inject_between_catalogue_markers(self, text: str, content: str) -> str:
        return self._inject_between_markers(text, "[CATALOGUE_START]", "[CATALOGUE_END]", content)

    def _build_product_index_block(self, catalog, featured_ids=None) -> str:
        """Formatte l'index des produits pour le prompt (Support V2 multi-produits)."""
        if not catalog: return "Aucun produit disponible."

        lines = []
        product_count = 0
        # Cas 1 : Conteneur multi-produits {"products": [{"product_id": "...", "product_name": "...", "catalog_v2": {...}}]}
        if isinstance(catalog.get("products"), list):
            product_count = len([p for p in catalog["products"] if isinstance(p, dict)])
            for p in catalog["products"]:
                if not isinstance(p, dict): continue
                # On utilise directement les clés à plat fournies par le loader
                pid = p.get("product_id") or p.get("id") or ""
                name = p.get("product_name") or p.get("name") or pid
                if pid:
                    suffix = " [STATUT: UNIQUE_PRODUIT_BOUTIQUE]" if product_count == 1 else ""
                    lines.append(f"- [{pid}] {name}{suffix}")
        
        # Cas 2 : Mono-produit direct
        else:
            product_count = 1 if (catalog.get("product_id") or catalog.get("id")) else 0
            pid = catalog.get("product_id") or catalog.get("id")
            name = catalog.get("product_name") or catalog.get("name") or pid
            if pid:
                suffix = " [STATUT: UNIQUE_PRODUIT_BOUTIQUE]" if product_count == 1 else ""
                lines.append(f"- [{pid}] {name}{suffix}")

        if not lines: return "Aucun produit disponible."
        return "\n".join(lines)

    def _build_product_context_block(self, catalog, p_id) -> str:
        if not catalog or not p_id:
            return ""

        p_data = None
        if isinstance(catalog.get("products"), list):
            for p in catalog["products"]:
                cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
                pid = p.get("product_id") or cat.get("product_id")
                if pid == p_id:
                    p_data = cat
                    break
        else:
            mono_pid = str(catalog.get("product_id") or catalog.get("id") or "").strip()
            if mono_pid and mono_pid == str(p_id).strip():
                p_data = catalog
            else:
                p_data = catalog.get(p_id) if "v" not in catalog else catalog

        if not isinstance(p_data, dict):
            return ""

        return build_catalogue_block_from_catalog_v2(p_data)

    def _build_bot_format_markdown(self, bot_format: Dict[str, Any], product_catalog: Dict[str, Any]) -> str:
        """Construit un markdown compact des contraintes bot_format."""
        if not isinstance(bot_format, dict) or not bot_format:
            return ""

        sales_mode = str(bot_format.get("sales_mode") or "").strip()
        allowed_units_raw = bot_format.get("allowed_units") if isinstance(bot_format.get("allowed_units"), list) else []
        unit_aliases_legacy = bot_format.get("unit_aliases") if isinstance(bot_format.get("unit_aliases"), dict) else {}
        min_order = bot_format.get("min_order") if isinstance(bot_format.get("min_order"), dict) else {}
        min_value = min_order.get("value")
        min_unit = str(min_order.get("unit") or "").strip()
        specs = bot_format.get("specs") if isinstance(bot_format.get("specs"), list) else []
        rules = bot_format.get("validation_rules") if isinstance(bot_format.get("validation_rules"), list) else []

        # Supporte les deux formats:
        # - legacy: allowed_units=["lot_300"], unit_aliases={...}
        # - v1: allowed_units=[{"key":"lot_300","aliases":[...]}]
        unit_aliases: Dict[str, List[str]] = {}
        allowed_units: List[str] = []
        for row in allowed_units_raw:
            if isinstance(row, dict):
                key = str(row.get("key") or "").strip()
                aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
                clean_aliases = [str(a).strip().lower() for a in aliases if str(a).strip()]
                if key:
                    allowed_units.append(key)
                    if clean_aliases:
                        unit_aliases[key] = sorted(set(clean_aliases))
            else:
                key = str(row).strip()
                if key:
                    allowed_units.append(key)
        if isinstance(unit_aliases_legacy, dict):
            for key, aliases in unit_aliases_legacy.items():
                k = str(key or "").strip()
                if not k:
                    continue
                a_list = aliases if isinstance(aliases, list) else []
                clean_aliases = [str(a).strip().lower() for a in a_list if str(a).strip()]
                if clean_aliases:
                    merged = set(unit_aliases.get(k, []))
                    merged.update(clean_aliases)
                    unit_aliases[k] = sorted(merged)
        allowed_units = sorted(set([u for u in allowed_units if u]))

        lines: List[str] = []
        if sales_mode:
            lines.append(f"- Type de vente autorisé: `{sales_mode}`")
        if allowed_units:
            lines.append(f"- Unités autorisées: {', '.join(f'`{u}`' for u in allowed_units)}")
        if isinstance(min_value, (int, float)) and int(min_value) > 0 and min_unit:
            lines.append(f"- Commande minimum: `{int(min_value)} {min_unit}`")

        if unit_aliases:
            alias_lines: List[str] = []
            for unit, aliases in unit_aliases.items():
                a_list = aliases if isinstance(aliases, list) else []
                clean_aliases = [str(a).strip().lower() for a in a_list if str(a).strip()]
                if clean_aliases:
                    alias_lines.append(f"  - `{str(unit).strip()}` <= {', '.join(f'`{a}`' for a in clean_aliases)}")
            if alias_lines:
                lines.append("- Aliases d'unités:")
                lines.extend(alias_lines)

        required_spec_keys: List[str] = []
        optional_spec_keys: List[str] = []
        if specs:
            spec_lines: List[str] = []
            for s in specs:
                if not isinstance(s, dict):
                    continue
                key = str(s.get("key") or "").strip()
                if not key:
                    continue
                stype = str(s.get("type") or "text").strip().lower()
                allowed_values = s.get("values") if isinstance(s.get("values"), list) else []
                if not allowed_values:
                    allowed_values = s.get("allowed_values") if isinstance(s.get("allowed_values"), list) else []
                clean_values = [str(v).strip() for v in allowed_values if str(v).strip()]
                required = len(clean_values) > 0
                if required:
                    required_spec_keys.append(key)
                else:
                    optional_spec_keys.append(key)
                values_txt = ""
                if clean_values:
                    values_txt = f" values={', '.join(f'`{v}`' for v in clean_values)}"
                spec_lines.append(f"  - `{key}` ({stype}) required={str(required).lower()}{values_txt}")
            if spec_lines:
                lines.append("- Specs attendues:")
                lines.extend(spec_lines)

        if rules:
            rule_lines: List[str] = []
            for r in rules:
                if not isinstance(r, dict):
                    continue
                when = str(r.get("when") or "").strip()
                expected = str(r.get("expected") or "").strip()
                reject_reason = str(r.get("reject_reason") or "").strip()
                if when or expected or reject_reason:
                    rule_lines.append(f"  - when=`{when}` -> expected=`{expected}` reason=`{reject_reason}`")
            if rule_lines:
                lines.append("- Règles de rejet Python:")
                lines.extend(rule_lines)

        # Slots dynamiques + fantômes (observabilité + déterminisme)
        has_variant = False
        if isinstance(product_catalog, dict):
            vtree = product_catalog.get("v")
            has_variant = isinstance(vtree, dict) and len(vtree.keys()) > 1
        slots_active: List[str] = ["PRODUIT"]
        if has_variant:
            slots_active.append("VARIANT")
        slots_active.extend([f"SPEC_{k.upper()}" for k in required_spec_keys])
        slots_active.extend(["QUANTITÉ", "ZONE", "TÉLÉPHONE", "PAIEMENT"])
        slots_ghost: List[str] = []
        if not has_variant:
            slots_ghost.append("VARIANT")
        slots_ghost.extend([f"SPEC_{k.upper()}" for k in optional_spec_keys])
        lines.append("- Slots actifs: " + ", ".join(slots_active))
        if slots_ghost:
            lines.append("- Slots fantômes (N/A): " + ", ".join(slots_ghost))
        logger.info(
            "[SLOTS_INIT] %s",
            json.dumps(
                {
                    "active_slots": slots_active,
                    "ghost_slots": slots_ghost,
                    "required_specs": required_spec_keys,
                },
                ensure_ascii=False,
            ),
        )

        if not lines:
            return ""

        return "\n".join(lines)

    def _resolve_active_product_id(self, user_id: str, active_product_id: Optional[str]) -> tuple[str, str]:
        pid = str(active_product_id or "").strip()
        if pid:
            return pid, "argument"

        try:
            pid = str(order_tracker.get_custom_meta(user_id, "active_product_id", default="") or "").strip()
            if pid:
                return pid, "order_tracker.meta"
        except Exception:
            pass

        try:
            state = order_tracker.get_state(user_id)
            pid = str(getattr(state, "produit", "") or "").strip()
            if pid:
                return pid, "order_tracker.state"
        except Exception:
            pass

        return "", "none"

    def _select_product_catalog(self, catalog: Any, p_id: str) -> Optional[Dict[str, Any]]:
        if not isinstance(catalog, dict) or not p_id:
            return None

        plist = catalog.get("products")
        if isinstance(plist, list):
            for p in plist:
                if not isinstance(p, dict):
                    continue
                cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
                pid = str(p.get("product_id") or cat.get("product_id") or cat.get("id") or "").strip()
                if pid == str(p_id).strip():
                    return cat if isinstance(cat, dict) else None
            return None

        mono_pid = str(catalog.get("product_id") or catalog.get("id") or "").strip()
        if mono_pid and mono_pid == str(p_id).strip():
            return catalog

        nested = catalog.get(str(p_id).strip())
        if isinstance(nested, dict):
            return nested
        return None

    def _resolve_mono_product_id(self, catalog: Any) -> str:
        if not isinstance(catalog, dict):
            return ""
        plist = catalog.get("products")
        if isinstance(plist, list):
            products = [p for p in plist if isinstance(p, dict)]
            if len(products) == 1:
                p = products[0]
                cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
                return str(p.get("product_id") or cat.get("product_id") or cat.get("id") or "").strip()
            return ""
        pid = str(catalog.get("product_id") or catalog.get("id") or "").strip()
        return pid if pid else ""

    async def build_prompt(
        self,
        user_id: str,
        company_id: str,
        query: str,
        has_image: bool = False,
        active_product_id: str = None,
        active_product_label: str = None,
        featured_ids: List[str] = None,
        # Paramètres optionnels d'enrichissement (Regex/Meili)
        detected_location: str = None,
        shipping_fee_s: str = None,
        delivery_time_s: str = None,
        product_context_s: str = None,
        pricing_context_s: str = None,
        conversation_history_s: str = None,
        expected_deposit_str: str = None,
        company_name_s: str = None,
        company_phone_s: str = None,
        payment_phone_s: str = None,
        payment_methods_s: str = None,
        delai_message_s: str = None,
        shop_url_s: str = None,
        **kwargs
    ) -> str:
        """
        Assemble le prompt final (ARCHITECTURE RADICALE).
        """
        # Mapping arguments from kwargs (legacy names vs internal _s names)
        active_product_id = active_product_id or kwargs.get('active_product_id')
        active_product_label = active_product_label or kwargs.get('active_product_label')
        active_product_id, active_product_source = self._resolve_active_product_id(user_id, active_product_id)
        
        detected_location = detected_location or kwargs.get('detected_location')
        detected_location_s = detected_location
        shipping_fee_s = shipping_fee_s or kwargs.get('shipping_fee')
        delivery_time_s = delivery_time_s or kwargs.get('delivery_time')
        product_context_s = product_context_s or kwargs.get('product_context')
        pricing_context_s = pricing_context_s or kwargs.get('pricing_context')
        conversation_history_s = conversation_history_s or kwargs.get('conversation_history')
        expected_deposit_str = expected_deposit_str or kwargs.get('expected_deposit')
        company_name_s = company_name_s or kwargs.get('company_name')
        
        # Mettre à jour la checklist
        checklist = self.update_checklist_from_message(
            user_id, company_id, query, has_image
        )
        
        logger.info(
            "🧭 [PROMPT_BUILD] active_product_id=%s source=%s query='%s'",
            active_product_id or "None",
            active_product_source,
            str(query or "")[:80]
        )

        # Récupérer le catalogue
        catalog_v2 = get_company_catalog_v2(company_id)

        if not active_product_id:
            mono_pid = self._resolve_mono_product_id(catalog_v2)
            if mono_pid:
                active_product_id = mono_pid
                active_product_source = "mono_product_auto"
                try:
                    order_tracker.set_custom_meta(user_id, "active_product_id", mono_pid)
                except Exception:
                    pass
                logger.info("[AUTO_INJECT] Mono-produit détecté -> force active_product_id=%s", mono_pid)

        try:
            current_state = order_tracker.get_state(user_id)
        except Exception:
            current_state = None
        phase = self._compute_phase(current_state)

        # Récupérer le prompt statique
        static_prompt = await self.get_static_prompt(company_id, phase=phase)

        # Inject PRODUCT_INDEX
        try:
            idx_block = self._build_product_index_block(catalog_v2, featured_ids=featured_ids)
            logger.info(f"📦 [PROMPT_BUILD] Index block généré: {idx_block[:50]}...")
            static_prompt = self._inject_between_product_index_markers(static_prompt, idx_block)
        except Exception as e:
            logger.error(f"❌ [PROMPT_BUILD] Erreur injection PRODUCT_INDEX: {e}")
            pass

        # Inject product-specific context
        try:
            selected_catalog = self._select_product_catalog(catalog_v2, active_product_id) if active_product_id else None
            pc_block = self._build_product_context_block(selected_catalog or catalog_v2, active_product_id) if active_product_id else ""
            if not active_product_id:
                logger.info("ℹ️ [CATALOGUE_INJECTION] skipped reason=no_active_product_id")
            elif not isinstance(selected_catalog, dict):
                logger.warning("⚠️ [CATALOGUE_INJECTION] failed product_id=%s reason=product_catalog_not_found", active_product_id)
            elif not pc_block.strip():
                logger.warning("⚠️ [CATALOGUE_INJECTION] failed product_id=%s reason=empty_context_block", active_product_id)
            else:
                product_name = str(selected_catalog.get("product_name") or selected_catalog.get("name") or "").strip()
                bot_format = selected_catalog.get("bot_format")
                if not isinstance(bot_format, dict):
                    ui_state = selected_catalog.get("ui_state") if isinstance(selected_catalog.get("ui_state"), dict) else {}
                    bot_format = ui_state.get("bot_format") if isinstance(ui_state, dict) else None
                logger.info(
                    "✅ [CATALOGUE_INJECTION] success product_id=%s product_name='%s' block_chars=%s",
                    active_product_id,
                    product_name or "unknown",
                    len(pc_block)
                )
                logger.info(
                    "[CATALOGUE_MD_INJECTION] %s",
                    json.dumps(
                        {
                            "product_id": active_product_id,
                            "has_bot_format": bool(isinstance(bot_format, dict) and bot_format),
                            "allowed_units_count": len((bot_format or {}).get("allowed_units", [])) if isinstance(bot_format, dict) else 0,
                            "specs_count": len((bot_format or {}).get("specs", [])) if isinstance(bot_format, dict) else 0,
                            "validation_rules_count": len((bot_format or {}).get("validation_rules", [])) if isinstance(bot_format, dict) else 0,
                        },
                        ensure_ascii=False,
                    ),
                )
            logger.info(f"📦 [PROMPT_BUILD] Détails catalogue injectés (active_id={active_product_id}, {len(pc_block)} chars)")
            static_prompt = self._inject_between_catalogue_markers(static_prompt, pc_block)
        except Exception as e:
            logger.error(f"❌ [PROMPT_BUILD] Erreur injection CATALOGUE: {e}")
            pass

        # --- RÉCUPÉRATION DU PROFIL (BLOC 1) ---
        c_profile = {}
        try:
            c_profile = await company_cache.get_cached_company_profile(company_id)
        except Exception as ce:
            print(f"⚠️ [BLOC 2] Erreur cache entreprise: {ce}")

        # Déterminer les variables
        mode = self._infer_mode(query=query, checklist=checklist)
        done, total = checklist.completion()
        completion_rate = f"{done}/{total}"
        compact_context = self._build_compact_context(
            location=detected_location,
            shipping=shipping_fee_s,
            delivery=delivery_time_s,
            history=conversation_history_s
        )

        # --- PRÉPARATION DES ARGUMENTS (SAFE REPLACE) ---
        format_args = {
            "mode": mode,
            "context": compact_context,
            "checklist": checklist.to_string(),
            "checklist_json": checklist.to_json(),
            "expected_deposit": expected_deposit_str or c_profile.get("expected_deposit") or "2000",
            "company_name": company_name_s or c_profile.get("shop_name") or "Rue du Grossiste",
            "company_phone": company_phone_s or c_profile.get("whatsapp_number") or "non spécifié",
            "payment_phone": payment_phone_s or c_profile.get("wave_number") or "0787360757",
            "payment_methods": payment_methods_s or "Wave, Orange Money",
            "pricing_context": pricing_context_s or "",
            "shipping_fee": shipping_fee_s or str(c_profile.get("expedition_base_fee") or "selon zone"),
            "delivery_time": delivery_time_s or c_profile.get("delai_message") or "quelques minutes",
            "delai_message": delai_message_s or c_profile.get("delai_message") or "quelques minutes",
            "detected_location": detected_location_s or "",
            "conversation_history": conversation_history_s or "",
            "completion_rate": completion_rate,
            "shop_url": shop_url_s or c_profile.get("shop_url") or "",
            "shop_name": company_name_s or c_profile.get("shop_name") or "Rue du Grossiste",
            "bot_name": c_profile.get("bot_name") or "Jessica",
            "boutique_block": c_profile.get("boutique_block") or "Boutique en ligne",
            "wave_number": c_profile.get("wave_number") or "0787360757",
            "depot_amount": c_profile.get("expected_deposit") or "2000",
            "expedition_base_fee": c_profile.get("expedition_base_fee") or "3500",
            "sav_number": c_profile.get("sav_number") or "0787360757",
            "whatsapp_number": c_profile.get("whatsapp_number") or "0160924560",
            "support_hours": c_profile.get("support_hours") or "24h/7j",
            "return_policy": c_profile.get("return_policy") or "Veuillez nous contacter pour les retours.",
            # CURRENT QUERY (CRITICAL FOR ANTI-HALLUCINATION)
            "query": query or "",
            # Support for dynamic blocks from RAG engine
            "instruction_block": kwargs.get('instruction_block') or "",
            "validation_errors_block": kwargs.get('validation_errors_block') or "",
            "price_calculation_block": kwargs.get('price_calculation_block') or "",
            "catalogue_reference_block": kwargs.get('catalogue_reference_block') or ""
        }

        # Formatage final avec la nouvelle méthode sécurisée
        final_prompt = self._safe_format(static_prompt, **format_args)
        # Garde-fou format de sortie: impose une réponse client dans <response>...</response>.
        response_contract = (
            "\n\n<output_contract>\n"
            "Tu dois répondre STRICTEMENT dans ce format:\n"
            "<thinking>...</thinking>\n"
            "<response>Message client final</response>\n"
            "Rien en dehors de ces balises.\n"
            "</output_contract>\n"
        )
        think_contract = (
            "\n\n<thinking_contract>\n"
            "CRITIQUE: Utilise OBLIGATOIREMENT <thinking>...</thinking> et JAMAIS <think>...</think>.\n"
            "Le bloc <thinking> est obligatoire et doit contenir exactement les balises definies ci-dessous.\n"
            "Sans ce bloc, le systeme ne peut pas traiter ta reponse.\n"
            "</thinking_contract>\n"
        )
        if _env_flag("ENABLE_THINKING_PROMPT_GUARD", False) and "<thinking_contract>" not in final_prompt:
            final_prompt += think_contract
        if _env_flag("ENABLE_OUTPUT_CONTRACT_GUARD", False) and "<output_contract>" not in final_prompt:
            final_prompt += response_contract
        logger.info(
            "[PROMPT_PHASE_KPI] %s",
            json.dumps(
                {
                    "company_id": company_id,
                    "user_id": user_id,
                    "phase": phase,
                    "prompt_chars": len(final_prompt),
                    "prompt_tokens_approx": len(final_prompt) // 4,
                },
                ensure_ascii=False,
            ),
        )
        return final_prompt

# Singleton
prompt_system = SimplifiedPromptSystem()

def get_simplified_prompt_system():
    """Helper pour récupérer le système de prompt (Utilisé par simplified_rag_engine)"""
    return prompt_system
