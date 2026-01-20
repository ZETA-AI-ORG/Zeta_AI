#!/usr/bin/env python3
"""
💬 TESTS CONVERSATIONNELS LONG TERME - CHATBOT RUE_DU_GROS
=========================================================
Tests de maintien du contexte sur conversations étendues
Validation de la mémoire conversationnelle
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
import uuid

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

class ConversationTester:
    def __init__(self):
        self.results = []
        self.context_failures = []
        
    # Scénarios de conversation longue
    CONVERSATION_SCENARIOS = [
        {
            "name": "Commande Progressive Complexe",
            "description": "Simulation d'une commande construite progressivement",
            "turns": [
                {
                    "message": "Bonjour, je cherche des couches pour mon bébé",
                    "expected_context": ["greeting", "couches", "bébé"],
                    "context_check": "initial_inquiry"
                },
                {
                    "message": "Il pèse 8 kg",
                    "expected_context": ["8 kg", "poids", "taille"],
                    "context_check": "weight_provided"
                },
                {
                    "message": "Quelle taille me conseillez-vous?",
                    "expected_context": ["conseil", "taille", "8 kg"],
                    "context_check": "advice_request"
                },
                {
                    "message": "Combien ça coûte?",
                    "expected_context": ["prix", "coût", "taille"],
                    "context_check": "price_inquiry"
                },
                {
                    "message": "Je veux 3 paquets",
                    "expected_context": ["3 paquets", "quantité"],
                    "context_check": "quantity_specified"
                },
                {
                    "message": "Livraison à Cocody possible?",
                    "expected_context": ["livraison", "cocody", "commande"],
                    "context_check": "delivery_inquiry"
                },
                {
                    "message": "Quel sera le total final?",
                    "expected_context": ["total", "3 paquets", "cocody", "calcul"],
                    "context_check": "final_calculation"
                }
            ]
        },
        {
            "name": "Support Client Évolutif",
            "description": "Conversation de support avec évolution des besoins",
            "turns": [
                {
                    "message": "J'ai un problème avec ma dernière commande",
                    "expected_context": ["problème", "commande", "support"],
                    "context_check": "support_request"
                },
                {
                    "message": "Les couches taille 4 ne conviennent pas à mon enfant",
                    "expected_context": ["taille 4", "ne conviennent pas", "enfant"],
                    "context_check": "problem_specification"
                },
                {
                    "message": "Il pèse maintenant 12 kg",
                    "expected_context": ["12 kg", "poids actuel", "croissance"],
                    "context_check": "weight_update"
                },
                {
                    "message": "Quelle taille serait mieux?",
                    "expected_context": ["nouvelle taille", "12 kg", "conseil"],
                    "context_check": "size_recommendation"
                },
                {
                    "message": "Puis-je échanger mes couches taille 4?",
                    "expected_context": ["échange", "taille 4", "politique retour"],
                    "context_check": "exchange_request"
                },
                {
                    "message": "Comment procéder pour l'échange?",
                    "expected_context": ["procédure", "échange", "étapes"],
                    "context_check": "process_inquiry"
                }
            ]
        },
        {
            "name": "Comparaison et Décision",
            "description": "Processus de comparaison et prise de décision",
            "turns": [
                {
                    "message": "Je veux comparer vos différentes couches",
                    "expected_context": ["comparaison", "différentes couches"],
                    "context_check": "comparison_request"
                },
                {
                    "message": "Quelles sont les tailles disponibles?",
                    "expected_context": ["tailles disponibles", "gamme produits"],
                    "context_check": "size_range_inquiry"
                },
                {
                    "message": "Différence entre couches normales et culottes?",
                    "expected_context": ["différence", "normales", "culottes"],
                    "context_check": "product_comparison"
                },
                {
                    "message": "Pour un enfant de 15 kg, que recommandez-vous?",
                    "expected_context": ["15 kg", "recommandation", "conseil"],
                    "context_check": "specific_recommendation"
                },
                {
                    "message": "Quel est le plus économique pour gros volume?",
                    "expected_context": ["économique", "gros volume", "prix"],
                    "context_check": "economic_inquiry"
                },
                {
                    "message": "Je prends 1 colis de culottes alors",
                    "expected_context": ["décision", "1 colis", "culottes"],
                    "context_check": "final_decision"
                }
            ]
        }
    ]
    
    # Tests de références contextuelles
    CONTEXTUAL_REFERENCE_TESTS = [
        {
            "name": "Références Pronominales",
            "conversation": [
                ("Combien coûtent les couches taille 3?", "price_inquiry"),
                ("Elles sont disponibles en combien d'unités?", "pronoun_reference"),
                ("Je les veux toutes", "quantity_decision"),
                ("Quand pouvez-vous me les livrer?", "delivery_timing")
            ]
        },
        {
            "name": "Références Temporelles",
            "conversation": [
                ("J'ai commandé hier des couches", "past_reference"),
                ("Aujourd'hui je veux ajouter des culottes", "present_action"),
                ("Demain j'aurai besoin de la livraison", "future_planning"),
                ("Pouvez-vous coordonner tout ça?", "temporal_coordination")
            ]
        }
    ]

    async def run_conversation_scenario(self, session, scenario):
        """Exécute un scénario de conversation complète"""
        print(f"\n💬 {scenario['name']}")
        print(f"📝 {scenario['description']}")
        print("="*50)
        
        user_id = f"convtest{int(time.time())}"
        conversation_results = []
        context_memory = []
        
        for turn_num, turn in enumerate(scenario['turns'], 1):
            print(f"\n{turn_num:2d}. User: '{turn['message']}'")
            
            success, response, duration = await self.send_request(
                session, turn['message'], user_id
            )
            
            if success:
                # Analyse du maintien du contexte
                context_maintained = self.analyze_context_maintenance(
                    turn, response, context_memory
                )
                
                turn_result = {
                    'turn_number': turn_num,
                    'user_message': turn['message'],
                    'bot_response': response,
                    'duration': duration,
                    'expected_context': turn['expected_context'],
                    'context_check': turn['context_check'],
                    'context_maintained': context_maintained['maintained'],
                    'context_score': context_maintained['score'],
                    'context_issues': context_maintained['issues'],
                    'timestamp': time.time()
                }
                
                conversation_results.append(turn_result)
                context_memory.append({
                    'turn': turn_num,
                    'message': turn['message'],
                    'response': response,
                    'key_elements': turn['expected_context']
                })
                
                print(f"    Bot: {response[:100]}{'...' if len(response) > 100 else ''}")
                print(f"    ⏱️ {duration:.1f}ms | 🧠 Contexte: {context_maintained['score']:.0f}%")
                
                if not context_maintained['maintained']:
                    print(f"    ⚠️ Problème contexte: {context_maintained['issues']}")
                    self.context_failures.append({
                        'scenario': scenario['name'],
                        'turn': turn_num,
                        'issue': context_maintained['issues']
                    })
            else:
                print(f"    ❌ Erreur: {response}")
            
            await asyncio.sleep(1)  # Pause entre tours
        
        return {
            'scenario_name': scenario['name'],
            'total_turns': len(scenario['turns']),
            'successful_turns': len([r for r in conversation_results if r['context_maintained']]),
            'average_context_score': sum(r['context_score'] for r in conversation_results) / len(conversation_results) if conversation_results else 0,
            'turns': conversation_results
        }

    async def run_contextual_reference_tests(self, session):
        """Tests spécifiques aux références contextuelles"""
        print(f"\n🔗 TESTS DE RÉFÉRENCES CONTEXTUELLES")
        print("="*50)
        
        reference_results = []
        
        for test in self.CONTEXTUAL_REFERENCE_TESTS:
            print(f"\n📎 {test['name']}")
            
            user_id = f"reftest{int(time.time())}"
            test_results = []
            
            for i, (message, context_type) in enumerate(test['conversation'], 1):
                print(f"  {i}. '{message}'")
                
                success, response, duration = await self.send_request(
                    session, message, user_id
                )
                
                if success:
                    reference_quality = self.analyze_reference_resolution(
                        message, response, context_type, test_results
                    )
                    
                    test_results.append({
                        'turn': i,
                        'message': message,
                        'response': response,
                        'context_type': context_type,
                        'reference_quality': reference_quality,
                        'duration': duration
                    })
                    
                    print(f"     ✅ {duration:.1f}ms | Référence: {reference_quality:.0f}%")
                else:
                    print(f"     ❌ Erreur: {response}")
                
                await asyncio.sleep(0.5)
            
            reference_results.append({
                'test_name': test['name'],
                'turns': test_results,
                'average_reference_quality': sum(t['reference_quality'] for t in test_results) / len(test_results) if test_results else 0
            })
        
        return reference_results

    def analyze_context_maintenance(self, turn, response, context_memory):
        """Analyse le maintien du contexte conversationnel"""
        score = 100.0
        issues = []
        
        expected_elements = turn['expected_context']
        response_lower = response.lower()
        
        # Vérifier la présence des éléments attendus
        elements_found = 0
        for element in expected_elements:
            if element.lower() in response_lower:
                elements_found += 1
        
        element_score = (elements_found / len(expected_elements)) * 100 if expected_elements else 100
        
        # Vérifier les références au contexte précédent
        context_references = 0
        if len(context_memory) > 0:
            # Chercher des références aux tours précédents
            for prev_turn in context_memory[-3:]:  # 3 derniers tours
                for key_element in prev_turn['key_elements']:
                    if key_element.lower() in response_lower:
                        context_references += 1
                        break
        
        context_ref_score = min(100, context_references * 25) if context_memory else 100
        
        # Score final
        final_score = (element_score + context_ref_score) / 2
        
        # Identification des problèmes
        if element_score < 50:
            issues.append(f"Éléments attendus manquants ({elements_found}/{len(expected_elements)})")
        
        if context_ref_score < 50 and len(context_memory) > 0:
            issues.append("Faible référence au contexte précédent")
        
        # Vérifications spécifiques selon le type de contexte
        context_check = turn['context_check']
        
        if context_check == "final_calculation" and len(context_memory) > 3:
            # Doit référencer quantité et lieu de livraison
            quantity_ref = any('paquet' in prev['message'].lower() for prev in context_memory)
            location_ref = any('cocody' in prev['message'].lower() for prev in context_memory)
            
            if not (quantity_ref and location_ref):
                issues.append("Calcul final sans référence aux éléments précédents")
                final_score -= 30
        
        return {
            'maintained': final_score >= 70,
            'score': final_score,
            'issues': issues
        }

    def analyze_reference_resolution(self, message, response, context_type, previous_turns):
        """Analyse la résolution des références contextuelles"""
        score = 100.0
        
        if context_type == "pronoun_reference":
            # Vérifier que les pronoms sont correctement résolus
            pronouns = ['elles', 'ils', 'les', 'la', 'le']
            if any(pronoun in message.lower() for pronoun in pronouns):
                # Doit faire référence au produit mentionné précédemment
                if previous_turns and 'couches' in response.lower():
                    score = 100
                else:
                    score = 30  # Référence non résolue
        
        elif context_type == "temporal_coordination":
            # Doit coordonner les éléments temporels mentionnés
            temporal_words = ['hier', 'aujourd\'hui', 'demain']
            if any(word in ' '.join([t['message'] for t in previous_turns]) for word in temporal_words):
                if any(word in response.lower() for word in ['coordonner', 'planifier', 'organiser']):
                    score = 100
                else:
                    score = 50
        
        return score

    async def send_request(self, session, query, user_id):
        """Envoie une requête de test"""
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": user_id
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
        """Lance tous les tests conversationnels"""
        print("💬 TESTS CONVERSATIONNELS LONG TERME - RUE_DU_GROS")
        print("="*60)
        print(f"🎯 URL: {ENDPOINT_URL}")
        print(f"🏢 Company ID: {COMPANY_ID}")
        print(f"🗣️ Tests de maintien du contexte conversationnel...")
        
        async with aiohttp.ClientSession() as session:
            all_results = []
            
            # Tests de scénarios conversationnels
            scenario_results = []
            for scenario in self.CONVERSATION_SCENARIOS:
                result = await self.run_conversation_scenario(session, scenario)
                scenario_results.append(result)
                all_results.append(result)
            
            # Tests de références contextuelles
            reference_results = await self.run_contextual_reference_tests(session)
            all_results.extend(reference_results)
            
            self.results = {
                'scenarios': scenario_results,
                'references': reference_results
            }
            
        await self.generate_conversation_report()

    async def generate_conversation_report(self):
        """Génère le rapport conversationnel final"""
        print("\n" + "="*60)
        print("💬 RAPPORT CONVERSATIONNEL FINAL")
        print("="*60)
        
        scenario_results = self.results['scenarios']
        reference_results = self.results['references']
        
        # Analyse des scénarios
        total_turns = sum(s['total_turns'] for s in scenario_results)
        successful_turns = sum(s['successful_turns'] for s in scenario_results)
        success_rate = (successful_turns / total_turns) * 100 if total_turns > 0 else 0
        
        avg_context_score = sum(s['average_context_score'] for s in scenario_results) / len(scenario_results) if scenario_results else 0
        
        print(f"📊 SCÉNARIOS CONVERSATIONNELS:")
        print(f"  • Tours de conversation: {successful_turns}/{total_turns} ({success_rate:.1f}%)")
        print(f"  • Score contexte moyen: {avg_context_score:.1f}%")
        
        # Détail par scénario
        for scenario in scenario_results:
            scenario_success = (scenario['successful_turns'] / scenario['total_turns']) * 100
            status = "✅" if scenario_success >= 80 else "🟡" if scenario_success >= 60 else "🔴"
            print(f"    {status} {scenario['scenario_name']}: {scenario['successful_turns']}/{scenario['total_turns']} ({scenario_success:.1f}%)")
        
        # Analyse des références
        if reference_results:
            avg_ref_quality = sum(r['average_reference_quality'] for r in reference_results) / len(reference_results)
            print(f"\n🔗 RÉFÉRENCES CONTEXTUELLES:")
            print(f"  • Qualité moyenne: {avg_ref_quality:.1f}%")
            
            for ref_test in reference_results:
                status = "✅" if ref_test['average_reference_quality'] >= 80 else "🟡" if ref_test['average_reference_quality'] >= 60 else "🔴"
                print(f"    {status} {ref_test['test_name']}: {ref_test['average_reference_quality']:.1f}%")
        
        # Problèmes de contexte
        if self.context_failures:
            print(f"\n⚠️ PROBLÈMES DE CONTEXTE ({len(self.context_failures)}):")
            for failure in self.context_failures[:5]:  # Top 5
                print(f"  • {failure['scenario']} (Tour {failure['turn']}): {failure['issue']}")
        
        # Score global
        global_score = (avg_context_score + (avg_ref_quality if reference_results else avg_context_score)) / 2
        
        print(f"\n🎯 SCORE GLOBAL CONVERSATIONNEL: {global_score:.1f}%")
        
        # Verdict final
        print(f"\n🏆 VERDICT CONVERSATIONNEL:")
        if global_score >= 85:
            print("✅ EXCELLENT - Très bon maintien du contexte")
        elif global_score >= 70:
            print("🟡 BON - Contexte généralement maintenu")
        elif global_score >= 55:
            print("🟠 MOYEN - Améliorations du contexte nécessaires")
        else:
            print("🔴 CRITIQUE - Problèmes majeurs de contexte")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        if global_score >= 85:
            print("  • Excellent maintien du contexte conversationnel")
        else:
            print("  • Améliorer la mémoire conversationnelle")
            print("  • Renforcer les références aux tours précédents")
            print("  • Optimiser la résolution des pronoms")
            print("  • Tester avec des conversations plus longues")
        
        # Sauvegarde du rapport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"conversation_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'global_score': global_score,
                    'total_turns': total_turns,
                    'successful_turns': successful_turns,
                    'success_rate': success_rate,
                    'avg_context_score': avg_context_score,
                    'context_failures': len(self.context_failures),
                    'timestamp': timestamp
                },
                'detailed_results': self.results,
                'context_failures': self.context_failures
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Rapport sauvegardé: {report_file}")

async def main():
    tester = ConversationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
