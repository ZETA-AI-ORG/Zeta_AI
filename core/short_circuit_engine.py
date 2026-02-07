"""
⚡ SHORT-CIRCUIT ENGINE — Bypass LLM pour messages simples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cas gérés (0 token LLM) :
  1. Numéro de téléphone seul  → récap + demande acompte Wave
  2. Zone de livraison seule   → frais + total + demande numéro
  3. Capture paiement (image)  → accusé réception
  4. Confirmation implicite    → (non implémenté ici, géré par post-confirm)

Garde-fous :
  - Message contient un mot interrogatif → JAMAIS short-circuit
  - Message contient un nom/variant produit du catalogue → JAMAIS short-circuit
  - Message > 40 mots → JAMAIS short-circuit
  - Cart vide → JAMAIS short-circuit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import re
import logging
import unicodedata
from typing import Optional, Dict, Any, List, Set

logger = logging.getLogger("short_circuit")

# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION DETECTION — Dictionnaire compact français
# ═══════════════════════════════════════════════════════════════════════════════

# Mots interrogatifs français (début de phrase ou isolés)
_QUESTION_WORDS_START: Set[str] = {
    # Pronoms / adverbes interrogatifs
    "qui", "que", "quoi", "quel", "quelle", "quels", "quelles",
    "lequel", "laquelle", "lesquels", "lesquelles",
    "où", "ou",  # avec et sans accent
    "quand", "comment", "combien", "pourquoi",
    # Locutions interrogatives
    "est-ce", "est ce",
    # Verbes inversés fréquents (début de phrase)
    "avez-vous", "avez vous", "as-tu",
    "pouvez-vous", "pouvez vous", "peux-tu",
    "peut-on", "peut on",
    "faites-vous", "faites vous", "fais-tu",
    "livrez-vous", "livrez vous",
    "acceptez-vous", "acceptez vous",
    "proposez-vous", "proposez vous",
    "y a-t-il", "y a t il", "y'a",
}

# Patterns interrogatifs qui peuvent apparaître n'importe où dans la phrase
_QUESTION_PATTERNS_ANYWHERE: List[str] = [
    r"\best[- ]ce que\b",
    r"\best[- ]ce qu['\u2019]",
    r"\bc['\u2019]est combien\b",
    r"\bça fait combien\b",
    r"\bca fait combien\b",
    r"\bc['\u2019]est quoi\b",
    r"\bça coûte combien\b",
    r"\bca coute combien\b",
    r"\bvous avez\b.*\?",
    r"\btu as\b.*\?",
    r"\bil y a\b.*\?",
    r"\bje peux\b.*\?",
    r"\bon peut\b.*\?",
    r"\bça marche comment\b",
    r"\bca marche comment\b",
    r"\bcomment ça\b",
    r"\bcomment ca\b",
    r"\bpourquoi\b",
    r"\bcombien\b",
    r"\bquel\b",
    r"\bquelle\b",
]


def _normalize_for_detection(text: str) -> str:
    """Minuscules + suppression accents + espaces normalisés."""
    t = str(text or "").strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = re.sub(r"[-_]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_question(message: str) -> bool:
    """Détecte si le message est une question (interrogatif)."""
    raw = str(message or "").strip()
    if not raw:
        return False

    # 1) Point d'interrogation explicite
    if "?" in raw:
        return True

    norm = _normalize_for_detection(raw)
    words = norm.split()
    if not words:
        return False

    # 2) Commence par un mot interrogatif (word-boundary check)
    for qw in _QUESTION_WORDS_START:
        qw_n = _normalize_for_detection(qw)
        if not qw_n:
            continue
        # Must match as complete word(s) at start, not prefix of another word
        # e.g. "ou" must not match "oui"
        pat = rf"^{re.escape(qw_n)}(?:\s|$)"
        if re.match(pat, norm):
            return True

    # 3) Pattern interrogatif n'importe où
    for pat in _QUESTION_PATTERNS_ANYWHERE:
        try:
            pat_n = _normalize_for_detection(pat)
            if re.search(pat_n, norm, flags=re.IGNORECASE):
                return True
        except Exception:
            pass

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT KEYWORD DETECTION — Scalable depuis catalogue
# ═══════════════════════════════════════════════════════════════════════════════

def _build_product_keywords(company_id: Optional[str]) -> Set[str]:
    """Construit dynamiquement les mots-clés produit depuis le catalogue."""
    keywords: Set[str] = set()
    if not company_id:
        return keywords
    try:
        from core.company_catalog_v2_loader import get_company_catalog_v2
        cat = get_company_catalog_v2(company_id)
        if not isinstance(cat, dict):
            return keywords

        def _extract_from_product(p: Dict[str, Any]):
            if not isinstance(p, dict):
                return
            cat_inner = p.get("catalog_v2") if isinstance(p.get("catalog_v2"), dict) else p
            if not isinstance(cat_inner, dict):
                return
            # Nom produit
            pname = str(cat_inner.get("product_name") or cat_inner.get("name") or "").strip().lower()
            if pname:
                for tok in pname.split():
                    tok_clean = _normalize_for_detection(tok)
                    if len(tok_clean) >= 3:
                        keywords.add(tok_clean)
            # Variants depuis vtree
            vtree = cat_inner.get("v") if isinstance(cat_inner.get("v"), dict) else None
            if isinstance(vtree, dict):
                for vk in vtree.keys():
                    vk_n = _normalize_for_detection(str(vk or ""))
                    if vk_n and len(vk_n) >= 3:
                        keywords.add(vk_n)

        # Multi-product container
        plist = cat.get("products")
        if isinstance(plist, list):
            for p in plist:
                _extract_from_product(p)
        else:
            _extract_from_product(cat)

    except Exception:
        pass
    return keywords


def _message_mentions_product(message: str, company_id: Optional[str]) -> bool:
    """Vérifie si le message mentionne un produit/variant du catalogue."""
    norm = _normalize_for_detection(message)
    if not norm:
        return False
    product_kw = _build_product_keywords(company_id)
    # Aussi ajouter des mots génériques liés aux produits/unités
    generic_kw = {"taille", "lot", "paquet", "paquets", "carton", "cartons", "colis", "balle"}
    all_kw = product_kw | generic_kw
    for kw in all_kw:
        if kw and kw in norm:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# PHONE NUMBER DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Côte d'Ivoire : 10 chiffres, commence par 0 ou +225
_PHONE_PATTERNS = [
    # 07 12 34 56 78 / 0712345678
    r"^[+]?(?:225\s*)?0[1-9](?:\s?\d{2}){4}$",
    # +225 07 12 34 56 78
    r"^[+]?225\s*0[1-9](?:\s?\d{2}){4}$",
    # Formats avec tirets : 07-12-34-56-78
    r"^[+]?(?:225\s*)?0[1-9](?:[-.\s]?\d{2}){4}$",
]


def _extract_phone(message: str) -> Optional[str]:
    """Extrait un numéro de téléphone CI si le message est UNIQUEMENT un numéro."""
    raw = str(message or "").strip()
    # Nettoyer ponctuation finale
    raw = re.sub(r"[.,;!]+$", "", raw).strip()
    if not raw:
        return None
    for pat in _PHONE_PATTERNS:
        if re.match(pat, raw):
            # Normaliser : garder uniquement les chiffres
            digits = re.sub(r"[^\d]", "", raw)
            # Si commence par 225, c'est le préfixe pays
            if digits.startswith("225") and len(digits) == 13:
                return digits[3:]  # Garder les 10 chiffres locaux
            if len(digits) == 10 and digits.startswith("0"):
                return digits
            return None
    return None


# Pattern pour trouver un numéro CI DANS un texte plus long
_PHONE_INLINE_RE = re.compile(
    r"[+]?(?:225\s*)?0[1-9](?:[-.\s]?\d{2}){4}"
)


def _extract_phone_from_text(message: str):
    """Extrait un numéro CI depuis un texte mixte (ex: 'angre 0160924560').

    Returns:
        tuple: (phone_normalized, remaining_text) ou (None, original_message)
    """
    raw = str(message or "").strip()
    m = _PHONE_INLINE_RE.search(raw)
    if not m:
        return None, raw
    matched = m.group(0).strip()
    digits = re.sub(r"[^\d]", "", matched)
    phone = None
    if digits.startswith("225") and len(digits) == 13:
        phone = digits[3:]
    elif len(digits) == 10 and digits.startswith("0"):
        phone = digits
    if not phone:
        return None, raw
    # Texte restant après suppression du numéro
    remaining = (raw[:m.start()] + " " + raw[m.end():]).strip()
    remaining = re.sub(r"\s+", " ", remaining).strip()
    return phone, remaining


def _format_phone_display(phone: str) -> str:
    """Formate un numéro pour affichage : 07 12 34 56 78."""
    d = str(phone or "")
    if len(d) == 10:
        return f"{d[0:2]} {d[2:4]} {d[4:6]} {d[6:8]} {d[8:10]}"
    return d


# ═══════════════════════════════════════════════════════════════════════════════
# ZONE DETECTION (réutilise delivery_zone_extractor)
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_zone_simple(message: str) -> Optional[Dict[str, Any]]:
    """Détecte une zone si le message est COURT et contient uniquement une zone."""
    raw = str(message or "").strip()
    # Max 4 mots (ex: "à Cocody", "Yopougon", "port bouet", "livraison cocody")
    words = raw.split()
    if len(words) > 5:
        return None
    try:
        from core.delivery_zone_extractor import extract_delivery_zone_and_cost
        return extract_delivery_zone_and_cost(raw)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES DE RÉPONSE
# ═══════════════════════════════════════════════════════════════════════════════

def _get_payment_phone() -> str:
    return str(os.getenv("PAYMENT_PHONE", "+225 0787360757") or "+225 0787360757").strip()


def _get_expected_deposit() -> str:
    return str(os.getenv("EXPECTED_DEPOSIT", "2 000 FCFA") or "2 000 FCFA").strip()


def _format_price(amount: int) -> str:
    """Formate un montant : 24000 → '24 000F'."""
    return f"{amount:,}F".replace(",", " ")


def _build_cart_recap_lines(
    cart_items: List[Dict[str, Any]],
    zone: Optional[str] = None,
    delivery_fee: Optional[int] = None,
    total: Optional[int] = None,
) -> str:
    """Construit un récapitulatif textuel du panier."""
    lines = ["📦 Récapitulatif :"]
    for item in cart_items:
        variant = str(item.get("variant") or "").strip()
        spec = str(item.get("spec") or item.get("specs") or "").strip()
        unit = str(item.get("unit") or "").strip()
        qty = item.get("qty") or 1
        label = (variant + (" " + spec if spec else "")).strip() or "Produit"
        unit_label = unit.replace("_", " ") if unit else ""
        lines.append(f"- {qty} {unit_label} {label}".strip())

    if zone:
        fee_str = _format_price(delivery_fee) if delivery_fee else "à calculer"
        lines.append(f"- Livraison {zone} ({fee_str})")

    if total:
        lines.append(f"💰 Total : {_format_price(total)}")

    return "\n".join(lines)


def template_numero_recu(
    cart_items: List[Dict[str, Any]],
    phone: str,
    zone: Optional[str] = None,
    delivery_fee: Optional[int] = None,
    total: Optional[int] = None,
    paiement_status: Optional[str] = None,
) -> str:
    """Template quand le client envoie son numéro.
    
    Scalable — aucun nom de produit hardcodé.
    Vérifie order_state pour ne jamais redemander une info déjà collectée.
    """
    _paid = bool(paiement_status and ("valid" in str(paiement_status).lower() or "reçu" in str(paiement_status).lower()))

    if not zone:
        return "Parfait !\nVous êtes dans quelle commune/quartier pour la livraison ?"

    # Zone + Numéro + Paiement déjà OK → simple confirmation
    if _paid:
        return "Parfait ! Tout est noté ✅"

    # Zone + Numéro OK, paiement manquant → demander paiement
    payment_phone = _get_payment_phone()
    deposit = _get_expected_deposit()

    return (
        f"Parfait !\n"
        f"J'aurais besoin d'un dépôt de validation de {deposit} via Wave au {payment_phone} "
        f"pour valider votre commande ; une fois fait envoyez-moi une capture svp 📸"
    )


def template_zone_recue(
    cart_items: List[Dict[str, Any]],
    zone_name: str,
    delivery_fee: int,
    subtotal: Optional[int] = None,
    total: Optional[int] = None,
    phone_current: Optional[str] = None,
    paiement_status: Optional[str] = None,
) -> str:
    """Template quand le client envoie sa zone.
    
    Scalable — aucun nom de produit hardcodé.
    Vérifie order_state pour ne jamais redemander une info déjà collectée.
    """
    fee_str = _format_price(delivery_fee)
    _paid = bool(paiement_status and ("valid" in str(paiement_status).lower() or "reçu" in str(paiement_status).lower()))

    if not phone_current:
        if _paid:
            return f"Noté ✅ la livraison à {zone_name} est de {fee_str}.\nSur quel numéro peut-on vous joindre ?"
        return f"Noté ✅ la livraison à {zone_name} est de {fee_str}.\nSur quel numéro peut-on vous joindre ?"

    # Zone + Numéro + Paiement déjà OK → simple confirmation
    if _paid:
        return f"Noté ✅ la livraison à {zone_name} est de {fee_str}. Tout est en ordre !"

    # Zone + Numéro OK, paiement manquant → demander paiement
    payment_phone = _get_payment_phone()
    deposit = _get_expected_deposit()

    return (
        f"Noté ✅ la livraison à {zone_name} est de {fee_str}.\n"
        f"J'aurais besoin d'un dépôt de validation de {deposit} via Wave au {payment_phone} "
        f"pour valider votre commande ; une fois fait envoyez-moi une capture svp 📸"
    )


def template_capture_recue() -> str:
    """Template quand le client envoie une capture de paiement."""
    return "Capture bien reçue ✅ Vérification en cours, vous serez contacté sous peu !"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN: CHECK SHORT-CIRCUIT
# ═══════════════════════════════════════════════════════════════════════════════

def check_short_circuit(
    message: str,
    user_id: str,
    company_id: Optional[str] = None,
    cart_manager: Any = None,
    order_tracker: Any = None,
    has_image: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Vérifie si le message peut être traité sans appel LLM.

    Returns:
        Dict avec {response, search_method, context_used} si short-circuit,
        None si le message doit passer au LLM.
    """
    raw = str(message or "").strip()
    if not raw and not has_image:
        return None

    # ── GARDE-FOU 1: Questions → toujours LLM ──
    if is_question(raw):
        logger.info("🚫 [SHORT_CIRCUIT] question detected → LLM")
        return None

    # ── GARDE-FOU 2: Message trop long → toujours LLM ──
    word_count = len(raw.split())
    if word_count > 40:
        logger.info("🚫 [SHORT_CIRCUIT] message too long (%d words) → LLM", word_count)
        return None

    # ── GARDE-FOU 3: Mention produit/variant → toujours LLM ──
    if _message_mentions_product(raw, company_id):
        logger.info("🚫 [SHORT_CIRCUIT] product keyword detected → LLM")
        return None

    # ── GARDE-FOU 4: Cart vide → toujours LLM ──
    cart_items: List[Dict[str, Any]] = []
    if cart_manager:
        try:
            cart_data = cart_manager.get_cart(user_id)
            cart_items = cart_data.get("items", []) if isinstance(cart_data, dict) else []
        except Exception:
            pass
    if not cart_items:
        logger.info("🚫 [SHORT_CIRCUIT] empty cart → LLM")
        return None

    # ── Lire l'état courant ──
    st = None
    zone_current = ""
    phone_current = ""
    paiement_current = ""
    if order_tracker:
        try:
            st = order_tracker.get_state(user_id)
            zone_current = str(getattr(st, "zone", "") or "").strip()
            phone_current = str(getattr(st, "telephone", "") or "").strip()
            paiement_current = str(getattr(st, "paiement", "") or "").strip()
        except Exception:
            pass

    # ── Récupérer le dernier prix calculé ──
    last_total: Optional[int] = None
    last_subtotal: Optional[int] = None
    last_delivery_fee: Optional[int] = None
    last_zone: Optional[str] = None
    if order_tracker:
        try:
            snap = order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None)
            if isinstance(snap, dict):
                last_total = snap.get("total")
                last_subtotal = snap.get("product_subtotal")
                last_delivery_fee = snap.get("delivery_fee")
                last_zone = snap.get("zone")
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # CAS A: IMAGE → JAMAIS short-circuit
    # Les images DOIVENT passer par Gemini Vision pour vérification paiement
    # (montant, destinataire Wave, PAYMENT_VERDICT). Ne pas bypasser.
    # ═══════════════════════════════════════════════════════════════════════
    if has_image:
        logger.info("🚫 [SHORT_CIRCUIT] image detected → LLM (Gemini Vision required)")
        return None

    # ═══════════════════════════════════════════════════════════════════════
    # EXTRACTION PARALLÈLE: PHONE + ZONE depuis le même message
    # Ex: "angre 0160924560" → phone=0160924560, zone=Angré
    # ═══════════════════════════════════════════════════════════════════════
    phone_found, text_after_phone = _extract_phone_from_text(raw)
    zone_info_found = None
    zone_name_found = None
    delivery_fee_found = None

    # Chercher une zone dans le texte restant (après extraction du numéro)
    text_for_zone = text_after_phone if phone_found else raw
    if not zone_current and word_count <= 8:
        zone_info_found = _extract_zone_simple(text_for_zone)
        if zone_info_found and zone_info_found.get("cost"):
            zone_name_found = zone_info_found.get("name", text_for_zone)
            delivery_fee_found = int(zone_info_found["cost"])

    # Si pas trouvé via inline, essayer full-match phone (cas simple: juste un numéro)
    if not phone_found:
        phone_found = _extract_phone(raw)

    # ── Persister ce qu'on a trouvé ──
    if phone_found and order_tracker:
        try:
            order_tracker.update_telephone(user_id, phone_found, source="SHORT_CIRCUIT", confidence=0.95)
        except Exception:
            pass

    if zone_name_found and order_tracker:
        try:
            order_tracker.update_zone(user_id, zone_name_found, source="SHORT_CIRCUIT", confidence=0.95)
        except Exception:
            pass

    # Calculer le total si on a zone + prix produit
    total_calc = None
    fee_for_template = delivery_fee_found or last_delivery_fee
    if zone_name_found and delivery_fee_found:
        if last_subtotal:
            total_calc = last_subtotal + delivery_fee_found
        elif last_total and last_delivery_fee:
            total_calc = (last_total - last_delivery_fee) + delivery_fee_found

    # ═══════════════════════════════════════════════════════════════════════
    # CAS B+C COMBO: PHONE + ZONE ensemble
    # ═══════════════════════════════════════════════════════════════════════
    if phone_found and zone_name_found:
        effective_zone = zone_name_found
        effective_phone = phone_found
        resp = template_zone_recue(
            cart_items=cart_items,
            zone_name=effective_zone,
            delivery_fee=delivery_fee_found,
            subtotal=last_subtotal,
            total=total_calc,
            phone_current=effective_phone,
            paiement_status=paiement_current,
        )
        logger.info("⚡ [SHORT_CIRCUIT] zone+phone combo: zone=%s phone=%s → Python", effective_zone, effective_phone[:4] + "****")
        return {
            "response": resp,
            "search_method": "python_short_circuit",
            "context_used": "zone_phone_combo",
            "sc_type": "ZONE_PHONE",
        }

    # ═══════════════════════════════════════════════════════════════════════
    # CAS B: NUMÉRO DE TÉLÉPHONE seul
    # ═══════════════════════════════════════════════════════════════════════
    if phone_found:
        resp = template_numero_recu(
            cart_items=cart_items,
            phone=phone_found,
            zone=last_zone or zone_current or None,
            delivery_fee=last_delivery_fee,
            total=last_total,
            paiement_status=paiement_current,
        )
        logger.info("⚡ [SHORT_CIRCUIT] phone=%s → Python", phone_found[:4] + "****")
        return {
            "response": resp,
            "search_method": "python_short_circuit",
            "context_used": "phone_received",
            "sc_type": "PHONE",
        }

    # ═══════════════════════════════════════════════════════════════════════
    # CAS C: ZONE DE LIVRAISON seule
    # ═══════════════════════════════════════════════════════════════════════
    if zone_name_found:
        resp = template_zone_recue(
            cart_items=cart_items,
            zone_name=zone_name_found,
            delivery_fee=delivery_fee_found,
            subtotal=last_subtotal,
            total=total_calc,
            phone_current=phone_current or None,
            paiement_status=paiement_current,
        )
        logger.info("⚡ [SHORT_CIRCUIT] zone=%s fee=%d → Python", zone_name_found, delivery_fee_found)
        return {
            "response": resp,
            "search_method": "python_short_circuit",
            "context_used": "zone_received",
            "sc_type": "ZONE",
        }

    # Pas de short-circuit possible
    return None
