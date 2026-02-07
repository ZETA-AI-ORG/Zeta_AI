"""
Tests de non-régression pour CartManager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Couvre:
  - Multi-item add / merge qty
  - Pivot freeze (CLARIFY_PIVOT → pending_pivot)
  - Resolve pending pivot (A=add, B=replace)
  - Delete item
  - Update item
  - Replace cart
  - upsert_from_items_json avec toutes les actions
  - Cart summary pour injection prompt
  - Fallback mémoire (pas de Redis)
"""

import os
import sys
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force memory fallback (no Redis dependency for tests)
os.environ["REDIS_URL"] = "redis://localhost:1/0"  # intentionally wrong port

from core.cart_manager import CartManager


@pytest.fixture
def cm():
    """CartManager instance with memory fallback."""
    mgr = CartManager(ttl_seconds=100)
    mgr._redis = None  # force memory mode
    return mgr


USER = "test_user_001"


# ───────────────────────────────────────────────
# 1. Basic add / merge
# ───────────────────────────────────────────────

def test_add_single_item(cm):
    item = {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1}
    cm.add_item(USER, item)
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Culotte"
    assert items[0]["qty"] == 1


def test_add_duplicate_merges_qty(cm):
    item = {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 2}
    cm.add_item(USER, item)
    cm.add_item(USER, dict(item))  # same signature
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["qty"] == 4  # 2 + 2


def test_add_different_items(cm):
    item1 = {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1}
    item2 = {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 2}
    cm.add_item(USER, item1)
    cm.add_item(USER, item2)
    items = cm.get_items(USER)
    assert len(items) == 2
    variants = {it["variant"] for it in items}
    assert variants == {"Culotte", "Pression"}


# ───────────────────────────────────────────────
# 2. Pivot freeze / pending pivot
# ───────────────────────────────────────────────

def test_set_pending_pivot(cm):
    # Pre-existing item
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})

    # Client changes to Pression → CLARIFY_PIVOT
    pending = {"product_id": "prod_abc", "variant": "Pression", "spec": "T5", "unit": "lot_300", "qty": 1}
    cm.set_pending_pivot(USER, pending)

    assert cm.has_pending_pivot(USER)
    pp = cm.get_pending_pivot(USER)
    assert pp["item"]["variant"] == "Pression"
    assert pp["awaiting_action"] == "A_or_B"

    # Cart items unchanged (freeze)
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Culotte"


def test_resolve_pivot_add(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.set_pending_pivot(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T5", "unit": "lot_300", "qty": 1})

    cm.resolve_pending_pivot(USER, "ADD")

    assert not cm.has_pending_pivot(USER)
    items = cm.get_items(USER)
    assert len(items) == 2
    variants = {it["variant"] for it in items}
    assert variants == {"Culotte", "Pression"}


def test_resolve_pivot_replace(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.set_pending_pivot(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T5", "unit": "lot_300", "qty": 1})

    cm.resolve_pending_pivot(USER, "REPLACE")

    assert not cm.has_pending_pivot(USER)
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Pression"


def test_resolve_pivot_alias_a_b(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.set_pending_pivot(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 1})

    # "A" = ADD
    cm.resolve_pending_pivot(USER, "A")
    items = cm.get_items(USER)
    assert len(items) == 2


# ───────────────────────────────────────────────
# 3. Delete item
# ───────────────────────────────────────────────

def test_delete_item(cm):
    item1 = {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1}
    item2 = {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 2}
    cm.add_item(USER, item1)
    cm.add_item(USER, item2)
    assert len(cm.get_items(USER)) == 2

    cm.delete_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150"})
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Pression"


# ───────────────────────────────────────────────
# 4. Update item
# ───────────────────────────────────────────────

def test_update_item_existing(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.update_item(USER, {"qty": 3, "unit": "lot_300"})

    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["qty"] == 3
    assert items[0]["unit"] == "lot_300"
    assert items[0]["variant"] == "Culotte"  # unchanged


def test_update_item_empty_cart(cm):
    cm.update_item(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 1})
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Pression"


# ───────────────────────────────────────────────
# 5. Replace cart
# ───────────────────────────────────────────────

def test_replace_cart(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 2})
    assert len(cm.get_items(USER)) == 2

    cm.replace_cart(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T6", "unit": "paquet_50", "qty": 5})
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["spec"] == "T6"
    assert items[0]["qty"] == 5


# ───────────────────────────────────────────────
# 6. upsert_from_items_json
# ───────────────────────────────────────────────

def test_upsert_none_action(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.upsert_from_items_json(USER, [{"product_id": "prod_abc", "variant": "Pression"}], action="NONE")
    assert len(cm.get_items(USER)) == 1  # no change


def test_upsert_add_action(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.upsert_from_items_json(USER, [{"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 1}], action="ADD")
    assert len(cm.get_items(USER)) == 2


def test_upsert_replace_action(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.upsert_from_items_json(USER, [{"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 3}], action="REPLACE")
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Pression"


def test_upsert_update_action(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.upsert_from_items_json(USER, [{"qty": 5, "unit": "lot_300"}], action="UPDATE")
    items = cm.get_items(USER)
    assert items[0]["qty"] == 5


def test_upsert_delete_action(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 2})
    cm.upsert_from_items_json(USER, [{"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150"}], action="DELETE")
    items = cm.get_items(USER)
    assert len(items) == 1
    assert items[0]["variant"] == "Pression"


def test_upsert_clarify_pivot_action(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.upsert_from_items_json(USER, [{"product_id": "prod_abc", "variant": "Pression", "spec": "T5", "unit": "lot_300", "qty": 1}], action="CLARIFY_PIVOT")

    assert cm.has_pending_pivot(USER)
    assert len(cm.get_items(USER)) == 1  # original unchanged
    assert cm.get_pending_pivot(USER)["item"]["variant"] == "Pression"


# ───────────────────────────────────────────────
# 7. Cart summary
# ───────────────────────────────────────────────

def test_cart_summary_empty(cm):
    assert cm.get_cart_summary(USER) == ""


def test_cart_summary_single_item(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 2})
    summary = cm.get_cart_summary(USER)
    assert "Culotte" in summary
    assert "T4" in summary
    assert "x2" in summary


def test_cart_summary_with_pending(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.set_pending_pivot(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T5"})
    summary = cm.get_cart_summary(USER)
    assert "EN ATTENTE" in summary
    assert "Pression" in summary


# ───────────────────────────────────────────────
# 8. Clear cart
# ───────────────────────────────────────────────

def test_clear_cart(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    assert len(cm.get_items(USER)) == 1
    cm.clear_cart(USER)
    assert len(cm.get_items(USER)) == 0


# ───────────────────────────────────────────────
# 9. Edge cases
# ───────────────────────────────────────────────

def test_resolve_no_pending(cm):
    """resolve_pending_pivot sans pending ne plante pas."""
    cart = cm.resolve_pending_pivot(USER, "ADD")
    assert cart["items"] == []


def test_upsert_empty_items(cm):
    """upsert avec items vide ne plante pas."""
    cart = cm.upsert_from_items_json(USER, [], action="ADD")
    assert cart["items"] == []


def test_items_count(cm):
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Culotte", "spec": "T4", "unit": "lot_150", "qty": 1})
    cm.add_item(USER, {"product_id": "prod_abc", "variant": "Pression", "spec": "T2", "unit": "lot_300", "qty": 2})
    assert cm.get_items_count(USER) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
