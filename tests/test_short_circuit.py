"""
Tests unitaires pour le short-circuit engine.
Vérifie la détection de questions, numéros, zones, et les garde-fous.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.short_circuit_engine import (
    is_question,
    _extract_phone,
    _extract_zone_simple,
    _message_mentions_product,
    _normalize_for_detection,
    check_short_circuit,
)


def test_question_detection():
    """Test la détection de questions françaises."""
    print("\n═══ TEST: Détection de questions ═══")

    # DOIT être détecté comme question
    questions = [
        "C'est combien ?",
        "Vous livrez à Cocody ?",
        "Quel est le prix ?",
        "Combien ça coûte",
        "Est-ce que vous avez du T4 ?",
        "Comment ça marche",
        "Pourquoi c'est cher",
        "Quelle taille vous conseillez ?",
        "Y a-t-il du stock ?",
        "Où est-ce que je peux payer ?",
        "Avez-vous des culottes ?",
        "C'est quoi la différence",
        "Vous faites des réductions ?",
        "Je peux payer en 2 fois ?",
    ]

    # NE DOIT PAS être détecté comme question
    not_questions = [
        "0712345678",
        "Cocody",
        "Oui",
        "OK merci",
        "07 12 34 56 78",
        "Yopougon",
        "D'accord",
        "Validé",
        "Port-Bouët",
    ]

    passed = 0
    total = len(questions) + len(not_questions)

    for q in questions:
        result = is_question(q)
        status = "✅" if result else "❌"
        if result:
            passed += 1
        print(f"  {status} QUESTION: '{q}' → {result}")

    for nq in not_questions:
        result = is_question(nq)
        status = "✅" if not result else "❌"
        if not result:
            passed += 1
        print(f"  {status} NOT_Q:    '{nq}' → {result}")

    print(f"\n  Score: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed == total


def test_phone_detection():
    """Test la détection de numéros de téléphone CI."""
    print("\n═══ TEST: Détection numéros téléphone ═══")

    # DOIT matcher
    valid_phones = [
        ("0712345678", "0712345678"),
        ("07 12 34 56 78", "0712345678"),
        ("07-12-34-56-78", "0712345678"),
        ("+225 0712345678", "0712345678"),
        ("0505050505", "0505050505"),
        ("05 05 05 05 05", "0505050505"),
    ]

    # NE DOIT PAS matcher
    invalid = [
        "Cocody",
        "1234",
        "je veux 0712345678 pour ma soeur",
        "0712345678 c'est pour Cocody",
        "prix total",
        "T4",
    ]

    passed = 0
    total = len(valid_phones) + len(invalid)

    for raw, expected in valid_phones:
        result = _extract_phone(raw)
        ok = result == expected
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} '{raw}' → {result} (expected {expected})")

    for raw in invalid:
        result = _extract_phone(raw)
        ok = result is None
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} '{raw}' → {result} (expected None)")

    print(f"\n  Score: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed == total


def test_zone_detection():
    """Test la détection de zones simples."""
    print("\n═══ TEST: Détection zones ═══")

    # DOIT matcher
    valid_zones = [
        ("Cocody", "Cocody"),
        ("cocody", "Cocody"),
        ("Yopougon", "Yopougon"),
        ("à Abobo", "Abobo"),
        ("Port-Bouët", "Port-Bouët"),
        ("Marcory", "Marcory"),
    ]

    # NE DOIT PAS matcher (trop long ou pas une zone)
    invalid_zones = [
        "je veux être livré à Cocody demain matin s'il vous plaît",
        "Paris",
        "T4",
        "0712345678",
    ]

    passed = 0
    total = len(valid_zones) + len(invalid_zones)

    for raw, expected_name in valid_zones:
        result = _extract_zone_simple(raw)
        ok = result is not None and result.get("name") == expected_name
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        name = result.get("name") if result else None
        print(f"  {status} '{raw}' → {name} (expected {expected_name})")

    for raw in invalid_zones:
        result = _extract_zone_simple(raw)
        ok = result is None
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} '{raw}' → {result} (expected None)")

    print(f"\n  Score: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed == total


def test_product_mention_guard():
    """Test le garde-fou produit (scalable depuis catalogue)."""
    print("\n═══ TEST: Garde-fou mention produit ═══")

    # Messages qui mentionnent un produit/unité → DOIT bloquer le short-circuit
    product_messages = [
        "je veux des pression taille 4",
        "un lot de culotte",
        "3 paquets de T2",
        "carton de couches",
    ]

    # Messages simples → NE DOIT PAS bloquer
    simple_messages = [
        "0712345678",
        "Cocody",
        "Oui",
        "OK",
        "Merci",
    ]

    passed = 0
    total = len(product_messages) + len(simple_messages)

    for msg in product_messages:
        result = _message_mentions_product(msg, None)  # Sans company_id, teste les mots génériques
        ok = result is True
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} BLOCK: '{msg}' → mentions_product={result}")

    for msg in simple_messages:
        result = _message_mentions_product(msg, None)
        ok = result is False
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} PASS:  '{msg}' → mentions_product={result}")

    print(f"\n  Score: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed == total


def test_full_short_circuit():
    """Test intégration check_short_circuit avec un mock cart."""
    print("\n═══ TEST: check_short_circuit (intégration) ═══")

    class MockOrderTracker:
        def __init__(self):
            self._state = type("S", (), {
                "zone": "",
                "numero": "",
                "paiement": "",
            })()
            self._meta = {}

        def get_state(self, user_id):
            return self._state

        def get_custom_meta(self, user_id, key, default=None):
            return self._meta.get(key, default)

        def set_custom_meta(self, user_id, key, value):
            self._meta[key] = value

        def update_numero(self, user_id, phone, source="", confidence=0.0):
            self._state.numero = phone

        def update_zone(self, user_id, zone, source="", confidence=0.0):
            self._state.zone = zone

    class MockCartManager:
        def __init__(self, items=None):
            self._items = items or []

        def get_cart(self, user_id):
            return {"items": self._items}

    # Cart avec un item
    cart_with_item = MockCartManager(items=[
        {"product_id": "prod_test", "variant": "Pression", "spec": "T4", "unit": "lot_300", "qty": 1}
    ])
    cart_empty = MockCartManager(items=[])
    tracker = MockOrderTracker()
    tracker._meta["last_total_snapshot"] = {
        "total": 24000,
        "product_subtotal": 22500,
        "delivery_fee": 1500,
        "zone": "Cocody",
    }

    tests = [
        # (message, cart, has_image, expected_sc_type_or_none)
        ("0712345678", cart_with_item, False, "PHONE"),
        ("07 12 34 56 78", cart_with_item, False, "PHONE"),
        ("Cocody", cart_with_item, False, "ZONE"),  # zone_current is empty
        ("0712345678", cart_empty, False, None),  # cart vide → pas de SC
        ("C'est combien ?", cart_with_item, False, None),  # question → pas de SC
        ("je veux un lot de pression", cart_with_item, False, None),  # produit → pas de SC
        ("Oui", cart_with_item, False, None),  # pas de SC (pas phone/zone/image)
        ("Voici la capture", cart_with_item, True, None),  # image → JAMAIS SC (Gemini Vision requis)
    ]

    passed = 0
    total = len(tests)

    for msg, cart, has_img, expected in tests:
        # Reset tracker zone for zone test
        if expected == "ZONE":
            tracker._state.zone = ""
        else:
            tracker._state.zone = "Cocody"

        result = check_short_circuit(
            message=msg,
            user_id="test_user",
            company_id=None,
            cart_manager=cart,
            order_tracker=tracker,
            has_image=has_img,
        )
        actual = result.get("sc_type") if result else None
        ok = actual == expected
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"  {status} '{msg}' (cart={'full' if cart._items else 'empty'}) → {actual} (expected {expected})")
        if result and result.get("response"):
            # Print first line of response
            first_line = result["response"].split("\n")[0][:80]
            print(f"       Response: {first_line}...")

    print(f"\n  Score: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed == total


if __name__ == "__main__":
    print("🧪 SHORT-CIRCUIT ENGINE — Tests unitaires\n")

    results = []
    results.append(("Question detection", test_question_detection()))
    results.append(("Phone detection", test_phone_detection()))
    results.append(("Zone detection", test_zone_detection()))
    results.append(("Product mention guard", test_product_mention_guard()))
    results.append(("Full short-circuit", test_full_short_circuit()))

    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    all_pass = True
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}: {name}")
        if not ok:
            all_pass = False

    print(f"\n{'🎉 TOUS LES TESTS PASSENT' if all_pass else '⚠️ CERTAINS TESTS ÉCHOUENT'}")
