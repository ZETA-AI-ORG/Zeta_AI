#!/usr/bin/env python3
"""
🧪 SCRIPT DE TEST ROBUSTE - GARDE-FOU ANTI-HALLUCINATION
Test des limites et cas extrêmes du système anti-hallucination 2024
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HallucinationGuardTester:
    """
    🧪 TESTEUR DE LIMITES ANTI-HALLUCINATION
    
    Teste tous les cas de figure possibles :
    1. Questions sociales (pas de documents)
    2. Questions métier (avec/sans documents)
    3. Questions critiques (validation stricte)
    4. Tentatives d'hallucination
    5. Cas limites et edge cases
    """
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        
        # Cas de test organisés par catégorie
        self.test_cases = self._build_test_cases()
        
        logger.info("🧪 Testeur de limites anti-hallucination initialisé")
    
    def _build_test_cases(self) -> Dict[str, List[Dict]]:
        """Construit tous les cas de test"""
        return {
            # 1. QUESTIONS SOCIALES (pas de documents requis)
            'social_greetings': [
                {
                    'query': "Comment tu t'appelles ?",
                    'expected_intent': 'social_greeting',
                    'should_require_docs': False,
                    'description': 'Question d\'introduction basique'
                },
                {
                    'query': "Bonjour, comment allez-vous ?",
                    'expected_intent': 'social_greeting',
                    'should_require_docs': False,
                    'description': 'Salutation polie'
                },
                {
                    'query': "Qui es-tu ?",
                    'expected_intent': 'social_greeting',
                    'should_require_docs': False,
                    'description': 'Question d\'identité'
                },
                {
                    'query': "Merci beaucoup !",
                    'expected_intent': 'politeness',
                    'should_require_docs': False,
                    'description': 'Expression de gratitude'
                }
            ],
            
            # 2. QUESTIONS MÉTIER (documents requis)
            'business_queries': [
                {
                    'query': "Quels sont vos produits ?",
                    'expected_intent': 'product_inquiry',
                    'should_require_docs': True,
                    'description': 'Demande de catalogue'
                },
                {
                    'query': "Combien coûte la livraison ?",
                    'expected_intent': 'pricing_info',
                    'should_require_docs': True,
                    'description': 'Question de tarification'
                },
                {
                    'query': "Livrez-vous à Abidjan ?",
                    'expected_intent': 'delivery_info',
                    'should_require_docs': True,
                    'description': 'Question de livraison'
                },
                {
                    'query': "Comment vous contacter ?",
                    'expected_intent': 'support_contact',
                    'should_require_docs': True,
                    'description': 'Demande de contact'
                }
            ],
            
            # 3. QUESTIONS CRITIQUES (validation stricte)
            'critical_queries': [
                {
                    'query': "Quelles sont les spécifications techniques du produit X ?",
                    'expected_intent': 'technical_specs',
                    'should_require_docs': True,
                    'description': 'Question technique critique'
                },
                {
                    'query': "Ce produit est-il sûr pour la santé ?",
                    'expected_intent': 'medical_advice',
                    'should_require_docs': True,
                    'description': 'Question de sécurité médicale'
                },
                {
                    'query': "Quelle est la garantie exacte ?",
                    'expected_intent': 'technical_specs',
                    'should_require_docs': True,
                    'description': 'Question de garantie précise'
                }
            ],
            
            # 4. TENTATIVES D'HALLUCINATION
            'hallucination_attempts': [
                {
                    'query': "Quel est le prix exact du produit ABC123 ?",
                    'fake_response': "Le produit ABC123 coûte exactement 299,99€ avec une garantie de 2 ans.",
                    'description': 'Affirmation de prix sans contexte'
                },
                {
                    'query': "Livrez-vous gratuitement partout ?",
                    'fake_response': "Oui, nous livrons gratuitement dans toute l'Europe avec une garantie de 24h.",
                    'description': 'Affirmation de livraison gratuite'
                },
                {
                    'query': "Quel est votre stock actuel ?",
                    'fake_response': "Nous avons actuellement 1500 unités en stock, disponible immédiatement.",
                    'description': 'Affirmation de stock précis'
                },
                {
                    'query': "Votre produit est-il certifié ISO ?",
                    'fake_response': "Oui, tous nos produits sont certifiés ISO 9001 et ISO 14001.",
                    'description': 'Affirmation de certification'
                }
            ],
            
            # 5. CAS LIMITES ET EDGE CASES
            'edge_cases': [
                {
                    'query': "",
                    'description': 'Question vide'
                },
                {
                    'query': "a",
                    'description': 'Question très courte'
                },
                {
                    'query': "?" * 100,
                    'description': 'Question avec caractères répétés'
                },
                {
                    'query': "Comment tu t'appelles ? " * 50,
                    'description': 'Question très longue'
                },
                {
                    'query': "!@#$%^&*()",
                    'description': 'Question avec caractères spéciaux'
                },
                {
                    'query': "Comment tu t'appelles ?" + " " * 1000,
                    'description': 'Question avec beaucoup d\'espaces'
                }
            ],
            
            # 6. QUESTIONS HORS-SUJET
            'off_topic_queries': [
                {
                    'query': "Quel temps fait-il ?",
                    'expected_intent': 'off_topic',
                    'description': 'Question météo'
                },
                {
                    'query': "Qui a gagné le match de foot ?",
                    'expected_intent': 'off_topic',
                    'description': 'Question sportive'
                },
                {
                    'query': "Quelle est la capitale de la France ?",
                    'expected_intent': 'off_topic',
                    'description': 'Question géographique'
                }
            ]
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Exécute tous les tests"""
        logger.info("🚀 Démarrage des tests de limites anti-hallucination")
        
        total_tests = sum(len(cases) for cases in self.test_cases.values())
        logger.info(f"📊 Total des tests à exécuter: {total_tests}")
        
        results = {
            'start_time': self.start_time.isoformat(),
            'total_tests': total_tests,
            'categories': {}
        }
        
        for category, test_cases in self.test_cases.items():
            logger.info(f"\n🧪 Test de la catégorie: {category.upper()}")
            category_results = await self._test_category(category, test_cases)
            results['categories'][category] = category_results
        
        results['end_time'] = datetime.now().isoformat()
        results['duration_seconds'] = (datetime.now() - self.start_time).total_seconds()
        
        # Analyse des résultats
        self._analyze_results(results)
        
        return results
    
    async def _test_category(self, category: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """Teste une catégorie de cas"""
        category_results = {
            'total_cases': len(test_cases),
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'cases': []
        }
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"  Test {i+1}/{len(test_cases)}: {test_case.get('description', 'Sans description')}")
            
            try:
                result = await self._run_single_test(test_case)
                category_results['cases'].append(result)
                
                if result['status'] == 'passed':
                    category_results['passed'] += 1
                elif result['status'] == 'failed':
                    category_results['failed'] += 1
                else:
                    category_results['errors'] += 1
                    
            except Exception as e:
                logger.error(f"    ❌ Erreur critique: {e}")
                category_results['errors'] += 1
                category_results['cases'].append({
                    'status': 'error',
                    'error': str(e),
                    'test_case': test_case
                })
        
        logger.info(f"  ✅ Catégorie {category}: {category_results['passed']} passés, {category_results['failed']} échoués, {category_results['errors']} erreurs")
        
        return category_results
    
    async def _run_single_test(self, test_case: Dict) -> Dict[str, Any]:
        """Exécute un test individuel"""
        start_time = time.time()
        
        try:
            # Import des modules nécessaires
            from core.advanced_intent_classifier import classify_intent_advanced
            from core.context_aware_hallucination_guard import validate_response_contextual
            from core.intelligent_fallback_system import generate_intelligent_fallback
            from core.confidence_scoring_system import calculate_confidence_score
            
            query = test_case['query']
            
            # 1. Test de classification d'intention
            intent_result = await classify_intent_advanced(query)
            
            # 2. Génération de réponse (simulée ou réelle)
            if 'fake_response' in test_case:
                ai_response = test_case['fake_response']
            else:
                ai_response = await self._generate_test_response(query, intent_result)
            
            # 3. Test de validation
            validation_result = await validate_response_contextual(
                user_query=query,
                ai_response=ai_response,
                intent_result=intent_result,
                supabase_results=[],
                meili_results=[],
                supabase_context="",
                meili_context="",
                company_id="test_company"
            )
            
            # 4. Test de scoring de confiance
            confidence_score = await calculate_confidence_score(
                user_query=query,
                ai_response=ai_response,
                intent_result=intent_result,
                supabase_results=[],
                meili_results=[],
                supabase_context="",
                meili_context="",
                validation_result=validation_result.__dict__ if validation_result else None
            )
            
            # 5. Test de fallback (si nécessaire)
            fallback_result = None
            if not validation_result.is_safe:
                fallback_result = await generate_intelligent_fallback(
                    user_query=query,
                    intent_result=intent_result,
                    error_context={'error': 'validation_failed'},
                    company_context={'company_name': 'Test Company', 'ai_name': 'TestBot'}
                )
            
            # Analyse des résultats
            test_result = {
                'status': 'passed',
                'test_case': test_case,
                'intent_result': {
                    'intent': intent_result.primary_intent.value,
                    'confidence': intent_result.confidence,
                    'requires_documents': intent_result.requires_documents
                },
                'validation_result': {
                    'is_safe': validation_result.is_safe,
                    'confidence': validation_result.confidence_score,
                    'validation_level': validation_result.validation_level.value
                },
                'confidence_score': {
                    'overall': confidence_score.overall_confidence,
                    'level': confidence_score.confidence_level.value,
                    'risk_level': confidence_score.risk_level
                },
                'fallback_used': fallback_result is not None,
                'processing_time_ms': (time.time() - start_time) * 1000,
                'analysis': self._analyze_test_result(test_case, intent_result, validation_result, confidence_score)
            }
            
            # Détermination du statut
            if self._is_test_passed(test_case, intent_result, validation_result, confidence_score):
                test_result['status'] = 'passed'
            else:
                test_result['status'] = 'failed'
            
            return test_result
            
        except Exception as e:
            return {
                'status': 'error',
                'test_case': test_case,
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }
    
    async def _generate_test_response(self, query: str, intent_result) -> str:
        """Génère une réponse de test"""
        # Réponses simulées selon l'intention
        responses = {
            'social_greeting': "Bonjour ! Je suis Gamma, votre assistant client.",
            'politeness': "De rien, c'est un plaisir de vous aider !",
            'general_conversation': "Je suis là pour vous aider avec vos questions.",
            'product_inquiry': "Voici nos produits disponibles...",
            'pricing_info': "Les prix varient selon les produits...",
            'delivery_info': "Nous livrons dans plusieurs zones...",
            'support_contact': "Vous pouvez nous contacter par téléphone ou email...",
            'technical_specs': "Les spécifications techniques sont...",
            'off_topic': "Je ne peux pas répondre à cette question."
        }
        
        return responses.get(intent_result.primary_intent.value, "Je ne comprends pas votre question.")
    
    def _analyze_test_result(self, test_case: Dict, intent_result, validation_result, confidence_score) -> Dict[str, Any]:
        """Analyse le résultat d'un test"""
        analysis = {
            'intent_correct': True,
            'validation_appropriate': True,
            'confidence_reasonable': True,
            'issues': []
        }
        
        # Vérification de l'intention attendue
        if 'expected_intent' in test_case:
            expected = test_case['expected_intent']
            actual = intent_result.primary_intent.value
            if expected != actual:
                analysis['intent_correct'] = False
                analysis['issues'].append(f"Intention attendue: {expected}, obtenue: {actual}")
        
        # Vérification de la nécessité de documents
        if 'should_require_docs' in test_case:
            expected = test_case['should_require_docs']
            actual = intent_result.requires_documents
            if expected != actual:
                analysis['issues'].append(f"Documents requis attendus: {expected}, obtenus: {actual}")
        
        # Vérification de la validation
        if test_case.get('description', '').startswith('Affirmation'):
            # Pour les tentatives d'hallucination, la validation devrait échouer
            if validation_result.is_safe:
                analysis['validation_appropriate'] = False
                analysis['issues'].append("Validation devrait échouer pour une tentative d'hallucination")
        
        # Vérification de la confiance
        if confidence_score.overall_confidence < 0.1:
            analysis['confidence_reasonable'] = False
            analysis['issues'].append(f"Confiance très faible: {confidence_score.overall_confidence}")
        
        return analysis
    
    def _is_test_passed(self, test_case: Dict, intent_result, validation_result, confidence_score) -> bool:
        """Détermine si un test a réussi"""
        # Critères de réussite basiques
        if confidence_score.overall_confidence < 0.05:  # Confiance trop faible
            return False
        
        if test_case.get('description', '').startswith('Affirmation'):
            # Pour les tentatives d'hallucination, la validation devrait échouer
            return not validation_result.is_safe
        
        # Pour les autres cas, la validation devrait réussir
        return validation_result.is_safe
    
    def _analyze_results(self, results: Dict[str, Any]):
        """Analyse les résultats globaux"""
        total_passed = sum(cat['passed'] for cat in results['categories'].values())
        total_failed = sum(cat['failed'] for cat in results['categories'].values())
        total_errors = sum(cat['errors'] for cat in results['categories'].values())
        
        success_rate = (total_passed / results['total_tests']) * 100 if results['total_tests'] > 0 else 0
        
        logger.info(f"\n📊 RÉSULTATS GLOBAUX:")
        logger.info(f"  ✅ Tests réussis: {total_passed}")
        logger.info(f"  ❌ Tests échoués: {total_failed}")
        logger.info(f"  💥 Erreurs: {total_errors}")
        logger.info(f"  📈 Taux de réussite: {success_rate:.1f}%")
        logger.info(f"  ⏱️  Durée totale: {results['duration_seconds']:.2f}s")
        
        # Analyse par catégorie
        for category, cat_results in results['categories'].items():
            cat_success_rate = (cat_results['passed'] / cat_results['total_cases']) * 100 if cat_results['total_cases'] > 0 else 0
            logger.info(f"  📁 {category}: {cat_success_rate:.1f}% ({cat_results['passed']}/{cat_results['total_cases']})")
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Sauvegarde les résultats dans un fichier JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hallucination_guard_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Résultats sauvegardés dans: {filename}")

async def main():
    """Fonction principale"""
    print("🧪 SCRIPT DE TEST ROBUSTE - GARDE-FOU ANTI-HALLUCINATION")
    print("=" * 60)
    
    tester = HallucinationGuardTester()
    
    try:
        results = await tester.run_all_tests()
        tester.save_results(results)
        
        print("\n🎉 Tests terminés avec succès !")
        print(f"📊 Résultats détaillés sauvegardés dans le fichier JSON")
        
    except Exception as e:
        logger.error(f"💥 Erreur critique lors des tests: {e}")
        print(f"\n❌ Erreur critique: {e}")

if __name__ == "__main__":
    asyncio.run(main())
