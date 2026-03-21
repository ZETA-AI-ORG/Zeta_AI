"""
🛒 CART MANAGER — Panier multi-produits avec persistance Redis 72h
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Clé Redis : cart:{user_id}
- TTL : 72h (259 200 s)
- Structure : { items[], pending_pivot, meta }
- Fallback mémoire si Redis indisponible
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("cart_manager")

# ──────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────
_DEFAULT_TTL = 259_200  # 72h


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_cart(user_id: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "items": [],
        "pending_pivot": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _item_signature(item: Dict[str, Any]) -> str:
    """Clé unique d'un item pour dédoublonnage (product_id + variant + spec + unit)."""
    pid = str(item.get("product_id") or "").strip().lower()
    var = str(item.get("variant") or "").strip().lower()
    spec = str(item.get("spec") or item.get("specs") or "").strip().lower()
    unit = str(item.get("unit") or "").strip().lower()
    return f"{pid}|{var}|{spec}|{unit}"


class CartManager:
    """Gestionnaire de panier multi-produits avec Redis (ou fallback mémoire)."""

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL):
        self.ttl = ttl_seconds
        self._redis = None
        self._memory: Dict[str, Dict[str, Any]] = {}  # fallback
        self._init_redis()

    # ── Redis bootstrap ──────────────────────────
    def _init_redis(self):
        try:
            import redis as _redis_mod
            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = _redis_mod.Redis.from_url(url, decode_responses=True)
            self._redis.ping()
            logger.info("✅ [CartManager] Redis connected (%s)", url)
        except Exception as exc:
            logger.warning("⚠️ [CartManager] Redis unavailable (%s) — using in-memory fallback", exc)
            self._redis = None

    def _redis_ok(self) -> bool:
        if self._redis is None:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            self._redis = None
            return False

    # ── Persistence layer ────────────────────────
    def _key(self, user_id: str) -> str:
        return f"cart:{user_id}"

    def _load(self, user_id: str) -> Dict[str, Any]:
        if self._redis_ok():
            try:
                raw = self._redis.get(self._key(user_id))
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                logger.warning("⚠️ [CartManager] Redis GET error: %s", exc)
        else:
            cart = self._memory.get(user_id)
            if cart:
                return cart
        return _empty_cart(user_id)

    def _save(self, user_id: str, cart: Dict[str, Any]):
        cart["updated_at"] = _now_iso()
        if self._redis_ok():
            try:
                self._redis.setex(
                    self._key(user_id),
                    self.ttl,
                    json.dumps(cart, ensure_ascii=False),
                )
            except Exception as exc:
                logger.warning("⚠️ [CartManager] Redis SET error: %s", exc)
                self._memory[user_id] = cart
        else:
            self._memory[user_id] = cart

    # ── Public API ───────────────────────────────

    def get_cart(self, user_id: str) -> Dict[str, Any]:
        """Retourne le panier complet (ou un panier vide)."""
        return self._load(user_id)

    def get_items(self, user_id: str) -> List[Dict[str, Any]]:
        return self.get_cart(user_id).get("items", [])

    # ── Item operations ──────────────────────────

    def add_item(self, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Ajoute un item. Si même signature existe, incrémente qty."""
        cart = self._load(user_id)
        sig = _item_signature(item)
        for existing in cart["items"]:
            if _item_signature(existing) == sig:
                old_qty = int(existing.get("qty") or 0)
                add_qty = int(item.get("qty") or 1)
                existing["qty"] = old_qty + add_qty
                logger.info("➕ [CartManager] qty merged: %s → qty=%d", sig, existing["qty"])
                self._save(user_id, cart)
                return cart
        item.setdefault("added_at", _now_iso())
        cart["items"].append(item)
        logger.info("➕ [CartManager] item added: %s", sig)
        self._save(user_id, cart)
        return cart

    def update_item(self, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour le dernier item (ou ajoute si panier vide)."""
        cart = self._load(user_id)
        if not cart["items"]:
            item.setdefault("added_at", _now_iso())
            cart["items"].append(item)
        else:
            last = cart["items"][-1]
            last.update({k: v for k, v in item.items() if v is not None})
        logger.info("✏️ [CartManager] item updated")
        self._save(user_id, cart)
        return cart

    def replace_cart(self, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Remplace tout le panier par un seul item."""
        cart = self._load(user_id)
        item.setdefault("added_at", _now_iso())
        cart["items"] = [item]
        cart["pending_pivot"] = None
        logger.info("🔄 [CartManager] cart replaced")
        self._save(user_id, cart)
        return cart

    def delete_item(self, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Supprime un item par signature."""
        cart = self._load(user_id)
        sig = _item_signature(item)
        cart["items"] = [it for it in cart["items"] if _item_signature(it) != sig]
        logger.info("🗑️ [CartManager] item deleted: %s", sig)
        self._save(user_id, cart)
        return cart

    def clear_cart(self, user_id: str):
        """Vide entièrement le panier."""
        if self._redis_ok():
            try:
                self._redis.delete(self._key(user_id))
            except Exception:
                pass
        self._memory.pop(user_id, None)
        logger.info("🧹 [CartManager] cart cleared for %s", user_id[:12])

    # ── Pending pivot (CLARIFY_PIVOT) ────────────

    def set_pending_pivot(self, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Stocke un item en attente de clarification A/B (freeze le panier)."""
        cart = self._load(user_id)
        cart["pending_pivot"] = {
            "item": item,
            "awaiting_action": "A_or_B",
            "created_at": _now_iso(),
        }
        logger.info("🛑 [CartManager] pending_pivot set: %s", _item_signature(item))
        self._save(user_id, cart)
        return cart

    def get_pending_pivot(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retourne le pending_pivot ou None."""
        cart = self._load(user_id)
        return cart.get("pending_pivot")

    def resolve_pending_pivot(self, user_id: str, choice: str) -> Dict[str, Any]:
        """
        Résout le pending_pivot.
          choice='A' ou 'add'   → ajoute l'item au panier
          choice='B' ou 'modify' → remplace le panier
        """
        cart = self._load(user_id)
        pp = cart.get("pending_pivot")
        if not pp or not isinstance(pp, dict):
            return cart

        pending_item = pp.get("item") or {}
        pending_item.setdefault("added_at", _now_iso())

        c = str(choice or "").strip().upper()

        if c in ("A", "ADD"):
            cart["items"].append(pending_item)
            logger.info("✅ [CartManager] pivot resolved → ADD")
        elif c in ("B", "MODIFY", "REPLACE"):
            cart["items"] = [pending_item]
            logger.info("✅ [CartManager] pivot resolved → REPLACE")
        else:
            logger.warning("⚠️ [CartManager] resolve_pending_pivot unknown choice: %s", choice)

        cart["pending_pivot"] = None
        self._save(user_id, cart)
        return cart

    # ── Bulk upsert from LLM detected_items_json ─

    def upsert_from_items_json(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        action: str,
    ) -> Dict[str, Any]:
        """
        Met à jour le panier à partir du detected_items_json du LLM + <maj><action>.

        Actions supportées:
          NONE            → ne rien faire (info only)
          ADD             → ajouter les items
          REPLACE         → remplacer tout le panier
          UPDATE          → mettre à jour le dernier item
          DELETE          → supprimer les items matchant
          CLARIFY_PIVOT   → stocker en pending_pivot (1er item)
        """
        act = str(action or "").strip().upper()

        if not items or act in ("NONE", ""):
            return self._load(user_id)

        if act == "CLARIFY_PIVOT":
            return self.set_pending_pivot(user_id, items[0])

        if act == "ADD":
            cart = self._load(user_id)
            for item in items:
                self.add_item(user_id, item)
            return self._load(user_id)

        if act == "REPLACE":
            if len(items) == 1:
                return self.replace_cart(user_id, items[0])
            cart = self._load(user_id)
            cart["items"] = []
            for item in items:
                item.setdefault("added_at", _now_iso())
                cart["items"].append(item)
            cart["pending_pivot"] = None
            self._save(user_id, cart)
            return cart

        if act == "UPDATE":
            return self.update_item(user_id, items[0])

        if act == "DELETE":
            for item in items:
                self.delete_item(user_id, item)
            return self._load(user_id)

        logger.warning("⚠️ [CartManager] unknown action: %s", act)
        return self._load(user_id)

    # ── Summary for prompt injection ─────────────

    def get_cart_summary(self, user_id: str) -> str:
        """Résumé textuel du panier pour injection dans le prompt LLM."""
        cart = self._load(user_id)
        items = cart.get("items", [])

        if not items:
            return ""

        lines = []
        for i, item in enumerate(items, 1):
            variant = str(item.get("variant") or "").strip()
            spec = str(item.get("spec") or item.get("specs") or "").strip()
            unit = str(item.get("unit") or "").strip()
            qty = item.get("qty")
            label = (variant + (" " + spec if spec else "")).strip() or "?"
            qty_str = f"x{qty}" if qty else ""
            unit_str = unit if unit else ""
            lines.append(f"{i}. {label} {qty_str} {unit_str}".strip())

        summary = " | ".join(lines)

        pp = cart.get("pending_pivot")
        if pp and isinstance(pp, dict) and pp.get("item"):
            pi = pp["item"]
            pv = str(pi.get("variant") or "").strip()
            ps = str(pi.get("spec") or "").strip()
            plabel = (pv + (" " + ps if ps else "")).strip() or "?"
            summary += f" | ⏳ EN ATTENTE: {plabel} (ajout ou remplacement ?)"

        return summary

    def get_items_count(self, user_id: str) -> int:
        return len(self.get_items(user_id))

    def has_pending_pivot(self, user_id: str) -> bool:
        pp = self.get_pending_pivot(user_id)
        return bool(pp and isinstance(pp, dict) and pp.get("item"))

    # ── Deep-link generation ──────────────────────

    @staticmethod
    def get_catalogue_url(shop_slug: str) -> str:
        """Retourne l'URL publique du catalogue pour un shop_slug donné."""
        base = os.getenv("PUBLIC_SITE_URL", "https://zetaapp.xyz").rstrip("/")
        if shop_slug:
            return f"{base}/shop/{shop_slug}"
        return ""

    def create_cart_link(self, user_id: str, shop_slug: str) -> str:
        """
        Génère un lien profond vers le catalogue public avec le panier pré-rempli.
        Format: https://zetaapp.xyz/shop/{slug}?cart={base64_json}
        Retourne '' si le panier est vide ou le slug absent.
        """
        import base64 as _b64

        if not shop_slug:
            return ""

        items = self.get_items(user_id)
        if not items:
            return ""

        # Garder uniquement les champs utiles pour le lien (léger)
        compact = []
        for it in items:
            entry: Dict[str, Any] = {}
            for k in ("product_id", "variant", "spec", "specs", "unit", "qty"):
                v = it.get(k)
                if v is not None and str(v).strip():
                    entry[k] = v
            if entry:
                compact.append(entry)

        if not compact:
            return ""

        payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
        encoded = _b64.urlsafe_b64encode(payload.encode()).decode()
        base_url = self.get_catalogue_url(shop_slug)
        return f"{base_url}?cart={encoded}"
