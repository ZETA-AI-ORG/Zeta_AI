#!/usr/bin/env python3
"""
🔍 TEST ULTIME MEILISEARCH - DIAGNOSTIC COMPLET
10 questions du plus simple au plus verbeux pour tester l'environnement MeiliSearch
"""

import asyncio
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuration
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser135"

class MeiliDiagnosticTest:
    """Test diagnostic complet de MeiliSearch"""
    
    def __init__(self):
        self.test_questions = [
            # 🟢 NIVEAU 1: QUESTIONS ULTRA-SIMPLES (1-2 mots) - TOUS LES INDEX
            {
                "level": 1,
                "category": "ultra_simple",
                "question": "wave",
                "expected_keywords": ["wave", "paiement", "2250787360757"],
                "expected_method": "meilisearch",
                "description": "Paiement - Index support"
            },
            {
                "level": 1,
                "category": "ultra_simple", 
                "question": "whatsapp",
                "expected_keywords": ["whatsapp", "2250160924560", "contact"],
                "expected_method": "meilisearch",
                "description": "Contact - Index support"
            },
            
            # 🟡 NIVEAU 2: QUESTIONS SIMPLES (3-4 mots) - DIVERSIFIÉES
            {
                "level": 2,
                "category": "simple",
                "question": "couches adultes prix",
                "expected_keywords": ["couches", "adultes", "588", "fcfa"],
                "expected_method": "meilisearch", 
                "description": "Produits adultes - Index products"
            },
            {
                "level": 2,
                "category": "simple",
                "question": "livraison yopougon tarif",
                "expected_keywords": ["livraison", "yopougon", "1500", "fcfa"],
                "expected_method": "meilisearch",
                "description": "Livraison zone - Index delivery"
            },
            
            # 🟠 NIVEAU 3: QUESTIONS MOYENNES (5-7 mots) - VARIÉES
            {
                "level": 3,
                "category": "moyenne",
                "question": "combien coûte 6 paquets couches culottes",
                "expected_keywords": ["6", "paquets", "couches", "culottes", "25000", "fcfa"],
                "expected_method": "meilisearch",
                "description": "Quantité spécifique - Index products"
            },
            {
                "level": 3,
                "category": "moyenne",
                "question": "délai livraison grand bassam combien jours",
                "expected_keywords": ["délai", "grand-bassam", "périphériques", "2000", "2500"],
                "expected_method": "meilisearch",
                "description": "Délai géographique - Index delivery"
            },
            
            # 🔴 NIVEAU 4: QUESTIONS COMPLEXES (8-12 mots) - MULTI-INDEX
            {
                "level": 4,
                "category": "complexe",
                "question": "je veux commander 12 paquets couches adultes avec livraison à cocody",
                "expected_keywords": ["12", "paquets", "couches", "adultes", "114000", "cocody", "1500"],
                "expected_method": "meilisearch",
                "description": "Commande complète - Index products + delivery"
            },
            {
                "level": 4,
                "category": "complexe",
                "question": "politique de retour si je ne suis pas satisfait du produit",
                "expected_keywords": ["retour", "24h", "définitives", "confirmée", "livrée"],
                "expected_method": "meilisearch",
                "description": "Politique retour - Index support"
            },
            
            # 🟣 NIVEAU 5: QUESTIONS ULTRA-VERBEUSES (13+ mots) - STOP WORDS MASSIFS
            {
                "level": 5,
                "category": "verbeux",
                "question": "bonjour monsieur gamma, est-ce que vous pourriez s'il vous plaît me dire combien ça coûte exactement un colis complet de 48 paquets de couches culottes et si c'est possible de me livrer ça à adjamé aujourd'hui même",
                "expected_keywords": ["colis", "48", "paquets", "couches", "culottes", "168000", "adjamé", "1500"],
                "expected_method": "meilisearch",
                "description": "Question ultra-verbeuse avec politesse - Multi-index"
            },
            {
                "level": 5,
                "category": "ultra_verbeux",
                "question": "salut, alors voilà, je suis une maman et j'aimerais bien savoir si vous avez des couches pour mon bébé qui pèse environ 15 kilos, et aussi combien ça va me coûter pour la livraison si j'habite à port-bouët, et est-ce que je peux payer avec wave comme d'habitude, merci beaucoup",
                "expected_keywords": ["15", "kilos", "taille", "6", "27900", "port-bouët", "2000", "2500", "wave"],
                "expected_method": "meilisearch",
                "description": "Question conversationnelle complexe - Tous les index"
            }
        ]
    
    def analyze_response(self, response_data: Dict, expected: Dict) -> Dict[str, Any]:
        """Analyse la réponse pour diagnostiquer MeiliSearch"""
        analysis = {
            "success": False,
            "method_used": "unknown",
            "documents_found": False,
            "context_length": 0,
            "keywords_found": [],
            "keywords_missing": [],
            "processing_time": 0,
            "confidence": 0,
            "issues": []
        }
        
        try:
            # Extraire les données de base
            if "response" in response_data:
                inner_response = response_data["response"]
                analysis["method_used"] = inner_response.get("search_method", "unknown")
                analysis["documents_found"] = inner_response.get("documents_found", False)
                analysis["processing_time"] = inner_response.get("processing_time_ms", 0)
                analysis["confidence"] = inner_response.get("confidence", 0)
                analysis["context_length"] = len(inner_response.get("context_used", ""))
                
                # Analyser le contexte pour les mots-clés
                context = inner_response.get("context_used", "").lower()
                response_text = inner_response.get("response", "").lower()
                full_text = f"{context} {response_text}"
                
                # Vérifier les mots-clés attendus
                for keyword in expected["expected_keywords"]:
                    if keyword.lower() in full_text:
                        analysis["keywords_found"].append(keyword)
                    else:
                        analysis["keywords_missing"].append(keyword)
                
                # Déterminer le succès
                analysis["success"] = (
                    analysis["method_used"] == expected["expected_method"] and
                    analysis["documents_found"] and
                    len(analysis["keywords_found"]) >= len(expected["expected_keywords"]) * 0.6
                )
                
                # Identifier les problèmes
                if analysis["method_used"] != expected["expected_method"]:
                    analysis["issues"].append(f"Méthode incorrecte: {analysis['method_used']} au lieu de {expected['expected_method']}")
                
                if not analysis["documents_found"]:
                    analysis["issues"].append("Aucun document trouvé")
                
                if analysis["context_length"] < 100:
                    analysis["issues"].append(f"Contexte trop court: {analysis['context_length']} chars")
                
                if len(analysis["keywords_missing"]) > len(expected["expected_keywords"]) * 0.4:
                    analysis["issues"].append(f"Trop de mots-clés manquants: {analysis['keywords_missing']}")
                
        except Exception as e:
            analysis["issues"].append(f"Erreur analyse: {str(e)}")
        
        return analysis
    
    async def run_single_test(self, test_case: Dict) -> Dict[str, Any]:
        """Exécute un test unique"""
        print(f"\n🧪 TEST NIVEAU {test_case['level']} - {test_case['category'].upper()}")
        print(f"📝 Question: '{test_case['question']}'")
        print(f"🎯 Description: {test_case['description']}")
        print(f"🔍 Mots-clés attendus: {test_case['expected_keywords']}")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            response = requests.post(API_URL, 
                json={
                    "message": test_case["question"],
                    "company_id": COMPANY_ID,
                    "user_id": USER_ID
                },
                timeout=30
            )
            
            end_time = time.time()
            
            if response.status_code == 200:
                response_data = response.json()
                analysis = self.analyze_response(response_data, test_case)
                analysis["http_status"] = 200
                analysis["total_time"] = (end_time - start_time) * 1000
                
                # Affichage des résultats
                status = "✅ SUCCÈS" if analysis["success"] else "❌ ÉCHEC"
                print(f"{status}")
                print(f"   🔧 Méthode: {analysis['method_used']}")
                print(f"   📄 Documents: {'Oui' if analysis['documents_found'] else 'Non'}")
                print(f"   📏 Contexte: {analysis['context_length']} chars")
                print(f"   ⏱️ Temps: {analysis['total_time']:.1f}ms")
                print(f"   🎯 Confiance: {analysis['confidence']}")
                print(f"   ✅ Mots trouvés: {analysis['keywords_found']}")
                if analysis['keywords_missing']:
                    print(f"   ❌ Mots manquants: {analysis['keywords_missing']}")
                if analysis['issues']:
                    print(f"   🚨 Problèmes: {analysis['issues']}")
                
                return {**test_case, **analysis}
                
            else:
                print(f"❌ ERREUR HTTP {response.status_code}")
                print(f"📄 Réponse: {response.text[:200]}...")
                return {
                    **test_case,
                    "success": False,
                    "http_status": response.status_code,
                    "issues": [f"HTTP {response.status_code}"]
                }
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            return {
                **test_case,
                "success": False,
                "issues": [f"Exception: {str(e)}"]
            }
    
    async def run_full_diagnostic(self):
        """Exécute le diagnostic complet"""
        print("🔍 DIAGNOSTIC ULTIME MEILISEARCH")
        print("=" * 80)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🏢 Company: {COMPANY_ID}")
        print(f"👤 User: {USER_ID}")
        print(f"🧪 Tests: {len(self.test_questions)} questions")
        print("=" * 80)
        
        results = []
        
        for i, test_case in enumerate(self.test_questions, 1):
            print(f"\n{'='*20} TEST {i}/{len(self.test_questions)} {'='*20}")
            result = await self.run_single_test(test_case)
            results.append(result)
            
            # Pause entre les tests
            await asyncio.sleep(1)
        
        # Analyse globale
        self.generate_summary_report(results)
        
        return results
    
    def generate_summary_report(self, results: List[Dict]):
        """Génère un rapport de synthèse"""
        print("\n" + "="*80)
        print("📊 RAPPORT DE SYNTHÈSE MEILISEARCH")
        print("="*80)
        
        # Statistiques globales
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success", False))
        meili_tests = sum(1 for r in results if r.get("method_used") == "meilisearch")
        supabase_tests = sum(1 for r in results if r.get("method_used") == "supabase_fallback")
        
        print(f"📈 PERFORMANCE GLOBALE:")
        print(f"   ✅ Tests réussis: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"   🔍 MeiliSearch utilisé: {meili_tests}/{total_tests} ({meili_tests/total_tests*100:.1f}%)")
        print(f"   🔄 Supabase fallback: {supabase_tests}/{total_tests} ({supabase_tests/total_tests*100:.1f}%)")
        
        # Analyse par niveau
        print(f"\n📊 PERFORMANCE PAR NIVEAU:")
        for level in range(1, 6):
            level_results = [r for r in results if r.get("level") == level]
            if level_results:
                level_success = sum(1 for r in level_results if r.get("success", False))
                level_meili = sum(1 for r in level_results if r.get("method_used") == "meilisearch")
                print(f"   Niveau {level}: {level_success}/{len(level_results)} succès, {level_meili}/{len(level_results)} MeiliSearch")
        
        # Problèmes identifiés
        all_issues = []
        for result in results:
            all_issues.extend(result.get("issues", []))
        
        if all_issues:
            print(f"\n🚨 PROBLÈMES IDENTIFIÉS:")
            issue_counts = {}
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
            
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {issue}: {count} fois")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        if meili_tests < total_tests * 0.8:
            print("   🔧 MeiliSearch n'est pas assez utilisé - vérifier la configuration")
        if successful_tests < total_tests * 0.8:
            print("   🛠️ Taux de succès faible - optimiser le preprocessing et les fallbacks")
        if "Aucun document trouvé" in [issue for result in results for issue in result.get("issues", [])]:
            print("   📚 Problème de contenu - vérifier l'indexation MeiliSearch")
        
        print("="*80)

async def main():
    """Point d'entrée principal"""
    diagnostic = MeiliDiagnosticTest()
    await diagnostic.run_full_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())
