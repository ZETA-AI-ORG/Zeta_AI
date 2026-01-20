#!/usr/bin/env python3
"""
Système d'auto-apprentissage des patterns regex
- Détecte automatiquement de nouveaux patterns dans les documents
- Ajoute les patterns pertinents au fichier patterns_metier.json
- Fait évoluer le système de manière automatisée
"""
import re
import json
import os
from typing import Dict, List, Set
from collections import Counter

class DynamicPatternLearner:
    def __init__(self, patterns_file_path: str):
        self.patterns_file_path = patterns_file_path
        self.existing_patterns = self._load_existing_patterns()
        self.candidate_patterns = {}
        self.pattern_confidence = {}
        
    def _load_existing_patterns(self) -> Dict[str, str]:
        """Charge les patterns existants"""
        try:
            with open(self.patterns_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_patterns(self, new_patterns: Dict[str, str]):
        """Sauvegarde les nouveaux patterns dans le fichier JSON"""
        all_patterns = {**self.existing_patterns, **new_patterns}
        with open(self.patterns_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_patterns, f, indent=2, ensure_ascii=False)
        print(f"✅ {len(new_patterns)} nouveaux patterns ajoutés au fichier")
    
    def detect_potential_patterns(self, documents: List[Dict]) -> Dict[str, List[str]]:
        """Détecte des patterns potentiels dans les documents"""
        potential_patterns = {
            'nouveaux_montants': [],
            'nouveaux_contacts': [],
            'nouvelles_zones': [],
            'nouveaux_delais': [],
            'nouvelles_marques': [],
            'nouveaux_produits': [],
            'nouvelles_conditions': [],
            'nouveaux_horaires': [],
            'nouvelles_adresses': []
        }
        
        for doc in documents:
            content = doc.get('content', '')
            
            # Détection de nouveaux montants (autres devises, formats)
            montants = re.findall(r'(\d+(?:[.,]\d+)?)\s*(euros?|dollars?|usd|eur|€|\$)', content, re.IGNORECASE)
            for montant, devise in montants:
                pattern = f"{montant} {devise}"
                if pattern not in str(self.existing_patterns.values()):
                    potential_patterns['nouveaux_montants'].append(pattern)
            
            # Détection de nouveaux formats de contact
            contacts = re.findall(r'((?:tel|téléphone|phone|contact)[:\s]*([+]?\d{2,4}[-\s]?\d{2,4}[-\s]?\d{2,4}[-\s]?\d{2,4}))', content, re.IGNORECASE)
            for match, numero in contacts:
                if numero not in str(self.existing_patterns.values()):
                    potential_patterns['nouveaux_contacts'].append(numero)
            
            # Détection de nouvelles zones géographiques
            zones = re.findall(r'\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\b(?=.*(?:zone|quartier|commune|ville|localité))', content)
            for zone in zones:
                if zone.lower() not in str(self.existing_patterns.values()).lower():
                    potential_patterns['nouvelles_zones'].append(zone)
            
            # Détection de nouveaux délais
            delais = re.findall(r'(\d+\s*(?:minutes?|min|heures?|h|jours?|j|semaines?|mois))', content, re.IGNORECASE)
            for delai in delais:
                if delai not in str(self.existing_patterns.values()):
                    potential_patterns['nouveaux_delais'].append(delai)
            
            # Détection de nouvelles marques/produits
            marques = re.findall(r'(?:marque|brand)[:\s]*([A-Z][a-zA-Z\s&]+)', content, re.IGNORECASE)
            for marque in marques:
                marque = marque.strip()
                if marque and marque not in str(self.existing_patterns.values()):
                    potential_patterns['nouvelles_marques'].append(marque)
            
            # Détection de nouveaux types de produits
            produits = re.findall(r'(?:produit|article|item)[:\s]*([a-zA-ZÀ-ÿ\s]+)', content, re.IGNORECASE)
            for produit in produits:
                produit = produit.strip()
                if produit and len(produit) > 3 and produit not in str(self.existing_patterns.values()):
                    potential_patterns['nouveaux_produits'].append(produit)
            
            # Détection de nouvelles conditions
            conditions = re.findall(r'(condition[s]?[:\s]*[^.]+)', content, re.IGNORECASE)
            for condition in conditions:
                if condition not in str(self.existing_patterns.values()):
                    potential_patterns['nouvelles_conditions'].append(condition)
            
            # Détection de nouveaux horaires
            horaires = re.findall(r'(\d{1,2}h\d{0,2}\s*[-à]\s*\d{1,2}h\d{0,2})', content, re.IGNORECASE)
            for horaire in horaires:
                if horaire not in str(self.existing_patterns.values()):
                    potential_patterns['nouveaux_horaires'].append(horaire)
            
            # Détection de nouvelles adresses
            adresses = re.findall(r'(?:adresse|située?|localisée?)[:\s]*([^.\n]+)', content, re.IGNORECASE)
            for adresse in adresses:
                adresse = adresse.strip()
                if adresse and len(adresse) > 10 and adresse not in str(self.existing_patterns.values()):
                    potential_patterns['nouvelles_adresses'].append(adresse)
        
        return potential_patterns
    
    def generate_regex_patterns(self, detected_patterns: Dict[str, List[str]]) -> Dict[str, str]:
        """Génère des patterns regex à partir des détections avec contexte métier complet"""
        new_patterns = {}
        
        for category, items in detected_patterns.items():
            if not items:
                continue
                
            # Compter les occurrences pour valider la pertinence
            item_counts = Counter(items)
            
            for item, count in item_counts.items():
                # Seuil de confiance : au moins 2 occurrences ou pattern très spécifique
                if count >= 2 or self._is_high_confidence_pattern(item, category):
                    
                    # VALIDATION CONTEXTUELLE : éviter les patterns trop courts/ambigus
                    if not self._is_contextually_safe_pattern(item, category):
                        print(f"⚠️ Pattern '{item}' rejeté (trop ambigu)")
                        continue
                    
                    if category == 'nouveaux_montants':
                        # Générer pattern pour nouveaux montants avec contexte
                        devise = item.split()[-1]
                        pattern_name = f"montant_{devise.lower()}_contextuel"
                        new_patterns[pattern_name] = f"(\\d+(?:[.,]\\d+)?)\\s*{re.escape(devise)}(?=\\s|\\.|,|$)"
                    
                    elif category == 'nouveaux_contacts':
                        # Pattern avec contexte métier complet
                        if len(item) >= 8:  # Numéros complets seulement
                            pattern_name = f"contact_format_{len(new_patterns)}"
                            generalized = re.sub(r'\d', '\\d', item)
                            new_patterns[pattern_name] = f"(?:tel|téléphone|contact|appel)[:\\s]*({generalized})"
                    
                    elif category == 'nouvelles_zones':
                        # Zones avec contexte géographique
                        if len(item) >= 4 and item.isalpha():  # Noms de lieux valides
                            if 'zone_geographique' in self.existing_patterns:
                                current_zones = self.existing_patterns['zone_geographique']
                                if item.lower() not in current_zones.lower():
                                    new_zones = current_zones.rstrip(')') + f"|{item.lower()})"
                                    new_patterns['zone_geographique'] = new_zones
                    
                    elif category == 'nouveaux_delais':
                        # Délais avec contexte temporel complet
                        if 'avant' in item.lower() or 'après' in item.lower() or 'commande' in item.lower():
                            pattern_name = f"condition_temporelle_{len(new_patterns)}"
                            new_patterns[pattern_name] = re.escape(item)
                        elif len(item.split()) >= 3:  # Phrases complètes seulement
                            pattern_name = f"delai_contextuel_{len(new_patterns)}"
                            new_patterns[pattern_name] = re.escape(item)
                    
                    elif category == 'nouvelles_marques':
                        # Marques avec contexte métier
                        if len(item) >= 3 and not item.isdigit():
                            pattern_name = f"marque_{item.lower().replace(' ', '_')[:15]}"
                            new_patterns[pattern_name] = f"(?:marque|brand|fabricant)[:\\s]*({re.escape(item)})"
                    
                    elif category == 'nouveaux_produits':
                        # Produits avec contexte descriptif
                        if len(item) >= 5 and len(item.split()) >= 2:
                            pattern_name = f"produit_{item.lower().replace(' ', '_')[:15]}"
                            new_patterns[pattern_name] = f"(?:produit|article|item)[:\\s]*({re.escape(item)})"
                    
                    elif category == 'nouvelles_conditions':
                        # Conditions avec contexte contractuel complet
                        if len(item) >= 10 and ('condition' in item.lower() or 'exigé' in item.lower()):
                            pattern_name = f"condition_contractuelle_{len(new_patterns)}"
                            new_patterns[pattern_name] = re.escape(item)
                    
                    elif category == 'nouveaux_horaires':
                        # Horaires avec contexte temporel complet
                        if ('ouvert' in item.lower() or 'fermé' in item.lower() or 
                            'horaire' in item.lower() or '→' in item or '-' in item):
                            pattern_name = f"horaire_contextuel_{len(new_patterns)}"
                            new_patterns[pattern_name] = re.escape(item)
                    
                    elif category == 'nouvelles_adresses':
                        # Adresses avec contexte géographique complet
                        if len(item) >= 15 and any(word in item.lower() for word in ['rue', 'avenue', 'boulevard', 'quartier']):
                            pattern_name = f"adresse_complete_{len(new_patterns)}"
                            new_patterns[pattern_name] = f"(?:adresse|située?|localisée?)[:\\s]*({re.escape(item)})"
        
        return new_patterns
    
    def _is_contextually_safe_pattern(self, item: str, category: str) -> bool:
        """Vérifie si un pattern est contextuellement sûr et non ambigu"""
        
        # Patterns trop courts (risque d'ambiguïté)
        if len(item.strip()) < 3:
            return False
        
        # Patterns uniquement numériques (très ambigus)
        if item.strip().isdigit():
            return False
        
        # Heures isolées (comme "11h" sans contexte)
        if re.match(r'^\d{1,2}h\d{0,2}?$', item.strip()):
            return False
        
        # Mots trop génériques
        generic_words = ['le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'à', 'en', 'sur', 'pour']
        if item.lower().strip() in generic_words:
            return False
        
        # Validation spécifique par catégorie
        if category == 'nouveaux_delais':
            # Accepter seulement les délais avec contexte
            return any(word in item.lower() for word in ['avant', 'après', 'commande', 'livraison', 'jour', 'heure', '→'])
        
        elif category == 'nouveaux_montants':
            # Montants avec devise explicite
            return any(symbol in item for symbol in ['€', '$', 'FCFA', 'EUR', 'USD'])
        
        elif category == 'nouvelles_zones':
            # Noms de lieux valides (pas de chiffres)
            return len(item) >= 4 and not any(char.isdigit() for char in item)
        
        elif category == 'nouveaux_contacts':
            # Numéros de téléphone complets
            return len(re.sub(r'[^\d]', '', item)) >= 8
        
        elif category == 'nouvelles_conditions':
            # Conditions avec mots-clés métier
            return any(word in item.lower() for word in ['condition', 'exigé', 'requis', 'obligatoire', 'nécessaire'])
        
        return True
    
    def _is_high_confidence_pattern(self, item: str, category: str) -> bool:
        """Détermine si un pattern est de haute confiance même avec peu d'occurrences"""
        high_confidence_indicators = {
            'nouveaux_montants': ['€', '$', 'EUR', 'USD'],
            'nouveaux_contacts': ['+', 'tel', 'phone'],
            'nouvelles_zones': ['ville', 'quartier', 'commune'],
            'nouveaux_delais': ['h', 'min', 'jour', 'semaine'],
            'nouvelles_marques': ['®', '™', 'Ltd', 'Inc'],
        }
        
        indicators = high_confidence_indicators.get(category, [])
        return any(indicator in item for indicator in indicators)
    
    def learn_from_documents(self, documents: List[Dict]) -> int:
        """Processus complet d'apprentissage à partir de documents"""
        print(f"🧠 Apprentissage automatique sur {len(documents)} documents...")
        
        # Détecter les patterns potentiels
        detected = self.detect_potential_patterns(documents)
        
        # Générer les nouveaux patterns regex
        new_patterns = self.generate_regex_patterns(detected)
        
        if new_patterns:
            print(f"🎯 {len(new_patterns)} nouveaux patterns détectés:")
            for name, pattern in new_patterns.items():
                print(f"   • {name}: {pattern}")
            
            # Sauvegarder les nouveaux patterns
            self._save_patterns(new_patterns)
            
            # Mettre à jour les patterns existants
            self.existing_patterns.update(new_patterns)
            
            return len(new_patterns)
        else:
            print("ℹ️  Aucun nouveau pattern détecté")
            return 0

def auto_learn_patterns(documents: List[Dict], patterns_file_path: str) -> int:
    """Fonction utilitaire pour l'apprentissage automatique"""
    learner = DynamicPatternLearner(patterns_file_path)
    return learner.learn_from_documents(documents)
