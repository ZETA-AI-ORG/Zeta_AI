"""
🎭 Amanda Prompt Loader - Système dédié de précommande Live
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Charge le template Amanda via `prompt_bots_loader` (Supabase → Redis → local)
et injecte les variables entreprise. Prompt 100% stable (cache prefix maximal).

Architecture :
    Supabase table `prompt_bots` (bot_type="amanda")
        ↓ cache Redis 1h (key: zeta:prompt_bots:amanda)
        ↓ fallback in-memory
        ↓ fallback fichier AMANDA PROMPT UNIVERSEL.md
    ↓
    Injection variables entreprise (shop_name, wave_number, ...)
    ↓
    Prompt final prêt pour LLM

Usage:
    from core.amanda_prompt_loader import load_amanda_prompt
    prompt = load_amanda_prompt(company_id="abc123")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import logging
from typing import Dict, Any, Optional

from core.prompt_bots_loader import get_prompt_template, invalidate_cache

logger = logging.getLogger(__name__)

_BOT_TYPE = "amanda"


def _load_template() -> str:
    """Charge le template Amanda (Supabase → Redis → in-memory → fichier local)."""
    template = get_prompt_template(_BOT_TYPE)
    if not template:
        logger.error(f"❌ [AMANDA] Aucun template disponible (tous fallbacks échoués)")
    return template


async def load_amanda_prompt(
    company_id: str,
    company_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Charge le prompt Amanda et injecte les variables entreprise.

    Args:
        company_id: ID Supabase de l'entreprise
        company_info: Dict optionnel avec infos pré-chargées (évite appel Supabase)

    Returns:
        Prompt Amanda prêt à envoyer au LLM (variables injectées)
    """
    template = _load_template()
    if not template:
        return ""

    # Récupérer infos entreprise si non fournies
    if company_info is None:
        try:
            from core.botlive_prompts_supabase import get_prompts_manager
            manager = get_prompts_manager()
            if manager:
                company_info = await manager.get_company_info(company_id) or {}
            else:
                company_info = {}
        except Exception as e:
            logger.warning(f"⚠️ [AMANDA] Impossible de charger company_info: {e}")
            company_info = {}

    # ════════════════════════════════════════════════════════════════════════
    # Variables à injecter dans le prompt Amanda
    # IMPORTANT: Amanda ne BLOQUE jamais sur paiement (facultatif côté live).
    # Toutes STATIQUES par company → cache prefix OK.
    # Section BOUTIQUE générée dynamiquement via core.boutique_block selon
    # le champ `boutique_type` (online / physical / hybrid).
    # ════════════════════════════════════════════════════════════════════════
    info = company_info or {}
    # 🛡️ GARDE-FOU : rag_behavior peut être une string legacy ("always", "never"…)
    # dans certaines bases pas encore migrées → on le force en dict pour éviter
    # 'str' object has no attribute 'get'.
    raw_rag = info.get("rag_behavior") if isinstance(info, dict) else None
    rag = raw_rag if isinstance(raw_rag, dict) else {}
    payment = rag.get("payment") if isinstance(rag.get("payment"), dict) else {}
    support = rag.get("support") if isinstance(rag.get("support"), dict) else {}

    shop_name = (
        info.get("company_name")
        or info.get("shop_name")
        or "la boutique"
    )

    # Wave — uniquement pour AFFICHAGE (numéro où le client PEUT déposer s'il veut).
    # Amanda ne demande JAMAIS de montant précis : elle ne connaît pas les prix articles.
    wave_number = (
        payment.get("wave_number")
        or info.get("whatsapp_phone")
        or "à demander"
    )

    # WhatsApp support
    whatsapp_number = (
        support.get("whatsapp")
        or info.get("whatsapp_phone")
        or info.get("whatsapp_number")
        or ""
    )

    # SAV / Horaires / Politique retour / Délais (présents dans le template Amanda)
    sav_number = (
        support.get("sav_number")
        or support.get("phone")
        or whatsapp_number
        or ""
    )
    support_hours = rag.get("support_hours") or "08:00 - 20:00"
    return_policy = rag.get("return_policy") or "Échange possible sous 48h (voir conditions)"
    delai_message = rag.get("delai_message") or ""

    # 🏪 Section BOUTIQUE dynamique selon boutique_type
    try:
        from core.boutique_block import build_boutique_block
        boutique_block = build_boutique_block(info)
    except Exception as blk_err:
        logger.warning(f"⚠️ [AMANDA] Fallback boutique_block: {blk_err}")
        boutique_block = (
            "Type : Exclusivement en ligne. Aucune visite en magasin possible.\n"
            "Service : Livraison (Abidjan) ou Expédition (Intérieur du pays) uniquement."
        )

    variables = {
        "shop_name": shop_name,
        "wave_number": wave_number,
        "whatsapp_number": whatsapp_number,
        "bot_name": "Amanda",
        "sav_number": sav_number,
        "support_hours": support_hours,
        "return_policy": return_policy,
        "delai_message": delai_message,
        "boutique_block": boutique_block,
    }

    # Remplacement simple {var}
    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{key}}}", str(value or ""))

    logger.info(
        f"✅ [AMANDA] Prompt prêt pour company={company_id} "
        f"(shop={shop_name}, boutique_type={info.get('boutique_type') or 'online'}, "
        f"wave={wave_number}, sav={sav_number or '∅'}, {len(prompt)} chars)"
    )
    return prompt


def clear_amanda_cache() -> bool:
    """Invalide le cache Amanda (Redis + in-memory). Utile pour tests/dev/resync."""
    ok = invalidate_cache(_BOT_TYPE)
    logger.info(f"🗑️ [AMANDA] Cache invalidé (success={ok})")
    return ok
