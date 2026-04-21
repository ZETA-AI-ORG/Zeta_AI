"""
🏪 Boutique Block Builder — génère dynamiquement la section "BOUTIQUE"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Centralise la logique de construction du bloc "BOUTIQUE" injecté dans les
prompts Amanda et Jessica, selon `boutique_type` (online|physique|hybride).

Source des données : `company_rag_configs` (col `boutique_type` + `rag_behavior`).

Placeholders concernés (dans les templates) :
    {boutique_block}   → remplacé par le bloc markdown complet

Utilisation :
    from core.boutique_block import build_boutique_block
    block = build_boutique_block(company_info)
    prompt = prompt.replace("{boutique_block}", block)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# ─── Blocs par défaut ────────────────────────────────────────────────────────

_BLOCK_ONLINE_DEFAULT = (
    "Type : Exclusivement en ligne. Aucune visite en magasin possible.\n"
    "Service : Livraison (Abidjan) ou Expédition (Intérieur du pays) uniquement."
)


def _normalize_type(boutique_type: Optional[str]) -> str:
    """Normalise le champ boutique_type. Valeurs reconnues :
    - online / en_ligne / ecommerce → "online"
    - physical / physique / store → "physical"
    - hybrid / hybride / mixte → "hybrid"
    Défaut : "online" (plus conservateur).
    """
    t = str(boutique_type or "").strip().lower()
    if t in {"physical", "physique", "store", "magasin", "boutique_physique"}:
        return "physical"
    if t in {"hybrid", "hybride", "mixte", "both"}:
        return "hybrid"
    return "online"


def _fmt_list(prefix: str, items) -> str:
    """Formate une ligne 'prefix : a, b, c' si items non vide."""
    if not items:
        return ""
    if isinstance(items, str):
        val = items.strip()
    elif isinstance(items, (list, tuple)):
        val = ", ".join(str(x).strip() for x in items if str(x).strip())
    else:
        val = str(items).strip()
    if not val:
        return ""
    return f"{prefix} : {val}"


def build_boutique_block(company_info: Optional[Dict[str, Any]]) -> str:
    """Construit le bloc markdown décrivant la boutique.

    Structure attendue dans `company_info.rag_behavior` pour un marchand physique :
        {
          "boutique": {
            "address": "123 rue des Lys, Abidjan",
            "commune": "Cocody",
            "quartier": "Angré 7e",
            "hours": "Lun-Sam 9h-19h",
            "landmarks": ["face au CNPS", "arrêt bus 33"],
            "phone_store": "+225 01 02 03 04 05"
          }
        }

    Args:
        company_info: dict renvoyé par BotlivePromptsManager.get_company_info()

    Returns:
        str: bloc markdown prêt à injecter via `{boutique_block}`
    """
    info = company_info or {}
    btype = _normalize_type(info.get("boutique_type"))
    rag = info.get("rag_behavior") or {}
    boutique = (rag.get("boutique") or {}) if isinstance(rag, dict) else {}

    # 🛒 100 % en ligne → bloc hardcodé historique
    if btype == "online":
        return _BLOCK_ONLINE_DEFAULT

    # 🏬 Physique ou hybride → on récupère tout ce qui est disponible
    address = str(boutique.get("address") or "").strip()
    commune = str(boutique.get("commune") or "").strip()
    quartier = str(boutique.get("quartier") or "").strip()
    hours = str(boutique.get("hours") or boutique.get("horaires") or "").strip()
    landmarks = boutique.get("landmarks") or boutique.get("reperes") or []
    phone_store = str(boutique.get("phone_store") or boutique.get("phone") or "").strip()

    # Construction dynamique (on n'imprime que ce qu'on a)
    location_parts = []
    if address:
        location_parts.append(address)
    elif commune or quartier:
        loc = " ".join(x for x in [commune, quartier] if x)
        if loc:
            location_parts.append(loc)

    lines: list[str] = []
    if btype == "physical":
        lines.append("Type : Boutique physique. Visite en magasin possible.")
    else:  # hybrid
        lines.append("Type : Boutique physique ET en ligne (hybride).")
        lines.append("Service : Visite en magasin OU Livraison/Expédition.")

    if location_parts:
        lines.append(f"Adresse : {location_parts[0]}")
    if hours:
        lines.append(f"Horaires : {hours}")
    if landmarks:
        lm = _fmt_list("Repères", landmarks)
        if lm:
            lines.append(lm)
    if phone_store:
        lines.append(f"Téléphone boutique : {phone_store}")

    # Si hybride mais aucune donnée physique remplie → retomber sur online
    if btype == "hybrid" and not any([address, commune, quartier, hours]):
        return _BLOCK_ONLINE_DEFAULT

    # Si physique mais aucune adresse → retomber sur online (sécurité)
    if btype == "physical" and not location_parts:
        return _BLOCK_ONLINE_DEFAULT

    return "\n".join(lines)
