"""
🎯 ROUTEUR D'INTENTIONS E-COMMERCE
Détecte automatiquement l'intention de l'utilisateur pour optimiser la recherche RAG
"""

import re
import os
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class IntentionResult:
    intentions: Dict[str, Dict]
    primary: str
    is_multi_intent: bool
    confidence_score: float

class IntentionRouter:
    """
    Routeur d'intentions basé sur mots-clés pour e-commerce
    Supporte les 4 domaines principaux + fallback intelligent
    """
    
    def __init__(self):
        self.intention_keywords = {
            "delivery": {
                "keywords": [
                    # Livraison de base
                    "livraison", "expedition", "envoi", "transport", "colis", "paquet",
                    "frais", "gratuit", "delai", "temps", "quand", "combien temps",
                    "reception", "arrive", "arriver", "shipping", "delivery",
                    
                    # Types de livraison
                    "express", "standard", "rapide", "urgent", "chronopost", 
                    "colissimo", "mondial relay", "point relais", "domicile",
                    
                    # Suivi
                    "suivi", "tracking", "numero", "suivre", "ou est", "statut"
                ],
                "meili_index_suffix": "delivery",
                "weight": 1.0
            },
            
            "product_catalog": {
                "keywords": [
                    # Prix et coûts
                    "prix", "cout", "tarif", "combien", "cher", "euros", "euro",
                    "promotion", "promo", "reduction", "solde", "remise",
                    
                    # Produits généraux
                    "produit", "article", "reference", "modele", "marque", "brand",
                    "casque", "moto", "equipement", "accessoire", "piece",
                    
                    # Produits bébé & puériculture (AJOUT ESSENTIEL)
                    "couches", "culottes", "bebe", "enfant", "nourrisson", "bambin",
                    "pression", "lingettes", "biberon", "tetine", "poussette", "landau",
                    "siege-auto", "gigoteuse", "body", "pyjama", "chaussons",
                    
                    # Caractéristiques
                    "couleur", "taille", "dimension", "poids", "materiau",
                    "caracteristiques", "details", "specification", "fiche",
                    "absorption", "confort", "douceur", "hypoallergenique",
                    
                    # Stock et disponibilité
                    "stock", "disponible", "rupture", "dispo", "en stock",
                    "image", "photo", "voir", "montrer"
                ],
                "meili_index_suffix": "products", 
                "weight": 1.2  # Priorité légèrement plus élevée
            },
            
            "company_identity": {
                "keywords": [
                    # Localisation
                    "boutique", "magasin", "entreprise", "societe", "qui etes vous",
                    "adresse", "ou", "localise", "trouve", "situe", "emplacement",
                    
                    # Contact et horaires
                    "horaires", "ouvert", "ferme", "contact", "telephone", "tel",
                    "email", "mail", "joindre", "contacter",
                    
                    # Type de commerce
                    "physique", "ligne", "local", "showroom", "atelier",
                    "visite", "venir", "rendez-vous"
                ],
                "meili_index_suffix": "company",
                "weight": 0.9
            },
            
            "support": {
                "keywords": [
                    # Support technique
                    "probleme", "bug", "erreur", "aide", "support", "sav",
                    "marche pas", "fonctionne pas", "casse", "defectueux",
                    
                    # Retours et garanties
                    "retour", "remboursement", "garantie", "reclamer", "echanger",
                    "rendre", "insatisfait", "defaut",
                    
                    # Paiement et méthodes (COMPLET AFRIQUE/FRANCE)
                    "paiement", "payer", "payez", "payer en ligne", "carte",
                    "visa", "mastercard", "moov", "mtn", "orange money",
                    "wave", "transfert", "bancaire", "virement", "compte",
                    "transaction", "echec", "erreur", "refuse", "annuler",
                    "remboursement", "litige", "facture", "recu", "confirmation",
                    "paiement à la livraison", "paiement sur place", "payer au depot",
                    "dépôt de validation", "dépot de confirmation", "paiement en espèce",
                    "liquide", "cash", "paypal", "cheque", "cb", "especes", 
                    "facilite", "echeance", "credit", "financement", "acompte",
                    
                    # Instructions d'usage
                    "comment", "utiliser", "installer", "configurer", "mode emploi",
                    "notice", "manuel", "tuto", "tutoriel"
                ],
                "meili_index_suffix": "support",
                "weight": 0.8
            }
        }
        
        # Mots parasites à ignorer dans la détection
        self.ignore_words = {
            "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cette",
            "je", "tu", "il", "nous", "vous", "ils", "mon", "ma", "mes",
            "est", "sont", "avoir", "etre", "faire", "aller", "venir",
            "bonjour", "salut", "merci", "svp", "sil vous plait"
        }
    
    def detect_intentions(self, query: str) -> IntentionResult:
        """
        Détecte toutes les intentions dans une requête avec scoring
        
        Args:
            query: Requête utilisateur
            
        Returns:
            IntentionResult avec intentions détectées et scores
        """
        if not query or len(query.strip()) < 3:
            return IntentionResult({}, None, False, 0.0)
        
        # Nettoyage et préparation
        clean_query = self._clean_query(query)
        query_words = set(clean_query.lower().split())
        
        # Suppression des mots parasites
        query_words = query_words - self.ignore_words
        
        detected_intentions = {}
        
        # Détection pour chaque intention
        for intention, config in self.intention_keywords.items():
            matches = query_words.intersection(set(config["keywords"]))
            
            if len(matches) >= 1:  # Seuil minimum : 1 mot-clé (ajustable)
                score = len(matches) * config["weight"]
                confidence = len(matches) / max(len(query_words), 1)
                
                detected_intentions[intention] = {
                    "score": score,
                    "matched_keywords": list(matches),
                    "confidence": confidence,
                    "meili_index": config["meili_index_suffix"]
                }
        
        # Tri par score décroissant
        sorted_intentions = dict(sorted(
            detected_intentions.items(), 
            key=lambda x: x[1]["score"], 
            reverse=True
        ))
        
        # Calcul du score de confiance global
        total_score = sum(intent["score"] for intent in sorted_intentions.values())
        global_confidence = min(total_score / len(query_words), 1.0) if query_words else 0.0
        
        # Logs de debug
        if os.getenv("DEBUG_INTENTIONS") == "1":
            print(f"[INTENTION_ROUTER] Query: '{query}'")
            print(f"[INTENTION_ROUTER] Detected: {list(sorted_intentions.keys())}")
            print(f"[INTENTION_ROUTER] Confidence: {global_confidence:.2f}")
        
        return IntentionResult(
            intentions=sorted_intentions,
            primary=list(sorted_intentions.keys())[0] if sorted_intentions else None,
            is_multi_intent=len(sorted_intentions) > 1,
            confidence_score=global_confidence
        )
    
    def _clean_query(self, query: str) -> str:
        """Nettoie la requête des caractères spéciaux"""
        # Suppression des caractères spéciaux sauf espaces et lettres
        cleaned = re.sub(r'[^\w\s]', ' ', query)
        # Suppression des espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    def get_target_indexes(self, company_id: str, intentions: IntentionResult) -> List[str]:
        """
        Retourne la liste des index MeiliSearch à interroger
        
        Args:
            company_id: ID de l'entreprise
            intentions: Résultat de la détection d'intentions
            
        Returns:
            Liste des index MeiliSearch à interroger
        """
        if not intentions.intentions:
            # Fallback sur l'index général
            return [f"company_docs_{company_id}"]
        
        indexes = []
        for intention, config in intentions.intentions.items():
            index_name = f"{config['meili_index']}_{company_id}"
            indexes.append(index_name)
        
        # Toujours ajouter l'index général en fallback
        general_index = f"company_docs_{company_id}"
        if general_index not in indexes:
            indexes.append(general_index)
        
        return indexes
    
    def should_use_specialized_hyde(self, intentions: IntentionResult) -> bool:
        """
        Détermine si on doit utiliser un HyDE spécialisé
        
        Args:
            intentions: Résultat de la détection d'intentions
            
        Returns:
            True si HyDE spécialisé recommandé
        """
        return (
            intentions.primary is not None and
            intentions.confidence_score > 0.3 and
            len(intentions.intentions) <= 2  # Max 2 intentions pour rester précis
        )

# Instance globale pour import facile
intention_router = IntentionRouter()
