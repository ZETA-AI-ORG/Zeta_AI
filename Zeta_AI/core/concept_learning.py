import json
import os
from typing import Dict, List
from utils import log3

CATCHALL_STORE = "catchall_terms_stats.json"

class ConceptLearner:
    def __init__(self, color_list: List[str], product_terms: List[str], size_terms: List[str]):
        from core.ecommerce_categories import CATEGORIES
        self.color_list = color_list
        self.product_terms = product_terms
        self.size_terms = size_terms
        self.stats = self._load_stats()
        self.ecommerce_categories = CATEGORIES

    def _load_stats(self) -> Dict[str, Dict]:
        if os.path.exists(CATCHALL_STORE):
            with open(CATCHALL_STORE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_stats(self):
        with open(CATCHALL_STORE, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    import time
    def observe(self, terms: List[str], context_text: str = ""):
        now = int(time.time())
        for term in terms:
            entry = self.stats.get(term, {"timestamps": [], "categories": []})
            # Ajout du timestamp de l'occurrence
            entry["timestamps"].append(now)
            # Garder uniquement les occurrences des 30 derniers jours
            one_month_ago = now - 30*24*3600
            entry["timestamps"] = [ts for ts in entry["timestamps"] if ts >= one_month_ago]
            # Classifier automatiquement si seuil atteint OU si nouveau contexte
            if len(entry["timestamps"]) >= 50:
                new_cat = self.classify(term, context_text)
                if new_cat and new_cat not in entry["categories"]:
                    entry["categories"].append(new_cat)
                    log3("[LEARNING][MULTI-CAT] Terme associé à une nouvelle catégorie (seuil 50/mois)", f"{term} → {new_cat}")
                    self.integrate(term, new_cat)
            self.stats[term] = entry
        self._save_stats()

    def classify(self, term: str, context_text: str = "") -> str:
        t = term.lower()
        ctx = context_text.lower() if context_text else ""
        # 1. Matching e-commerce catégories (avec contexte)
        for cat, souscats in self.ecommerce_categories.items():
            for souscat in souscats:
                if souscat.lower() in t or t in souscat.lower():
                    # Contexte fort : si le contexte contient la souscatégorie, priorité
                    if ctx and (souscat.lower() in ctx or cat.lower() in ctx):
                        return f"category:{cat}"
                    # Sinon, on note la catégorie
                    return f"category:{cat}"
        # 2. Heuristique couleur
        if any(c in t for c in ["bleu", "vert", "rouge", "noir", "jaune", "rose", "gris", "marron", "beige", "violet", "dor", "argent", "turquoise", "kaki", "ivoire", "prune", "sable", "corail", "lilas", "azur", "marine", "menthe", "chocolat", "caramel", "café"]):
            return "color"
        # 3. Heuristique taille
        if t in ["xs", "s", "m", "l", "xl", "xxl"] or "taille" in t or any(x in t for x in ["kg", "g", "gramme", "litre", "cl", "ml", "cm", "mm"]):
            return "size"
        # 4. Heuristique produit
        if any(x in t for x in ["couche", "casque", "bavoir", "lingette", "siège", "paquet", "carton", "lot", "boîte", "pack", "article", "produit"]):
            return "product"
        return "other"

    def integrate(self, term: str, category: str):
        if category == "color" and term not in self.color_list:
            self.color_list.append(term)
        elif category == "product" and term not in self.product_terms:
            self.product_terms.append(term)
        elif category == "size" and term not in self.size_terms:
            self.size_terms.append(term)
        elif category.startswith("category:"):
            cat = category.split(":", 1)[1]
            # Ajout dans le mapping e-commerce (en mémoire, persisté si besoin)
            if term not in self.ecommerce_categories.get(cat, []):
                self.ecommerce_categories.setdefault(cat, []).append(term)
                log3(f"[LEARNING][E-COM CAT] Terme ajouté à la catégorie e-commerce {cat}", term)
        # Sinon, log "other" et propose à l'admin une revue manuelle
        else:
            log3("[LEARNING][OTHER] Terme non classé automatiquement", term)

    def get_stats(self):
        return self.stats
