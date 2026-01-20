#!/usr/bin/env python3
"""
Module de calcul automatique universel
Gère tous les calculs pour toutes les entreprises
"""
import re
from typing import Dict, List, Optional, Tuple

class UniversalCalculator:
    """Calculateur universel pour opérations e-commerce"""
    
    def __init__(self):
        self.operations_log = []
    
    def detect_calculation_need(self, question: str) -> Dict:
        """
        Détecte si la question nécessite un calcul
        UNIVERSEL - fonctionne pour toute entreprise
        """
        question_lower = question.lower()
        
        detection = {
            'needs_calculation': False,
            'calc_type': None,
            'confidence': 0.0
        }
        
        # 1. Multiplication (quantité × prix)
        if any(word in question_lower for word in ['achète', 'acheter', 'prendre', 'commander', 'paquets', 'lots']):
            match = re.search(r'(\d+)\s+(?:paquets?|lots?|cartons?|unités?)', question_lower)
            if match:
                detection['needs_calculation'] = True
                detection['calc_type'] = 'multiplication'
                detection['quantity'] = int(match.group(1))
                detection['confidence'] = 0.95
                return detection
        
        # 2. Différence entre deux valeurs
        if 'différence' in question_lower or 'écart' in question_lower:
            detection['needs_calculation'] = True
            detection['calc_type'] = 'difference'
            detection['confidence'] = 0.90
            return detection
        
        # 3. Somme/Total (plusieurs items)
        if any(word in question_lower for word in ['total', 'ensemble', 'cumul', 'combiné', 'somme']):
            detection['needs_calculation'] = True
            detection['calc_type'] = 'sum'
            detection['confidence'] = 0.85
            return detection
        
        # 4. Division (quantité nécessaire / taille lot)
        if any(word in question_lower for word in ['combien de lots', 'combien de paquets', 'besoin de']):
            match = re.search(r'(\d+)\s+(?:couches|pièces|unités)', question_lower)
            if match:
                detection['needs_calculation'] = True
                detection['calc_type'] = 'division'
                detection['desired_quantity'] = int(match.group(1))
                detection['confidence'] = 0.90
                return detection
        
        return detection
    
    def extract_prices_from_context(self, context: str) -> List[Dict]:
        """
        Extrait tous les prix du contexte avec métadonnées
        UNIVERSEL - marche pour tous produits
        """
        prices = []
        
        # Pattern 1: "300 pièces de X: 24.500 F CFA"
        pattern1 = r'(\d+)\s+(?:pièces?|unités?)\s+de\s+([^:]+):\s*(\d{1,3}(?:[.,\s]\d{3})*)\s*F?\s*CFA'
        matches1 = re.findall(pattern1, context, re.IGNORECASE)
        for qty, product, price_str in matches1:
            price_clean = price_str.replace(" ", "").replace(".", "").replace(",", "")
            try:
                prices.append({
                    'product': product.strip(),
                    'quantity': int(qty),
                    'price': int(price_clean),
                    'unit_price': int(price_clean) / int(qty),
                    'formatted': f"{int(price_clean):,} FCFA".replace(",", " ")
                })
            except (ValueError, ZeroDivisionError):
                continue
        
        # Pattern 2: "Livraison Zone: 1 500 FCFA"
        pattern2 = r'(?:livraison|frais).*?([A-Za-zÀ-ÿ\s-]+):\s*(\d{1,3}(?:[.,\s]\d{3})*)\s*F?\s*CFA'
        matches2 = re.findall(pattern2, context, re.IGNORECASE)
        for zone, price_str in matches2:
            price_clean = price_str.replace(" ", "").replace(".", "").replace(",", "")
            try:
                prices.append({
                    'product': f"Livraison {zone.strip()}",
                    'quantity': 1,
                    'price': int(price_clean),
                    'unit_price': int(price_clean),
                    'formatted': f"{int(price_clean):,} FCFA".replace(",", " ")
                })
            except ValueError:
                continue
        
        return prices
    
    def calculate(self, calc_type: str, **kwargs) -> Dict:
        """
        Effectue le calcul demandé
        """
        if calc_type == 'multiplication':
            return self._calc_multiplication(kwargs.get('quantity'), kwargs.get('unit_price'))
        
        elif calc_type == 'difference':
            return self._calc_difference(kwargs.get('price1'), kwargs.get('price2'))
        
        elif calc_type == 'sum':
            return self._calc_sum(kwargs.get('prices', []))
        
        elif calc_type == 'division':
            return self._calc_division(kwargs.get('desired_quantity'), kwargs.get('lot_size'))
        
        return {'error': 'Type de calcul non supporté'}
    
    def _calc_multiplication(self, quantity: int, unit_price: float) -> Dict:
        """Calcul: quantité × prix unitaire"""
        if not quantity or not unit_price:
            return {'error': 'Paramètres manquants'}
        
        total = int(quantity * unit_price)
        return {
            'operation': 'multiplication',
            'formula': f"{quantity} × {int(unit_price):,} FCFA".replace(",", " "),
            'result': total,
            'result_formatted': f"{total:,} FCFA".replace(",", " "),
            'explanation': f"Pour {quantity} paquets à {int(unit_price):,} FCFA chacun, le total est de {total:,} FCFA".replace(",", " ")
        }
    
    def _calc_difference(self, price1: int, price2: int) -> Dict:
        """Calcul: différence entre deux prix"""
        if not price1 or not price2:
            return {'error': 'Paramètres manquants'}
        
        diff = abs(price1 - price2)
        return {
            'operation': 'difference',
            'formula': f"|{price1:,} - {price2:,}| FCFA".replace(",", " "),
            'result': diff,
            'result_formatted': f"{diff:,} FCFA".replace(",", " "),
            'explanation': f"La différence entre {max(price1, price2):,} FCFA et {min(price1, price2):,} FCFA est de {diff:,} FCFA".replace(",", " ")
        }
    
    def _calc_sum(self, prices: List[int]) -> Dict:
        """Calcul: somme de plusieurs prix"""
        if not prices:
            return {'error': 'Aucun prix fourni'}
        
        total = sum(prices)
        formula_parts = [f"{p:,}".replace(",", " ") for p in prices]
        return {
            'operation': 'sum',
            'formula': f"{' + '.join(formula_parts)} = {total:,} FCFA".replace(",", " "),
            'result': total,
            'result_formatted': f"{total:,} FCFA".replace(",", " "),
            'explanation': f"Le total de {len(prices)} éléments est {total:,} FCFA".replace(",", " ")
        }
    
    def _calc_division(self, desired_quantity: int, lot_size: int) -> Dict:
        """Calcul: nombre de lots nécessaires"""
        if not desired_quantity or not lot_size:
            return {'error': 'Paramètres manquants'}
        
        import math
        lots_needed = math.ceil(desired_quantity / lot_size)
        total_quantity = lots_needed * lot_size
        
        return {
            'operation': 'division',
            'formula': f"⌈{desired_quantity} ÷ {lot_size}⌉ = {lots_needed} lots",
            'result': lots_needed,
            'result_formatted': f"{lots_needed} lot(s) de {lot_size} = {total_quantity} pièces",
            'explanation': f"Pour obtenir {desired_quantity} pièces, vous devez commander {lots_needed} lot(s) de {lot_size} pièces, soit {total_quantity} pièces au total"
        }
    
    def format_calculation_for_llm(self, calculation: Dict) -> str:
        """
        Formate le résultat de calcul pour injection dans le prompt LLM
        """
        if 'error' in calculation:
            return ""
        
        return f"""
📊 CALCUL AUTOMATIQUE EFFECTUÉ:
   Opération: {calculation['operation']}
   Formule: {calculation['formula']}
   Résultat: {calculation['result_formatted']}
   
   ⚠️ INSTRUCTION: Utilise CE résultat exact dans ta réponse. NE calcule PAS toi-même.
   Explication à donner au client: {calculation.get('explanation', '')}
"""


# Instance globale
calculator = UniversalCalculator()
