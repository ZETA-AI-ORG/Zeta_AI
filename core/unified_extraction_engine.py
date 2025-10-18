#!/usr/bin/env python3
"""
🚀 MOTEUR D'EXTRACTION UNIFIÉ - NIVEAU ENTERPRISE
Combine tous les extracteurs pour une extraction multi-niveaux optimale

Modules intégrés:
1. ConceptExtractor - 43 couleurs, 25+ communes, patterns métier
2. ProductAttributeExtractor - Extraction dynamique depuis MeiliSearch
3. RAGRegexExtractor - Patterns JSON + auto-apprentissage
4. FrenchNLPProcessor - Normalisation, lemmatisation, NER
5. AdvancedIntentClassifier - Classification multi-classe
6. SmartMetadataExtractor - Extraction produits, zones, téléphones
7. DeliveryZoneExtractor - Zones Abidjan + calcul frais
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATACLASSES RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExtractionResult:
    """Résultat complet d'extraction multi-niveaux"""
    # Niveau 1: NLP Processing
    normalized_text: str
    lemmatized_words: List[str]
    corrected_text: str
    
    # Niveau 2: Intent Classification
    primary_intent: str
    intent_confidence: float
    all_intents: Dict[str, float]
    requires_documents: bool
    
    # Niveau 3: Concept Extraction
    concepts: Dict[str, List[str]]  # {category: [values]}
    
    # Niveau 4: Smart Metadata
    products: List[str]
    zones: List[str]
    phones: List[str]
    prices: List[float]
    payment_methods: List[str]
    
    # Niveau 5: Regex Entities
    regex_entities: Dict[str, List[str]]
    
    # Niveau 6: Product Attributes (si contexte fourni)
    product_attributes: Dict[str, str]
    
    # Niveau 7: Delivery Info
    delivery_zone: Optional[str]
    delivery_cost: Optional[int]
    delivery_type: Optional[str]  # centre/périphérie
    
    # Métadonnées
    extraction_time_ms: float
    confidence_score: float
    warnings: List[str]

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedExtractionEngine:
    """
    🚀 MOTEUR D'EXTRACTION UNIFIÉ ENTERPRISE
    
    Combine 7 niveaux d'extraction pour une analyse complète:
    1. NLP Processing (normalisation, lemmatisation)
    2. Intent Classification (multi-classe avec confiance)
    3. Concept Extraction (couleurs, communes, patterns métier)
    4. Smart Metadata (produits, zones, téléphones, prix)
    5. Regex Entities (acompte, IBAN, dates, emails)
    6. Product Attributes (extraction dynamique MeiliSearch)
    7. Delivery Info (zones Abidjan + frais)
    """
    
    def __init__(self, config=None):
        """
        Initialise tous les extracteurs
        
        Args:
            config: ExtractionConfig optionnel (sinon utilise config globale)
        """
        from core.extraction_config import get_extraction_config
        self.config = config or get_extraction_config()
        self._init_extractors()
        logger.info(f"🚀 [UNIFIED_EXTRACTION] Moteur initialisé\n{self.config}")
    
    def _init_extractors(self):
        """Initialise tous les modules d'extraction"""
        # Niveau 1: NLP Processor
        if self.config.enable_nlp_processor:
            try:
                from core.french_nlp_processor import FrenchNLPProcessor
                self.nlp_processor = FrenchNLPProcessor()
                logger.info("✅ [LEVEL 1] FrenchNLPProcessor chargé")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 1] FrenchNLPProcessor non disponible: {e}")
                self.nlp_processor = None
        else:
            self.nlp_processor = None
            logger.info("⏭️ [LEVEL 1] FrenchNLPProcessor désactivé (config)")
        
        # Niveau 2: Intent Classifier
        if self.config.enable_intent_classifier:
            try:
                from core.advanced_intent_classifier import AdvancedIntentClassifier
                self.intent_classifier = AdvancedIntentClassifier()
                logger.info("✅ [LEVEL 2] AdvancedIntentClassifier chargé")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 2] AdvancedIntentClassifier non disponible: {e}")
                self.intent_classifier = None
        else:
            self.intent_classifier = None
            logger.info("⏭️ [LEVEL 2] AdvancedIntentClassifier désactivé (config)")
        
        # Niveau 3: Concept Extractor
        if self.config.enable_concept_extractor:
            try:
                from core.concept_extractor import ConceptExtractor
                self.concept_extractor = ConceptExtractor()
                logger.info("✅ [LEVEL 3] ConceptExtractor chargé (43 couleurs, 25+ communes)")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 3] ConceptExtractor non disponible: {e}")
                self.concept_extractor = None
        else:
            self.concept_extractor = None
            logger.info("⏭️ [LEVEL 3] ConceptExtractor désactivé (config)")
        
        # Niveau 4: Smart Metadata Extractor
        if self.config.enable_smart_metadata:
            try:
                from core.smart_metadata_extractor import extract_all_metadata
                self.smart_metadata_extractor = extract_all_metadata
                logger.info("✅ [LEVEL 4] SmartMetadataExtractor chargé")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 4] SmartMetadataExtractor non disponible: {e}")
                self.smart_metadata_extractor = None
        else:
            self.smart_metadata_extractor = None
            logger.info("⏭️ [LEVEL 4] SmartMetadataExtractor désactivé (config)")
        
        # Niveau 5: RAG Regex Extractor
        if self.config.enable_regex_extractor:
            try:
                from core.rag_regex_extractor import extract_regex_entities_from_docs
                self.regex_extractor = extract_regex_entities_from_docs
                logger.info("✅ [LEVEL 5] RAGRegexExtractor chargé (auto-apprentissage)")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 5] RAGRegexExtractor non disponible: {e}")
                self.regex_extractor = None
        else:
            self.regex_extractor = None
            logger.info("⏭️ [LEVEL 5] RAGRegexExtractor désactivé (config)")
        
        # Niveau 6: Product Attribute Extractor
        if self.config.enable_product_attributes:
            try:
                from core.product_attribute_extractor import extract_product_attributes
                self.product_attr_extractor = extract_product_attributes
                logger.info("✅ [LEVEL 6] ProductAttributeExtractor chargé")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 6] ProductAttributeExtractor non disponible: {e}")
                self.product_attr_extractor = None
        else:
            self.product_attr_extractor = None
            logger.info("⏭️ [LEVEL 6] ProductAttributeExtractor désactivé (config)")
        
        # Niveau 7: Delivery Zone Extractor
        if self.config.enable_delivery_extractor:
            try:
                from core.delivery_zone_extractor import extract_delivery_zone_and_cost
                self.delivery_extractor = extract_delivery_zone_and_cost
                logger.info("✅ [LEVEL 7] DeliveryZoneExtractor chargé (25+ communes Abidjan)")
            except Exception as e:
                logger.warning(f"⚠️ [LEVEL 7] DeliveryZoneExtractor non disponible: {e}")
                self.delivery_extractor = None
        else:
            self.delivery_extractor = None
            logger.info("⏭️ [LEVEL 7] DeliveryZoneExtractor désactivé (config)")
    
    async def extract_all(
        self, 
        message: str, 
        context: str = "", 
        company_id: str = None
    ) -> ExtractionResult:
        """
        Extraction complète multi-niveaux
        
        Args:
            message: Message utilisateur à analyser
            context: Contexte additionnel (documents RAG, historique)
            company_id: ID entreprise pour extraction attributs dynamiques
        
        Returns:
            ExtractionResult avec toutes les données extraites
        """
        import time
        start_time = time.time()
        warnings = []
        
        logger.info(f"🔍 [UNIFIED] Extraction multi-niveaux: '{message[:50]}...'")
        
        # ═══ NIVEAU 1: NLP PROCESSING ═══
        normalized_text = message
        lemmatized_words = []
        corrected_text = message
        
        if self.nlp_processor:
            try:
                nlp_result = self.nlp_processor.process(message)
                normalized_text = nlp_result.normalized
                lemmatized_words = nlp_result.lemmatized_words
                corrected_text = nlp_result.corrected
                logger.debug(f"✅ [L1] NLP: {len(lemmatized_words)} mots lemmatisés")
            except Exception as e:
                logger.error(f"❌ [L1] NLP erreur: {e}")
                warnings.append(f"NLP: {str(e)}")
        
        # ═══ NIVEAU 2: INTENT CLASSIFICATION ═══
        primary_intent = "unknown"
        intent_confidence = 0.0
        all_intents = {}
        requires_documents = True
        
        if self.intent_classifier:
            try:
                intent_result = await self.intent_classifier.classify(message, context)
                primary_intent = intent_result.primary_intent.value
                intent_confidence = intent_result.confidence
                all_intents = {k.value: v for k, v in intent_result.all_intents.items()}
                requires_documents = intent_result.requires_documents
                logger.debug(f"✅ [L2] Intent: {primary_intent} ({intent_confidence:.2f})")
            except Exception as e:
                logger.error(f"❌ [L2] Intent erreur: {e}")
                warnings.append(f"Intent: {str(e)}")
        
        # ═══ NIVEAU 3: CONCEPT EXTRACTION ═══
        concepts = {}
        
        if self.concept_extractor:
            try:
                concepts = self.concept_extractor.extract_concepts(message)
                logger.debug(f"✅ [L3] Concepts: {len(concepts)} catégories")
            except Exception as e:
                logger.error(f"❌ [L3] Concepts erreur: {e}")
                warnings.append(f"Concepts: {str(e)}")
        
        # ═══ NIVEAU 4: SMART METADATA ═══
        products = []
        zones = []
        phones = []
        prices = []
        payment_methods = []
        
        if self.smart_metadata_extractor:
            try:
                metadata = self.smart_metadata_extractor(message)
                products = metadata.get('products', [])
                zones = metadata.get('zones', [])
                phones = metadata.get('phones', [])
                prices = metadata.get('prices', [])
                payment_methods = metadata.get('payment_methods', [])
                logger.debug(f"✅ [L4] Metadata: {len(products)} produits, {len(zones)} zones")
            except Exception as e:
                logger.error(f"❌ [L4] Metadata erreur: {e}")
                warnings.append(f"Metadata: {str(e)}")
        
        # ═══ NIVEAU 5: REGEX ENTITIES ═══
        regex_entities = {}
        
        if self.regex_extractor:
            try:
                docs = [{'content': message}]
                if context:
                    docs.append({'content': context})
                regex_entities = self.regex_extractor(docs, enable_learning=False)
                logger.debug(f"✅ [L5] Regex: {len(regex_entities)} types d'entités")
            except Exception as e:
                logger.error(f"❌ [L5] Regex erreur: {e}")
                warnings.append(f"Regex: {str(e)}")
        
        # ═══ NIVEAU 6: PRODUCT ATTRIBUTES ═══
        product_attributes = {}
        
        if self.product_attr_extractor and context:
            try:
                # Attributs standards e-commerce
                attrs = [
                    'nom_produit', 'prix', 'taille', 'couleur', 'stock',
                    'catégorie', 'sous_catégorie', 'description', 'quantité'
                ]
                product_attributes = self.product_attr_extractor(context, attrs)
                logger.debug(f"✅ [L6] Attributs: {len(product_attributes)} extraits")
            except Exception as e:
                logger.error(f"❌ [L6] Attributs erreur: {e}")
                warnings.append(f"Attributs: {str(e)}")
        
        # ═══ NIVEAU 7: DELIVERY INFO ═══
        delivery_zone = None
        delivery_cost = None
        delivery_type = None
        
        if self.delivery_extractor:
            try:
                delivery_info = self.delivery_extractor(message)
                if delivery_info:
                    delivery_zone = delivery_info.get('zone')
                    delivery_cost = delivery_info.get('cost')
                    delivery_type = delivery_info.get('type')
                    logger.debug(f"✅ [L7] Livraison: {delivery_zone} ({delivery_cost} FCFA)")
            except Exception as e:
                logger.error(f"❌ [L7] Livraison erreur: {e}")
                warnings.append(f"Livraison: {str(e)}")
        
        # ═══ CALCUL SCORE DE CONFIANCE GLOBAL ═══
        confidence_score = self._calculate_confidence(
            intent_confidence,
            len(products) > 0,
            len(zones) > 0,
            len(phones) > 0,
            delivery_zone is not None
        )
        
        extraction_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"✅ [UNIFIED] Extraction terminée en {extraction_time_ms:.0f}ms (confiance: {confidence_score:.2f})")
        
        return ExtractionResult(
            normalized_text=normalized_text,
            lemmatized_words=lemmatized_words,
            corrected_text=corrected_text,
            primary_intent=primary_intent,
            intent_confidence=intent_confidence,
            all_intents=all_intents,
            requires_documents=requires_documents,
            concepts=concepts,
            products=products,
            zones=zones,
            phones=phones,
            prices=prices,
            payment_methods=payment_methods,
            regex_entities=regex_entities,
            product_attributes=product_attributes,
            delivery_zone=delivery_zone,
            delivery_cost=delivery_cost,
            delivery_type=delivery_type,
            extraction_time_ms=extraction_time_ms,
            confidence_score=confidence_score,
            warnings=warnings
        )
    
    def _calculate_confidence(
        self,
        intent_conf: float,
        has_products: bool,
        has_zones: bool,
        has_phones: bool,
        has_delivery: bool
    ) -> float:
        """Calcule un score de confiance global"""
        # Pondération: intent 40%, données extraites 60%
        intent_score = intent_conf * 0.4
        
        data_score = 0.0
        if has_products:
            data_score += 0.2
        if has_zones:
            data_score += 0.15
        if has_phones:
            data_score += 0.15
        if has_delivery:
            data_score += 0.1
        
        return min(1.0, intent_score + data_score)
    
    def extract_sync(
        self, 
        message: str, 
        context: str = "", 
        company_id: str = None
    ) -> ExtractionResult:
        """Version synchrone de extract_all"""
        return asyncio.run(self.extract_all(message, context, company_id))
    
    def to_dict(self, result: ExtractionResult) -> Dict[str, Any]:
        """Convertit ExtractionResult en dictionnaire"""
        return asdict(result)
    
    def format_for_llm(self, result: ExtractionResult) -> str:
        """Formate le résultat pour injection dans prompt LLM"""
        lines = []
        lines.append("🔍 EXTRACTION AUTOMATIQUE:")
        
        if result.products:
            lines.append(f"📦 Produits détectés: {', '.join(result.products)}")
        
        if result.zones:
            lines.append(f"📍 Zones détectées: {', '.join(result.zones)}")
        
        if result.delivery_zone:
            lines.append(f"🚚 Livraison: {result.delivery_zone} ({result.delivery_cost} FCFA)")
        
        if result.phones:
            lines.append(f"📞 Téléphones: {', '.join(result.phones)}")
        
        if result.prices:
            prices_str = ', '.join([f"{p:.0f} FCFA" for p in result.prices])
            lines.append(f"💰 Prix détectés: {prices_str}")
        
        if result.payment_methods:
            lines.append(f"💳 Paiement: {', '.join(result.payment_methods)}")
        
        lines.append(f"🎯 Intention: {result.primary_intent} (confiance: {result.intent_confidence:.0%})")
        lines.append(f"✅ Score global: {result.confidence_score:.0%}")
        
        return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 INSTANCE GLOBALE (SINGLETON)
# ═══════════════════════════════════════════════════════════════════════════════

_unified_engine = None

def get_unified_extraction_engine() -> UnifiedExtractionEngine:
    """Retourne l'instance singleton du moteur d'extraction"""
    global _unified_engine
    if _unified_engine is None:
        _unified_engine = UnifiedExtractionEngine()
    return _unified_engine

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    async def test_extraction():
        """Test du moteur d'extraction"""
        engine = get_unified_extraction_engine()
        
        # Test 1: Commande produit
        print("\n" + "="*80)
        print("🧪 TEST 1: Commande produit")
        print("="*80)
        
        result = await engine.extract_all(
            "Je veux le lot 150 de couches culottes taille 4 à Cocody, mon numéro est 0160924560"
        )
        
        print(f"\n📊 Résultats:")
        print(f"  - Produits: {result.products}")
        print(f"  - Zones: {result.zones}")
        print(f"  - Téléphones: {result.phones}")
        print(f"  - Livraison: {result.delivery_zone} ({result.delivery_cost} FCFA)")
        print(f"  - Intention: {result.primary_intent} ({result.intent_confidence:.0%})")
        print(f"  - Confiance: {result.confidence_score:.0%}")
        print(f"  - Temps: {result.extraction_time_ms:.0f}ms")
        
        print(f"\n📝 Format LLM:")
        print(engine.format_for_llm(result))
        
        # Test 2: Question prix
        print("\n" + "="*80)
        print("🧪 TEST 2: Question prix")
        print("="*80)
        
        result2 = await engine.extract_all(
            "Combien coûte la livraison à Yopougon ?"
        )
        
        print(f"\n📊 Résultats:")
        print(f"  - Zones: {result2.zones}")
        print(f"  - Livraison: {result2.delivery_zone} ({result2.delivery_cost} FCFA)")
        print(f"  - Intention: {result2.primary_intent} ({result2.intent_confidence:.0%})")
        print(f"  - Confiance: {result2.confidence_score:.0%}")
        
        print(f"\n📝 Format LLM:")
        print(engine.format_for_llm(result2))
    
    asyncio.run(test_extraction())
