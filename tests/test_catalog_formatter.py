"""Test catalog_formatter.py with real vtree data."""
from core.catalog_formatter import format_price_list

vtree = {
    "Culotte": {
        "s": {
            "T3": {"u": {"lot_150": [13500, 500], "lot_300": [24000, 500], "paquet_50": [5500, 500]}},
            "T4": {"u": {"lot_150": [13500, 500], "lot_300": [24000, 500], "paquet_50": [5500, 500]}},
            "T5": {"u": {"lot_150": [13500, 500], "lot_300": [24000, 500], "paquet_50": [5500, 500]}},
            "T6": {"u": {"lot_150": [13500, 500], "lot_300": [24000, 500], "paquet_50": [5500, 500]}},
        }
    },
    "Pression": {
        "s": {
            "T1": {"u": {"lot_300": [17000, 500]}},
            "T2": {"u": {"lot_300": [18500, 500]}},
            "T3": {"u": {"lot_300": [20500, 500]}},
            "T4": {"u": {"lot_300": [22500, 500]}},
            "T5": {"u": {"lot_300": [24000, 500]}},
            "T6": {"u": {"lot_300": [24500, 500]}},
        }
    },
}

pid = "prod_ml6dxg73_a0rloi"
cf = [
    {"type": "paquet", "quantity": "50", "unitLabel": "pieces"},
    {"type": "lot", "quantity": "150", "unitLabel": "pieces"},
    {"type": "lot", "quantity": "300", "unitLabel": "pieces"},
]


def test_case1_unit_known_spec_missing():
    """Case 1: 'paquet de 50 culottes' → show specs only."""
    text, items = format_price_list(
        product_id=pid, variant_key="Culotte", variant_node=vtree["Culotte"],
        detected_spec=None, detected_unit="paquet_50", custom_formats=cf,
    )
    print("=" * 60)
    print("CASE 1: Culotte + unit=paquet_50, spec=null")
    print("=" * 60)
    print(text)
    print(f"Items: {len(items)}")
    assert len(items) == 4, f"Expected 4 items, got {len(items)}"
    assert all(it["unit"] == "paquet_50" for it in items), "All items should have unit=paquet_50"
    assert all(it["spec"] is not None for it in items), "All items should have a spec"
    print("PASS\n")


def test_case2_spec_known_unit_missing():
    """Case 2: 'culottes T5' → show units only."""
    text, items = format_price_list(
        product_id=pid, variant_key="Culotte", variant_node=vtree["Culotte"],
        detected_spec="T5", detected_unit=None, custom_formats=cf,
    )
    print("=" * 60)
    print("CASE 2: Culotte + spec=T5, unit=null")
    print("=" * 60)
    print(text)
    print(f"Items: {len(items)}")
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    assert all(it["spec"] == "T5" for it in items), "All items should have spec=T5"
    print("PASS\n")


def test_case3a_both_missing_same_price():
    """Case 3a: 'culottes' → SAME_PRICE_PER_UNIT compact format."""
    text, items = format_price_list(
        product_id=pid, variant_key="Culotte", variant_node=vtree["Culotte"],
        detected_spec=None, detected_unit=None, custom_formats=cf,
    )
    print("=" * 60)
    print("CASE 3a: Culotte + both null (SAME_PRICE_PER_UNIT)")
    print("=" * 60)
    print(text)
    print(f"Items: {len(items)}")
    assert len(items) == 3, f"Expected 3 format items, got {len(items)}"
    assert "taille" in text.lower() or "Tailles" in text, "Should mention tailles"
    print("PASS\n")


def test_case3b_both_missing_unique_unit():
    """Case 3b: 'pression' → UNIQUE_UNIT numbered spec list."""
    text, items = format_price_list(
        product_id=pid, variant_key="Pression", variant_node=vtree["Pression"],
        detected_spec=None, detected_unit=None, custom_formats=cf,
    )
    print("=" * 60)
    print("CASE 3b: Pression + both null (UNIQUE_UNIT)")
    print("=" * 60)
    print(text)
    print(f"Items: {len(items)}")
    assert len(items) == 6, f"Expected 6 items, got {len(items)}"
    assert "uniquement" in text.lower(), "Should mention unit in header"
    print("PASS\n")


def test_case4_both_known():
    """Case 4: 'paquet de 50 T5' → empty (caller confirms)."""
    text, items = format_price_list(
        product_id=pid, variant_key="Culotte", variant_node=vtree["Culotte"],
        detected_spec="T5", detected_unit="paquet_50", custom_formats=cf,
    )
    print("=" * 60)
    print("CASE 4: Culotte + both known → empty")
    print("=" * 60)
    print(f'Text: "{text}"')
    print(f"Items: {len(items)}")
    assert text == "", "Should be empty when both known"
    assert items == [], "Should be empty when both known"
    print("PASS\n")


def test_auto_fill_pression_unit():
    """Pression has only lot_300 → auto-fill unit."""
    from core.catalog_formatter import auto_fill_single_options
    af = auto_fill_single_options(
        variant_node=vtree["Pression"],
        detected_spec=None, detected_unit=None,
    )
    print("=" * 60)
    print("AUTO-FILL: Pression (only lot_300)")
    print("=" * 60)
    print(f"filled_unit={af['filled_unit']} filled_spec={af['filled_spec']} reason={af['reason']}")
    assert af["filled_unit"] == "lot_300", f"Expected lot_300, got {af['filled_unit']}"
    assert af["filled_spec"] is None, "Pression has 6 specs, should NOT auto-fill"
    print("PASS\n")


def test_auto_fill_culotte_nothing():
    """Culotte has 3 units × 4 specs → NO auto-fill."""
    from core.catalog_formatter import auto_fill_single_options
    af = auto_fill_single_options(
        variant_node=vtree["Culotte"],
        detected_spec=None, detected_unit=None,
    )
    print("=" * 60)
    print("AUTO-FILL: Culotte (multiple units+specs)")
    print("=" * 60)
    print(f"filled_unit={af['filled_unit']} filled_spec={af['filled_spec']}")
    assert af["filled_unit"] is None, "Culotte has 3 units, should NOT auto-fill"
    assert af["filled_spec"] is None, "Culotte has 4 specs, should NOT auto-fill"
    print("PASS\n")


if __name__ == "__main__":
    test_case1_unit_known_spec_missing()
    test_case2_spec_known_unit_missing()
    test_case3a_both_missing_same_price()
    test_case3b_both_missing_unique_unit()
    test_case4_both_known()
    test_auto_fill_pression_unit()
    test_auto_fill_culotte_nothing()
    print("ALL TESTS PASSED!")
