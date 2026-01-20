#!/usr/bin/env python3
"""
🔄 TESTS DE COHÉRENCE & CONSISTANCE - CHATBOT RUE_DU_GROS
========================================================
Tests de paraphrases et vérification de la consistance des réponses
Validation de la cohérence sémantique
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
import difflib
from collections import defaultdict

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

class CoherenceTester:
    def __init__(self):
        self.results = []
        self.inconsistencies = []
        
    # Tests de paraphrases - même question formulée différemment
    PARAPHRASE_TESTS = [
        {
            "name": "Prix Couches Taille 1",
            "variations": [
                "combien coûtent les couches taille 1",
                "quel est le prix des couches pour nouveau-né taille 1",
                "prix couches taille 1 nouveau-né",
                "tarif couches taille 1"
            ],
            "expected_consistency": "price_info",
            "key_elements": ["17.900", "taille 1", "0 à 4 kg", "300 couches"]
        },
        {
            "name": "Livraison Cocody",
            "variations": [
                "livraison à Cocody combien ça coûte",
                "vous livrez à Cocody quel tarif",
                "frais de livraison Cocody",
                "coût livraison zone Cocody"
            ],
            "expected_consistency": "delivery_info",
            "key_elements": ["cocody", "1500", "fcfa", "livraison"]
        },
        {
            "name": "Paiement Wave",
            "variations": [
                "je peux payer avec wave money",
                "vous acceptez wave comme paiement",
                "paiement par wave possible",
                "wave money accepté"
            ],
            "expected_consistency": "payment_method",
            "key_elements": ["wave", "accepté", "paiement", "+2250787360757"]
        },
        {
            "name": "Contact WhatsApp",
            "variations": [
                "numéro whatsapp pour commander",
                "votre whatsapp c'est quoi",
                "contact whatsapp commande",
                "numéro whatsapp entreprise"
            ],
            "expected_consistency": "contact_info",
            "key_elements": ["+2250160924560", "whatsapp", "commander"]
        }
    ]
    
    # Tests de consistance temporelle - même question à différents moments
    TEMPORAL_CONSISTENCY_TESTS = [
        {
            "name": "Stabilité Prix Taille 4",
            "query": "prix couches taille 4 pour enfant 10 kg",
            "repetitions": 5,
            "expected_consistency": "stable_pricing",
            "key_elements": ["25.900", "taille 4", "9 à 14 kg"]
        },
        {
            "name": "Stabilité Politique Acompte",
            "query": "faut-il payer un acompte pour commander",
            "repetitions": 5,
            "expected_consistency": "stable_policy",
            "key_elements": ["acompte", "2000", "fcfa", "obligatoire"]
        },
        {
            "name": "Stabilité Horaires",
            "query": "à quelle heure je peux vous contacter",
            "repetitions": 3,
            "expected_consistency": "stable_hours",
            "key_elements": ["toujours ouvert", "contact"]
        }
    ]
    
    # Tests de cohérence contextuelle
    CONTEXTUAL_COHERENCE_TESTS = [
        {
            "name": "Calcul Total Commande",
            "queries": [
                "prix 2 paquets couches culottes",
                "livraison à Marcory combien",
                "total pour 2 paquets culottes + livraison Marcory"
            ],
            "expected_consistency": "mathematical_coherence",
            "validation_type": "calculation"
        },
        {
            "name": "Comparaison Tailles",
            "queries": [
                "prix couches taille 3",
                "prix couches taille 6", 
                "différence prix entre taille 3 et taille 6"
            ],
            "expected_consistency": "comparative_coherence",
            "validation_type": "comparison"
        }
    ]

    async def run_paraphrase_tests(self, session):
        """Tests de paraphrases pour vérifier la consistance"""
        print(f"\n🔄 TESTS DE PARAPHRASES")
        print("="*50)
        
        paraphrase_results = []
        
        for test_group in self.PARAPHRASE_TESTS:
            print(f"\n📝 {test_group['name']}")
            
            responses = []
            for i, variation in enumerate(test_group['variations'], 1):
                print(f"  {i}. '{variation}'")
                
                success, response, duration = await self.send_request(session, variation)
                
                if success:
                    responses.append({
                        'variation': variation,
                        'response': response,
                        'duration': duration
                    })
                    print(f"     ✅ {duration:.1f}ms")
                else:
                    print(f"     ❌ Erreur: {response}")
                
                await asyncio.sleep(0.5)
            
            # Analyse de cohérence
            if len(responses) >= 2:
                consistency_score, inconsistencies = self.analyze_paraphrase_consistency(
                    test_group, responses
                )
                
                result = {
                    'test_name': test_group['name'],
                    'type': 'paraphrase',
                    'variations_tested': len(responses),
                    'consistency_score': consistency_score,
                    'responses': responses,
                    'inconsistencies': inconsistencies,
                    'key_elements': test_group['key_elements']
                }
                
                paraphrase_results.append(result)
                
                print(f"  📊 Score cohérence: {consistency_score:.1f}%")
                if inconsistencies:
                    print(f"  ⚠️ Incohérences: {len(inconsistencies)}")
                    for inc in inconsistencies:
                        print(f"    • {inc}")
        
        return paraphrase_results

    async def run_temporal_consistency_tests(self, session):
        """Tests de consistance temporelle"""
        print(f"\n⏰ TESTS DE CONSISTANCE TEMPORELLE")
        print("="*50)
        
        temporal_results = []
        
        for test in self.TEMPORAL_CONSISTENCY_TESTS:
            print(f"\n🔁 {test['name']} ({test['repetitions']} répétitions)")
            
            responses = []
            for i in range(test['repetitions']):
                print(f"  Répétition {i+1}/{test['repetitions']}")
                
                success, response, duration = await self.send_request(session, test['query'])
                
                if success:
                    responses.append({
                        'repetition': i+1,
                        'response': response,
                        'duration': duration,
                        'timestamp': time.time()
                    })
                    print(f"    ✅ {duration:.1f}ms")
                else:
                    print(f"    ❌ Erreur: {response}")
                
                await asyncio.sleep(2)  # Pause entre répétitions
            
            # Analyse de stabilité
            if len(responses) >= 2:
                stability_score, variations = self.analyze_temporal_stability(
                    test, responses
                )
                
                result = {
                    'test_name': test['name'],
                    'type': 'temporal',
                    'repetitions': len(responses),
                    'stability_score': stability_score,
                    'responses': responses,
                    'variations': variations,
                    'key_elements': test['key_elements']
                }
                
                temporal_results.append(result)
                
                print(f"  📊 Score stabilité: {stability_score:.1f}%")
                if variations:
                    print(f"  🔄 Variations détectées: {len(variations)}")
        
        return temporal_results

    async def run_contextual_coherence_tests(self, session):
        """Tests de cohérence contextuelle"""
        print(f"\n🧩 TESTS DE COHÉRENCE CONTEXTUELLE")
        print("="*50)
        
        contextual_results = []
        
        for test in self.CONTEXTUAL_COHERENCE_TESTS:
            print(f"\n🔗 {test['name']}")
            
            responses = []
            for i, query in enumerate(test['queries'], 1):
                print(f"  {i}. '{query}'")
                
                success, response, duration = await self.send_request(session, query)
                
                if success:
                    responses.append({
                        'query': query,
                        'response': response,
                        'duration': duration
                    })
                    print(f"     ✅ {duration:.1f}ms")
                else:
                    print(f"     ❌ Erreur: {response}")
                
                await asyncio.sleep(1)
            
            # Analyse de cohérence contextuelle
            if len(responses) >= 2:
                coherence_score, issues = self.analyze_contextual_coherence(
                    test, responses
                )
                
                result = {
                    'test_name': test['name'],
                    'type': 'contextual',
                    'queries_tested': len(responses),
                    'coherence_score': coherence_score,
                    'responses': responses,
                    'coherence_issues': issues,
                    'validation_type': test['validation_type']
                }
                
                contextual_results.append(result)
                
                print(f"  📊 Score cohérence: {coherence_score:.1f}%")
                if issues:
                    print(f"  ⚠️ Problèmes: {len(issues)}")
        
        return contextual_results

    def analyze_paraphrase_consistency(self, test_group, responses):
        """Analyse la consistance entre paraphrases"""
        consistency_score = 100.0
        inconsistencies = []
        
        # Vérification des éléments clés
        key_elements = test_group['key_elements']
        element_presence = defaultdict(list)
        
        for resp in responses:
            response_lower = resp['response'].lower()
            for element in key_elements:
                if element.lower() in response_lower:
                    element_presence[element].append(resp['variation'])
        
        # Vérifier que tous les éléments clés sont présents dans toutes les réponses
        for element in key_elements:
            presence_rate = len(element_presence[element]) / len(responses)
            if presence_rate < 0.8:  # 80% minimum
                inconsistencies.append(f"Élément '{element}' manquant dans {(1-presence_rate)*100:.0f}% des réponses")
                consistency_score -= 20
        
        # Vérification de la similarité sémantique
        response_texts = [r['response'] for r in responses]
        similarity_scores = []
        
        for i in range(len(response_texts)):
            for j in range(i+1, len(response_texts)):
                similarity = difflib.SequenceMatcher(None, response_texts[i], response_texts[j]).ratio()
                similarity_scores.append(similarity)
        
        if similarity_scores:
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            if avg_similarity < 0.6:  # 60% minimum de similarité
                inconsistencies.append(f"Faible similarité sémantique: {avg_similarity*100:.1f}%")
                consistency_score -= (0.6 - avg_similarity) * 100
        
        return max(0, consistency_score), inconsistencies

    def analyze_temporal_stability(self, test, responses):
        """Analyse la stabilité temporelle des réponses"""
        stability_score = 100.0
        variations = []
        
        # Comparaison des réponses successives
        response_texts = [r['response'] for r in responses]
        
        for i in range(1, len(response_texts)):
            similarity = difflib.SequenceMatcher(None, response_texts[0], response_texts[i]).ratio()
            
            if similarity < 0.8:  # 80% minimum de similarité
                variations.append({
                    'repetition': i+1,
                    'similarity': similarity,
                    'description': f"Variation significative par rapport à la première réponse"
                })
                stability_score -= (0.8 - similarity) * 100
        
        # Vérification des éléments clés
        key_elements = test['key_elements']
        for element in key_elements:
            element_count = sum(1 for resp in responses if element.lower() in resp['response'].lower())
            consistency_rate = element_count / len(responses)
            
            if consistency_rate < 1.0:
                variations.append({
                    'element': element,
                    'consistency_rate': consistency_rate,
                    'description': f"Élément '{element}' absent dans {(1-consistency_rate)*100:.0f}% des répétitions"
                })
                stability_score -= (1.0 - consistency_rate) * 20
        
        return max(0, stability_score), variations

    def analyze_contextual_coherence(self, test, responses):
        """Analyse la cohérence contextuelle"""
        coherence_score = 100.0
        issues = []
        
        validation_type = test['validation_type']
        
        if validation_type == "calculation":
            # Vérifier la cohérence mathématique
            issues.extend(self.validate_mathematical_coherence(responses))
        
        elif validation_type == "comparison":
            # Vérifier la cohérence comparative
            issues.extend(self.validate_comparative_coherence(responses))
        
        # Pénalité par problème détecté
        coherence_score -= len(issues) * 25
        
        return max(0, coherence_score), issues

    def validate_mathematical_coherence(self, responses):
        """Valide la cohérence mathématique"""
        issues = []
        
        # Extraction des prix mentionnés
        import re
        price_pattern = r'(\d+\.?\d*)\s*(?:fcfa|f\s*cfa)'
        
        extracted_prices = {}
        for resp in responses:
            prices = re.findall(price_pattern, resp['response'].lower())
            if prices:
                extracted_prices[resp['query']] = [float(p.replace('.', '')) for p in prices]
        
        # Vérification de cohérence (exemple basique)
        if len(extracted_prices) >= 3:
            # Logique de validation spécifique selon le contexte
            issues.append("Validation mathématique nécessite implémentation spécifique")
        
        return issues

    def validate_comparative_coherence(self, responses):
        """Valide la cohérence comparative"""
        issues = []
        
        # Vérification que les comparaisons sont logiques
        # Implémentation basique - peut être étendue
        for resp in responses:
            if "différence" in resp['response'].lower():
                if not any(word in resp['response'].lower() for word in ['plus', 'moins', 'supérieur', 'inférieur']):
                    issues.append("Comparaison sans indication claire de direction")
        
        return issues

    async def send_request(self, session, query):
        """Envoie une requête de test"""
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": "coherencetest123"
        }
        
        start_time = time.time()
        try:
            async with session.post(ENDPOINT_URL, json=payload, timeout=30) as response:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                if response.status == 200:
                    response_text = await response.text()
                    try:
                        response_json = json.loads(response_text)
                        actual_response = response_json.get('response', response_text)
                    except:
                        actual_response = response_text
                    return True, actual_response, duration
                else:
                    error_text = await response.text()
                    return False, f"HTTP {response.status}: {error_text}", duration
                    
        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            return False, str(e), duration

    async def run_all_tests(self):
        """Lance tous les tests de cohérence"""
        print("🔄 TESTS DE COHÉRENCE & CONSISTANCE - RUE_DU_GROS")
        print("="*60)
        print(f"🎯 URL: {ENDPOINT_URL}")
        print(f"🏢 Company ID: {COMPANY_ID}")
        print(f"🔍 Tests de cohérence et consistance...")
        
        async with aiohttp.ClientSession() as session:
            all_results = []
            
            # Tests de paraphrases
            paraphrase_results = await self.run_paraphrase_tests(session)
            all_results.extend(paraphrase_results)
            
            # Tests de consistance temporelle
            temporal_results = await self.run_temporal_consistency_tests(session)
            all_results.extend(temporal_results)
            
            # Tests de cohérence contextuelle
            contextual_results = await self.run_contextual_coherence_tests(session)
            all_results.extend(contextual_results)
            
            self.results = all_results
            
        await self.generate_coherence_report()

    async def generate_coherence_report(self):
        """Génère le rapport de cohérence final"""
        print("\n" + "="*60)
        print("🔄 RAPPORT DE COHÉRENCE FINAL")
        print("="*60)
        
        if not self.results:
            print("❌ Aucun résultat à analyser")
            return
        
        # Calcul des scores moyens par type
        type_scores = defaultdict(list)
        for result in self.results:
            test_type = result['type']
            if 'consistency_score' in result:
                type_scores[test_type].append(result['consistency_score'])
            elif 'stability_score' in result:
                type_scores[test_type].append(result['stability_score'])
            elif 'coherence_score' in result:
                type_scores[test_type].append(result['coherence_score'])
        
        overall_scores = []
        print(f"📊 SCORES PAR CATÉGORIE:")
        for test_type, scores in type_scores.items():
            avg_score = sum(scores) / len(scores)
            overall_scores.extend(scores)
            status = "✅" if avg_score >= 90 else "🟡" if avg_score >= 70 else "🔴"
            print(f"  {status} {test_type.title()}: {avg_score:.1f}% (sur {len(scores)} tests)")
        
        # Score global
        global_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        print(f"\n🎯 SCORE GLOBAL DE COHÉRENCE: {global_score:.1f}%")
        
        # Analyse détaillée
        total_issues = 0
        for result in self.results:
            issues = (result.get('inconsistencies', []) + 
                     result.get('variations', []) + 
                     result.get('coherence_issues', []))
            total_issues += len(issues)
        
        print(f"⚠️ Total des problèmes détectés: {total_issues}")
        
        # Verdict final
        print(f"\n🏆 VERDICT COHÉRENCE:")
        if global_score >= 90:
            print("✅ EXCELLENT - Très haute cohérence")
        elif global_score >= 75:
            print("🟡 BON - Cohérence satisfaisante")
        elif global_score >= 60:
            print("🟠 MOYEN - Améliorations nécessaires")
        else:
            print("🔴 CRITIQUE - Problèmes de cohérence majeurs")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        if global_score >= 90:
            print("  • Excellente cohérence, maintenir la qualité")
        else:
            print("  • Améliorer la consistance des réponses")
            print("  • Standardiser les informations clés")
            print("  • Renforcer la validation des calculs")
            print("  • Tester régulièrement la stabilité")
        
        # Sauvegarde du rapport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"coherence_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'global_score': global_score,
                    'total_tests': len(self.results),
                    'total_issues': total_issues,
                    'timestamp': timestamp
                },
                'type_scores': {k: sum(v)/len(v) for k, v in type_scores.items()},
                'detailed_results': self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Rapport sauvegardé: {report_file}")

async def main():
    tester = CoherenceTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
