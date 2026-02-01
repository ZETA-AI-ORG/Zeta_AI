#!/usr/bin/env python3
"""
🤖 BOTLIVE RAG HYBRID - Système hybride DeepSeek V3 + Groq 70B
Intégration du routeur intelligent avec prompts spécialisés et outils
"""

import os
import re
import re as regex
import json
import logging
import asyncio
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from app_utils import log3
from config import BOTLIVE_COOPERATIVE_HUMAN_MODE, LLM_TRANSMISSION_TOKEN
from core.order_state_tracker import order_tracker
from core.timezone_helper import (
    get_current_time_ci,
    is_same_day_delivery_possible,
    get_delivery_context_with_time,
)

# Imports locaux
from .hyde_smart_router import hyde_router
from .botlive_prompts_supabase import get_prompts_manager  # ← NOUVEAU: Supabase au lieu de hardcodé
from .botlive_tools import execute_tools_in_response, should_suggest_calculator, should_suggest_notepad
from core.loop_botlive_engine import get_loop_engine
from core.llm_response_validator import (
    build_system_state_check,
    extract_system_state_dict,
    validate_llm_response_checklist,
)

try:
    from rapidfuzz import process as rf_process
    from rapidfuzz import fuzz as rf_fuzz
except Exception:
    rf_process = None
    rf_fuzz = None

logger = logging.getLogger(__name__)

# Activation du court-circuit Python (forcé à True pour Botlive)
ENABLE_PYTHON_DIRECT = False

class BotliveRAGHybrid:
    """
    Système RAG hybride pour Botlive avec routage intelligent
    """
    
    def __init__(self, company_id: str = None):
        self.router = hyde_router
        self.company_id = company_id  # ← NOUVEAU: Stocker company_id
        
        # Initialiser le gestionnaire de prompts avec fallback
        try:
            self.prompts_manager = get_prompts_manager()
            if self.prompts_manager:
                logger.info("✅ [BOTLIVE_HYBRID] Prompts manager Supabase activé")
            else:
                logger.warning("⚠️ [BOTLIVE_HYBRID] Prompts manager None - Utilisation hardcodés")
        except Exception as e:
            logger.error(f"❌ [BOTLIVE_HYBRID] Erreur init prompts_manager: {e}")
            self.prompts_manager = None
        
        self.stats = {
            'total_requests': 0,
            'primary_llm_requests': 0,  # Groq 70B principal
            'fallback_llm_requests': 0,  # Fallback éventuel
            'tools_used': 0,
            'fallbacks': 0
        }
        
        # (Désactivé) Ancien système "Cerveau Dual" (notification/modes) retiré pour stabilité.
        self.notification_service = None

    def _record_python_verdict(self, context: Dict[str, Any], trigger: Dict[str, Any], suggestion: str) -> None:
        try:
            if not isinstance(context, dict):
                return
            verdicts = context.get("python_verdicts")
            if not isinstance(verdicts, list):
                verdicts = []
                context["python_verdicts"] = verdicts
            entry = {
                "type": trigger.get("type"),
                "data": trigger.get("data"),
                "suggestion": suggestion,
            }
            verdicts.append(entry)
            try:
                logger.info(
                    "🧩 [PYTHON_VERDICT] type=%s data_keys=%s",
                    entry.get("type"),
                    list((entry.get("data") or {}).keys()) if isinstance(entry.get("data"), dict) else None,
                )
            except Exception:
                pass
        except Exception:
            return

    def _norm_text_simple(self, text: str) -> str:
        try:
            t = str(text or "").strip().lower()
        except Exception:
            t = ""
        if not t:
            return ""
        t = (
            t.replace("à", "a")
            .replace("â", "a")
            .replace("ä", "a")
            .replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("ë", "e")
            .replace("î", "i")
            .replace("ï", "i")
            .replace("ô", "o")
            .replace("ö", "o")
            .replace("ù", "u")
            .replace("û", "u")
            .replace("ü", "u")
            .replace("ç", "c")
        )
        t = regex.sub(r"[^a-z0-9\s-]+", " ", t)
        t = t.replace("-", " ")
        t = regex.sub(r"\s+", " ", t).strip()
        return t

    def _norm_text_match(self, text: str) -> str:
        try:
            import unicodedata

            t = str(text or "").strip().lower()
            if not t:
                return ""
            t = unicodedata.normalize("NFKD", t)
            t = "".join(ch for ch in t if not unicodedata.combining(ch))
        except Exception:
            t = str(text or "").strip().lower()
        if not t:
            return ""
        t = regex.sub(r"[^a-z0-9\s-]+", " ", t)
        t = t.replace("-", " ")
        t = regex.sub(r"\s+", " ", t).strip()
        return t

    def _product_id_hash(self, product_name: str) -> str:
        n = self._norm_text_simple(product_name)
        if not n:
            return ""
        h = hashlib.sha1(n.encode("utf-8", errors="replace")).hexdigest()[:8]
        return f"prod_{h}"

    def _inject_between(self, prompt: str, start_tag: str, end_tag: str, content: str) -> str:
        base = str(prompt or "")
        if not base.strip():
            return base
        s = str(start_tag or "")
        e = str(end_tag or "")
        if not s or not e:
            return base
        si = base.find(s)
        ei = base.find(e)
        if si == -1 or ei == -1 or ei <= si:
            return base
        block_start = si + len(s)
        c = str(content or "")
        if c and not c.startswith("\n"):
            c = "\n" + c
        if c and not c.endswith("\n"):
            c = c + "\n"
        return base[:block_start] + c + base[ei:]

    def _inject_product_index(self, prompt: str, idx_block: str) -> str:
        base = str(prompt or "")
        block = str(idx_block or "").strip()
        if not base.strip() or not block:
            return base
        if "[[PRODUCT_INDEX]]" in base:
            return base.replace("[[PRODUCT_INDEX]]", block)
        return self._inject_between(base, "[[PRODUCT_INDEX_START]]", "[[PRODUCT_INDEX_END]]", "\n" + block + "\n")

    def _inject_catalogue_markers(self, prompt: str, content: str) -> str:
        base = str(prompt or "")
        if not base.strip():
            return base
        pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
        matches = list(regex.finditer(pat, base, flags=regex.IGNORECASE | regex.DOTALL))
        if not matches:
            return base
        m = matches[-1]
        start_marker = "[CATALOGUE_START]"
        end_marker = "[CATALOGUE_END]"
        c = str(content or "").strip()
        replacement = start_marker + "\n" + c + "\n" + end_marker if c else (start_marker + "\n\n" + end_marker)
        return base[: m.start()] + replacement + base[m.end() :]

    def _build_flash_constraint(self, mono_catalog_v2: Dict[str, Any]) -> str:
        try:
            if not isinstance(mono_catalog_v2, dict):
                return ""
            vtree = mono_catalog_v2.get("v")
            if not isinstance(vtree, dict) or not vtree:
                return ""
            parts = []
            for vk, vnode in vtree.items():
                if not isinstance(vnode, dict):
                    continue
                has_specs = isinstance(vnode.get("s"), dict) and bool(vnode.get("s"))
                tag = "VARIABLE" if has_specs else "FIXE"
                vn = str(vk or "").strip()
                if vn:
                    parts.append(f"{vn}={tag}")
            parts = [p for p in parts if p]
            if not parts:
                return ""
            return " | ".join(parts[:6])
        except Exception:
            return ""

    def _build_light_product_index(self, company_catalog_container: Dict[str, Any], *, hide_variants_for_product_id: str = "") -> Tuple[str, Dict[str, Dict[str, Any]]]:
        products_by_id: Dict[str, Dict[str, Any]] = {}
        if not isinstance(company_catalog_container, dict):
            return "", products_by_id

        plist = company_catalog_container.get("products")
        mono = None
        if isinstance(plist, list) and plist:
            products = [p for p in plist if isinstance(p, dict)]
        else:
            products = []
            if isinstance(company_catalog_container.get("v"), dict):
                mono = company_catalog_container
                products = [{"product_name": str(mono.get("product_name") or mono.get("name") or "").strip(), "catalog_v2": mono}]

        lines = []
        for p in products:
            cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else None
            if not isinstance(cat, dict):
                continue
            pname = str(p.get("product_name") or cat.get("product_name") or cat.get("name") or "").strip()
            if not pname:
                continue
            pid = self._product_id_hash(pname)
            if not pid:
                continue
            vtree = cat.get("v")
            variants = []
            if isinstance(vtree, dict) and vtree:
                variants = [str(k).strip() for k in vtree.keys() if str(k).strip()]
                variants = sorted(set(variants), key=lambda x: x.lower())

            products_by_id[pid] = {
                "product_name": pname,
                "product_id": pid,
                "variants": variants,
                "catalog_v2": cat,
            }

        if not products_by_id:
            return "", products_by_id

        for pid, info in sorted(products_by_id.items(), key=lambda kv: str(kv[1].get("product_name") or "").lower()):
            pname = str(info.get("product_name") or "").strip()
            if not pname:
                continue
            variants = list(info.get("variants") or [])
            if hide_variants_for_product_id and str(hide_variants_for_product_id) == str(pid):
                variants = []
            variants_s = ", ".join(variants) if variants else "Aucune"
            flash = self._build_flash_constraint(info.get("catalog_v2") if isinstance(info.get("catalog_v2"), dict) else {})
            if flash:
                lines.append(f"- {pname} [ID: {pid}] | Variantes: {variants_s} | Flash: {flash}")
            else:
                lines.append(f"- {pname} [ID: {pid}] | Variantes: {variants_s}")

        block = "\n".join(lines).strip()
        return block, products_by_id

    def _pick_product_id_strict(self, message: str, products_by_id: Dict[str, Dict[str, Any]]) -> str:
        msg = self._norm_text_match(message)
        if not msg or not isinstance(products_by_id, dict) or not products_by_id:
            return ""

        for pid, info in products_by_id.items():
            pname = self._norm_text_match(str(info.get("product_name") or ""))
            if pname and pname in msg:
                return str(pid)

        variant_hits: Dict[str, set] = {}
        for pid, info in products_by_id.items():
            for v in (info.get("variants") or []):
                vn = self._norm_text_match(v)
                if vn and re.search(r"\b" + re.escape(vn) + r"\b", msg, flags=re.IGNORECASE):
                    variant_hits.setdefault(vn, set()).add(str(pid))

        for vn, pids in variant_hits.items():
            if len(pids) == 1:
                return list(pids)[0]

        try:
            enabled = (os.getenv("BOTLIVE_PRODUCT_FUZZY_MATCH", "true") or "").strip().lower() in {"1", "true", "yes", "y", "on"}
        except Exception:
            enabled = True

        if (not enabled) or (rf_process is None) or (rf_fuzz is None):
            return ""

        try:
            thr_raw = os.getenv("BOTLIVE_PRODUCT_FUZZY_THRESHOLD", "80")
            threshold = int(str(thr_raw or "80").strip() or "80")
        except Exception:
            threshold = 80

        try:
            delta_raw = os.getenv("BOTLIVE_PRODUCT_FUZZY_DELTA", "4")
            min_delta = int(str(delta_raw or "4").strip() or "4")
        except Exception:
            min_delta = 4

        stop = {
            "je",
            "j",
            "veux",
            "voudrais",
            "svp",
            "stp",
            "de",
            "des",
            "du",
            "la",
            "le",
            "les",
            "un",
            "une",
            "a",
            "au",
            "pour",
            "avec",
            "et",
            "sur",
            "en",
            "c",
            "ce",
            "ces",
            "sa",
            "son",
            "ma",
            "mon",
            "mes",
            "ta",
            "ton",
            "tes",
            "vos",
            "votre",
            "suis",
            "est",
            "bonjour",
            "bonsoir",
            "salut",
        }

        tokens = [t for t in msg.split() if len(t) >= 3 and t not in stop]
        if not tokens:
            return ""

        keyword_to_pids: Dict[str, set] = {}
        for pid, info in products_by_id.items():
            pname = self._norm_text_match(str(info.get("product_name") or ""))
            if pname:
                keyword_to_pids.setdefault(pname, set()).add(str(pid))
                for w in pname.split():
                    if len(w) >= 3:
                        keyword_to_pids.setdefault(w, set()).add(str(pid))
            for v in (info.get("variants") or []):
                vn = self._norm_text_match(v)
                if vn:
                    keyword_to_pids.setdefault(vn, set()).add(str(pid))
                    for w in vn.split():
                        if len(w) >= 3:
                            keyword_to_pids.setdefault(w, set()).add(str(pid))

        choices = list(keyword_to_pids.keys())
        if not choices:
            return ""

        pid_scores: Dict[str, int] = {}
        for tok in tokens[:12]:
            best = rf_process.extractOne(tok, choices, scorer=rf_fuzz.WRatio)
            if not best:
                continue
            kw, score, _ = best
            try:
                score_i = int(score)
            except Exception:
                score_i = 0
            if score_i < threshold:
                continue
            pids = keyword_to_pids.get(str(kw) or "") or set()
            if len(pids) != 1:
                continue
            pid = list(pids)[0]
            prev = pid_scores.get(pid, 0)
            if score_i > prev:
                pid_scores[pid] = score_i

        if not pid_scores:
            return ""

        ranked = sorted(pid_scores.items(), key=lambda kv: kv[1], reverse=True)
        best_pid, best_score = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0
        if best_score >= threshold and (best_score - second) >= min_delta:
            return str(best_pid)

        return ""

    def _extract_product_id_from_text(self, text: str, products_by_id: Dict[str, Dict[str, Any]]) -> str:
        raw = str(text or "")
        if not raw.strip() or not isinstance(products_by_id, dict) or not products_by_id:
            return ""

        m = regex.search(r"<detected_product>\s*(prod_[0-9a-f]{8})\s*</detected_product>", raw, flags=regex.IGNORECASE)
        if m:
            pid = str(m.group(1) or "").lower().strip()
            if pid in products_by_id:
                return pid

        m = regex.search(r"<detected_product>\s*([^<]{2,120})\s*</detected_product>", raw, flags=regex.IGNORECASE)
        if m:
            cand_name = self._norm_text_match(str(m.group(1) or "").strip())
            if cand_name:
                hits = []
                for pid, info in products_by_id.items():
                    pname = self._norm_text_match(str(info.get("product_name") or ""))
                    if pname and pname == cand_name:
                        hits.append(str(pid))
                if len(hits) == 1 and hits[0] in products_by_id:
                    return hits[0]

        m = regex.search(r"Catalogue\s+propose\s*:\s*([^\n\r<]{2,160})", raw, flags=regex.IGNORECASE)
        if m:
            cand_name = self._norm_text_match(str(m.group(1) or "").strip())
            if cand_name:
                hits = []
                for pid, info in products_by_id.items():
                    pname = self._norm_text_match(str(info.get("product_name") or ""))
                    if pname and pname == cand_name:
                        hits.append(str(pid))
                if len(hits) == 1 and hits[0] in products_by_id:
                    return hits[0]

        m = regex.search(r"\"product_id\"\s*:\s*\"(prod_[0-9a-f]{8})\"", raw, flags=regex.IGNORECASE)
        if m:
            pid = str(m.group(1) or "").lower().strip()
            if pid in products_by_id:
                return pid

        m = regex.search(r"\bprod_[0-9a-f]{8}\b", raw, flags=regex.IGNORECASE)
        if m:
            pid = m.group(0).lower()
            if pid in products_by_id:
                return pid
        raw_norm = self._norm_text_match(raw)
        for pid, info in products_by_id.items():
            pname = self._norm_text_match(str(info.get("product_name") or ""))
            if pname and pname in raw_norm:
                return str(pid)
        return ""

    def _build_full_catalogue_block(self, mono_catalog_v2: Dict[str, Any]) -> str:
        if not isinstance(mono_catalog_v2, dict):
            return ""
        pname = str(mono_catalog_v2.get("product_name") or mono_catalog_v2.get("name") or "").strip()
        vtree = mono_catalog_v2.get("v")
        if not isinstance(vtree, dict) or not vtree:
            return f"# {pname}" if pname else ""
        lines = []
        if pname:
            lines.append(f"# {pname}")
        for vk in sorted([str(k).strip() for k in vtree.keys() if str(k).strip()], key=lambda x: x.lower()):
            vnode = vtree.get(vk)
            if not isinstance(vnode, dict):
                continue
            lines.append("")
            lines.append(f"## {vk}")

            specs = []
            s_map = vnode.get("s")
            if isinstance(s_map, dict) and s_map:
                specs = [str(k).strip() for k in s_map.keys() if str(k).strip()]
                specs = sorted(set(specs), key=lambda x: x.lower())
            if specs:
                lines.append("Specs: " + ", ".join(specs))

            units_set = set()
            u_map = vnode.get("u") if isinstance(vnode.get("u"), dict) else None
            if isinstance(u_map, dict) and u_map:
                for uk in u_map.keys():
                    if str(uk).strip():
                        units_set.add(str(uk).strip())
            if isinstance(s_map, dict) and s_map:
                for sub in s_map.values():
                    if not isinstance(sub, dict):
                        continue
                    uu = sub.get("u")
                    if not isinstance(uu, dict):
                        continue
                    for uk in uu.keys():
                        if str(uk).strip():
                            units_set.add(str(uk).strip())
            if units_set:
                units_sorted = sorted(units_set, key=lambda x: x.lower())
                lines.append("Units: " + ", ".join(units_sorted))

            has_specs = isinstance(vnode.get("s"), dict) and bool(vnode.get("s"))
            lines.append("Pricing: VARIABLE" if has_specs else "Pricing: FIXE")

        return "\n".join([ln for ln in lines if ln is not None]).strip()

    def _build_canonical_verdict(self, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            verdicts = context.get("python_verdicts") if isinstance(context, dict) else None
            verdicts = verdicts if isinstance(verdicts, list) else []

            def _last_by_type(prefix: str) -> Optional[Dict[str, Any]]:
                for v in reversed(verdicts):
                    try:
                        if isinstance(v, dict) and str(v.get("type") or "") == prefix:
                            return v
                    except Exception:
                        continue
                return None

            def _last_type_in(types: list) -> Optional[Dict[str, Any]]:
                wanted = {str(t) for t in (types or [])}
                for v in reversed(verdicts):
                    try:
                        if isinstance(v, dict) and str(v.get("type") or "") in wanted:
                            return v
                    except Exception:
                        continue
                return None

            msg = str((context.get("message") if isinstance(context, dict) else "") or "")
            images = context.get("images", []) if isinstance(context, dict) else []
            has_images = isinstance(images, list) and len(images) > 0

            # Permet de persister l'état (produit déjà validé) à travers les tours.
            # Important: un screenshot de paiement ne doit pas rétrograder PHOTO.
            user_id = str(context.get("user_id") or "").strip() if isinstance(context, dict) else ""

            # IMPORTANT: next_action dépend de l'état global (notamment produit_details).
            # Sans order_state, ce bloc levait une exception silencieuse et forçait NEXT=COLLECT_PHOTO par défaut.
            order_state = None
            try:
                if isinstance(context, dict):
                    order_state = context.get("order_state")
            except Exception:
                order_state = None
            try:
                if order_state is None and user_id:
                    order_state = order_tracker.get_state(user_id)
            except Exception:
                order_state = None

            photo_v = _last_by_type("photo_produit")
            zone_v = _last_by_type("zone_detectee")
            tel_v = _last_type_in(["telephone_final", "telephone_detecte"])
            pay_v = _last_by_type("paiement_ocr")

            photo_data = (photo_v or {}).get("data") if isinstance(photo_v, dict) else {}
            zone_data = (zone_v or {}).get("data") if isinstance(zone_v, dict) else {}
            tel_data = (tel_v or {}).get("data") if isinstance(tel_v, dict) else {}
            pay_data = (pay_v or {}).get("data") if isinstance(pay_v, dict) else {}

            # Fallback: si aucune détection photo sur CE tour, mais produit déjà connu en mémoire,
            # on conserve PHOTO=✅.
            try:
                if (not isinstance(photo_data, dict) or not photo_data) and user_id:
                    st = order_tracker.get_state(user_id)
                    if getattr(st, "produit", None):
                        photo_data = {
                            "description": str(getattr(st, "produit") or "").strip(),
                            "confidence": None,
                            "error": None,
                            "valid": True,
                            "product_detected": True,
                        }
            except Exception:
                pass

            try:
                if (not isinstance(zone_data, dict) or not zone_data) and user_id:
                    st = order_tracker.get_state(user_id)
                    zone_val = str(getattr(st, "zone", "") or "").strip()
                    if zone_val:
                        zone_data = {
                            "zone": zone_val,
                            "name": zone_val,
                            "detected": True,
                        }
                        try:
                            if isinstance(context, dict) and context.get("delivery_cost") is not None:
                                zone_data["cost"] = int(context.get("delivery_cost"))
                        except Exception:
                            pass
            except Exception:
                pass

            def _status_from_flags(*, present: bool, valid: Optional[bool] = None, refused: bool = False) -> str:
                if refused:
                    return "REFUSED"
                if not present:
                    return "MISSING"
                if valid is True:
                    return "VALIDATED"
                if valid is False:
                    return "INVALID"
                return "PENDING"

            photo_present = bool(photo_data)
            photo_valid = bool(photo_data.get("valid")) if isinstance(photo_data, dict) else False
            if photo_present:
                photo_status = _status_from_flags(present=True, valid=(True if photo_valid else False))
            elif has_images:
                # Image présente mais pas une photo produit (ex: reçu Wave) -> ne pas invalider.
                photo_status = "PENDING"
            else:
                photo_status = "MISSING"

            zone_present = bool(zone_data.get("zone")) or bool(zone_data.get("name")) or bool(zone_data.get("detected"))
            zone_detected = bool(zone_data.get("detected")) if isinstance(zone_data, dict) else False
            zone_status = _status_from_flags(present=zone_present, valid=(True if zone_detected else (False if zone_present else None)))

            tel_present = bool(tel_data.get("number")) or bool(tel_data.get("raw_input"))
            tel_valid = bool(tel_data.get("valid")) if isinstance(tel_data, dict) else False
            tel_status = _status_from_flags(present=tel_present, valid=(True if tel_valid else (False if tel_present else None)))

            pay_amount = 0
            try:
                pay_amount = int(pay_data.get("amount", 0) or 0) if isinstance(pay_data, dict) else 0
            except Exception:
                pay_amount = 0
            pay_refused = bool(pay_data.get("error_message")) if isinstance(pay_data, dict) else False
            pay_sufficient = bool(pay_data.get("sufficient")) if isinstance(pay_data, dict) else False
            pay_present = bool(pay_data) or (pay_amount > 0)

            # Anti-pollution OCR:
            # Tant que Photo+Zone+Tel ne sont pas validés, un échec OCR ne doit PAS devenir un "paiement refusé".
            # Seul un paiement réellement validé (sufficient=True / amount>0) remonte.
            in_payment_phase = (photo_status == "VALIDATED") and (zone_status == "VALIDATED") and (tel_status == "VALIDATED")
            if not in_payment_phase and not pay_sufficient:
                # Hors phase paiement: ignorer complètement les données OCR paiement
                pay_refused = False
                pay_sufficient = False
                pay_amount = 0
                try:
                    if isinstance(pay_data, dict):
                        pay_data = dict(pay_data)
                        pay_data.pop("error_message", None)
                        pay_data["error_message"] = None
                        pay_data["sufficient"] = False
                        pay_data["amount"] = 0
                except Exception:
                    pass
                pay_status = "MISSING"
            else:
                pay_status = _status_from_flags(
                    present=pay_present,
                    valid=(True if pay_sufficient else (False if pay_present else None)),
                    refused=pay_refused,
                )

            next_action = "COLLECT_UNKNOWN"
            if photo_status != "VALIDATED":
                next_action = "COLLECT_PHOTO"
            elif not getattr(order_state, "produit_details", None):
                next_action = "COLLECT_SPECS"
            elif zone_status != "VALIDATED":
                next_action = "COLLECT_ZONE"
            elif tel_status != "VALIDATED":
                next_action = "VALIDATE_TEL" if tel_status == "INVALID" else "COLLECT_TEL"
            elif pay_status != "VALIDATED":
                next_action = "REQUEST_WAVE"
            else:
                next_action = "TRANSFER_HUMAN"

            verdict_global = {
                "next_action": next_action,
                "photo": {
                    "status": photo_status,
                    "value": photo_data.get("description") if isinstance(photo_data, dict) else None,
                    "confidence": photo_data.get("confidence") if isinstance(photo_data, dict) else None,
                    "suggestion": (photo_v or {}).get("suggestion") if isinstance(photo_v, dict) else None,
                },
                "zone": {
                    "status": zone_status,
                    "value": zone_data.get("name") or zone_data.get("zone") if isinstance(zone_data, dict) else None,
                    "cost": zone_data.get("cost") if isinstance(zone_data, dict) else None,
                    "suggestion": (zone_v or {}).get("suggestion") if isinstance(zone_v, dict) else None,
                },
                "telephone": {
                    "status": tel_status,
                    "raw_input": tel_data.get("raw_input") if isinstance(tel_data, dict) else None,
                    "value": tel_data.get("number") if isinstance(tel_data, dict) else None,
                    "error": tel_data.get("format_error") if isinstance(tel_data, dict) else None,
                    "suggestion": (tel_v or {}).get("suggestion") if isinstance(tel_v, dict) else None,
                },
                "paiement": {
                    "status": pay_status,
                    "amount": pay_amount,
                    "error": pay_data.get("error_message") if isinstance(pay_data, dict) else None,
                    "sufficient": pay_sufficient,
                    "suggestion": (pay_v or {}).get("suggestion") if isinstance(pay_v, dict) else None,
                },
                "raw_input": {
                    "message": msg,
                    "images_count": len(images) if isinstance(images, list) else 0,
                },
            }

            context["verdict_global"] = verdict_global
            return verdict_global
        except Exception:
            return {}

    def _format_canonical_verdict_for_prompt(self, context: Dict[str, Any]) -> str:
        try:
            verdict = self._build_canonical_verdict(context)
            if not isinstance(verdict, dict) or not verdict:
                return ""

            def _st(status: str) -> str:
                m = {
                    "VALIDATED": "✅",
                    "MISSING": "∅",
                    "INVALID": "❌",
                    "REFUSED": "🚫",
                    "PENDING": "⏳",
                }
                return m.get(str(status or "").upper(), "⏳")

            photo = verdict.get("photo") or {}
            zone = verdict.get("zone") or {}
            tel = verdict.get("telephone") or {}
            pay = verdict.get("paiement") or {}

            photo_lbl = str(photo.get("value") or "").strip()
            zone_lbl = str(zone.get("value") or "").strip()
            tel_err = str(tel.get("error") or "").strip()
            pay_err = str(pay.get("error") or "").strip()

            zone_cost = zone.get("cost")
            try:
                zone_cost = int(zone_cost) if zone_cost is not None else None
            except Exception:
                zone_cost = zone.get("cost")

            pay_amt = pay.get("amount")
            try:
                pay_amt = int(pay_amt) if pay_amt is not None else 0
            except Exception:
                pay_amt = pay.get("amount")

            line_photo = f"PHOTO: {_st(photo.get('status'))}" + (f" ({photo_lbl})" if photo_lbl else "")
            line_zone = f"ZONE:  {_st(zone.get('status'))}" + (f" ({zone_lbl}{(' - ' + str(zone_cost) + 'F') if zone_cost else ''})" if zone_lbl else "")

            # TEL: message unique (UX), pas de codes techniques
            tel_status = str(tel.get("status") or "").upper()
            if tel_status == "VALIDATED":
                line_tel = f"TEL:   ✅" + (f" ({str(tel.get('value') or '').strip()})" if str(tel.get('value') or '').strip() else "")
            elif tel_status in {"INVALID", "REFUSED"}:
                line_tel = "TEL:   ❌"
            else:
                line_tel = "TEL:   ⏳"

            # PAY: Afficher ✅ si suffisant (même si autres champs manquants), sinon ∅ ou ❌
            # Cela permet de ne pas ignorer un paiement valide envoyé dès le début.
            pay_status = str(pay.get("status") or "").upper()
            pay_sufficient = bool(pay.get("sufficient"))
            
            if pay_sufficient:
                # Paiement valide et suffisant -> Toujours ✅
                line_pay = f"PAY:   ✅" + (f" ({pay_amt}F)" if pay_amt else "")
            elif pay_status == "VALIDATED":
                # Cas rare: validé manuellement sans flag sufficient
                line_pay = f"PAY:   ✅" + (f" ({pay_amt}F)" if pay_amt else "")
            elif info_ready and pay_err:
                # Erreur affichée seulement si on est en phase paiement
                line_pay = f"PAY:   ❌" + (f" ({pay_err})" if pay_err else "")
            else:
                # Sinon on attend
                line_pay = "PAY:   ⏳"

            next_action = str(verdict.get("next_action") or "").strip()
            next_line = f"NEXT:  {next_action}" if next_action else ""

            lines = [ln for ln in [line_photo, line_zone, line_tel, line_pay, next_line] if ln]
            return "\n".join(lines).strip()
        except Exception:
            return ""

    def _format_python_verdicts_for_prompt(self, context: Dict[str, Any]) -> str:
        try:
            verdicts = context.get("python_verdicts") if isinstance(context, dict) else None
            if not isinstance(verdicts, list) or not verdicts:
                return ""

            # Hors phase paiement (Photo+Zone+Tel non validés), on évite d'injecter des erreurs OCR longues.
            in_payment_phase = False
            try:
                vg = context.get("verdict_global") if isinstance(context, dict) else None
                if isinstance(vg, dict):
                    in_payment_phase = (
                        str(((vg.get("photo") or {}).get("status") or "")).upper() == "VALIDATED"
                        and str(((vg.get("zone") or {}).get("status") or "")).upper() == "VALIDATED"
                        and str(((vg.get("telephone") or {}).get("status") or "")).upper() == "VALIDATED"
                    )
                if not in_payment_phase:
                    user_id = str(context.get("user_id") or "").strip() if isinstance(context, dict) else ""
                    if user_id:
                        st = order_tracker.get_state(user_id)
                        in_payment_phase = bool(getattr(st, "produit", None) and getattr(st, "zone", None) and getattr(st, "numero", None))
            except Exception:
                in_payment_phase = False

            lines = ["PYTHON_VERDICTS (à respecter strictement):"]
            for v in verdicts[-6:]:
                if not isinstance(v, dict):
                    continue
                v_type = str(v.get("type") or "").strip()
                data = v.get("data")

                if v_type == "paiement_ocr" and not in_payment_phase:
                    try:
                        amt = 0
                        if isinstance(data, dict):
                            amt = int(data.get("amount", 0) or 0)
                        if amt <= 0:
                            continue
                    except Exception:
                        continue

                compact_data = data
                try:
                    if isinstance(data, dict):
                        if v_type == "paiement_ocr":
                            compact_data = {
                                "amount": int(data.get("amount", 0) or 0),
                                "valid": bool(data.get("valid")),
                                "sufficient": bool(data.get("sufficient")),
                                "currency": data.get("currency"),
                            }
                        elif v_type == "photo_produit":
                            compact_data = {
                                "description": data.get("description"),
                                "confidence": data.get("confidence"),
                                "valid": bool(data.get("valid")),
                            }
                        elif v_type in {"zone_detectee", "telephone_detecte", "telephone_final"}:
                            compact_data = {
                                k: data.get(k)
                                for k in ["zone", "name", "cost", "number", "valid", "raw_input"]
                                if k in data
                            }
                except Exception:
                    compact_data = data

                payload = ""
                try:
                    payload = json.dumps(compact_data, ensure_ascii=False)
                except Exception:
                    payload = str(compact_data)

                lines.append(f"- TYPE={v_type} | DATA={payload}")
            return "\n".join(lines).strip()
        except Exception:
            return ""

    def _format_scanner_truth_for_prompt(self, context: Dict[str, Any]) -> str:
        try:
            canon = self._format_canonical_verdict_for_prompt(context)
            details = self._format_python_verdicts_for_prompt(context)
            if canon and details:
                return canon + "\n\n" + details
            return canon or details or ""
        except Exception:
            return ""

    def _format_minimalist_checklist_for_prompt(self, context: Dict[str, Any]) -> str:
        try:
            vg = self._build_canonical_verdict(context)
            photo = (vg.get("photo") or {}) if isinstance(vg, dict) else {}
            zone = (vg.get("zone") or {}) if isinstance(vg, dict) else {}
            tel = (vg.get("telephone") or {}) if isinstance(vg, dict) else {}
            pay = (vg.get("paiement") or {}) if isinstance(vg, dict) else {}

            def _sym(status: str) -> str:
                s = str(status or "").upper().strip()
                if s == "VALIDATED":
                    return "✅"
                if s in {"INVALID", "REFUSED"}:
                    return "❌"
                if s == "MISSING":
                    return "∅"
                return "⏳"

            photo_label = str(photo.get("value") or "").strip()
            if len(photo_label) > 48:
                photo_label = photo_label[:48].rstrip() + "…"

            zone_label = str(zone.get("value") or "").strip()
            if len(zone_label) > 48:
                zone_label = zone_label[:48].rstrip() + "…"
            zone_cost = zone.get("cost")
            try:
                zone_cost = int(zone_cost) if zone_cost is not None else None
            except Exception:
                zone_cost = None

            pay_amt = pay.get("amount")
            try:
                pay_amt = int(pay_amt) if pay_amt is not None else 0
            except Exception:
                pay_amt = 0

            def _line(label: str, sym: str, details: str = "") -> str:
                l = f"{label}: {sym}".rstrip()
                d = (details or "").strip()
                if d:
                    l = f"{l} ({d})"
                return l

            photo_sym = _sym(photo.get("status"))
            zone_sym = _sym(zone.get("status"))
            tel_sym = _sym(tel.get("status"))
            pay_sym = _sym(pay.get("status"))

            photo_details = photo_label if (photo_label and photo_sym == "✅") else ""
            zone_details = ""
            if zone_label and zone_sym == "✅":
                zone_details = zone_label
                if zone_cost is not None:
                    zone_details = f"{zone_details} - {zone_cost}F"

            pay_details = f"{pay_amt}F" if pay_amt > 0 else ""

            lines = [
                _line("PHOTO", photo_sym, photo_details),
                _line("ZONE", zone_sym, zone_details),
                _line("TEL", tel_sym, ""),
                _line("PAY", pay_sym, pay_details),
            ]

            next_action = str((vg.get("next_action") if isinstance(vg, dict) else "") or "").strip()
            if next_action:
                lines.append(f"NEXT: {next_action}")

            return "\n".join([ln for ln in lines if ln is not None]).strip()
        except Exception:
            return ""
    
    def _categorize_post_order_message(self, message: str) -> str:
        """Catégorise un message post-commande sans LLM."""
        msg = (message or "").lower().strip()

        if any(w in msg for w in ["ok", "merci", "oui", "d'accord", "👍", "✅"]) and len(msg) < 25:
            return "CONFIRMATION"

        if any(w in msg for w in ["quand", "délai", "delai", "livraison", "livré", "livre", "arriver", "recevoir"]):
            return "DELAI"

        if any(w in msg for w in ["paiement", "payer", "avant", "après", "apres", "modalité", "modalite"]):
            return "PAIEMENT"

        if any(w in msg for w in ["récap", "recap", "résumé", "resume", "confirmez", "confirmation", "c'est bon", "cest bon"]):
            return "RECAP"

        if len(msg) < 3 or msg in [".", "..", "..."]:
            return "SILENCE"

        return "AUTRE"
        
    async def process_request(self, 
                            user_id: str,
                            message: str, 
                            context: Dict[str, Any],
                            conversation_history: str = "",
                            company_id: str = None) -> Dict[str, Any]:
        """
        Traite une requête avec le système hybride
        
        Args:
            user_id: Identifiant utilisateur
            message: Message utilisateur
            context: Contexte (vision, transactions, etc.)
            conversation_history: Historique conversation
        
        Returns:
            Dict: Réponse complète avec métadonnées
        """
        import os

        # Propager le company_id reçu dans l'instance (utile pour logs et fallback)
        if company_id and company_id != self.company_id:
            self.company_id = company_id

        print("\n========== DEBUG BOTLIVE SUPABASE ==========")
        print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
        _svc = os.getenv('SUPABASE_SERVICE_KEY')
        if _svc and len(_svc) > 12:
            _svc = _svc[:6] + "..." + _svc[-4:]
        print(f"SUPABASE_SERVICE_KEY: {_svc if _svc else 'MISSING'}")
        print(f"prompts_manager: {self.prompts_manager}")
        print(f"company_id reçu: {company_id} | self.company_id: {self.company_id}")
        print("============================================\n")

        # Sécuriser le contexte
        if context is None:
            context = {}

        # Toujours fournir user_id/message au builder des verdicts (persistance via order_tracker)
        try:
            context["user_id"] = user_id
            context["message"] = message
        except Exception:
            pass

        # Délai de livraison dynamique (aujourd'hui/demain) basé sur l'heure CI
        try:
            now_ci = get_current_time_ci()
            delai = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
        except Exception:
            now_ci = None
            delai = ""

        # NOTE: l'heure minute-par-minute dans le prompt casse le caching provider.
        # On utilise un bucket stable (Matin/Midi/Après-midi/Soir) à la place.
        try:
            bucket = ""
            if now_ci is not None:
                h = int(getattr(now_ci, "hour", 0) or 0)
                if 5 <= h < 11:
                    bucket = "Matin"
                elif 11 <= h < 14:
                    bucket = "Midi"
                elif 14 <= h < 19:
                    bucket = "Après-midi"
                else:
                    bucket = "Soir"

            if bucket and delai:
                delivery_context_val = f"⏰ HEURE CI: {bucket}. Livraison prévue {delai}."
            elif bucket:
                delivery_context_val = f"⏰ HEURE CI: {bucket}."
            elif delai:
                delivery_context_val = f"Livraison prévue {delai}."
            else:
                delivery_context_val = ""
        except Exception:
            delivery_context_val = ""

        if delai:
            context.setdefault("delai_message", delai)
        if delivery_context_val:
            context.setdefault("delivery_context", delivery_context_val)

        start_time = datetime.now()
        timings = {}  # Track temps par étape
        python_short_circuit = False
        prompt_used_key: str = ""
        prompt_expected_key: str = ""
        prompt_ok: Optional[bool] = None
        prompt_segment_letter: str = ""
        prompt_gating_path: str = ""
        
        try:
            # ═══ ÉTAPE 1: LLM FIXE POUR BOTLIVE (Groq 70B) ═══
            step_start = datetime.now()
            routing_mode = (os.getenv("BOTLIVE_ROUTING_MODE", "direct") or "direct").strip().lower()
            hyde_enabled = bool(routing_mode != "direct")
            llm_choice = "openrouter" if os.getenv("OPENROUTER_API_KEY") else "groq-70b"
            prompt_llm_choice = "openrouter" if llm_choice == "openrouter" else "groq-70b"
            routing_reason = "botlive_openrouter" if llm_choice == "openrouter" else "botlive_fixed_groq_70b"
            python_sc_env = os.getenv("BOTLIVE_PYTHON_SHORT_CIRCUIT_ENABLED")
            if python_sc_env is None:
                python_short_circuit_enabled = (llm_choice != "openrouter")
            else:
                python_short_circuit_enabled = (str(python_sc_env).strip().lower() == "true")
            router_metrics: Dict[str, Any] = {}
            timings["routing"] = (datetime.now() - step_start).total_seconds()
            
            logger.info(f"🎯 [BOTLIVE] Routage fixe: {llm_choice}")
            logger.info(
                "⚡ [CONFIG] BOTLIVE_ROUTING_MODE=%s | HYDE=%s",
                routing_mode,
                "❌ Désactivé (direct)" if not hyde_enabled else "✅ Activé",
            )
            try:
                openrouter_key_present = bool((os.getenv("OPENROUTER_API_KEY") or "").strip())
                openrouter_model = os.getenv("OPENROUTER_BOTLIVE_MODEL", os.getenv("LLM_MODEL", "mistralai/mistral-small-3.2-24b-instruct"))
                groq_default_model = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile")
                logger.info(
                    "🧭 [BOTLIVE][LLM_SELECTION] "
                    f"openrouter_key_present={openrouter_key_present} "
                    f"selected_llm={llm_choice} "
                    f"openrouter_model={openrouter_model} "
                    f"groq_default_model={groq_default_model} "
                    f"routing_reason={routing_reason}"
                )
            except Exception:
                pass
            
            # ═══ ÉTAPE 1.5: VALIDATION AUTOMATIQUE PAIEMENT ═══
            payment_validation = None
            if context.get('filtered_transactions'):
                from core.payment_validator import validate_payment_cumulative, format_payment_for_prompt
                
                # Extraire montant requis du contexte (dynamique)
                expected_deposit_str = context.get('expected_deposit', '2000 FCFA')
                try:
                    m = regex.search(r'(\d+)', expected_deposit_str)
                    required_amount = int(m.group(1)) if m else 2000
                except Exception:
                    required_amount = 2000
                
                payment_validation = validate_payment_cumulative(
                    current_transactions=context.get('filtered_transactions', []),
                    conversation_history=conversation_history,
                    required_amount=required_amount
                )
                
                logger.info(f"💰 Validation paiement: {payment_validation['message']}")
                try:
                    logger.info(
                        "🔍 [SCAN][OCR/TRANSACTIONS] Résultat : valid=%s total_received=%s required_amount=%s tx_count=%s",
                        bool(payment_validation.get("valid")),
                        payment_validation.get("total_received"),
                        required_amount,
                        len(context.get("filtered_transactions") or []),
                    )
                except Exception:
                    pass
                
                # Ajouter au contexte pour le prompt
                context['payment_validation'] = payment_validation
                
                # 🔥 CORRECTION CRITIQUE: Persister le paiement validé dans order_state
                if payment_validation.get('valid'):
                    from core.order_state_tracker import order_tracker
                    total_received = payment_validation.get('total_received', 0)
                    order_tracker.update_paiement(user_id, f"validé_{total_received}F")
                    logger.info(f"✅ [PERSISTENCE] Paiement {total_received}F sauvegardé pour {user_id}")
            
            # === DÉTECTION DIRECTE ET COURT-CIRCUIT PYTHON ===
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost
            from core.order_state_tracker import order_tracker as _ot
            from core.loop_botlive_engine import get_loop_engine
            state = _ot.get_state(user_id)

            # Normaliser les variables de prompt: certains templates utilisent {expected_deposit_str}
            # alors que le backend stocke historiquement expected_deposit.
            try:
                if isinstance(context, dict) and context.get("expected_deposit_str") is None:
                    context["expected_deposit_str"] = str(context.get("expected_deposit") or "2000 FCFA")
            except Exception:
                pass

            # Capture détails produit (ex: taille/pointure/couleur) quand un produit est déjà identifié.
            # Objectif: éviter que SetFit/segmenter classe cela comme SHOPPING→B et couper le flux NEXT.
            try:
                msg_lc_details = (message or "").strip().lower()
                payment_kw = [
                    "wave",
                    "paiement",
                    "payer",
                    "avance",
                    "acompte",
                    "depot",
                    "dépôt",
                    "deposer",
                    "déposer",
                    "versement",
                    "confirmation",
                ]
                has_detail_marker = any(k in msg_lc_details for k in [
                    "taille",
                    "pointure",
                    "couleur",
                    "42",
                    "43",
                    "44",
                    "xl",
                    "l ",
                    "m ",
                    "s ",
                ])
                looks_like_detail_statement = bool(
                    has_detail_marker
                    and not any(k in msg_lc_details for k in ["combien", "prix", "dispo", "disponible", "stock", "c'est combien"])
                )

                # Ne pas écraser des SPECS déjà collectées, et ne pas confondre une discussion paiement avec des specs.
                if (
                    getattr(state, "produit", None)
                    and looks_like_detail_statement
                    and not getattr(state, "produit_details", None)
                    and not any(k in msg_lc_details for k in payment_kw)
                ):
                    _ot.update_produit_details(user_id, (message or "").strip()[:300])
                    try:
                        context["produit_details"] = (message or "").strip()[:300]
                    except Exception:
                        pass
                    logger.info("[PYTHON_DIRECT][DETAILS] produit_details mémorisés")
            except Exception:
                pass

            # Enrichir delai_message avec infos livraison (zone + coût + délai) pour alimenter PLACEORDER.
            # IMPORTANT: on évite d'injecter des données minute-par-minute dans {question} (cache). Ici on enrichit {delai_message}.
            try:
                msg_lc = (message or "").strip().lower()
                has_delivery_ask = any(k in msg_lc for k in ["livraison", "livrer", "livré", "frais", "tarif", "coût", "cout"]) 
                if has_delivery_ask:
                    zi = None
                    zone_source = ""

                    # 1) Priorité: extraire la zone depuis le message (plus robuste: "livraison yopougon ?")
                    zi_msg = extract_delivery_zone_and_cost(str(message or ""))
                    if isinstance(zi_msg, dict) and zi_msg.get("name"):
                        zi = zi_msg
                        zone_source = "message"

                    # 2) Sinon fallback: zone déjà mémorisée dans l'état
                    if zi is None and getattr(state, "zone", None):
                        zi_state = extract_delivery_zone_and_cost(str(state.zone))
                        if isinstance(zi_state, dict) and zi_state.get("name"):
                            zi = zi_state
                            zone_source = "state"

                    if isinstance(zi, dict) and zi.get("name") and zi.get("cost"):
                        zone_name = str(zi.get("name") or "").strip()
                        cost_val = zi.get("cost")

                        # Persister la zone si elle n'est pas déjà en mémoire
                        try:
                            if zone_name and (not getattr(state, "zone", None) or str(getattr(state, "zone", "")).strip().lower() != zone_name.lower()):
                                _ot.update_zone(user_id, zone_name)
                                state = _ot.get_state(user_id)
                        except Exception:
                            pass

                        # Construire un delai_message complet (zone+coût+délai) pour PLACEORDER
                        delai_calcule = str(zi.get("delai_calcule") or "").strip()
                        if not delai_calcule:
                            try:
                                delai_calcule = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                            except Exception:
                                delai_calcule = ""

                        enriched = f"Livraison {zone_name}: {cost_val}F."
                        if delai_calcule:
                            enriched = f"{enriched} Délai: {delai_calcule}."
                        context["delai_message"] = enriched
                        context["delivery_info"] = zi
                        context["delivery_zone"] = zone_name
                        context["delivery_cost"] = cost_val
                        logger.info("[DELIVERY][PLACEORDER] delai_message enrichi source=%s zone=%s cost=%s", zone_source, zone_name, cost_val)
            except Exception:
                pass

            # 0. Intent embeddings "délai de livraison" → Python si score ≥ 0.80 (commande en cours)
            delay_similarity = 0.0
            if routing_mode != "direct":
                try:
                    from core.botlive_intent_router import get_delivery_delay_similarity
                    delay_similarity = float(get_delivery_delay_similarity(message))
                except Exception:
                    delay_similarity = 0.0

            msg_norm = (message or "").strip().lower()
            if routing_mode == "direct" and BOTLIVE_COOPERATIVE_HUMAN_MODE:
                try:
                    explicit_handoff_keywords = [
                        "parler a un humain",
                        "parler à un humain",
                        "parler a quelqu'un",
                        "parler à quelqu'un",
                        "parler a un conseiller",
                        "parler à un conseiller",
                        "un humain",
                        "un conseiller",
                    ]
                    negative_keywords = [
                        "service de merde",
                        "nul",
                        "pourri",
                        "inadmissible",
                    ]
                    explicit_handoff = any(kw in msg_norm for kw in explicit_handoff_keywords)
                    is_frustrated = any(kw in msg_norm for kw in negative_keywords)
                    if explicit_handoff or is_frustrated:
                        if isinstance(router_metrics, dict):
                            router_metrics["cooperative_mode"] = True
                            router_metrics["human_required"] = True
                            router_metrics["bypass_llm"] = True
                            router_metrics["handoff_reason"] = "direct_mode_disjoncteur"
                            router_metrics["routing_mode"] = routing_mode
                        end_time = datetime.now()
                        processing_time = (end_time - start_time).total_seconds()
                        return {
                            "response": None,
                            "status": "PENDING_HUMAN",
                            "human_required": True,
                            "bypass_llm": True,
                            "routing_reason": "cooperative_direct_mode_disjoncteur",
                            "processing_time": processing_time,
                            "timings": timings,
                            "router_metrics": {
                                **(router_metrics or {}),
                                "prompt_used_key": "D_GHOST",
                                "prompt_expected_key": "D_GHOST",
                                "prompt_ok": True,
                                "gating_path": "human_bypass",
                                "segment_letter": "D",
                            },
                            "tools_executed": False,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_cost": 0,
                            "success": True,
                        }
                except Exception:
                    pass
            is_delivery_price_question = (
                ("combien" in msg_norm or "prix" in msg_norm or "coût" in msg_norm or "cout" in msg_norm)
                and ("livraison" in msg_norm or "frais" in msg_norm)
            )
            has_delay_keywords = any(
                k in msg_norm
                for k in [
                    "delai",
                    "délai",
                    "quand",
                    "arrive",
                    "arriver",
                    "heure",
                    "pas encore reçu",
                    "pas encore recu",
                    "toujours pas",
                    "reçu",
                    "recu",
                ]
            )

            # Note: pas de réponse Python pour le prix livraison.
            # Le LLM répond via PLACEORDER grâce au {delai_message} enrichi ci-dessus.

            if python_short_circuit_enabled and (not state.is_complete()) and has_delay_keywords and delay_similarity >= 0.80:
                try:
                    delai_auto = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                except Exception:
                    from datetime import datetime as _dt
                    heure_tmp = _dt.now().hour
                    delai_auto = "aujourd'hui" if heure_tmp < 13 else "demain"

                zone_name = state.zone or "votre zone"
                processed_response = (
                    f"Pour une commande standard, la livraison pour {zone_name} est généralement prévue {delai_auto}. "
                    "Le livreur vous contactera pour préciser l'heure exacte 😊"
                )

                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()

                return {
                    'response': processed_response,
                    'thinking': "",
                    'llm_used': 'python',
                    'validation': None,
                    'routing_reason': 'python_delivery_delay_high_conf',
                    'processing_time': processing_time,
                    'timings': timings,
                    'router_metrics': {'delivery_delay_similarity': delay_similarity},
                    'tools_executed': False,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_cost': 0,
                    'success': True
                }

            # Court-circuit post-commande : 100% géré par Python (sans LLM)
            if state.is_complete():
                intent_post = self._categorize_post_order_message(message)

                # Construction réponses Python simples
                if intent_post == "CONFIRMATION":
                    processed_response = "Parfait ! On vous rappelle très vite 😊"
                elif intent_post == "DELAI":
                    zone_name = state.zone or "votre zone"
                    processed_response = f"Livraison {zone_name} sous 24-48h. On confirme avec vous."
                elif intent_post == "PAIEMENT":
                    montant = 0
                    try:
                        paiement_str = state.paiement or ""
                        m = regex.search(r"(\d+)", str(paiement_str))
                        montant = int(m.group(1)) if m else 0
                    except Exception:
                        pass
                    if montant > 0:
                        processed_response = f"Paiement avant livraison. Votre acompte de {montant}F est validé ✅"
                    else:
                        processed_response = "Paiement avant livraison. Votre acompte est bien validé ✅"
                elif intent_post == "RECAP":
                    montant = 0
                    try:
                        paiement_str = state.paiement or ""
                        m = regex.search(r"(\d+)", str(paiement_str))
                        montant = int(m.group(1)) if m else 0
                    except Exception:
                        pass
                    try:
                        delai_po = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                    except Exception:
                        from datetime import datetime as _dt
                        heure_actuelle_po = _dt.now().hour
                        delai_po = "aujourd'hui" if heure_actuelle_po < 13 else "demain"
                    if montant <= 0:
                        montant = 2000
                    processed_response = (
                        f"✅PARFAIT Commande confirmée 😊\n"
                        f"Livraison prévue {delai_po}, acompte de {montant} F déjà versé.\n"
                        "Nous vous rappellerons bientôt pour les détails et le coût total.\n"
                        "Veuillez ne pas répondre à ce message."
                    )
                elif intent_post == "SILENCE":
                    processed_response = ""
                else:  # AUTRE → escalade opérateur
                    processed_response = "Un collègue reprend avec vous sous peu pour finaliser."

                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()

                return {
                    'response': processed_response,
                    'thinking': "",
                    'llm_used': 'python',
                    'validation': None,
                    'routing_reason': f'post_order_{intent_post.lower()}',
                    'processing_time': processing_time,
                    'timings': timings,
                    'router_metrics': {'post_order_intent': intent_post},
                    'tools_executed': False,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_cost': 0,
                    'success': True
                }

            # Helpers
            def _safe_conf(val, default: float = 0.6) -> float:
                try:
                    if val is None:
                        return default
                    if isinstance(val, (int, float)):
                        return float(val)
                    s = str(val).strip().lower()
                    if s in ("high", "haut", "élevé", "eleve"):
                        return 0.9
                    if s in ("medium", "moyen"):
                        return 0.7
                    if s in ("low", "faible"):
                        return 0.5
                    return float(s)
                except Exception:
                    return default

            def _required_amount_from_context(ctx: Dict[str, Any]) -> int:
                try:
                    expected_deposit_str = ctx.get('expected_deposit', '2000 FCFA')
                    m = regex.search(r'(\d+)', str(expected_deposit_str))
                    return int(m.group(1)) if m else 2000
                except Exception:
                    return 2000

            # 1. Détection zone
            zone_info = extract_delivery_zone_and_cost(message)
            if zone_info and zone_info.get('name'):
                zone_name = zone_info['name']
                cost = zone_info.get('cost', 1500)
                _ot.update_zone(user_id, zone_name)
                logger.info(f"[PYTHON_DIRECT][ZONE] Zone détectée: {zone_name} ({cost}F)")
                try:
                    logger.info(
                        "🔍 [SCAN][REGEX_ZONE] Commune détectée : %s | Frais : %sF",
                        zone_name,
                        cost,
                    )
                except Exception:
                    pass

                # Si le message est une zone seule (ex: "abobo"), on court-circuite le LLM.
                # Objectif: éviter un appel Groq 70B inutile et garantir une réponse déterministe.
                msg_tokens = [t for t in (message or "").strip().lower().split() if t]
                is_zone_only_message = len(msg_tokens) <= 2
                if python_short_circuit_enabled and is_zone_only_message:
                    try:
                        delai_msg = str(context.get("delai_message") or "").strip()
                        if not delai_msg:
                            delai_msg = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                    except Exception:
                        delai_msg = ""

                    processed_response = (
                        f"Noté 👍 Livraison à {zone_name} → {cost}F 🚚\n"
                        f"Livraison prévue {delai_msg}.\n"
                        "Dernière info : votre numéro de téléphone ? 📞"
                    )

                    end_time = datetime.now()
                    processing_time = (end_time - start_time).total_seconds()
                    return {
                        'response': processed_response,
                        'thinking': '',
                        'llm_used': 'python',
                        'routing_reason': 'python_direct_zone_only',
                        'processing_time': processing_time,
                        'timings': timings,
                        'router_metrics': {
                            'python_direct_zone_only': True,
                            'prompt_used_key': 'PYTHON_SHORT_CIRCUIT',
                            'prompt_expected_key': 'PYTHON_SHORT_CIRCUIT',
                            'prompt_ok': True,
                        },
                        'tools_executed': False,
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_cost': 0,
                        'success': True
                    }

                # Sécurité: toujours enrichir le context pour que le LLM puisse répondre
                # même si le shortcut Python n'est pas exécuté (llm_takeover) ou échoue.
                try:
                    delai_from_zone = ""
                    if isinstance(zone_info, dict):
                        delai_from_zone = str(zone_info.get("delai_calcule") or "").strip()
                    if not delai_from_zone:
                        delai_from_zone = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                except Exception:
                    delai_from_zone = ""

                if delai_from_zone:
                    context.setdefault("delai_message", delai_from_zone)
                context.setdefault("delivery_zone", zone_name)
                context.setdefault("delivery_cost", cost)
                if isinstance(zone_info, dict):
                    if zone_info.get("category"):
                        context.setdefault("delivery_category", zone_info.get("category"))
                    if zone_info.get("source"):
                        context.setdefault("delivery_source", zone_info.get("source"))
                    if zone_info.get("confidence") is not None:
                        context.setdefault("delivery_confidence", zone_info.get("confidence"))
                    if zone_info.get("error"):
                        context.setdefault("delivery_error", zone_info.get("error"))

                engine = get_loop_engine()
                # Ajout des champs obligatoires pour TriggerValidator
                periph = {"port-bouët", "attécoubé", "bingerville", "songon", "anyama", "port-bouet", "attecoube"}
                centrale_zones = {"plateau", "cocody", "marcory", "koumassi", "treichville"}
                if zone_name and zone_name.lower() in centrale_zones:
                    category = "centrale"
                elif zone_name and zone_name.lower() in periph:
                    category = "peripherique"
                else:
                    category = "expedition"
                source = "delivery_info" if isinstance(zone_info, dict) else "regex_message"
                confidence = _safe_conf(zone_info.get('confidence'), 0.9) if isinstance(zone_info, dict) else 0.6
                trigger = {
                    'type': 'zone_detectee',
                    'data': {
                        'zone': zone_name,
                        'cost': cost,
                        'name': zone_name,
                        'category': category,
                        'source': source,
                        'confidence': confidence,
                    }
                }
                loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                python_resp = engine._python_auto_response(trigger, loop_state, message)
                if python_resp and python_resp != "llm_takeover":
                    self._record_python_verdict(context, trigger, python_resp)

            # 2. Détection numéro
            message_text = context.get('message', message) or ''
            import re as regex
            numero_patterns = [
                r'\+225\s?0?([157]\d{8})',
                r'\b(0[157]\d{8})\b',
                r'\b0([157])\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\b'
            ]
            numero = None
            numero_raw_input = None
            for pattern in numero_patterns:
                match = regex.search(pattern, message_text)
                if match:
                    try:
                        numero_raw_input = match.group(0)
                    except Exception:
                        numero_raw_input = None
                    if len(match.groups()) == 1:
                        numero = match.group(1)
                    else:
                        numero = "0" + "".join(match.groups())
                    break
            if numero:
                _ot.update_numero(user_id, numero)
                logger.info(f"[PYTHON_DIRECT][TEL] Numéro détecté: {numero}")
                try:
                    logger.info("🔍 [SCAN][REGEX_TEL] Numéro valide : %s", numero)
                except Exception:
                    pass
                engine = get_loop_engine()
                after_state = _ot.get_state(user_id)
                tel_len = len(numero)
                tel_valid = bool(tel_len == 10 and numero.startswith('0'))
                tel_data = {
                    'raw': message_text,
                    'clean': numero,
                    'valid': tel_valid,
                    'length': tel_len,
                    'format_error': None,
                }
                if not tel_valid:
                    if tel_len < 10:
                        tel_data['format_error'] = 'TOO_SHORT'
                    elif tel_len > 10:
                        tel_data['format_error'] = 'TOO_LONG'
                    elif not numero.startswith('0'):
                        tel_data['format_error'] = 'WRONG_PREFIX'
                    else:
                        tel_data['format_error'] = 'INVALID_FORMAT'
                trigger_type = 'telephone_final' if (tel_valid and after_state.produit and after_state.paiement and after_state.zone) else 'telephone_detecte'
                tel_data['raw_input'] = numero_raw_input or message_text
                trigger = {'type': trigger_type, 'data': tel_data}
                loop_state = self._build_loop_state(after_state, context)
                python_resp = engine._python_auto_response(trigger, loop_state, message)
                if python_resp and python_resp != "llm_takeover":
                    self._record_python_verdict(context, trigger, python_resp)

            # 3. Détection PRODUIT depuis contexte (BLIP déjà exécuté en amont)
            detected_objects_ctx = context.get('detected_objects') or context.get('vision_objects') or []
            if isinstance(detected_objects_ctx, list) and detected_objects_ctx:
                def _obj_conf(o):
                    try:
                        if isinstance(o, dict):
                            return _safe_conf(o.get('confidence'), 0.8)
                        return 0.0
                    except Exception:
                        return 0.0
                # Normaliser name/label
                def _obj_name(o):
                    if isinstance(o, dict):
                        return o.get('name') or o.get('label') or o.get('type') or 'Produit détecté'
                    return str(o)
                best = max(detected_objects_ctx, key=_obj_conf)
                best_conf = _obj_conf(best)
                if best_conf >= 0.7:
                    produit_name = _obj_name(best)
                    _ot.update_produit(user_id, produit_name)
                    logger.info(f"[PYTHON_DIRECT][PHOTO] Produit détecté (ctx): {produit_name} ({best_conf:.2f})")
                    engine = get_loop_engine()
                    photo_data = {
                        'description': produit_name,
                        'confidence': best_conf,
                        'error': None,
                        'valid': True,
                        'product_detected': True,
                    }
                    trigger = {'type': 'photo_produit', 'data': photo_data}
                    loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                    python_resp = engine._python_auto_response(trigger, loop_state, message)
                    if python_resp and python_resp != "llm_takeover":
                        self._record_python_verdict(context, trigger, python_resp)

            # 3bis. Détection PAIEMENT depuis contexte (OCR déjà exécuté en amont)
            filtered_ctx = context.get('filtered_transactions') or []
            if isinstance(filtered_ctx, list) and filtered_ctx:
                try:
                    montant_ctx = int((filtered_ctx[0] or {}).get('amount', 0) or 0)
                except Exception:
                    try:
                        montant_ctx = int(str((filtered_ctx[0] or {}).get('amount', '0')).strip())
                    except Exception:
                        montant_ctx = 0
                if montant_ctx > 0:
                    req_amt = _required_amount_from_context(context)
                    if montant_ctx >= req_amt:
                        _ot.update_paiement(user_id, f"{montant_ctx}F")
                        logger.info(f"[PYTHON_DIRECT][PAIEMENT] Montant SUFFISANT détecté (ctx): {montant_ctx}F >= {req_amt}F -> SAUVEGARDÉ")
                    else:
                        logger.info(f"[PYTHON_DIRECT][PAIEMENT] Montant INSUFFISANT détecté (ctx): {montant_ctx}F < {req_amt}F -> NON SAUVEGARDÉ")
                engine = get_loop_engine()
                req_amt = _required_amount_from_context(context)
                sufficient_ctx = bool(montant_ctx >= req_amt)
                pay_data_ctx = {
                    'amount': montant_ctx,
                    'valid': bool(montant_ctx > 0),
                    'error': None,
                    'currency': 'FCFA',
                    'transactions': filtered_ctx or [],
                    'raw_text': '',
                    'sufficient': sufficient_ctx,
                }
                trigger = {'type': 'paiement_ocr', 'data': pay_data_ctx}
                loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                python_resp = engine._python_auto_response(trigger, loop_state, message)
                if python_resp and python_resp != "llm_takeover":
                    self._record_python_verdict(context, trigger, python_resp)

            # 4. Détection images (produit/paiement) si non fourni par contexte
            images = context.get('images', [])
            has_images = isinstance(images, list) and len(images) > 0
            if not has_images:
                try:
                    logger.info(" [SCAN][SKIP] Message texte pur : OCR et BLIP ignorés (images=[])")
                except Exception:
                    pass
            if has_images:
                # Éviter doublon: si la vision a déjà tourné en amont (ex: via Zeta_AI.app._process_botlive_vision)
                # et a rempli le contexte, ne pas relancer OCR/BLIP ici.
                try:
                    already_has_objs = isinstance(context.get('detected_objects'), list) and len(context.get('detected_objects') or []) > 0
                    already_has_txs = isinstance(context.get('filtered_transactions'), list) and len(context.get('filtered_transactions') or []) > 0
                except Exception:
                    already_has_objs = False
                    already_has_txs = False

                if already_has_objs or already_has_txs:
                    try:
                        logger.info(
                            " [SCAN][SKIP] Vision déjà présente dans context (objs=%s tx=%s) → skip OCR/BLIP",
                            already_has_objs,
                            already_has_txs,
                        )
                    except Exception:
                        pass
                    has_images = False

            if has_images:
                try:
                    logger.info(" [SCAN][START] Traitement images (OCR/BLIP) - images=%s", len(images))
                except Exception:
                    pass
                vision_result = await self._process_images(images, context)
                detected_objects = vision_result.get('detected_objects', [])
                filtered_transactions = vision_result.get('filtered_transactions', [])
                # Produit
                if detected_objects:
                    best_product = max(detected_objects, key=lambda x: x.get('confidence', 0))
                    if best_product.get('confidence', 0) >= 0.7:
                        produit_name = best_product.get('name', 'Produit détecté')
                        _ot.update_produit(user_id, produit_name)
                        logger.info(f"[PYTHON_DIRECT][PHOTO] Produit détecté: {produit_name}")
                        engine = get_loop_engine()
                        conf_val = _safe_conf(best_product.get('confidence'), 0.8)
                        photo_data = {
                            'description': produit_name,
                            'confidence': conf_val,
                            'error': None,
                            'valid': True,
                            'product_detected': True,
                        }
                        trigger = {'type': 'photo_produit', 'data': photo_data}
                        loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                        python_resp = engine._python_auto_response(trigger, loop_state, message)
                        if python_resp and python_resp != "llm_takeover":
                            self._record_python_verdict(context, trigger, python_resp)
                try:
                    current_state_after_vision = _ot.get_state(user_id)
                except Exception:
                    current_state_after_vision = state
                if (not bool(getattr(current_state_after_vision, "produit", None))) and (not detected_objects):
                    _ot.update_produit(user_id, "photo_recue")
                    logger.info("[PYTHON_DIRECT][PHOTO] Photo reçue mais aucun produit détecté -> produit=photo_recue")
                # Paiement
                if filtered_transactions:
                    best_payment = filtered_transactions[0]
                    try:
                        montant = int(best_payment.get('amount', 0) or 0)
                    except Exception:
                        try:
                            montant = int(str(best_payment.get('amount', '0')).strip())
                        except Exception:
                            montant = 0
                    if montant > 0:
                        req_amt = _required_amount_from_context(context)
                        if montant >= req_amt:
                            _ot.update_paiement(user_id, f"{montant}F")
                            logger.info(f"[PYTHON_DIRECT][PAIEMENT] Montant SUFFISANT détecté: {montant}F >= {req_amt}F -> SAUVEGARDÉ")
                        else:
                            logger.info(f"[PYTHON_DIRECT][PAIEMENT] Montant INSUFFISANT détecté: {montant}F < {req_amt}F -> NON SAUVEGARDÉ")
                    engine = get_loop_engine()
                    req_amt = _required_amount_from_context(context)
                    sufficient = bool(montant >= req_amt)
                    pay_data = {
                        'amount': montant,
                        'valid': bool(montant > 0),
                        'error': None,
                        'currency': 'FCFA',
                        'transactions': filtered_transactions or [],
                        'raw_text': '',
                        'sufficient': sufficient,
                    }
                    trigger = {'type': 'paiement_ocr', 'data': pay_data}
                    loop_state = self._build_loop_state(_ot.get_state(user_id), context)
                    python_resp = engine._python_auto_response(trigger, loop_state, message)
                    if python_resp and python_resp != "llm_takeover":
                        self._record_python_verdict(context, trigger, python_resp)
            # Si aucune détection, continuer flow (LLM)
            
            # ═══ ÉTAPE 2: GÉNÉRATION PROMPT SPÉCIALISÉ ═══
            step_start = datetime.now()
            
            # Préparer les données pour le prompt (optimisé tokens)
            raw_transactions = context.get('filtered_transactions', [])
            # Transactions COMPACTES (top 2)
            if isinstance(raw_transactions, list) and raw_transactions:
                top = raw_transactions[:2]
                compact_entries = []
                for t in top:
                    try:
                        amt = str(t.get('amount', '0'))
                        phone = str(t.get('phone', ''))
                        phone_short = f"…{phone[-4:]}" if phone and len(phone) >= 4 else phone
                        compact_entries.append(f"{amt}F:+225{phone_short}")
                    except Exception:
                        continue
                compact_transactions = ", ".join(compact_entries) if compact_entries else "0F"
            else:
                compact_transactions = "0F"

            # Si paiement validé automatiquement, enrichir le prompt
            if payment_validation:
                validation_message = format_payment_for_prompt(payment_validation)
                compact_transactions = f"{compact_transactions} | {validation_message}" if compact_transactions else validation_message
                logger.info(f"💳 Message validation ajouté au prompt: {validation_message[:150]}...")

            logger.debug(f"📋 TRANSACTIONS envoyées au LLM (compact): {compact_transactions[:300]}...")
            
            # ═══ RÉCUPÉRATION ÉTAT COMMANDE (MÉMOIRE CONTEXTE) ═══
            from core.order_state_tracker import order_tracker
            state = order_tracker.get_state(user_id)
            state_before = state
            state_was_complete = bool(state.is_complete())
            missing = state.get_missing_fields()
            
            # Résumé état COMPACT (éviter doublons avec règles Jessica)
            state_resume = (
                "ETAT_COMMANDE:\n"
                f"- produit:{'✅ ' + state.produit if state.produit else '❌'}  "
                f"- paiement:{'✅ ' + state.paiement if state.paiement else '❌'}  "
                f"- zone:{'✅ ' + state.zone if state.zone else '❌'}  "
                f"- tel:{'✅ ' + state.numero if state.numero else '❌'}\n"
            )

            # Checklist COMPACTE
            missing_list = []
            if not state.produit:
                missing_list.append('photo')
            if not getattr(state, 'produit_details', None):
                missing_list.append('specs')
            if not state.paiement:
                missing_list.append('paiement')
            if not state.zone:
                missing_list.append('zone')
            if not (state.numero and getattr(state, 'tel_valide', False)):
                missing_list.append('tel')
            compact_checklist = f"CHECKLIST: MISSING=[{', '.join(missing_list) if missing_list else 'aucun'}]"
            
            logger.info(f"📊 [ORDER_STATE] État pour {user_id}:")
            logger.info(f"   - Produit: {state.produit or 'NON COLLECTÉ'}")
            logger.info(f"   - Paiement: {state.paiement or 'NON COLLECTÉ'}")
            logger.info(f"   - Zone: {state.zone or 'NON COLLECTÉ'}")
            logger.info(f"   - Numéro: {state.numero or 'NON COLLECTÉ'}")
            
            # 06a NOUVEAU: Re9cupe9rer prompt brut depuis Supabase (Jessica)
            # Utiliser company_id du parame8tre ou de l'instance
            active_company_id = company_id or self.company_id
            if not active_company_id:
                raise ValueError("10 company_id requis pour re9cupe9rer les prompts Botlive")

            # Injecter le contexte delivery dans la question si disponible
            delivery_context = context.get('delivery_context', '')
            question_with_delivery = message
            if delivery_context:
                # IMPORTANT: ne pas injecter l'heure/contexte dynamique dans {question} (casse le caching)
                logger.info(f"8 [DELIVERY] Contexte delivery disponible ({len(str(delivery_context) or '')} chars) - non injecté dans la question")

            # 02 HYDE-LIKE: Hypothèse d'intent (désactivé par défaut car augmente tokens + casse cache + crée conflits)
            inject_intent_hypothesis = (os.getenv("BOTLIVE_INJECT_INTENT_HYPOTHESIS", "0") or "0").strip() in {"1", "true", "yes"}
            if inject_intent_hypothesis:
                try:
                    from core.intent_hypothesis import build_intent_hypothesis
                    hyp = build_intent_hypothesis(message)
                    if hyp:
                        question_with_delivery = f"{hyp}\n\n{question_with_delivery}"
                        logger.info(f"8 [HYPOTHESIS] Bloc intent ajoute9 ({len(hyp)} chars)")
                except Exception as e:
                    logger.warning(f"1f [HYPOTHESIS] Erreur injection: {e}")

            logger.info(f" [BOTLIVE] Re9cupe9ration prompt (Jessica) pour company_id={active_company_id}, llm={prompt_llm_choice}")

            # Ve9rifier si prompts_manager est disponible
            if not self.prompts_manager:
                logger.error(" [BOTLIVE] prompts_manager est None - Impossible de re9cupe9rer le prompt")
                raise ValueError("Prompts manager non initialise9 - Utiliser fallback _botlive_handle")

            # 06a Re9cupe9ration PROMPT + ROUTER EMBEDDINGS + JESSICA + HYDE SECOUR X 06a
            try:
                from core.botlive_intent_router import route_botlive_intent
                from core.jessica_prompt_segmenter import build_jessica_prompt_segment
                from core.hyde_secour_x import run_hyde_secour_x
                from core.company_catalog_v2_loader import get_company_catalog_v2_container

                # 1) Template brut Supabase pour Jessica (sans formatage global)
                # llm_choice="groq-70b" → lit prompt_botlive_groq_70b dans company_rag_configs
                base_prompt_template = self.prompts_manager.get_prompt(active_company_id, prompt_llm_choice)
                # 2) Construire state_compact pour le router embeddings
                state_compact = {
                    "photo_collected": bool(state.produit),
                    "specs_collected": bool(getattr(state, "produit_details", None)),
                    "paiement_collected": bool(state.paiement),
                    "zone_collected": bool(state.zone),
                    "tel_collected": bool(state.numero),
                    "tel_valide": bool(state.numero),
                    "collected_count": int(
                        bool(state.produit)
                        + bool(getattr(state, "produit_details", None))
                        + bool(state.paiement)
                        + bool(state.zone)
                        + bool(state.numero)
                    ),
                    "is_complete": bool(state.is_complete()),
                }

                # IMPORTANT:
                # Même en mode "direct", on ne doit PAS forcer un intent synthétique (ex: ACHAT_COMMANDE),
                # sinon le segmenter va systématiquement router vers le prompt C.
                # En mode direct, on désactive complètement le routage (SetFit/HYDE) pour réduire la latence.
                # On fabrique un routing minimal pour que le reste de la pipeline reste compatible.
                disable_routing = (routing_mode == "direct") or ((os.getenv("BOTLIVE_DISABLE_ROUTING", "false") or "").strip().lower() in {"1", "true", "yes", "y", "on"})
                if disable_routing:
                    from core.setfit_intent_router import BotliveRoutingResult

                    routing = BotliveRoutingResult(
                        intent="SHOPPING",
                        confidence=1.0,
                        intent_group="SHOPPING",
                        mode="GUIDEUR",
                        missing_fields=[],
                        state=state_compact or {},
                        debug={
                            "router": "disabled",
                            "router_source": "direct_env",
                            "routing_mode": routing_mode,
                        },
                    )
                else:
                    routing = await route_botlive_intent(
                        company_id=active_company_id,
                        user_id=user_id,
                        message=message,
                        conversation_history=conversation_history or "",
                        state_compact=state_compact,
                        hyde_pre_enabled=None,
                    )

                if routing is not None:
                    try:
                        routing_debug = getattr(routing, "debug", None)
                        bypass_llm = bool(routing_debug.get("bypass_llm")) if isinstance(routing_debug, dict) else False
                        human_required = bool(routing_debug.get("human_required")) if isinstance(routing_debug, dict) else False
                        # IMPORTANT: "human_required" peut servir à notifier l'humain (semi-auto)
                        # sans pour autant court-circuiter le LLM. Le court-circuit doit être piloté
                        # uniquement par bypass_llm.
                        if BOTLIVE_COOPERATIVE_HUMAN_MODE and bypass_llm:
                            if isinstance(router_metrics, dict):
                                router_metrics["cooperative_mode"] = True
                                router_metrics["human_required"] = True
                                router_metrics["bypass_llm"] = True
                                router_metrics["handoff_reason"] = "setfit_human_required"
                                router_metrics["intent"] = str(getattr(routing, "intent", "") or "")
                                router_metrics["confidence"] = float(getattr(routing, "confidence", 0.0) or 0.0)
                                router_metrics["routing_mode"] = routing_mode
                            end_time = datetime.now()
                            processing_time = (end_time - start_time).total_seconds()
                            return {
                                "response": None,
                                "status": "PENDING_HUMAN",
                                "human_required": True,
                                "bypass_llm": True,
                                "routing_reason": "cooperative_setfit_bypass_llm",
                                "processing_time": processing_time,
                                "timings": timings,
                                "router_metrics": {
                                    **(router_metrics or {}),
                                    "prompt_used_key": "D_GHOST",
                                    "prompt_expected_key": "D_GHOST",
                                    "prompt_ok": True,
                                    "gating_path": "human_bypass",
                                    "segment_letter": "D",
                                },
                                "tools_executed": False,
                                "prompt_tokens": 0,
                                "completion_tokens": 0,
                                "total_cost": 0,
                                "success": True,
                            }
                    except Exception:
                        pass

                if routing is not None:
                    logger.info(
                        " [EMB_ROUTER] intent=%s mode=%s conf=%.3f missing=%s",
                        routing.intent,
                        routing.mode,
                        routing.confidence,
                        routing.missing_fields,
                    )
                    try:
                        if isinstance(router_metrics, dict):
                            router_metrics.setdefault("intent", str(getattr(routing, "intent", "") or ""))
                            router_metrics.setdefault("confidence", float(getattr(routing, "confidence", 0.0) or 0.0))
                            router_metrics.setdefault("mode", str(getattr(routing, "mode", "") or ""))
                            try:
                                rdbg = getattr(routing, "debug", None)
                                if isinstance(rdbg, dict):
                                    router_metrics.setdefault("router_source", rdbg.get("router_source") or rdbg.get("router"))
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        log3(
                            "EMB_ROUTER",
                            {
                                "intent": routing.intent,
                                "confidence": routing.confidence,
                                "mode": routing.mode,
                                "missing_fields": routing.missing_fields,
                                "state_compact": routing.state,
                                "intent_score": routing.debug.get("intent_score"),
                                "raw_message": routing.debug.get("raw_message"),
                            },
                        )
                    except Exception:
                        pass

                # hyde_result structure compatible avec build_jessica_prompt_segment
                if routing is not None:
                    hyde_result = {
                        "success": True,
                        "intent": routing.intent,
                        "confidence": routing.confidence,
                        "mode": routing.mode,
                        "missing_fields": routing.missing_fields,
                        "state": routing.state,
                        "raw": (getattr(routing, "debug", None) or {}).get("raw_message", ""),
                        "token_info": {
                            "source": "router_setfit",
                            "intent_score": (getattr(routing, "debug", None) or {}).get("intent_score"),
                        },
                    }

                # ------------------------------------------------------------------
                # V5 SEMI-AUTO (SHOPPING): notifier l'équipe SANS appeler le LLM.
                # Prompt B devient un fallback (si on désactive ce bypass ou si besoin).
                # ------------------------------------------------------------------
                try:
                    bypass_shopping_llm = (os.getenv("BOTLIVE_SEMI_AUTO_SHOPPING_BYPASS_LLM", "false") or "").strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "y",
                        "on",
                    }
                    if (
                        bypass_shopping_llm
                        and BOTLIVE_COOPERATIVE_HUMAN_MODE
                        and routing_mode != "direct"
                        and str(getattr(routing, "intent", "") or "").upper() == "SHOPPING"
                    ):
                        fallback_msg = (
                            os.getenv(
                                "BOTLIVE_SEMI_AUTO_SHOPPING_FALLBACK_MESSAGE",
                                "Les infos (prix/stock/catalogue) sont sur le Live TikTok 📱. Je transmets à l'équipe, elle revient vers toi.",
                            )
                            or ""
                        ).strip()
                        if isinstance(router_metrics, dict):
                            router_metrics["cooperative_mode"] = True
                            router_metrics["human_required"] = True
                            router_metrics["bypass_llm"] = False
                            router_metrics["handoff_reason"] = "semi_auto_shopping_bypass_llm"
                            router_metrics["intent"] = str(getattr(routing, "intent", "") or "")
                            router_metrics["confidence"] = float(getattr(routing, "confidence", 0.0) or 0.0)
                            router_metrics["prompt_used_key"] = "SHOPPING_BYPASS_LLM"
                            router_metrics["prompt_expected_key"] = "JESSICA_PROMPT_B"
                            router_metrics["prompt_ok"] = True

                        end_time = datetime.now()
                        processing_time = (end_time - start_time).total_seconds()
                        return {
                            "response": fallback_msg,
                            "status": "PENDING_HUMAN",
                            "human_required": True,
                            "bypass_llm": False,
                            "routing_reason": "semi_auto_shopping_bypass_llm",
                            "processing_time": processing_time,
                            "timings": timings,
                            "router_metrics": {
                                **(router_metrics or {}),
                                "gating_path": "human_notify_only",
                                "segment_letter": "B",
                            },
                            "tools_executed": False,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_cost": 0,
                            "success": True,
                        }
                except Exception:
                    pass

                # 3) Premier passage Jessica pour obtenir le gating_path
                detected_objects_str = self._format_detected_objects(
                    context.get("detected_objects", [])
                )
                expected_deposit_str = context.get("expected_deposit", "2000 FCFA")

                # Mémoire épisodique (résumé long-terme persistant)
                resume_faits_saillants = ""
                try:
                    import os as _os
                    import redis as _redis

                    _redis_url = _os.getenv("REDIS_URL", "redis://localhost:6379/0")
                    _r = _redis.Redis.from_url(_redis_url, decode_responses=True)
                    _key = f"botlive_summary:{active_company_id}:{user_id}"
                    resume_faits_saillants = str(_r.get(_key) or "").strip()
                    if resume_faits_saillants:
                        try:
                            _words = resume_faits_saillants.split()
                            if len(_words) > 500:
                                resume_faits_saillants = " ".join(_words[-500:]).strip()
                        except Exception:
                            resume_faits_saillants = resume_faits_saillants[:4000].strip()
                except Exception:
                    resume_faits_saillants = ""

                # Troncature HISTORY (≈200 tokens ≈ 800 chars)
                # IMPORTANT: conversation_history doit contenir uniquement les tours passés.
                # On supprime le message courant s'il est déjà présent (souvent en dernier) pour éviter cache-busting.
                truncated_history = (conversation_history or "")
                try:
                    msg_norm = (message or "").strip()
                    if msg_norm and truncated_history:
                        lines = [ln.rstrip("\r") for ln in truncated_history.split("\n")]
                        while lines:
                            tail = (lines[-1] or "").strip()
                            if not tail:
                                lines.pop()
                                continue
                            tail_lc = tail.lower()
                            candidate = tail
                            if tail_lc.startswith("user:"):
                                candidate = tail.split(":", 1)[1].strip() if ":" in tail else ""
                            if candidate.strip() == msg_norm:
                                lines.pop()
                                continue
                            break
                        truncated_history = "\n".join(lines).strip()
                except Exception:
                    truncated_history = (conversation_history or "")
                if len(truncated_history) > 800:
                    truncated_history = "…" + truncated_history[-800:]

                # Forcer le chemin ACQUISITION (segment C) si on vient de capter un détail produit.
                try:
                    if isinstance(context, dict) and context.get("produit_details") and getattr(state, "produit", None) and (not getattr(state, "is_complete", lambda: False)()):
                        hyde_result["intent"] = "ACQUISITION"
                        hyde_result["mode"] = "ACQUISITION"
                        hyde_result["confidence"] = float(max(float(hyde_result.get("confidence") or 0.0), 0.90))
                except Exception:
                    pass

                segment = build_jessica_prompt_segment(
                    base_prompt_template=base_prompt_template,
                    hyde_result=hyde_result,
                    question_with_context=question_with_delivery,
                    conversation_history=truncated_history,
                    resume_faits_saillants=resume_faits_saillants,
                    detected_objects_str=detected_objects_str,
                    filtered_transactions_str=compact_transactions or "0F",
                    expected_deposit_str=expected_deposit_str,
                    enriched_checklist=self._format_minimalist_checklist_for_prompt(context),
                    routing=routing,
                    delai_message=context.get("delai_message", ""),
                )

                # Exposer prompt utilisé (clé logique, pas le texte)
                try:
                    prompt_segment_letter = str(segment.get("segment_letter") or "").strip().upper()
                    prompt_gating_path = str(segment.get("gating_path") or "").strip().lower()
                    used_light = bool(segment.get("used_light"))
                    used_prompt_x = bool(segment.get("used_prompt_x"))

                    if used_prompt_x:
                        prompt_used_key = "JESSICA_PROMPT_X"
                    elif prompt_segment_letter == "U":
                        prompt_used_key = "JESSICA_PROMPT_LIGHT_UNIQUE" if used_light else "JESSICA_PROMPT_UNIQUE"
                    elif used_light and prompt_segment_letter:
                        prompt_used_key = f"JESSICA_PROMPT_LIGHT_{prompt_segment_letter}"
                    elif prompt_segment_letter:
                        prompt_used_key = f"JESSICA_PROMPT_{prompt_segment_letter}"
                    else:
                        prompt_used_key = "JESSICA_PROMPT_UNKNOWN"
                except Exception:
                    prompt_used_key = "JESSICA_PROMPT_UNKNOWN"

                # Log du message utilisateur (bien distinct) + segment EXACT envoyé au LLM
                try:
                    log3("[USER][MESSAGE]", message or "", max_lines=10, max_length=800)
                except Exception:
                    pass

                try:
                    show_full_segment = (os.getenv("BOTLIVE_DEBUG_SHOW_FULL_SEGMENT", "false") or "").strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "y",
                        "on",
                    }
                    log3(
                        "[LLM][PROMPT_SEGMENT]",
                        f"prompt_used_key={prompt_used_key} | segment_letter={prompt_segment_letter} | gating_path={prompt_gating_path}\n\n{segment.get('prompt') or ''}",
                        max_lines=120,
                        max_length=12000,
                        show_full_in_console=show_full_segment,
                    )
                except Exception:
                    pass

                # Heuristique: quel bloc Jessica aurait dû être utilisé (A/B/C/D)
                try:
                    def _get_root_segment(prompt_key: str) -> str:
                        k = (prompt_key or "").strip().upper()
                        if not k:
                            return ""
                        if k in {"PYTHON_SHORT_CIRCUIT", "JESSICA_PROMPT_X", "JESSICA_PROMPT_UNIQUE", "JESSICA_PROMPT_LIGHT_UNIQUE"}:
                            return k
                        k = k.replace("JESSICA_PROMPT_", "")
                        k = k.replace("JESSICA_PROMPT_LIGHT_", "")
                        return k.split("_")[0]

                    # Mode prompt UNIQUE: on attend toujours UNIQUE (sauf PROMPT_X)
                    if _get_root_segment(prompt_used_key) in {"JESSICA_PROMPT_UNIQUE", "JESSICA_PROMPT_LIGHT_UNIQUE"}:
                        prompt_expected_key = prompt_used_key
                        prompt_ok = True
                    else:
                        msg_lower_expected = (message or "").strip().lower()
                        expected_letter = "A"
                        if any(k in msg_lower_expected for k in ["dispo", "disponible", "rupture", "stock", "en rupture", "il en reste"]):
                            expected_letter = "B"
                        elif any(k in msg_lower_expected for k in [
                            "paiement",
                            "wave",
                            "espèce",
                            "espece",
                            "option",
                            "options",
                            "obligatoire",
                        ]):
                            expected_letter = "C"
                        elif any(k in msg_lower_expected for k in [
                            "où en est",
                            "ou en est",
                            "ma commande",
                            "commande actuelle",
                            "suivi",
                            "tracking",
                            "livreur",
                            "pas encore",
                            "toujours pas",
                            "pas recu",
                            "pas reçu",
                        ]):
                            expected_letter = "D"
                        elif any(k in msg_lower_expected for k in ["livraison", "livrer", "livrez", "livré"]):
                            expected_letter = "C"
                        elif any(k in msg_lower_expected for k in ["couche", "couches", "modèle", "modeles", "modèles"]):
                            expected_letter = "B"
                        else:
                            expected_letter = "A"

                        # Conserver le même type de gating (light / standard / prompt_x)
                        # mais appliquer la lettre attendue.
                        if prompt_gating_path == "prompt_x":
                            prompt_expected_key = "JESSICA_PROMPT_X"
                        elif prompt_gating_path == "light":
                            prompt_expected_key = f"JESSICA_PROMPT_LIGHT_{expected_letter}"
                        else:
                            prompt_expected_key = f"JESSICA_PROMPT_{expected_letter}"

                        prompt_ok = bool(
                            _get_root_segment(prompt_used_key)
                            == _get_root_segment(prompt_expected_key)
                        )
                except Exception:
                    prompt_expected_key = ""
                    prompt_ok = None

                gating_path = segment.get("gating_path", "standard")
                logger.info(
                    " [JESSICA] gating_path=%s letter=%s conf=%.3f",
                    gating_path,
                    segment.get("segment_letter"),
                    float(segment.get("confidence") or 0.0),
                )

                # 4) HYDE SECOUR X si gating_path == "hyde" OU requête très courte (clarification via historique)
                force_hyde_short = False
                try:
                    _msg = (message or "").strip()
                    _tokens = [t for t in _msg.lower().split() if t]
                    force_hyde_short = (len(_tokens) <= 2 and len(_msg) <= 6) or (_msg.lower() in {"ok", "okay", "oui", "d'accord", "daccord"})
                except Exception:
                    force_hyde_short = False

                if gating_path == "hyde" or force_hyde_short:
                    try:
                        required_amount = required_amount if "required_amount" in locals() else 2000
                    except Exception:
                        required_amount = 2000

                    try:
                        hyde_raw = await run_hyde_secour_x(
                            base_prompt_template=base_prompt_template,
                            question=message,
                            conversation_history=conversation_history or "",
                            checklist=routing.state,
                            state=routing.state,
                            intent=routing.intent,
                            confidence=routing.confidence,
                            mode=routing.mode,
                            missing_fields=routing.missing_fields,
                            detected_objects=detected_objects_str,
                            filtered_transactions=compact_transactions or "0F",
                            expected_deposit=str(required_amount),
                        )

                        # Parse JSON minimal: {"hyde_question": "..."}
                        hyde_payload = None
                        try:
                            json_start = hyde_raw.find("{")
                            json_end = hyde_raw.rfind("}")
                            if (
                                json_start != -1
                                and json_end != -1
                                and json_end > json_start
                            ):
                                import json as _json

                                hyde_payload = _json.loads(
                                    hyde_raw[json_start : json_end + 1]
                                )
                        except Exception as parse_e:
                            logger.warning(
                                " [HYDE_X] Erreur parse JSON HYDE SECOUR X: %s",
                                parse_e,
                            )

                        if isinstance(hyde_payload, dict):
                            hyde_question = hyde_payload.get("hyde_question")
                            if isinstance(hyde_question, str) and hyde_question.strip():
                                original_text = (message or "").strip()
                                original_lower = original_text.lower()
                                hq = hyde_question.strip()
                                hq_lower = hq.lower()

                                allow = True

                                has_photo = bool(state_compact.get("photo_collected", False))
                                has_payment = bool(state_compact.get("paiement_collected", False))

                                purchase_markers = [
                                    "commander",
                                    "acheter",
                                    "passer commande",
                                    "passe commande",
                                    "je prends",
                                    "je veux commander",
                                ]
                                orig_has_purchase = any(m in original_lower for m in purchase_markers)
                                hyde_has_purchase = any(m in hq_lower for m in purchase_markers)
                                if hyde_has_purchase and (not orig_has_purchase) and (not has_photo) and (not has_payment):
                                    allow = False

                                if ("couch" in original_lower or "lait" in original_lower) and not (
                                    ("couch" in hq_lower) or ("lait" in hq_lower)
                                ):
                                    allow = False

                                import re as _re
                                orig_digits = _re.findall(r"\d{6,}", original_text)
                                if orig_digits and not any(d in hq for d in orig_digits):
                                    allow = False

                                if ("où" in original_lower or "sit" in original_lower) and (
                                    "adresse" in hq_lower and ("vous" not in hq_lower)
                                ):
                                    allow = False

                                # Reroute embeddings sur la reformulation HYDE, sans HYDE_PRE (évite boucle LLM)
                                try:
                                    if allow:
                                        reroute = await route_botlive_intent(
                                            company_id=active_company_id,
                                            user_id=user_id,
                                            message=hq,
                                            conversation_history=conversation_history or "",
                                            state_compact=state_compact,
                                            hyde_pre_enabled=False,
                                        )

                                        base_conf = float(routing.confidence or 0.0)
                                        new_conf = float(reroute.confidence or 0.0)
                                        base_intent = str(routing.intent or "").upper()
                                        new_intent = str(reroute.intent or "").upper()

                                        accept = True
                                        if new_intent != base_intent and new_conf < base_conf + 0.05:
                                            accept = False
                                        if new_conf < base_conf - 0.02:
                                            accept = False

                                        # Exception: sur requêtes très courtes (OK) on accepte la reformulation HYDE
                                        # si elle clarifie vers le champ manquant TEL/CONTACT.
                                        try:
                                            missing = [str(x or "").lower() for x in (routing.missing_fields or [])]
                                            wants_contact = any(k in hq_lower for k in ["numéro", "numero", "whatsapp", "contact", "téléphone", "telephone"])
                                            if force_hyde_short and wants_contact and ("tel" in missing):
                                                accept = True
                                                reroute.intent = "ACQUISITION"  # type: ignore[attr-defined]
                                                reroute.mode = "ACQUISITION"  # type: ignore[attr-defined]
                                                new_intent = "ACQUISITION"
                                                new_conf = max(new_conf, 0.95)
                                        except Exception:
                                            pass

                                        if accept:
                                            hyde_result["intent"] = reroute.intent
                                            hyde_result["confidence"] = new_conf
                                            hyde_result["mode"] = reroute.mode
                                            hyde_result["missing_fields"] = reroute.missing_fields

                                            logger.info(
                                                " [HYDE_X] Reroute accepté: %s(%.3f) -> %s(%.3f) | q=%s",
                                                base_intent,
                                                base_conf,
                                                new_intent,
                                                new_conf,
                                                hq[:120],
                                            )
                                        else:
                                            logger.info(
                                                " [HYDE_X] Reroute refusé: %s(%.3f) -> %s(%.3f) | q=%s",
                                                base_intent,
                                                base_conf,
                                                new_intent,
                                                new_conf,
                                                hq[:120],
                                            )
                                    else:
                                        logger.info(" [HYDE_X] Reformulation refusée (garde-fou) | q=%s", hq[:120])
                                except Exception as reroute_e:
                                    logger.warning(" [HYDE_X] Erreur reroute embeddings post-HYDE: %s", reroute_e)

                            # Attacher au router_metrics pour logs JSON
                            if isinstance(router_metrics, dict):
                                router_metrics["hyde_json"] = hyde_payload
                                router_metrics["hyde_raw"] = hyde_raw

                            # Recalculer le segment Jessica avec le routage raffiné
                            segment = build_jessica_prompt_segment(
                                base_prompt_template=base_prompt_template,
                                hyde_result=hyde_result,
                                question_with_context=question_with_delivery,
                                conversation_history=truncated_history,
                                resume_faits_saillants=resume_faits_saillants,
                                detected_objects_str=detected_objects_str,
                                filtered_transactions_str=compact_transactions or "0F",
                                expected_deposit_str=expected_deposit_str,
                                enriched_checklist="",
                                routing=routing,
                                delai_message=context.get("delai_message", ""),
                            )
                            # Recalculer metadata prompt après reroute
                            try:
                                prompt_segment_letter = str(segment.get("segment_letter") or "").strip().upper()
                                prompt_gating_path = str(segment.get("gating_path") or "").strip().lower()
                                used_light = bool(segment.get("used_light"))
                                used_prompt_x = bool(segment.get("used_prompt_x"))
                                if used_prompt_x:
                                    prompt_used_key = "JESSICA_PROMPT_X"
                                elif prompt_segment_letter == "U":
                                    prompt_used_key = "JESSICA_PROMPT_LIGHT_UNIQUE" if used_light else "JESSICA_PROMPT_UNIQUE"
                                elif used_light and prompt_segment_letter:
                                    prompt_used_key = f"JESSICA_PROMPT_LIGHT_{prompt_segment_letter}"
                                elif prompt_segment_letter:
                                    prompt_used_key = f"JESSICA_PROMPT_{prompt_segment_letter}"
                                else:
                                    prompt_used_key = "JESSICA_PROMPT_UNKNOWN"
                            except Exception:
                                pass

                    except Exception as hyde_e:
                        logger.error(
                            " [HYDE_X] Erreur exe9cution HYDE SECOUR X: %s",
                            hyde_e,
                        )

                prompt = segment.get('prompt', '')
                prompt_base = prompt

                try:
                    company_container = get_company_catalog_v2_container(active_company_id)
                except Exception:
                    company_container = None

                try:
                    botlive_disable_catalogue_injection = (os.getenv("BOTLIVE_DISABLE_CATALOGUE_INJECTION", "false") or "").strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "y",
                        "on",
                    }
                except Exception:
                    botlive_disable_catalogue_injection = False

                try:
                    botlive_disable_product_matching = (os.getenv("BOTLIVE_DISABLE_PRODUCT_MATCHING", "false") or "").strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "y",
                        "on",
                    }
                except Exception:
                    botlive_disable_product_matching = False

                try:
                    botlive_disable_second_pass = (os.getenv("BOTLIVE_DISABLE_SECOND_PASS", "false") or "").strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "y",
                        "on",
                    }
                except Exception:
                    botlive_disable_second_pass = False

                if isinstance(company_container, dict):
                    try:
                        product_index_block, products_by_id = self._build_light_product_index(company_container)
                    except Exception:
                        product_index_block, products_by_id = "", {}

                if products_by_id and (not botlive_disable_product_matching):
                    try:
                        selected_product_id = self._pick_product_id_strict(message or "", products_by_id)
                    except Exception:
                        selected_product_id = ""

                # Fallback (critical): if there is only one product in the catalog, always select it.
                # This guarantees catalogue markers are injected even on generic queries like "je veux des couches".
                if (not selected_product_id) and isinstance(products_by_id, dict) and len(products_by_id) == 1:
                    try:
                        selected_product_id = next(iter(products_by_id.keys()))
                    except Exception:
                        selected_product_id = ""

                if selected_product_id:
                    try:
                        if isinstance(context, dict):
                            context["selected_product_id"] = str(selected_product_id)
                            context["detected_product_id"] = str(selected_product_id)
                    except Exception:
                        pass
                    try:
                        logger.info("🎯 [PRODUCT_MATCH] stage=pre_llm detected_product_id=%s", str(selected_product_id))
                    except Exception:
                        pass

                if selected_product_id and selected_product_id in products_by_id:
                    try:
                        selected_mono_catalog = products_by_id[selected_product_id].get("catalog_v2")
                    except Exception:
                        selected_mono_catalog = None

                if product_index_block:
                    try:
                        hide_pid = selected_product_id if selected_product_id else ""
                        if hide_pid:
                            product_index_block2, _ = self._build_light_product_index(company_container, hide_variants_for_product_id=hide_pid)  # type: ignore[arg-type]
                            if product_index_block2:
                                product_index_block = product_index_block2
                    except Exception:
                        pass
                    if not botlive_disable_catalogue_injection:
                        prompt = self._inject_product_index(prompt, product_index_block)

                if selected_mono_catalog is not None:
                    try:
                        full_block = self._build_full_catalogue_block(selected_mono_catalog)
                        if not botlive_disable_catalogue_injection:
                            prompt = self._inject_catalogue_markers(prompt, full_block)
                    except Exception:
                        pass

                if not prompt or len(prompt) < 100:
                    raise ValueError(
                        f" Prompt Jessica invalide ou vide: {len(prompt) if prompt else 0} chars"
                    )

                timings["prompt_generation"] = (
                    datetime.now() - step_start
                ).total_seconds()

                logger.info(
                    " [BOTLIVE] Prompt Jessica construit: %s caracte8res",
                    len(prompt),
                )

            except Exception as prompt_error:
                import traceback

                print(f"\n{'='*80}")
                print(f" [ERREUR PROMPT JESSICA]")
                print(f"{'='*80}")
                print(f"Company ID: {active_company_id}")
                print(f"LLM Choice: {llm_choice}")
                print(f"Erreur: {prompt_error}")
                print(f"Type: {type(prompt_error).__name__}")
                print(f"\nTraceback complet:")
                traceback.print_exc()
                print(f"{'='*80}\n")
                logger.error(
                    f" Erreur construction prompt Jessica: {prompt_error}",
                    exc_info=True,
                )
                raise

            # ═══════════════════════════════════════════════════════════════
            # 🌸 LOG PROMPT BOTLIVE (SEGMENT JESSICA EFFECTIF, VERSION RÉSUMÉE)
            # ═══════════════════════════════════════════════════════════════
            MAGENTA = '\033[95m'
            BOLD = '\033[1m'
            RESET = '\033[0m'
            safe_prompt = prompt or ""
            first_line = safe_prompt.splitlines()[0] if safe_prompt else ""
            logger.info(f"{MAGENTA}{BOLD}[BOTLIVE_PROMPT] LLM={llm_choice.upper()} len={len(safe_prompt)} chars (~{len(safe_prompt)//4} tokens){RESET}")
            if first_line:
                logger.info(f"{MAGENTA}[BOTLIVE_PROMPT_FIRST_LINE] {first_line[:200]}{RESET}")

            try:
                log_full_prompt = (os.getenv("BOTLIVE_LOG_FULL_PROMPT", "false") or "").strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "y",
                    "on",
                }
            except Exception:
                log_full_prompt = False

            if log_full_prompt and safe_prompt:
                try:
                    logger.info(f"{MAGENTA}[BOTLIVE_PROMPT_FULL_START]{RESET}\n{safe_prompt}\n{MAGENTA}[BOTLIVE_PROMPT_FULL_END]{RESET}")
                except Exception:
                    pass
            
            # ═══ ÉTAPE 3: APPEL LLM ═══
            step_start = datetime.now()
            if llm_choice == "openrouter":
                # Mode prompt UNIQUE: on utilise le modèle OpenRouter par défaut (env OPENROUTER_BOTLIVE_MODEL / LLM_MODEL)
                response_data = await self._call_openrouter(
                    prompt,
                    user_id,
                    model_name=None,
                    segment_letter=prompt_segment_letter,
                )
            else:
                logger.info(
                    "🧭 [BOTLIVE][LLM_CALL] selected_llm=groq-70b reason="
                    f"{routing_reason} openrouter_key_present={bool((os.getenv('OPENROUTER_API_KEY') or '').strip())}"
                )
                response_data = await self._call_groq(prompt, user_id)
            self.stats['primary_llm_requests'] += 1
            timings['llm_call'] = (datetime.now() - step_start).total_seconds()
            
            # ═══ ÉTAPE 4: VALIDATION RÉPONSE ═══
            if not self._is_valid_response(response_data, llm_choice):
                # Fallback possible (à activer si on ajoute un deuxième LLM)
                logger.warning(f"🔄 [BOTLIVE] Réponse LLM jugée invalide pour {user_id}, pas de second LLM configuré (Groq 70B unique)")
                self.router.record_failure(user_id, llm_choice)
                self.stats['fallbacks'] += 1

            # Strict format enforcement (OpenRouter):
            # If model didn't follow <response>...</response> (and didn't output TRANSMISSIONXXX), retry once
            # with an explicit constraint to avoid leaking internal analysis / prompt echo.
            try:
                if llm_choice == "openrouter":
                    token = (LLM_TRANSMISSION_TOKEN or "TRANSMISSIONXXX").strip()
                    raw0 = str(response_data.get("response") or "")
                    raw0_lc = raw0.lower()
                    has_open_response = "<response>" in raw0_lc
                    has_close_response = "</response>" in raw0_lc
                    has_response_tag = has_open_response and has_close_response
                    has_token = bool(token) and token.lower() in raw0_lc

                    if raw0 and (not has_token) and (not has_response_tag):
                        repaired = None
                        try:
                            if has_open_response and (not has_close_response):
                                repaired = raw0 + "</response>"
                            elif not has_open_response:
                                candidate = raw0.strip()
                                if candidate and "</thinking>" in raw0_lc:
                                    after_thinking = regex.search(r"</thinking>(.*)$", raw0, regex.DOTALL | regex.IGNORECASE)
                                    if after_thinking:
                                        candidate = after_thinking.group(1).strip()
                                if candidate:
                                    repaired = f"<response>{candidate}</response>"
                        except Exception:
                            repaired = None

                        if repaired:
                            repaired_lc = repaired.lower()
                            if "<response>" in repaired_lc and "</response>" in repaired_lc:
                                response_data = {**response_data, "response": repaired}
                                raw0 = repaired
                                raw0_lc = repaired_lc
                                has_open_response = True
                                has_close_response = True
                                has_response_tag = True

                    strict_retry_enabled = (os.getenv("BOTLIVE_STRICT_RESPONSE_RETRY", "true") or "").strip().lower() in {
                        "true",
                        "1",
                        "yes",
                        "y",
                        "on",
                    }
                    if strict_retry_enabled and raw0 and (not has_response_tag) and (not has_token):
                        retry_suffix = (
                            "\n\nIMPORTANT (STRICT OUTPUT):\n"
                            "- If handoff is required: output ONLY 'TRANSMISSIONXXX' (no tags, no extra text).\n"
                            "- Otherwise output ONLY: <response>...</response>\n"
                            "- Do NOT output analysis, do NOT repeat the prompt."
                        )
                        retry_prompt = f"{prompt}\n\n{retry_suffix}"

                        step_retry = datetime.now()
                        response_data_retry = await self._call_openrouter(
                            retry_prompt,
                            user_id,
                            model_name=None,
                            segment_letter=prompt_segment_letter,
                        )
                        timings["llm_call_retry"] = (datetime.now() - step_retry).total_seconds()

                        raw1 = str(response_data_retry.get("response") or "")
                        raw1_lc = raw1.lower()
                        has_response_tag_1 = "<response>" in raw1_lc and "</response>" in raw1_lc
                        has_token_1 = bool(token) and token.lower() in raw1_lc
                        if has_response_tag_1 or has_token_1:
                            response_data = response_data_retry
            except Exception:
                pass
            
            # ═══ ÉTAPE 5: EXTRACTION THINKING/RESPONSE ═══
            step_start = datetime.now()
            raw_response = response_data.get('response', '')
            thinking = response_data.get('thinking', '')
            final_response = raw_response

            # Extraire thinking et response si format structuré
            meta_match = None
            meta_tag = None
            if raw_response and "<meta>" in raw_response.lower():
                meta_match = regex.search(r'<meta>(.*?)</meta>', raw_response, regex.DOTALL | regex.IGNORECASE)
                if meta_match:
                    meta_tag = "meta"
            if not meta_match and raw_response and "<thinking>" in raw_response.lower():
                meta_match = regex.search(r'<thinking>(.*?)(</thinking>|$)', raw_response, regex.DOTALL | regex.IGNORECASE)
                if meta_match:
                    meta_tag = "thinking"

            response_match = None
            if raw_response and "<response>" in raw_response.lower():
                response_match = regex.search(r'<response>(.*?)(</response>|$)', raw_response, regex.DOTALL | regex.IGNORECASE)

            if meta_match:
                thinking = meta_match.group(1).strip()
                if meta_tag == "thinking":
                    execute_tools_in_response(thinking, user_id)
                    logger.debug(f"🧠 [THINKING] Outils exécutés pour {user_id}")

            # Extraction silencieuse de détails produit (sans valider PHOTO/produit)
            try:
                from core.thinking_parser import get_thinking_parser
                from core.order_state_tracker import order_tracker

                tp = get_thinking_parser()
                extracted_details = tp.extract_extracted_details(thinking or "")
                if extracted_details:
                    order_tracker.update_produit_details(user_id, extracted_details)
            except Exception:
                pass

            extracted_response = None
            if response_match:
                extracted_response = response_match.group(1).strip()

            # Si pas de <response>, tenter de prendre le texte après </thinking>
            if not extracted_response and raw_response and "</thinking>" in raw_response.lower():
                try:
                    after_thinking = regex.search(r'</thinking>(.*)$', raw_response, regex.DOTALL | regex.IGNORECASE)
                    if after_thinking:
                        extracted_response = (after_thinking.group(1) or "").strip()
                except Exception:
                    pass

            # Fallback: nettoyer les tags connus (y compris <thinking> non fermé)
            if not extracted_response:
                cleaned = raw_response or ""
                cleaned = regex.sub(r'<meta>.*?</meta>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                cleaned = regex.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                cleaned = regex.sub(r'<thinking>.*$', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                cleaned = regex.sub(r'</?response>', '', cleaned, flags=regex.IGNORECASE)
                cleaned = cleaned.strip()
                extracted_response = cleaned

            if not extracted_response:
                extracted_response = "Désolé, je n'ai pas pu traiter votre message. Pouvez-vous réessayer s'il vous plaît ?"

            final_response = extracted_response

            did_second_pass = False
            try:
                if (not botlive_disable_second_pass) and (not selected_product_id) and (not did_second_pass) and thinking and products_by_id and isinstance(company_container, dict):
                    inferred_pid = self._extract_product_id_from_text(thinking, products_by_id)
                    if inferred_pid and inferred_pid in products_by_id:
                        inferred_cat = products_by_id[inferred_pid].get("catalog_v2")
                        if isinstance(inferred_cat, dict):
                            try:
                                idx2, _ = self._build_light_product_index(company_container, hide_variants_for_product_id=inferred_pid)
                            except Exception:
                                idx2 = ""
                            try:
                                prompt2 = prompt_base
                            except Exception:
                                prompt2 = prompt
                            if idx2:
                                prompt2 = self._inject_product_index(prompt2, idx2)
                            full_block2 = self._build_full_catalogue_block(inferred_cat)
                            prompt2 = self._inject_catalogue_markers(prompt2, full_block2)

                            step_retry2 = datetime.now()
                            if llm_choice == "openrouter":
                                response_data2 = await self._call_openrouter(
                                    prompt2,
                                    user_id,
                                    model_name=None,
                                    segment_letter=prompt_segment_letter,
                                )
                            else:
                                response_data2 = await self._call_groq(prompt2, user_id)
                            timings["llm_call_pass2"] = (datetime.now() - step_retry2).total_seconds()

                            raw_response2 = response_data2.get('response', '')
                            thinking2 = response_data2.get('thinking', '')

                            meta_match2 = None
                            if raw_response2 and "<meta>" in raw_response2.lower():
                                meta_match2 = regex.search(r'<meta>(.*?)</meta>', raw_response2, regex.DOTALL | regex.IGNORECASE)
                            if not meta_match2 and raw_response2 and "<thinking>" in raw_response2.lower():
                                meta_match2 = regex.search(r'<thinking>(.*?)(</thinking>|$)', raw_response2, regex.DOTALL | regex.IGNORECASE)
                            if meta_match2:
                                thinking2 = meta_match2.group(1).strip()

                            response_match2 = None
                            if raw_response2 and "<response>" in raw_response2.lower():
                                response_match2 = regex.search(r'<response>(.*?)(</response>|$)', raw_response2, regex.DOTALL | regex.IGNORECASE)
                            extracted_response2 = None
                            if response_match2:
                                extracted_response2 = response_match2.group(1).strip()
                            if not extracted_response2 and raw_response2 and "</thinking>" in raw_response2.lower():
                                after_thinking2 = regex.search(r'</thinking>(.*)$', raw_response2, regex.DOTALL | regex.IGNORECASE)
                                if after_thinking2:
                                    extracted_response2 = (after_thinking2.group(1) or "").strip()
                            if not extracted_response2:
                                cleaned2 = raw_response2 or ""
                                cleaned2 = regex.sub(r'<meta>.*?</meta>', '', cleaned2, flags=regex.DOTALL | regex.IGNORECASE)
                                cleaned2 = regex.sub(r'<thinking>.*?</thinking>', '', cleaned2, flags=regex.DOTALL | regex.IGNORECASE)
                                cleaned2 = regex.sub(r'<thinking>.*$', '', cleaned2, flags=regex.DOTALL | regex.IGNORECASE)
                                cleaned2 = regex.sub(r'</?response>', '', cleaned2, flags=regex.IGNORECASE)
                                cleaned2 = cleaned2.strip()
                                extracted_response2 = cleaned2

                            if extracted_response2:
                                final_response = extracted_response2
                                thinking = thinking2
                                response_data = response_data2
                                did_second_pass = True
            except Exception:
                did_second_pass = did_second_pass

            try:
                if BOTLIVE_COOPERATIVE_HUMAN_MODE:
                    token = (LLM_TRANSMISSION_TOKEN or "TRANSMISSIONXXX").strip()
                    if token and token.lower() in (final_response or "").lower():
                        if isinstance(router_metrics, dict):
                            router_metrics["cooperative_mode"] = True
                            router_metrics["human_required"] = True
                            router_metrics["bypass_llm"] = True
                            router_metrics["handoff_reason"] = "llm_transmission_token"
                            router_metrics["transmission_token"] = token
                        end_time = datetime.now()
                        processing_time = (end_time - start_time).total_seconds()
                        return {
                            "response": None,
                            "status": "PENDING_HUMAN",
                            "human_required": True,
                            "bypass_llm": True,
                            "routing_reason": "cooperative_llm_transmission_token",
                            "processing_time": processing_time,
                            "timings": timings,
                            "router_metrics": {
                                **(router_metrics or {}),
                                "prompt_used_key": (prompt_used_key or ""),
                                "prompt_expected_key": (prompt_expected_key or ""),
                                "prompt_ok": prompt_ok,
                                "gating_path": (prompt_gating_path or ""),
                                "segment_letter": (prompt_segment_letter or ""),
                            },
                            "tools_executed": False,
                            "prompt_tokens": response_data.get("prompt_tokens", 0),
                            "completion_tokens": response_data.get("completion_tokens", 0),
                            "total_cost": response_data.get("total_cost", 0),
                            "success": True,
                        }
            except Exception:
                pass
            
            # ═══ ÉTAPE 6: VALIDATION ANTI-HALLUCINATION ═══
            validation_enabled = os.getenv("BOTLIVE_VALIDATION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
            validation_result = None
            if validation_enabled:
                from core.llm_response_validator import validator as llm_validator
                from core.order_state_tracker import order_tracker
                
                validation_result = llm_validator.validate(
                    response=final_response,
                    thinking=thinking,
                    order_state=order_tracker.get_state(user_id),
                    payment_validation=payment_validation,
                    context_documents=[context.get('context_used', '')]
                )
                
                # Si hallucination détectée, régénérer (DEBUG uniquement)
                if validation_result.should_regenerate:
                    logger.warning(f"🚨 [HALLUCINATION] Régénération requise pour {user_id}")
                    logger.warning(f"   Erreurs: {validation_result.errors}")
                    
                    # Régénérer avec prompt corrigé
                    corrected_prompt = prompt + "\n\n" + validation_result.correction_prompt
                    
                    logger.info(f"🔄 [REGENERATION] Appel LLM avec correction...")
                    # Botlive : toujours Groq 70B pour la régénération
                    response_data = await self._call_groq(corrected_prompt, user_id)
                    
                    # Extraire nouvelle réponse
                    raw_response = response_data.get('response', '')

                    meta_match = regex.search(r'<meta>(.*?)</meta>', raw_response, regex.DOTALL | regex.IGNORECASE)
                    if meta_match:
                        thinking = meta_match.group(1).strip()
                    else:
                        thinking_match = regex.search(r'<thinking>(.*?)</thinking>', raw_response, regex.DOTALL | regex.IGNORECASE)
                        if thinking_match:
                            thinking = thinking_match.group(1).strip()

                    extracted_response = None
                    response_match = regex.search(r'<response>(.*?)(</response>|$)', raw_response, regex.DOTALL | regex.IGNORECASE)
                    if response_match:
                        extracted_response = response_match.group(1).strip()

                    if not extracted_response and raw_response and "</thinking>" in raw_response.lower():
                        try:
                            after_thinking = regex.search(r'</thinking>(.*)$', raw_response, regex.DOTALL | regex.IGNORECASE)
                            if after_thinking:
                                extracted_response = (after_thinking.group(1) or "").strip()
                        except Exception:
                            pass

                    if not extracted_response:
                        cleaned = raw_response or ""
                        cleaned = regex.sub(r'<meta>.*?</meta>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                        cleaned = regex.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                        cleaned = regex.sub(r'<thinking>.*$', '', cleaned, flags=regex.DOTALL | regex.IGNORECASE)
                        cleaned = regex.sub(r'</?response>', '', cleaned, flags=regex.IGNORECASE)
                        cleaned = cleaned.strip()
                        extracted_response = cleaned

                    if not extracted_response:
                        extracted_response = "Désolé, je n'ai pas pu traiter votre message. Pouvez-vous réessayer s'il vous plaît ?"

                    final_response = extracted_response
                    
                    # Valider à nouveau
                    validation_result2 = llm_validator.validate(
                        response=final_response,
                        thinking=thinking,
                        order_state=order_tracker.get_state(user_id),
                        payment_validation=payment_validation,
                        context_documents=[context.get('context_used', '')]
                    )
                    
                    if not validation_result2.valid:
                        logger.error("❌ [REGENERATION] Échec après correction, réponse conservée")
            
            # ═══ ÉTAPE 7: EXÉCUTION OUTILS ═══
            processed_response = execute_tools_in_response(final_response, user_id)
            timings['tools_execution'] = (datetime.now() - step_start).total_seconds()
            
            if processed_response != final_response:
                self.stats['tools_used'] += 1
                logger.debug(f"🧠 Outils exécutés pour {user_id}")
            
            # ═══ ÉTAPE 6.4: DÉTECTION AUTOMATIQUE ET SAUVEGARDE (OPTIMISÉE) ═══
            try:
                from core.order_state_tracker import order_tracker
                
                # Détecter et sauvegarder automatiquement les données
                vision_objects = context.get('vision_objects', [])
                detected_objects = context.get('detected_objects', [])
                message_text = context.get('message', message)  # Utiliser message du paramètre si pas dans context
                message_lower = message_text.lower() if message_text else ""
                
                # 🔍 DEBUG: Voir ce qui arrive vraiment
                logger.info(f"🔍 [AUTO-DETECT DEBUG] user_id={user_id}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] vision_objects={vision_objects}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] detected_objects={detected_objects}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] message_text={message_text[:100] if message_text else 'VIDE'}")
                logger.info(f"🔍 [AUTO-DETECT DEBUG] context.keys()={list(context.keys())}")
                
                # 1. PRODUIT détecté dans VISION (BLIP) SEULEMENT
                # ⚠️ IMPORTANT: Sans validation BLIP, on ne peut pas fiabiliser les noms de produits
                # pour des milliers d'entreprises. Seule la vision validée est acceptée.
                
                if vision_objects or detected_objects:
                    # Fusionner les deux sources
                    all_objects = vision_objects + detected_objects
                    if all_objects:
                        # Détecter le produit (tout objet non monétaire)
                        for obj in all_objects:
                            obj_text = None
                            
                            # FORMAT 1: Dict {'label': '...', 'confidence': 0.85}
                            if isinstance(obj, dict) and 'label' in obj:
                                obj_text = obj['label']
                            
                            # FORMAT 2: String "objet:lingettes~0.85"
                            elif isinstance(obj, str) and obj.startswith('objet:'):
                                # Extraire le label entre "objet:" et "~"
                                parts = obj.split('~')
                                if len(parts) > 0:
                                    obj_text = parts[0].replace('objet:', '')
                            
                            # Valider et sauvegarder (VISION BLIP SEULEMENT)
                            if obj_text:
                                obj_str = str(obj_text).lower()
                                if not regex.search(r'\d+\s*f', obj_str) and len(obj_str) > 2:
                                    produit = obj_text[:50]
                                    order_tracker.update_produit(user_id, produit)
                                    logger.info(f"📦 [AUTO-DETECT] Produit (BLIP vision): {produit}")
                                    break
                        
                # 2. PAIEMENT détecté dans TRANSACTIONS (prioritaire) ou vision
                filtered_transactions = context.get('filtered_transactions', [])
                req_amt = _required_amount_from_context(context)
                
                if filtered_transactions:
                    # Transactions OCR détectées
                    first_transaction = filtered_transactions[0]
                    try:
                        amt_val = int(first_transaction.get('amount', 0) or 0)
                    except Exception:
                        try:
                            amt_val = int(str(first_transaction.get('amount', '0')).strip())
                        except Exception:
                            amt_val = 0
                            
                    if amt_val > 0:
                        if amt_val >= req_amt:
                            montant = f"{amt_val}F[TRANSACTIONS]"
                            order_tracker.update_paiement(user_id, montant)
                            logger.info(f"💰 [AUTO-DETECT] Paiement SUFFISANT (OCR): {montant} >= {req_amt}F -> SAUVEGARDÉ")
                        else:
                            logger.info(f"💰 [AUTO-DETECT] Paiement INSUFFISANT (OCR): {amt_val}F < {req_amt}F -> NON SAUVEGARDÉ")
                else:
                    # Sinon chercher dans vision
                    for obj in vision_objects + detected_objects:
                        obj_str = str(obj).lower()
                        if 'fcfa' in obj_str or regex.search(r'\d+\s*f\b', obj_str):
                            # Extraire montant
                            montant_match = regex.search(r'(\d+)\s*f', obj_str)
                            if montant_match:
                                try:
                                    amt_val = int(montant_match.group(1) or 0)
                                except Exception:
                                    amt_val = 0
                                
                                if amt_val > 0:
                                    if amt_val >= req_amt:
                                        montant = f"{amt_val}F[VISION]"
                                        order_tracker.update_paiement(user_id, montant)
                                        logger.info(f"💰 [AUTO-DETECT] Paiement SUFFISANT (vision): {montant} >= {req_amt}F -> SAUVEGARDÉ")
                                        break
                                    else:
                                        logger.info(f"💰 [AUTO-DETECT] Paiement INSUFFISANT (vision): {amt_val}F < {req_amt}F -> NON SAUVEGARDÉ")
                
                # 3. ZONE détectée dans message
                zones = ["yopougon", "cocody", "plateau", "adjamé", "abobo", "marcory", 
                         "koumassi", "treichville", "angré", "riviera", "port-bouet", "attécoubé"]
                for zone in zones:
                    if zone in message_lower:
                        zone_formatted = f"{zone.capitalize()}"
                        order_tracker.update_zone(user_id, zone_formatted)
                        logger.info(f"📍 [AUTO-DETECT] Zone: {zone_formatted}")
                        break
                
                # 4. NUMÉRO détecté dans message (4 formats)
                numero_patterns = [
                    r'\+225\s?0?([157]\d{8})',  # +2250787360757 ou +225 0787360757
                    r'\b(0[157]\d{8})\b',        # 0787360757
                    r'\b0([157])\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\b'  # 07 87 36 07 57
                ]
                
                numero = None
                numero_raw_input = None
                for pattern in numero_patterns:
                    match = regex.search(pattern, message_text) if message_text else None
                    if match:
                        try:
                            numero_raw_input = match.group(0)
                        except Exception:
                            numero_raw_input = None
                        if len(match.groups()) == 1:
                            # Format simple
                            numero = f"0{match.group(1)}" if not match.group(1).startswith('0') else f"{match.group(1)}"
                        else:
                            # Format avec espaces
                            numero = f"0{''.join(match.groups())}"
                        break
                
                if numero:
                    order_tracker.update_numero(user_id, numero)
                    logger.info(f"📞 [AUTO-DETECT] Numéro: {numero}")
                    
            except Exception as e:
                logger.error(f"⚠️ Auto-détection échouée: {e}")

            # ═══ MÉMOIRE ÉPISODIQUE: mise à jour du résumé long-terme (Redis) ═══
            try:
                import redis as _redis

                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                r = _redis.Redis.from_url(redis_url, decode_responses=True)

                counter_key = f"botlive_summary_turn:{active_company_id}:{user_id}"
                summary_key = f"botlive_summary:{active_company_id}:{user_id}"
                ttl_seconds = int(os.getenv("BOTLIVE_SUMMARY_TTL_SECONDS", str(7 * 24 * 3600)))

                # Toujours incrémenter le compteur pour créer la clé même si l'historique est tronqué.
                turn = int(r.incr(counter_key) or 0)
                try:
                    r.expire(counter_key, ttl_seconds)
                except Exception:
                    pass
                try:
                    logger.info("🧠 [BOTLIVE][SUMMARY] turn_counter=%s key=%s", turn, counter_key)
                except Exception:
                    pass

                every_n = int(os.getenv("BOTLIVE_SUMMARY_EVERY_N", "3"))
                if every_n <= 0:
                    every_n = 3

                # Le seuil utilise le nombre de tours (plus fiable que conversation_history qui peut être tronqué)
                min_turns = int(os.getenv("BOTLIVE_SUMMARY_MIN_LINES", "10"))
                should_consider_summary = bool(turn >= min_turns)

                if should_consider_summary and (turn % every_n == 0):
                    prev_summary = str(r.get(summary_key) or "").strip()
                    user_msg = (message or "").strip()
                    assistant_msg = (processed_response or final_response or "").strip()

                    # Prompt Summarizer: factuel, pas de checklist Photo/Zone/Tel/Pay
                    summarizer_prompt = (
                        "Tu es un summarizer de conversation commerciale.\n"
                        "Tu dois produire un résumé FACTUEL et très court (max 6 lignes).\n"
                        "Tu dois résumer uniquement:\n"
                        "1) contraintes temps/lieu, 2) préférences produit, 3) objections déjà traitées.\n"
                        "INTERDICTION d'inclure les infos déjà dans la checklist (Photo/Zone/Tel/Pay).\n"
                        "INTERDICTION d'inventer.\n\n"
                        f"Résumé actuel (si vide, ignorer):\n{prev_summary}\n\n"
                        f"Dernier message client:\n{user_msg}\n\n"
                        f"Dernière réponse Jessica:\n{assistant_msg}\n\n"
                        "Retourne uniquement le nouveau résumé (texte brut)."
                    )

                    new_summary = ""
                    try:
                        # Priorité: OpenRouter (cheap/fast). Si indisponible, ne pas bloquer.
                        if (os.getenv("OPENROUTER_API_KEY") or "").strip():
                            model = os.getenv(
                                "OPENROUTER_SUMMARIZER_MODEL",
                                os.getenv("OPENROUTER_BOTLIVE_MODEL", "mistralai/mistral-small-3.2-24b-instruct"),
                            )
                            summary_data = await self._call_openrouter(
                                summarizer_prompt,
                                user_id,
                                model_name=model,
                                segment_letter="",
                            )
                            new_summary = str(summary_data.get("response") or "").strip()
                    except Exception:
                        new_summary = ""

                    if new_summary:
                        try:
                            r.setex(summary_key, ttl_seconds, new_summary)
                        except Exception:
                            pass
            except Exception:
                pass
            
            # ═══ ÉTAPE 6.45: PYTHON DIRECT (court-circuit si déclencheur actif) ═══
            try:
                if ENABLE_PYTHON_DIRECT:
                    from core.order_state_tracker import order_tracker as _ot
                    state_after = _ot.get_state(user_id)
                    trigger = self._build_loop_trigger(state_before, state_after, context, message)
                    if trigger:
                        loop_state = self._build_loop_state(state_after, context)
                        engine = get_loop_engine()
                        python_resp = engine._python_auto_response(trigger, loop_state, message)
                        if python_resp and python_resp != "llm_takeover":
                            self._record_python_verdict(context, trigger, python_resp)
                            if isinstance(router_metrics, dict):
                                router_metrics["python_direct"] = True
            except Exception as e:
                logger.debug(f"⚠️ [PYTHON_DIRECT] Ignoré (erreur non bloquante): {e}")
            
            # ═══ ÉTAPE 6.5: FINALISATION FORCÉE SI COMMANDE COMPLÈTE (TRANSITION) ═══
            try:
                from core.order_state_tracker import order_tracker
                state_after = order_tracker.get_state(user_id)

                became_complete = bool(state_after.is_complete()) and not bool(state_was_complete)

                if became_complete and not python_short_circuit:
                    montant = 2000
                    try:
                        paiement_str = getattr(state_after, "paiement", "") or ""
                        m = regex.search(r"(\d+)", str(paiement_str))
                        montant = int(m.group(1)) if m else montant
                    except Exception:
                        pass

                    try:
                        delai = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                    except Exception:
                        from datetime import datetime as _dt
                        heure_actuelle = _dt.now().hour
                        delai = "aujourd'hui" if heure_actuelle < 13 else "demain"

                    processed_response = (
                        f"✅PARFAIT Commande confirmée 😊\n"
                        f"Livraison prévue {delai}, acompte de {montant} F déjà versé.\n"
                        "Nous vous rappellerons bientôt pour les détails et le coût total.\n"
                        "Veuillez ne pas répondre à ce message."
                    )
                    logger.info(
                        f"✅ [FINALISATION AUTO] Commande complétée sur ce tour pour {user_id} "
                        f"(montant={montant}, delai={delai})"
                    )
            except Exception as e:
                logger.debug(f"⚠️ Vérification finalisation échouée: {e}")
            
            # ═══ ÉTAPE 6.6: NETTOYAGE TRACES TECHNIQUES ═══
            processed_response = self._clean_response(processed_response)

            # ═══ ÉTAPE 6.7: CHECKLIST SYSTEM STATE (ANTI-HALLUCINATION) ═══
            try:
                # IMPORTANT: Le validator checklist dépend de verdict_global + order_state.
                # Si ces champs ne sont pas présents dans context, extract_system_state_dict() retombe sur
                # NEXT=COLLECT_PHOTO par défaut et peut réécrire une réponse LLM pourtant correcte.
                try:
                    from core.order_state_tracker import order_tracker
                    if isinstance(context, dict):
                        context["order_state"] = order_tracker.get_state(user_id)
                        # Construire/rafraîchir verdict_global en cohérence avec l'état et le message courant
                        self._build_canonical_verdict(context)
                except Exception:
                    pass

                if isinstance(context, dict):
                    context["checklist_system_state"] = build_system_state_check(context)

                system_state_dict = extract_system_state_dict(context if isinstance(context, dict) else {})
                validated = validate_llm_response_checklist(
                    processed_response,
                    system_state_dict,
                    context if isinstance(context, dict) else None,
                )
                if validated != processed_response:
                    logger.warning(
                        "🛡️ [CHECKLIST_VALIDATION] Réponse réécrite (user_id=%s next=%s)",
                        user_id,
                        system_state_dict.get("next_step"),
                    )
                    try:
                        if isinstance(router_metrics, dict) and isinstance(context, dict):
                            router_metrics["checklist_rewrite"] = True
                            router_metrics["checklist_rewrite_reason"] = str(context.get("checklist_rewrite_reason") or "")
                    except Exception:
                        pass
                    processed_response = validated
            except Exception as e:
                logger.debug("⚠️ [CHECKLIST_VALIDATION] Ignoré (erreur non bloquante): %s", e)
            
            # ═══ ÉTAPE 7: ENREGISTREMENT SUCCÈS ═══
            self.router.record_success(user_id, llm_choice)
            
            # ═══ ÉTAPE 8: CONSTRUCTION RÉPONSE FINALE ═══
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self.stats['total_requests'] += 1
            
            try:
                _pt = int(response_data.get('prompt_tokens', 0) or 0)
                _ct = int(response_data.get('completion_tokens', 0) or 0)
                _tt = int(response_data.get('total_tokens', _pt + _ct) or 0)
            except Exception:
                _pt = int(response_data.get('prompt_tokens', 0) or 0)
                _ct = int(response_data.get('completion_tokens', 0) or 0)
                _tt = _pt + _ct

            _usage = response_data.get('usage') if isinstance(response_data, dict) else None
            if not isinstance(_usage, dict):
                _usage = {}

            return {
                'response': processed_response,
                'thinking': "" if python_short_circuit else thinking,
                'llm_used': 'python' if python_short_circuit else llm_choice,
                'llm_raw': "" if python_short_circuit else (raw_response or ""),
                'usage': {} if python_short_circuit else _usage,
                'validation': {  # ← NOUVEAU: Résultats validation
                    'valid': validation_result.valid if validation_result is not None else None,
                    'errors': validation_result.errors if validation_result is not None else None,
                    'warnings': validation_result.warnings if validation_result is not None else None,
                    'should_regenerate': validation_result.should_regenerate if validation_result is not None else None
                },
                'routing_reason': routing_reason,
                'processing_time': processing_time,
                'timings': timings,
                'router_metrics': {
                    **(router_metrics or {}),
                    'prompt_used_key': ("PYTHON_SHORT_CIRCUIT" if python_short_circuit else (prompt_used_key or "")),
                    'prompt_expected_key': ("PYTHON_SHORT_CIRCUIT" if python_short_circuit else (prompt_expected_key or "")),
                    'prompt_ok': (True if python_short_circuit else prompt_ok),
                    'gating_path': ("python" if python_short_circuit else (prompt_gating_path or "")),
                    'segment_letter': ("" if python_short_circuit else (prompt_segment_letter or "")),
                },
                'tools_executed': processed_response != final_response,
                'prompt_tokens': _pt,
                'completion_tokens': _ct,
                'total_tokens': _tt,
                'total_cost': response_data.get('total_cost', 0),
                'cost': response_data.get('total_cost', 0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement requête {user_id}: {e}")
            # Réponse d'erreur plus humaine et légèrement variée
            import random

            error_messages = [
                "D\u00e9sol\u00e9, erreur technique. R\u00e9essayez s'il vous pla\u00eet.",
                "Un souci technique est survenu. Pouvez-vous reformuler ?",
                "Oups, petit probl\u00e8me de connexion. Essayons \u00e0 nouveau.",
                "Erreur temporaire. Retentons ensemble dans un instant.",
            ]

            friendly_error = random.choice(error_messages)

            return {
                'response': friendly_error,
                'thinking': '',
                'llm_used': 'error',
                'routing_reason': f'Erreur: {str(e)}',
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'tools_executed': False,
                'success': False
            }
    
    def _clean_response(self, response: str) -> str:
        """
        Nettoie la réponse pour enlever toute trace technique
        (notepad, calculator, etc.)
        
        Args:
            response: Réponse brute du LLM
        
        Returns:
            str: Réponse nettoyée
        """
        # Supprimer notepad(...) et contenu associé
        response = regex.sub(r"notepad\([^)]*\)\s*puis\s*[^\s]+", "", response)
        response = regex.sub(r"notepad\([^)]*\)", "", response)
        response = regex.sub(r"calculator\([^)]*\)", "", response)
        # Supprimer traces ✅CHAMP:valeur[SOURCE]
        response = regex.sub(r"✅\w+:[^\s\|]+\[\w+\]", "", response)
        # Supprimer blocs XML internes (<thinking>, <response>, <answer>)
        response = regex.sub(
            r"<thinking>.*?</thinking>", "", response, flags=regex.DOTALL | regex.IGNORECASE
        )
        response = regex.sub(
            r"<meta>.*?</meta>", "", response, flags=regex.DOTALL | regex.IGNORECASE
        )
        response = regex.sub(r"</?response>", "", response, flags=regex.IGNORECASE)
        response = regex.sub(r"</?answer>", "", response, flags=regex.IGNORECASE)
        # Nettoyer espaces multiples
        response = regex.sub(r"\s{2,}", " ", response).strip()
        return response

    async def _process_images(self, images: list, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper vision: utilise Zeta_AI.app._process_botlive_vision pour chaque image.
        Normalise les clés pour correspondre au format attendu par le moteur (name/confidence).
        """
        result: Dict[str, Any] = {'detected_objects': [], 'filtered_transactions': []}
        if not images:
            return result
        # Import local pour éviter hard dependency si module absent
        try:
            from Zeta_AI.app import _process_botlive_vision
        except Exception as e:
            logger.debug(f"[VISION_WRAPPER] Module indisponible: {e}")
            return result

        company_phone = context.get('company_phone')
        for img in images:
            try:
                vision = await _process_botlive_vision(img, company_phone=company_phone)
                if not isinstance(vision, dict):
                    continue
                # Normaliser objets détectés
                objs = []
                for o in vision.get('detected_objects', []) or []:
                    if isinstance(o, dict):
                        name = o.get('name') or o.get('label') or o.get('type') or 'Produit détecté'
                        conf = o.get('confidence', 0)
                        try:
                            conf = float(conf)
                        except Exception:
                            conf = 0.0
                        objs.append({'name': name, 'confidence': conf})
                    else:
                        objs.append({'name': str(o), 'confidence': 0.0})
                if objs:
                    result['detected_objects'].extend(objs)

                # Transactions OCR filtrées
                txs = vision.get('filtered_transactions', [])
                if isinstance(txs, list) and txs:
                    result['filtered_transactions'].extend(txs)
            except Exception as e:
                logger.debug(f"[VISION_WRAPPER] Erreur traitement image: {e}")
                continue
        return result

    async def _call_deepseek(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """Appel API DeepSeek V3 (actuellement proxifié via Groq 70B)."""
        try:
            # Import du bon module Groq
            from core.llm_client_groq import complete

            logger.debug(f"📡 Appel DeepSeek V3 pour {user_id}")

            # Pour l'instant, utiliser Groq en attendant l'API DeepSeek
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.3-70b-versatile",  # Temporaire
                max_tokens=500,
                temperature=0.1,
            )

            prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
            completion_tokens = int(token_info.get("completion_tokens", 0) or 0)
            total_tokens = int(
                token_info.get("total_tokens", prompt_tokens + completion_tokens) or 0
            )
            cost = self._calculate_groq_cost(token_info)
            model = token_info.get("model", "llama-3.3-70b-versatile")

            try:
                log3("[LLM]", f"Groq {model} (via DeepSeek) | {len(prompt)} chars")
                cached_tokens = 0
                try:
                    cached_tokens = int(
                        usage.get("cached_tokens")
                        or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                        or 0
                    )
                except Exception:
                    cached_tokens = 0
                token_msg = f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens (cost=${cost:.6f})"
                if cached_tokens:
                    token_msg = f"{token_msg} | cached_prompt_tokens={cached_tokens}"
                log3("[LLM][TOKENS]", token_msg)
                log3("[LLM][RAW]", content, max_lines=40, max_length=4000)
            except Exception:
                pass

            return {
                "response": content,
                "thinking": "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": cost,
                # On conserve le label logique DeepSeek côté métriques
                "model": "deepseek-chat",
            }
        except Exception as e:
            logger.error(f"❌ Erreur DeepSeek API: {e}")
            raise

    async def _call_openrouter(
        self,
        prompt: str,
        user_id: str,
        model_name: Optional[str] = None,
        segment_letter: str = "",
    ) -> Dict[str, Any]:
        try:
            from core.llm_client_openrouter import complete

            if not model_name:
                model_name = os.getenv(
                    "OPENROUTER_BOTLIVE_MODEL",
                    os.getenv("LLM_MODEL", "mistralai/mistral-small-3.2-24b-instruct"),
                )

            seg = (segment_letter or "").strip().upper()
            try:
                max_tokens_default = int(os.getenv("BOTLIVE_MAX_TOKENS", "900"))
            except Exception:
                max_tokens_default = 900
            if seg == "A":
                max_tokens = max_tokens_default
                temperature = 0.55
                top_p = 0.9
                frequency_penalty = 0.2
            elif seg == "B":
                max_tokens = max_tokens_default
                temperature = 0.4
                top_p = 0.9
                frequency_penalty = 0.0
            elif seg == "C":
                max_tokens = max_tokens_default
                temperature = 0.07
                top_p = 0.9
                frequency_penalty = 0.15
            else:
                max_tokens = max_tokens_default
                temperature = float(os.getenv("BOTLIVE_TEMPERATURE", "0.3"))
                top_p = float(os.getenv("BOTLIVE_TOP_P", "0.9"))
                try:
                    frequency_penalty = float(os.getenv("BOTLIVE_FREQUENCY_PENALTY", "0.0"))
                except Exception:
                    frequency_penalty = 0.0

            logger.debug(f"📡 Appel OpenRouter ({model_name}) pour {user_id}")

            marker = "# 📊 DONNÉES DYNAMIQUES"
            messages = None
            try:
                if isinstance(prompt, str) and marker in prompt:
                    before, after = prompt.split(marker, 1)
                    system_content = (before or "").strip()
                    try:
                        if system_content and "<verdict_sys>" in system_content and "</verdict_sys>" in system_content:
                            system_content = regex.sub(
                                r"<verdict_sys>.*?</verdict_sys>",
                                "<verdict_sys>CHECKLIST en bas → next:[ACTION]</verdict_sys>",
                                system_content,
                                flags=regex.DOTALL,
                            )
                    except Exception:
                        pass
                    user_dynamic_content = f"{marker}{after}".strip()
                    if system_content and user_dynamic_content:
                        messages = [
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": user_dynamic_content},
                        ]
            except Exception:
                messages = None

            content, token_info = await complete(
                prompt=prompt if not messages else "",
                messages=messages,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
            )

            prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
            completion_tokens = int(token_info.get("completion_tokens", 0) or 0)
            total_tokens = int(token_info.get("total_tokens", prompt_tokens + completion_tokens) or 0)
            model = token_info.get("model", model_name)
            usage = token_info.get("usage") if isinstance(token_info, dict) else None
            if not isinstance(usage, dict):
                usage = {}

            cost = 0.0
            try:
                if token_info.get("total_cost") is not None:
                    cost = float(token_info.get("total_cost") or 0.0)
            except Exception:
                cost = 0.0

            try:
                content_len = 0
                if messages:
                    try:
                        content_len = sum(len(str(m.get("content") or "")) for m in messages)
                    except Exception:
                        content_len = 0
                else:
                    content_len = len(prompt)
                log3("[LLM]", f"OpenRouter {model} | {content_len} chars")
                token_msg = f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens"
                if cost:
                    token_msg = f"{token_msg} (cost=${cost:.6f})"
                cached_tokens = 0
                try:
                    cached_tokens = int(
                        usage.get("cached_tokens")
                        or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                        or 0
                    )
                except Exception:
                    cached_tokens = 0
                if cached_tokens:
                    token_msg = f"{token_msg} | cached_prompt_tokens={cached_tokens}"
                log3("[LLM][TOKENS]", token_msg)
                if usage:
                    log3("[LLM][USAGE]", usage)
                log3("[LLM][RAW]", content, max_lines=40, max_length=4000)
            except Exception:
                pass

            return {
                "response": content,
                "thinking": "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": cost,
                "model": model,
                "usage": usage,
            }
        except Exception as e:
            logger.error(f"❌ Erreur OpenRouter API: {e}")
            raise

    async def _call_groq(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """Appel API Groq 70B."""
        try:
            # Import du bon module Groq
            from core.llm_client_groq import complete

            logger.debug(f"📡 Appel Groq 70B pour {user_id}")

            # Appel API Groq réel
            content, token_info = await complete(
                prompt=prompt,
                model_name="llama-3.3-70b-versatile",
                max_tokens=1000,
                temperature=0.1,
            )

            prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
            completion_tokens = int(token_info.get("completion_tokens", 0) or 0)
            total_tokens = int(
                token_info.get("total_tokens", prompt_tokens + completion_tokens) or 0
            )
            cost = self._calculate_groq_cost(token_info)
            model = token_info.get("model", "llama-3.3-70b-versatile")

            try:
                log3("[LLM]", f"Groq {model} | {len(prompt)} chars")
                cached_tokens = 0
                try:
                    cached_tokens = int(
                        usage.get("cached_tokens")
                        or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                        or 0
                    )
                except Exception:
                    cached_tokens = 0
                token_msg = f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens (cost=${cost:.6f})"
                if cached_tokens:
                    token_msg = f"{token_msg} | cached_prompt_tokens={cached_tokens}"
                log3("[LLM][TOKENS]", token_msg)
                log3("[LLM][RAW]", content, max_lines=40, max_length=4000)
            except Exception:
                pass

            # Extraire thinking/response si format spécialisé
            thinking = ""
            response = content

            if "<thinking>" in content and "</thinking>" in content:
                thinking_match = regex.search(r"<thinking>(.*?)</thinking>", content, regex.DOTALL)
                response_match = regex.search(r"<response>(.*?)</response>", content, regex.DOTALL)

                if thinking_match:
                    thinking = thinking_match.group(1).strip()
                    try:
                        log3("[LLM][THINKING]", thinking, max_lines=40, max_length=4000)
                    except Exception:
                        pass
                if response_match:
                    response = response_match.group(1).strip()
                    try:
                        log3("[LLM][RESPONSE]", response, max_lines=40, max_length=4000)
                    except Exception:
                        pass

            return {
                "response": response,
                "thinking": thinking,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": cost,
                "model": model,
            }
        except Exception as e:
            logger.error(f"❌ Erreur Groq API: {e}")
            raise

    def _calculate_groq_cost(self, token_info: Dict[str, Any]) -> float:
        """Calcule le coût Groq selon les tokens utilisés (USD)."""
        prompt_tokens = int(token_info.get("prompt_tokens", 0) or 0)
        completion_tokens = int(token_info.get("completion_tokens", 0) or 0)

        # Tarifs Groq 70B (USD)
        input_cost = (prompt_tokens / 1_000_000) * 0.59
        output_cost = (completion_tokens / 1_000_000) * 0.79

        return input_cost + output_cost
    
    def _is_valid_response(self, response_data: Dict, llm_used: str) -> bool:
        """
        Valide la qualité d'une réponse LLM
        
        Args:
            response_data: Données de réponse
            llm_used: LLM utilisé
        
        Returns:
            bool: True si réponse valide
        """
        response = response_data.get('response', '')
        
        # 1. Réponse non vide
        if not response or len(response.strip()) < 5:
            logger.warning(f"⚠️ Réponse vide de {llm_used}")
            return False
        
        # 2. Pas de réponse générique répétitive (pour DeepSeek)
        if llm_used == "deepseek-v3":
            generic_responses = [
                "salut 👋 envoie photo produit",
                "envoie photo du produit",
                "impossible de télécharger"
            ]

            if any(generic.lower() in response.lower() for generic in generic_responses):
                # Acceptable pour DeepSeek si c'est approprié au contexte
                pass

        # 3. Format thinking/meta respecté
        if llm_used == "groq-70b":
            if "<thinking>" in response and "</thinking>" not in response:
                logger.warning(f" Format thinking malformé de {llm_used}")
                return False
        if llm_used == "openrouter":
            if "<meta>" in response.lower() and "</meta>" not in response.lower():
                logger.warning(f" Format meta malformé de {llm_used}")
                return False

        return True

    def _format_detected_objects(self, detected_objects: list) -> str:
        """Formate les objets détectés pour le prompt"""
        if not detected_objects:
            return "[AUCUN OBJET DÉTECTÉ]"

        
        formatted = []
        for obj in detected_objects:
            if isinstance(obj, str):
                formatted.append(obj)
            elif isinstance(obj, dict):
                # Support pour format BLIP-2: {'label': 'nom', 'confidence': 0.85}
                label = obj.get('label', obj.get('type', obj.get('description', 'objet inconnu')))
                confidence = obj.get('confidence', 0)
                if confidence > 0:
                    formatted.append(f"{label} (confiance: {confidence:.0%})")
                else:
                    formatted.append(label)
        
        return ", ".join(formatted) if formatted else "[AUCUN OBJET DÉTECTÉ]"
    
    def _format_transactions(self, transactions: list) -> str:
        """Formate les transactions pour le prompt (optimisé tokens)"""
        if not transactions:
            return "0F"
        
        formatted = []
        for trans in transactions:
            if isinstance(trans, dict):
                amount = trans.get('amount', '0')
                phone = trans.get('phone', '')
                # Tronquer numéro pour économiser tokens (garder 4 derniers chiffres)
                if phone and len(phone) >= 4:
                    phone_short = f"...{phone[-4:]}"
                else:
                    phone_short = phone
                formatted.append(f"{amount}F -> +225{phone_short}")
        
        return ", ".join(formatted) if formatted else "0F"
    
    def _build_loop_state(self, order_state: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Construit l'état attendu par LoopBotliveEngine à partir de OrderState + contexte."""
        def _extract_amount(p: Optional[str]) -> int:
            if not p:
                return 0
            try:
                m = regex.search(r'(\d+)', str(p))
                return int(m.group(1)) if m else 0
            except Exception:
                return 0

        # Coût livraison selon zone détectée
        zone_name = order_state.zone or ""
        periph = {"port-bouët", "attécoubé", "bingerville", "songon", "anyama", "port-bouet", "attecoube"}
        default_cost = 2000 if zone_name.lower() in periph else 1500
        if isinstance(context.get('delivery_info'), dict):
            try:
                default_cost = int(context['delivery_info'].get('cost', default_cost) or default_cost)
            except Exception:
                pass

        tel_valide = bool(order_state.numero and len(order_state.numero) == 10 and order_state.numero.startswith('0'))

        return {
            "photo": {"collected": bool(order_state.produit), "data": order_state.produit},
            "produit": {"collected": bool(order_state.produit), "data": order_state.produit},
            "paiement": {"collected": bool(order_state.paiement), "data": _extract_amount(order_state.paiement)},
            "zone": {"collected": bool(order_state.zone), "data": order_state.zone, "cost": default_cost},
            "tel": {"collected": bool(order_state.numero), "data": order_state.numero, "valid": tel_valide},
        }

    def _build_loop_trigger(
        self,
        before: Any,
        after: Any,
        context: Dict[str, Any],
        message: str,
    ) -> Optional[Dict[str, Any]]:
        """Construit le déclencheur pour LoopBotliveEngine en comparant before/after."""
        def _extract_amount(p: Optional[str]) -> int:
            if not p:
                return 0
            try:
                m = regex.search(r'(\d+)', str(p))
                return int(m.group(1)) if m else 0
            except Exception:
                return 0

        # Déterminer le montant requis
        expected_deposit_str = context.get('expected_deposit', '2000 FCFA')
        try:
            mm = regex.search(r'(\d+)', str(expected_deposit_str))
            required_amount = int(mm.group(1)) if mm else 2000
        except Exception:
            required_amount = 2000

        changed_produit = bool(after.produit and not before.produit)
        changed_paiement = bool(after.paiement and not before.paiement)
        changed_zone = bool(after.zone and not before.zone)
        changed_tel = bool(after.numero and not before.numero)
        completed_now = bool(after.is_complete() and not before.is_complete())

        # Téléphone d'abord (peut être final)
        if changed_tel:
            tel_clean = after.numero or ""
            tel_len = len(tel_clean)
            tel_valid = bool(tel_len == 10 and tel_clean.startswith('0'))
            all_others_collected = bool(after.produit and after.paiement and after.zone)
            # Payload complet attendu par TriggerValidator.validate_telephone_trigger
            base_tel_data = {
                "raw": message,
                "clean": tel_clean,
                "valid": tel_valid,
                "length": tel_len,
                "format_error": None,
            }

            if not tel_valid:
                if tel_len < 10:
                    base_tel_data["format_error"] = "TOO_SHORT"
                elif tel_len > 10:
                    base_tel_data["format_error"] = "TOO_LONG"
                elif not tel_clean.startswith('0'):
                    base_tel_data["format_error"] = "WRONG_PREFIX"
                else:
                    base_tel_data["format_error"] = "INVALID_FORMAT"

            if all_others_collected:
                # Téléphone final → déclencheur telephone_final
                return {"type": "telephone_final", "data": base_tel_data}

            # Sinon, téléphone détecté mais pas final
            return {"type": "telephone_detecte", "data": base_tel_data}

        # Paiement via OCR/transactions
        if changed_paiement:
            amt = _extract_amount(after.paiement)
            # Payload complet attendu par TriggerValidator.validate_paiement_trigger
            data = {
                "amount": amt,
                "valid": bool(amt > 0),
                "error": None,
                "currency": "FCFA",
                "transactions": context.get('filtered_transactions', []) or [],
                "raw_text": "",
                "sufficient": bool(amt >= required_amount),
            }
            return {"type": "paiement_ocr", "data": data}

        # Zone détectée
        if changed_zone:
            zone_name = after.zone
            periph = {"port-bouët", "attécoubé", "bingerville", "songon", "anyama", "port-bouet", "attecoube"}
            cost = 2000 if (zone_name and zone_name.lower() in periph) else 1500
            if isinstance(context.get('delivery_info'), dict):
                try:
                    cost = int(context['delivery_info'].get('cost', cost) or cost)
                except Exception:
                    pass
            # Payload complet attendu par TriggerValidator.validate_zone_trigger
            zone_info = context.get('delivery_info') if isinstance(context.get('delivery_info'), dict) else None
            # Catégorie heuristique
            centrale_zones = {"plateau", "cocody", "marcory", "koumassi", "treichville"}
            if zone_name and zone_name.lower() in centrale_zones:
                category = "centrale"
            elif zone_name and zone_name.lower() in periph:
                category = "peripherique"
            else:
                category = "expedition"

            data = {
                "zone": zone_name,
                "cost": cost,
                "category": category,
                "name": zone_name,
                "source": "delivery_info" if zone_info else "regex_message",
                "confidence": float(zone_info.get('confidence', 0.9)) if zone_info else 0.6,
            }
            return {"type": "zone_detectee", "data": data}

        # Photo/produit détecté
        if changed_produit:
            conf = 0.8
            try:
                det = context.get('detected_objects', []) or []
                for obj in det:
                    if isinstance(obj, dict) and str(obj.get('label', '')).lower() in str(after.produit or '').lower():
                        if 'confidence' in obj:
                            conf = float(obj['confidence'])
                            break
            except Exception:
                pass
            # Payload complet attendu par TriggerValidator.validate_photo_trigger
            photo_data = {
                "description": after.produit or "",
                "confidence": conf,
                "error": None,
                "valid": True,
                "product_detected": True,
            }
            return {"type": "photo_produit", "data": photo_data}

        # Récap automatique si complété sur ce tour
        if completed_now:
            return {"type": "recap_auto", "data": None}

        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du système hybride
        
        Returns:
            Dict: Statistiques complètes
        """
        router_stats = self.router.get_stats()

        total = max(self.stats['total_requests'], 1)
        return {
            **self.stats,
            **router_stats,
            'primary_llm_percentage': (self.stats['primary_llm_requests'] / total) * 100,
            'fallback_llm_percentage': (self.stats['fallback_llm_requests'] / total) * 100,
            'tools_usage_rate': (self.stats['tools_used'] / total) * 100,
            'fallback_rate': (self.stats['fallbacks'] / total) * 100,
        }
    
    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            'total_requests': 0,
            'primary_llm_requests': 0,
            'fallback_llm_requests': 0,
            'tools_used': 0,
            'fallbacks': 0,
        }

# Instance globale
botlive_hybrid = BotliveRAGHybrid()

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 FONCTIONS DE TEST
# ═══════════════════════════════════════════════════════════════════════════════

async def test_hybrid_system():
    """Test rapide du système hybride"""
    print("🧪 Test système hybride Botlive")
    
    # Test cas simple (DeepSeek attendu)
    print("\n1. Test cas simple:")
    result1 = await botlive_hybrid.process_request(
        user_id="test_user_1",
        message="Bonjour",
        context={},
        conversation_history=""
    )
    print(f"LLM: {result1['llm_used']} | Réponse: {result1['response']}")
    
    # Test cas complexe (Groq attendu)
    print("\n2. Test cas complexe:")
    result2 = await botlive_hybrid.process_request(
        user_id="test_user_2", 
        message="Validation paiement",
        context={
            'filtered_transactions': [{'amount': '2020', 'phone': '0787360757'}],
            'expected_deposit': '2000 FCFA'
        },
        conversation_history="Photo reçue ! Confirmes ?"
    )
    print(f"LLM: {result2['llm_used']} | Réponse: {result2['response']}")
    
    # Affichage stats
    print(f"\n📊 Stats: {botlive_hybrid.get_stats()}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_system())
