#!/usr/bin/env python3
"""
🧪 TESTS COMPLETS DU PIPELINE RAG FRANCOPHONE AVANCÉ
Tests de validation pour l'architecture complète avec métriques détaillées
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestCase:
    """Cas de test pour le pipeline avancé"""
    name: str
    query: str
    expected_intentions: List[str]
    expected_entities: List[str]
    expected_keywords: List[str]
    min_confidence: float
    description: str

@dataclass
class TestResult:
    """Résultat d'un test"""
    test_name: str
    success: bool
    response: str
    confidence: float
    processing_time_ms: float
    nlp_analysis: Dict[str, Any]
    fusion_metadata: Dict[str, Any]
    verification_result: Dict[str, Any]
    quality_score: float
    pipeline_stages: List[str]
    errors: List[str]

class AdvancedRAGTester:
    """
    🧪 TESTEUR COMPLET DU PIPELINE RAG AVANCÉ
    
    Valide :
    - Analyse NLP française
    - Recherche hybride
    - Fusion intelligente
    - Enrichissement prompt
    - Vérification QA
    - Performance globale
    """
    
    def __init__(self):
        self.company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
        self.user_id = "test_advanced_user"
        self.company_name = "Rue du Gros"
        
        # Cas de test stratégiques
        self.test_cases = [
            TestCase(
                name="Commande Simple",
                query="Je veux 2 paquets de couches taille 3",
                expected_intentions=["product_inquiry", "purchase_intent"],
                expected_entities=["2", "couches", "taille 3"],
                expected_keywords=["paquets", "couches", "taille"],
                min_confidence=0.7,
                description="Test commande basique avec quantité et taille"
            ),
            TestCase(
                name="Multi-Intentions Complexe",
                query="Bonjour, je veux 3 paquets couches taille 2 et combien pour livraison Cocody?",
                expected_intentions=["greeting", "product_inquiry", "delivery_inquiry", "price_inquiry"],
                expected_entities=["3", "couches", "taille 2", "Cocody"],
                expected_keywords=["paquets", "livraison", "combien"],
                min_confidence=0.8,
                description="Test multi-intentions avec salutation, produit, livraison et prix"
            ),
            TestCase(
                name="Requête avec Fautes",
                query="salut je veut des couchs rouge pour bebe taille 1 svp",
                expected_intentions=["greeting", "product_inquiry"],
                expected_entities=["couches", "rouge", "bébé", "taille 1"],
                expected_keywords=["couches", "rouge", "bébé"],
                min_confidence=0.6,
                description="Test correction orthographique et normalisation"
            ),
            TestCase(
                name="Contact et Support",
                query="Comment vous contacter par WhatsApp pour passer commande?",
                expected_intentions=["contact_inquiry", "support_request"],
                expected_entities=["WhatsApp", "commande"],
                expected_keywords=["contacter", "WhatsApp", "commande"],
                min_confidence=0.7,
                description="Test demande de contact et support"
            ),
            TestCase(
                name="Calcul Prix Complexe",
                query="Prix total pour 5 paquets couches culottes taille 4 plus livraison Yopougon?",
                expected_intentions=["price_inquiry", "calculation_request", "delivery_inquiry"],
                expected_entities=["5", "couches culottes", "taille 4", "Yopougon"],
                expected_keywords=["prix", "total", "livraison"],
                min_confidence=0.8,
                description="Test calcul prix avec livraison"
            ),
            TestCase(
                name="Disponibilité Stock",
                query="Avez-vous des couches adultes en stock? Quelle taille disponible?",
                expected_intentions=["stock_inquiry", "product_inquiry"],
                expected_entities=["couches adultes", "stock", "taille"],
                expected_keywords=["stock", "disponible", "taille"],
                min_confidence=0.7,
                description="Test vérification stock et disponibilité"
            ),
            TestCase(
                name="Paiement Wave",
                query="Je peux payer par Wave? Quel est le numéro?",
                expected_intentions=["payment_inquiry", "contact_inquiry"],
                expected_entities=["Wave", "numéro"],
                expected_keywords=["payer", "Wave", "numéro"],
                min_confidence=0.7,
                description="Test méthode de paiement Wave"
            ),
            TestCase(
                name="Requête Longue Conversationnelle",
                query="Bonsoir Jessica, j'espère que vous allez bien. Je suis intéressé par vos couches à pression pour mon bébé de 6 mois qui pèse environ 8kg. Pourriez-vous me conseiller la bonne taille et me dire combien coûtent 10 paquets avec livraison à Port-Bouët? Merci beaucoup.",
                expected_intentions=["greeting", "product_inquiry", "advice_request", "price_inquiry", "delivery_inquiry"],
                expected_entities=["Jessica", "couches à pression", "bébé", "6 mois", "8kg", "10", "Port-Bouët"],
                expected_keywords=["conseiller", "taille", "coûtent", "livraison"],
                min_confidence=0.8,
                description="Test requête conversationnelle longue et complexe"
            )
        ]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Exécute tous les tests et génère un rapport complet"""
        print(f"\n{'='*80}")
        print(f"🧪 TESTS PIPELINE RAG FRANCOPHONE AVANCÉ")
        print(f"{'='*80}")
        print(f"🏢 Company: {self.company_name} ({self.company_id})")
        print(f"👤 User: {self.user_id}")
        print(f"📊 Tests: {len(self.test_cases)} cas de test")
        print(f"{'='*80}")
        
        start_time = time.time()
        results = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n🔍 [TEST {i}/{len(self.test_cases)}] {test_case.name}")
            print(f"📝 Query: '{test_case.query}'")
            print(f"📋 Description: {test_case.description}")
            
            result = await self.run_single_test(test_case)
            results.append(result)
            
            # Affichage résultat immédiat
            status = "✅ SUCCÈS" if result.success else "❌ ÉCHEC"
            print(f"🎯 Résultat: {status}")
            print(f"📊 Confiance: {result.confidence:.2f}")
            print(f"⏱️ Temps: {result.processing_time_ms:.0f}ms")
            
            if result.quality_score:
                print(f"✅ Qualité: {result.quality_score:.2f}")
            
            if result.errors:
                print(f"❌ Erreurs: {', '.join(result.errors)}")
            
            print("-" * 60)
        
        total_time = time.time() - start_time
        
        # Génération du rapport final
        report = self.generate_report(results, total_time)
        
        # Affichage du rapport
        self.display_report(report)
        
        # Sauvegarde JSON
        await self.save_report(report)
        
        return report
    
    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Exécute un test individuel"""
        errors = []
        
        try:
            # Import du moteur avancé
            from core.universal_rag_engine_advanced import get_advanced_rag_response
            
            # Exécution du pipeline complet
            test_start = time.time()
            
            result = await get_advanced_rag_response(
                message=test_case.query,
                company_id=self.company_id,
                user_id=self.user_id,
                company_name=self.company_name
            )
            
            test_time = (time.time() - test_start) * 1000
            
            # Validation des résultats
            success = True
            
            # Vérification confiance minimale
            if result.get('confidence', 0) < test_case.min_confidence:
                success = False
                errors.append(f"Confiance {result.get('confidence', 0):.2f} < {test_case.min_confidence}")
            
            # Vérification NLP
            nlp_analysis = result.get('nlp_analysis', {})
            if nlp_analysis:
                # Vérification intentions
                found_intentions = [intent.get('intent', '') for intent in nlp_analysis.get('intentions', [])]
                missing_intentions = [intent for intent in test_case.expected_intentions 
                                    if not any(intent.lower() in found.lower() for found in found_intentions)]
                if missing_intentions:
                    errors.append(f"Intentions manquantes: {missing_intentions}")
                
                # Vérification entités
                found_entities = [entity.get('entity', '') for entity in nlp_analysis.get('entities', [])]
                normalized_text = nlp_analysis.get('normalized', '').lower()
                missing_entities = []
                for expected_entity in test_case.expected_entities:
                    if not any(expected_entity.lower() in found.lower() for found in found_entities) and \
                       expected_entity.lower() not in normalized_text:
                        missing_entities.append(expected_entity)
                
                if missing_entities:
                    errors.append(f"Entités manquantes: {missing_entities}")
            
            # Vérification réponse non vide
            if not result.get('response', '').strip():
                success = False
                errors.append("Réponse vide")
            
            # Vérification pipeline stages
            pipeline_stages = result.get('pipeline_stages', [])
            expected_stages = ['nlp_analysis', 'hybrid_search', 'enriched_generation']
            missing_stages = [stage for stage in expected_stages if stage not in pipeline_stages]
            if missing_stages:
                errors.append(f"Étapes pipeline manquantes: {missing_stages}")
            
            return TestResult(
                test_name=test_case.name,
                success=success and len(errors) == 0,
                response=result.get('response', ''),
                confidence=result.get('confidence', 0),
                processing_time_ms=result.get('processing_time_ms', test_time),
                nlp_analysis=nlp_analysis,
                fusion_metadata=result.get('fusion_metadata', {}),
                verification_result=result.get('verification_result', {}),
                quality_score=result.get('quality_score', 0),
                pipeline_stages=pipeline_stages,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur test {test_case.name}: {e}")
            
            return TestResult(
                test_name=test_case.name,
                success=False,
                response="",
                confidence=0,
                processing_time_ms=0,
                nlp_analysis={},
                fusion_metadata={},
                verification_result={},
                quality_score=0,
                pipeline_stages=[],
                errors=[f"Exception: {str(e)}"]
            )
    
    def generate_report(self, results: List[TestResult], total_time: float) -> Dict[str, Any]:
        """Génère un rapport complet des tests"""
        successful_tests = [r for r in results if r.success]
        failed_tests = [r for r in results if not r.success]
        
        # Métriques globales
        success_rate = len(successful_tests) / len(results) * 100
        avg_confidence = sum(r.confidence for r in results) / len(results)
        avg_processing_time = sum(r.processing_time_ms for r in results) / len(results)
        avg_quality_score = sum(r.quality_score for r in results if r.quality_score > 0) / max(1, len([r for r in results if r.quality_score > 0]))
        
        # Analyse des pipeline stages
        stage_coverage = {}
        for result in results:
            for stage in result.pipeline_stages:
                stage_coverage[stage] = stage_coverage.get(stage, 0) + 1
        
        # Analyse des erreurs
        error_analysis = {}
        for result in failed_tests:
            for error in result.errors:
                error_type = error.split(':')[0] if ':' in error else error
                error_analysis[error_type] = error_analysis.get(error_type, 0) + 1
        
        # Analyse NLP
        nlp_stats = {
            'intentions_detected': 0,
            'entities_detected': 0,
            'corrections_applied': 0,
            'multi_intent_queries': 0
        }
        
        for result in results:
            nlp = result.nlp_analysis
            if nlp:
                nlp_stats['intentions_detected'] += len(nlp.get('intentions', []))
                nlp_stats['entities_detected'] += len(nlp.get('entities', []))
                if nlp.get('corrected', '') != nlp.get('original', ''):
                    nlp_stats['corrections_applied'] += 1
                if len(nlp.get('split_queries', [])) > 1:
                    nlp_stats['multi_intent_queries'] += 1
        
        # Analyse fusion
        fusion_stats = {
            'hybrid_searches': 0,
            'avg_sources_used': 0,
            'avg_documents_found': 0
        }
        
        sources_counts = []
        docs_counts = []
        
        for result in results:
            fusion = result.fusion_metadata
            if fusion:
                fusion_stats['hybrid_searches'] += 1
                sources_count = fusion.get('total_sources', 0)
                docs_count = fusion.get('total_documents', 0)
                sources_counts.append(sources_count)
                docs_counts.append(docs_count)
        
        if sources_counts:
            fusion_stats['avg_sources_used'] = sum(sources_counts) / len(sources_counts)
        if docs_counts:
            fusion_stats['avg_documents_found'] = sum(docs_counts) / len(docs_counts)
        
        return {
            'test_summary': {
                'total_tests': len(results),
                'successful_tests': len(successful_tests),
                'failed_tests': len(failed_tests),
                'success_rate_percent': success_rate,
                'total_time_seconds': total_time
            },
            'performance_metrics': {
                'avg_confidence': avg_confidence,
                'avg_processing_time_ms': avg_processing_time,
                'avg_quality_score': avg_quality_score,
                'fastest_test_ms': min(r.processing_time_ms for r in results),
                'slowest_test_ms': max(r.processing_time_ms for r in results)
            },
            'pipeline_analysis': {
                'stage_coverage': stage_coverage,
                'nlp_statistics': nlp_stats,
                'fusion_statistics': fusion_stats
            },
            'error_analysis': error_analysis,
            'detailed_results': [
                {
                    'test_name': r.test_name,
                    'success': r.success,
                    'confidence': r.confidence,
                    'processing_time_ms': r.processing_time_ms,
                    'quality_score': r.quality_score,
                    'pipeline_stages': r.pipeline_stages,
                    'errors': r.errors,
                    'response_preview': r.response[:100] + '...' if len(r.response) > 100 else r.response
                }
                for r in results
            ],
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_configuration': {
                'company_id': self.company_id,
                'company_name': self.company_name,
                'user_id': self.user_id,
                'test_cases_count': len(self.test_cases)
            }
        }
    
    def display_report(self, report: Dict[str, Any]):
        """Affiche le rapport final"""
        print(f"\n{'='*80}")
        print(f"📊 RAPPORT FINAL - PIPELINE RAG FRANCOPHONE AVANCÉ")
        print(f"{'='*80}")
        
        # Résumé
        summary = report['test_summary']
        print(f"🎯 RÉSUMÉ GLOBAL:")
        print(f"   • Tests réussis: {summary['successful_tests']}/{summary['total_tests']} ({summary['success_rate_percent']:.1f}%)")
        print(f"   • Temps total: {summary['total_time_seconds']:.1f}s")
        
        # Performance
        perf = report['performance_metrics']
        print(f"\n⚡ PERFORMANCE:")
        print(f"   • Confiance moyenne: {perf['avg_confidence']:.2f}")
        print(f"   • Temps moyen: {perf['avg_processing_time_ms']:.0f}ms")
        print(f"   • Qualité moyenne: {perf['avg_quality_score']:.2f}")
        print(f"   • Plus rapide: {perf['fastest_test_ms']:.0f}ms")
        print(f"   • Plus lent: {perf['slowest_test_ms']:.0f}ms")
        
        # Pipeline
        pipeline = report['pipeline_analysis']
        print(f"\n🔄 ANALYSE PIPELINE:")
        print(f"   • Couverture stages: {dict(pipeline['stage_coverage'])}")
        print(f"   • Intentions détectées: {pipeline['nlp_statistics']['intentions_detected']}")
        print(f"   • Entités détectées: {pipeline['nlp_statistics']['entities_detected']}")
        print(f"   • Corrections appliquées: {pipeline['nlp_statistics']['corrections_applied']}")
        print(f"   • Requêtes multi-intentions: {pipeline['nlp_statistics']['multi_intent_queries']}")
        print(f"   • Recherches hybrides: {pipeline['fusion_statistics']['hybrid_searches']}")
        print(f"   • Sources moyennes: {pipeline['fusion_statistics']['avg_sources_used']:.1f}")
        
        # Erreurs
        if report['error_analysis']:
            print(f"\n❌ ANALYSE ERREURS:")
            for error_type, count in report['error_analysis'].items():
                print(f"   • {error_type}: {count} occurrences")
        
        # Tests détaillés
        print(f"\n📋 DÉTAIL DES TESTS:")
        for result in report['detailed_results']:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['test_name']}: {result['confidence']:.2f} conf, {result['processing_time_ms']:.0f}ms")
            if result['errors']:
                print(f"      Erreurs: {', '.join(result['errors'])}")
        
        print(f"\n{'='*80}")
    
    async def save_report(self, report: Dict[str, Any]):
        """Sauvegarde le rapport en JSON"""
        filename = f"advanced_rag_test_report_{int(time.time())}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Rapport sauvegardé: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde rapport: {e}")

async def main():
    """Point d'entrée principal"""
    tester = AdvancedRAGTester()
    
    try:
        report = await tester.run_all_tests()
        
        # Résumé final
        success_rate = report['test_summary']['success_rate_percent']
        
        if success_rate >= 80:
            print(f"\n🎉 SUCCÈS GLOBAL: {success_rate:.1f}% - Pipeline RAG francophone opérationnel!")
        elif success_rate >= 60:
            print(f"\n⚠️ SUCCÈS PARTIEL: {success_rate:.1f}% - Améliorations nécessaires")
        else:
            print(f"\n❌ ÉCHEC CRITIQUE: {success_rate:.1f}% - Révision majeure requise")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Erreur critique tests: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
