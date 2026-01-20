#!/usr/bin/env python3
"""
🎛️ CONFIGURATION EXTRACTION - FEATURE FLAGS
Permet d'activer/désactiver les modules d'extraction individuellement
"""

from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class ExtractionConfig:
    """Configuration des modules d'extraction"""
    
    # ═══ NIVEAU 1: NLP PROCESSING ═══
    enable_nlp_processor: bool = True  # ⚠️ DÉLICAT - Normalisation, lemmatisation
    
    # ═══ NIVEAU 2: INTENT CLASSIFICATION ═══
    enable_intent_classifier: bool = True  # ⚠️ DÉLICAT - Classification multi-classe
    
    # ═══ NIVEAU 3: CONCEPT EXTRACTION ═══
    enable_concept_extractor: bool = True  # ✅ STABLE - Couleurs, communes
    
    # ═══ NIVEAU 4: SMART METADATA ═══
    enable_smart_metadata: bool = True  # ✅ STABLE - Produits, zones, téléphones
    
    # ═══ NIVEAU 5: REGEX ENTITIES ═══
    enable_regex_extractor: bool = True  # ✅ STABLE - IBAN, dates, emails
    
    # ═══ NIVEAU 6: PRODUCT ATTRIBUTES ═══
    enable_product_attributes: bool = True  # ✅ STABLE - Extraction MeiliSearch
    
    # ═══ NIVEAU 7: DELIVERY INFO ═══
    enable_delivery_extractor: bool = True  # ✅ STABLE - Zones Abidjan
    
    # ═══ CONFIGURATION AVANCÉE ═══
    nlp_fallback_on_error: bool = True  # Si NLP échoue, continuer sans
    intent_fallback_on_error: bool = True  # Si Intent échoue, continuer sans
    
    @classmethod
    def from_env(cls) -> 'ExtractionConfig':
        """Charge la configuration depuis les variables d'environnement"""
        return cls(
            enable_nlp_processor=os.getenv('ENABLE_NLP_PROCESSOR', 'true').lower() == 'true',
            enable_intent_classifier=os.getenv('ENABLE_INTENT_CLASSIFIER', 'true').lower() == 'true',
            enable_concept_extractor=os.getenv('ENABLE_CONCEPT_EXTRACTOR', 'true').lower() == 'true',
            enable_smart_metadata=os.getenv('ENABLE_SMART_METADATA', 'true').lower() == 'true',
            enable_regex_extractor=os.getenv('ENABLE_REGEX_EXTRACTOR', 'true').lower() == 'true',
            enable_product_attributes=os.getenv('ENABLE_PRODUCT_ATTRIBUTES', 'true').lower() == 'true',
            enable_delivery_extractor=os.getenv('ENABLE_DELIVERY_EXTRACTOR', 'true').lower() == 'true',
            nlp_fallback_on_error=os.getenv('NLP_FALLBACK_ON_ERROR', 'true').lower() == 'true',
            intent_fallback_on_error=os.getenv('INTENT_FALLBACK_ON_ERROR', 'true').lower() == 'true',
        )
    
    @classmethod
    def safe_mode(cls) -> 'ExtractionConfig':
        """Configuration SAFE MODE - Désactive les modules délicats"""
        return cls(
            enable_nlp_processor=False,  # ❌ DÉSACTIVÉ
            enable_intent_classifier=False,  # ❌ DÉSACTIVÉ
            enable_concept_extractor=True,
            enable_smart_metadata=True,
            enable_regex_extractor=True,
            enable_product_attributes=True,
            enable_delivery_extractor=True,
        )
    
    @classmethod
    def minimal_mode(cls) -> 'ExtractionConfig':
        """Configuration MINIMALE - Seulement les extracteurs de base"""
        return cls(
            enable_nlp_processor=False,
            enable_intent_classifier=False,
            enable_concept_extractor=False,
            enable_smart_metadata=True,  # ✅ Essentiel
            enable_regex_extractor=True,  # ✅ Essentiel
            enable_product_attributes=False,
            enable_delivery_extractor=True,  # ✅ Essentiel
        )
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return {
            'nlp_processor': self.enable_nlp_processor,
            'intent_classifier': self.enable_intent_classifier,
            'concept_extractor': self.enable_concept_extractor,
            'smart_metadata': self.enable_smart_metadata,
            'regex_extractor': self.enable_regex_extractor,
            'product_attributes': self.enable_product_attributes,
            'delivery_extractor': self.enable_delivery_extractor,
        }
    
    def __str__(self) -> str:
        """Affichage lisible"""
        status = []
        status.append("🎛️ CONFIGURATION EXTRACTION:")
        status.append(f"  {'✅' if self.enable_nlp_processor else '❌'} NLP Processor")
        status.append(f"  {'✅' if self.enable_intent_classifier else '❌'} Intent Classifier")
        status.append(f"  {'✅' if self.enable_concept_extractor else '❌'} Concept Extractor")
        status.append(f"  {'✅' if self.enable_smart_metadata else '❌'} Smart Metadata")
        status.append(f"  {'✅' if self.enable_regex_extractor else '❌'} Regex Extractor")
        status.append(f"  {'✅' if self.enable_product_attributes else '❌'} Product Attributes")
        status.append(f"  {'✅' if self.enable_delivery_extractor else '❌'} Delivery Extractor")
        return "\n".join(status)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 INSTANCE GLOBALE
# ═══════════════════════════════════════════════════════════════════════════════

# Par défaut: tout activé
_global_config: Optional[ExtractionConfig] = None

def get_extraction_config() -> ExtractionConfig:
    """Retourne la configuration globale"""
    global _global_config
    if _global_config is None:
        _global_config = ExtractionConfig.from_env()
    return _global_config

def set_extraction_config(config: ExtractionConfig):
    """Définit la configuration globale"""
    global _global_config
    _global_config = config

def enable_safe_mode():
    """Active le mode SAFE (désactive NLP + Intent)"""
    set_extraction_config(ExtractionConfig.safe_mode())

def enable_minimal_mode():
    """Active le mode MINIMAL (seulement extracteurs de base)"""
    set_extraction_config(ExtractionConfig.minimal_mode())

def disable_nlp():
    """Désactive uniquement le NLP Processor"""
    config = get_extraction_config()
    config.enable_nlp_processor = False

def disable_intent_classifier():
    """Désactive uniquement l'Intent Classifier"""
    config = get_extraction_config()
    config.enable_intent_classifier = False


# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*80)
    print("🧪 TEST CONFIGURATION EXTRACTION")
    print("="*80)
    
    # Test 1: Configuration par défaut
    print("\n📊 Configuration par défaut:")
    config_default = ExtractionConfig()
    print(config_default)
    
    # Test 2: Safe Mode
    print("\n🛡️ Safe Mode (NLP + Intent désactivés):")
    config_safe = ExtractionConfig.safe_mode()
    print(config_safe)
    
    # Test 3: Minimal Mode
    print("\n⚡ Minimal Mode (seulement essentiels):")
    config_minimal = ExtractionConfig.minimal_mode()
    print(config_minimal)
    
    # Test 4: Variables d'environnement
    print("\n🌍 Configuration depuis ENV:")
    os.environ['ENABLE_NLP_PROCESSOR'] = 'false'
    os.environ['ENABLE_INTENT_CLASSIFIER'] = 'false'
    config_env = ExtractionConfig.from_env()
    print(config_env)
    
    # Test 5: Modification dynamique
    print("\n🔧 Modification dynamique:")
    set_extraction_config(ExtractionConfig())
    print("Avant:", get_extraction_config().enable_nlp_processor)
    disable_nlp()
    print("Après disable_nlp():", get_extraction_config().enable_nlp_processor)
