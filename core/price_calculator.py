#!/usr/bin/env python3
"""
🧮 CALCULATEUR DE PRIX INTELLIGENT RUE DU GROS
Système de calcul automatique des prix pour les couches avec frais de livraison
"""

import re
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass

from core.company_catalog_v2_loader import get_company_catalog_v2

@dataclass
class ProductPrice:
    """Structure pour stocker les informations de prix d'un produit"""
    product_type: str
    size: str
    quantity: int
    unit_price: float
    total_price: float
    description: str

@dataclass
class DeliveryInfo:
    """Structure pour les informations de livraison"""
    zone: str
    delivery_cost: float
    delivery_time: str
    is_central: bool

class UniversalPriceCalculator:
    """Calculateur de prix universel pour toutes les entreprises (100% synchrone, fallback si besoin)"""
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id
        self.products_catalog = {}
        self.delivery_zones = {}
        self.payment_info = {}
        # Chargement synchrone direct (fallback en dur)
        self._load_fallback_data()
    
    async def _load_company_data(self):
        """Charge les données de l'entreprise depuis la base de données"""
        if not self.company_id:
            return
        
        try:
            # Charger les données dynamiquement depuis la base de données
            from core.dynamic_catalog_loader import load_company_catalog
            
            catalog_data = await load_company_catalog(self.company_id)
            
            self.products_catalog = catalog_data.get("products", {})
            self.delivery_zones = catalog_data.get("delivery_zones", {})
            self.payment_info = catalog_data.get("payment_info", {})
            
            print(f"[PRICE_CALCULATOR] ✅ Données chargées pour {self.company_id}")
            print(f"[PRICE_CALCULATOR] - Produits: {len(self.products_catalog)} catégories")
            print(f"[PRICE_CALCULATOR] - Zones: {len(self.delivery_zones)} zones")
            print(f"[PRICE_CALCULATOR] - Paiement: {self.payment_info.get('method', 'N/A')}")
            
        except Exception as e:
            print(f"[PRICE_CALCULATOR] ❌ Erreur chargement données entreprise {self.company_id}: {e}")
            # Fallback vers les données Rue du Gros si disponible
            if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
                self._load_fallback_data()
    
    def _load_products_from_database(self):
        """Charge le catalogue produits depuis la base de données"""
        # Cette méthode sera implémentée pour charger depuis MeiliSearch/Supabase
        # Pour l'instant, on garde les données Rue du Gros comme exemple
        if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
            self.products_catalog = {
                "couches_pression": {
                    "taille 1": {"weight_range": "0-4kg", "price": 17900, "units": 300},
                    "taille 2": {"weight_range": "3-8kg", "price": 18900, "units": 300},
                    "taille 3": {"weight_range": "6-11kg", "price": 22900, "units": 300},
                    "taille 4": {"weight_range": "9-14kg", "price": 25900, "units": 300},
                    "taille 5": {"weight_range": "12-17kg", "price": 25900, "units": 300},
                    "taille 6": {"weight_range": "15-25kg", "price": 27900, "units": 300},
                    "taille 7": {"weight_range": "20-30kg", "price": 28900, "units": 300}
                },
                "couches_culottes": {
                    "1 paquet": {"price": 5500, "unit_price": 5500},
                    "2 paquets": {"price": 9800, "unit_price": 4900},
                    "3 paquets": {"price": 13500, "unit_price": 4500},
                    "6 paquets": {"price": 25000, "unit_price": 4167},
                    "12 paquets": {"price": 48000, "unit_price": 4000},
                    "1 colis (48)": {"price": 168000, "unit_price": 3500}
                },
                "couches_adultes": {
                    "1 paquet (10)": {"price": 5880, "unit_price": 588},
                    "2 paquets (20)": {"price": 11760, "unit_price": 570},
                    "3 paquets (30)": {"price": 16200, "unit_price": 540},
                    "6 paquets (60)": {"price": 36000, "unit_price": 500},
                    "12 paquets (120)": {"price": 114000, "unit_price": 475},
                    "1 colis (240)": {"price": 216000, "unit_price": 450}
                }
            }
    
    def _load_delivery_zones_from_database(self):
        """Charge les zones de livraison depuis la base de données"""
        if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
            self.delivery_zones = {
                "centrales": {
                    "zones": ["yopougon", "cocody", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville", "angré", "riviera"],
                    "cost": 1500,
                    "time": "Jour même si commande avant 11h, lendemain après 11h"
                },
                "périphériques": {
                    "zones": ["port-bouët", "attécoubé", "bingerville", "songon", "anyama", "brofodoumé", "grand-bassam", "dabou"],
                    "cost": 2250,
                    "time": "Jour même si commande avant 11h, lendemain après 11h"
                },
                "hors_abidjan": {
                    "zones": ["autres villes côte d'ivoire"],
                    "cost": 4250,
                    "time": "24h-72h selon la localité"
                }
            }
    
    def _load_payment_info_from_database(self):
        """Charge les informations de paiement depuis la base de données"""
        if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
            self.payment_info = {
                "method": "Wave",
                "phone": "+2250787360757",
                "deposit_required": 2000,
                "currency": "FCFA"
            }
    
    def extract_quantity_from_text(self, text: str) -> Tuple[int, str]:
        """Extrait la quantité et le type de produit du texte"""
        text_lower = text.lower()
        
        # Patterns pour extraire les quantités
        quantity_patterns = [
            r'(\d+)\s*paquets?',
            r'(\d+)\s*colis',
            r'(\d+)\s*unités?',
            r'(\d+)\s*couches?'
        ]
        
        quantity = 1
        for pattern in quantity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                quantity = int(match.group(1))
                break
        
        # Détecter le type de produit
        if any(word in text_lower for word in ['culottes', 'culotte']):
            return quantity, "culottes"
        elif any(word in text_lower for word in ['adultes', 'adulte']):
            return quantity, "adultes"
        else:
            return quantity, "pression"

    @staticmethod
    def _parse_int(s: str) -> Optional[int]:
        try:
            return int(str(s).strip())
        except Exception:
            return None

    @staticmethod
    def _extract_size_t1_t7(text: str) -> str:
        t = str(text or "").lower()
        m = re.search(r"\b(?:taille\s*)?([1-7])\b", t)
        if m:
            return f"taille {m.group(1)}"
        m = re.search(r"\b(?:t)([1-7])\b", t)
        if m:
            return f"taille {m.group(1)}"
        return ""

    @staticmethod
    def build_price_calculation_block_from_detected_items(
        *,
        company_id: Optional[str] = None,
        items: List[Dict[str, Any]],
        zone: str,
        delivery_fee_fcfa: Optional[int] = None,
    ) -> str:
        try:
            zone_s = str(zone or "").strip()
            delivery_fee = int(delivery_fee_fcfa) if delivery_fee_fcfa is not None else 0

            def _canon_product(v: str) -> str:
                s = str(v or "").strip().lower()
                if s in {"pressions", "pression"}:
                    return "pressions"
                if s in {"culottes", "culotte"}:
                    return "culottes"
                return ""

            def _canon_specs_t(v: str) -> str:
                s = str(v or "").strip().upper()
                m = re.fullmatch(r"T([1-7])", s)
                if m:
                    return f"T{m.group(1)}"
                return ""

            def _canon_unit(v: str) -> str:
                s = str(v or "").strip().lower()
                if s in {"lot", "lots"}:
                    return "lot"
                if s in {"paquet", "paquets", "pack", "packs"}:
                    return "paquet"
                return ""

            def _get_int_or_none(v) -> Optional[int]:
                if v is None:
                    return None
                if isinstance(v, bool):
                    return None
                if isinstance(v, int):
                    return v
                if isinstance(v, float) and v.is_integer():
                    return int(v)
                if isinstance(v, str):
                    m = re.fullmatch(r"\s*(\d+)\s*", v)
                    if m:
                        return int(m.group(1))
                return None

            normalized: List[Dict[str, Any]] = []
            for raw in (items or []):
                if not isinstance(raw, dict):
                    continue
                p = _canon_product(raw.get("product"))
                specs = _canon_specs_t(raw.get("specs"))
                unit = _canon_unit(raw.get("unit"))
                qty = _get_int_or_none(raw.get("qty"))
                normalized.append({"product": p, "specs": specs, "unit": unit, "qty": qty})

            normalized = [x for x in normalized if x.get("product") and x.get("specs") and x.get("unit") and isinstance(x.get("qty"), int)]
            if not normalized:
                return ""

            def _calc_from_catalog_v2(catalog_v2: Dict[str, Any]) -> Optional[str]:
                try:
                    if str(catalog_v2.get("pricing_strategy") or "").upper() != "UNIT_AS_ATOMIC":
                        return None

                    vtree = catalog_v2.get("v")
                    if not isinstance(vtree, dict):
                        return None

                    canonical_units = catalog_v2.get("canonical_units")
                    if not isinstance(canonical_units, list):
                        canonical_units = []
                    canonical_units = [str(u) for u in canonical_units if str(u).strip()]
                    if not canonical_units:
                        return None

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

                        # Soft matching (keeps legacy behavior for "pressions"/"culottes" while allowing arbitrary names)
                        p_low = product_s.lower()
                        for k in keys:
                            k_low = str(k or "").lower()
                            if p_low and (p_low in k_low or k_low in p_low):
                                return str(k)
                        return None

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

                        # Normalizer for common "taille 4" / "T4" patterns (keeps existing diaper behavior)
                        specs_up = specs_s.upper()
                        m = re.search(r"\bT([1-9]\d*)\b", specs_up)
                        if m:
                            t_norm = f"T{m.group(1)}"
                            exact2 = _match_key_case_insensitive(sub_keys, t_norm)
                            if exact2:
                                return exact2
                        m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", specs_up)
                        if m2:
                            t_norm = f"T{m2.group(1)}"
                            exact3 = _match_key_case_insensitive(sub_keys, t_norm)
                            if exact3:
                                return exact3

                        for k in sub_keys:
                            k_low = str(k or "").lower()
                            s_low = specs_s.lower()
                            if s_low and (s_low in k_low or k_low in s_low):
                                return str(k)
                        return None

                    lines: List[str] = []
                    subtotal_products = 0

                    for idx, it in enumerate(normalized, start=1):
                        product_raw = str(it.get("product") or "")
                        specs_raw = str(it.get("specs") or "").strip()
                        unit_key = str(it.get("unit") or "").strip()
                        qty = it.get("qty")

                        if not product_raw:
                            return None
                        if not unit_key:
                            return None
                        if not isinstance(qty, int) or qty <= 0:
                            return None

                        # IMPORTANT: unit must be explicit (exactly one of canonical_units)
                        if unit_key not in canonical_units:
                            return None

                        variant_key = _find_variant_key(product_raw)
                        node = vtree.get(variant_key) if variant_key else None
                        if not isinstance(node, dict):
                            return None

                        unit_price = None

                        node_s = node.get("s")
                        if isinstance(node_s, dict):
                            sub_key = _find_subvariant_key(node_s, specs_raw)
                            sub = node_s.get(sub_key) if sub_key else None
                            if not isinstance(sub, dict):
                                return None
                            u_map = sub.get("u")
                            if not isinstance(u_map, dict):
                                return None
                            tup = u_map.get(unit_key)
                            if tup is None:
                                return None
                            try:
                                unit_price = int(float(tup[0])) if isinstance(tup, list) and len(tup) >= 1 else int(float(tup))
                            except Exception:
                                unit_price = None

                            size_label = sub_key or specs_raw
                        else:
                            u_map = node.get("u")
                            if not isinstance(u_map, dict):
                                return None
                            tup = u_map.get(unit_key)
                            if tup is None:
                                return None
                            try:
                                unit_price = int(float(tup[0])) if isinstance(tup, list) and len(tup) >= 1 else int(float(tup))
                            except Exception:
                                unit_price = None

                            size_label = specs_raw or (variant_key or product_raw)

                        if unit_price is None or unit_price <= 0:
                            return None

                        item_subtotal = int(unit_price * qty)
                        subtotal_products += item_subtotal

                        qty_tag = "qty_units"
                        if unit_key.startswith("lot_"):
                            qty_tag = "qty_lots"
                        elif unit_key.startswith("paquet_"):
                            qty_tag = "qty_packs"
                        elif unit_key.startswith("colis_"):
                            qty_tag = "qty_colis"
                        elif unit_key.startswith("balle_"):
                            qty_tag = "qty_balles"

                        product_label = str(variant_key or product_raw).strip().upper() or "PRODUCT"

                        lines.append(
                            "  <item>\n"
                            f"    <index>{idx}</index>\n"
                            f"    <product>{UniversalPriceCalculator._xml_escape(product_label)}</product>\n"
                            f"    <size>{UniversalPriceCalculator._xml_escape(size_label)}</size>\n"
                            f"    <unit>{UniversalPriceCalculator._xml_escape(unit_key)}</unit>\n"
                            f"    <{qty_tag}>{qty}</{qty_tag}>\n"
                            f"    <unit_price_fcfa>{unit_price}</unit_price_fcfa>\n"
                            f"    <subtotal_fcfa>{item_subtotal}</subtotal_fcfa>\n"
                            "  </item>"
                        )

                    delivery_known = bool(zone_s) and (delivery_fee_fcfa is not None)
                    total = int(subtotal_products) + (int(delivery_fee) if delivery_known else 0)
                    if delivery_known:
                        ready = (
                            f"Le total fait {UniversalPriceCalculator._fmt_fcfa(total)}F"
                            + f" (produits {UniversalPriceCalculator._fmt_fcfa(subtotal_products)}F"
                            + f" + livraison {UniversalPriceCalculator._fmt_fcfa(delivery_fee)}F)."
                        )
                    else:
                        ready = f"Le total produits fait {UniversalPriceCalculator._fmt_fcfa(subtotal_products)}F."

                    return (
                        "  <status>OK</status>\n"
                        "  <mode>MULTI_ITEMS</mode>\n"
                        + "\n".join(lines)
                        + "\n"
                        + f"  <product_subtotal_fcfa>{int(subtotal_products)}</product_subtotal_fcfa>\n"
                        + f"  <delivery_fee_fcfa>{int(delivery_fee) if delivery_known else 0}</delivery_fee_fcfa>\n"
                        + f"  <total_fcfa>{int(total)}</total_fcfa>\n"
                        + f"  <zone>{UniversalPriceCalculator._xml_escape(zone_s)}</zone>\n"
                        + f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
                    )
                except Exception:
                    return None

            if company_id:
                try:
                    catalog_v2 = get_company_catalog_v2(company_id)
                except Exception:
                    catalog_v2 = None
                if isinstance(catalog_v2, dict):
                    out_dyn = _calc_from_catalog_v2(catalog_v2)
                    if out_dyn:
                        return out_dyn

            pressions_prices = {
                "T1": 17900,
                "T2": 18900,
                "T3": 22900,
                "T4": 25900,
                "T5": 25900,
                "T6": 27900,
                "T7": 28900,
            }

            culottes_prices_by_packs = {
                1: 5500,
                2: 9800,
                3: 13500,
                6: 25000,
                12: 48000,
                48: 168000,
            }

            lines: List[str] = []
            subtotal_products = 0

            for idx, it in enumerate(normalized, start=1):
                p = str(it.get("product") or "")
                specs = str(it.get("specs") or "")
                unit = str(it.get("unit") or "")
                qty = it.get("qty")

                if not p or not specs or unit not in {"lot", "paquet"} or not isinstance(qty, int) or qty <= 0:
                    return ""

                if p == "pressions":
                    if unit != "lot":
                        return ""
                    unit_price = int(pressions_prices.get(specs) or 0)
                    if unit_price <= 0:
                        return ""
                    item_subtotal = unit_price * qty
                    subtotal_products += item_subtotal
                    lines.append(
                        "  <item>\n"
                        f"    <index>{idx}</index>\n"
                        "    <product>PRESSIONS</product>\n"
                        f"    <size>{UniversalPriceCalculator._xml_escape(specs)}</size>\n"
                        f"    <qty_lots>{qty}</qty_lots>\n"
                        f"    <unit_price_fcfa>{unit_price}</unit_price_fcfa>\n"
                        f"    <subtotal_fcfa>{item_subtotal}</subtotal_fcfa>\n"
                        "  </item>"
                    )
                elif p == "culottes":
                    if unit != "paquet":
                        return ""
                    if qty not in culottes_prices_by_packs:
                        return ""
                    item_subtotal = int(culottes_prices_by_packs.get(qty) or 0)
                    if item_subtotal <= 0:
                        return ""
                    subtotal_products += item_subtotal
                    lines.append(
                        "  <item>\n"
                        f"    <index>{idx}</index>\n"
                        "    <product>CULOTTES</product>\n"
                        f"    <size>{UniversalPriceCalculator._xml_escape(specs)}</size>\n"
                        f"    <qty_packs>{qty}</qty_packs>\n"
                        f"    <subtotal_fcfa>{item_subtotal}</subtotal_fcfa>\n"
                        "  </item>"
                    )
                else:
                    return ""

            delivery_known = bool(zone_s) and (delivery_fee_fcfa is not None)
            total = int(subtotal_products) + (int(delivery_fee) if delivery_known else 0)
            if delivery_known:
                ready = (
                    f"Le total fait {UniversalPriceCalculator._fmt_fcfa(total)}F"
                    + f" (produits {UniversalPriceCalculator._fmt_fcfa(subtotal_products)}F"
                    + f" + livraison {UniversalPriceCalculator._fmt_fcfa(delivery_fee)}F)."
                )
            else:
                ready = f"Le total produits fait {UniversalPriceCalculator._fmt_fcfa(subtotal_products)}F."

            return (
                "  <status>OK</status>\n"
                "  <mode>MULTI_ITEMS</mode>\n"
                + "\n".join(lines)
                + "\n"
                + f"  <product_subtotal_fcfa>{int(subtotal_products)}</product_subtotal_fcfa>\n"
                + f"  <delivery_fee_fcfa>{int(delivery_fee) if delivery_known else 0}</delivery_fee_fcfa>\n"
                + f"  <total_fcfa>{int(total)}</total_fcfa>\n"
                + f"  <zone>{UniversalPriceCalculator._xml_escape(zone_s)}</zone>\n"
                + f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
            )

        except Exception:
            return ""

    @staticmethod
    def _build_price_block_from_catalog_v2(
        *,
        catalog_v2: Dict[str, Any],
        produit: str,
        specs: str,
        quantite: str,
        zone: str,
        delivery_fee: int,
    ) -> str:
        # Normalisation produit
        p = str(produit or "").strip().lower()
        if "pression" in p or "press" in p:
            product_key = "pressions"
        elif "culott" in p:
            product_key = "culottes"
        else:
            product_key = ""

        if not product_key:
            return ""

        # Specs: accepter T3, taille 3
        spec_raw = str(specs or "").strip().upper()
        spec = spec_raw
        m = re.search(r"\bT([1-9]\d*)\b", spec_raw)
        if m:
            spec = f"T{m.group(1)}"
        else:
            m2 = re.search(r"\bTAILLE\s*([1-9]\d*)\b", spec_raw)
            if m2:
                spec = f"T{m2.group(1)}"

        if not spec:
            return ""

        # Quantité: accepte "2 lots" / "6 paquets" / "1 colis" etc.
        q_s = str(quantite or "").strip().lower()
        m_q = re.search(r"(\d+)", q_s)
        if not m_q:
            return ""
        qty = int(m_q.group(1))
        if qty <= 0:
            return ""

        # Déterminer l'unité atomique (unit) à partir du texte + du catalogue.
        canonical_units = catalog_v2.get("canonical_units")
        if not isinstance(canonical_units, list):
            canonical_units = []
        canonical_units = [str(u) for u in canonical_units if str(u).strip()]

        def _pick_single(prefix: str) -> Optional[str]:
            matches = [u for u in canonical_units if u.startswith(prefix)]
            if len(matches) == 1:
                return matches[0]
            return None

        unit: Optional[str] = None

        if "lot" in q_s:
            if "12" in q_s and "lot_12" in canonical_units:
                unit = "lot_12"
            elif "6" in q_s and "lot_6" in canonical_units:
                unit = "lot_6"
            else:
                unit = _pick_single("lot_")
        elif "paquet" in q_s or "pack" in q_s:
            unit = _pick_single("paquet_") or ("piece" if "piece" in canonical_units else None)
        elif "colis" in q_s:
            unit = _pick_single("colis_")
        elif "balle" in q_s:
            unit = _pick_single("balle_")
        elif "piece" in q_s or "pièce" in q_s or "pcs" in q_s:
            unit = "piece" if "piece" in canonical_units else None

        if not unit:
            return ""

        # Le catalogue v2 peut exister sous 2 formats:
        # - legacy: matrix (flat)
        # - compact: v (tree) avec u[unit] = [price, stock]
        price_lookup: Dict[tuple, int] = {}

        matrix = catalog_v2.get("matrix")
        if isinstance(matrix, list):
            for row in matrix:
                if not isinstance(row, dict):
                    continue
                r_spec = str(row.get("spec") or "").strip().upper()
                r_unit = str(row.get("unit") or "").strip()
                r_price = row.get("price")
                try:
                    r_price_i = int(float(r_price))
                except Exception:
                    continue
                if r_spec and r_unit and r_price_i > 0:
                    price_lookup[(r_spec, r_unit)] = r_price_i

        vtree = catalog_v2.get("v")
        if (not price_lookup) and isinstance(vtree, dict):
            def _find_variant_key(target: str) -> Optional[str]:
                t = target.lower()
                for k in vtree.keys():
                    kk = str(k or "").strip()
                    if not kk:
                        continue
                    k_low = kk.lower()
                    if t == "pressions" and "pression" in k_low:
                        return kk
                    if t == "culottes" and "culott" in k_low:
                        return kk
                return None

            variant_key = _find_variant_key(product_key)
            node = vtree.get(variant_key) if variant_key else None
            if isinstance(node, dict):
                # Culottes: u[unit] direct
                u = node.get("u") if isinstance(node.get("u"), dict) else None
                if isinstance(u, dict):
                    for unit_raw, tup in u.items():
                        uu = str(unit_raw or "").strip()
                        if not uu:
                            continue
                        try:
                            price_i = int(float(tup[0])) if isinstance(tup, list) and len(tup) >= 1 else int(float(tup))
                        except Exception:
                            continue
                        if price_i > 0:
                            price_lookup[((variant_key or "").upper(), uu)] = price_i

                # Pressions: s[Tn].u[unit]
                s = node.get("s") if isinstance(node.get("s"), dict) else None
                if isinstance(s, dict):
                    for sub_raw, sub_node in s.items():
                        sub = str(sub_raw or "").strip().upper()
                        if not sub:
                            continue
                        sub_u = sub_node.get("u") if isinstance(sub_node, dict) and isinstance(sub_node.get("u"), dict) else None
                        if not isinstance(sub_u, dict):
                            continue
                        for unit_raw, tup in sub_u.items():
                            uu = str(unit_raw or "").strip()
                            if not uu:
                                continue
                            try:
                                price_i = int(float(tup[0])) if isinstance(tup, list) and len(tup) >= 1 else int(float(tup))
                            except Exception:
                                continue
                            if price_i > 0:
                                price_lookup[(sub, uu)] = price_i

        # Dans le format compact, on utilise:
        # - pressions: spec=Tn
        # - culottes: spec=variant_key
        lookup_spec = spec
        if product_key == "culottes":
            lookup_spec = ((variant_key or "").upper() if 'variant_key' in locals() and variant_key else spec)

        unit_price = price_lookup.get((lookup_spec, unit))
        if not unit_price:
            return ""

        subtotal = int(unit_price * qty)
        total = int(subtotal + int(delivery_fee or 0))

        ready = (
            f"Pour {qty} {unit.replace('_', ' ')} de {product_key} {spec}"
            + (f" + livraison {zone} ({UniversalPriceCalculator._fmt_fcfa(int(delivery_fee or 0))}F)" if zone and delivery_fee else "")
            + f", le total fait {UniversalPriceCalculator._fmt_fcfa(total)}F ✅"
        )

        return (
            "  <status>OK</status>\n"
            f"  <product>{product_key.upper()}</product>\n"
            f"  <size>{UniversalPriceCalculator._xml_escape(spec)}</size>\n"
            f"  <unit>{UniversalPriceCalculator._xml_escape(unit)}</unit>\n"
            f"  <quantity>{qty}</quantity>\n"
            f"  <product_subtotal_fcfa>{subtotal}</product_subtotal_fcfa>\n"
            f"  <delivery_fee_fcfa>{int(delivery_fee or 0)}</delivery_fee_fcfa>\n"
            f"  <total_fcfa>{total}</total_fcfa>\n"
            f"  <zone>{UniversalPriceCalculator._xml_escape(zone)}</zone>\n"
            f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
        )

    @staticmethod
    def build_price_calculation_block_for_rue_du_grossiste(
        *,
        company_id: Optional[str] = None,
        produit: str,
        specs: str,
        quantite: str,
        zone: str,
        delivery_fee_fcfa: Optional[int] = None,
    ) -> str:
        try:
            produit_l = str(produit or "").strip().lower()
            specs_l = str(specs or "").strip().lower()
            quant_l = str(quantite or "").strip().lower()
            zone_s = str(zone or "").strip()
            delivery_fee = int(delivery_fee_fcfa) if delivery_fee_fcfa is not None else 0

            # --- Nouveau: calcul UNIT_AS_ATOMIC via Catalogue V2 (si dispo) ---
            if company_id:
                try:
                    catalog_v2 = get_company_catalog_v2(company_id)
                except Exception:
                    catalog_v2 = None

                if isinstance(catalog_v2, dict) and str(catalog_v2.get("pricing_strategy") or "").upper() == "UNIT_AS_ATOMIC":
                    try:
                        pc = UniversalPriceCalculator._build_price_block_from_catalog_v2(
                            catalog_v2=catalog_v2,
                            produit=produit_l,
                            specs=specs_l,
                            quantite=quant_l,
                            zone=zone_s,
                            delivery_fee=delivery_fee,
                        )
                        if str(pc or "").strip():
                            return pc
                    except Exception:
                        pass

            is_culottes = "culott" in produit_l
            is_pression = ("pression" in produit_l) or ("press" in produit_l)

            if not (is_culottes or is_pression):
                return ""

            q = UniversalPriceCalculator._extract_quantity_int(quant_l)
            if q is None:
                return ""

            delivery_fee = 0
            if isinstance(delivery_fee_fcfa, int) and delivery_fee_fcfa >= 0:
                delivery_fee = int(delivery_fee_fcfa)

            if is_culottes:
                allowed = [1, 2, 3, 6, 12, 48]
                prices = {1: 5500, 2: 9800, 3: 13500, 6: 25000, 12: 48000, 48: 168000}

                if q not in prices:
                    below = [x for x in allowed if x < q]
                    above = [x for x in allowed if x > q]
                    s1 = below[-1] if below else (above[0] if above else allowed[0])
                    s2 = above[0] if above else (below[-1] if below else allowed[-1])
                    ready = (
                        "Pour les culottes, les quantités dispo c’est 1, 2, 3, 6, 12 ou 48 paquets. "
                        f"Tu préfères {s1} ou {s2} paquets ?"
                    )
                    return (
                        "  <status>INVALID_QUANTITY</status>\n"
                        "  <product>CULOTTES</product>\n"
                        f"  <requested_quantity_packs>{q}</requested_quantity_packs>\n"
                        f"  <allowed_quantities>{','.join(str(x) for x in allowed)}</allowed_quantities>\n"
                        f"  <suggested_quantities>{s1},{s2}</suggested_quantities>\n"
                        f"  <delivery_fee_fcfa>{delivery_fee}</delivery_fee_fcfa>\n"
                        f"  <zone>{UniversalPriceCalculator._xml_escape(zone_s)}</zone>\n"
                        f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
                    )

                subtotal = int(prices[q])
                total = subtotal + delivery_fee
                ready = (
                    f"Pour {q} paquet{'s' if q > 1 else ''} de culottes"
                    + (
                        f" + livraison {zone_s} ({UniversalPriceCalculator._fmt_fcfa(delivery_fee)}F)"
                        if zone_s and delivery_fee
                        else ""
                    )
                    + f", le total fait {UniversalPriceCalculator._fmt_fcfa(total)}F ✅"
                )

                return (
                    "  <status>OK</status>\n"
                    "  <product>CULOTTES</product>\n"
                    f"  <quantity_packs>{q}</quantity_packs>\n"
                    f"  <product_subtotal_fcfa>{subtotal}</product_subtotal_fcfa>\n"
                    f"  <delivery_fee_fcfa>{delivery_fee}</delivery_fee_fcfa>\n"
                    f"  <total_fcfa>{total}</total_fcfa>\n"
                    f"  <zone>{UniversalPriceCalculator._xml_escape(zone_s)}</zone>\n"
                    f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
                )

            if is_pression:
                taille = UniversalPriceCalculator._extract_size_t1_t7(specs_l) or UniversalPriceCalculator._extract_size_t1_t7(produit_l)
                if not taille:
                    return ""

                prices = {
                    "taille 1": 17900,
                    "taille 2": 18900,
                    "taille 3": 22900,
                    "taille 4": 25900,
                    "taille 5": 25900,
                    "taille 6": 27900,
                    "taille 7": 28900,
                }

                is_lot_wording = "lot" in quant_l
                qty_lots: Optional[int] = None
                qty_packs: Optional[int] = None
                if is_lot_wording:
                    qty_lots = int(q)
                    qty_packs = int(q) * 6
                else:
                    qty_packs = int(q)
                    qty_lots = 1 if int(q) == 6 else None

                if qty_lots is None or qty_lots <= 0 or qty_packs is None or qty_packs <= 0:
                    ready = "Les pressions sont vendues uniquement par lot de 6 paquets. Tu veux 1 lot (6 paquets) ?"
                    return (
                        "  <status>INVALID_QUANTITY</status>\n"
                        "  <product>PRESSIONS</product>\n"
                        f"  <size>{UniversalPriceCalculator._xml_escape(taille)}</size>\n"
                        f"  <requested_quantity_packs>{int(q)}</requested_quantity_packs>\n"
                        "  <allowed_quantities>6</allowed_quantities>\n"
                        f"  <delivery_fee_fcfa>{delivery_fee}</delivery_fee_fcfa>\n"
                        f"  <zone>{UniversalPriceCalculator._xml_escape(zone_s)}</zone>\n"
                        f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
                    )

                unit_price_lot = int(prices.get(taille) or 0)
                subtotal = int(unit_price_lot * qty_lots)
                if subtotal <= 0:
                    return ""

                total = subtotal + delivery_fee
                ready = (
                    f"Pour {qty_lots} lot{'s' if qty_lots > 1 else ''} ({qty_packs} paquets) de pressions {taille}"
                    + (
                        f" + livraison {zone_s} ({UniversalPriceCalculator._fmt_fcfa(delivery_fee)}F)"
                        if zone_s and delivery_fee
                        else ""
                    )
                    + f", le total fait {UniversalPriceCalculator._fmt_fcfa(total)}F ✅"
                )

                return (
                    "  <status>OK</status>\n"
                    "  <product>PRESSIONS</product>\n"
                    f"  <size>{UniversalPriceCalculator._xml_escape(taille)}</size>\n"
                    f"  <quantity_packs>{int(qty_packs)}</quantity_packs>\n"
                    f"  <product_subtotal_fcfa>{subtotal}</product_subtotal_fcfa>\n"
                    f"  <delivery_fee_fcfa>{delivery_fee}</delivery_fee_fcfa>\n"
                    f"  <total_fcfa>{total}</total_fcfa>\n"
                    f"  <zone>{UniversalPriceCalculator._xml_escape(zone_s)}</zone>\n"
                    f"  <ready_to_send>{UniversalPriceCalculator._xml_escape(ready)}</ready_to_send>"
                )

            return ""
        except Exception:
            return ""
    
    def extract_size_from_text(self, text: str, product_type: str) -> str:
        """Extrait la taille du produit du texte"""
        text_lower = text.lower()
        
        if product_type == "pression":
            # Chercher les tailles 1-7
            for i in range(1, 8):
                if f"taille {i}" in text_lower or f"t{i}" in text_lower:
                    return f"taille {i}"
            
            # Chercher par poids
            weight_patterns = {
                "taille 1": [0, 1, 2, 3, 4],
                "taille 2": [3, 4, 5, 6, 7, 8],
                "taille 3": [6, 7, 8, 9, 10, 11],
                "taille 4": [9, 10, 11, 12, 13, 14],
                "taille 5": [12, 13, 14, 15, 16, 17],
                "taille 6": [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
                "taille 7": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
            }
            
            for weight in range(0, 31):
                if f"{weight}kg" in text_lower or f"{weight} kg" in text_lower:
                    for taille, poids_range in weight_patterns.items():
                        if weight in poids_range:
                            return taille
            
            return "taille 3"  # Taille par défaut
        
        elif product_type == "culottes":
            # Pour les culottes, on cherche le nombre de paquets
            if "1 paquet" in text_lower or "un paquet" in text_lower:
                return "1 paquet"
            elif "2 paquets" in text_lower or "deux paquets" in text_lower:
                return "2 paquets"
            elif "3 paquets" in text_lower or "trois paquets" in text_lower:
                return "3 paquets"
            elif "6 paquets" in text_lower or "six paquets" in text_lower:
                return "6 paquets"
            elif "12 paquets" in text_lower or "douze paquets" in text_lower:
                return "12 paquets"
            elif "colis" in text_lower:
                return "1 colis (48)"
            else:
                return "1 paquet"  # Par défaut
        
        elif product_type == "adultes":
            # Pour les adultes, même logique
            if "1 paquet" in text_lower or "un paquet" in text_lower:
                return "1 paquet (10)"
            elif "2 paquets" in text_lower or "deux paquets" in text_lower:
                return "2 paquets (20)"
            elif "3 paquets" in text_lower or "trois paquets" in text_lower:
                return "3 paquets (30)"
            elif "6 paquets" in text_lower or "six paquets" in text_lower:
                return "6 paquets (60)"
            elif "12 paquets" in text_lower or "douze paquets" in text_lower:
                return "12 paquets (120)"
            elif "colis" in text_lower:
                return "1 colis (240)"
            else:
                return "1 paquet (10)"  # Par défaut
        
        return "taille 3"  # Fallback
    
    def extract_delivery_zone(self, text: str) -> DeliveryInfo:
        """Extrait la zone de livraison du texte"""
        text_lower = text.lower()
        
        # Vérifier les zones centrales
        for zone in self.delivery_zones["centrales"]["zones"]:
            if zone in text_lower:
                return DeliveryInfo(
                    zone=zone.title(),
                    delivery_cost=self.delivery_zones["centrales"]["cost"],
                    delivery_time=self.delivery_zones["centrales"]["time"],
                    is_central=True
                )
        
        # Vérifier les zones périphériques
        for zone in self.delivery_zones["périphériques"]["zones"]:
            if zone in text_lower:
                return DeliveryInfo(
                    zone=zone.title(),
                    delivery_cost=self.delivery_zones["périphériques"]["cost"],
                    delivery_time=self.delivery_zones["périphériques"]["time"],
                    is_central=False
                )
        
        # Par défaut, zone centrale
        return DeliveryInfo(
            zone="Zone centrale (à confirmer)",
            delivery_cost=self.delivery_zones["centrales"]["cost"],
            delivery_time=self.delivery_zones["centrales"]["time"],
            is_central=True
        )
    
    def calculate_product_price(self, text: str) -> List[ProductPrice]:
        # Sécurité : print si attributs essentiels absents
        if not hasattr(self, 'products_catalog'):
            print('[BUG CALCULATEUR] products_catalog absent')
            self.products_catalog = {}
        if not hasattr(self, 'delivery_zones'):
            print('[BUG CALCULATEUR] delivery_zones absent')
            self.delivery_zones = {}
        if not hasattr(self, 'payment_info'):
            print('[BUG CALCULATEUR] payment_info absent')
            self.payment_info = {}
        """Calcule le prix des produits à partir du texte"""
        quantity, product_type = self.extract_quantity_from_text(text)
        size = self.extract_size_from_text(text, product_type)
        
        products = []
        
        # Mapper les types de produits vers les clés du catalogue
        product_mapping = {
            "pression": "couches_pression",
            "culottes": "couches_culottes", 
            "adultes": "couches_adultes"
        }
        
        catalog_key = product_mapping.get(product_type)
        if not catalog_key or catalog_key not in self.products_catalog:
            return products
        
        product_catalog = self.products_catalog[catalog_key]
        
        if size in product_catalog:
            price_info = product_catalog[size]
            total_price = price_info["price"] * quantity
            
            # Déterminer le type de produit pour l'affichage
            product_type_names = {
                "couches_pression": "Couches à pression",
                "couches_culottes": "Couches culottes",
                "couches_adultes": "Couches adultes"
            }
            
            product_name = product_type_names.get(catalog_key, "Produit")
            
            # Construire la description
            if catalog_key == "couches_pression":
                description = f"{quantity} paquet(s) de couches à pression {size} - {price_info.get('units', 'N/A')} couches par paquet"
                size_display = f"{size} ({price_info.get('weight_range', '')})"
            else:
                description = f"{quantity} x {size} de {product_name.lower()}"
                size_display = size
            
            products.append(ProductPrice(
                product_type=product_name,
                size=size_display,
                quantity=quantity,
                unit_price=price_info.get("unit_price", price_info["price"]),
                total_price=total_price,
                description=description
            ))
        
        return products
    
    def calculate_total_price(self, products: List[ProductPrice], delivery_zone: str = None) -> Dict:
        """Calcule le prix total avec livraison"""
        if not products:
            return {
                "products": [],
                "subtotal": 0,
                "delivery_cost": 0,
                "total": 0,
                "delivery_info": None,
                "breakdown": "Aucun produit identifié"
            }
        
        # Calculer le sous-total
        subtotal = sum(product.total_price for product in products)
        
        # Calculer les frais de livraison
        delivery_info = None
        delivery_cost = 0
        
        if delivery_zone:
            delivery_info = self.extract_delivery_zone(delivery_zone)
            delivery_cost = delivery_info.delivery_cost
        
        total = subtotal + delivery_cost
        
        return {
            "products": products,
            "subtotal": subtotal,
            "delivery_cost": delivery_cost,
            "total": total,
            "delivery_info": delivery_info,
            "breakdown": self._generate_price_breakdown(products, delivery_cost, delivery_info)
        }
    
    def _generate_price_breakdown(self, products: List[ProductPrice], delivery_cost: float, delivery_info: DeliveryInfo = None) -> str:
        """Génère un récapitulatif détaillé des prix"""
        breakdown = "🧮 RÉCAPITULATIF DE PRIX :\n\n"
        
        # Détail des produits
        for i, product in enumerate(products, 1):
            breakdown += f"📦 Produit {i}: {product.description}\n"
            breakdown += f"   💰 Prix unitaire: {product.unit_price:,.0f} FCFA\n"
            breakdown += f"   📊 Quantité: {product.quantity}\n"
            breakdown += f"   💵 Sous-total: {product.total_price:,.0f} FCFA\n\n"
        
        # Sous-total
        subtotal = sum(p.total_price for p in products)
        breakdown += f"📋 SOUS-TOTAL PRODUITS: {subtotal:,.0f} FCFA\n"
        
        # Frais de livraison
        if delivery_info:
            breakdown += f"🚚 LIVRAISON ({delivery_info.zone}): {delivery_cost:,.0f} FCFA\n"
            breakdown += f"   ⏰ Délai: {delivery_info.delivery_time}\n"
        else:
            breakdown += f"🚚 LIVRAISON: {delivery_cost:,.0f} FCFA (zone à confirmer)\n"
        
        # Total
        total = subtotal + delivery_cost
        breakdown += f"\n🎯 TOTAL À PAYER: {total:,.0f} FCFA\n"
        
        # Acompte
        breakdown += f"💳 ACOMPTE REQUIS: 2.000 FCFA\n"
        breakdown += f"💰 RESTE À PAYER: {total - 2000:,.0f} FCFA"
        
        return breakdown

# Cache des calculateurs par entreprise
_calculator_cache = {}

def get_price_calculator(company_id: str) -> UniversalPriceCalculator:
    """Obtient ou crée un calculateur de prix pour une entreprise"""
    if company_id not in _calculator_cache:
        _calculator_cache[company_id] = UniversalPriceCalculator(company_id)
    return _calculator_cache[company_id]

def calculate_order_price(message: str, company_id: str, delivery_zone: str = None) -> Dict:
    """
    Fonction principale pour calculer le prix d'une commande
    
    Args:
        message: Message du client contenant la commande
        company_id: ID de l'entreprise
        delivery_zone: Zone de livraison (optionnel)
    
    Returns:
        Dictionnaire avec les informations de prix calculées
    """
    calculator = get_price_calculator(company_id)
    products = calculator.calculate_product_price(message)
    return calculator.calculate_total_price(products, delivery_zone)

def extract_delivery_zone_from_conversation(conversation_history: List[Dict]) -> str:
    """
    Extrait la zone de livraison de l'historique de conversation
    """
    for message in reversed(conversation_history):  # Commencer par les plus récents
        text = message.get("message", "").lower()
        if any(zone in text for zone in ["cocody", "yopougon", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville", "angré", "riviera", "bingerville", "port-bouët", "attécoubé"]):
            return message.get("message", "")
    return None
