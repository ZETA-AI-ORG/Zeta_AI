"""
🎯 MOTEUR RAG SIMPLIFIÉ - ARCHITECTURE RADICALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Philosophie : Abandon de la recherche complexe Meili/Supabase
- ✅ Prompt statique avec infos entreprise
- ✅ Injection dynamique minimale (regex + Gemini + Meili coûts/stock)
- ✅ Checklist commande intégrée
- ✅ Token usage réel depuis OpenRouter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import time
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import re

from config import LLM_TRANSMISSION_TOKEN


CONFIDENCE_THRESHOLD = 0.8

from core.order_state_tracker import order_tracker
from core.payment_validator import validate_payment_cumulative, format_payment_for_prompt

from core.simplified_prompt_system import get_simplified_prompt_system
from core.price_calculator import UniversalPriceCalculator
from core.dynamic_context_injector import get_dynamic_context_injector
from core.llm_client import get_llm_client
from core.company_catalog_v2_loader import get_company_catalog_v2, get_company_product_catalog_v2
from core.catalog_v2_item_normalizer import normalize_detected_items
from core.cart_manager import CartManager


@dataclass
class SimplifiedRAGResult:
    """Résultat du moteur RAG simplifié"""
    response: str
    confidence: float
    processing_time_ms: float
    checklist_state: str
    next_step: str
    detected_location: Optional[str]
    shipping_fee: Optional[str]
    
    # Métriques LLM (OpenRouter)
    usage: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    
    # Thinking
    thinking: str = ""


class SimplifiedRAGEngine:
    """Moteur RAG simplifié avec prompt statique + injection dynamique minimale"""
    
    def __init__(self):
        """Initialise le moteur RAG simplifié"""
        self.prompt_system = get_simplified_prompt_system()
        self.context_injector = get_dynamic_context_injector()
        self.llm_client = None
        self.cart_manager = CartManager(ttl_seconds=259200)
    
    async def initialize(self):
        """Initialise le client LLM"""
        if self.llm_client is None:
            self.llm_client = get_llm_client()
            print("✅ [SIMPLIFIED RAG] LLM client initialisé")
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        company_id: str,
        company_name: str = "Rue du Grossiste",
        images: Optional[List[str]] = None,
        request_id: str = "unknown"
    ) -> SimplifiedRAGResult:
        """
        Traite une requête avec le système simplifié
        
        Pipeline:
        1. Collecte contexte dynamique (regex + Gemini + Meili)
        2. Construction prompt (statique + dynamique)
        3. Génération LLM avec token tracking
        4. Extraction thinking + response
        
        Args:
            query: Question utilisateur
            user_id: ID utilisateur
            company_id: ID entreprise
            company_name: Nom entreprise
            images: URLs images (optionnel)
            request_id: ID requête pour tracking
        
        Returns:
            SimplifiedRAGResult avec réponse + métriques
        """
        start_time = time.time()

        # Si un handoff a été déclenché, on met le bot en pause pour éviter qu'il réponde pendant l'intervention humaine.
        # (Le frontend/humain peut reprendre la conversation via un autre canal.)
        try:
            if order_tracker.get_flag(user_id, "bot_paused"):
                paused_msg = (os.getenv("SIMPLIFIED_RAG_PAUSED_MESSAGE") or "Je t'ai passé le responsable, il revient vers toi.").strip()
                processing_time = (time.time() - start_time) * 1000
                checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                print("⏸️ [SIMPLIFIED RAG] bot_paused=True -> short-circuit")
                return SimplifiedRAGResult(
                    response=paused_msg,
                    confidence=1.0,
                    processing_time_ms=processing_time,
                    checklist_state=checklist.to_string(),
                    next_step=checklist.get_next_step(),
                    detected_location=None,
                    shipping_fee=None,
                    usage=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    model="python_paused_short_circuit",
                    thinking="",
                )
        except Exception:
            pass

        # Post-confirmation: quand la commande est complète, éviter de rappeler le LLM principal
        # pour des confirmations/courtoisie simples.
        try:
            st0 = order_tracker.get_state(user_id)
            completion_rate = float(st0.get_completion_rate()) if st0 is not None else 0.0
        except Exception:
            completion_rate = 0.0

        async def _call_mini_llm_post_confirmation(user_message: str) -> Dict[str, Any]:
            prompt = (
                "Tu es un classificateur rapide. La commande est COMPLETE et confirmee.\n"
                f"Message client: \"{str(user_message or '').strip()}\"\n\n"
                "Classifie l'intention:\n"
                "- THANKS: remerciements\n"
                "- SMALL_TALK: conversation legere\n"
                "- GOODBYE: au revoir\n"
                "- PROBLEM: probleme serieux\n"
                "- COMPLAINT: reclamation\n"
                "- QUESTION: question importante\n"
                "- MODIFICATION: modifier commande\n\n"
                "Reponds UNIQUEMENT en JSON: {\"intent\":\"...\",\"response\":\"...\" ou null}"
            )
            try:
                if self.llm_client is None:
                    await self.initialize()
                out = await self.llm_client.complete(
                    prompt=prompt,
                    model_name="google/gemini-2.5-flash",
                    temperature=0.0,
                    max_tokens=100,
                )
                txt = str((out or {}).get("response") if isinstance(out, dict) else out).strip()

                # Robust JSON extraction (model may wrap in ```json ...```)
                if txt.startswith("```"):
                    txt = re.sub(r"^```(?:json)?\s*", "", txt.strip(), flags=re.IGNORECASE)
                    txt = re.sub(r"```\s*$", "", txt.strip())

                m_obj = re.search(r"\{.*\}", txt, flags=re.DOTALL)
                txt_json = (m_obj.group(0).strip() if m_obj else txt.strip())

                data = json.loads(txt_json) if txt_json else {}
                if not isinstance(data, dict):
                    return {"intent": "UNKNOWN", "response": None}
                return {
                    "intent": str(data.get("intent") or "UNKNOWN").strip().upper(),
                    "response": (None if data.get("response") is None else str(data.get("response") or "").strip()),
                }
            except Exception:
                return {"intent": "UNKNOWN", "response": None}

        async def _handle_post_confirmation(user_message: str) -> Optional[Dict[str, Any]]:
            try:
                msg = str(user_message or "").strip().lower()
            except Exception:
                msg = ""
            if not msg:
                return None

            confirmation_simple = r"^\s*(oui|ok|d'?accord|parfait|valide|valid[eé]?|yes|oui\s+oui|c'?est\s+bon)\s*[!.]?\s*$"
            if re.match(confirmation_simple, msg, flags=re.IGNORECASE):
                return {"response": "C'est noté ! 🎉 Merci !", "level": "L1_PYTHON"}

            courtoisie = r"^\s*(merci|merci\s+beaucoup|merci\s+bien|ok\s+merci|super|cool|nickel|parfait\s+merci)\s*[!.]?\s*$"
            if re.match(courtoisie, msg, flags=re.IGNORECASE):
                return {"response": "Avec plaisir ! 😊", "level": "L1_PYTHON"}

            mini = await _call_mini_llm_post_confirmation(user_message)
            intent = str(mini.get("intent") or "UNKNOWN").strip().upper()
            resp = mini.get("response")
            if intent in {"THANKS", "SMALL_TALK", "GOODBYE"} and resp:
                return {"response": str(resp), "level": "L2_MINI_LLM"}

            if intent in {"PROBLEM", "COMPLAINT", "QUESTION", "MODIFICATION"}:
                return None

            if resp:
                return {"response": str(resp), "level": "L2_MINI_LLM"}

            return {"response": "Merci pour votre confiance ! 😊", "level": "L1_FALLBACK"}

        try:
            if completion_rate >= 1.0:
                post_conf = await _handle_post_confirmation(query)
                if post_conf and post_conf.get("response"):
                    processing_time = (time.time() - start_time) * 1000
                    checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                    level = str(post_conf.get("level") or "UNKNOWN")
                    return SimplifiedRAGResult(
                        response=str(post_conf.get("response") or "").strip(),
                        confidence=1.0,
                        processing_time_ms=processing_time,
                        checklist_state=checklist.to_string(),
                        next_step=checklist.get_next_step(),
                        detected_location=None,
                        shipping_fee=None,
                        usage=None,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        cost=0.0,
                        model=f"post_confirmation_{level.lower()}",
                        thinking="",
                    )
        except Exception:
            pass

        # ANSI colors (console)
        C_RESET = "\033[0m"
        C_YELLOW = "\033[33m"
        C_RED = "\033[31m"
        C_GREEN = "\033[32m"
        
        print(f"\n🎯 [SIMPLIFIED RAG] Début traitement: '{query[:50]}...'")
        print(f"🏢 Company: {company_id[:12]}... | User: {user_id[:12]}...")
        
        try:
            current_turn = 0
            try:
                current_turn = order_tracker.bump_turn(user_id)
            except Exception as _turn_e:
                print(f"⚠️ [ORDER_STATE] bump_turn_error: {type(_turn_e).__name__}: {_turn_e}")

            def _norm_name_for_id(name: str) -> str:
                try:
                    import unicodedata as _ud

                    t = str(name or "").strip().lower()
                    t = _ud.normalize("NFKD", t)
                    t = "".join([c for c in t if not _ud.combining(c)])
                except Exception:
                    t = str(name or "").strip().lower()
                t = re.sub(r"[^a-z0-9\s-]+", " ", t)
                t = t.replace("-", " ")
                t = re.sub(r"\s+", " ", t).strip()
                return t

            def _product_id_hash(name: str) -> str:
                base = _norm_name_for_id(name)
                if not base:
                    return ""
                try:
                    import hashlib as _hashlib

                    h = _hashlib.sha1(base.encode("utf-8", errors="replace")).hexdigest()
                    return f"prod_{h[:8]}"
                except Exception:
                    return ""

            def _looks_like_product_id(v: str) -> bool:
                s = str(v or "").strip().lower()
                if not s:
                    return False
                if not s.startswith("prod_"):
                    return False
                return bool(re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", s, flags=re.IGNORECASE))

            def _parse_price_value(raw: Any) -> Optional[int]:
                try:
                    if raw is None:
                        return None
                    if isinstance(raw, bool):
                        return None
                    if isinstance(raw, (int, float)):
                        v = int(raw)
                        return v if v > 0 else None
                    if isinstance(raw, (list, tuple)) and raw:
                        x0 = raw[0]
                        if isinstance(x0, (int, float)):
                            v = int(x0)
                            return v if v > 0 else None
                        if isinstance(x0, str):
                            m = re.search(r"(\d+)", x0.replace(" ", ""))
                            v = int(m.group(1)) if m else 0
                            return v if v > 0 else None
                    if isinstance(raw, dict):
                        for k in ["price", "prix", "amount", "value"]:
                            if k in raw:
                                return _parse_price_value(raw.get(k))
                    s = str(raw)
                    m2 = re.search(r"(\d+)", s.replace(" ", ""))
                    v2 = int(m2.group(1)) if m2 else 0
                    return v2 if v2 > 0 else None
                except Exception:
                    return None

            def _match_key_case_insensitive(keys: List[str], target: str) -> str:
                t = str(target or "").strip().lower()
                if not t:
                    return ""
                for k in keys:
                    if str(k or "").strip().lower() == t:
                        return str(k)
                return ""

            def _format_unit_label(unit_key: str, custom_formats: List[Dict[str, Any]]) -> str:
                u = str(unit_key or "").strip()
                if not u:
                    return ""

                def _from_unit_key(u0: str) -> str:
                    try:
                        m = re.match(r"^(paquet|lot)_(\d{1,4})$", str(u0 or "").strip(), flags=re.IGNORECASE)
                        if m:
                            typ = str(m.group(1) or "").strip().lower()
                            qty = str(m.group(2) or "").strip()
                            if typ and qty:
                                return f"{typ} de {qty}".strip()
                    except Exception:
                        pass
                    return ""

                try:
                    for f in (custom_formats or []):
                        if not isinstance(f, dict):
                            continue
                        f_type = str(f.get("type") or "").strip()
                        qty = f.get("quantity")
                        try:
                            qty_i = int(qty) if qty is not None else None
                        except Exception:
                            qty_i = None
                        canonical = ""
                        if f_type and qty_i and qty_i > 0:
                            canonical = f"{f_type}_{qty_i}"
                        if canonical and canonical.strip().lower() == u.lower():
                            primary = str(
                                f.get("label")
                                or f.get("customLabel")
                                or f.get("custom_label")
                                or ""
                            ).strip()
                            if primary:
                                return primary

                            unit_label = str(f.get("unitLabel") or "").strip()
                            if unit_label and unit_label.lower() not in {"pièces", "pieces", "piece", "pcs", "pc"}:
                                return unit_label

                            if f_type and qty_i and qty_i > 0:
                                return f"{f_type} de {qty_i}".strip()

                            by_key = _from_unit_key(u)
                            if by_key:
                                return by_key

                            return u.replace("_", " ")
                except Exception:
                    pass
                by_key = _from_unit_key(u)
                if by_key:
                    return by_key
                return u.replace("_", " ")

            def _generate_price_list_for_tool_call(
                *,
                company_id_val: str,
                product_id_val: str,
                variant_val: str,
                spec_val: Optional[str] = None,
            ) -> Tuple[str, List[Dict[str, Any]]]:
                try:
                    pid = str(product_id_val or "").strip()
                    if not pid:
                        return "", []
                    variant_s = str(variant_val or "").strip()
                    if not variant_s:
                        return "", []

                    selected_catalog = None
                    try:
                        selected_catalog = get_company_product_catalog_v2(company_id_val, pid)
                    except Exception:
                        selected_catalog = None
                    if not isinstance(selected_catalog, dict):
                        try:
                            container = get_company_catalog_v2(company_id_val)
                        except Exception:
                            container = None
                        if isinstance(container, dict) and isinstance(container.get("products"), list):
                            for p in (container.get("products") or []):
                                if not isinstance(p, dict):
                                    continue
                                ppid = str(p.get("product_id") or (p.get("catalog_v2") or {}).get("product_id") or "").strip()
                                if ppid and ppid.strip().lower() == pid.lower() and isinstance(p.get("catalog_v2"), dict):
                                    selected_catalog = p.get("catalog_v2")
                                    break
                        elif isinstance(container, dict):
                            selected_catalog = container

                    if not isinstance(selected_catalog, dict):
                        return "", []

                    if str(selected_catalog.get("pricing_strategy") or "").upper() != "UNIT_AS_ATOMIC":
                        return "", []

                    product_name = str(selected_catalog.get("product_name") or selected_catalog.get("name") or "").strip()
                    ui_state = selected_catalog.get("ui_state") if isinstance(selected_catalog.get("ui_state"), dict) else {}
                    custom_formats = ui_state.get("customFormats") if isinstance(ui_state.get("customFormats"), list) else []
                    vtree = selected_catalog.get("v") if isinstance(selected_catalog.get("v"), dict) else {}
                    if not vtree:
                        return "", []

                    variant_key = _match_key_case_insensitive([str(k) for k in vtree.keys()], variant_s)
                    if not variant_key:
                        return "", []
                    node = vtree.get(variant_key)
                    if not isinstance(node, dict):
                        return "", []

                    u_map = node.get("u") if isinstance(node.get("u"), dict) else None
                    items: List[Dict[str, Any]] = []
                    if isinstance(u_map, dict) and u_map:
                        for unit_key, raw_price in u_map.items():
                            p = _parse_price_value(raw_price)
                            if p is None:
                                continue
                            uk = str(unit_key or "").strip()
                            if not uk:
                                continue
                            label = _format_unit_label(uk, custom_formats)
                            items.append(
                                {
                                    "product_id": pid,
                                    "variant": variant_key,
                                    "spec": str(spec_val).strip() if spec_val else None,
                                    "unit": uk,
                                    "label": label,
                                    "price_fcfa": int(p),
                                }
                            )
                    else:
                        # Fallback: certains catalogues stockent les prix sous s->u (prix par spec)
                        s_map = node.get("s") if isinstance(node.get("s"), dict) else None
                        if not isinstance(s_map, dict) or not s_map:
                            return "", []

                        spec_keys = [str(k) for k in s_map.keys() if str(k).strip()]
                        spec_keys = sorted(spec_keys)
                        for sk in spec_keys[:12]:
                            snode = s_map.get(sk)
                            if not isinstance(snode, dict):
                                continue
                            u2 = snode.get("u") if isinstance(snode.get("u"), dict) else None
                            if not isinstance(u2, dict) or not u2:
                                continue
                            for unit_key, raw_price in u2.items():
                                p = _parse_price_value(raw_price)
                                if p is None:
                                    continue
                                uk = str(unit_key or "").strip()
                                if not uk:
                                    continue
                                label = _format_unit_label(uk, custom_formats)
                                items.append(
                                    {
                                        "product_id": pid,
                                        "variant": variant_key,
                                        "spec": str(sk).strip(),
                                        "unit": uk,
                                        "label": label,
                                        "price_fcfa": int(p),
                                    }
                                )

                    if not items:
                        return "", []

                    items = sorted(items, key=lambda x: int(x.get("price_fcfa") or 0))
                    if len(items) > 12:
                        items = items[:12]

                    lines: List[str] = []
                    head = (product_name if product_name else "Catalogue").strip()

                    def _num_emoji(n: int) -> str:
                        try:
                            mp = {
                                1: "1️⃣",
                                2: "2️⃣",
                                3: "3️⃣",
                                4: "4️⃣",
                                5: "5️⃣",
                                6: "6️⃣",
                                7: "7️⃣",
                                8: "8️⃣",
                                9: "9️⃣",
                                10: "🔟",
                            }
                            return mp.get(int(n), f"{n}.")
                        except Exception:
                            return f"{n}."

                    lines.append(f"D'accord 😊 Voici les options pour {str(variant_key).strip().lower()} :")
                    lines.append("")
                    for i, it in enumerate(items, 1):
                        lbl = str(it.get("label") or "").strip() or str(it.get("unit") or "").strip()
                        sp = str(it.get("spec") or "").strip()
                        price_i = int(it.get("price_fcfa") or 0)
                        if lbl.lower() in {"pièces", "pieces", "piece", "pcs", "pc"}:
                            lbl = _format_unit_label(str(it.get("unit") or "").strip(), custom_formats)

                        if sp and (not spec_val):
                            left = f"{_num_emoji(i)} {sp} - {lbl}".strip()
                            lines.append(f"{left} — {UniversalPriceCalculator._fmt_fcfa(price_i)}F")
                        else:
                            left = f"{_num_emoji(i)} {lbl}".strip()
                            lines.append(f"{left} — {UniversalPriceCalculator._fmt_fcfa(price_i)}F")
                    lines.append("")
                    lines.append("Que prenez-vous ? (répondez par le numéro)")

                    for i, it in enumerate(items, 1):
                        it["index"] = i

                    return "\n".join([ln for ln in lines if ln is not None]), items
                except Exception:
                    return "", []

            def _generate_price_table_for_product(
                *,
                company_id_val: str,
                product_id_val: str,
            ) -> Tuple[str, List[Dict[str, Any]]]:
                try:
                    pid = str(product_id_val or "").strip()
                    if not pid:
                        return "", []

                    selected_catalog = None
                    try:
                        selected_catalog = get_company_product_catalog_v2(company_id_val, pid)
                    except Exception:
                        selected_catalog = None
                    if not isinstance(selected_catalog, dict):
                        try:
                            container = get_company_catalog_v2(company_id_val)
                        except Exception:
                            container = None
                        if isinstance(container, dict) and isinstance(container.get("products"), list):
                            for p in (container.get("products") or []):
                                if not isinstance(p, dict):
                                    continue
                                ppid = str(p.get("product_id") or (p.get("catalog_v2") or {}).get("product_id") or "").strip()
                                if ppid and ppid.strip().lower() == pid.lower() and isinstance(p.get("catalog_v2"), dict):
                                    selected_catalog = p.get("catalog_v2")
                                    break
                        elif isinstance(container, dict):
                            selected_catalog = container

                    if not isinstance(selected_catalog, dict):
                        return "", []

                    if str(selected_catalog.get("pricing_strategy") or "").upper() != "UNIT_AS_ATOMIC":
                        return "", []

                    product_name = str(selected_catalog.get("product_name") or selected_catalog.get("name") or "").strip()
                    ui_state = selected_catalog.get("ui_state") if isinstance(selected_catalog.get("ui_state"), dict) else {}
                    custom_formats = ui_state.get("customFormats") if isinstance(ui_state.get("customFormats"), list) else []
                    vtree = selected_catalog.get("v") if isinstance(selected_catalog.get("v"), dict) else {}
                    if not vtree:
                        return "", []

                    items: List[Dict[str, Any]] = []

                    def _add_unit_map(*, variant_key: str, spec_key: Optional[str], u_map: Dict[str, Any]) -> None:
                        if not isinstance(u_map, dict) or not u_map:
                            return
                        for unit_key, raw_price in u_map.items():
                            p = _parse_price_value(raw_price)
                            if p is None:
                                continue
                            uk = str(unit_key or "").strip()
                            if not uk:
                                continue
                            label = _format_unit_label(uk, custom_formats)
                            items.append(
                                {
                                    "product_id": pid,
                                    "variant": str(variant_key),
                                    "spec": str(spec_key).strip() if spec_key else None,
                                    "unit": uk,
                                    "label": label,
                                    "price_fcfa": int(p),
                                }
                            )

                    for vk, vnode in vtree.items():
                        vkey = str(vk or "").strip()
                        if not vkey:
                            continue
                        if not isinstance(vnode, dict):
                            continue

                        u_map0 = vnode.get("u") if isinstance(vnode.get("u"), dict) else None
                        if isinstance(u_map0, dict) and u_map0:
                            _add_unit_map(variant_key=vkey, spec_key=None, u_map=u_map0)
                            continue

                        s_map = vnode.get("s") if isinstance(vnode.get("s"), dict) else None
                        if isinstance(s_map, dict) and s_map:
                            sub_keys = [str(k) for k in s_map.keys() if str(k).strip()]
                            sub_keys = sorted(sub_keys)
                            for sk in sub_keys[:8]:
                                snode = s_map.get(sk)
                                if not isinstance(snode, dict):
                                    continue
                                u_map1 = snode.get("u") if isinstance(snode.get("u"), dict) else None
                                if isinstance(u_map1, dict) and u_map1:
                                    _add_unit_map(variant_key=vkey, spec_key=str(sk), u_map=u_map1)

                    if not items:
                        return "", []

                    items = sorted(items, key=lambda x: (str(x.get("variant") or ""), int(x.get("price_fcfa") or 0)))
                    if len(items) > 18:
                        items = items[:18]

                    lines: List[str] = []
                    head = (product_name if product_name else "Catalogue").strip()

                    def _num_emoji(n: int) -> str:
                        try:
                            mp = {
                                1: "1️⃣",
                                2: "2️⃣",
                                3: "3️⃣",
                                4: "4️⃣",
                                5: "5️⃣",
                                6: "6️⃣",
                                7: "7️⃣",
                                8: "8️⃣",
                                9: "9️⃣",
                                10: "🔟",
                            }
                            return mp.get(int(n), f"{n}.")
                        except Exception:
                            return f"{n}."

                    # ── Regrouper par variante pour une meilleure lisibilité WhatsApp ──
                    from collections import OrderedDict
                    grouped: OrderedDict = OrderedDict()
                    for it in items:
                        vk = str(it.get("variant") or "").strip()
                        if vk not in grouped:
                            grouped[vk] = []
                        grouped[vk].append(it)

                    lines.append("D'accord 😊 Voici nos formats disponibles :")
                    lines.append("")
                    global_idx = 1
                    for variant_name, variant_items in grouped.items():
                        # Sous-titre par variante
                        has_specs = any(str(it.get("spec") or "").strip() for it in variant_items)
                        # Déterminer le format unique si tous les items ont le même unit
                        unique_units = set(str(it.get("label") or it.get("unit") or "").strip() for it in variant_items)
                        unit_suffix = ""
                        if has_specs and len(unique_units) == 1:
                            unit_suffix = f" ({list(unique_units)[0]})"
                        lines.append(f"🔹 {variant_name}{unit_suffix}")
                        for it in variant_items:
                            sp = str(it.get("spec") or "").strip()
                            lbl = str(it.get("label") or "").strip() or str(it.get("unit") or "").strip()
                            price_i = int(it.get("price_fcfa") or 0)
                            price_str = f"{UniversalPriceCalculator._fmt_fcfa(price_i)} F"
                            if has_specs:
                                # Variante avec specs (ex: Pression T1-T6) → "Taille X : prix"
                                lines.append(f"{_num_emoji(global_idx)} {sp} : {price_str}")
                            else:
                                # Variante sans specs, formats multiples (ex: Culotte paquet/lot) → "format : prix"
                                lines.append(f"{_num_emoji(global_idx)} {lbl} : {price_str}")
                            it["index"] = global_idx
                            global_idx += 1
                        lines.append("")
                    lines.append("👉 Dites-moi simplement le numéro de votre choix.")

                    return "\n".join([ln for ln in lines if ln is not None]), items
                except Exception:
                    return "", []

            def _reverse_lookup_price_choice(message: str, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
                try:
                    if not items:
                        return None

                    m_ord = re.search(r"\b(\d{1,2})\s*(?:e|eme|ème|er)\b", message)
                    if m_ord:
                        idx = int(m_ord.group(1))
                        if 1 <= idx <= len(items):
                            return items[idx - 1]

                    # Support: "le 2", "option 2", "numéro 2", "choix 2", "n°2"
                    m_idx = re.search(r"\b(?:le|la|l'|option|choix|numero|numéro|n°|no)\s*(\d{1,2})\b", message, flags=re.IGNORECASE)
                    if m_idx:
                        idx0 = int(m_idx.group(1))
                        if 1 <= idx0 <= len(items):
                            return items[idx0 - 1]

                    if re.fullmatch(r"\d{1,2}", message):
                        idx2 = int(message)
                        if 1 <= idx2 <= len(items):
                            return items[idx2 - 1]

                    # Dernier filet: si le message contient un chiffre unique (ex: "2" dans une phrase)
                    digits = re.findall(r"\b(\d{1,2})\b", message)
                    if len(digits) == 1:
                        idx3 = int(digits[0])
                        if 1 <= idx3 <= len(items):
                            return items[idx3 - 1]

                    norm_msg = _norm_name_for_id(message)
                    best = None
                    for it in items:
                        lbl = _norm_name_for_id(str(it.get("label") or ""))
                        uk = _norm_name_for_id(str(it.get("unit") or ""))
                        if lbl and lbl in norm_msg:
                            best = it
                            break
                        if uk and uk in norm_msg:
                            best = it
                            break
                    if best is not None:
                        return best

                    m_amt = re.search(r"(\d{3,6})", message.replace(" ", ""))
                    if m_amt:
                        amt = int(m_amt.group(1))
                        matches = [it for it in items if int(it.get("price_fcfa") or 0) == amt]
                        if len(matches) == 1:
                            return matches[0]

                    return None
                except Exception:
                    return None

            def _pick_pid_from_product_entry(p: dict, pname: str) -> str:
                try:
                    cat = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else {}
                except Exception:
                    cat = {}
                real_id = str(p.get("product_id") or (cat or {}).get("product_id") or "").strip()
                if real_id:
                    return real_id
                return _product_id_hash(pname)

            def _map_product_name_to_pid(company_id_val: str, cand: str) -> str:
                cname = _norm_name_for_id(cand)
                if not cname:
                    return ""
                try:
                    container = get_company_catalog_v2(company_id_val)
                except Exception:
                    container = None

                if isinstance(container, dict) and isinstance(container.get("products"), list):
                    for p in (container.get("products") or []):
                        if not isinstance(p, dict):
                            continue
                        pname = str(p.get("product_name") or (p.get("catalog_v2") or {}).get("product_name") or "").strip()
                        if pname and _norm_name_for_id(pname) == cname:
                            real_id = str(p.get("product_id") or (p.get("catalog_v2") or {}).get("product_id") or "").strip()
                            if real_id:
                                return real_id
                            return _product_id_hash(pname)

                if isinstance(container, dict):
                    pname = str(container.get("product_name") or container.get("name") or "").strip()
                    if pname and _norm_name_for_id(pname) == cname:
                        real_id = str(container.get("product_id") or "").strip()
                        if real_id:
                            return real_id
                        return _product_id_hash(pname)

                return ""

            prev_product_before_llm = ""
            try:
                st_prev = order_tracker.get_state(user_id)
                prev_product_before_llm = str(getattr(st_prev, "produit", "") or "").strip()
            except Exception:
                prev_product_before_llm = ""

            def _is_price_intent(msg: str) -> bool:
                try:
                    s = str(msg or "").lower()
                except Exception:
                    s = ""
                if not s.strip():
                    return False
                return bool(
                    re.search(
                        r"\b(prix|tarif|tarifs|combien|co[uû]te|cout|co[uû]t|c'est\s+combien|cest\s+combien|montant)\b",
                        s,
                        flags=re.IGNORECASE,
                    )
                )

            pending_price_list_text = ""
            pending_price_list_items: List[Dict[str, Any]] = []

            try:
                if order_tracker.get_flag(user_id, "awaiting_price_choice"):
                    raw_items = order_tracker.get_custom_meta(user_id, "price_list_items", default=[])
                    price_list_items = raw_items if isinstance(raw_items, list) else []
                    price_list_text = str(order_tracker.get_custom_meta(user_id, "price_list_text", default="") or "").strip()

                    picked = _reverse_lookup_price_choice(query, price_list_items)
                    if picked is None:
                        # Ne pas boucler en renvoyant la liste: laisser le LLM interpréter la réponse libre.
                        # On garde la liste pour l'injecter dans l'historique (contexte) plus bas.
                        if price_list_text:
                            pending_price_list_text = price_list_text
                            pending_price_list_items = price_list_items if isinstance(price_list_items, list) else []
                    else:
                        order_tracker.set_flag(user_id, "awaiting_price_choice", False)
                        try:
                            order_tracker.set_custom_meta(user_id, "price_list_choice", picked)
                        except Exception:
                            pass

                        # Si un panier existe déjà et que ce choix pivote (variant/spec/unit), demander A/B
                        # au lieu d'écraser silencieusement l'existant.
                        try:
                            existing_items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                            existing_items = existing_items if isinstance(existing_items, list) else []
                        except Exception:
                            existing_items = []

                        try:
                            if isinstance(existing_items, list) and existing_items:
                                ex0 = existing_items[0] if isinstance(existing_items[0], dict) else {}
                                ex_pid = str((ex0 or {}).get("product_id") or "").strip().lower()
                                ex_var = str((ex0 or {}).get("variant") or "").strip().lower()

                                pk_pid = str(picked.get("product_id") or "").strip().lower()
                                pk_var = str(picked.get("variant") or "").strip().lower()

                                would_pivot = bool((ex_pid and pk_pid and ex_pid != pk_pid) or (ex_var and pk_var and ex_var != pk_var))

                                if would_pivot:
                                    ans = _parse_add_or_modify_answer(query)
                                    if not ans:
                                        detected_items_choice = [
                                            {
                                                "product_id": str(picked.get("product_id") or "").strip(),
                                                "variant": str(picked.get("variant") or "").strip() or None,
                                                "spec": (str(picked.get("spec") or "").strip() or None),
                                                "unit": str(picked.get("unit") or "").strip() or None,
                                                "qty": 1,
                                                "confidence": 0.95,
                                            }
                                        ]
                                        try:
                                            order_tracker.set_custom_meta(user_id, "pending_cart_items", detected_items_choice)
                                            order_tracker.set_custom_meta(user_id, "pending_cart_question", "add_or_modify")
                                        except Exception:
                                            pass

                                        processing_time = (time.time() - start_time) * 1000
                                        checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                                        new_variant = str(picked.get("variant") or "").strip()
                                        new_spec = str(picked.get("spec") or "").strip()
                                        new_label = (new_variant + (" " + new_spec if new_spec else "")).strip()

                                        cur_label = ""
                                        try:
                                            ex0 = existing_items[0] if existing_items and isinstance(existing_items[0], dict) else {}
                                            cur_v = str((ex0 or {}).get("variant") or "").strip()
                                            cur_s = str((ex0 or {}).get("spec") or "").strip()
                                            cur_label = (cur_v + (" " + cur_s if cur_s else "")).strip()
                                        except Exception:
                                            cur_label = ""

                                        if cur_label and new_label:
                                            forced_q = f"Vous modifiez votre panier ({cur_label}) pour {new_label} ou on ajoute ?"
                                        elif new_label:
                                            forced_q = f"On ajoute {new_label} au panier ou vous modifiez ?"
                                        else:
                                            forced_q = "On ajoute au panier ou vous modifiez ?"

                                        return SimplifiedRAGResult(
                                            response=forced_q,
                                            confidence=1.0,
                                            processing_time_ms=processing_time,
                                            checklist_state=checklist.to_string(),
                                            next_step=checklist.get_next_step(),
                                            detected_location=None,
                                            shipping_fee=None,
                                            usage=None,
                                            prompt_tokens=int(prompt_tokens or 0),
                                            completion_tokens=int(completion_tokens or 0),
                                            total_tokens=int(total_tokens or 0),
                                            cost=float(cost or 0.0),
                                            model="python_cart_change_clarify",
                                            thinking="",
                                        )
                        except Exception:
                            pass

                        # Cleanup: avoid stale list being replayed on future turns.
                        try:
                            order_tracker.set_custom_meta(user_id, "price_list_text", "")
                            order_tracker.set_custom_meta(user_id, "price_list_items", [])
                        except Exception:
                            pass

                        try:
                            pid = str(picked.get("product_id") or "").strip()
                            if pid:
                                order_tracker.set_custom_meta(user_id, "active_product_id", pid)
                                order_tracker.update_produit(user_id, pid, source="PRICE_LIST_CHOICE", confidence=0.95)
                        except Exception:
                            pass

                        try:
                            v = str(picked.get("variant") or "").strip()
                            sp = str(picked.get("spec") or "").strip()
                            details = (v + (" " + sp if sp else "")).strip()
                            if details:
                                order_tracker.update_produit_details(user_id, details, source="PRICE_LIST_CHOICE", confidence=0.9)
                        except Exception:
                            pass

                        try:
                            u = str(picked.get("unit") or "").strip().lower()
                            if u:
                                order_tracker.update_quantite(user_id, f"1 {u}", source="PRICE_LIST_CHOICE", confidence=0.9)
                        except Exception:
                            pass

                        try:
                            detected_items_choice = [
                                {
                                    "product_id": str(picked.get("product_id") or "").strip(),
                                    "variant": str(picked.get("variant") or "").strip() or None,
                                    "spec": (str(picked.get("spec") or "").strip() or None),
                                    "unit": str(picked.get("unit") or "").strip() or None,
                                    "qty": 1,
                                    "confidence": 0.95,
                                }
                            ]
                            order_tracker.set_custom_meta(user_id, "detected_items", detected_items_choice)
                        except Exception:
                            pass
            except Exception:
                pass

            # Clarification "ajout ou modification": si on a une question en attente, résoudre ici
            # avant de relancer une détection/LLM. Objectif: éviter fusion/pivot implicite.
            try:
                pending_q = str(order_tracker.get_custom_meta(user_id, "pending_cart_question", default="") or "").strip()
            except Exception:
                pending_q = ""

            try:
                pending_items = order_tracker.get_custom_meta(user_id, "pending_cart_items", default=[])
                pending_items = pending_items if isinstance(pending_items, list) else []
            except Exception:
                pending_items = []

            def _parse_add_or_modify_answer(msg: str) -> str:
                try:
                    s = str(msg or "").strip().lower()
                except Exception:
                    s = ""
                if not s:
                    return ""
                if re.fullmatch(r"\s*(a|1)\s*", s, flags=re.IGNORECASE):
                    return "add"
                if re.fullmatch(r"\s*(b|2)\s*", s, flags=re.IGNORECASE):
                    return "modify"
                if re.search(r"\b(ajout|ajouter|ajoute|en\s*plus|aussi|rajoute|rajouter)\b", s, flags=re.IGNORECASE):
                    return "add"
                if re.search(r"\b(modif|modifier|modification|change|changer|remplace|remplacer|au\s+lieu|plut[oô]t|annule|annuler)\b", s, flags=re.IGNORECASE):
                    return "modify"
                return ""

            def _dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                out: List[Dict[str, Any]] = []
                seen = set()
                for it in (items or []):
                    if not isinstance(it, dict):
                        continue
                    pid = str(it.get("product_id") or "").strip()
                    var = str(it.get("variant") or "").strip()
                    spec = str(it.get("spec") or "").strip()
                    unit = str(it.get("unit") or "").strip()
                    k = (pid.lower(), var.lower(), spec.lower(), unit.lower())
                    if k in seen:
                        continue
                    seen.add(k)
                    out.append(it)
                return out

            try:
                if pending_q == "add_or_modify" and pending_items:
                    choice = _parse_add_or_modify_answer(query)
                    if not choice:
                        processing_time = (time.time() - start_time) * 1000
                        checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                        pending_variant = ""
                        pending_spec = ""
                        try:
                            it0 = pending_items[0] if pending_items else {}
                            if isinstance(it0, dict):
                                pending_variant = str(it0.get("variant") or "").strip()
                                pending_spec = str(it0.get("spec") or "").strip()
                        except Exception:
                            pending_variant = ""
                            pending_spec = ""
                        pending_label = (pending_variant + (" " + pending_spec if pending_spec else "")).strip()
                        forced_q = f"On ajoute {pending_label} au panier ou vous modifiez ?" if pending_label else "On ajoute au panier ou vous modifiez ?"

                        return SimplifiedRAGResult(
                            response=forced_q,
                            confidence=1.0,
                            processing_time_ms=processing_time,
                            checklist_state=checklist.to_string(),
                            next_step=checklist.get_next_step(),
                            detected_location=None,
                            shipping_fee=None,
                            usage=None,
                            prompt_tokens=int(prompt_tokens or 0),
                            completion_tokens=int(completion_tokens or 0),
                            total_tokens=int(total_tokens or 0),
                            cost=float(cost or 0.0),
                            model="python_cart_change_clarify",
                            thinking="",
                        )

                    if choice == "modify":
                        # ── CartManager: resolve pending pivot → REPLACE ──
                        try:
                            self.cart_manager.resolve_pending_pivot(user_id, "REPLACE")
                        except Exception:
                            pass

                        try:
                            order_tracker.set_custom_meta(user_id, "detected_items", pending_items)
                        except Exception:
                            pass

                        try:
                            it0 = pending_items[0] if pending_items else {}
                            pid0 = str(it0.get("product_id") or "").strip()
                            if pid0:
                                order_tracker.set_custom_meta(user_id, "active_product_id", pid0)
                                order_tracker.update_produit(user_id, pid0, source="CART_MODIFY", confidence=0.9)
                        except Exception:
                            pass

                        try:
                            it0 = pending_items[0] if pending_items else {}
                            v0 = str(it0.get("variant") or "").strip()
                            sp0 = str(it0.get("spec") or "").strip()
                            details0 = (v0 + (" " + sp0 if sp0 else "")).strip()
                            if details0:
                                order_tracker.update_produit_details(user_id, details0, source="CART_MODIFY", confidence=0.85)
                        except Exception:
                            pass

                        # Quantité: on efface pour éviter carry-over (elle sera redemandée ou redétectée).
                        try:
                            order_tracker.update_quantite(user_id, "", source="CART_MODIFY", confidence=0.7)
                        except Exception:
                            pass

                    if choice == "add":
                        # ── CartManager: resolve pending pivot → ADD ──
                        try:
                            self.cart_manager.resolve_pending_pivot(user_id, "ADD")
                        except Exception:
                            pass

                        try:
                            existing = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                            existing = existing if isinstance(existing, list) else []
                        except Exception:
                            existing = []
                        try:
                            merged = _dedupe_items((existing or []) + (pending_items or []))
                            order_tracker.set_custom_meta(user_id, "detected_items", merged)
                        except Exception:
                            pass

                    try:
                        order_tracker.set_custom_meta(user_id, "pending_cart_items", [])
                        order_tracker.set_custom_meta(user_id, "pending_cart_question", "")
                        order_tracker.set_custom_meta(user_id, "backend_forced_pivot", False)
                        order_tracker.set_custom_meta(user_id, "backend_forced_pivot_maj_action", "")
                    except Exception:
                        pass

                    processing_time = (time.time() - start_time) * 1000
                    checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                    return SimplifiedRAGResult(
                        response="D'accord.",
                        confidence=1.0,
                        processing_time_ms=processing_time,
                        checklist_state=checklist.to_string(),
                        next_step=checklist.get_next_step(),
                        detected_location=None,
                        shipping_fee=None,
                        usage=None,
                        prompt_tokens=int(prompt_tokens or 0),
                        completion_tokens=int(completion_tokens or 0),
                        total_tokens=int(total_tokens or 0),
                        cost=float(cost or 0.0),
                        model="python_cart_change_apply",
                        thinking="",
                    )
            except Exception:
                pass

            # Pre-LLM: si on détecte clairement un produit depuis le catalogue local, on pré-remplit l'état.
            try:
                container = get_company_catalog_v2(company_id)
                msg_norm = _norm_name_for_id(query)
                detected_pid = ""
                detected_name = ""
                detected_variant = ""

                # Variant hint (company-agnostic but geared for diaper catalog vocab)
                try:
                    ql = str(query or "")
                except Exception:
                    ql = ""

                def _fuzzy_pick_variant(msg: str) -> str:
                    m = _norm_name_for_id(msg)
                    if not m:
                        return ""

                    def _extract_variants_from_catalog(obj: Any) -> List[str]:
                        try:
                            if not isinstance(obj, dict):
                                return []

                            # Primary source of truth: catalog.v keys
                            vtree = obj.get("v") if isinstance(obj.get("v"), dict) else None
                            if isinstance(vtree, dict) and vtree:
                                out = []
                                for k in list(vtree.keys()):
                                    kk = str(k or "").strip()
                                    if kk:
                                        out.append(kk)
                                return out

                            # Fallback: ui_state.variants (may contain trailing spaces)
                            ui = obj.get("ui_state") if isinstance(obj.get("ui_state"), dict) else {}
                            vv = ui.get("variants") if isinstance(ui.get("variants"), list) else []
                            out2 = []
                            for x in vv:
                                xs = str(x or "").strip()
                                if xs:
                                    out2.append(xs)
                            return out2
                        except Exception:
                            return []

                    def _pick_best_variant_from_candidates(candidates: List[str]) -> str:
                        try:
                            cand = [str(x or "").strip() for x in (candidates or []) if str(x or "").strip()]
                            if not cand:
                                return ""

                            # Cheap hints first
                            for v in cand:
                                vn = _norm_name_for_id(v)
                                if vn and re.search(rf"\b{re.escape(vn)}\b", m, flags=re.IGNORECASE):
                                    return v
                        except Exception:
                            pass
                        return ""

                    # --- SCALABLE: catalog-driven variant detection (works for ANY company) ---
                    # Step 1: Try real company variants from the catalogue FIRST.
                    raw_variants: List[str] = []
                    try:
                        raw_variants = _extract_variants_from_catalog(selected_catalog) if isinstance(selected_catalog, dict) else []
                    except Exception:
                        raw_variants = []

                    if raw_variants:
                        # Direct substring match against catalog variant names
                        best_direct = _pick_best_variant_from_candidates(raw_variants)
                        if best_direct:
                            return best_direct

                    # Step 2: Fuzzy match against catalog variants (handles typos)
                    if raw_variants:
                        try:
                            from rapidfuzz import fuzz  # type: ignore
                            best_variant = ""
                            best_score = 0
                            for v in raw_variants:
                                vn = _norm_name_for_id(v)
                                if not vn:
                                    continue
                                score_v = int(fuzz.partial_ratio(m, vn) or 0)
                                if score_v > best_score:
                                    best_score = score_v
                                    best_variant = v
                            if best_variant and best_score >= 85:
                                return best_variant
                        except Exception:
                            pass

                    # Step 3: Legacy hardcoded hints (fallback when no catalog available)
                    # These only fire if the catalog didn't provide variant names.
                    if not raw_variants:
                        try:
                            if re.search(r"\bculott", m, flags=re.IGNORECASE):
                                return "Culotte"
                            if re.search(r"\bpression\b|\bpress\b", m, flags=re.IGNORECASE):
                                return "Pression"
                        except Exception:
                            pass

                    return ""

                detected_variant = _fuzzy_pick_variant(ql)
                print(f"🔍 [PREMATCH_DEBUG] detected_variant='{detected_variant}' | container_type={type(container).__name__} | has_products={isinstance(container, dict) and isinstance(container.get('products'), list) if isinstance(container, dict) else 'N/A'}")

                if isinstance(container, dict) and isinstance(container.get("products"), list):
                    candidates = []
                    for p in (container.get("products") or []):
                        if not isinstance(p, dict):
                            continue
                        pname = str(p.get("product_name") or (p.get("catalog_v2") or {}).get("product_name") or "").strip()
                        if not pname:
                            continue
                        pn_norm = _norm_name_for_id(pname)
                        if pn_norm:
                            candidates.append((pname, pn_norm, p))

                    # Strategy A: strict substring (keeps old behavior)
                    for pname, pn_norm, p in candidates:
                        if pn_norm and pn_norm in msg_norm:
                            detected_name = pname
                            detected_pid = _pick_pid_from_product_entry(p, pname)
                            break

                    # Strategy B: token match with uniqueness (handles queries like "je veux des couches")
                    if not detected_pid and msg_norm:
                        msg_pad = f" {msg_norm} "
                        stop_tokens = {
                            "avec",
                            "sans",
                            "pour",
                            "pack",
                            "lot",
                            "paquet",
                            "carton",
                            "colis",
                            "bebe",
                            "bb",
                        }

                        matched_products = []  # list of (pname, pn_norm, matched_tokens)
                        token_to_products = {}
                        for pname, pn_norm, p in candidates:
                            toks = [t for t in pn_norm.split() if len(t) >= 4 and t not in stop_tokens]
                            hits = [t for t in toks if f" {t} " in msg_pad]
                            if hits:
                                matched_products.append((pname, pn_norm, hits, p))
                                for t in hits:
                                    token_to_products.setdefault(t, set()).add(pname)

                        # If exactly one product matches any significant token => pick it.
                        if len(matched_products) == 1:
                            detected_name = matched_products[0][0]
                            detected_pid = _pick_pid_from_product_entry(matched_products[0][3], detected_name)
                        else:
                            # If a token uniquely identifies a single product => pick it.
                            uniq_tokens = []
                            for t, pset in (token_to_products or {}).items():
                                if isinstance(pset, set) and len(pset) == 1:
                                    uniq_tokens.append(t)
                            # Prefer longer tokens for specificity.
                            uniq_tokens = sorted(set(uniq_tokens), key=lambda x: (-len(x), x))
                            if uniq_tokens:
                                only_name = list(token_to_products[uniq_tokens[0]])[0]
                                detected_name = str(only_name)
                                for pname, pn_norm, hits, p in matched_products:
                                    if pname == detected_name:
                                        detected_pid = _pick_pid_from_product_entry(p, detected_name)
                                        break

                    # Strategy C: variant-only mention on a mono-product container.
                    # If the user says "prix culotte ?" without the product name, but the company has exactly one product,
                    # we can safely select that product_id and carry the variant hint.
                    if (not detected_pid) and detected_variant:
                        try:
                            plist = [pp for pp in (container.get("products") or []) if isinstance(pp, dict)]
                            print(f"🔍 [PREMATCH_DEBUG] Strategy C: detected_variant='{detected_variant}' | plist_len={len(plist)}")
                            if len(plist) == 1:
                                only_p = plist[0]
                                only_name = str(
                                    only_p.get("product_name")
                                    or (only_p.get("catalog_v2") or {}).get("product_name")
                                    or ""
                                ).strip()
                                detected_name = only_name
                                detected_pid = _pick_pid_from_product_entry(only_p, only_name)
                                print(f"🔍 [PREMATCH_DEBUG] Strategy C matched: pid='{detected_pid}' name='{detected_name}'")
                        except Exception as _sc_e:
                            print(f"⚠️ [PREMATCH_DEBUG] Strategy C error: {type(_sc_e).__name__}: {_sc_e}")
                            pass

                    # Strategy D: variant-only mention on a multi-product container.
                    # If multiple products exist, pick the unique product whose catalog.v contains the variant.
                    if (not detected_pid) and detected_variant:
                        try:
                            plist = [pp for pp in (container.get("products") or []) if isinstance(pp, dict)]
                            if len(plist) >= 2:
                                v_norm = _norm_name_for_id(detected_variant)
                                matches = []
                                for pp in plist:
                                    cat = pp.get("catalog_v2") if isinstance(pp.get("catalog_v2"), dict) else None
                                    if not isinstance(cat, dict):
                                        continue
                                    vtree = cat.get("v") if isinstance(cat.get("v"), dict) else None
                                    if not isinstance(vtree, dict) or not vtree:
                                        continue
                                    keys = [str(k or "").strip() for k in list(vtree.keys())]
                                    if any(_norm_name_for_id(k) == v_norm for k in keys if str(k).strip()):
                                        matches.append(pp)

                                if len(matches) == 1:
                                    one = matches[0]
                                    one_name = str(
                                        one.get("product_name")
                                        or (one.get("catalog_v2") or {}).get("product_name")
                                        or (one.get("catalog_v2") or {}).get("name")
                                        or ""
                                    ).strip()
                                    detected_name = one_name
                                    detected_pid = _pick_pid_from_product_entry(one, one_name)
                        except Exception:
                            pass
                elif isinstance(container, dict):
                    pname = str(container.get("product_name") or container.get("name") or "").strip()
                    pn_norm = _norm_name_for_id(pname)
                    if pn_norm and pn_norm in msg_norm:
                        detected_name = pname
                        real_id = str(container.get("product_id") or "").strip()
                        detected_pid = real_id if real_id else _product_id_hash(pname)

                    # Strategy E: mono-product container + variant detected in message
                    # If product_name didn't match but we detected a variant, check vtree
                    if (not detected_pid) and detected_variant and pname:
                        try:
                            vtree = container.get("v") if isinstance(container.get("v"), dict) else None
                            if isinstance(vtree, dict) and vtree:
                                v_norm = _norm_name_for_id(detected_variant)
                                for vk in vtree.keys():
                                    if _norm_name_for_id(str(vk)) == v_norm:
                                        detected_name = pname
                                        real_id = str(container.get("product_id") or "").strip()
                                        detected_pid = real_id if real_id else _product_id_hash(pname)
                                        print(f"🎯 [PREMATCH_DEBUG] Strategy E (mono+variant): pid='{detected_pid}' variant='{detected_variant}'")
                                        break
                        except Exception:
                            pass

                if detected_pid:
                    if prev_product_before_llm and (str(prev_product_before_llm).strip() != detected_pid):
                        try:
                            order_tracker.update_produit_details(user_id, "", source="PYTHON_PREMATCH_RESET", confidence=0.9)
                        except Exception:
                            pass
                        try:
                            order_tracker.update_quantite(user_id, "", source="PYTHON_PREMATCH_RESET", confidence=0.9)
                        except Exception:
                            pass
                        try:
                            order_tracker.set_custom_meta(user_id, "detected_items", [])
                            order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                        except Exception:
                            pass

                    if (not prev_product_before_llm) or (str(prev_product_before_llm).strip() != detected_pid):
                        order_tracker.update_produit(user_id, detected_pid, source="PYTHON_PREMATCH", confidence=0.9)

                    order_tracker.set_custom_meta(user_id, "active_product_id", detected_pid)
                    order_tracker.set_custom_meta(user_id, "active_product_label", detected_name)
                    print(f"✅ [PYTHON_PREMATCH] product_id={detected_pid} product='{detected_name}'")

                    # If this is a price intent and we have a clear variant, short-circuit the LLM and send price list.
                    # This is a robustness fallback when the prompt doesn't emit <tool_call>.
                    try:
                        if _is_price_intent(query):
                            if detected_variant:
                                list_text, list_items = _generate_price_list_for_tool_call(
                                    company_id_val=company_id,
                                    product_id_val=detected_pid,
                                    variant_val=detected_variant,
                                    spec_val=None,
                                )
                            else:
                                list_text, list_items = _generate_price_table_for_product(
                                    company_id_val=company_id,
                                    product_id_val=detected_pid,
                                )

                            if list_text and list_items:
                                try:
                                    order_tracker.set_custom_meta(user_id, "price_list_text", list_text)
                                    order_tracker.set_custom_meta(user_id, "price_list_items", list_items)
                                    order_tracker.set_flag(user_id, "awaiting_price_choice", True)
                                except Exception:
                                    pass

                                processing_time = (time.time() - start_time) * 1000
                                checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                                return SimplifiedRAGResult(
                                    response=list_text,
                                    confidence=1.0,
                                    processing_time_ms=processing_time,
                                    checklist_state=checklist.to_string(),
                                    next_step=checklist.get_next_step(),
                                    detected_location=None,
                                    shipping_fee=None,
                                    usage=None,
                                    prompt_tokens=0,
                                    completion_tokens=0,
                                    total_tokens=0,
                                    cost=0.0,
                                    model="python_price_list_short_circuit",
                                    thinking="",
                                )
                    except Exception:
                        pass
            except Exception as _prem_e:
                print(f"⚠️ [PYTHON_PREMATCH] error: {type(_prem_e).__name__}: {_prem_e}")

            # 1. Initialisation LLM si nécessaire
            if self.llm_client is None:
                await self.initialize()
            
            # 2. Collecte contexte dynamique en parallèle
            print("📦 [CONTEXT] Collecte contexte dynamique...")
            dynamic_context = await self.context_injector.collect_dynamic_context(
                query=query,
                user_id=user_id,
                company_id=company_id
            )

            # Si on attend un choix de prix et que Python n'a pas pu parser la réponse du client,
            # on injecte la dernière liste envoyée dans l'historique pour que le LLM puisse choisir.
            try:
                if pending_price_list_text:
                    prev_hist = str(dynamic_context.get("conversation_history") or "")
                    if pending_price_list_text not in prev_hist:
                        dyn_tail = ("\n\nASSISTANT:\n" + pending_price_list_text.strip()).strip()
                        dynamic_context["conversation_history"] = (prev_hist + dyn_tail).strip() if prev_hist.strip() else dyn_tail
            except Exception:
                pass

            # Fallback persistance livraison (zone/frais) :
            # si le message courant ne contient pas la zone, on réutilise la dernière zone connue.
            try:
                if (not dynamic_context.get("detected_location")) and int(current_turn or 0) > 1:
                    slot_meta = order_tracker.get_slot_meta(user_id)
                    zone_meta = None
                    try:
                        zone_meta = (slot_meta.get("slot_meta") or {}).get("ZONE")
                    except Exception:
                        zone_meta = None

                    zone_source = str((zone_meta or {}).get("source") or "").strip().upper()
                    zone_conf = (zone_meta or {}).get("confidence")
                    try:
                        zone_conf_f = float(zone_conf) if zone_conf is not None else 0.0
                    except Exception:
                        zone_conf_f = 0.0

                    if zone_source and (zone_source not in {"CONTEXT_INFERRED", "UNKNOWN"}) and zone_conf_f >= 0.8:
                        st_prev = order_tracker.get_state(user_id)
                        prev_zone = str(getattr(st_prev, "zone", "") or "").strip()
                        if prev_zone:
                            z_name, z_info = self.context_injector.resolve_zone_info(prev_zone)
                            if z_name:
                                dynamic_context["detected_location"] = z_name
                            if z_info:
                                fee = z_info.get("fee")
                                if isinstance(fee, int):
                                    dynamic_context["shipping_fee"] = f"{fee} FCFA"
                                else:
                                    dynamic_context["shipping_fee"] = str(fee)
                                dynamic_context["delivery_time"] = z_info.get("delay")
            except Exception as e:
                print(f"⚠️ [CONTEXT] Fallback zone/frais: {type(e).__name__}: {e}")

            # 2.b Vision (Gemini ONLY) si images[] présent
            # NOTE: le chemin Simplified RAG ne doit plus dépendre d'OCR legacy.
            vision_summary = ""
            payment_verdict_line = ""
            has_image = bool(images and len(images) > 0)
            if has_image:
                try:
                    analyze_product_with_gemini = None
                    try:
                        from Zeta_AI.vision_gemini import analyze_product_with_gemini as _analyze_product_with_gemini

                        analyze_product_with_gemini = _analyze_product_with_gemini
                        print("🖼️ [VISION][GEMINI] import=Zeta_AI.vision_gemini")
                    except Exception as _imp_e1:
                        try:
                            from vision_gemini import analyze_product_with_gemini as _analyze_product_with_gemini

                            analyze_product_with_gemini = _analyze_product_with_gemini
                            print("🖼️ [VISION][GEMINI] import=vision_gemini")
                        except Exception as _imp_e2:
                            raise ModuleNotFoundError(
                                f"vision_gemini import failed: {type(_imp_e1).__name__}: {_imp_e1} | {type(_imp_e2).__name__}: {_imp_e2}"
                            )

                    image_url = str((images or [""])[0] or "").strip()
                    if image_url:
                        default_company_phone = (os.getenv("WAVE_PHONE") or os.getenv("COMPANY_WAVE_PHONE") or "0787360757").strip()
                        try:
                            default_required_amount = int(str(os.getenv("EXPECTED_DEPOSIT") or "2000").strip())
                        except Exception:
                            default_required_amount = 2000

                        print(f"🖼️ [VISION][GEMINI] start | image_url={image_url[:120]}... | phone={default_company_phone} | required={default_required_amount}")
                        gemini_result, gemini_meta = await analyze_product_with_gemini(
                            image_url=image_url,
                            user_message=query,
                            company_phone=default_company_phone,
                            required_amount=default_required_amount,
                        )

                        # Logs robustesse (raw + parsed)
                        try:
                            raw_txt = str((gemini_result or {}).get("raw") or "")
                            raw_short = raw_txt[:600] + ("..." if len(raw_txt) > 600 else "")
                            meta_short = {}
                            if isinstance(gemini_meta, dict):
                                for k in ["model", "provider", "usage", "prompt_tokens", "completion_tokens", "total_tokens", "total_cost"]:
                                    if k in gemini_meta:
                                        meta_short[k] = gemini_meta.get(k)
                            print(f"🖼️ [VISION][GEMINI] meta={json.dumps(meta_short, ensure_ascii=False)}")
                            if raw_short:
                                print(f"🖼️ [VISION][GEMINI] raw(600)=\n{raw_short}")
                        except Exception as _log_e:
                            print(f"🖼️ [VISION][GEMINI] log_error: {type(_log_e).__name__}: {_log_e}")

                        # Normaliser vers 2 sorties: produit + transactions
                        detected_objects: List[Dict[str, Any]] = []
                        filtered_transactions: List[Dict[str, Any]] = []

                        # Produit
                        try:
                            product_name = str((gemini_result or {}).get("name") or "").strip()
                            conf = (gemini_result or {}).get("confidence")
                            is_product_image = (gemini_result or {}).get("is_product_image")
                            if isinstance(is_product_image, bool) and is_product_image and product_name:
                                try:
                                    conf_f = float(conf) if conf is not None else 0.0
                                except Exception:
                                    conf_f = 0.0
                                detected_objects.append({"label": product_name, "confidence": conf_f, "source": "gemini"})
                                order_tracker.update_produit(user_id, product_name, source="VISION_GEMINI", confidence=max(0.0, min(1.0, conf_f)))
                                print(f"📦 [VISION][GEMINI] produit='{product_name}' conf={conf}")
                        except Exception as _prod_e:
                            print(f"🖼️ [VISION][GEMINI] product_parse_error: {type(_prod_e).__name__}: {_prod_e}")

                        # Paiement
                        try:
                            payment = (gemini_result or {}).get("payment")
                            if isinstance(payment, dict):
                                error_code = str(payment.get("error_code") or "").strip() or None
                                amount = payment.get("amount")
                                try:
                                    amount_i = int(float(amount)) if amount is not None else 0
                                except Exception:
                                    amount_i = 0

                                if error_code:
                                    print(f"💳 [VISION][GEMINI] payment_error_code={error_code}")

                                    # Cas spécial: montant insuffisant = on a un montant détecté, donc c'est INSUFFICIENT (pas REFUSED)
                                    if str(error_code).upper() == "MONTANT_INSUFFISANT" and amount_i > 0:
                                        diff_i = amount_i - int(default_required_amount or 0)
                                        missing_i = abs(diff_i) if diff_i < 0 else 0
                                        payment_verdict_line = (
                                            "PAYMENT_VERDICT"
                                            f"|status=INSUFFICIENT"
                                            f"|received={amount_i}"
                                            f"|required={default_required_amount}"
                                            f"|diff={diff_i}"
                                            f"|missing={missing_i}"
                                            f"|message=GEMINI_ERROR:{error_code}"
                                        )
                                        # Persister un état explicite (INSUFFICIENT)
                                        try:
                                            order_tracker.update_paiement(
                                                user_id,
                                                f"insuffisant_{amount_i}F",
                                                source="VERDICT",
                                                confidence=0.95,
                                            )
                                        except Exception:
                                            pass
                                    else:
                                        filtered_transactions.append({"amount": 0, "currency": "FCFA", "error_message": f"GEMINI_ERROR:{error_code}"})
                                        payment_verdict_line = (
                                            "PAYMENT_VERDICT"
                                            f"|status=REFUSED"
                                            f"|received=0"
                                            f"|required={default_required_amount}"
                                            f"|diff={-default_required_amount}"
                                            f"|missing={default_required_amount}"
                                            f"|message=GEMINI_ERROR:{error_code}"
                                        )

                                        # Persister un état explicite (REFUSED) pour transparence
                                        try:
                                            order_tracker.update_paiement(
                                                user_id,
                                                f"refusé_GEMINI_ERROR:{error_code}",
                                                source="VERDICT",
                                                confidence=0.95,
                                            )
                                        except Exception:
                                            pass

                                    # NV3: tracer la source même si on ne persiste pas un paiement valide
                                    try:
                                        order_tracker.set_slot_meta(user_id, "PAIEMENT", source="VISION_GEMINI", confidence=0.8)
                                    except Exception:
                                        pass
                                elif amount_i > 0:
                                    filtered_transactions.append({"amount": amount_i, "currency": str(payment.get("currency") or "FCFA"), "reference": str(payment.get("reference") or "")})
                                    print(f"💳 [VISION][GEMINI] payment_amount={amount_i} {payment.get('currency') or 'FCFA'}")

                                    try:
                                        order_tracker.set_slot_meta(user_id, "PAIEMENT", source="VISION_GEMINI", confidence=0.9)
                                    except Exception:
                                        pass

                                try:
                                    if filtered_transactions and not error_code:
                                        validation = validate_payment_cumulative(
                                            current_transactions=filtered_transactions,
                                            conversation_history=str(dynamic_context.get('conversation_history') or ''),
                                            required_amount=default_required_amount,
                                        )
                                        payment_verdict_line = format_payment_for_prompt(validation)
                                        if validation and validation.get("status") == "VALID":
                                            total_received = int(validation.get("total_received") or 0)
                                            order_tracker.update_paiement(user_id, f"validé_{total_received}F", source="VERDICT", confidence=1.0)
                                            print(f"💾 [ORDER_STATE][PAYMENT] saved validé_{total_received}F")
                                        else:
                                            try:
                                                st = str(validation.get("status") or "").upper()
                                                total_received = int(validation.get("total_received") or 0)
                                            except Exception:
                                                st = ""
                                                total_received = 0
                                            if st:
                                                # Persister les états non-validants
                                                # - INSUFFICIENT -> insuffisant_XXXXF
                                                # - REFUSED -> refusé
                                                # - NONE -> (ne rien persister)
                                                try:
                                                    if st == "INSUFFICIENT" and total_received > 0:
                                                        order_tracker.update_paiement(
                                                            user_id,
                                                            f"insuffisant_{total_received}F",
                                                            source="VERDICT",
                                                            confidence=0.95,
                                                        )
                                                        print(f"💾 [ORDER_STATE][PAYMENT] saved insuffisant_{total_received}F")
                                                    elif st == "REFUSED":
                                                        # Conserver une valeur courte et stable
                                                        order_tracker.update_paiement(
                                                            user_id,
                                                            "refusé",
                                                            source="VERDICT",
                                                            confidence=0.95,
                                                        )
                                                        print("💾 [ORDER_STATE][PAYMENT] saved refusé")
                                                    else:
                                                        print(
                                                            f"💾 [ORDER_STATE][PAYMENT] not saved ({st} received={total_received} required={default_required_amount})"
                                                        )
                                                except Exception as _st_save_e:
                                                    print(f"💾 [ORDER_STATE][PAYMENT] state_save_error: {type(_st_save_e).__name__}: {_st_save_e}")
                                except Exception as _pv_e:
                                    print(f"🖼️ [VISION][GEMINI] payment_verdict_error: {type(_pv_e).__name__}: {_pv_e}")
                        except Exception as _pay_e:
                            print(f"🖼️ [VISION][GEMINI] payment_parse_error: {type(_pay_e).__name__}: {_pay_e}")

                        # Injecter un résumé compact dans le prompt (même si LLM n'a pas "vu" l'image)
                        try:
                            prod_s = detected_objects[0]["label"] if detected_objects else "∅"
                            pay_s = "∅"
                            if filtered_transactions:
                                t0 = filtered_transactions[0]
                                if t0.get("amount"):
                                    pay_s = f"{t0.get('amount')}F"
                                elif t0.get("error_message"):
                                    pay_s = str(t0.get("error_message"))
                            vision_summary = f"VISION_GEMINI: produit={prod_s} | paiement={pay_s}"
                            print(f"🧩 [VISION][GEMINI] summary='{vision_summary}'")
                        except Exception:
                            vision_summary = ""
                except Exception as e:
                    print(f"🖼️ [VISION][GEMINI] fatal_error: {type(e).__name__}: {e}")

            # Mise à jour OrderStateTracker via signaux déterministes (sans RAG retrieval)
            try:
                detected_location = dynamic_context.get('detected_location')
                if detected_location:
                    order_tracker.update_zone(user_id, str(detected_location), source="CONTEXT_INFERRED", confidence=0.7)
            except Exception as e:
                print(f"⚠️ [ORDER_STATE] Erreur update zone: {e}")

            phone_match = None
            try:
                msg_lower = str(query or "").lower()

                # Téléphone CI (heuristique simple)
                # On persiste les numéros au format 0XXXXXXXXX (10 chiffres), y compris si fournis en +225.
                normalized_phone = ""
                try:
                    from FIX_CONTEXT_LOSS_COMPLETE import validate_phone_ci

                    v = validate_phone_ci(str(query or ""))
                    if isinstance(v, dict) and v.get("valid") and v.get("normalized"):
                        normalized_phone = str(v.get("normalized") or "").strip()
                except Exception:
                    normalized_phone = ""

                if normalized_phone and re.fullmatch(r"0\d{9}", normalized_phone):
                    phone_match = True
                    order_tracker.update_numero(user_id, normalized_phone, source="USER_TEXT", confidence=1.0)
                else:
                    phone_match = re.search(r"\b(0\d{9})\b", str(query or ""))
                    if phone_match:
                        order_tracker.update_numero(user_id, phone_match.group(1), source="USER_TEXT", confidence=1.0)

                # Quantité (carton/paquets) - persistance (slot obligatoire)
                qty_match = re.search(
                    r"\b(\d+)\s*(cartons?|carton|paquets?|packs?|unit[ée]s?)\b",
                    str(query or ""),
                    flags=re.IGNORECASE,
                )
                if qty_match:
                    q = str(query or "")
                    q_low = q.lower()

                    # On ne valide pas une quantité si c'est une question/hypothèse (devis)
                    is_interrogative = (
                        "?" in q
                        or "ça fait combien" in q_low
                        or "ca fait combien" in q_low
                        or q_low.strip().startswith("et si")
                        or q_low.strip().startswith("si je")
                        or "combien" in q_low
                    )

                    # On valide uniquement si intention d'achat explicite
                    has_commit_verb = bool(
                        re.search(
                            r"\b(je\s+(prends|veux|commande|confirme|ach[eè]te)|mets\s*moi|met\s*moi|envoie|envoyez|ok\s+pour|c['’]?est\s+bon\s+pour|on\s+part\s+sur)\b",
                            q_low,
                            flags=re.IGNORECASE,
                        )
                    )

                    if (not is_interrogative) and has_commit_verb:
                        n = qty_match.group(1)
                        u = qty_match.group(2)
                        order_tracker.update_quantite(user_id, f"{n} {u}".strip(), source="USER_TEXT", confidence=1.0)
            except Exception as e:
                print(f"⚠️ [ORDER_STATE] Erreur update téléphone/paiement: {e}")

            phone_verdict_line = ""
            location_verdict_line = ""
            validation_errors_block = ""

            def _kv_get(line: str) -> Dict[str, str]:
                out: Dict[str, str] = {}
                try:
                    for part in str(line or "").split("|"):
                        p = part.strip()
                        if not p:
                            continue
                        if "=" in p:
                            k, v = p.split("=", 1)
                            out[k.strip().lower()] = v.strip()
                except Exception:
                    return {}
                return out

            def _xml_escape(s: str) -> str:
                s = str(s or "")
                return (
                    s.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )

            def _build_validation_errors_xml(payment_line: str, phone_issue: Dict[str, str]) -> str:
                blocks: List[str] = []

                # Paiement
                pv = _kv_get(payment_line)
                pv_status = (pv.get("status") or "").strip().upper()
                if pv_status in {"INSUFFICIENT", "REFUSED"}:
                    detected_amount = (pv.get("received") or "").strip()
                    required_amount = (pv.get("required") or "").strip()
                    missing_amount = (pv.get("missing") or "").strip()
                    message = (pv.get("message") or "").strip() or pv_status
                    blocks.append(
                        "  <PAIEMENT>\n"
                        f"    <status>{_xml_escape(pv_status)}</status>\n"
                        f"    <detected_amount>{_xml_escape((detected_amount + 'F') if detected_amount and not detected_amount.endswith('F') else detected_amount)}</detected_amount>\n"
                        f"    <required_amount>{_xml_escape((required_amount + 'F') if required_amount and not required_amount.endswith('F') else required_amount)}</required_amount>\n"
                        f"    <missing_amount>{_xml_escape((missing_amount + 'F') if missing_amount and not missing_amount.endswith('F') else missing_amount)}</missing_amount>\n"
                        f"    <message>{_xml_escape(message)}</message>\n"
                        "  </PAIEMENT>"
                    )

                # Téléphone
                if phone_issue:
                    status = str(phone_issue.get("status") or "").strip()
                    detected_value = str(phone_issue.get("detected_value") or "").strip()
                    expected_format = str(phone_issue.get("expected_format") or "").strip()
                    message = str(phone_issue.get("message") or "").strip()
                    blocks.append(
                        "  <TÉLÉPHONE>\n"
                        f"    <status>{_xml_escape(status)}</status>\n"
                        f"    <detected_value>{_xml_escape(detected_value)}</detected_value>\n"
                        f"    <expected_format>{_xml_escape(expected_format)}</expected_format>\n"
                        f"    <message>{_xml_escape(message)}</message>\n"
                        "  </TÉLÉPHONE>"
                    )

                return "\n".join(blocks)

            def _build_items_validation_errors_xml(company_id: str, user_id: str) -> str:
                """Build deterministic validation error blocks for invalid/unconfirmed detected_items.

                Purpose: when Python rejects unit/qty, the LLM must recadrer with catalogue choices
                instead of validating a broken order.
                """
                try:
                    v = order_tracker.get_custom_meta(user_id, "detected_items_validation", default={})
                except Exception:
                    v = {}
                if not isinstance(v, dict):
                    return ""

                reasons = v.get("reasons") if isinstance(v.get("reasons"), list) else []
                invalid = v.get("invalid") if isinstance(v.get("invalid"), list) else []
                unconfirmed = v.get("unconfirmed") if isinstance(v.get("unconfirmed"), list) else []

                if ("invalid_items" not in reasons) and ("unconfirmed_items" not in reasons):
                    return ""

                def _escape(s: str) -> str:
                    return _xml_escape(s)

                def _fmt_units(units: List[str]) -> str:
                    try:
                        uniq = [u for u in sorted({str(x).strip() for x in (units or []) if str(x).strip()})]
                        return ", ".join(uniq)
                    except Exception:
                        return ""

                # pick a target item (first invalid, else first unconfirmed)
                target_pack = None
                if invalid:
                    target_pack = invalid[0] if isinstance(invalid[0], dict) else None
                elif unconfirmed:
                    target_pack = unconfirmed[0] if isinstance(unconfirmed[0], dict) else None

                target_item = target_pack.get("item") if isinstance(target_pack, dict) else None
                target_reason = str(target_pack.get("reason") or "").strip().lower() if isinstance(target_pack, dict) else ""
                if not isinstance(target_item, dict):
                    return ""

                # resolve allowed units from catalog_v2 vtree for this product/variant/spec
                allowed_units: List[str] = []
                try:
                    catalog_v2 = get_company_catalog_v2(company_id)
                except Exception:
                    catalog_v2 = None

                selected_catalog = None
                try:
                    plist = catalog_v2.get("products") if isinstance(catalog_v2, dict) else None
                    if isinstance(plist, list):
                        pid = str(target_item.get("product_id") or "").strip()
                        if pid:
                            selected_catalog = get_company_product_catalog_v2(company_id, pid)
                        else:
                            only_one = [p for p in plist if isinstance(p, dict) and isinstance(p.get("catalog_v2"), dict)]
                            if len(only_one) == 1:
                                selected_catalog = only_one[0].get("catalog_v2")
                    else:
                        selected_catalog = catalog_v2
                except Exception:
                    selected_catalog = catalog_v2

                try:
                    vtree = selected_catalog.get("v") if isinstance(selected_catalog, dict) else None
                    if isinstance(vtree, dict):
                        variant = str(target_item.get("variant") or target_item.get("product") or "").strip()
                        spec = str(target_item.get("specs") or target_item.get("spec") or "").strip()

                        node = vtree.get(variant) if variant else None
                        if isinstance(node, dict):
                            node_s = node.get("s")
                            if isinstance(node_s, dict) and node_s and spec:
                                sub = node_s.get(spec)
                                if isinstance(sub, dict) and isinstance(sub.get("u"), dict):
                                    allowed_units = [str(k) for k in sub.get("u").keys() if str(k).strip()]
                            if not allowed_units and isinstance(node.get("u"), dict):
                                allowed_units = [str(k) for k in node.get("u").keys() if str(k).strip()]
                except Exception:
                    allowed_units = []

                unit_got = str(target_item.get("unit") or "").strip()
                qty_got = target_item.get("qty")
                fmt = _fmt_units(allowed_units)

                # Build the XML block
                msg = ""
                if target_reason == "bad_unit":
                    if fmt:
                        msg = f"Unité '{unit_got or '∅'}' non reconnue. Formats dispo: {fmt}."
                    else:
                        msg = f"Unité '{unit_got or '∅'}' non reconnue."
                elif target_reason in {"qty_null", "qty_invalid"}:
                    if fmt:
                        msg = f"Quantité invalide/ambiguë. Choisis un format parmi: {fmt}."
                    else:
                        msg = "Quantité invalide/ambiguë."
                else:
                    if fmt:
                        msg = f"Panier à confirmer/corriger. Formats dispo: {fmt}."
                    else:
                        msg = "Panier à confirmer/corriger."

                pid_dbg = str(target_item.get("product_id") or "").strip()
                var_dbg = str(target_item.get("variant") or "").strip()
                spec_dbg = str(target_item.get("specs") or target_item.get("spec") or "").strip()

                return (
                    "  <PANIER>\n"
                    f"    <status>INVALID</status>\n"
                    f"    <product_id>{_escape(pid_dbg)}</product_id>\n"
                    f"    <variant>{_escape(var_dbg)}</variant>\n"
                    f"    <specs>{_escape(spec_dbg)}</specs>\n"
                    f"    <unit_recue>{_escape(unit_got)}</unit_recue>\n"
                    f"    <qty_recue>{_escape(str(qty_got) if qty_got is not None else '')}</qty_recue>\n"
                    f"    <formats_disponibles>{_escape(fmt)}</formats_disponibles>\n"
                    f"    <message>{_escape(msg)}</message>\n"
                    "  </PANIER>"
                )

            # Détecter un téléphone invalide (texte contient des chiffres mais pas 0XXXXXXXXX)
            phone_issue: Dict[str, str] = {}
            try:
                raw_q = str(query or "")
                digits = re.sub(r"\D+", "", raw_q)
                has_phone_like = bool(digits) and ("tel" in raw_q.lower() or "num" in raw_q.lower() or len(digits) >= 6)
                if has_phone_like and not phone_match:
                    # Exemple: 070000, +225..., 7 chiffres, etc.
                    # On renvoie une erreur de format, sans persister.
                    phone_issue = {
                        "status": "INVALID_FORMAT",
                        "detected_value": digits[:16],
                        "expected_format": "10 chiffres (07XXXXXXXX ou 01XXXXXXXX)",
                        "message": "Numéro incomplet ou format non reconnu",
                    }
            except Exception:
                phone_issue = {}

            try:
                state = order_tracker.get_state(user_id)
                numero = str(getattr(state, "numero", "") or "").strip()
                zone = str(getattr(state, "zone", "") or "").strip()
                quantite = str(getattr(state, "quantite", "") or "").strip()

                if numero:
                    phone_verdict_line = f"PHONE_VERDICT|status=OK|value={numero}"
                else:
                    if phone_issue:
                        phone_verdict_line = f"PHONE_VERDICT|status=INVALID_FORMAT|value={phone_issue.get('detected_value','')}|expected={phone_issue.get('expected_format','')}|message={phone_issue.get('message','')}"
                    else:
                        phone_verdict_line = "PHONE_VERDICT|status=MISSING"

                if zone and zone != "Non détecté":
                    location_verdict_line = f"LOCATION_VERDICT: [PRESENT] value={zone}"
                else:
                    location_verdict_line = "LOCATION_VERDICT: [MISSING]"

                # Quantité verdict simple (présence/absence) - pour guider Jessica
                quantite_verdict_line = ""
                if quantite:
                    quantite_verdict_line = f"QUANTITE_VERDICT: [PRESENT] value={quantite}"
                else:
                    quantite_verdict_line = "QUANTITE_VERDICT: [MISSING]"

                # Construire validation_errors_block à partir des signaux déterministes
                try:
                    base_err = _build_validation_errors_xml(payment_verdict_line, phone_issue)
                    items_err = _build_items_validation_errors_xml(company_id, user_id)
                    validation_errors_block = "\n".join([b for b in [base_err, items_err] if str(b or "").strip()])
                except Exception:
                    validation_errors_block = ""
            except Exception as e:
                print(f"⚠️ [CTX_VERDICTS] state_error: {type(e).__name__}: {e}")
            
            print(f"✅ [CONTEXT] Zone: {dynamic_context.get('detected_location', 'N/A')}")
            print(f"✅ [CONTEXT] Frais: {dynamic_context.get('shipping_fee', 'N/A')}")

            # 2.c Instruction immédiate (Python -> Jessica)
            instruction_block = ""
            try:
                instruction_mode = (os.getenv("INSTRUCTION_MODE") or "rigid").strip().lower()

                # Mode d'ablation: couper entièrement l'instruction_immediate
                if instruction_mode in {"off", "none", "0", "false"}:
                    instruction_block = ""
                    raise RuntimeError("INSTRUCTION_MODE_OFF")

                st_now = order_tracker.get_state(user_id)
                next_field = order_tracker.get_next_required_field(user_id, current_turn=current_turn)

                slot_meta_bundle = None
                try:
                    slot_meta_bundle = order_tracker.get_slot_meta(user_id)
                except Exception:
                    slot_meta_bundle = {"turn": current_turn, "ask_counts": {}, "last_asked": {}, "slot_meta": {}}

                msg_lower = str(query or "").lower()

                def _detect_user_question(q: str) -> Dict[str, str]:
                    qt = str(q or "").strip()
                    ql = qt.lower()
                    is_question = (
                        ("?" in qt)
                        or ("combien" in ql)
                        or ("prix" in ql)
                        or ("ça fait combien" in ql)
                        or ("ca fait combien" in ql)
                        or ("livraison" in ql)
                        or ("livrez" in ql)
                        or ("delai" in ql)
                        or ("délai" in ql)
                    )

                    topic = ""
                    if any(k in ql for k in ["livraison", "livrez", "livrer", "frais", "commune", "quartier", "adresse"]):
                        topic = "DELIVERY"
                    elif any(k in ql for k in ["combien", "prix", "tarif", "coût", "cout", "fcfa"]):
                        topic = "PRICE"
                    elif any(k in ql for k in ["dispo", "disponible", "stock"]):
                        topic = "AVAILABILITY"
                    elif any(k in ql for k in ["délai", "delai", "quand", "heure", "aujourd", "demain"]):
                        topic = "DELIVERY_TIME"
                    return {
                        "is_question": "true" if is_question else "false",
                        "topic": topic,
                        "text": qt,
                    }

                def _infer_intent(q: str) -> Dict[str, str]:
                    qt = str(q or "").strip()
                    ql = qt.lower()

                    is_hypo = bool(
                        ("si je" in ql)
                        or ("et si" in ql)
                        or ("suppos" in ql)
                        or ("imagin" in ql)
                    )
                    has_commit = bool(
                        re.search(
                            r"\b(je\s+(prends|veux|commande|confirme|ach[eè]te)|on\s+part\s+sur|mets?\s*moi|mettez\s*moi|ok\s+pour|c['’]?est\s+bon\s+pour|envoie|envoyez)\b",
                            ql,
                            flags=re.IGNORECASE,
                        )
                    )

                    user_q = _detect_user_question(qt)
                    topic = user_q.get("topic") or ""

                    intent = ""
                    reformulation = ""

                    if user_q.get("is_question") == "true" and topic == "DELIVERY":
                        intent = "ASK_DELIVERY_INFO"
                        reformulation = "Le client demande les informations de livraison."
                    elif user_q.get("is_question") == "true" and topic in {"PRICE", "AVAILABILITY"}:
                        intent = "ASK_PRODUCT_INFO"
                        reformulation = "Le client demande une information sur le produit (prix/disponibilité)."
                    elif user_q.get("is_question") == "true" and topic == "DELIVERY_TIME":
                        intent = "ASK_DELIVERY_TIME"
                        reformulation = "Le client demande le délai de livraison."
                    elif any(k in ql for k in ["paiement", "payer", "paye", "paye", "acompte", "wave", "transfert"]):
                        intent = "PAYMENT_DISCUSSION"
                        reformulation = "Le client parle du paiement (intention ou preuve)."
                    elif has_commit:
                        intent = "COMMIT_ORDER"
                        reformulation = "Le client exprime un engagement d'achat/commande."
                    else:
                        intent = "CONTINUE_ORDER"
                        reformulation = "Le client continue la conversation de commande."

                    certainty = "PROBABLE"
                    if user_q.get("is_question") == "true":
                        certainty = "CERTAIN"
                    elif is_hypo:
                        certainty = "HYPOTHESE"
                    elif has_commit:
                        certainty = "CERTAIN"

                    return {
                        "intent": intent,
                        "certainty": certainty,
                        "reformulation": reformulation,
                        "user_question_is_question": user_q.get("is_question") or "false",
                        "user_question_topic": topic,
                        "user_question_text": user_q.get("text") or "",
                    }

                def _build_historique_compact(
                    ask_counts: Dict[str, Any],
                    last_asked: Dict[str, Any],
                    turn: int,
                ) -> Dict[str, str]:
                    cooldowns = {
                        "PRODUIT": 2,
                        "SPECS": 2,
                        "QUANTITE": 1,
                        "ZONE": 1,
                        "NUMERO": 2,
                        "PAIEMENT": 2,
                    }

                    def _norm(k: str) -> str:
                        kk = str(k or "").upper().strip()
                        if kk in {"TELEPHONE", "TÉLÉPHONE", "TEL", "NUMERO", "NUMÉRO"}:
                            return "NUMERO"
                        if kk in {"QUANTITE", "QUANTITÉ"}:
                            return "QUANTITE"
                        return kk

                    # Normaliser les dictionnaires entrants pour consolider les variantes (accents / legacy)
                    norm_ask_counts: Dict[str, int] = {}
                    for k, v in (ask_counts or {}).items():
                        try:
                            nk = _norm(k)
                            norm_ask_counts[nk] = norm_ask_counts.get(nk, 0) + int(v or 0)
                        except Exception:
                            continue

                    norm_last_asked: Dict[str, int] = {}
                    for k, v in (last_asked or {}).items():
                        try:
                            nk = _norm(k)
                            norm_last_asked[nk] = max(norm_last_asked.get(nk, 0), int(v or 0))
                        except Exception:
                            continue

                    asked_sorted = []
                    for k, v in (norm_last_asked or {}).items():
                        try:
                            asked_sorted.append((_norm(k), int(v or 0)))
                        except Exception:
                            continue
                    asked_sorted.sort(key=lambda x: x[1], reverse=True)
                    asked_sorted = asked_sorted[:6]

                    recent_xml = "\n".join(
                        [
                            f"      <q slot=\"{k}\" turn=\"{t}\" asked=\"{int((norm_ask_counts or {}).get(k) or 0)}\"/>"
                            for (k, t) in asked_sorted
                        ]
                    )
                    if recent_xml:
                        recent_xml = "    <recent_questions>\n" + recent_xml + "\n    </recent_questions>"
                    else:
                        recent_xml = "    <recent_questions></recent_questions>"

                    bans = []
                    for slot, cd in cooldowns.items():
                        last_t = None
                        try:
                            last_t = int((norm_last_asked or {}).get(slot) or 0)
                        except Exception:
                            last_t = 0
                        delta = int(turn or 0) - int(last_t or 0)
                        if int(cd or 0) > 0 and int(last_t or 0) > 0 and delta < int(cd or 0):
                            bans.append((slot, int(cd) - delta))

                    bans_xml = "\n".join([f"      <ban slot=\"{s}\" remaining=\"{rem}\"/>" for (s, rem) in bans])
                    if bans_xml:
                        bans_xml = "    <cooldown_bans>\n" + bans_xml + "\n    </cooldown_bans>"
                    else:
                        bans_xml = "    <cooldown_bans></cooldown_bans>"

                    return {"recent": recent_xml, "bans": bans_xml}

                def _is_triggered() -> bool:
                    # Triggers visés: paiement (verdict), tel (regex), zone (regex)
                    if bool(payment_verdict_line):
                        return True
                    # Intention paiement sans preuve (ex: "je vais faire l'acompte")
                    if any(k in msg_lower for k in ["acompte", "wave", "payer", "payé", "paye", "paiement", "transfert", "envoyé", "envoye"]):
                        return True
                    if bool(re.search(r"\b(0\d{9})\b", str(query or ""))):
                        return True
                    if bool(dynamic_context.get("detected_location")):
                        return True
                    return False

                triggered = _is_triggered()

                def _next_question_for(field: Optional[str]) -> str:
                    f = str(field or "").upper().strip()
                    if f == "PRODUIT":
                        return "Tu veux quel produit exactement (marque/modèle) stp ?"
                    if f == "SPECS":
                        return "Tu veux quelle taille et quel type exactement (ex: T3, T4 / pants ou adhésive) ?"
                    if f == "QUANTITÉ":
                        return "Tu veux combien (1 carton, 2 cartons, ou combien de paquets) ?"
                    if f == "ZONE":
                        return "Tu es dans quelle commune/quartier pour la livraison stp ?"
                    if f in {"NUMÉRO", "NUMERO", "TELEPHONE", "TÉLÉPHONE"}:
                        return "Ton numéro WhatsApp pour le livreur stp ?"
                    if f == "PAIEMENT":
                        return "Tu peux envoyer l’acompte Wave de 2000 FCFA et la capture stp ?"
                    return ""

                trigger_type = "NONE"
                if payment_verdict_line:
                    trigger_type = "PAYMENT"
                elif any(k in msg_lower for k in ["acompte", "wave", "payer", "payé", "paye", "paiement", "transfert", "envoyé", "envoye"]):
                    trigger_type = "PAYMENT"
                elif re.search(r"\b(0\d{9})\b", str(query or "")):
                    trigger_type = "TEL"
                elif dynamic_context.get("detected_location"):
                    trigger_type = "ZONE"

                if triggered:
                    # Construire instruction XML minimaliste
                    ack_type = ""
                    ack_status = ""
                    if trigger_type == "PAYMENT":
                        ack_type = "paiement"
                        # Extraire status depuis line si possible
                        # Support 2 formats:
                        # - legacy: PAYMENT_VERDICT: [VALID] ...
                        # - kv: PAYMENT_VERDICT|status=VALID|...
                        m = re.search(r"\[(VALID|INSUFFICIENT|REFUSED|NONE)\]", str(payment_verdict_line or ""), re.IGNORECASE)
                        if m:
                            ack_status = m.group(1).upper()
                        else:
                            m2 = re.search(r"\bstatus\s*=\s*(VALID|INSUFFICIENT|REFUSED|NONE)\b", str(payment_verdict_line or ""), re.IGNORECASE)
                            ack_status = (m2.group(1).upper() if m2 else "PENDING")
                    elif trigger_type == "TEL":
                        ack_type = "telephone"
                        ack_status = "OK" if getattr(st_now, "numero", None) else "DETECTED"
                    elif trigger_type == "ZONE":
                        ack_type = "zone"
                        ack_status = "OK" if getattr(st_now, "zone", None) else "DETECTED"

                    question = _next_question_for(next_field)
                    field_xml = str(next_field or "").strip()

                    try:
                        if next_field:
                            order_tracker.record_asked(user_id, str(next_field), int(current_turn or 0))
                    except Exception:
                        pass

                    ask_counts = slot_meta_bundle.get("ask_counts") if isinstance(slot_meta_bundle, dict) else {}
                    ask_counts = ask_counts if isinstance(ask_counts, dict) else {}
                    last_asked = slot_meta_bundle.get("last_asked") if isinstance(slot_meta_bundle, dict) else {}
                    last_asked = last_asked if isinstance(last_asked, dict) else {}
                    slot_meta = slot_meta_bundle.get("slot_meta") if isinstance(slot_meta_bundle, dict) else {}
                    slot_meta = slot_meta if isinstance(slot_meta, dict) else {}

                    intent_pack = _infer_intent(str(query or ""))
                    hist_pack = _build_historique_compact(ask_counts, last_asked, int(current_turn or 0))
                    must_answer = (intent_pack.get("user_question_is_question") or "false") == "true"

                    intention_xml = (
                        "    <intention_client>\n"
                        f"      <intent>{intent_pack.get('intent') or ''}</intent>\n"
                        f"      <certainty>{intent_pack.get('certainty') or ''}</certainty>\n"
                        f"      <reformulation>{intent_pack.get('reformulation') or ''}</reformulation>\n"
                        f"      <user_question topic=\"{intent_pack.get('user_question_topic') or ''}\">{intent_pack.get('user_question_text') or ''}</user_question>\n"
                        "    </intention_client>"
                    )

                    # Simplified: only intention_client, no priorite_reponse or historique_compact

                    try:
                        missing_now = sorted(list(st_now.get_missing_fields()))
                    except Exception:
                        missing_now = []
                    missing_set = set([str(m).upper().strip() for m in (missing_now or [])])

                    def _v(attr: str) -> str:
                        return str(getattr(st_now, attr, "") or "").strip()

                    def _slot_xml(field: str, value: str) -> str:
                        f = str(field or "").upper().strip()
                        status = "PRESENT" if value else ("MISSING" if f in missing_set else "UNKNOWN")
                        asked = int(ask_counts.get(f) or 0)
                        last = int(last_asked.get(f) or 0)
                        meta = slot_meta.get(f) if isinstance(slot_meta.get(f), dict) else {}
                        src = str((meta or {}).get("source") or "")
                        conf = (meta or {}).get("confidence")
                        vv = str(value or "").replace("&", "and")
                        return (
                            f"      <slot name=\"{f}\" status=\"{status}\" asked=\"{asked}\" last_asked_turn=\"{last}\" source=\"{src}\" confidence=\"{conf}\">{vv}</slot>"
                        )

                    slots_block = (
                        "    <status_slots>\n"
                        + "\n".join(
                            [
                                _slot_xml("PRODUIT", _v("produit")),
                                _slot_xml("SPECS", _v("produit_details")),
                                _slot_xml("QUANTITÉ", _v("quantite")),
                                _slot_xml("ZONE", _v("zone")),
                                _slot_xml("NUMÉRO", _v("numero")),
                                _slot_xml("PAIEMENT", _v("paiement")),
                            ]
                        )
                        + "\n    </status_slots>"
                    )

                    tracking_block = (
                        "    <tracking>\n"
                        f"      <turn>{int(current_turn or 0)}</turn>\n"
                        "    </tracking>"
                    )

                    # Mode "soft": fournir un état + intention, sans imposer de question au modèle.
                    # (Ablation utile pour vérifier si le bégaiement vient d'un must_do trop rigide)
                    is_soft = instruction_mode in {"soft", "status_only", "status", "advisory"}

                    # Si complet, on laisse Jessica gérer la finalisation, mais on garde une consigne simple.
                    if not next_field:
                        if is_soft:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <intent>FINALIZE_OR_RECAP</intent>\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                f"    <status_next>NONE</status_next>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                        else:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                "    <must_do>\n"
                                "      <action>FINALIZE_OR_RECAP</action>\n"
                                "      <field>NONE</field>\n"
                                "      <question></question>\n"
                                "    </must_do>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                    else:
                        if is_soft:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <intent>ASK_NEXT_MISSING_FIELD</intent>\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                f"    <status_next>{field_xml}</status_next>\n"
                                f"    <suggested_question>{question}</suggested_question>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                        else:
                            instruction_block = (
                                "    <triggered>true</triggered>\n"
                                f"    <trigger_type>{trigger_type}</trigger_type>\n"
                                f"{intention_xml}\n"
                                "    <must_ack>\n"
                                f"      <what>{ack_type or 'signal'}</what>\n"
                                f"      <status>{ack_status or 'OK'}</status>\n"
                                "    </must_ack>\n"
                                "    <must_do>\n"
                                "      <action>ASK_NEXT_MISSING_FIELD</action>\n"
                                f"      <field>{field_xml}</field>\n"
                                f"      <question>{question}</question>\n"
                                "    </must_do>\n"
                                f"{tracking_block}\n"
                                f"{slots_block}\n"
                                "    <constraints>\n"
                                "      <one_question>true</one_question>\n"
                                "      <no_validation_loop>true</no_validation_loop>\n"
                                "    </constraints>"
                            )
                else:
                    intent_pack = _infer_intent(str(query or ""))
                    intention_xml = (
                        "    <intention_client>\n"
                        f"      <intent>{intent_pack.get('intent') or ''}</intent>\n"
                        f"      <certainty>{intent_pack.get('certainty') or ''}</certainty>\n"
                        f"      <reformulation>{intent_pack.get('reformulation') or ''}</reformulation>\n"
                        f"      <user_question topic=\"{intent_pack.get('user_question_topic') or ''}\">{intent_pack.get('user_question_text') or ''}</user_question>\n"
                        "    </intention_client>"
                    )
                    instruction_block = (
                        "    <triggered>false</triggered>\n"
                        f"{intention_xml}"
                    )

                short_instr = instruction_block.replace("\n", " ")
                if len(short_instr) > 220:
                    short_instr = short_instr[:220] + "..."
                print(f"🧭 [INSTRUCTION] triggered={'OUI' if triggered else 'NON'} | next_field={next_field or 'NONE'} | {short_instr}")
            except Exception as e:
                instruction_block = "    <triggered>false</triggered>"
                print(f"⚠️ [INSTRUCTION] error: {type(e).__name__}: {e}")
            
            # 3. Construction prompt complet
            print("🔨 [PROMPT] Construction prompt...")

            # Ajouter un bloc vision compact au contexte (pour forcer l'action LLM sur des données validées)
            try:
                verdict_lines = []
                if payment_verdict_line:
                    verdict_lines.append(payment_verdict_line)
                if phone_verdict_line:
                    verdict_lines.append(phone_verdict_line)
                if location_verdict_line:
                    verdict_lines.append(location_verdict_line)
                if 'quantite_verdict_line' in locals() and quantite_verdict_line:
                    verdict_lines.append(quantite_verdict_line)
                if vision_summary:
                    verdict_lines.append(vision_summary)

                if verdict_lines:
                    prev_pc = str(dynamic_context.get('product_context', '') or '')
                    inject = "\n".join([v for v in verdict_lines if v])
                    dynamic_context['product_context'] = (prev_pc + "\n" + inject).strip() if prev_pc else inject
            except Exception:
                pass
            
            price_calculation_block = ""
            try:
                st_for_price = order_tracker.get_state(user_id)
                produit_val = str(getattr(st_for_price, "produit", "") or "").strip()
                specs_val = str(getattr(st_for_price, "produit_details", "") or "").strip()
                quantite_val = str(getattr(st_for_price, "quantite", "") or "").strip()
                zone_val = str(dynamic_context.get("detected_location") or getattr(st_for_price, "zone", "") or "").strip()

                # Option A (cart-first): si on a déjà un panier (detected_items) confirmé, on calcule le prix
                # sur ce panier plutôt que sur les slots mono-produit (qui peuvent être obsolètes).
                try:
                    detected_items_pre = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                except Exception:
                    detected_items_pre = []

                def _extract_quantity_value(text: str) -> str:
                    try:
                        t = str(text or "")
                        # Match digit + unit
                        m = re.search(
                            r"\b(\d+)\s*(cartons?|paquets?|packs?|lots?|unit[ée]s?)\b",
                            t,
                            flags=re.IGNORECASE,
                        )
                        if m:
                            return f"{m.group(1)} {m.group(2)}".strip()
                        # Match French number word + unit (un lot, deux paquets, etc.)
                        _fr_nums = {"un": "1", "une": "1", "deux": "2", "trois": "3", "quatre": "4", "cinq": "5"}
                        m2 = re.search(
                            r"\b(un|une|deux|trois|quatre|cinq)\s+(cartons?|paquets?|packs?|lots?|unit[ée]s?)\b",
                            t,
                            flags=re.IGNORECASE,
                        )
                        if m2:
                            n = _fr_nums.get(m2.group(1).lower(), m2.group(1))
                            return f"{n} {m2.group(2)}".strip()
                        return ""
                    except Exception:
                        return ""

                def _parse_fee(v) -> Optional[int]:
                    if v is None:
                        return None
                    if isinstance(v, (int, float)):
                        return int(v)
                    s = str(v)
                    m = re.search(r"(\d+)", s)
                    return int(m.group(1)) if m else None

                delivery_fee_fcfa = _parse_fee(dynamic_context.get("shipping_fee"))

                # Fallback: si le message courant ne contient pas de zone, lire depuis OrderState persisté
                if delivery_fee_fcfa is None or int(delivery_fee_fcfa or 0) <= 0:
                    try:
                        _st_fee = order_tracker.get_state(user_id)
                        _zone_persisted = str(getattr(_st_fee, "zone", "") or "").strip()
                        if _zone_persisted:
                            from core.delivery_zone_extractor import extract_delivery_zone_and_cost
                            _zinfo = extract_delivery_zone_and_cost(_zone_persisted)
                            _fee2 = (_zinfo or {}).get("cost") if isinstance(_zinfo, dict) else None
                            if isinstance(_fee2, (int, float)) and int(_fee2) > 0:
                                delivery_fee_fcfa = int(_fee2)
                                print(f"📦 [PRICE_CALC] fee recovered from OrderState zone='{_zone_persisted}' → {delivery_fee_fcfa}")
                    except Exception:
                        pass

                def _validate_cart_items(items) -> bool:
                    if not isinstance(items, list) or not items:
                        return False

                    try:
                        catalog_v2 = get_company_catalog_v2(company_id)
                    except Exception:
                        catalog_v2 = None

                    if not isinstance(catalog_v2, dict):
                        return False

                    def _match_key_case_insensitive(keys: List[str], target: str) -> Optional[str]:
                        t = str(target or "").strip().lower()
                        if not t:
                            return None
                        for k in keys:
                            if str(k or "").strip().lower() == t:
                                return str(k)
                        return None

                    def _find_variant_key(product_raw: str) -> Optional[str]:
                        product_s = str(product_raw or "").strip()
                        if not product_s:
                            return None
                        keys = [str(k) for k in vtree.keys()]
                        exact = _match_key_case_insensitive(keys, product_s)
                        if exact:
                            return exact
                        p_low = product_s.lower()
                        for k in keys:
                            k_low = str(k or "").lower()
                            if p_low and (p_low in k_low or k_low in p_low):
                                return str(k)
                        if len(keys) == 1:
                            return str(keys[0])
                        return None

                    def _extract_t_number(specs_raw: str) -> Optional[int]:
                        s = str(specs_raw or "").strip().upper()
                        m = re.search(r"\bT\s*([1-9]\d*)\b", s)
                        if m:
                            try:
                                return int(m.group(1))
                            except Exception:
                                return None
                        m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", s)
                        if m2:
                            try:
                                return int(m2.group(1))
                            except Exception:
                                return None
                        return None

                    def _spec_key_matches(sub_key: str, requested_specs: str) -> bool:
                        if not sub_key:
                            return False
                        keys = [str(sub_key)]
                        exact = _match_key_case_insensitive(keys, requested_specs)
                        if exact:
                            return True

                        req_n = _extract_t_number(requested_specs)
                        if req_n is None:
                            return False

                        # Range support: parse all T numbers in the key and see if req_n fits in min..max
                        nums = [int(x) for x in re.findall(r"T\s*([1-9]\d*)", str(sub_key).upper()) if x.isdigit()]
                        if not nums:
                            return False
                        lo, hi = min(nums), max(nums)
                        return lo <= req_n <= hi

                    def _find_subvariant_key(node_s: Dict[str, Any], specs_raw: str) -> Optional[str]:
                        if not isinstance(node_s, dict):
                            return None
                        specs_s = str(specs_raw or "").strip()
                        if not specs_s:
                            return None
                        sub_keys = [str(k) for k in node_s.keys()]
                        exact = _match_key_case_insensitive(sub_keys, specs_s)
                        if exact:
                            return exact
                        for k in sub_keys:
                            if _spec_key_matches(k, specs_s):
                                return str(k)
                        # Soft match last
                        s_low = specs_s.lower()
                        for k in sub_keys:
                            k_low = str(k or "").lower()
                            if s_low and (s_low in k_low or k_low in s_low):
                                return str(k)
                        return None

                    for it in items:
                        if not isinstance(it, dict):
                            return False

                        # Multi-product support: select mono-product catalog by item.product_id
                        selected_catalog = None
                        try:
                            plist = catalog_v2.get("products") if isinstance(catalog_v2, dict) else None
                            if isinstance(plist, list):
                                pid = str(it.get("product_id") or "").strip()
                                if pid:
                                    selected_catalog = get_company_product_catalog_v2(company_id, pid)
                                    if not isinstance(selected_catalog, dict):
                                        try:
                                            if re.fullmatch(r"prod_[0-9a-f]{8}", pid, flags=re.IGNORECASE):
                                                import hashlib as _hashlib
                                                import unicodedata as _ud

                                                def _norm_name_for_id(name: str) -> str:
                                                    t = str(name or "").strip().lower()
                                                    t = _ud.normalize("NFKD", t)
                                                    t = "".join([c for c in t if not _ud.combining(c)])
                                                    t = re.sub(r"[^a-z0-9\s-]+", " ", t)
                                                    t = t.replace("-", " ")
                                                    t = re.sub(r"\s+", " ", t).strip()
                                                    return t

                                                def _pid_hash(name: str) -> str:
                                                    base = _norm_name_for_id(name)
                                                    if not base:
                                                        return ""
                                                    h = _hashlib.sha1(base.encode("utf-8", errors="replace")).hexdigest()
                                                    return f"prod_{h[:8]}"

                                                for p in (plist or []):
                                                    if not isinstance(p, dict):
                                                        continue
                                                    pname = str(p.get("product_name") or (p.get("catalog_v2") or {}).get("product_name") or "").strip()
                                                    if pname and _pid_hash(pname).lower() == pid.lower() and isinstance(p.get("catalog_v2"), dict):
                                                        selected_catalog = p.get("catalog_v2")
                                                        break
                                        except Exception:
                                            pass
                                else:
                                    # Only allow missing product_id if there is exactly one product.
                                    only_one = [p for p in plist if isinstance(p, dict) and isinstance(p.get("catalog_v2"), dict)]
                                    if len(only_one) == 1:
                                        selected_catalog = only_one[0].get("catalog_v2")
                            else:
                                selected_catalog = catalog_v2
                        except Exception:
                            selected_catalog = catalog_v2

                        if not isinstance(selected_catalog, dict):
                            return False

                        if str(selected_catalog.get("pricing_strategy") or "").upper() != "UNIT_AS_ATOMIC":
                            return False

                        vtree = selected_catalog.get("v")
                        if not isinstance(vtree, dict) or not vtree:
                            return False

                        canonical_units = selected_catalog.get("canonical_units")
                        if not isinstance(canonical_units, list):
                            canonical_units = []
                        canonical_units = [str(u).strip() for u in canonical_units if str(u).strip()]
                        if not canonical_units:
                            return False

                        product_raw = str(it.get("product") or "").strip()
                        if not product_raw:
                            product_raw = str(it.get("product_id") or "").strip()
                        specs_raw = str(it.get("specs") or "").strip()
                        if not specs_raw:
                            specs_raw = str(it.get("spec") or "").strip()
                        unit = str(it.get("unit") or "").strip()
                        qty = it.get("qty")
                        conf = it.get("confidence")
                        try:
                            conf_f = float(conf) if conf is not None else 0.0
                        except Exception:
                            conf_f = 0.0

                        if unit not in canonical_units:
                            return False

                        variant_key = _find_variant_key(product_raw)
                        node = vtree.get(variant_key) if variant_key else None
                        if not isinstance(node, dict):
                            return False

                        # If the catalog defines sub-variants (node.s), specs must match one of its keys (including ranges)
                        node_s = node.get("s")
                        if isinstance(node_s, dict) and node_s:
                            sub_key = _find_subvariant_key(node_s, specs_raw)
                            if not sub_key:
                                return False
                            sub_node = node_s.get(sub_key)
                            if not isinstance(sub_node, dict):
                                return False
                            u_map = sub_node.get("u")
                            if not isinstance(u_map, dict) or unit not in u_map:
                                return False
                        else:
                            u_map = node.get("u")
                            if not isinstance(u_map, dict) or unit not in u_map:
                                return False

                        if qty is None or (not isinstance(qty, int)) or qty <= 0:
                            return False
                        if conf_f < float(CONFIDENCE_THRESHOLD):
                            return False
                    return True

                if _validate_cart_items(detected_items_pre) and zone_val:
                    pc_inner_cart = UniversalPriceCalculator.build_price_calculation_block_from_detected_items(
                        company_id=company_id,
                        items=detected_items_pre,
                        zone=zone_val,
                        delivery_fee_fcfa=delivery_fee_fcfa,
                    )
                    if str(pc_inner_cart or "").strip():
                        price_calculation_block = str(pc_inner_cart)
                        print(f"✅ [PRICE_CART_FIRST] pre_llm injected | items={len(detected_items_pre)} | zone='{zone_val}'")
                        raise StopIteration("skip_mono_price_calc_due_to_cart")

                # Fallback quantité/specs AVANT le LLM:
                # OrderStateTracker est alimenté principalement APRÈS parsing du <thinking>,
                # donc au 1er tour la quantité peut être vide alors qu'elle est présente dans le message.
                if not quantite_val:
                    quantite_val = _extract_quantity_value(query)
                if not specs_val:
                    # Si le client écrit "taille 4" ou "T4" on le garde en specs (utile pour pressions).
                    m_sz = re.search(r"\b(?:taille\s*|t)([1-7])\b", str(query or ""), flags=re.IGNORECASE)
                    if m_sz:
                        specs_val = f"taille {m_sz.group(1)}"

                # Fallback product detection (scalable, non spécifique entreprise):
                # uniquement pour calculer le prix quand le LLM n'a pas rempli PRODUIT.
                msg_l = str(query or "").lower()
                # Si le client indique explicitement un changement ("finalement", "à la place"...),
                # on autorise le switch produit même si un ancien produit est déjà en mémoire.
                change_markers = ["finalement", "a la place", "à la place", "plutot", "plutôt", "change", "remplace"]
                is_switch = any(m in msg_l for m in change_markers)
                # Detect variant from message using catalog vtree keys (scalable for any company).
                # Variant names are NEVER written to the produit slot — only to produit_details.
                variant_hint = ""
                try:
                    _cat_for_vh = None
                    try:
                        _cat_for_vh = get_company_catalog_v2(company_id)
                    except Exception:
                        _cat_for_vh = None
                    _vtree_vh = _cat_for_vh.get("v") if isinstance(_cat_for_vh, dict) and isinstance(_cat_for_vh.get("v"), dict) else None
                    if isinstance(_vtree_vh, dict) and _vtree_vh:
                        for _vk in _vtree_vh.keys():
                            _vk_s = str(_vk or "").strip()
                            _vk_low = _vk_s.lower()
                            if _vk_low and _vk_low in msg_l:
                                variant_hint = _vk_s
                                break
                    # Legacy fallback when catalog has no vtree
                    if not variant_hint:
                        if "culott" in msg_l:
                            variant_hint = "Culotte"
                        elif "pression" in msg_l or "press" in msg_l:
                            variant_hint = "Pression"
                except Exception:
                    variant_hint = ""

                # Best-effort: si on est sur un catalogue mono-produit, on peut fixer active_product_id,
                # et mettre la variante dans produit_details (jamais dans produit).
                if variant_hint:
                    try:
                        catalog_v2_for_variant = None
                        try:
                            catalog_v2_for_variant = get_company_catalog_v2(company_id)
                        except Exception:
                            catalog_v2_for_variant = None

                        only_pid = ""
                        if isinstance(catalog_v2_for_variant, dict) and isinstance(catalog_v2_for_variant.get("products"), list):
                            plist = [p for p in (catalog_v2_for_variant.get("products") or []) if isinstance(p, dict)]
                            if len(plist) == 1:
                                one = plist[0]
                                only_pid = str(one.get("product_id") or (one.get("catalog_v2") or {}).get("product_id") or "").strip()
                        elif isinstance(catalog_v2_for_variant, dict):
                            only_pid = str(catalog_v2_for_variant.get("product_id") or "").strip()

                        if only_pid:
                            # Ne fixe produit_val que si c'est un ID stable.
                            if _is_stable_product_id(only_pid):
                                produit_val = only_pid
                                try:
                                    order_tracker.set_custom_meta(user_id, "active_product_id", only_pid)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                # Pré-remplissage tracker AVANT LLM (évite missing=QUANTITÉ alors que présent dans le message)
                try:
                    st_pre = order_tracker.get_state(user_id)
                    # Si le message courant apporte une nouvelle valeur, on autorise la mise à jour même si
                    # une ancienne valeur existe (cas: "finalement", correction, changement de produit).
                    if produit_val and str(getattr(st_pre, "produit", "") or "").strip() != produit_val:
                        order_tracker.update_produit(user_id, produit_val, source="CONTEXT_INFERRED", confidence=0.8)

                        # Pivot produit: on tue immédiatement les attributs du produit précédent.
                        # Sinon le pré-calcul envoie une chimère (ex: produit=pressions + specs=T4 + quantite=3 paquet).
                        try:
                            specs_val = ""
                            quantite_val = ""
                            order_tracker.update_produit_details(user_id, "", source="CONTEXT_INFERRED", confidence=0.6)
                            order_tracker.update_quantite(user_id, "", source="CONTEXT_INFERRED", confidence=0.6)
                            print("🧹 [ORDER_STATE] SPECS+QUANTITÉ cleared (pre_llm_pivot)")
                            # Re-extract from current message (pivot clears stale values,
                            # but the current message may carry fresh specs+qty).
                            quantite_val = _extract_quantity_value(query) or ""
                            m_sz_re = re.search(r"\b(?:taille\s*|t)([1-7])\b", str(query or ""), flags=re.IGNORECASE)
                            if m_sz_re:
                                specs_val = f"taille {m_sz_re.group(1)}"
                            # Prepend variant hint so price_calc can resolve product_key
                            # e.g. "Pression taille 1" instead of just "taille 1"
                            if variant_hint:
                                if specs_val and variant_hint.lower() not in specs_val.lower():
                                    specs_val = f"{variant_hint} {specs_val}"
                                elif not specs_val:
                                    specs_val = variant_hint
                            print(f"🔄 [ORDER_STATE] Re-extracted from msg: specs='{specs_val}' quantite='{quantite_val}'")
                        except Exception:
                            pass

                    if specs_val and str(getattr(st_pre, "produit_details", "") or "").strip() != specs_val:
                        order_tracker.update_produit_details(user_id, specs_val, source="CONTEXT_INFERRED", confidence=0.8)

                    # Si on a détecté une variante (culotte/pression) mais pas de specs, on la stocke en details.
                    # (On évite de polluer produit.)
                    try:
                        if variant_hint and (not specs_val):
                            cur_details = str(getattr(st_pre, "produit_details", "") or "").strip()
                            if not cur_details:
                                order_tracker.update_produit_details(user_id, variant_hint, source="CONTEXT_INFERRED", confidence=0.75)
                    except Exception:
                        pass

                    # Quantité: si détectée dans le message, elle doit remplacer l'ancienne (sinon on recycle une
                    # quantité obsolète sur un nouveau produit et le price_calc part sur INVALID_QUANTITY).
                    if quantite_val and str(getattr(st_pre, "quantite", "") or "").strip() != quantite_val:
                        order_tracker.update_quantite(user_id, quantite_val, source="CONTEXT_INFERRED", confidence=0.8)

                    # Si on switch produit et que le message parle de lots/plusieurs tailles,
                    # la quantité globale précédente ne doit jamais rester (elle devient incohérente).
                    try:
                        if is_switch and (" lot" in msg_l or " lots" in msg_l) and str(getattr(st_pre, "quantite", "") or "").strip():
                            order_tracker.update_quantite(user_id, "", source="CONTEXT_INFERRED", confidence=0.6)
                            quantite_val = ""
                            print("🧹 [ORDER_STATE] QUANTITÉ cleared (pre_llm_switch)")
                    except Exception:
                        pass
                except Exception:
                    pass

                # Si le message ressemble à un panier multi-items (lots + plusieurs tailles),
                # ne pas faire de pré-calcul: on attend detected_items_json du LLM.
                pre_llm_price_calc_allowed = True
                try:
                    if is_switch and (" lot" in msg_l or " lots" in msg_l):
                        pre_llm_price_calc_allowed = False
                        specs_val = ""
                        quantite_val = ""
                except Exception:
                    pass

                # Ensure variant_hint is in specs_val so price_calc can resolve product_key
                # when produit is a product_id (e.g. prod_ml6dxg73_a0rloi)
                try:
                    if variant_hint and specs_val and variant_hint.lower() not in specs_val.lower():
                        specs_val = f"{variant_hint} {specs_val}"
                    elif variant_hint and not specs_val:
                        specs_val = variant_hint
                except Exception:
                    pass

                try:
                    print(
                        "🧾 [PRICE_CALC][INPUTS] "
                        + f"produit='{produit_val}' specs='{specs_val}' quantite='{quantite_val}' "
                        + f"zone='{zone_val}' shipping_fee='{dynamic_context.get('shipping_fee')}'"
                    )
                except Exception:
                    pass

                # Injection prix: ne dépend pas d'un company_id hardcodé.
                # Si produit+quantité sont détectés, on calcule avec les règles du catalogue/tiers actif.
                if pre_llm_price_calc_allowed:
                    price_calculation_block = UniversalPriceCalculator.build_price_calculation_block_for_rue_du_grossiste(
                        company_id=company_id,
                        produit=produit_val,
                        specs=specs_val,
                        quantite=quantite_val,
                        zone=zone_val,
                        delivery_fee_fcfa=delivery_fee_fcfa,
                    )
                else:
                    price_calculation_block = ""

                # Persister le pricing mono-produit dès qu'il est calculé, même si le LLM rend un <response> valide.
                # Sinon, PRICE_GUARD / post-processing peuvent croire (à tort) qu'aucun prix n'est validé.
                try:
                    pc_inner = str(price_calculation_block or "").strip()
                    if pc_inner:
                        order_tracker.set_custom_meta(
                            user_id,
                            "price_calculation_block",
                            "<price_calculation>\n" + pc_inner + "\n</price_calculation>",
                        )
                except Exception:
                    pass

                try:
                    if str(price_calculation_block or "").strip():
                        short_pc = str(price_calculation_block).replace("\n", " ")
                        if len(short_pc) > 300:
                            short_pc = short_pc[:300] + "..."
                        print(f"🧮 [PRICE_CALC] computed | produit='{produit_val}' specs='{specs_val}' quantite='{quantite_val}' fee='{delivery_fee_fcfa}' | {short_pc}")
                    else:
                        print(f"🧮 [PRICE_CALC] EMPTY | produit='{produit_val}' specs='{specs_val}' quantite='{quantite_val}' zone='{zone_val}' fee='{delivery_fee_fcfa}'")
                except Exception:
                    pass
            except Exception as _pc_e:
                print(f"⚠️ [PRICE_CALC] error: {type(_pc_e).__name__}: {_pc_e}")

            try:
                pc_meta_now = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                snap_now = _snapshot_from_price_block(pc_meta_now)
                if snap_now:
                    order_tracker.set_custom_meta(user_id, "last_total_snapshot", snap_now)
            except Exception:
                pass

            try:
                snap = order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None)
            except Exception:
                snap = None
            if isinstance(snap, dict) and (snap.get("total") is not None):
                try:
                    prev_pr = str(dynamic_context.get('pricing_context', '') or '')
                except Exception:
                    prev_pr = ""
                try:
                    snap_txt = json.dumps(snap, ensure_ascii=False)
                except Exception:
                    snap_txt = "{}"
                inject = f"LAST_TOTAL_SNAPSHOT_JSON: {snap_txt}"
                dynamic_context['pricing_context'] = (prev_pr + "\n" + inject).strip() if prev_pr else inject

            # Catalogue reference: injecter les formats de vente (customFormats) + unités canoniques
            # et unités autorisées par produit/spec. Objectif: guider le LLM sans hardcode produit.
            catalogue_reference_block_override = ""
            try:
                catalog_v2 = None
                try:
                    catalog_v2 = get_company_catalog_v2(company_id)
                except Exception:
                    catalog_v2 = None

                # Multi-product: select active product catalog if known, else mono fallback if exactly one product.
                selected_catalog = catalog_v2
                try:
                    if isinstance(catalog_v2, dict) and isinstance(catalog_v2.get("products"), list):
                        active_pid = str(order_tracker.get_custom_meta(user_id, "active_product_id", default="") or "").strip()
                        if active_pid:
                            selected_catalog = get_company_product_catalog_v2(company_id, active_pid)
                        else:
                            only_one = [p for p in (catalog_v2.get("products") or []) if isinstance(p, dict) and isinstance(p.get("catalog_v2"), dict)]
                            if len(only_one) == 1:
                                selected_catalog = only_one[0].get("catalog_v2")
                            else:
                                selected_catalog = None
                except Exception:
                    selected_catalog = catalog_v2

                if isinstance(selected_catalog, dict) and str(selected_catalog.get("pricing_strategy") or "").upper() == "UNIT_AS_ATOMIC":
                    canonical_units = selected_catalog.get("canonical_units")
                    if not isinstance(canonical_units, list):
                        canonical_units = []
                    canonical_units = [str(u).strip() for u in canonical_units if str(u).strip()]

                    ui_state = selected_catalog.get("ui_state")
                    if not isinstance(ui_state, dict):
                        ui_state = {}
                    custom_formats = ui_state.get("customFormats")
                    if not isinstance(custom_formats, list):
                        custom_formats = []

                    vtree = selected_catalog.get("v")
                    if not isinstance(vtree, dict):
                        vtree = {}

                    # Construire un bloc lisible (texte + mini-structure) qui reste stable/scalable.
                    lines = []
                    if canonical_units:
                        lines.append("CANONICAL_UNITS: " + " | ".join(canonical_units))

                    if custom_formats:
                        lines.append("FORMATS_DE_VENTE:")
                        for cf in custom_formats:
                            if not isinstance(cf, dict):
                                continue
                            cf_type = str(cf.get("type") or "").strip()
                            cf_qty = str(cf.get("quantity") or "").strip()
                            cf_label = str(cf.get("unitLabel") or "").strip()
                            cf_enabled = cf.get("enabled")
                            enabled_s = "true" if bool(cf_enabled) else "false"
                            # Exemple attendu: type=lot quantity=300 => canonical unit lot_300
                            canon_guess = ""
                            if cf_type and cf_qty and str(cf_qty).isdigit():
                                canon_guess = f"{cf_type}_{cf_qty}"
                            parts = [
                                f"type={cf_type}" if cf_type else "type=∅",
                                f"quantity={cf_qty}" if cf_qty else "quantity=∅",
                                f"unitLabel={cf_label}" if cf_label else "unitLabel=∅",
                                f"enabled={enabled_s}",
                            ]
                            if canon_guess:
                                parts.append(f"canonical={canon_guess}")
                            lines.append("- " + " | ".join(parts))

                    # Unités autorisées par produit/spec (à partir du vtree)
                    allowed_lines = []
                    try:
                        for variant_k, node in vtree.items():
                            if not isinstance(node, dict):
                                continue
                            node_s = node.get("s")
                            if isinstance(node_s, dict) and node_s:
                                for sub_k, sub_node in node_s.items():
                                    if not isinstance(sub_node, dict):
                                        continue
                                    u_map = sub_node.get("u")
                                    if not isinstance(u_map, dict):
                                        continue
                                    units = [str(k) for k in u_map.keys() if str(k).strip()]
                                    if units:
                                        allowed_lines.append(
                                            f"- product={str(variant_k).strip()} | specs={str(sub_k).strip()} | units={', '.join(units)}"
                                        )
                            else:
                                u_map = node.get("u")
                                if not isinstance(u_map, dict):
                                    continue
                                units = [str(k) for k in u_map.keys() if str(k).strip()]
                                if units:
                                    allowed_lines.append(
                                        f"- product={str(variant_k).strip()} | units={', '.join(units)}"
                                    )
                    except Exception:
                        allowed_lines = []

                    if allowed_lines:
                        lines.append("UNITS_PAR_PRODUIT:")
                        lines.extend(allowed_lines)

                    if lines:
                        catalogue_reference_block_override = "\n".join(lines).strip()
            except Exception:
                catalogue_reference_block_override = ""

            had_product_context_in_prompt = False
            try:
                had_product_context_in_prompt = bool(str(dynamic_context.get('product_context', '') or '').strip())
            except Exception:
                had_product_context_in_prompt = False

            active_pid_before_prompt = ""
            try:
                active_pid_before_prompt = str(order_tracker.get_custom_meta(user_id, "active_product_id", default="") or "").strip()
            except Exception:
                active_pid_before_prompt = ""

            # ── CartManager: injecter le résumé panier dans le prompt ──
            try:
                cart_summary = self.cart_manager.get_cart_summary(user_id)
                if cart_summary:
                    instruction_block += f"\n<current_cart>{cart_summary}</current_cart>\n"
            except Exception as _cart_e:
                print(f"⚠️ [CART_SUMMARY] injection error: {type(_cart_e).__name__}: {_cart_e}")

            # ── PATCH D: Hints proactifs — Python injecte les montants connus pour que Jessica les annonce ──
            proactive_hints = []
            try:
                # Hint 1: Prix produit — si price_calculation_block contient un ready_to_send, le LLM DOIT l'annoncer
                _pc_block_str = str(price_calculation_block or "").strip()

                # OPT-1/3: Vérifier si le prix a DÉJÀ été annoncé dans l'historique récent
                _conv_hist = str(dynamic_context.get('conversation_history') or '').lower()
                _price_already_announced = False
                try:
                    if _pc_block_str:
                        _m_total = re.search(r"<total_fcfa>(\d+)</total_fcfa>", _pc_block_str)
                        if _m_total:
                            _total_str = _m_total.group(1)
                            # Vérifier si ce montant exact apparaît dans l'historique (IA l'a déjà dit)
                            _total_formatted = f"{int(_total_str):,}".replace(",", " ").replace("\u202f", " ")
                            _total_plain = str(int(_total_str))
                            if (f"{_total_plain}f" in _conv_hist.replace(" ", "")
                                or f"{_total_plain} f" in _conv_hist
                                or _total_formatted.lower() in _conv_hist
                                or f"total fait {_total_plain}" in _conv_hist.replace(" ", "").replace("\u00a0", "")
                                or f"{_total_plain}f ✅" in _conv_hist.replace(" ", "")):
                                _price_already_announced = True
                except Exception:
                    _price_already_announced = False

                if _pc_block_str:
                    _ready_hint = ""
                    try:
                        _m_ready = re.search(r"<ready_to_send>(.*?)</ready_to_send>", _pc_block_str, re.DOTALL | re.IGNORECASE)
                        if _m_ready:
                            _ready_hint = str(_m_ready.group(1) or "").strip()
                    except Exception:
                        pass
                    if _ready_hint:
                        if _price_already_announced:
                            # OPT-1/3: Prix déjà annoncé → NE PAS répéter le récap complet
                            proactive_hints.append(
                                f"<proactive_price_already_shown>\n"
                                f"  ⚠️ Le prix total a DÉJÀ été annoncé au client dans un message précédent.\n"
                                f"  NE RÉPÈTE PAS le récapitulatif de prix. Réponds UNIQUEMENT à la question actuelle du client\n"
                                f"  (zone, numéro, paiement, etc.) de manière concise.\n"
                                f"  Si le client demande explicitement le total/prix, tu peux le redonner.\n"
                                f"</proactive_price_already_shown>"
                            )
                        else:
                            proactive_hints.append(
                                f"<proactive_price>\n"
                                f"  Python a calculé le prix. Tu DOIS annoncer ce montant au client dans ta réponse.\n"
                                f"  Copie-colle ce récapitulatif tel quel :\n"
                                f"  {_ready_hint}\n"
                                f"  Puis enchaîne naturellement (ex: demander zone, paiement, numéro selon ce qui manque).\n"
                                f"</proactive_price>"
                            )

                # Hint 2: Frais de livraison — si zone connue + fee calculé, le LLM DOIT annoncer les frais
                if delivery_fee_fcfa and isinstance(delivery_fee_fcfa, int) and delivery_fee_fcfa > 0 and zone_val:
                    # OPT-1/3: Ne pas annoncer les frais si déjà dans l'historique
                    _fee_str = str(delivery_fee_fcfa)
                    _fee_already = bool(f"{_fee_str}f" in _conv_hist.replace(" ", "") or f"livraison" in _conv_hist and _fee_str in _conv_hist)
                    if not _fee_already:
                        proactive_hints.append(
                            f"<proactive_delivery>\n"
                            f"  La livraison à {zone_val} coûte {delivery_fee_fcfa} FCFA.\n"
                            f"  Tu DOIS informer le client de ce montant dans ta réponse si ce n'est pas déjà fait.\n"
                            f"</proactive_delivery>"
                        )
            except Exception as _ph_e:
                print(f"⚠️ [PROACTIVE_HINTS] error: {type(_ph_e).__name__}: {_ph_e}")

            if proactive_hints:
                instruction_block += "\n" + "\n".join(proactive_hints) + "\n"
                print(f"💡 [PROACTIVE_HINTS] {len(proactive_hints)} hint(s) injected into instruction_block")

            final_prompt = await self.prompt_system.build_prompt(
                query=query,
                user_id=user_id,
                company_id=company_id,
                detected_location=dynamic_context.get('detected_location'),
                shipping_fee=dynamic_context.get('shipping_fee'),
                delivery_time=dynamic_context.get('delivery_time'),
                product_context=dynamic_context.get('product_context', ''),
                pricing_context=dynamic_context.get('pricing_context', ''),
                conversation_history=str(dynamic_context.get('conversation_history') or ''),
                instruction_block=instruction_block,
                validation_errors_block=validation_errors_block,
                price_calculation_block=price_calculation_block,
                catalogue_reference_block=(
                    catalogue_reference_block_override
                    if str(catalogue_reference_block_override or "").strip()
                    else "\n".join(
                        [
                            ln
                            for ln in str(dynamic_context.get('product_context', '') or '').splitlines()
                            if ln.strip()
                            and (not str(ln).upper().startswith('PAYMENT_VERDICT'))
                            and (not str(ln).upper().startswith('PHONE_VERDICT'))
                            and (not str(ln).upper().startswith('LOCATION_VERDICT'))
                            and (not str(ln).upper().startswith('VISION_GEMINI'))
                        ]
                    ).strip()
                ),
                has_image=bool(images and len(images) > 0),
            )

            first_pass_catalogue_block_empty = True
            try:
                pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
                m_cat = list(re.finditer(pat, str(final_prompt or ""), flags=re.IGNORECASE | re.DOTALL))
                if m_cat:
                    inner = str(m_cat[-1].group(1) or "").strip()
                    first_pass_catalogue_block_empty = not bool(inner)
                else:
                    first_pass_catalogue_block_empty = True
            except Exception:
                first_pass_catalogue_block_empty = True
            
            print(f"✅ [PROMPT] Prompt construit: {len(final_prompt)} chars")
            
            # Affichage prompt pour debug
            print(f"\n{'='*80}")
            print(f"🧠 PROMPT COMPLET ENVOYÉ AU LLM")
            print(f"{'='*80}")
            print(final_prompt[:1000] + "..." if len(final_prompt) > 1000 else final_prompt)
            print(f"{'='*80}\n")
            
            # 4. Génération LLM avec tracking tokens
            print("🤖 [LLM] Génération réponse...")

            # Choix modèle: fallback sur env (OpenRouter) si rien n'est piloté par ailleurs.
            model_name = (
                os.getenv("SIMPLIFIED_RAG_MODEL")
                or os.getenv("LLM_MODEL")
                or "google/gemini-2.5-flash-lite"
            ).strip()

            max_tokens_cfg = int(os.getenv("SIMPLIFIED_RAG_MAX_TOKENS", "900"))
            print(f"🧪 [LLM_CONFIG] model='{model_name}' | max_tokens={max_tokens_cfg}")
            
            llm_result = await self.llm_client.complete(
                prompt=final_prompt,
                model_name=model_name,
                temperature=0.2,
                top_p=0.7,
                # 320-420 peut couper la fermeture </response> quand le <thinking> est long.
                # Rendre configurable (env) + augmenter le défaut pour éviter "<response> tag not found".
                max_tokens=max_tokens_cfg,
                frequency_penalty=0.0,
            )
            
            # 5. Extraction métriques tokens
            token_usage = {}
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            total_cost = 0.0
            model_used = "unknown"
            
            if isinstance(llm_result, dict):
                response = llm_result.get("response", llm_result)
                token_usage = llm_result.get("usage", {}) or {}
                model_used = llm_result.get("model", "unknown")
                
                try:
                    if isinstance(token_usage, dict):
                        prompt_tokens = int(token_usage.get("prompt_tokens") or 0)
                        completion_tokens = int(token_usage.get("completion_tokens") or 0)
                        total_tokens = int(token_usage.get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
                        total_cost = float(
                            token_usage.get("total_cost")
                            if token_usage.get("total_cost") is not None
                            else (token_usage.get("cost") or 0.0)
                        )
                except Exception as e:
                    print(f"⚠️ [TOKENS] Erreur extraction: {e}")
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    total_cost = 0.0
            else:
                response = llm_result

            # Garder la sortie brute du LLM (avant extraction <thinking>/<response>) pour diagnostics/failsafes.
            raw_llm_output = str(response or "")
            
            print(f"✅ [LLM] Réponse générée: {len(str(response))} chars")
            print(
                f"{C_GREEN}💰 [TOKENS] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens} | Cost: ${total_cost:.6f} | Model: {model_used}{C_RESET}"
            )
            
            # 6. Extraction thinking + response
            thinking = ""
            thinking_parsed: Dict[str, Any] = {}
            tool_call_req: Optional[Dict[str, Any]] = None
            second_pass_attempted = False

            def _coerce_json_obj(raw: str) -> Optional[Any]:
                try:
                    s = str(raw or "").strip()
                    if not s:
                        return None

                    # Strip markdown code fences if the model wrapped the JSON.
                    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
                    s = re.sub(r"\s*```$", "", s, flags=re.IGNORECASE)
                    s = s.strip()

                    # Best-effort: extract the first JSON object/array substring.
                    first_obj = s.find("{")
                    last_obj = s.rfind("}")
                    first_arr = s.find("[")
                    last_arr = s.rfind("]")

                    cand = ""
                    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
                        cand = s[first_obj : last_obj + 1]
                    elif first_arr != -1 and last_arr != -1 and last_arr > first_arr:
                        cand = s[first_arr : last_arr + 1]
                    else:
                        cand = s

                    cand = cand.strip()
                    if not cand:
                        return None
                    return json.loads(cand)
                except Exception:
                    return None

            def _norm_text(s: str) -> str:
                try:
                    import unicodedata

                    t = str(s or "")
                    t = unicodedata.normalize("NFKD", t)
                    t = "".join(ch for ch in t if not unicodedata.combining(ch))
                    t = t.lower()
                    t = re.sub(r"[^a-z0-9\s]", " ", t)
                    t = re.sub(r"\s+", " ", t).strip()
                    return t
                except Exception:
                    return str(s or "").lower().strip()

            def _is_value_mentioned(message: str, value: str) -> bool:
                """Vérification conservative: n'accepte que si la valeur est réellement mentionnée.

                But: empêcher que le LLM invente PRODUIT/SPECS/QUANTITÉ dans <thinking>.
                """
                mv = _norm_text(value)
                mm = _norm_text(message)
                if not mv or mv in {"∅", "o", "ok", "oui", "non", "na", "n a"}:
                    return False
                if not mm:
                    return False

                # Quantités: exiger présence du chiffre dans le message.
                d = re.findall(r"\b\d+\b", mv)
                if d:
                    return any(re.search(rf"\b{re.escape(x)}\b", mm) for x in d)

                # Sinon: match tokens significatifs (>=3 chars), au moins 1 token présent.
                tokens = [t for t in mv.split() if len(t) >= 3]
                if not tokens:
                    return mv in mm
                return any(re.search(rf"\b{re.escape(t)}\b", mm) for t in tokens)

            def _extract_tag(text: str, tag: str) -> str:
                m = re.search(rf'<{tag}>(.*?)</{tag}>', text or "", re.DOTALL | re.IGNORECASE)
                return m.group(1).strip() if m else ""

            def _parse_thinking_schema(thinking_text: str) -> Dict[str, Any]:
                t = thinking_text or ""

                def pick(pattern: str) -> str:
                    m = re.search(pattern, t, re.IGNORECASE)
                    return m.group(1).strip() if m else ""

                def pick_tag(tag: str) -> str:
                    m = re.search(rf"<{tag}>\s*(?:\[([^\]]+)\]|(.*?))\s*</{tag}>", t, re.IGNORECASE | re.DOTALL)
                    if not m:
                        return ""
                    return (m.group(1) or m.group(2) or "").strip()

                def pick_field(label: str) -> str:
                    m = re.search(
                        rf"-\s*{label}:\s*(?:\[([^\]]+)\]|(.+))",
                        t,
                        re.IGNORECASE,
                    )
                    if not m:
                        return ""
                    return (m.group(1) or m.group(2) or "").strip()

                intent = pick_tag("intent")
                priority = pick_tag("priority")
                next_step = pick(r"<next>\s*(.*?)\s*</next>")

                produit = pick_field("PRODUIT")
                specs = pick_field("SPECS")
                quantite = pick_field("QUANTIT[ÉE]")
                prix_cite = pick_field("PRIX_CIT[ÉE]")

                zone = pick_field("ZONE")
                telephone = pick_field("T[ÉE]L[ÉE]PHONE")
                paiement = pick_field("PAIEMENT")

                # Fallback: format compact (ex: 'Le produit est "culottes" et la quantité "3 paquets".')
                # Ce format est fréquent avec certains prompts; on extrait de façon conservative.
                if not produit:
                    m_prod = re.search(r"\bproduit\s+est\s+\"([^\"]+)\"", t, re.IGNORECASE)
                    if m_prod:
                        produit = (m_prod.group(1) or "").strip()
                if not quantite:
                    m_qty = re.search(r"\bquantit[ée]\s+\"([^\"]+)\"", t, re.IGNORECASE)
                    if m_qty:
                        quantite = (m_qty.group(1) or "").strip()
                if not zone:
                    m_zone = re.search(r"\bzone\s+\"([^\"]+)\"", t, re.IGNORECASE)
                    if m_zone:
                        zone = (m_zone.group(1) or "").strip()

                urgence = pick_tag("signal_urgence")

                def clean(v: str) -> str:
                    vv = str(v or "").strip()
                    if vv in {"∅", "Ø", "N/A", "NA", "none", "null", ""}:
                        return ""
                    return vv

                return {
                    "intent": clean(intent),
                    "priority": clean(priority),
                    "next": clean(next_step),
                    "signal_urgence": clean(urgence),
                    "detection": {
                        "produit": clean(produit),
                        "specs": clean(specs),
                        "quantite": clean(quantite),
                        "prix_cite": clean(prix_cite),
                        "zone": clean(zone),
                        "telephone": clean(telephone),
                        "paiement": clean(paiement),
                    },
                }

            try:
                def _is_stable_product_id(v: str) -> bool:
                    return bool(re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", str(v or "").strip(), flags=re.IGNORECASE))

                stable_pid = ""
                stable_label = ""

                if first_pass_catalogue_block_empty and (not active_pid_before_prompt) and (not second_pass_attempted):
                    t_match0 = re.search(r'<thinking>(.*?)</thinking>', raw_llm_output, re.DOTALL | re.IGNORECASE)
                    t0 = t_match0.group(1).strip() if t_match0 else ""

                    if t0:
                        di_txt = _extract_tag(t0, "detected_items_json")
                        if di_txt:
                            try:
                                txt = str(di_txt or "").strip()
                                start = txt.find("[")
                                end = txt.rfind("]")
                                if start != -1 and end != -1 and end > start:
                                    txt = txt[start : end + 1]
                                parsed = json.loads(txt)
                                if isinstance(parsed, list):
                                    for it in parsed:
                                        if not isinstance(it, dict):
                                            continue
                                        pid = str(it.get("product_id") or "").strip()
                                        if _is_stable_product_id(pid):
                                            stable_pid = pid
                                            break
                            except Exception:
                                pass

                        if not stable_pid:
                            try:
                                tp0 = _parse_thinking_schema(t0)
                                cand = str(((tp0 or {}).get("detection") or {}).get("produit") or "").strip()
                                if _is_stable_product_id(cand):
                                    stable_pid = cand
                            except Exception:
                                pass

                        if not stable_pid:
                            det_prod_raw = _extract_tag(t0, "detected_product")
                            det_prod = str(det_prod_raw or "").strip()
                            if det_prod:
                                try:
                                    mapped = _map_product_name_to_pid(company_id, det_prod)
                                except Exception:
                                    mapped = ""
                                if _is_stable_product_id(mapped):
                                    stable_pid = mapped
                                    stable_label = det_prod

                    if stable_pid:
                        try:
                            order_tracker.set_custom_meta(user_id, "active_product_id", stable_pid)
                            if stable_label:
                                order_tracker.set_custom_meta(user_id, "active_product_label", stable_label)
                        except Exception:
                            pass

                        second_pass_attempted = True

                        final_prompt_2 = await self.prompt_system.build_prompt(
                            query=query,
                            user_id=user_id,
                            company_id=company_id,
                            detected_location=dynamic_context.get('detected_location'),
                            shipping_fee=dynamic_context.get('shipping_fee'),
                            delivery_time=dynamic_context.get('delivery_time'),
                            product_context=dynamic_context.get('product_context', ''),
                            pricing_context=dynamic_context.get('pricing_context', ''),
                            conversation_history=str(dynamic_context.get('conversation_history') or ''),
                            instruction_block=instruction_block,
                            validation_errors_block=validation_errors_block,
                            price_calculation_block=price_calculation_block,
                            catalogue_reference_block=(
                                catalogue_reference_block_override
                                if str(catalogue_reference_block_override or "").strip()
                                else "\n".join(
                                    [
                                        ln
                                        for ln in str(dynamic_context.get('product_context', '') or '').splitlines()
                                        if ln.strip()
                                        and (not str(ln).upper().startswith('PAYMENT_VERDICT'))
                                        and (not str(ln).upper().startswith('PHONE_VERDICT'))
                                        and (not str(ln).upper().startswith('LOCATION_VERDICT'))
                                        and (not str(ln).upper().startswith('VISION_GEMINI'))
                                    ]
                                ).strip()
                            ),
                            has_image=bool(images and len(images) > 0),
                        )

                        print(f"🔁 [LLM_SECOND_PASS] product_id='{stable_pid}' | prompt_chars={len(final_prompt_2)}")

                        llm_result_2 = await self.llm_client.complete(
                            prompt=final_prompt_2,
                            model_name=model_name,
                            temperature=0.2,
                            top_p=0.7,
                            max_tokens=max_tokens_cfg,
                            frequency_penalty=0.0,
                        )

                        if isinstance(llm_result_2, dict):
                            response = llm_result_2.get("response", llm_result_2)
                        else:
                            response = llm_result_2

                        raw_llm_output = str(response or "")
            except Exception as _second_e:
                print(f"⚠️ [LLM_SECOND_PASS] error: {type(_second_e).__name__}: {_second_e}")

            # Extraire <thinking>
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_llm_output, re.DOTALL | re.IGNORECASE)
            if thinking_match:
                thinking = thinking_match.group(1).strip()
                thinking_parsed = _parse_thinking_schema(thinking)

                try:
                    tool_call_raw = _extract_tag(thinking, "tool_call")
                    if tool_call_raw:
                        tool_call_req = _coerce_json_obj(tool_call_raw)
                except Exception:
                    tool_call_req = None

                if not tool_call_req:
                    try:
                        m_tc = re.search(
                            r"\{.*?\"action\"\s*:\s*\"SEND_PRICE_LIST\".*?\}",
                            str(thinking or ""),
                            flags=re.IGNORECASE | re.DOTALL,
                        )
                        if m_tc:
                            tool_call_req = _coerce_json_obj(m_tc.group(0))
                    except Exception:
                        pass

                def _is_price_list_request(*, thinking_text: str, tool_req: Any) -> bool:
                    try:
                        if isinstance(tool_req, dict):
                            act = str(tool_req.get("action") or "").strip().upper()
                            if act == "SEND_PRICE_LIST":
                                return True
                    except Exception:
                        pass
                    try:
                        t = str(thinking_text or "")
                    except Exception:
                        t = ""
                    if not t.strip():
                        return False
                    if re.search(r"<tool_call>.*?SEND_PRICE_LIST.*?</tool_call>", t, flags=re.IGNORECASE | re.DOTALL):
                        return True
                    if re.search(r"\"action\"\s*:\s*\"SEND_PRICE_LIST\"", t, flags=re.IGNORECASE):
                        return True
                    return False

                def _extract_maj_action(thinking_text: str) -> str:
                    try:
                        t = str(thinking_text or "")
                    except Exception:
                        t = ""
                    if not t.strip():
                        return ""
                    m = re.search(r"<maj>.*?<action>(.*?)</action>.*?</maj>", t, flags=re.IGNORECASE | re.DOTALL)
                    return str(m.group(1) or "").strip().upper() if m else ""

                print(f"{C_YELLOW}🧠 [THINKING] {len(thinking)} chars{C_RESET}")
                print(f"{C_YELLOW}{'='*80}{C_RESET}")
                print(f"{C_YELLOW}{thinking}{C_RESET}")
                print(f"{C_YELLOW}{'='*80}{C_RESET}")

                def _normalize_packaging_items(items: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
                    """Normalise des formulations type "lot/pack/carton/colis de N".

                    Objectif: éviter les erreurs qty/unit quand le client exprime un conditionnement.
                    Ex: "LOT de 6 paquets" => qty=1, unit="lot" (si le LLM a renvoyé qty=6, unit="paquet").

                    Règle générique (scalable): uniquement basée sur le texte utilisateur.
                    """
                    try:
                        msg = str(message or "")
                        msg_l = msg.lower()

                        m = re.search(r"\b(lot|pack|carton|colis)[\s_-]*(?:de\s*)?(\d+)\b", msg_l)
                        if not m:
                            return items

                        pack_unit = str(m.group(1) or "").strip().lower()
                        pack_n = int(m.group(2))

                        normalized: List[Dict[str, Any]] = []
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            qty = it.get("qty")
                            unit = str(it.get("unit") or "").strip().lower()

                            if isinstance(qty, int) and qty == pack_n and unit in {"paquet", "paquets", "pack", "packs"}:
                                it2 = dict(it)
                                it2["qty"] = 1
                                it2["unit"] = pack_unit
                                normalized.append(it2)
                            else:
                                normalized.append(it)

                        return normalized
                    except Exception:
                        return items

                # Extraire <detected_items_json> (JSON strict) et persister pour validation/pricing
                try:
                    detected_items_json_text = _extract_tag(thinking, "detected_items_json")
                    if detected_items_json_text:
                        try:
                            txt = str(detected_items_json_text or "").strip()
                            parsed_items = json.loads(txt)
                            if isinstance(parsed_items, list):
                                items_raw_to_persist = detected_items_json_text
                                try:
                                    parsed_items = _normalize_packaging_items(parsed_items, query)
                                except Exception:
                                    pass

                                cat_container = None
                                try:
                                    cat_container = get_company_catalog_v2(company_id)
                                except Exception:
                                    cat_container = None

                                parsed_items = normalize_detected_items(
                                    company_id=company_id,
                                    items=parsed_items,
                                    message=query,
                                    catalog_container=cat_container,
                                )

                                # Pivot panier: ne pas écraser un panier existant sans intention explicite.
                                # Si le message n'indique pas clairement AJOUT/MODIFICATION, on demande A/B.

                                def _extract_first_item_sig(items: List[Dict[str, Any]]) -> Tuple[str, str]:
                                    try:
                                        for it in (items or []):
                                            if not isinstance(it, dict):
                                                continue
                                            pid = str(it.get("product_id") or "").strip()
                                            var = str(it.get("variant") or "").strip()
                                            if pid or var:
                                                return pid, var
                                    except Exception:
                                        pass
                                    return "", ""

                                def _infer_cart_change_intent(msg: str) -> str:
                                    try:
                                        s = str(msg or "").lower()
                                    except Exception:
                                        s = ""
                                    if not s.strip():
                                        return ""
                                    # add
                                    if re.search(r"\b(ajout|ajoute|ajouter|en\s*plus|aussi|rajoute|rajouter|mets\s+aussi|ajouter\s+au\s+panier)\b", s, flags=re.IGNORECASE):
                                        return "add"
                                    # modify
                                    if re.search(r"\b(change|changer|remplace|remplacer|finalement|plut[oô]t|au\s+lieu|modif|modifier|annule|annuler|retire|retirer)\b", s, flags=re.IGNORECASE):
                                        return "modify"
                                    return ""

                                def _dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                                    out: List[Dict[str, Any]] = []
                                    seen = set()
                                    for it in (items or []):
                                        if not isinstance(it, dict):
                                            continue
                                        pid = str(it.get("product_id") or "").strip()
                                        var = str(it.get("variant") or "").strip()
                                        spec = str(it.get("spec") or "").strip()
                                        unit = str(it.get("unit") or "").strip()
                                        k = (pid.lower(), var.lower(), spec.lower(), unit.lower())
                                        if k in seen:
                                            continue
                                        seen.add(k)
                                        out.append(it)
                                    return out

                                def _items_are_informational(items: List[Dict[str, Any]]) -> bool:
                                    try:
                                        xs = [it for it in (items or []) if isinstance(it, dict)]
                                        if not xs:
                                            return False
                                        for it in xs:
                                            if it.get("qty") not in (None, "", 0):
                                                return False
                                        return True
                                    except Exception:
                                        return False

                                try:
                                    cur_items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                                    cur_items = cur_items if isinstance(cur_items, list) else []

                                    cur_state_details = ""
                                    cur_state_variant = ""
                                    try:
                                        st0 = order_tracker.get_state(user_id)
                                        cur_state_details = str(getattr(st0, "produit_details", "") or "").strip()
                                    except Exception:
                                        cur_state_details = ""

                                    try:
                                        s_l = cur_state_details.lower()
                                        # Catalog-driven variant detection
                                        _cat_csv = None
                                        try:
                                            _cat_csv = get_company_catalog_v2(company_id) if company_id else None
                                        except Exception:
                                            _cat_csv = None
                                        _vt_csv = _cat_csv.get("v") if isinstance(_cat_csv, dict) and isinstance(_cat_csv.get("v"), dict) else None
                                        if isinstance(_vt_csv, dict):
                                            for _vk in _vt_csv.keys():
                                                _vk_s = str(_vk or "").strip()
                                                if _vk_s and _vk_s.lower() in s_l:
                                                    cur_state_variant = _vk_s
                                                    break
                                        # Legacy fallback
                                        if not cur_state_variant:
                                            if "culotte" in s_l:
                                                cur_state_variant = "Culotte"
                                            elif "pression" in s_l:
                                                cur_state_variant = "Pression"
                                    except Exception:
                                        cur_state_variant = ""

                                    cur_pid, cur_var = _extract_first_item_sig(cur_items)
                                    new_pid, new_var = _extract_first_item_sig(parsed_items if isinstance(parsed_items, list) else [])

                                    has_existing_cart = bool(cur_items) or bool(cur_state_variant) or bool(cur_state_details)

                                    pivot = bool(
                                        (cur_pid and new_pid and cur_pid.strip().lower() != new_pid.strip().lower())
                                        or (cur_var and new_var and cur_var.strip().lower() != new_var.strip().lower())
                                        or (cur_state_variant and new_var and cur_state_variant.strip().lower() != new_var.strip().lower())
                                    )

                                    is_price_tool = _is_price_list_request(thinking_text=thinking, tool_req=tool_call_req)
                                    if is_price_tool:
                                        try:
                                            order_tracker.set_custom_meta(user_id, "detected_items_price_probe", parsed_items)
                                            order_tracker.set_custom_meta(user_id, "detected_items_price_probe_raw", detected_items_json_text)
                                        except Exception:
                                            pass
                                        try:
                                            items_raw_to_persist = str(
                                                order_tracker.get_custom_meta(user_id, "detected_items_raw", default="") or ""
                                            )
                                        except Exception:
                                            items_raw_to_persist = str(items_raw_to_persist or "")
                                        parsed_items = cur_items

                                    if pivot and has_existing_cart and (not is_price_tool):
                                        intent = _infer_cart_change_intent(query)

                                        maj_action = _extract_maj_action(thinking)

                                        if not intent:
                                            try:
                                                order_tracker.set_custom_meta(user_id, "pending_cart_items", parsed_items)
                                                order_tracker.set_custom_meta(user_id, "pending_cart_question", "add_or_modify")
                                            except Exception:
                                                pass
                                            # ── CartManager: stocker en pending_pivot ──
                                            try:
                                                if isinstance(parsed_items, list) and parsed_items:
                                                    self.cart_manager.set_pending_pivot(user_id, parsed_items[0])
                                            except Exception:
                                                pass

                                            processing_time = (time.time() - start_time) * 1000
                                            checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                                            new_label = ""
                                            try:
                                                pid_x, var_x = _extract_first_item_sig(parsed_items)
                                                sp_x = ""
                                                try:
                                                    for _it in (parsed_items or []):
                                                        if isinstance(_it, dict):
                                                            sp_x = str(_it.get("spec") or "").strip()
                                                            if sp_x:
                                                                break
                                                except Exception:
                                                    sp_x = ""
                                                new_label = (str(var_x or "").strip() + (" " + sp_x if sp_x else "")).strip()
                                            except Exception:
                                                new_label = ""

                                            cur_label = ""
                                            try:
                                                itc0 = cur_items[0] if cur_items and isinstance(cur_items[0], dict) else {}
                                                cur_v = str((itc0 or {}).get("variant") or "").strip()
                                                cur_s = str((itc0 or {}).get("spec") or "").strip()
                                                cur_label = (cur_v + (" " + cur_s if cur_s else "")).strip()
                                            except Exception:
                                                cur_label = ""
                                            if not cur_label:
                                                cur_label = cur_state_details

                                            forced_q = "On ajoute au panier ou vous modifiez ?"
                                            if cur_label and new_label:
                                                forced_q = f"Vous modifiez votre panier ({cur_label}) pour {new_label} ou on ajoute ?"
                                            elif new_label:
                                                forced_q = f"On ajoute {new_label} au panier ou vous modifiez ?"

                                            try:
                                                order_tracker.set_custom_meta(user_id, "backend_forced_pivot", maj_action != "CLARIFY_PIVOT")
                                                order_tracker.set_custom_meta(user_id, "backend_forced_pivot_maj_action", maj_action)
                                            except Exception:
                                                pass

                                            return SimplifiedRAGResult(
                                                response=forced_q,
                                                confidence=1.0,
                                                processing_time_ms=processing_time,
                                                checklist_state=checklist.to_string(),
                                                next_step=checklist.get_next_step(),
                                                detected_location=None,
                                                shipping_fee=None,
                                                usage=None,
                                                prompt_tokens=int(prompt_tokens or 0),
                                                completion_tokens=int(completion_tokens or 0),
                                                total_tokens=int(total_tokens or 0),
                                                cost=float(cost or 0.0),
                                                model="python_cart_change_clarify",
                                                thinking=thinking,
                                            )

                                        if intent == "add":
                                            try:
                                                parsed_items = _dedupe_items((cur_items or []) + (parsed_items or []))
                                            except Exception:
                                                pass
                                        # intent == 'modify' => keep parsed_items
                                except Exception:
                                    pass

                                order_tracker.set_custom_meta(user_id, "detected_items", parsed_items)
                                try:
                                    order_tracker.set_custom_meta(user_id, "detected_items_raw", items_raw_to_persist)
                                except Exception:
                                    order_tracker.set_custom_meta(user_id, "detected_items_raw", detected_items_json_text)
                                order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                                print(f"✅ [ITEMS_JSON] parsed_items={len(parsed_items)}")

                                # ── CartManager: upsert panier selon <maj><action> ──
                                try:
                                    maj_action_now = _extract_maj_action(thinking)
                                    if maj_action_now and isinstance(parsed_items, list) and parsed_items:
                                        self.cart_manager.upsert_from_items_json(
                                            user_id=user_id,
                                            items=parsed_items,
                                            action=maj_action_now,
                                        )
                                        print(f"🛒 [CART] upsert action={maj_action_now} items={len(parsed_items)}")

                                        # ── FIX: Après DELETE/UPDATE, synchroniser OrderStateTracker depuis CartManager ──
                                        # CartManager = source de vérité. OrderStateTracker doit refléter le panier réel.
                                        if maj_action_now in ("DELETE", "UPDATE"):
                                            try:
                                                _real_cart = self.cart_manager.get_cart(user_id)
                                                _real_items = _real_cart.get("items", []) if isinstance(_real_cart, dict) else []

                                                if _real_items:
                                                    # Reconstruire SPECS depuis items restants
                                                    _specs_parts = []
                                                    _pids = set()
                                                    for _ri in _real_items:
                                                        if not isinstance(_ri, dict):
                                                            continue
                                                        _rv = str(_ri.get("variant") or "").strip()
                                                        _rs = str(_ri.get("spec") or _ri.get("specs") or "").strip().upper()
                                                        _rp = str(_ri.get("product_id") or "").strip()
                                                        if _rp:
                                                            _pids.add(_rp)
                                                        _label = (_rv + (" " + _rs if _rs else "")).strip()
                                                        if _label:
                                                            _specs_parts.append(_label)
                                                    _new_specs = ", ".join(_specs_parts)
                                                    order_tracker.update_produit_details(user_id, _new_specs, source="CART_SYNC", confidence=0.95)
                                                    # Clear global quantité (multi-items or changed)
                                                    order_tracker.update_quantite(user_id, "", source="CART_SYNC", confidence=0.9)
                                                    # Update produit if single pid
                                                    if len(_pids) == 1:
                                                        order_tracker.update_produit(user_id, list(_pids)[0], source="CART_SYNC", confidence=0.95)
                                                    print(f"✅ [CART_SYNC] OrderState synced after {maj_action_now} | specs='{_new_specs}' | items={len(_real_items)}")

                                                    # Override parsed_items with real cart for downstream items_slot_summary
                                                    parsed_items = _real_items
                                                else:
                                                    # Panier vide → reset produit/specs/quantité
                                                    order_tracker.update_produit_details(user_id, "", source="CART_SYNC_EMPTY", confidence=0.95)
                                                    order_tracker.update_quantite(user_id, "", source="CART_SYNC_EMPTY", confidence=0.95)
                                                    order_tracker.update_produit(user_id, "", source="CART_SYNC_EMPTY", confidence=0.95)
                                                    parsed_items = []
                                                    print(f"🧹 [CART_SYNC] OrderState cleared (cart empty after {maj_action_now})")

                                                # Invalider le cache price_calculation_block (stale après modif panier)
                                                order_tracker.set_custom_meta(user_id, "price_calculation_block", "")
                                                order_tracker.set_custom_meta(user_id, "last_total_snapshot", None)
                                                print(f"🗑️ [CART_SYNC] price_calculation_block cache invalidated")
                                            except Exception as _sync_e:
                                                print(f"⚠️ [CART_SYNC] error: {type(_sync_e).__name__}: {_sync_e}")
                                except Exception as _cart_upsert_e:
                                    print(f"⚠️ [CART] upsert error: {type(_cart_upsert_e).__name__}: {_cart_upsert_e}")

                                # Hot-swap product context: persist the current active product id/label.
                                try:
                                    active_pid = ""
                                    for it in parsed_items:
                                        if not isinstance(it, dict):
                                            continue
                                        pid = str(it.get("product_id") or "").strip()
                                        if pid:
                                            active_pid = pid
                                            break
                                    if active_pid:
                                        order_tracker.set_custom_meta(user_id, "active_product_id", active_pid)

                                        try:
                                            if re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", str(active_pid), flags=re.IGNORECASE):
                                                st_now = order_tracker.get_state(user_id)
                                                if not str(getattr(st_now, "produit", "") or "").strip():
                                                    order_tracker.update_produit(user_id, str(active_pid), source="ITEMS_JSON", confidence=0.95)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                                # Fallback tool pricing (scalable): si intention=prix et product_id+variant détectés,
                                # on envoie la liste de prix immédiatement même si unit/spec/qty sont null.
                                try:
                                    if (
                                        (not order_tracker.get_flag(user_id, "awaiting_price_choice"))
                                        and _is_price_intent(query)
                                        and (not _is_price_list_request(thinking_text=thinking, tool_req=tool_call_req))
                                    ):
                                        v_pid = ""
                                        v_variant = ""
                                        for it in parsed_items:
                                            if not isinstance(it, dict):
                                                continue
                                            v_pid = str(it.get("product_id") or "").strip()
                                            v_variant = str(it.get("variant") or "").strip()
                                            if v_pid and v_variant:
                                                break

                                        if v_pid and v_variant and re.fullmatch(
                                            r"prod_[a-z0-9_\-]{6,80}", str(v_pid), flags=re.IGNORECASE
                                        ):
                                            list_text, list_items = _generate_price_list_for_tool_call(
                                                company_id_val=company_id,
                                                product_id_val=v_pid,
                                                variant_val=v_variant,
                                                spec_val=None,
                                            )
                                            if list_text and list_items:
                                                try:
                                                    order_tracker.set_custom_meta(user_id, "price_list_text", list_text)
                                                    order_tracker.set_custom_meta(user_id, "price_list_items", list_items)
                                                    order_tracker.set_flag(user_id, "awaiting_price_choice", True)
                                                except Exception:
                                                    pass

                                                processing_time = (time.time() - start_time) * 1000
                                                checklist = self.prompt_system.get_checklist_state(user_id, company_id)
                                                return SimplifiedRAGResult(
                                                    response=list_text,
                                                    confidence=0.95,
                                                    processing_time_ms=processing_time,
                                                    checklist_state=checklist.to_string(),
                                                    next_step=checklist.get_next_step(),
                                                    detected_location=None,
                                                    shipping_fee=None,
                                                    usage=None,
                                                    prompt_tokens=int(prompt_tokens or 0),
                                                    completion_tokens=int(completion_tokens or 0),
                                                    total_tokens=int(total_tokens or 0),
                                                    cost=float(cost or 0.0),
                                                    model="python_price_list_post_llm_fallback",
                                                    thinking=thinking,
                                                )
                                except Exception:
                                    pass

                                # Source de vérité: dériver un résumé de slots depuis items.
                                # Mono item => remplir PRODUIT/SPECS/QUANTITÉ.
                                # Multi items => remplir PRODUIT/SPECS (résumé) et vider QUANTITÉ globale.
                                try:
                                    items_summary: Dict[str, Any] = {
                                        "has_items": False,
                                        "count": 0,
                                        "produit": "",
                                        "specs": "",
                                        "quantite": "",
                                        "is_multi": False,
                                    }

                                    clean_items = [it for it in parsed_items if isinstance(it, dict)]
                                    items_summary["has_items"] = bool(clean_items)
                                    items_summary["count"] = len(clean_items)
                                    items_summary["is_multi"] = len(clean_items) > 1

                                    def _norm(s: Any) -> str:
                                        return str(s or "").strip()

                                    if len(clean_items) == 1:
                                        it0 = clean_items[0]
                                        pid0 = _norm(it0.get("product_id"))
                                        # Important: `product` can represent a VARIANT (e.g. "culottes") and must never be
                                        # used as a fallback product id/label.
                                        items_summary["produit"] = pid0 if re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", pid0, flags=re.IGNORECASE) else ""
                                        variant0 = _norm(it0.get("variant")).strip()
                                        base_specs0 = _norm(it0.get("spec")).upper() or _norm(it0.get("specs")).upper()
                                        items_summary["specs"] = (variant0 + (" " + base_specs0 if base_specs0 else "")).strip() if variant0 else base_specs0
                                        q = it0.get("qty")
                                        u = _norm(it0.get("unit")).lower()
                                        if isinstance(q, int) and q > 0 and u:
                                            items_summary["quantite"] = f"{q} {u}".strip()
                                    elif len(clean_items) > 1:
                                        prods = []
                                        specs_list = []
                                        for it in clean_items:
                                            pid_i = _norm(it.get("product_id"))
                                            p = pid_i if re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", pid_i, flags=re.IGNORECASE) else ""
                                            v = _norm(it.get("variant")).strip()
                                            s0 = _norm(it.get("spec")).upper() or _norm(it.get("specs")).upper()
                                            s = (v + (" " + s0 if s0 else "")).strip() if v else s0
                                            if p:
                                                prods.append(p)
                                            if s:
                                                specs_list.append(s)

                                        uniq_prods = sorted(list({p for p in prods if p}))
                                        items_summary["produit"] = " + ".join(uniq_prods)
                                        items_summary["specs"] = ", ".join([s for s in specs_list if s])
                                        items_summary["quantite"] = ""  # multi-items => quantité globale vide

                                    order_tracker.set_custom_meta(user_id, "items_slot_summary", items_summary)
                                except Exception as _sum_e:
                                    order_tracker.set_custom_meta(user_id, "items_slot_summary", {})
                                    print(f"⚠️ [ITEMS_JSON] summary error: {type(_sum_e).__name__}: {_sum_e}")
                            else:
                                order_tracker.set_custom_meta(user_id, "detected_items", [])
                                order_tracker.set_custom_meta(user_id, "detected_items_raw", detected_items_json_text)
                                order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "not_a_list")
                                print(f"⚠️ [ITEMS_JSON] not a list")
                        except Exception as e:
                            # Tolérance: certains modèles mettent des commentaires/texte dans le tag.
                            # On tente d'extraire le premier tableau JSON [...] avant de fallback.
                            try:
                                txt2 = str(detected_items_json_text or "")
                                start = txt2.find("[")
                                end = txt2.rfind("]")
                                if start != -1 and end != -1 and end > start:
                                    cand = txt2[start : end + 1]
                                    parsed_items = json.loads(cand)
                                    if isinstance(parsed_items, list):
                                        parsed_items = _normalize_packaging_items(parsed_items, query)
                                        try:
                                            cat_container = None
                                            try:
                                                cat_container = get_company_catalog_v2(company_id)
                                            except Exception:
                                                cat_container = None

                                            parsed_items = normalize_detected_items(
                                                company_id=company_id,
                                                items=parsed_items,
                                                message=query,
                                                catalog_container=cat_container,
                                            )
                                        except Exception:
                                            pass
                                        order_tracker.set_custom_meta(user_id, "detected_items", parsed_items)
                                        order_tracker.set_custom_meta(user_id, "detected_items_raw", cand)
                                        order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                                        print(f"✅ [ITEMS_JSON] parsed_items={len(parsed_items)}")
                                    else:
                                        order_tracker.set_custom_meta(user_id, "detected_items", [])
                                        order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                                        order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "not_a_list")
                                else:
                                    order_tracker.set_custom_meta(user_id, "detected_items", [])
                                    order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                                    order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                            except Exception:
                                order_tracker.set_custom_meta(user_id, "detected_items", [])
                                order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                                order_tracker.set_custom_meta(user_id, "detected_items_parse_error", "")
                    else:
                        order_tracker.set_custom_meta(user_id, "detected_items_raw", "")
                except Exception as e:
                    print(f"⚠️ [ITEMS_JSON] extraction error: {type(e).__name__}: {e}")

                # Post-LLM: si le JSON items est vide/ambigu, on tente de récupérer le produit depuis d'autres indices.
                # (Ex: <detected_product>Couches bebe</detected_product> ou 'Catalogue propose: Couches bebe (0-25kg)')
                try:
                    mapped_pid = ""
                    mapped_label = ""

                    det_prod_raw = _extract_tag(thinking, "detected_product")
                    det_prod = str(det_prod_raw or "").strip()
                    if det_prod:
                        if re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", det_prod, flags=re.IGNORECASE):
                            mapped_pid = det_prod
                            mapped_label = det_prod
                        else:
                            mapped_pid = _map_product_name_to_pid(company_id, det_prod)
                            mapped_label = det_prod

                    if not mapped_pid:
                        m = re.search(r"Catalogue\s+propose\s*:\s*([^\n\r<]{2,160})", thinking, flags=re.IGNORECASE)
                        if m:
                            cand = str(m.group(1) or "").strip()
                            if cand:
                                mapped_pid = _map_product_name_to_pid(company_id, cand)
                                mapped_label = cand

                    if mapped_pid:
                        current_prod = ""
                        try:
                            st_now = order_tracker.get_state(user_id)
                            current_prod = str(getattr(st_now, "produit", "") or "").strip()
                        except Exception:
                            current_prod = ""

                        if not current_prod:
                            order_tracker.update_produit(user_id, mapped_pid, source="POST_LLM_NAME_MAP", confidence=0.85)
                            order_tracker.set_custom_meta(user_id, "active_product_id", mapped_pid)
                            order_tracker.set_custom_meta(user_id, "active_product_label", mapped_label)
                            print(f"✅ [POST_LLM_NAME_MAP] product_id={mapped_pid} product='{mapped_label}'")
                except Exception as _map_e:
                    print(f"⚠️ [POST_LLM_NAME_MAP] error: {type(_map_e).__name__}: {_map_e}")

                # Mise à jour OrderStateTracker depuis le thinking avec fusion intelligente
                try:
                    det = thinking_parsed.get("detection") if isinstance(thinking_parsed, dict) else {}
                    if isinstance(det, dict):
                        # Récupérer l'état actuel pour fusion intelligente
                        current_state = order_tracker.get_state(user_id)

                        def _extract_variant_from_details(txt: str) -> str:
                            try:
                                s = str(txt or "")
                            except Exception:
                                s = ""
                            s_l = s.lower()
                            if not s_l:
                                return ""
                            # Catalog-driven: match against vtree keys
                            try:
                                _cat_evd = get_company_catalog_v2(company_id) if company_id else None
                                _vt_evd = _cat_evd.get("v") if isinstance(_cat_evd, dict) and isinstance(_cat_evd.get("v"), dict) else None
                                if isinstance(_vt_evd, dict):
                                    for _vk in _vt_evd.keys():
                                        _vk_s = str(_vk or "").strip()
                                        if _vk_s and _vk_s.lower() in s_l:
                                            return _vk_s
                            except Exception:
                                pass
                            # Legacy fallback
                            if "culotte" in s_l:
                                return "Culotte"
                            if "pression" in s_l:
                                return "Pression"
                            return ""

                        def _is_unit_allowed(*, pid: str, variant: str, spec: str, unit: str) -> bool:
                            try:
                                pid_s = str(pid or "").strip()
                                v_s = str(variant or "").strip()
                                u_s = str(unit or "").strip()
                                if not pid_s or not v_s or not u_s:
                                    return True

                                cat = None
                                try:
                                    cat = get_company_product_catalog_v2(company_id, pid_s)
                                except Exception:
                                    cat = None
                                if not isinstance(cat, dict):
                                    return True
                                vtree = cat.get("v") if isinstance(cat.get("v"), dict) else {}
                                if not isinstance(vtree, dict) or not vtree:
                                    return True

                                node = vtree.get(v_s)
                                if not isinstance(node, dict):
                                    # try case-insensitive match
                                    for k in list(vtree.keys()):
                                        if str(k).strip().lower() == v_s.lower():
                                            node = vtree.get(k)
                                            break
                                if not isinstance(node, dict):
                                    return True

                                spec_s = str(spec or "").strip()
                                if spec_s:
                                    s_map = node.get("s") if isinstance(node.get("s"), dict) else None
                                    if isinstance(s_map, dict) and s_map:
                                        sn = s_map.get(spec_s)
                                        if not isinstance(sn, dict):
                                            # try case-insensitive
                                            for sk in list(s_map.keys()):
                                                if str(sk).strip().lower() == spec_s.lower():
                                                    sn = s_map.get(sk)
                                                    break
                                        if isinstance(sn, dict):
                                            u_map = sn.get("u") if isinstance(sn.get("u"), dict) else None
                                            if isinstance(u_map, dict) and u_map:
                                                return u_s in {str(x).strip() for x in u_map.keys()}

                                u_map0 = node.get("u") if isinstance(node.get("u"), dict) else None
                                if isinstance(u_map0, dict) and u_map0:
                                    return u_s in {str(x).strip() for x in u_map0.keys()}
                            except Exception:
                                return True
                            return True

                        # Pivot protection (scalable): si le LLM pivote de variante/format (ex: Culotte -> Pression)
                        # on nettoie les slots dépendants pour éviter carry-over.
                        try:
                            di0 = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                        except Exception:
                            di0 = []
                        try:
                            if isinstance(di0, list) and len(di0) == 1 and isinstance(di0[0], dict):
                                new_pid = str(di0[0].get("product_id") or "").strip()
                                new_variant = str(di0[0].get("variant") or "").strip()
                                new_spec = str(di0[0].get("spec") or di0[0].get("specs") or "").strip()
                                new_unit = str(di0[0].get("unit") or "").strip()

                                old_variant = _extract_variant_from_details(str(getattr(current_state, "produit_details", "") or ""))

                                if old_variant and new_variant and old_variant != new_variant:
                                    if not _is_price_list_request(thinking_text=thinking, tool_req=tool_call_req):
                                        # ── PIVOT FREEZE: ne PAS reset si CLARIFY_PIVOT ou pending pivot actif ──
                                        _maj_action_pivot = _extract_maj_action(thinking)
                                        _pending_q2 = ""
                                        _cart_pending = False
                                        try:
                                            _pending_q2 = str(order_tracker.get_custom_meta(user_id, "pending_cart_question", default="") or "").strip()
                                        except Exception:
                                            _pending_q2 = ""
                                        try:
                                            _cart_pending = self.cart_manager.has_pending_pivot(user_id)
                                        except Exception:
                                            _cart_pending = False

                                        if _maj_action_pivot == "CLARIFY_PIVOT" or _pending_q2 or _cart_pending:
                                            # Freeze: stocker le nouvel item en pending_pivot au lieu de reset
                                            try:
                                                if isinstance(di0, list) and di0 and isinstance(di0[0], dict):
                                                    self.cart_manager.set_pending_pivot(user_id, di0[0])
                                            except Exception:
                                                pass
                                            print(f"🛑 [ORDER_STATE] pivot_FREEZE (no reset) variant {old_variant} -> {new_variant}")
                                        else:
                                            order_tracker.update_produit_details(user_id, "", source="PIVOT_RESET", confidence=0.9)
                                            order_tracker.update_quantite(user_id, "", source="PIVOT_RESET", confidence=0.9)
                                            print(f"🧹 [ORDER_STATE] pivot_reset variant {old_variant} -> {new_variant}")

                                # If unit is not allowed for the new variant/spec, clear global quantity.
                                if str(getattr(current_state, "quantite", "") or "").strip():
                                    # parse current global unit from 'qty unit'
                                    cur_q = str(getattr(current_state, "quantite", "") or "").strip().lower()
                                    m_q = re.search(r"\b([a-z_]+\d*)\b", cur_q)
                                    cur_unit_guess = m_q.group(1).strip() if m_q else ""
                                    if new_pid and new_variant and cur_unit_guess and (not _is_unit_allowed(pid=new_pid, variant=new_variant, spec=new_spec, unit=cur_unit_guess)):
                                        order_tracker.update_quantite(user_id, "", source="PIVOT_UNIT_NOT_ALLOWED", confidence=0.9)
                                        print(f"🧹 [ORDER_STATE] QUANTITÉ cleared (unit_not_allowed): {cur_unit_guess}")
                        except Exception:
                            pass

                        # Si le LLM a détecté plusieurs items (multi-produits/tailles),
                        # la quantité globale ne doit pas rester (sinon carryover: "3 paquets").
                        try:
                            di = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                            if isinstance(di, list) and len(di) > 1:
                                if str(getattr(current_state, "quantite", "") or "").strip():
                                    order_tracker.update_quantite(user_id, "", source="LLM_INFERRED", confidence=0.6)
                                    print("🧹 [ORDER_STATE] QUANTITÉ cleared (multi_items)")
                        except Exception:
                            pass
                        
                        # Hiérarchie stricte:
                        # - Si detected_items_json est présent => SOURCE DE VÉRITÉ pour PRODUIT/SPECS/QUANTITÉ.
                        # - <detection> ne sert qu'au reste (ZONE/TÉLÉPHONE/PAIEMENT) et au résumé humain.
                        try:
                            items_summary = order_tracker.get_custom_meta(user_id, "items_slot_summary", default={})
                        except Exception:
                            items_summary = {}

                        use_items_as_truth = bool(isinstance(items_summary, dict) and items_summary.get("has_items"))

                        produit = str(items_summary.get("produit") or "").strip() if use_items_as_truth else str(det.get("produit") or "").strip()
                        specs = str(items_summary.get("specs") or "").strip() if use_items_as_truth else str(det.get("specs") or "").strip()
                        quantite = str(items_summary.get("quantite") or "").strip() if use_items_as_truth else str(det.get("quantite") or "").strip()
                        prix_cite = str(det.get("prix_cite") or "").strip()

                        zone = str(det.get("zone") or "").strip()
                        telephone = str(det.get("telephone") or "").strip()
                        paiement = str(det.get("paiement") or "").strip()

                        def _normalize_ci_phone(raw: str) -> str:
                            try:
                                s = str(raw or "").strip()
                                if not s or s in {"∅", "Ø", "N/A"}:
                                    return ""
                                digits = re.sub(r"\D+", "", s)
                                if not digits:
                                    return ""

                                # Cas +225XXXXXXXXXX (13 digits)
                                if digits.startswith("225") and len(digits) == 13:
                                    digits = digits[3:]  # -> 10 digits (ex: 0160824536)

                                # Accepter uniquement le format local 0XXXXXXXXX
                                if re.fullmatch(r"0\d{9}", digits):
                                    return digits
                                return ""
                            except Exception:
                                return ""
                        
                        # PRODUIT: doit rester un ID technique stable (prod_...).
                        # IMPORTANT: le LLM peut renvoyer une variante (ex: "culottes", "pressions") dans det['produit'].
                        # Dans ce cas, on ne doit PAS écraser le produit persisté.
                        def _is_stable_product_id(v: str) -> bool:
                            try:
                                return bool(re.fullmatch(r"prod_[a-z0-9_\-]{6,80}", str(v or "").strip(), flags=re.IGNORECASE))
                            except Exception:
                                return False

                        produit_candidate = str(produit or "").strip()
                        if produit_candidate and produit_candidate != "∅":
                            if _is_stable_product_id(produit_candidate):
                                if use_items_as_truth:
                                    order_tracker.update_produit(user_id, produit_candidate, source="ITEMS_JSON", confidence=0.9)
                                else:
                                    if _is_value_mentioned(query or "", produit_candidate):
                                        order_tracker.update_produit(user_id, produit_candidate, source="LLM_INFERRED", confidence=0.6)
                            else:
                                # Route the non-stable product candidate into specs (human readable), never into produit.
                                # Keep existing produit unchanged.
                                try:
                                    existing_specs = str(getattr(current_state, "specs", "") or "").strip()
                                    cand_l = produit_candidate.lower()
                                    if cand_l and cand_l not in existing_specs.lower():
                                        merged = (existing_specs + (" " if existing_specs else "") + produit_candidate).strip()
                                        order_tracker.update_specs(user_id, merged, source="LLM_INFERRED", confidence=0.5)
                                except Exception:
                                    pass
                        
                        # QUANTITÉ: persistance directe si LLM détecte une valeur non-vide
                        # Le LLM a déjà validé l'intention dans <thinking>, on fait confiance
                        ql = str(quantite or "").strip().lower()
                        q_is_nullish = (
                            (not ql)
                            or ql in {"∅", "ø", "n/a"}
                            or "null" in ql
                            or "correction" in ql
                            or "invalide" in ql
                        )

                        # Si le LLM indique explicitement une quantité inconnue/null/correction nécessaire,
                        # on efface la quantité persistée pour éviter de recalculer sur une ancienne valeur.
                        # MAIS: ne PAS effacer si detected_items_json était vide (message = zone/tel/paiement).
                        if q_is_nullish and use_items_as_truth:
                            try:
                                if str(current_state.quantite or "").strip():
                                    order_tracker.update_quantite(user_id, "", source="LLM_INFERRED", confidence=0.4)
                                    print("🧹 [ORDER_STATE] QUANTITÉ cleared (thinking_nullish)")
                            except Exception:
                                pass
                        elif q_is_nullish and not use_items_as_truth:
                            print("🛡️ [ORDER_STATE] QUANTITÉ preserved (no items in thinking, msg likely zone/tel/payment)")

                        if (not q_is_nullish) and quantite and quantite != "∅" and (use_items_as_truth or _is_value_mentioned(query or "", quantite)):
                            # Nettoyer la quantité (enlever parenthèses, commentaires)
                            quantite_clean = re.sub(r"\s*\(.*?\)\s*", "", quantite).strip()
                            if quantite_clean and quantite_clean != str(getattr(current_state, "quantite", "") or "").strip():
                                order_tracker.update_quantite(user_id, quantite_clean, source="LLM_INFERRED", confidence=0.8)
                                print(f"✅ [ORDER_STATE] QUANTITÉ persistée (overwrite): {quantite_clean}")
                        # FUSION: garde l'ancienne quantité si nouvelle = vide
                        
                        # SPECS: nettoyer TOUTE mention de Quantité/Prix
                        if specs and specs != "∅" and (use_items_as_truth or _is_value_mentioned(query or "", specs)):
                            # Supprimer toute mention de "Quantité:" ou "Prix:" dans specs
                            specs_clean = specs
                            # Split par | et ne garder que les parties sans "quantité" ni "prix"
                            parts = [p.strip() for p in specs_clean.split("|")]
                            parts_filtered = []
                            for p in parts:
                                p_low = p.lower()
                                if "quantité" not in p_low and "quantite" not in p_low and "prix" not in p_low:
                                    # Supprimer aussi les commentaires entre parenthèses
                                    p_clean = re.sub(r"\s*\(.*?\)\s*", "", p).strip()
                                    if p_clean:
                                        parts_filtered.append(p_clean)
                            
                            if parts_filtered:
                                specs_final = ", ".join(parts_filtered)
                                # Éviter doublons: ne pas re-sauvegarder si identique
                                if specs_final != current_state.produit_details:
                                    order_tracker.update_produit_details(user_id, specs_final, source="LLM_INFERRED", confidence=0.6)
                        
                        # ZONE: fallback depuis thinking si le tracker ne l'a pas persistée
                        if zone and zone != "∅":
                            zone_clean = re.sub(r"\s*\(.*?\)\s*", "", zone).strip()
                            if zone_clean and not current_state.zone:
                                try:
                                    from core.delivery_zone_extractor import extract_delivery_zone_and_cost, normalize_text

                                    q_norm = normalize_text(str(query or ""))
                                    zone_proof = extract_delivery_zone_and_cost(str(query or ""))
                                    zone_name = str((zone_proof or {}).get("name") or "").strip()
                                    if zone_proof and zone_name:
                                        # Zone reconnue par notre extracteur sur le message utilisateur → preuve suffisante
                                        order_tracker.update_zone(user_id, zone_name, source="CONTEXT_INFERRED", confidence=0.7)
                                        print(f"✅ [ORDER_STATE] ZONE persistée (proof=extractor): {zone_name}")
                                    else:
                                        # Ville/zone non répertoriée: persister uniquement si le texte apparaît dans le message client
                                        zone_norm = normalize_text(zone_clean)
                                        if zone_norm and (zone_norm in q_norm):
                                            order_tracker.update_zone(user_id, zone_clean, source="USER_EXTRACTED", confidence=0.7)
                                            print(f"✅ [ORDER_STATE] ZONE persistée (proof=substring): {zone_clean}")
                                        else:
                                            print(f"⚠️ [ORDER_STATE] ZONE ignorée (no proof in user query): {zone_clean}")
                                except Exception as e:
                                    print(f"⚠️ [ORDER_STATE] ZONE fallback error: {type(e).__name__}: {e}")

                        # TÉLÉPHONE: fallback depuis thinking uniquement si on peut normaliser
                        phone_norm = _normalize_ci_phone(telephone)
                        if phone_norm and not current_state.numero:
                            order_tracker.update_numero(user_id, phone_norm, source="LLM_INFERRED", confidence=0.7)
                            print(f"✅ [ORDER_STATE] NUMÉRO persisté (thinking): {phone_norm}")
                        
                        # PAIEMENT: PROTÉGER les paiements validés (validé_XXXF)
                        # Ne JAMAIS écraser un paiement validé par une valeur générique
                        if current_state.paiement and current_state.paiement.startswith("validé_"):
                            pass  # Paiement déjà validé, ne pas toucher
                        # Sinon, on laisse le système de vision gérer le paiement

                        # Fallback ultra-conservateur: si le thinking fournit déjà un format verdict stable,
                        # on peut le persister uniquement si le tracker est vide.
                        if (not current_state.paiement) and paiement and paiement != "∅":
                            p_low = paiement.lower()
                            if p_low.startswith("validé_") or p_low.startswith("valide_"):
                                order_tracker.update_paiement(user_id, paiement, source="LLM_INFERRED", confidence=0.6)
                            elif p_low.startswith("insuffisant_") or p_low.startswith("refus"):
                                # Utile pour aligner l'état si le verdict a été perdu (sans dire que c'est validé)
                                order_tracker.update_paiement(user_id, paiement, source="LLM_INFERRED", confidence=0.5)
                            
                except Exception as e:
                    print(f"⚠️ [ORDER_STATE] Erreur update depuis thinking: {e}")

            # Afficher l'avancement OrderStateTracker
            try:
                st = order_tracker.get_state(user_id)
                missing = sorted(list(st.get_missing_fields()))
                missing_str = ", ".join(missing) if missing else "Aucun"
                completion = st.get_completion_rate() if hasattr(st, "get_completion_rate") else 0.0
                print(f"{C_YELLOW}📊 [ORDER_STATUS] completion={completion:.2f} | missing={C_RED}{missing_str}{C_YELLOW}{C_RESET}")
                try:
                    collected = st.to_notepad_format() if hasattr(st, "to_notepad_format") else ""
                    if collected:
                        print(f"{C_YELLOW}📌 [ORDER_STATUS] {collected}{C_RESET}")
                except Exception:
                    pass
            except Exception as e:
                print(f"⚠️ [ORDER_STATUS] Erreur lecture state: {e}")

            # Extraire <response>
            response_match = re.search(r'<response>(.*?)</response>', raw_llm_output, re.DOTALL | re.IGNORECASE)
            if response_match:
                response = response_match.group(1).strip()
                print(f"✅ [RESPONSE] Extrait: {len(response)} chars")
                try:
                    _prev = str(response or "").replace("\n", " ").strip()
                    if len(_prev) > 220:
                        _prev = _prev[:220] + "..."
                    print(f"🧪 [RESPONSE_PREVIEW] {_prev}")
                except Exception:
                    pass

                try:
                    detected_items_chk = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                    qty_nullish = False
                    if isinstance(detected_items_chk, list) and detected_items_chk:
                        try:
                            qty_nullish = any(isinstance(it, dict) and (it.get("qty") is None) for it in detected_items_chk)
                        except Exception:
                            qty_nullish = False
                    if _is_packsize_question(str(query or "")) and qty_nullish:
                        if re.search(r"\b\d+\b", str(response or "")):
                            response = "Le catalogue ne précise pas le nombre de pièces dans 1 lot. Tu parles d’un lot de combien de pièces exactement stp ?"
                except Exception:
                    pass
            else:
                validated_price_single = False
                try:
                    raw_preview = str(raw_llm_output or "")
                    raw_preview_short = raw_preview[:600] + ("..." if len(raw_preview) > 600 else "")
                    print(f"⚠️ [RESPONSE] <response> tag not found. raw(600)=\n{raw_preview_short}")
                except Exception:
                    pass

                # Si on a déjà un prix calculé côté Python (mono-produit), on priorise ready_to_send.
                try:
                    pc_block = str(price_calculation_block or "").strip()
                    if pc_block:
                        ready_single = _extract_tag(pc_block, "ready_to_send")
                        if ready_single:
                            response = str(ready_single).strip()
                            order_tracker.set_custom_meta(user_id, "price_calculation_block", "<price_calculation>\n" + pc_block + "\n</price_calculation>")
                            validated_price_single = True
                except Exception:
                    pass

                # Fallback robuste:
                # - Supprimer le bloc <thinking>...
                # - Supprimer les code fences (```xml / ```)
                # - Si la sortie ne contient que du XML, forcer une question utile
                if not validated_price_single:
                    response = re.sub(r'<thinking>.*?</thinking>', '', str(response or ''), flags=re.DOTALL | re.IGNORECASE).strip()
                    response = re.sub(r"```[a-zA-Z0-9_-]*\s*", "", response).strip()
                    response = response.replace("```", "").strip()

                # Si le modèle a rendu un <response> sans fermeture, récupérer le contenu après la balise.
                # (sinon on risque de renvoyer littéralement "<response>" au client)
                resp_l = str(response or "")
                if re.search(r"<response\b", resp_l, re.IGNORECASE) and not re.search(r"</response>", resp_l, re.IGNORECASE):
                    parts = re.split(r"<response\b[^>]*>", resp_l, flags=re.IGNORECASE)
                    if len(parts) >= 2:
                        response = parts[-1].strip()
                # Nettoyage final: enlever une éventuelle balise fermante qui traîne.
                response = re.sub(r"</response>", "", str(response or ""), flags=re.IGNORECASE).strip()

                # Si on détecte encore des balises XML, c'est que le modèle a fuité le format -> fallback question
                if (not str(response or "").strip()) or str(response or "").strip().lower() in {"<response>", "</response>", "<response/>"} or re.search(r"</?(thinking|q_exact|intention_client|comprehension|detection|intent|priority|next|response)\b", response, re.IGNORECASE):
                    nf = order_tracker.get_next_required_field(user_id, current_turn=current_turn)

                    def _fallback_question(field: Optional[str]) -> str:
                        f = str(field or "").upper().strip()
                        if f == "PRODUIT":
                            # Catalog-driven: list available variants/products
                            try:
                                _cat_fb = get_company_catalog_v2(company_id) if company_id else None
                                _vt_fb = _cat_fb.get("v") if isinstance(_cat_fb, dict) and isinstance(_cat_fb.get("v"), dict) else None
                                if isinstance(_vt_fb, dict) and _vt_fb:
                                    vnames = [str(k).strip() for k in _vt_fb.keys() if str(k).strip()]
                                    if vnames:
                                        return f"{' ou '.join(vnames)} ?"
                            except Exception:
                                pass
                            return "Quel produit vous intéresse ?"
                        if f == "SPECS":
                            return "Tu veux quelle taille exactement stp ?"
                        if f == "QUANTITÉ":
                            return "Tu en veux combien (carton/paquets) stp ?"
                        if f == "ZONE":
                            return "Tu es dans quelle commune/quartier stp ?"
                        if f in {"NUMÉRO", "NUMERO"}:
                            return "Ton numéro WhatsApp pour le livreur stp ?"
                        if f == "PAIEMENT":
                            return "Tu peux envoyer l’acompte Wave de 2000F et la capture stp ?"
                        return "Tu peux préciser stp ?"

                    response = _fallback_question(nf)
                    print(f"🛡️ [RESPONSE_FALLBACK] xml_leak_detected | next={nf}")

            # 6.0 SAV/HUMAN HANDOFF (RAG): si le LLM sort le token de transmission, on notifie et on stoppe.
            # IMPORTANT: déclenché AVANT toute post-transformation (pricing, guards) pour éviter de polluer le message.
            try:
                token = (LLM_TRANSMISSION_TOKEN or "TRANSMISSIONXXX").strip()
                resp_text = str(response or "")
                raw_text = str(raw_llm_output or "")
                has_token = bool(token) and (token.lower() in resp_text.lower() or token.lower() in raw_text.lower())
                if has_token:
                    from core.human_notification_service import HumanNotificationService

                    # Permettre un message client optionnel avant le token (séparateur §§).
                    # Exemple LLM: "Un instant je te passe le responsable. §§ TRANSMISSIONXXX"
                    cleaned = resp_text
                    if token.lower() in cleaned.lower():
                        parts = re.split(re.escape(token), cleaned, flags=re.IGNORECASE)
                        cleaned = (parts[0] or "").strip()
                    cleaned = cleaned.replace("§§", "").strip()

                    if not cleaned:
                        cleaned = os.getenv(
                            "SIMPLIFIED_RAG_HANDOFF_CUSTOMER_MESSAGE",
                            "Un instant, je te passe le responsable pour régler ça."
                        ).strip()

                    try:
                        order_tracker.set_flag(user_id, "bot_paused", True)
                        order_tracker.set_custom_meta(user_id, "handoff_reason", "SAV")
                        order_tracker.set_custom_meta(user_id, "handoff_trigger", token)
                    except Exception:
                        pass

                    try:
                        st = order_tracker.get_state(user_id)
                        ctx = {
                            "company_name": company_name,
                            "zone": str(getattr(st, "zone", "") or ""),
                            "phone": str(getattr(st, "numero", "") or ""),
                        }
                    except Exception:
                        ctx = {"company_name": company_name}

                    try:
                        notifier = HumanNotificationService()
                        await notifier.notify_vendor(
                            company_id=company_id,
                            user_id=user_id,
                            user_name=user_id,
                            question=query,
                            reason="SAV_TRANSMISSION",
                            context=ctx,
                        )
                        print("🔔 [SAV_HANDOFF] notification sent")
                    except Exception as _hn_e:
                        print(f"⚠️ [SAV_HANDOFF] notify failed: {type(_hn_e).__name__}: {_hn_e}")

                    response = cleaned
            except Exception as _handoff_e:
                print(f"⚠️ [SAV_HANDOFF] error: {type(_handoff_e).__name__}: {_handoff_e}")

            try:
                st_now = order_tracker.get_state(user_id)
                curr_product = str(getattr(st_now, "produit", "") or "").strip()

                if curr_product and (curr_product != prev_product_before_llm) and (not had_product_context_in_prompt):
                    try:
                        catalog_v2 = get_company_catalog_v2(company_id)
                    except Exception:
                        catalog_v2 = None

                    vtree = (catalog_v2 or {}).get("v") if isinstance(catalog_v2, dict) else None
                    if not isinstance(vtree, dict):
                        vtree = {}

                    def _match_variant_key(product_raw: str) -> str:
                        p = str(product_raw or "").strip().lower()
                        if not p:
                            return ""
                        keys = [str(k) for k in vtree.keys()]
                        for k in keys:
                            if str(k).strip().lower() == p:
                                return str(k)
                        for k in keys:
                            kl = str(k).strip().lower()
                            if p and (p in kl or kl in p):
                                return str(k)
                        return ""

                    variant_key = _match_variant_key(curr_product)

                    def _extract_allowed_units_for_variant(vnode: Dict[str, Any]) -> List[str]:
                        out: set[str] = set()
                        if not isinstance(vnode, dict):
                            return []
                        node_s = vnode.get("s")
                        if isinstance(node_s, dict) and node_s:
                            for _, sub_node in node_s.items():
                                if not isinstance(sub_node, dict):
                                    continue
                                sub_u = sub_node.get("u")
                                if not isinstance(sub_u, dict):
                                    continue
                                for uk, raw_price in sub_u.items():
                                    p = _parse_price_value(raw_price)
                                    if p is None or p <= 0:
                                        continue
                                    out.add(str(uk))
                        else:
                            u_map = vnode.get("u")
                            if isinstance(u_map, dict) and u_map:
                                for uk, raw_price in u_map.items():
                                    p = _parse_price_value(raw_price)
                                    if p is None or p <= 0:
                                        continue
                                    out.add(str(uk))
                        return sorted({u for u in out if str(u).strip()})

                    def _extract_specs_for_variant(vnode: Dict[str, Any]) -> List[str]:
                        if not isinstance(vnode, dict):
                            return []
                        node_s = vnode.get("s")
                        if not isinstance(node_s, dict) or not node_s:
                            return []
                        specs = [str(k).strip() for k in node_s.keys() if str(k).strip()]
                        return sorted(set(specs))

                    def _compress_seq(items: List[str]) -> str:
                        xs = [str(x).strip() for x in (items or []) if str(x).strip()]
                        if not xs:
                            return ""
                        xs = sorted(set(xs), key=lambda x: x)

                        m_all = [re.fullmatch(r"([A-Za-z]+)(\d+)", x) for x in xs]
                        if all(m_all):
                            pref = m_all[0].group(1)
                            if all(mm.group(1) == pref for mm in m_all):
                                nums = sorted({int(mm.group(2)) for mm in m_all})
                                if len(nums) >= 3 and nums == list(range(min(nums), max(nums) + 1)):
                                    return f"{pref}{min(nums)}-{pref}{max(nums)}"
                        if len(xs) <= 8:
                            return ", ".join(xs)
                        return f"{xs[0]}, …, {xs[-1]} ({len(xs)})"

                    if not variant_key:
                        keys = [str(k).strip() for k in vtree.keys() if str(k).strip()]
                        keys = sorted(set(keys))
                        if len(keys) >= 2:
                            response = f"Tu parles de quel produit: {keys[0]} ou {keys[1]} ?"
                        elif len(keys) == 1:
                            response = f"Tu parles de {keys[0]} c'est ça ?"
                        else:
                            response = "Tu veux quel produit exactement stp ?"
                    else:
                        vnode = vtree.get(variant_key)
                        allowed_units = _extract_allowed_units_for_variant(vnode)
                        specs = _extract_specs_for_variant(vnode)

                        msg_low = str(query or "").lower()
                        has_spec_in_msg = any(_is_value_mentioned(query or "", s) for s in specs) if specs else False

                        ctx_lines = []
                        ctx_lines.append(f"product={variant_key}")
                        if allowed_units:
                            ctx_lines.append("sold_only_by=" + ",".join(allowed_units))
                        if specs:
                            ctx_lines.append("specs=" + _compress_seq(specs))
                        product_ctx = "\n".join(ctx_lines)

                        async def _mini_product_clarify(message: str, product_context: str) -> str:
                            from core.llm_client import complete as mini_complete

                            msg_txt = str(message or "").strip()
                            prompt = (
                                "Tu es un assistant WhatsApp.")
                            prompt += "\nBut: répondre UNE SEULE FOIS pour clarifier la demande produit."
                            prompt += "\nRègles: 1 phrase, 1 question max, style A/B si possible, pas de prix, pas de blabla."
                            prompt += "\nTu n'inventes rien en dehors de PRODUCT_CONTEXT."
                            prompt += f"\nPRODUCT_CONTEXT:\n{product_context}\n"
                            prompt += f"\nMESSAGE_CLIENT: {json.dumps(msg_txt, ensure_ascii=False)}\n"
                            raw = await mini_complete(
                                prompt=prompt,
                                model_name=os.getenv("PRODUCT_CLARIFIER_MODEL", "google/gemini-2.5-flash-lite"),
                                temperature=0.2,
                                max_tokens=int(os.getenv("PRODUCT_CLARIFIER_MAX_TOKENS", "70")),
                            )
                            return str(raw or "").strip()

                        if specs and (not has_spec_in_msg):
                            if len(specs) == 2:
                                response = f"Pour {variant_key}, tu veux {specs[0]} ou {specs[1]} ?"
                            else:
                                response = await _mini_product_clarify(query, product_ctx)
                        elif allowed_units and (not any(u.replace("_", " ") in msg_low or u in msg_low for u in allowed_units)):
                            if len(allowed_units) == 2:
                                response = f"Pour {variant_key}, tu prends {allowed_units[0]} ou {allowed_units[1]} ?"
                            else:
                                response = await _mini_product_clarify(query, product_ctx)
                        else:
                            response = await _mini_product_clarify(query, product_ctx)
            except Exception as _mini_prod_e:
                print(f"⚠️ [MINI_PRODUCT] error: {type(_mini_prod_e).__name__}: {_mini_prod_e}")

            # 6.a Pricing multi-items (post LLM): validation + injection du ready_to_send
            validated_price = False
            try:
                try:
                    pending_cart_q = str(order_tracker.get_custom_meta(user_id, "pending_cart_question", default="") or "").strip()
                except Exception:
                    pending_cart_q = ""
                if pending_cart_q:
                    raise StopIteration("pending_cart_question")

                detected_items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                detected_items_raw = order_tracker.get_custom_meta(user_id, "detected_items_raw", default="")

                def _has_valid_price_meta() -> bool:
                    try:
                        pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                        if not pc_meta:
                            return False
                        status = str(_extract_tag(pc_meta, "status") or "").strip().upper()
                        ready = str(_extract_tag(pc_meta, "ready_to_send") or "").strip()
                        return (status == "OK") and bool(ready)
                    except Exception:
                        return False

                def _is_price_request(msg: str) -> bool:
                    m = str(msg or "").lower()
                    if _is_packsize_question(m):
                        return False
                    if any(k in m for k in ["prix", "tarif", "tarifs", "total", "montant", "c'est combien", "cest combien", "ça coute", "ca coute"]):
                        return True
                    if re.search(r"\b(ca|ça)\s*(va\s*)?faire\s*combien\b", m):
                        return True
                    if re.search(r"\bcombien\s*(ca|ça)\s*(fait|fera|va\s*faire)\b", m):
                        return True
                    if re.search(r"\b(ca|ça)\s*va\s*(etre|être)\s*(de\s*)?combien\b", m):
                        return True
                    if re.search(r"\b(le\s*)?total\s*va\s*(etre|être)\s*(de\s*)?combien\b", m):
                        return True
                    if re.search(r"\btotal\s*(=|:)?\s*combien\b", m):
                        return True
                    if re.search(r"\b(revient|revient\s+a)\s*combien\b", m):
                        return True
                    return False

                def _is_packsize_question(m: str) -> bool:
                    t = str(m or "").lower()
                    if any(k in t for k in ["dans un lot", "dans le lot", "dans 1 lot", "dans un paquet", "dans le paquet", "dans 1 paquet"]):
                        return True
                    if any(k in t for k in ["combien de pieces", "combien de pièces", "nombre de pieces", "nombre de pièces", "ça contient combien", "ca contient combien"]):
                        return True
                    if re.search(r"\b(quantité|qte)\s*(par|dans)\s*(lot|paquet)\b", t):
                        return True
                    return False

                def _validate_items(items) -> Dict[str, Any]:
                    out = {
                        "ok": False,
                        "confirmed": [],
                        "unconfirmed": [],
                        "invalid": [],
                        "reasons": [],
                    }
                    if not isinstance(items, list) or not items:
                        out["reasons"].append("no_items")
                        return out

                    try:
                        catalog_v2 = get_company_catalog_v2(company_id)
                    except Exception:
                        catalog_v2 = None

                    if not isinstance(catalog_v2, dict):
                        out["reasons"].append("catalog_unavailable")
                        return out

                    def _parse_unit_key(u: str) -> Optional[Dict[str, Any]]:
                        s = str(u or "").strip().lower()
                        if not s or "_" not in s:
                            return None
                        t, n = s.split("_", 1)
                        try:
                            size_i = int(re.sub(r"\D+", "", n) or "0")
                        except Exception:
                            size_i = 0
                        if not t or size_i <= 0:
                            return None
                        return {"type": t, "size": size_i}

                    def _norm_unit_token(raw: str) -> str:
                        s = str(raw or "").strip().lower()
                        if not s:
                            return ""
                        s = s.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ô", "o").replace("û", "u")
                        s = re.sub(r"[^a-z0-9_\s-]+", "", s)
                        s = s.replace("-", " ")
                        s = re.sub(r"\s+", " ", s).strip()
                        if s.endswith("s") and len(s) > 1:
                            s = s[:-1]
                        # alias très génériques (pas par produit)
                        if s in {"pack"}:
                            s = "paquet"
                        if s in {"paquet", "paquet_", "paquet50"}:
                            s = "paquet"
                        return s

                    def _canonicalize_item_unit(
                        it: Dict[str, Any],
                        *,
                        allowed_units: List[str],
                        parsed_units: List[Dict[str, Any]],
                    ) -> Dict[str, Any]:
                        """Canonise unit/qty à partir des canonical_units.

                        Objectif: accepter une unité humaine (ex: "paquets") et convertir vers
                        une unit canonique existante (ex: "lot_300") sans hardcode produit.
                        """

                        unit_raw = str(it.get("unit") or "").strip()
                        if unit_raw in allowed_units:
                            return it

                        qty = it.get("qty")
                        qty_i: Optional[int]
                        try:
                            qty_i = int(qty) if qty is not None else None
                        except Exception:
                            qty_i = None

                        token = _norm_unit_token(unit_raw)
                        if not token:
                            return it

                        # Trouver un "format de base" par type (ex: paquet -> paquet_50)
                        base = [p for p in (parsed_units or []) if p.get("type") == token]
                        base = sorted(base, key=lambda x: int(x.get("size") or 0))
                        base_unit = base[0] if base else None
                        if not base_unit:
                            return it

                        # Cas 1: si on a une qty, essayer de convertir en unité qui matche le total (ex: 6*50=300 -> lot_300)
                        if qty_i is not None and qty_i > 0:
                            total_size = qty_i * int(base_unit.get("size") or 0)
                            if total_size > 0:
                                # On privilégie une unité réellement vendue sur ce produit (allowed_units)
                                candidates = [
                                    p
                                    for p in (parsed_units or [])
                                    if int(p.get("size") or 0) == total_size and str(p.get("key") or "") in allowed_units
                                ]
                                if candidates:
                                    best = candidates[0]
                                    nxt = dict(it)
                                    nxt["unit"] = str(best.get("key"))
                                    nxt["qty"] = 1
                                    return nxt

                        # Cas 2: fallback simple -> convertir vers l'unité de base (ex: paquets -> paquet_50)
                        if str(base_unit.get("key") or "") in allowed_units:
                            nxt = dict(it)
                            nxt["unit"] = str(base_unit.get("key"))
                            return nxt

                        return it

                    def _match_key_case_insensitive(keys: List[str], target: str) -> Optional[str]:
                        t = str(target or "").strip().lower()
                        if not t:
                            return None
                        for k in keys:
                            if str(k or "").strip().lower() == t:
                                return str(k)
                        return None

                    def _find_variant_key(product_raw: str) -> Optional[str]:
                        p = str(product_raw or "").strip().lower()
                        if not p:
                            return ""
                        keys = [str(k) for k in vtree.keys()]
                        for k in keys:
                            if str(k).strip().lower() == p:
                                return str(k)
                        for k in keys:
                            kl = str(k).strip().lower()
                            if p and (p in kl or kl in p):
                                return str(k)
                        if len(keys) == 1:
                            return str(keys[0])
                        return ""

                    def _extract_t_number(specs_raw: str) -> Optional[int]:
                        s = str(specs_raw or "").strip().upper()
                        m = re.search(r"\bT\s*([1-9]\d*)\b", s)
                        if m:
                            try:
                                return int(m.group(1))
                            except Exception:
                                return None
                        m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", s)
                        if m2:
                            try:
                                return int(m2.group(1))
                            except Exception:
                                return None
                        return None

                    def _spec_key_matches(sub_key: str, requested_specs: str) -> bool:
                        if not sub_key:
                            return False
                        keys = [str(sub_key)]
                        exact = _match_key_case_insensitive(keys, requested_specs)
                        if exact:
                            return True

                        req_n = _extract_t_number(requested_specs)
                        if req_n is None:
                            return False

                        nums = [int(x) for x in re.findall(r"T\s*([1-9]\d*)", str(sub_key).upper()) if x.isdigit()]
                        if not nums:
                            return False
                        lo, hi = min(nums), max(nums)
                        return lo <= req_n <= hi

                    def _find_subvariant_key(node_s: Dict[str, Any], specs_raw: str) -> Optional[str]:
                        if not isinstance(node_s, dict):
                            return None
                        specs_s = str(specs_raw or "").strip()
                        if not specs_s:
                            return None
                        sub_keys = [str(k) for k in node_s.keys()]
                        exact = _match_key_case_insensitive(sub_keys, specs_s)
                        if exact:
                            return exact
                        for k in sub_keys:
                            if _spec_key_matches(k, specs_s):
                                return str(k)
                        s_low = specs_s.lower()
                        for k in sub_keys:
                            k_low = str(k or "").lower()
                            if s_low and (s_low in k_low or k_low in s_low):
                                return str(k)
                        return None

                    for it in items:
                        if not isinstance(it, dict):
                            out["invalid"].append({"item": it, "reason": "not_dict"})
                            continue
                        product_raw = str(it.get("product") or "").strip()
                        if not product_raw:
                            product_raw = str(it.get("product_id") or "").strip()
                        variant_raw = str(it.get("variant") or "").strip()
                        specs_raw = str(it.get("specs") or "").strip()
                        if not specs_raw:
                            specs_raw = str(it.get("spec") or "").strip()
                        unit = str(it.get("unit") or "").strip()
                        confidence = it.get("confidence")
                        qty = it.get("qty")

                        selected_catalog = None
                        try:
                            plist = catalog_v2.get("products") if isinstance(catalog_v2, dict) else None
                            if isinstance(plist, list):
                                pid = str(it.get("product_id") or "").strip()
                                if pid:
                                    selected_catalog = get_company_product_catalog_v2(company_id, pid)
                                    if not isinstance(selected_catalog, dict):
                                        try:
                                            if re.fullmatch(r"prod_[0-9a-f]{8}", pid, flags=re.IGNORECASE):
                                                import hashlib as _hashlib
                                                import unicodedata as _ud

                                                def _norm_name_for_id(name: str) -> str:
                                                    t = str(name or "").strip().lower()
                                                    t = _ud.normalize("NFKD", t)
                                                    t = "".join([c for c in t if not _ud.combining(c)])
                                                    t = re.sub(r"[^a-z0-9\s-]+", " ", t)
                                                    t = t.replace("-", " ")
                                                    t = re.sub(r"\s+", " ", t).strip()
                                                    return t

                                                def _pid_hash(name: str) -> str:
                                                    base = _norm_name_for_id(name)
                                                    if not base:
                                                        return ""
                                                    h = _hashlib.sha1(base.encode("utf-8", errors="replace")).hexdigest()
                                                    return f"prod_{h[:8]}"

                                                for p in (plist or []):
                                                    if not isinstance(p, dict):
                                                        continue
                                                    pname = str(p.get("product_name") or (p.get("catalog_v2") or {}).get("product_name") or "").strip()
                                                    if pname and _pid_hash(pname).lower() == pid.lower() and isinstance(p.get("catalog_v2"), dict):
                                                        selected_catalog = p.get("catalog_v2")
                                                        break
                                        except Exception:
                                            pass
                                else:
                                    only_one = [p for p in plist if isinstance(p, dict) and isinstance(p.get("catalog_v2"), dict)]
                                    if len(only_one) == 1:
                                        selected_catalog = only_one[0].get("catalog_v2")
                            else:
                                selected_catalog = catalog_v2
                        except Exception:
                            selected_catalog = catalog_v2

                        if not isinstance(selected_catalog, dict):
                            out["invalid"].append({"item": it, "reason": "catalog_unavailable"})
                            continue

                        canonical_units = selected_catalog.get("canonical_units")
                        if not isinstance(canonical_units, list):
                            canonical_units = []
                        canonical_units = [str(u).strip() for u in canonical_units if str(u).strip()]

                        parsed_units: List[Dict[str, Any]] = []
                        for cu in canonical_units:
                            p = _parse_unit_key(cu)
                            if p:
                                p["key"] = str(cu)
                                parsed_units.append(p)

                        vtree = selected_catalog.get("v")
                        if not isinstance(vtree, dict) or not vtree:
                            out["invalid"].append({"item": it, "reason": "catalog_unavailable"})
                            continue

                        variant_key = _find_variant_key(variant_raw or product_raw)
                        node = vtree.get(variant_key) if variant_key else None
                        if not isinstance(node, dict):
                            out["invalid"].append({"item": it, "reason": "bad_product"})
                            continue

                        node_s = node.get("s")
                        if isinstance(node_s, dict) and node_s:
                            sub_key = _find_subvariant_key(node_s, specs_raw)
                            if not sub_key:
                                out["invalid"].append({"item": it, "reason": "bad_specs"})
                                continue
                            sub_node = node_s.get(sub_key)
                            if not isinstance(sub_node, dict):
                                out["invalid"].append({"item": it, "reason": "bad_specs"})
                                continue
                            u_map = sub_node.get("u")
                            allowed_units = list(u_map.keys()) if isinstance(u_map, dict) else []
                            it2 = _canonicalize_item_unit(dict(it), allowed_units=allowed_units, parsed_units=parsed_units)
                            unit2 = str(it2.get("unit") or "").strip()
                            if not isinstance(u_map, dict) or unit2 not in u_map:
                                out["invalid"].append({"item": it, "reason": "bad_unit"})
                                continue
                            it = it2
                            unit = unit2
                            qty = it.get("qty")
                        else:
                            u_map = node.get("u")
                            allowed_units = list(u_map.keys()) if isinstance(u_map, dict) else []
                            it2 = _canonicalize_item_unit(dict(it), allowed_units=allowed_units, parsed_units=parsed_units)
                            unit2 = str(it2.get("unit") or "").strip()
                            if not isinstance(u_map, dict) or unit2 not in u_map:
                                out["invalid"].append({"item": it, "reason": "bad_unit"})
                                continue
                            it = it2
                            unit = unit2
                            qty = it.get("qty")

                        try:
                            conf_f = float(confidence) if confidence is not None else 0.0
                        except Exception:
                            conf_f = 0.0

                        if qty is None:
                            out["unconfirmed"].append({"item": it, "reason": "qty_null"})
                            continue
                        if not isinstance(qty, int) or qty <= 0:
                            out["invalid"].append({"item": it, "reason": "qty_invalid"})
                            continue

                        if conf_f < float(CONFIDENCE_THRESHOLD):
                            out["unconfirmed"].append({"item": it, "reason": "low_confidence", "confidence": conf_f})
                            continue

                        out["confirmed"].append(it)

                    if out["invalid"]:
                        out["reasons"].append("invalid_items")
                        return out
                    if out["unconfirmed"]:
                        out["reasons"].append("unconfirmed_items")
                        return out
                    out["ok"] = True
                    return out

                validation = _validate_items(detected_items)
                order_tracker.set_custom_meta(user_id, "detected_items_validation", validation)
                if validation.get("ok"):
                    st_for_zone = order_tracker.get_state(user_id)
                    zone_for_price = str(getattr(st_for_zone, "zone", "") or "").strip() or str(dynamic_context.get("detected_location") or "").strip()

                    def _norm_amt(s: str) -> str:
                        return re.sub(r"\D+", "", str(s or ""))

                    def _parse_fee(v) -> Optional[int]:
                        if v is None:
                            return None
                        if isinstance(v, (int, float)):
                            return int(v)
                        s = str(v)
                        m = re.search(r"(\d+)", s)
                        return int(m.group(1)) if m else None

                    delivery_fee_fcfa = _parse_fee(dynamic_context.get("shipping_fee"))
                    if (delivery_fee_fcfa is None or int(delivery_fee_fcfa) <= 0) and zone_for_price:
                        try:
                            from core.delivery_zone_extractor import extract_delivery_zone_and_cost

                            zinfo = extract_delivery_zone_and_cost(str(zone_for_price))
                            fee2 = (zinfo or {}).get("cost") if isinstance(zinfo, dict) else None
                            if isinstance(fee2, (int, float)) and int(fee2) > 0:
                                delivery_fee_fcfa = int(fee2)
                        except Exception:
                            pass
                    pc_inner = UniversalPriceCalculator.build_price_calculation_block_from_detected_items(
                        company_id=company_id,
                        items=detected_items,
                        zone=zone_for_price,
                        delivery_fee_fcfa=delivery_fee_fcfa,
                    )
                    if str(pc_inner or "").strip():
                        price_block = "<price_calculation>\n" + str(pc_inner).strip() + "\n</price_calculation>"
                        order_tracker.set_custom_meta(user_id, "price_calculation_block", price_block)
                        validated_price = True
                        ready = _extract_tag(price_block, "ready_to_send")
                        if ready:
                            llm_resp = str(response or "").strip()
                            ready_txt = str(ready).strip()
                            try:
                                current_sig = "|".join(
                                    [
                                        _norm_amt(_extract_tag(price_block, "total_fcfa") or ""),
                                        _norm_amt(_extract_tag(price_block, "product_subtotal_fcfa") or ""),
                                        _norm_amt(_extract_tag(price_block, "delivery_fee_fcfa") or ""),
                                        str(zone_for_price or "").strip().lower(),
                                    ]
                                )
                                last_sig = str(
                                    order_tracker.get_custom_meta(user_id, "last_price_signature_shown", default="") or ""
                                ).strip()
                                try:
                                    last_turn_raw = order_tracker.get_custom_meta(user_id, "last_price_shown_turn", default=0)
                                    last_turn = int(last_turn_raw) if last_turn_raw is not None else 0
                                except Exception:
                                    last_turn = 0
                                price_requested_now = bool(_is_price_request(query or ""))
                                allow_show_price = price_requested_now or (not last_sig) or (last_sig != current_sig)
                                if (not price_requested_now) and last_sig and (last_sig == current_sig) and last_turn and current_turn:
                                    try:
                                        if int(current_turn) - int(last_turn) <= 2:
                                            allow_show_price = False
                                    except Exception:
                                        pass
                            except Exception:
                                current_sig = ""
                                allow_show_price = True

                            orientation_marker = "§§"
                            llm_calc_part = llm_resp
                            llm_orientation_part = ""
                            if orientation_marker in llm_resp:
                                parts = llm_resp.split(orientation_marker, 1)
                                llm_calc_part = (parts[0] or "").strip()
                                llm_orientation_part = (parts[1] or "").strip()

                            def _with_orientation_marker(q: str) -> str:
                                try:
                                    t = str(q or "").strip()
                                    if not t:
                                        return ""
                                    # Ensure marker is present and separated.
                                    if t.startswith(orientation_marker):
                                        t = t[len(orientation_marker) :].strip()
                                    return f"{orientation_marker} {t}".strip()
                                except Exception:
                                    return ""

                            def _extract_single_question(text: str) -> str:
                                try:
                                    t = str(text or "").strip()
                                    if not t:
                                        return ""
                                    # Prefer the last question sentence.
                                    # Example: "... Pour quelle commune c'est ?" -> keep that.
                                    qs = re.findall(r"([^?]{3,}\?)", t)
                                    if qs:
                                        return str(qs[-1]).strip()
                                    return ""
                                except Exception:
                                    return ""

                            total_fcfa = str(_extract_tag(price_block, "total_fcfa") or "").strip()
                            subtotal_fcfa = str(_extract_tag(price_block, "product_subtotal_fcfa") or "").strip()
                            delivery_fcfa = str(_extract_tag(price_block, "delivery_fee_fcfa") or "").strip()

                            # ── Template simplifié: "Noté, ça fera XX XXXF." au lieu du récap verbeux ──
                            try:
                                _total_int = int(total_fcfa) if total_fcfa and total_fcfa.isdigit() else 0
                                _simple_price_txt = f"Noté, ça fera {_total_int:,}F.".replace(",", " ") if _total_int > 0 else ready_txt
                            except Exception:
                                _simple_price_txt = ready_txt

                            expected_amounts = {
                                a
                                for a in (
                                    _norm_amt(total_fcfa),
                                    _norm_amt(subtotal_fcfa),
                                    _norm_amt(delivery_fcfa),
                                )
                                if a
                            }

                            money_pattern = re.compile(r"\b\d[\d\s.,]*\s*(?:fcfa|f)\b", re.IGNORECASE)
                            llm_amounts = [_norm_amt(m.group(0)) for m in money_pattern.finditer(llm_calc_part)]
                            llm_amounts = [a for a in llm_amounts if a]
                            has_marker = orientation_marker in llm_resp
                            resp_no_marker = str(llm_resp).replace(orientation_marker, "", 1).strip() if has_marker else llm_resp

                            def _next_question_after_price() -> str:
                                try:
                                    stp = order_tracker.get_state(user_id)
                                    missing2 = sorted(list(stp.get_missing_fields())) if stp else []
                                except Exception:
                                    missing2 = []

                                if not missing2:
                                    return "Vous confirmez la commande ? (Oui/Non)"

                                _has_zone_missing = any(x in {"ZONE"} for x in missing2)
                                _has_phone_missing = any(x in {"NUMÉRO", "NUMERO", "TÉLÉPHONE", "TELEPHONE"} for x in missing2)
                                _has_payment_missing = any(x in {"PAIEMENT"} for x in missing2)

                                # Combo: zone + numéro manquants → demander les 2 en 1 question
                                if _has_zone_missing and _has_phone_missing:
                                    return "Pouvez-vous m'envoyer le numéro à joindre ainsi que le lieu de livraison (commune) ?"

                                if _has_zone_missing:
                                    return "Vous êtes dans quelle commune/quartier pour la livraison ?"
                                if _has_phone_missing:
                                    return "Quel est votre numéro WhatsApp pour le livreur ?"
                                if _has_payment_missing:
                                    _pp = str(os.getenv("PAYMENT_PHONE", "+225 0787360757") or "+225 0787360757").strip()
                                    _dp = str(os.getenv("EXPECTED_DEPOSIT", "2000 FCFA") or "2000 FCFA").strip()
                                    return f"J'aurais besoin d'un dépôt de validation de {_dp} via Wave au {_pp} pour valider votre commande ; une fois fait envoyez-moi une capture svp 📸"

                                return "Vous confirmez la commande ? (Oui/Non)"

                            # Déterminer si c'est la PREMIÈRE fois qu'on montre le prix
                            _first_time_price = allow_show_price and (not last_sig)

                            if price_requested_now and allow_show_price and (not has_marker):
                                follow_q = _next_question_after_price()
                                response = (_simple_price_txt + " " + str(follow_q or "").strip()).strip()
                                try:
                                    if current_sig:
                                        order_tracker.set_custom_meta(user_id, "last_price_signature_shown", current_sig)
                                        order_tracker.set_custom_meta(user_id, "last_price_shown_turn", int(current_turn or 0))
                                except Exception:
                                    pass
                            elif has_marker:
                                tail = (llm_orientation_part or "").strip() or _extract_single_question(resp_no_marker) or str(resp_no_marker).strip()
                                try:
                                    tail = money_pattern.sub("", str(tail))
                                    tail = re.sub(r"\s+", " ", tail).strip()
                                except Exception:
                                    pass

                                if allow_show_price:
                                    if price_requested_now:
                                        follow_q = _next_question_after_price()
                                        response = (_simple_price_txt + " " + str(follow_q or "").strip()).strip()
                                    else:
                                        response = (_simple_price_txt + "\n" + _with_orientation_marker(tail)).strip()
                                    try:
                                        if current_sig:
                                            order_tracker.set_custom_meta(user_id, "last_price_signature_shown", current_sig)
                                            order_tracker.set_custom_meta(user_id, "last_price_shown_turn", int(current_turn or 0))
                                    except Exception:
                                        pass
                                else:
                                    response = str(tail).strip()
                            elif _first_time_price:
                                # Prix calculé pour la 1ère fois + produit complet → TOUJOURS annoncer le prix
                                # même si le client n'a pas demandé explicitement le total
                                follow_q = _next_question_after_price()
                                response = (_simple_price_txt + "\n" + str(follow_q or "").strip()).strip()
                                try:
                                    if current_sig:
                                        order_tracker.set_custom_meta(user_id, "last_price_signature_shown", current_sig)
                                        order_tracker.set_custom_meta(user_id, "last_price_shown_turn", int(current_turn or 0))
                                except Exception:
                                    pass
                                print(f"💡 [PRICE_MULTI] first-time price shown (no marker, no explicit request)")
                            else:
                                response = llm_resp
                        print(f"✅ [PRICE_MULTI] injected | items={len(detected_items)} | zone='{zone_for_price}'")
                    else:
                        print(f"⚠️ [PRICE_MULTI] calc returned empty | raw_items_len={len(str(detected_items_raw or ''))}")
                else:
                    print(f"🧾 [PRICE_MULTI] skipped | reasons={validation.get('reasons')}")
                    if _is_price_request(query or ""):
                        order_tracker.set_custom_meta(user_id, "price_requested", True)

                        # Si un pricing mono-produit est déjà calculé et valide, ne JAMAIS remplacer la réponse
                        # par une recap Oui/Non (ça casse le flux et supprime la réponse LLM parfaite).
                        if _has_valid_price_meta():
                            raise StopIteration("skip_clarify_due_to_valid_single_price")

                        # Clarification (1 seule) si le client demande le prix mais que les items sont flous.
                        try:
                            already_clarified = order_tracker.get_flag(user_id, "clarification_attempted")

                            def _build_closed_clarification(v: Dict[str, Any]) -> Optional[str]:
                                unconf = v.get("unconfirmed") if isinstance(v.get("unconfirmed"), list) else []
                                inv = v.get("invalid") if isinstance(v.get("invalid"), list) else []
                                target = None
                                target_reason = None

                                if unconf:
                                    first = unconf[0] if isinstance(unconf[0], dict) else {}
                                    target = first.get("item") if isinstance(first.get("item"), dict) else None
                                    target_reason = str(first.get("reason") or "").strip().lower()
                                elif inv:
                                    first = inv[0] if isinstance(inv[0], dict) else {}
                                    target = first.get("item") if isinstance(first.get("item"), dict) else None
                                    target_reason = str(first.get("reason") or "").strip().lower()

                                if not isinstance(target, dict):
                                    return None

                                prod = str(target.get("product") or "").strip().lower()
                                specs = str(target.get("specs") or "").strip().upper()
                                unit = str(target.get("unit") or "").strip().lower()
                                qty = target.get("qty")

                                # Question fermée (Oui/Non) pour valider le panier détecté.
                                # On évite toute nouvelle extraction ou calcul.
                                if target_reason in {"qty_null", "qty_invalid"}:
                                    if unit == "lot":
                                        return f"Je confirme: c’est {prod} {specs} en 1 lot ? (Oui/Non)"
                                    if unit == "paquet":
                                        return f"Je confirme: c’est {prod} {specs} en 1 paquet ? (Oui/Non)"
                                    return f"Je confirme: c’est {prod} {specs} ? (Oui/Non)"

                                if prod and specs and unit and isinstance(qty, int) and qty > 0:
                                    return f"Je confirme: {qty} {unit}(s) de {prod} {specs} ? (Oui/Non)"

                                if prod and specs:
                                    return f"Je confirme: {prod} {specs} ? (Oui/Non)"

                                if prod:
                                    return f"Je confirme: {prod} ? (Oui/Non)"

                                return None

                            # Si on est au stade 'tout sauf paiement' mais items non confirmés -> on force une recap courte.
                            st_now = order_tracker.get_state(user_id)
                            missing_now = sorted(list(st_now.get_missing_fields()))

                            if (not already_clarified) and (not _is_packsize_question(str(query or ""))) and ("unconfirmed_items" in (validation.get("reasons") or []) or "invalid_items" in (validation.get("reasons") or [])):
                                recap_gate = (missing_now == ["PAIEMENT"]) or (missing_now == ["PAIEMENT"])

                                msg = _build_closed_clarification(validation)
                                if msg:
                                    response = msg
                                    order_tracker.set_flag(user_id, "clarification_attempted", True)
                                    print("❓ [CLARIFY] asked_once_for_items")

                                # Si on est à 1 étape du paiement, on évite de demander paiement tant que panier non confirmé.
                                if recap_gate and not msg:
                                    response = "Je récapitule: tu veux bien les couches notées ci-dessus ? (Oui/Non)"
                                    order_tracker.set_flag(user_id, "clarification_attempted", True)
                                    print("🧾 [RECAP_GATE] basket_confirm_before_payment")
                        except Exception as _cl_e:
                            print(f"⚠️ [CLARIFY] error: {type(_cl_e).__name__}: {_cl_e}")
            except Exception as e:
                if isinstance(e, StopIteration):
                    print(f"❓ [CLARIFY] SKIP: {e}")
                else:
                    print(f"⚠️ [PRICE_MULTI] error: {type(e).__name__}: {e}")

            # Failsafe: si le modèle a rendu un output incomplet (ex: pas de <response> car max_tokens atteint),
            # mais que Python a un ready_to_send valide (mono ou multi), on le renvoie quoi qu'il arrive.
            try:
                resp_missing = bool(re.search(r"<response\b", str(raw_llm_output or ""), re.IGNORECASE)) is False
                if resp_missing:
                    pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                    if pc_meta:
                        ready_any = _extract_tag(pc_meta, "ready_to_send")
                        if ready_any:
                            response = str(ready_any).strip()
                            print("🛟 [RESPONSE_FAILSAFE] used_ready_to_send")
            except Exception as _rf_e:
                print(f"⚠️ [RESPONSE_FAILSAFE] error: {type(_rf_e).__name__}: {_rf_e}")

            # Anti-hallucination prix: si un montant est présent mais aucun pricing validé, on neutralise.
            try:
                # 6.a Hallucination Guard: enlever les mentions de prix non validées
                has_money = bool(re.search(r"\b\d[\d\s.,]*\s*(?:fcfa|f)\b", str(response or ""), re.IGNORECASE))
                q_low = str(query or "").lower()
                is_price_request_now = any(
                    k in q_low
                    for k in [
                        "prix",
                        "total",
                        "ça fait combien",
                        "ca fait combien",
                        "montant",
                        "combien",
                    ]
                )
                price_is_validated = bool(validated_price or ("validated_price_single" in locals() and validated_price_single))
                if not price_is_validated:
                    try:
                        pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                        if pc_meta:
                            status = str(_extract_tag(pc_meta, "status") or "").strip().upper()
                            ready = str(_extract_tag(pc_meta, "ready_to_send") or "").strip()
                            if status == "OK" and ready:
                                price_is_validated = True
                    except Exception:
                        pass
                if has_money and is_price_request_now and (not price_is_validated):
                    response = re.sub(r"\b\d[\d\s.,]*\s*(?:fcfa|f)\b", "", str(response or ""), flags=re.IGNORECASE)
                    response = re.sub(r"\s+", " ", response).strip()
                    print("⚠️ [PRICE_GUARD] hallucination prevented")
            except Exception as _hg_e:
                print(f"⚠️ [PRICE_GUARD] error: {type(_hg_e).__name__}: {_hg_e}")

            # 6.b Failsafe anti-validation fantôme (Python)
            # Si des slots obligatoires manquent, on interdit les formulations de validation/confirmation.
            try:
                st_chk = order_tracker.get_state(user_id)
                missing_now = sorted(list(st_chk.get_missing_fields()))
                if missing_now:
                    resp_low = str(response or "").lower()
                    # Gardes: ne jamais écraser une vraie clarification/question en cours.
                    try:
                        pending_cart_q2 = str(order_tracker.get_custom_meta(user_id, "pending_cart_question", default="") or "").strip()
                    except Exception:
                        pending_cart_q2 = ""
                    if pending_cart_q2:
                        raise StopIteration("pending_cart_question")

                    if "?" in str(response or ""):
                        raise StopIteration("skip_failsafe_question")
                    try:
                        if (
                            isinstance(thinking_parsed, dict)
                            and str(thinking_parsed.get("priority") or "").strip().upper() == "CLARIFY_PIVOT"
                        ):
                            raise StopIteration("skip_failsafe_clarify_pivot")
                        if isinstance(thinking_parsed, dict) and str(thinking_parsed.get("priority") or "").strip().upper() == "CLARIFY":
                            raise StopIteration("skip_failsafe_clarify")
                    except StopIteration:
                        raise
                    except Exception:
                        pass

                    if re.search(r"\b(on\s+valide|je\s+valide|je\s+confirme|on\s+confirme|commande\s+confirm|commande\s+valid|c['’]?est\s+bon)\b", resp_low):
                        # Rediriger vers le prochain champ manquant
                        nf = order_tracker.get_next_required_field(user_id, current_turn=current_turn)

                        def _fallback_question(field: Optional[str]) -> str:
                            f = str(field or "").upper().strip()
                            if f == "PRODUIT":
                                return "Tu veux quel produit exactement stp ?"
                            if f == "SPECS":
                                return "Tu veux quelle taille et quel type stp ?"
                            if f == "QUANTITÉ":
                                return "Tu veux combien (carton/paquets) stp ?"
                            if f == "ZONE":
                                return "Tu es dans quelle commune/quartier stp ?"
                            if f in {"NUMÉRO", "NUMERO"}:
                                return "Ton numéro WhatsApp pour le livreur stp ?"
                            if f == "PAIEMENT":
                                return "Tu peux envoyer l’acompte Wave de 2000 FCFA et la capture stp ?"
                            return "Tu peux préciser stp ?"

                        response = _fallback_question(nf)
                        print(f"🛡️ [FAILSAFE] validation_phantom_blocked | missing={','.join(missing_now)} | next={nf}")
            except StopIteration as _skip_fs:
                print(f"🛡️ [FAILSAFE] SKIP: {_skip_fs}")
            except Exception as _fs_e:
                print(f"⚠️ [FAILSAFE] error: {type(_fs_e).__name__}: {_fs_e}")

            # IMPORTANT: do NOT strip the orientation marker globally.
            # When price_calculation status=OK, the required output is:
            #   Line 1: ready_to_send (exact)
            #   Line 2: starts with '§§ ' + ONE question

            # Replace ##RECAP## marker by a structured recap built from price_calculation/last_total_snapshot.
            try:
                if re.search(r"##\s*RECAP\s*##", str(response or ""), flags=re.IGNORECASE):
                    price_block = ""
                    try:
                        price_block = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "")
                    except Exception:
                        price_block = ""

                    def _extract_local(tag: str) -> str:
                        try:
                            m = re.search(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", price_block, flags=re.IGNORECASE | re.DOTALL)
                            return (m.group(1) if m else "").strip()
                        except Exception:
                            return ""

                    def _int_or_none(v: str) -> Optional[int]:
                        try:
                            if not v:
                                return None
                            m = re.search(r"(\d+)", str(v))
                            return int(m.group(1)) if m else None
                        except Exception:
                            return None

                    recap_lines = []
                    try:
                        items = []
                        try:
                            items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                        except Exception:
                            items = []
                        if isinstance(items, list) and items:
                            for it in items:
                                if not isinstance(it, dict):
                                    continue
                                p = str(it.get("product") or it.get("variant") or "").strip().lower()
                                specs = str(it.get("specs") or it.get("spec") or "").strip().upper()
                                unit = str(it.get("unit") or "").strip().lower()
                                qty = it.get("qty")
                                if p == "pressions" and specs and unit == "lot" and isinstance(qty, int) and qty > 0:
                                    # Try read unit price from price_block, else show only subtotal if present.
                                    unit_price = _int_or_none(_extract_local("unit_price_fcfa"))
                                    subtotal = _int_or_none(_extract_local("product_subtotal_fcfa"))
                                    if unit_price:
                                        line = f"- Produit: pressions {specs} × {qty} lot ({UniversalPriceCalculator._fmt_fcfa(unit_price * qty)}F)"
                                    elif subtotal:
                                        line = f"- Produit: pressions {specs} × {qty} lot ({UniversalPriceCalculator._fmt_fcfa(subtotal)}F)"
                                    else:
                                        line = f"- Produit: pressions {specs} × {qty} lot"
                                    recap_lines.append(line)
                                elif p == "culottes" and specs and unit == "paquet" and isinstance(qty, int) and qty > 0:
                                    subtotal = _int_or_none(_extract_local("product_subtotal_fcfa"))
                                    if subtotal:
                                        line = f"- Produit: culottes {specs} × {qty} paquet ({UniversalPriceCalculator._fmt_fcfa(subtotal)}F)"
                                    else:
                                        line = f"- Produit: culottes {specs} × {qty} paquet"
                                    recap_lines.append(line)
                    except Exception:
                        recap_lines = []

                    if not recap_lines:
                        # fallback to totals only
                        snap = None
                        try:
                            snap = order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None)
                        except Exception:
                            snap = None
                        if isinstance(snap, dict):
                            subtotal = snap.get("product_subtotal")
                            zone = str(snap.get("zone") or "").strip()
                            fee = snap.get("delivery_fee")
                            total = snap.get("total")
                            if subtotal is not None:
                                recap_lines.append(f"- Produits: {UniversalPriceCalculator._fmt_fcfa(int(subtotal))}F")
                            if zone and fee is not None:
                                recap_lines.append(f"- Livraison: {zone} ({UniversalPriceCalculator._fmt_fcfa(int(fee))}F)")
                            if total is not None:
                                recap_lines.append(f"- Total: {UniversalPriceCalculator._fmt_fcfa(int(total))}F")

                    if not recap_lines:
                        try:
                            st_r = order_tracker.get_state(user_id)
                            prod_r = str(getattr(st_r, "produit", "") or "").strip()
                            specs_r = str(getattr(st_r, "produit_details", "") or "").strip()
                            qty_r = str(getattr(st_r, "quantite", "") or "").strip()
                            zone_r = str(getattr(st_r, "zone", "") or "").strip()
                            tel_r = str(getattr(st_r, "numero", "") or "").strip()
                            if prod_r or specs_r or qty_r:
                                recap_lines.append(f"- Produit: {prod_r} {specs_r} {qty_r}".strip())
                            if zone_r:
                                recap_lines.append(f"- Livraison: {zone_r}")
                            if tel_r:
                                recap_lines.append(f"- Numéro: {tel_r}")
                        except Exception:
                            pass

                    recap_block = "\n".join(recap_lines).strip()
                    response = re.sub(r"##\s*RECAP\s*##", recap_block, str(response or ""), flags=re.IGNORECASE).strip()
            except Exception:
                pass

            try:
                st_tel = order_tracker.get_state(user_id)
                tel_val = str(getattr(st_tel, "numero", "") or "").strip() or str(getattr(st_tel, "telephone", "") or "").strip()
                tel_digits = re.sub(r"[^\d]", "", tel_val)
                if len(tel_digits) == 10 and tel_digits.startswith("0"):
                    resp_low = str(response or "").lower()
                    if "pas au bon format" in resp_low or "n'est pas au bon format" in resp_low or "n’est pas au bon format" in resp_low:
                        parts = re.split(r"(?<=[.!?])\s+", str(response or "").strip())
                        kept = [p for p in parts if not re.search(r"(pas au bon format|n['’]est pas au bon format)", p, re.IGNORECASE)]
                        response = " ".join(kept).strip() or response
            except Exception:
                pass

            try:
                if isinstance(tool_call_req, dict) and str(tool_call_req.get("action") or "").strip().upper() == "SEND_PRICE_LIST":
                    pid = str(tool_call_req.get("product_id") or "").strip()
                    if not pid:
                        pid = str(order_tracker.get_custom_meta(user_id, "active_product_id", default="") or "").strip()
                    variant = str(tool_call_req.get("variant") or "").strip()
                    spec = tool_call_req.get("spec")
                    spec_s = str(spec).strip() if spec is not None and str(spec).strip() else None
                    if pid:
                        if variant:
                            list_text, list_items = _generate_price_list_for_tool_call(
                                company_id_val=company_id,
                                product_id_val=pid,
                                variant_val=variant,
                                spec_val=spec_s,
                            )
                        else:
                            list_text, list_items = _generate_price_table_for_product(
                                company_id_val=company_id,
                                product_id_val=pid,
                            )
                        if list_text and list_items:
                            order_tracker.set_custom_meta(user_id, "price_list_text", list_text)
                            order_tracker.set_custom_meta(user_id, "price_list_items", list_items)
                            order_tracker.set_flag(user_id, "awaiting_price_choice", True)
                            response = list_text
            except Exception:
                pass
            
            # 7. Récupérer état checklist
            # IMPORTANT: la checklist doit refléter l'état persistant (OrderStateTracker)
            # après parsing du <thinking>, sinon next_step reste bloqué à MISSING.
            checklist = self.prompt_system.get_checklist_state(user_id, company_id)
            try:
                st_post = order_tracker.get_state(user_id)
                checklist.model = bool(str(getattr(st_post, "produit", "") or "").strip())
                checklist.details = bool(str(getattr(st_post, "produit_details", "") or "").strip())
                checklist.quantity = bool(str(getattr(st_post, "quantite", "") or "").strip())
                checklist.zone = bool(str(getattr(st_post, "zone", "") or "").strip())
                checklist.telephone = bool(str(getattr(st_post, "numero", "") or "").strip())
                try:
                    paiement_post = str(getattr(st_post, "paiement", "") or "").strip().lower()
                    checklist.payment = bool(paiement_post.startswith("validé_") or paiement_post.startswith("valide_"))
                except Exception:
                    checklist.payment = False
            except Exception:
                pass
            
            # 8. Calcul temps traitement
            processing_time = (time.time() - start_time) * 1000
            
            print(f"✅ [SIMPLIFIED RAG] Terminé en {processing_time:.0f}ms")
            
            # 9. Construction résultat
            return SimplifiedRAGResult(
                response=response,
                confidence=0.95,  # Confiance élevée car prompt statique
                processing_time_ms=processing_time,
                checklist_state=checklist.to_string(),
                next_step=checklist.get_next_step(),
                detected_location=dynamic_context.get('detected_location'),
                shipping_fee=dynamic_context.get('shipping_fee'),
                usage=token_usage if isinstance(token_usage, dict) else None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=total_cost,
                model=str(model_used),
                thinking=thinking
            )
        
        except Exception as e:
            print(f"❌ [SIMPLIFIED RAG] Erreur: {e}")
            import traceback
            traceback.print_exc()
            
            # Retour fallback
            processing_time = (time.time() - start_time) * 1000
            return SimplifiedRAGResult(
                response="Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?",
                confidence=0.0,
                processing_time_ms=processing_time,
                checklist_state="Erreur",
                next_step="Réessayer",
                detected_location=None,
                shipping_fee=None
            )


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PUBLIQUE (COMPATIBLE AVEC L'API)
# ═══════════════════════════════════════════════════════════════════════════════

_simplified_rag_engine: Optional[SimplifiedRAGEngine] = None

def get_simplified_rag_engine() -> SimplifiedRAGEngine:
    """Retourne le singleton du moteur RAG simplifié"""
    global _simplified_rag_engine
    if _simplified_rag_engine is None:
        _simplified_rag_engine = SimplifiedRAGEngine()
    return _simplified_rag_engine


async def get_simplified_rag_response(
    query: str,
    company_id: str,
    user_id: str,
    company_name: str = "Rue du Grossiste",
    images: Optional[List[str]] = None,
    request_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Interface publique compatible avec l'API existante
    
    Args:
        query: Question utilisateur
        company_id: ID entreprise
        user_id: ID utilisateur
        company_name: Nom entreprise
        images: URLs images (optionnel)
        request_id: ID requête
    
    Returns:
        Dict avec response + métriques (compatible avec ancien format)
    """
    msg = str(query or "").strip()

    def _is_affirmation(s: str) -> bool:
        t = str(s or "").strip().lower()
        t = re.sub(r"\s+", " ", t)
        if not t:
            return False
        # Strong signals (including repeated forms)
        if re.fullmatch(r"(oui)( oui)*", t):
            return True
        if re.fullmatch(r"(ok|okay)( ok| okay)*", t):
            return True
        if t in {"oui", "ok", "okay", "d'accord", "dac", "daccord", "ça marche", "ca marche", "c'est bon", "cest bon", "valide", "validé", "validee", "go", "je confirme", "confirme", "confirmed"}:
            return True
        # Mixed short confirmations
        if t.startswith("oui") and any(k in t for k in ["merci", "stp", "svp", "je confirme", "confirme", "c'est bon", "cest bon"]):
            return True
        if "je confirme" in t or "oui je confirme" in t:
            return True
        return False

    def _is_negation(s: str) -> bool:
        t = str(s or "").strip().lower()
        return t in {"non", "nop", "pas", "annule", "annuler", "stop"}

    def _is_simple_ack(s: str) -> bool:
        t = str(s or "").strip().lower()
        return t in {"ok", "okay", "merci", "thanks", "d'accord", "dac", "reçu", "recu", "cool"}

    def _looks_like_new_request(s: str) -> bool:
        t = str(s or "").strip().lower()
        if len(t) >= 8 and any(k in t for k in ["ajoute", "changer", "finalement", "annule", "annuler", "modifier", "je veux", "je prend", "je prends", "rajoute", "plus", "encore"]):
            return True
        # Generic product/unit keywords (scalable, not company-specific)
        if any(k in t for k in ["taille", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "lot", "paquet", "livraison", "carton", "colis", "balle"]):
            return True
        return False

    def _is_price_request_local(msg: str) -> bool:
        m = str(msg or "").lower()
        return any(k in m for k in ["prix", "total", "ça fait combien", "ca fait combien", "combien", "montant"])

    def _is_total_request_local(msg: str, company_id: Optional[str] = None) -> bool:
        m = str(msg or "").lower()
        if not m.strip():
            return False
        # If the user explicitly asks about a product, do NOT short-circuit to last_total_snapshot.
        # Build exclusion keywords from catalog vtree keys (scalable) + generic unit/size keywords.
        product_keywords = {"taille", "lot", "paquet", "paquets", "carton", "cartons", "colis", "balle"}
        try:
            _cat_tr = get_company_catalog_v2(company_id) if company_id else None
            _vt_tr = _cat_tr.get("v") if isinstance(_cat_tr, dict) and isinstance(_cat_tr.get("v"), dict) else None
            if isinstance(_vt_tr, dict):
                for _vk in _vt_tr.keys():
                    _vk_low = str(_vk or "").strip().lower()
                    if _vk_low:
                        product_keywords.add(_vk_low)
        except Exception:
            pass
        if any(k in m for k in product_keywords):
            return False
        # Otherwise, only accept explicit cart/total wording.
        return any(
            k in m
            for k in [
                "total",
                "montant",
                "à payer",
                "a payer",
                "prix total",
                "au total",
                "ça fait combien",
                "ca fait combien",
            ]
        )

    def _extract_tag_local(xml: str, tag: str) -> str:
        try:
            m = re.search(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", str(xml or ""), flags=re.IGNORECASE | re.DOTALL)
            return (m.group(1) if m else "")
        except Exception:
            return ""

    def _parse_int_amount(s: str) -> Optional[int]:
        try:
            if s is None:
                return None
            txt = str(s)
            m = re.search(r"(\d+)", txt.replace(" ", ""))
            return int(m.group(1)) if m else None
        except Exception:
            return None

    def _snapshot_from_price_block(pc_meta: str) -> Optional[Dict[str, Any]]:
        pc = str(pc_meta or "").strip()
        if not pc:
            return None
        status = str(_extract_tag_local(pc, "status") or "").strip().upper()
        if status and status != "OK":
            return None
        total_fcfa = _parse_int_amount(_extract_tag_local(pc, "total_fcfa"))
        subtotal_fcfa = _parse_int_amount(_extract_tag_local(pc, "product_subtotal_fcfa"))
        delivery_fcfa = _parse_int_amount(_extract_tag_local(pc, "delivery_fee_fcfa"))
        zone = str(_extract_tag_local(pc, "zone") or "").strip() or None
        if total_fcfa is None and subtotal_fcfa is None and delivery_fcfa is None:
            return None
        try:
            items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
        except Exception:
            items = []
        return {
            "items": items if isinstance(items, list) else [],
            "zone": zone,
            "delivery_fee": delivery_fcfa,
            "product_subtotal": subtotal_fcfa,
            "total": total_fcfa,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _mini_route_confirmation(message: str) -> str:
        from core.llm_client import complete as mini_complete

        msg_txt = str(message or "").strip()
        prompt = (
            "Tu es un classificateur. Retourne uniquement du JSON valide.\n"
            "But: classifier la réponse client après une question de validation de commande.\n"
            "Sortie JSON: {\"action\": \"CONFIRM|CANCEL|EDIT_REQUEST|NEW_REQUEST|ACK|UNKNOWN\", \"confidence\": 0-1, \"reason\": \"...\"}.\n"
            "Règles: \n"
            "- CONFIRM si le client confirme/valide la commande.\n"
            "- CANCEL si le client refuse/annule.\n"
            "- ACK si simple acquittement (ok/merci/d'accord) sans demande.\n"
            "- EDIT_REQUEST si il veut changer quelque chose mais sans préciser un nouveau panier complet.\n"
            "- NEW_REQUEST si il formule une nouvelle demande (nouveau produit/qté/zone, etc.).\n"
            "- UNKNOWN sinon.\n"
            f"MESSAGE_CLIENT: {json.dumps(msg_txt, ensure_ascii=False)}\n"
        )

        try:
            raw = await mini_complete(
                prompt=prompt,
                model_name=os.getenv("CONFIRM_ROUTER_MODEL", "google/gemini-2.5-flash-lite"),
                temperature=0.0,
                max_tokens=int(os.getenv("CONFIRM_ROUTER_MAX_TOKENS", "120")),
            )
        except Exception:
            return "UNKNOWN"

        raw_s = str(raw or "").strip()
        try:
            data = json.loads(raw_s)
        except Exception:
            if "{" in raw_s and "}" in raw_s:
                try:
                    cand = raw_s[raw_s.find("{") : raw_s.rfind("}") + 1]
                    data = json.loads(cand)
                except Exception:
                    return "UNKNOWN"
            else:
                return "UNKNOWN"

        act = str((data or {}).get("action") or "").strip().upper()
        if act in {"CONFIRM", "CANCEL", "EDIT_REQUEST", "NEW_REQUEST", "ACK", "UNKNOWN"}:
            return act
        return "UNKNOWN"

    awaiting_code = str(order_tracker.get_custom_meta(user_id, "awaiting_confirmation_code", default="") or "").strip()
    confirmed_code = str(order_tracker.get_custom_meta(user_id, "order_confirmed_code", default="") or "").strip()

    async def _mini_smalltalk_reply(message: str) -> str:
        from core.llm_client import complete as mini_complete

        msg_txt = str(message or "").strip()
        prompt = (
            "Tu es un assistant WhatsApp très bref.\n"
            "But: répondre aux messages de politesse/ack (merci, ok, super, d'accord) après une commande.\n"
            "Règles: 0-6 mots, max 1 emoji, pas de question, pas de prix, pas de nouveaux sujets.\n"
            "Si une réponse n'est pas nécessaire, réponds exactement: SILENCE\n"
            f"MESSAGE_CLIENT: {json.dumps(msg_txt, ensure_ascii=False)}\n"
        )
        try:
            raw = await mini_complete(
                prompt=prompt,
                model_name=os.getenv("POST_CONFIRM_MINI_MODEL", "google/gemini-2.5-flash-lite"),
                temperature=0.2,
                max_tokens=int(os.getenv("POST_CONFIRM_MINI_MAX_TOKENS", "40")),
            )
        except Exception:
            return ""
        out = str(raw or "").strip()
        if out.upper() == "SILENCE":
            return ""
        return out

    if awaiting_code and not confirmed_code:
        # We are waiting for the client's explicit YES/NO.
        if _is_affirmation(msg):
            order_tracker.set_custom_meta(user_id, "order_confirmed_code", awaiting_code)
            order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", "")
            return {
                "response": "Commande confirmée ✅\nL'équipe vous rappelera pour procéder à votre livraison.\nMerci de ne pas répondre à ce message.",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "confirmation_code",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "CONFIRMED",
                "next_step": "STOP",
                "detected_location": None,
                "shipping_fee": None,
            }
        if _is_negation(msg):
            order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", "")
            return {
                "response": "D'accord 👍 Dites-moi juste ce que vous voulez changer (produit, taille, quantité ou livraison).",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "order_confirmation",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "EDIT",
                "next_step": "CONTINUE",
                "detected_location": None,
                "shipping_fee": None,
            }

        if _is_simple_ack(msg) and (not _looks_like_new_request(msg)):
            return {
                "response": "OK ✅",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "order_confirmation",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "AWAITING_CONFIRMATION",
                "next_step": "WAIT_CONFIRMATION",
                "detected_location": None,
                "shipping_fee": None,
            }

    # Post-confirmation: mini-LLM routeur systématique pour TOUS les messages.
    if confirmed_code:
        # Fast path: pure confirmation/ack → block
        if _is_affirmation(msg) or (_is_simple_ack(msg) and not _looks_like_new_request(msg)):
            print(f"🛑 [POST_CONFIRM] blocked ack/confirm: '{msg[:50]}'")
            return {
                "response": "Votre commande est déjà confirmée ✅ L'équipe vous contactera pour la livraison. Merci de ne pas répondre à ce message.",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "short_circuit",
                "context_used": "post_confirmation_block",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "CONFIRMED",
                "next_step": "STOP",
                "detected_location": None,
                "shipping_fee": None,
            }

        # All other messages → mini-LLM router to classify intent
        try:
            route_action = await _mini_route_confirmation(msg)
            print(f"🔀 [POST_CONFIRM_ROUTER] action={route_action} | msg='{msg[:60]}'")
        except Exception as _route_e:
            print(f"⚠️ [POST_CONFIRM_ROUTER] error: {_route_e}")
            route_action = "UNKNOWN"

        if route_action in {"CONFIRM", "ACK"}:
            return {
                "response": "Votre commande est déjà confirmée ✅ L'équipe vous contactera pour la livraison. Merci de ne pas répondre à ce message.",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "mini_llm_router",
                "context_used": "post_confirmation_block",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "CONFIRMED",
                "next_step": "STOP",
                "detected_location": None,
                "shipping_fee": None,
            }

        if route_action == "CANCEL":
            try:
                order_tracker.set_custom_meta(user_id, "order_confirmed_code", "")
            except Exception:
                pass
            return {
                "response": "D'accord, votre commande est annulée. Dites-moi si vous souhaitez passer une nouvelle commande 👍",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": "mini_llm_router",
                "context_used": "post_confirmation_cancel",
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": "CANCELLED",
                "next_step": "RESTART",
                "detected_location": None,
                "shipping_fee": None,
            }

        if route_action in {"EDIT_REQUEST", "NEW_REQUEST"}:
            # Re-open flow → route to full Jessica LLM
            try:
                order_tracker.set_custom_meta(user_id, "order_confirmed_code", "")
                print(f"🔓 [POST_CONFIRM] re-opened flow for {route_action}")
            except Exception:
                pass
            # Fall through to full LLM below

        # UNKNOWN → also route to Jessica (could be SAV, question, etc.)
        if route_action == "UNKNOWN":
            print(f"❓ [POST_CONFIRM] UNKNOWN intent, routing to Jessica LLM")

    # ── PATCH C: Short-circuit total/price requests when cart is already known ──
    # Si le client demande le total/combien et qu'on a déjà un panier + prix calculé,
    # Python répond directement sans appeler le LLM (économie ~9000 tokens).
    # IMPORTANT: Toujours recalculer depuis CartManager (source de vérité), jamais depuis le cache.
    if _is_price_request_local(msg) and not _looks_like_new_request(msg):
        try:
            _engine_tmp = get_simplified_rag_engine()
            _cart_data = _engine_tmp.cart_manager.get_cart(user_id)
            _cart_items = _cart_data.get("items", []) if isinstance(_cart_data, dict) else []

            ready_stored = ""
            if _cart_items:
                _st_sc = order_tracker.get_state(user_id)
                _zone_sc = str(getattr(_st_sc, "zone", "") or "").strip()
                _fee_sc = None
                if _zone_sc:
                    try:
                        from core.delivery_zone_extractor import extract_delivery_zone_and_cost
                        _zinfo_sc = extract_delivery_zone_and_cost(_zone_sc)
                        _fee_val = (_zinfo_sc or {}).get("cost") if isinstance(_zinfo_sc, dict) else None
                        if isinstance(_fee_val, (int, float)) and int(_fee_val) > 0:
                            _fee_sc = int(_fee_val)
                    except Exception:
                        pass
                # Recalculer le prix depuis CartManager (source de vérité)
                _pc_fresh = UniversalPriceCalculator.build_price_calculation_block_from_detected_items(
                    company_id=company_id,
                    items=_cart_items,
                    zone=_zone_sc,
                    delivery_fee_fcfa=_fee_sc,
                )
                if str(_pc_fresh or "").strip():
                    ready_stored = str(_extract_tag_local(_pc_fresh, "ready_to_send") or "").strip()
                    # Persister le prix recalculé
                    if ready_stored:
                        order_tracker.set_custom_meta(
                            user_id,
                            "price_calculation_block",
                            "<price_calculation>\n" + str(_pc_fresh).strip() + "\n</price_calculation>",
                        )

            if ready_stored:
                # ── Simplifier: extraire le total et utiliser le format court ──
                _simple_sc = ready_stored
                try:
                    _total_tag = str(_extract_tag_local(_pc_fresh, "total_fcfa") or "").strip()
                    if _total_tag and _total_tag.isdigit():
                        _t_int = int(_total_tag)
                        _simple_sc = f"Noté, ça fera {_t_int:,}F.".replace(",", " ")
                except Exception:
                    pass

                # ── Follow-up intelligent: vérifier ce qui manque RÉELLEMENT ──
                _st_sc2 = order_tracker.get_state(user_id)
                _missing = sorted(list(_st_sc2.get_missing_fields())) if hasattr(_st_sc2, "get_missing_fields") else []

                _has_numero = "NUMÉRO" not in _missing and "NUMERO" not in _missing
                _has_zone = "ZONE" not in _missing
                _has_paiement = "PAIEMENT" not in _missing

                follow_up = ""
                if _has_numero and _has_zone and _has_paiement:
                    follow_up = "\nEnvoyez-moi une capture du paiement dès que c'est fait 📸"
                elif _has_numero and _has_zone and not _has_paiement:
                    payment_phone_s = str(os.getenv("PAYMENT_PHONE", "+225 0787360757") or "+225 0787360757").strip()
                    expected_deposit = str(os.getenv("EXPECTED_DEPOSIT", "2000 FCFA") or "2000 FCFA").strip()
                    follow_up = f"\nJ'aurais besoin d'un dépôt de validation de {expected_deposit} via Wave au {payment_phone_s} pour valider votre commande ; une fois fait envoyez-moi une capture svp 📸"
                elif not _has_numero and not _has_zone:
                    follow_up = "\nPouvez-vous m'envoyer le numéro à joindre ainsi que le lieu de livraison (commune) ?"
                elif not _has_numero and _has_zone:
                    follow_up = "\nSur quel numéro peut-on vous joindre pour la livraison ?"
                elif not _has_zone and _has_numero:
                    follow_up = "\nVous êtes dans quelle commune/quartier pour la livraison ?"

                print(f"⚡ [SHORT_CIRCUIT_PRICE] simplified | items={len(_cart_items)} | missing={_missing}")
                return {
                    "response": _simple_sc + follow_up,
                    "confidence": 1.0,
                    "documents_found": True,
                    "processing_time_ms": 0,
                    "search_method": "python_price_shortcircuit",
                    "context_used": "cart_price_live",
                    "thinking": "",
                    "validation": None,
                    "usage": {},
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "model": "none",
                    "checklist_state": "PRICE_SHOWN",
                    "next_step": "PAIEMENT" if not _has_paiement else "CONTINUE",
                    "detected_location": None,
                    "shipping_fee": None,
                }
        except Exception as _sc_e:
            print(f"⚠️ [SHORT_CIRCUIT_PRICE] error: {type(_sc_e).__name__}: {_sc_e}")

    # ── SHORT-CIRCUIT ENGINE: bypass LLM pour messages simples ──
    # (numéro de téléphone, zone seule, capture paiement)
    try:
        from core.short_circuit_engine import check_short_circuit as _sc_check
        _sc_engine = get_simplified_rag_engine()
        _sc_result = _sc_check(
            message=msg,
            user_id=user_id,
            company_id=company_id,
            cart_manager=_sc_engine.cart_manager,
            order_tracker=order_tracker,
            has_image=bool(images and len(images) > 0),
        )
        if _sc_result and _sc_result.get("response"):
            sc_type = _sc_result.get("sc_type", "UNKNOWN")
            print(f"⚡ [SHORT_CIRCUIT] type={sc_type} → Python direct (0 LLM tokens)")
            return {
                "response": str(_sc_result["response"]),
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": 0,
                "search_method": str(_sc_result.get("search_method", "python_short_circuit")),
                "context_used": str(_sc_result.get("context_used", "short_circuit")),
                "thinking": "",
                "validation": None,
                "usage": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "model": "none",
                "checklist_state": f"SC_{sc_type}",
                "next_step": "CONTINUE",
                "detected_location": None,
                "shipping_fee": None,
            }
    except Exception as _sc_err:
        print(f"⚠️ [SHORT_CIRCUIT] error: {type(_sc_err).__name__}: {_sc_err}")

    engine = get_simplified_rag_engine()
    
    result = await engine.process_query(
        query=query,
        user_id=user_id,
        company_id=company_id,
        company_name=company_name,
        images=images,
        request_id=request_id
    )

    # IMPORTANT: do not strip the orientation marker here.
    # The marker may be needed for downstream formatting rules.

    try:
        pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
        snap = _snapshot_from_price_block(pc_meta)
        if snap:
            order_tracker.set_custom_meta(user_id, "last_total_snapshot", snap)
    except Exception:
        pass
    try:
        st_after = order_tracker.get_state(user_id)
        is_complete = bool(getattr(st_after, "is_complete", lambda: False)())
    except Exception:
        is_complete = False

    try:
        resp_l = str(result.response or "").lower()
        asks_validation = bool(re.search(r"\b(on\s+valide|on\s+confirme|c['’]?est\s+bien\s+ça)\b", resp_l)) and ("?" in str(result.response or ""))
        already_waiting = bool(str(order_tracker.get_custom_meta(user_id, "awaiting_confirmation_code", default="") or "").strip())
        already_confirmed = bool(str(order_tracker.get_custom_meta(user_id, "order_confirmed_code", default="") or "").strip())
        if is_complete and (not already_waiting) and (not already_confirmed):
            # ── OPT-2: Auto-clôture si paiement validé ──
            # Si le paiement est déjà validé (validé_XXXF), pas besoin de demander confirmation.
            # On clôture directement → économie d'1 tour complet.
            _paiement_now = ""
            try:
                _st_cloture = order_tracker.get_state(user_id)
                _paiement_now = str(getattr(_st_cloture, "paiement", "") or "").strip()
            except Exception:
                _paiement_now = ""

            _payment_is_validated = _paiement_now.lower().startswith("validé_") or _paiement_now.lower().startswith("valide_")

            if _payment_is_validated:
                # Paiement validé + commande complète → clôture directe (0 tour supplémentaire)
                _auto_code = uuid.uuid4().hex[:8]
                order_tracker.set_custom_meta(user_id, "order_confirmed_code", _auto_code)
                order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", "")

                # Construire le recap dynamique depuis price_calculation_block + order state
                _cloture_msg = "Commande confirmée ✅\nL'équipe vous rappelera pour procéder à votre livraison.\nMerci pour votre confiance 🙏"
                try:
                    _pc_auto = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
                    _total_tag = str(_extract_tag_local(_pc_auto, "total_fcfa") or "").strip()
                    _subtotal_tag = str(_extract_tag_local(_pc_auto, "product_subtotal_fcfa") or "").strip()
                    _fee_tag = str(_extract_tag_local(_pc_auto, "delivery_fee_fcfa") or "").strip()
                    _zone_tag = str(_extract_tag_local(_pc_auto, "zone") or "").strip()

                    # Extraire le montant de l'avance depuis le paiement
                    _advance_amount = 0
                    try:
                        _adv_match = re.search(r"(\d+)", _paiement_now)
                        if _adv_match:
                            _advance_amount = int(_adv_match.group(1))
                    except Exception:
                        pass

                    _total_int = int(_total_tag) if _total_tag and _total_tag.isdigit() else 0
                    _fee_int = int(_fee_tag) if _fee_tag and _fee_tag.isdigit() else 0
                    _balance = max(0, _total_int - _advance_amount) if _total_int and _advance_amount else 0

                    # Construire les lignes panier depuis CartManager
                    _cart_lines = []
                    try:
                        _rag_eng = get_simplified_rag_engine()
                        if _rag_eng and _rag_eng.cart_manager:
                            _cart_data = _rag_eng.cart_manager.get_cart(user_id)
                            _cart_items_recap = _cart_data.get("items", []) if isinstance(_cart_data, dict) else []
                            for _ci in _cart_items_recap:
                                _cv = str(_ci.get("variant") or "").strip()
                                _cs = str(_ci.get("spec") or _ci.get("specs") or "").strip()
                                _cu = str(_ci.get("unit") or "").strip().replace("_", " ")
                                _cq = _ci.get("qty") or 1
                                _cp = int(_ci.get("price_fcfa") or _ci.get("unit_price") or 0)
                                _item_label = (_cv + (" " + _cs if _cs else "")).strip() or "Produit"
                                _unit_label = _cu if _cu else ""
                                _price_str = f"{_cp:,}".replace(",", " ") + " F" if _cp else ""
                                _cart_lines.append(f"• {_item_label} — {_unit_label} x{_cq} : {_price_str}")
                    except Exception:
                        pass

                    # Délai de livraison
                    _delai_txt = ""
                    try:
                        from core.timezone_helper import get_delai_message
                        _delai_txt = get_delai_message()
                    except Exception:
                        _delai_txt = ""

                    if _total_int > 0:
                        _recap_lines = ["Commande validée ✅", ""]
                        _recap_lines.append("🧺 Votre commande")
                        if _cart_lines:
                            _recap_lines.extend(_cart_lines)
                        if _fee_int > 0 and _zone_tag:
                            _recap_lines.append(f"🚚 Livraison {_zone_tag} : {_fee_int:,} F".replace(",", " "))
                        _recap_lines.append(f"💰 Total : {_total_int:,} F".replace(",", " "))
                        _recap_lines.append("")
                        if _advance_amount > 0:
                            _recap_lines.append(f"Avance reçue : {_advance_amount:,} FCFA".replace(",", " "))
                            if _balance > 0:
                                _recap_lines.append(f"Reste à payer à la livraison : {_balance:,} FCFA".replace(",", " "))
                        _recap_lines.append("")
                        if _delai_txt:
                            _recap_lines.append(f"🚚 {_delai_txt}")
                            _recap_lines.append("")
                        _recap_lines.append("L'équipe vous rappelera. Merci ! 🙏")
                        _cloture_msg = "\n".join(_recap_lines)
                except Exception:
                    pass

                print(f"⚡ [AUTO_CLOTURE] payment={_paiement_now} → clôture directe (skip confirmation) | code={_auto_code}")
                return {
                    "response": _cloture_msg,
                    "confidence": 1.0,
                    "documents_found": True,
                    "processing_time_ms": result.processing_time_ms,
                    "search_method": "python_auto_cloture",
                    "context_used": "payment_validated_complete",
                    "thinking": result.thinking,
                    "validation": None,
                    "usage": result.usage,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "total_tokens": result.total_tokens,
                    "cost": result.cost,
                    "model": result.model,
                    "checklist_state": "CONFIRMED",
                    "next_step": "STOP",
                    "detected_location": result.detected_location,
                    "shipping_fee": result.shipping_fee,
                }

            # Paiement non validé → flow normal avec confirmation
            code = uuid.uuid4().hex[:8]
            order_tracker.set_custom_meta(user_id, "awaiting_confirmation_code", code)

            pc_meta = str(order_tracker.get_custom_meta(user_id, "price_calculation_block", default="") or "").strip()
            snap = _snapshot_from_price_block(pc_meta) or (order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None) or None)
            zone = None
            delivery_fee = None
            product_subtotal = None
            total = None
            if isinstance(snap, dict):
                zone = snap.get("zone")
                delivery_fee = snap.get("delivery_fee")
                product_subtotal = snap.get("product_subtotal")
                total = snap.get("total")

            try:
                st_now = order_tracker.get_state(user_id)
                phone = str(getattr(st_now, "numero", "") or getattr(st_now, "telephone", "") or "").strip()
            except Exception:
                phone = ""

            try:
                pay = str(order_tracker.get_custom_meta(user_id, "paiement", default="") or "").strip()
            except Exception:
                pay = ""

            # ── Build recap: prefer ready_to_send (detailed, Python-calculated) ──
            ready_to_send_recap = ""
            try:
                ready_to_send_recap = str(_extract_tag_local(pc_meta, "ready_to_send") or "").strip()
            except Exception:
                pass

            lines = []

            if ready_to_send_recap:
                # ready_to_send already contains item breakdown + total
                lines.append(ready_to_send_recap)
            else:
                # Fallback: build manually from detected_items + snapshot
                try:
                    items = order_tracker.get_custom_meta(user_id, "detected_items", default=[])
                except Exception:
                    items = []
                if isinstance(items, list) and items:
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        p = str(it.get("product") or "").strip().upper()
                        specs = str(it.get("specs") or "").strip().upper()
                        unit = str(it.get("unit") or "").strip().lower()
                        qty = it.get("qty")
                        if p and isinstance(qty, int) and qty > 0:
                            sfx = f" {specs}" if specs else ""
                            ufx = f" {unit}" if unit else ""
                            lines.append(f"- {p}{sfx} x{qty} {ufx}".strip())

                if zone:
                    fee_out = delivery_fee
                    try:
                        fee_i = int(fee_out) if fee_out is not None else None
                    except Exception:
                        fee_i = None

                    if fee_i is None or fee_i <= 0:
                        try:
                            from core.delivery_zone_extractor import extract_delivery_zone_and_cost

                            zinfo = extract_delivery_zone_and_cost(str(zone))
                            fee2 = (zinfo or {}).get("cost") if isinstance(zinfo, dict) else None
                            if isinstance(fee2, (int, float)) and int(fee2) > 0:
                                fee_i = int(fee2)
                                fee_out = fee_i
                        except Exception:
                            pass

                    if fee_i is not None and fee_i > 0:
                        lines.append(f"Livraison {zone} → {UniversalPriceCalculator._fmt_fcfa(int(fee_i))}F")
                        try:
                            delivery_fee = int(fee_i)
                        except Exception:
                            pass
                    else:
                        lines.append(f"Livraison {zone}")
                if total is not None:
                    if product_subtotal is not None and delivery_fee is not None:
                        lines.append(
                            f"Total : {UniversalPriceCalculator._fmt_fcfa(int(total))}F (produits {UniversalPriceCalculator._fmt_fcfa(int(product_subtotal))}F + livraison {UniversalPriceCalculator._fmt_fcfa(int(delivery_fee))}F)"
                        )
                    else:
                        lines.append(f"Total : {UniversalPriceCalculator._fmt_fcfa(int(total))}F")

            recap = "\n".join([str(x).strip() for x in lines if str(x).strip()])

            print(f"📋 [CONFIRMATION_RECAP] code={code} | recap_len={len(recap)}")
            return {
                "response": f"{recap}\n\nVous confirmez votre commande ?",
                "confidence": 1.0,
                "documents_found": True,
                "processing_time_ms": result.processing_time_ms,
                "search_method": "python_recap",
                "context_used": f"Checklist: {result.checklist_state}",
                "thinking": result.thinking,
                "validation": None,
                "usage": result.usage,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "cost": result.cost,
                "model": result.model,
                "checklist_state": result.checklist_state,
                "next_step": "WAIT_CONFIRMATION",
                "detected_location": result.detected_location,
                "shipping_fee": result.shipping_fee,
            }
    except Exception:
        pass
    
    # ── CartManager: récupérer le panier pour l'API response ──
    cart_items_for_response = []
    cart_pending_for_response = None
    try:
        _cm = engine.cart_manager
        _cart = _cm.get_cart(user_id)
        cart_items_for_response = _cart.get("items", [])
        cart_pending_for_response = _cart.get("pending_pivot")
    except Exception:
        pass

    # Format compatible avec l'ancien système
    return {
        "response": result.response,
        "confidence": result.confidence,
        "documents_found": True,  # Toujours True car prompt statique
        "processing_time_ms": result.processing_time_ms,
        "search_method": "simplified_prompt_system",
        "context_used": f"Checklist: {result.checklist_state}",
        "thinking": result.thinking,
        "validation": None,
        
        # Métriques LLM
        "usage": result.usage,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "cost": result.cost,
        "model": result.model,
        
        # Infos supplémentaires
        "checklist_state": result.checklist_state,
        "next_step": result.next_step,
        "detected_location": result.detected_location,
        "shipping_fee": result.shipping_fee,

        # Panier multi-produits (CartManager)
        "cart": {
            "items": cart_items_for_response,
            "pending_pivot": cart_pending_for_response,
            "items_count": len(cart_items_for_response),
        },
    }
