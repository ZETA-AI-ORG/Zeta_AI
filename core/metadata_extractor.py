import re
from typing import Dict, List, Set
from utils import log3

class MetadataExtractor:
    """
    Extracteur automatique de mots critiques depuis les métadonnées d'entreprise
    Système scalable basé sur les clés métadonnées → scores prédéterminés
    """
    
    def __init__(self):
        # Mapping métadonnées → scores prédéterminés
        self.metadata_score_mapping = {
            # SCORE 10 - CRITIQUES BUSINESS
            "product_name": 10,     # "CASQUES MOTO" → casques:10, moto:10
            "price": 10,            # Toujours critique
            "currency": 10,         # "FCFA" → fcfa:10
            
            # SCORE 9 - TRÈS PERTINENTS  
            "category": 9,          # "Auto & Moto" → auto:9, moto:9
            "subcategory": 9,       # "Casques & Équipement Moto"
            "zone": 9,              # "Yopougon" → yopougon:9
            "method": 9,            # "Wave" → wave:9
            "ai_name": 9,           # "jessica" → jessica:9
            
            # SCORE 8 - PERTINENTS
            "zone_group": 8,        # Zones périphérie
            "sector": 8,            # "Auto & Moto"
            "channels": 8,          # "phone", "whatsapp"
            "name": 8,              # company name
            "tags": 8,              # Tags produit
        }
        
        # Score par défaut pour tous les variants = 8 (PERTINENTS)
        # Plus simple et scalable pour gérer tous les types d'attributs
        self.default_variant_score = 8
        
        # Mapping spécial pour quelques cas critiques seulement
        self.attribute_score_mapping = {
            # SCORE 10 - CRITIQUES VISUELS (couleurs restent prioritaires)
            "color": 10,
            "couleur": 10,
            
            # SCORE 9 - MARQUES (très pertinentes)
            "brand": 9,
            "marque": 9,
            
            # Tous les autres variants = score 8 par défaut
        }
        
        # Stop words pour filtrage
        self.stop_words = {
            "le", "la", "les", "un", "une", "des", "du", "de", "d'", "à", "au", "aux",
            "en", "dans", "sur", "avec", "sans", "pour", "par", "et", "ou", "mais",
            "que", "qui", "dont", "où", "ce", "cet", "cette", "ces", "est", "sont"
        }
    
    def extract_from_company_data(self, company_data: List[Dict]) -> Dict[int, Set[str]]:
        """
        Extrait automatiquement les mots critiques depuis les données d'entreprise
        
        Returns:
            Dict[int, Set[str]]: {10: {mots_score_10}, 9: {mots_score_9}, 8: {mots_score_8}}
        """
        dynamic_words = {10: set(), 9: set(), 8: set(), 7: set()}
        
        log3("[METADATA_EXTRACTOR]", "Début extraction automatique des mots...")
        
        for company in company_data:
            for doc in company.get("text_documents", []):
                metadata = doc.get("metadata", {})
                
                # Parcourir chaque clé de métadonnée
                for key, value in metadata.items():
                    if key in self.metadata_score_mapping:
                        score = self.metadata_score_mapping[key]
                        words = self._extract_words_from_value(value)
                        
                        if words:  # Seulement si des mots ont été extraits
                            dynamic_words[score].update(words)
                            log3("[METADATA_EXTRACTOR]", 
                                f"'{key}': '{value}' → {words} (score {score})")
                
                # Gestion spéciale des variants (attributes_canonical, attribute_list)
                self._extract_from_variants(metadata, dynamic_words)
        
        # Logs de résumé
        total = sum(len(words) for words in dynamic_words.values())
        log3("[METADATA_EXTRACTOR]", f"Extraction terminée: {total} mots extraits")
        log3("[METADATA_EXTRACTOR]", f"  - Score 10: {len(dynamic_words[10])} mots")
        log3("[METADATA_EXTRACTOR]", f"  - Score 9: {len(dynamic_words[9])} mots")
        log3("[METADATA_EXTRACTOR]", f"  - Score 8: {len(dynamic_words[8])} mots")
        log3("[METADATA_EXTRACTOR]", f"  - Score 7: {len(dynamic_words[7])} mots")
        
        return dynamic_words
    
    def _extract_words_from_value(self, value) -> Set[str]:
        """
        Extrait les mots d'une valeur de métadonnée (string, list, dict, etc.)
        """
        words = set()
        
        if isinstance(value, str):
            extracted = self._clean_and_extract_words(value)
            words.update(extracted)
            
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    extracted = self._clean_and_extract_words(item)
                    words.update(extracted)
                    
        elif isinstance(value, dict):
            # Pour les attributs comme {"Couleur": "BLEU"}
            for v in value.values():
                if isinstance(v, str):
                    extracted = self._clean_and_extract_words(v)
                    words.update(extracted)
        
        return words
    
    def _clean_and_extract_words(self, text: str) -> Set[str]:
        """
        Nettoie et extrait les mots d'un texte
        """
        if not text:
            return set()
            
        # Nettoyer et normaliser
        text = text.lower().strip()
        text = re.sub(r'[^\w\s\-àâäéèêëïîôöùûüÿç]', ' ', text)
        
        # Extraire les mots
        words = [w.strip() for w in text.split() if w.strip()]
        
        # Filtrer les mots valides
        filtered_words = {
            word for word in words 
            if len(word) >= 3 
            and word not in self.stop_words
            and not self._is_numeric(word)
        }
        
        return filtered_words
    
    def _extract_from_variants(self, metadata: Dict, dynamic_words: Dict[int, Set[str]]):
        """
        Extrait intelligemment les mots depuis les variants produits
        Analyse attributes_canonical et attribute_list pour déterminer le type d'attribut
        """
        # Méthode 1: attribute_list (plus précise)
        if "attribute_list" in metadata:
            for attr in metadata["attribute_list"]:
                if isinstance(attr, dict) and "name" in attr and "value" in attr:
                    attr_name = attr["name"].lower()
                    attr_value = attr["value"]
                    
                    # Utiliser mapping spécial ou score par défaut
                    score = self.attribute_score_mapping.get(attr_name, self.default_variant_score)
                    words = self._clean_and_extract_words(str(attr_value))
                    
                    if words:
                        dynamic_words[score].update(words)
                        log3("[METADATA_EXTRACTOR]", 
                            f"Variant '{attr_name}': '{attr_value}' → {words} (score {score})")
        
        # Méthode 2: attributes_canonical (fallback)
        elif "attributes_canonical" in metadata:
            for attr_name, attr_value in metadata["attributes_canonical"].items():
                attr_name_lower = attr_name.lower()
                
                # Utiliser mapping spécial ou score par défaut
                score = self.attribute_score_mapping.get(attr_name_lower, self.default_variant_score)
                words = self._clean_and_extract_words(str(attr_value))
                
                if words:
                    dynamic_words[score].update(words)
                    log3("[METADATA_EXTRACTOR]", 
                        f"Attribut '{attr_name}': '{attr_value}' → {words} (score {score})")
        
        # Méthode 3: variants array (structure alternative)
        if "variants" in metadata:
            for variant in metadata["variants"]:
                if isinstance(variant, dict):
                    # Traiter attributes_canonical dans chaque variant
                    if "attributes_canonical" in variant:
                        for attr_name, attr_value in variant["attributes_canonical"].items():
                            attr_name_lower = attr_name.lower()
                            
                            # Utiliser mapping spécial ou score par défaut
                            score = self.attribute_score_mapping.get(attr_name_lower, self.default_variant_score)
                            words = self._clean_and_extract_words(str(attr_value))
                            
                            if words:
                                dynamic_words[score].update(words)
                                log3("[METADATA_EXTRACTOR]", 
                                    f"Variant '{attr_name}': '{attr_value}' → {words} (score {score})")
    
    def _is_numeric(self, word: str) -> bool:
        """
        Vérifie si un mot est numérique
        """
        try:
            float(word.replace(',', '.'))
            return True
        except ValueError:
            return False


# Fonction utilitaire pour intégration facile
def extract_dynamic_words_from_company_data(company_data: List[Dict]) -> Dict[int, Set[str]]:
    """
    Fonction utilitaire pour extraire rapidement les mots dynamiques
    """
    extractor = MetadataExtractor()
    return extractor.extract_from_company_data(company_data)


# Test rapide
if __name__ == "__main__":
    # Exemple de données d'entreprise
    test_data = [{
        "text_documents": [{
            "metadata": {
                "product_name": "CASQUES MOTO",
                "color": "BLEU",
                "category": "Auto & Moto",
                "zone": "Yopougon",
                "method": "Wave"
            }
        }]
    }]
    
    extractor = MetadataExtractor()
    result = extractor.extract_from_company_data(test_data)
    
    print("=== RÉSULTATS EXTRACTION ===")
    for score, words in result.items():
        print(f"Score {score}: {words}")
