#!/usr/bin/env python3
"""
🚀 ULTIMATE RAG BENCHMARK - TEST DE PERTINENCE, PERFORMANCE & SOPHISTICATION
=============================================================================

Test ultra-robuste pour évaluer :
- Pertinence des réponses (scoring métier)
- Performance temporelle (MeiliSearch vs Supabase)
- Sophistication de l'ingénierie (extraction regex, auto-apprentissage)
- Robustesse du système (fallbacks, gestion d'erreurs)

Company: Rue_du_gros (MpfnlSbqwaZ6F4HvxQLRL9du0yG3)
"""

import asyncio
import time
import json
import re
import sys
import os
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Ajout du chemin parent pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class BenchmarkResult:
    """Résultat d'un test de benchmark"""
    question: str
    response: str
    confidence: float
    processing_time_ms: float
    search_method: str
    entities_extracted: int
    context_length: int
    relevance_score: float
    sophistication_score: float
    performance_score: float
    overall_score: float
    details: Dict[str, Any]

class UltimateRAGBenchmark:
    """
    🎯 BENCHMARK ULTIME DU SYSTÈME RAG
    
    Tests multi-dimensionnels :
    1. Pertinence métier (0-100)
    2. Performance technique (0-100) 
    3. Sophistication ingénierie (0-100)
    4. Robustesse système (0-100)
    """
    
    def __init__(self, company_id: str = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"):
        self.company_id = company_id
        self.company_name = "Rue_du_gros"
        
        # Questions de test avec niveaux de difficulté
        self.test_questions = [
            # NIVEAU 1 : Questions simples variées
            {
                "question": "Quel est le coût pour faire livrer une commande à Yopougon aujourd'hui ?",
                "niveau": "facile",
                "reponse_attendue": {"tarif": 1500, "zone": "centrale"},
                "entites_attendues": ["zone_geographique", "tarif_livraison"],
                "poids": 1.0
            },
            {
                "question": "À combien revient un paquet de couches culottes taille 3 ?",
                "niveau": "facile",
                "reponse_attendue": {"prix": 5500},
                "entites_attendues": ["montant_fcfa"],
                "poids": 1.0
            },
            {
                "question": "Quel est le prix d'un paquet de couches pour adulte ?",
                "niveau": "facile",
                "reponse_attendue": {"prix": 12000},
                "entites_attendues": ["montant_fcfa"],
                "poids": 1.0
            },
            # NIVEAU 2 : Questions moyennes variées
            {
                "question": "Si je passe commande avant midi, puis-je être livré à Cocody le même jour ?",
                "niveau": "moyen",
                "reponse_attendue": {"delai": "jour_meme", "condition": "avant_12h", "zone": "centrale"},
                "entites_attendues": ["zone_geographique", "delai_livraison"],
                "poids": 1.5
            },
            {
                "question": "Quel montant dois-je payer pour 4 paquets de couches culottes avec livraison à Plateau ?",
                "niveau": "moyen",
                "reponse_attendue": {"prix_produit": 18000, "prix_livraison": 1500, "total": 19500},
                "entites_attendues": ["montant_fcfa", "zone_geographique", "tarif_livraison"],
                "poids": 1.5
            },
            # NIVEAU 3 : Calculs & recommandations
            {
                "question": "Quel est le meilleur choix pour 6 paquets de couches, livraison à Marcory ?",
                "niveau": "difficile",
                "reponse_attendue": {"recommandation": True, "prix_total": 27000, "livraison": 1500},
                "entites_attendues": ["montant_fcfa", "zone_geographique", "tarif_livraison", "recommandation"],
                "poids": 2.0
            },
            {
                "question": "Je souhaite acheter 10 paquets de couches à livrer à Grand-Bassam, commande à 14h. Quel sera le total avec acompte ?",
                "niveau": "difficile",
                "reponse_attendue": {"prix_produit": 40000, "livraison": 2000, "acompte": 2000, "delai": "lendemain", "total": 42000},
                "entites_attendues": ["montant_fcfa", "zone_geographique", "tarif_livraison", "acompte"],
                "poids": 2.0
            },
            # NIVEAU 4 : Questions ultra-complexes/edge cases
            {
                "question": "Je suis parent de triplés de 12 mois pesant 9kg, 11kg et 13kg, j'habite à Bingerville, je travaille à Koumassi. Livraison possible, prix total, tailles recommandées ?",
                "niveau": "expert",
                "reponse_attendue": {"livraison_possible": True, "tailles": ["3", "4", "5"], "zones": ["bingerville", "koumassi"], "tarifs": [2000, 1500]},
                "entites_attendues": ["zone_geographique", "tarif_livraison", "montant_fcfa", "recommandation"],
                "poids": 3.0
            },
            # NIVEAU 5 : Stress test & pièges variés
            {
                "question": "Est-ce que la livraison express est gratuite pour les commandes de plus de 100 000 FCFA ?",
                "niveau": "piege",
                "reponse_attendue": {"gratuite": False, "tarif_minimum": 1500},
                "entites_attendues": ["tarif_livraison"],
                "poids": 2.5
            },
            {
                "question": "Couches pour adulte de 90kg disponibles ?",
                "niveau": "piege",
                "reponse_attendue": {"impossible": True, "max_poids": 30, "suggestion": "couches_speciales"},
                "entites_attendues": [],
                "poids": 2.5
            },
            {
                "question": "Combien puis-je économiser si je prends 8 paquets au lieu de 3 ?",
                "niveau": "difficile",
                "reponse_attendue": {"economie": True, "prix_8": 32000, "prix_3": 13500},
                "entites_attendues": ["montant_fcfa", "economie"],
                "poids": 2.0
            },
            {
                "question": "Quel est le montant total pour 2 paquets de couches à pression et 3 paquets de couches culottes livrés à Abobo ?",
                "niveau": "difficile",
                "reponse_attendue": {"prix_total": 23000, "livraison": 1500},
                "entites_attendues": ["montant_fcfa", "zone_geographique", "tarif_livraison"],
                "poids": 2.0
            }
        ]
    
    async def run_ultimate_benchmark(self) -> Dict[str, Any]:
        """🚀 Lance le benchmark ultime complet"""
        print("🚀 " + "="*80)
        print("🚀 ULTIMATE RAG BENCHMARK - RUE_DU_GROS")
        print("🚀 " + "="*80)
        print(f"🏢 Company: {self.company_name} ({self.company_id[:12]}...)")
        print(f"📊 Tests prévus: {len(self.test_questions)}")
        print(f"⏰ Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Import du système RAG
        try:
            from core.universal_rag_engine import get_universal_rag_response
            print("✅ Système RAG importé avec succès")
        except ImportError as e:
            print(f"❌ Erreur import RAG: {e}")
            return {"error": "Import RAG failed"}
        
        results = []
        total_start = time.time()
        
        # Tests séquentiels pour éviter les conflits
        for i, test_case in enumerate(self.test_questions, 1):
            print(f"\n📝 TEST {i}/{len(self.test_questions)} - {test_case['niveau'].upper()}")
            print(f"❓ Question: {test_case['question'][:60]}...")
            
            try:
                # Exécution du test
                start_time = time.time()
                rag_result = await get_universal_rag_response(
                    message=test_case['question'],
                    company_id=self.company_id,
                    user_id=f"benchmark_user_{i}",
                    company_name=self.company_name
                )
                end_time = time.time()
                
                # Analyse des résultats
                benchmark_result = self._analyze_result(test_case, rag_result, end_time - start_time)
                results.append(benchmark_result)
                
                # Affichage résumé
                print(f"⏱️  Temps: {benchmark_result.processing_time_ms:.0f}ms")
                print(f"🎯 Pertinence: {benchmark_result.relevance_score:.1f}/100")
                print(f"🔧 Sophistication: {benchmark_result.sophistication_score:.1f}/100")
                print(f"⚡ Performance: {benchmark_result.performance_score:.1f}/100")
                print(f"🏆 Score global: {benchmark_result.overall_score:.1f}/100")
                
            except Exception as e:
                print(f"❌ Erreur test {i}: {str(e)[:50]}")
                # Créer un résultat d'erreur
                error_result = BenchmarkResult(
                    question=test_case['question'],
                    response=f"ERREUR: {str(e)}",
                    confidence=0.0,
                    processing_time_ms=0.0,
                    search_method="error",
                    entities_extracted=0,
                    context_length=0,
                    relevance_score=0.0,
                    sophistication_score=0.0,
                    performance_score=0.0,
                    overall_score=0.0,
                    details={"error": str(e)}
                )
                results.append(error_result)
        
        total_time = time.time() - total_start
        
        # Calcul des métriques globales
        global_metrics = self._calculate_global_metrics(results, total_time)
        
        # Rapport final
        self._generate_final_report(results, global_metrics)
        
        return {
            "results": results,
            "global_metrics": global_metrics,
            "total_time": total_time,
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_result(self, test_case: Dict, rag_result: Dict, execution_time: float) -> BenchmarkResult:
        """🔍 Analyse approfondie d'un résultat de test"""
        
        response = rag_result.get('response', '')
        confidence = rag_result.get('confidence', 0.0)
        processing_time = rag_result.get('processing_time_ms', 0.0)
        search_method = rag_result.get('search_method', 'unknown')
        context_used = rag_result.get('context_used', '')
        
        # 1. SCORE DE PERTINENCE (0-100)
        relevance_score = self._calculate_relevance_score(test_case, response)
        
        # 2. SCORE DE SOPHISTICATION (0-100) 
        sophistication_score = self._calculate_sophistication_score(rag_result, context_used)
        
        # 3. SCORE DE PERFORMANCE (0-100)
        performance_score = self._calculate_performance_score(processing_time, search_method)
        
        # 4. EXTRACTION D'ENTITÉS
        entities_extracted = self._count_entities_in_context(context_used)
        
        # 5. SCORE GLOBAL PONDÉRÉ
        poids = test_case.get('poids', 1.0)
        overall_score = (
            relevance_score * 0.5 +
            sophistication_score * 0.3 + 
            performance_score * 0.2
        ) * poids / 3.0  # Normalisation par le poids
        
        return BenchmarkResult(
            question=test_case['question'],
            response=response,
            confidence=confidence,
            processing_time_ms=processing_time,
            search_method=search_method,
            entities_extracted=entities_extracted,
            context_length=len(context_used),
            relevance_score=relevance_score,
            sophistication_score=sophistication_score,
            performance_score=performance_score,
            overall_score=min(100, overall_score),  # Cap à 100
            details={
                "niveau": test_case['niveau'],
                "entites_attendues": test_case.get('entites_attendues', []),
                "reponse_attendue": test_case.get('reponse_attendue', {}),
                "execution_time": execution_time,
                "context_preview": context_used[:200] + "..." if len(context_used) > 200 else context_used
            }
        )
    
    def _calculate_relevance_score(self, test_case: Dict, response: str) -> float:
        """🎯 Calcule le score de pertinence métier (0-100)"""
        score = 0.0
        response_lower = response.lower()
        
        reponse_attendue = test_case.get('reponse_attendue', {})
        niveau = test_case.get('niveau', 'facile')
        
        # Vérifications spécifiques par niveau
        if niveau == "facile":
            # Vérification prix/tarifs
            if 'tarif' in reponse_attendue:
                if str(reponse_attendue['tarif']) in response or f"{reponse_attendue['tarif']} fcfa" in response_lower:
                    score += 40
            if 'prix' in reponse_attendue:
                if str(reponse_attendue['prix']) in response or f"{reponse_attendue['prix']} fcfa" in response_lower:
                    score += 40
            
            # Vérification zones
            if 'zone' in reponse_attendue:
                if reponse_attendue['zone'] == 'centrale' and any(zone in response_lower for zone in ['yopougon', 'cocody', 'plateau']):
                    score += 20
        
        elif niveau == "moyen":
            # Vérifications plus complexes
            if 'delai' in reponse_attendue and 'jour' in response_lower:
                score += 30
            if 'total' in reponse_attendue:
                total_attendu = reponse_attendue['total']
                if str(total_attendu) in response or f"{total_attendu} fcfa" in response_lower:
                    score += 40
            if 'condition' in reponse_attendue and '11h' in response_lower:
                score += 30
        
        elif niveau in ["difficile", "expert"]:
            # Logique métier avancée
            if 'taille' in reponse_attendue:
                score += 25
            if 'livraison_possible' in reponse_attendue and reponse_attendue['livraison_possible']:
                if 'possible' in response_lower or 'oui' in response_lower:
                    score += 25
            if 'zones' in reponse_attendue:
                zones_trouvees = sum(1 for zone in reponse_attendue['zones'] if zone in response_lower)
                score += (zones_trouvees / len(reponse_attendue['zones'])) * 25
            if 'economie' in reponse_attendue:
                score += 25
        
        elif niveau == "piege":
            # Tests de robustesse
            if 'gratuite' in reponse_attendue and not reponse_attendue['gratuite']:
                if 'gratuit' not in response_lower or 'pas gratuit' in response_lower:
                    score += 50
            if 'impossible' in reponse_attendue and reponse_attendue['impossible']:
                if 'impossible' in response_lower or 'pas possible' in response_lower:
                    score += 50
        
        # Bonus pour cohérence et complétude
        if len(response) > 50:  # Réponse substantielle
            score += 10
        if any(word in response_lower for word in ['fcfa', 'livraison', 'commande']):  # Vocabulaire métier
            score += 10
        
        return min(100, score)
    
    def _calculate_sophistication_score(self, rag_result: Dict, context_used: str) -> float:
        """🔧 Calcule le score de sophistication technique (0-100)"""
        score = 0.0
        
        # 1. Méthode de recherche utilisée (30 points)
        search_method = rag_result.get('search_method', '')
        if search_method == 'meilisearch':
            score += 30  # Meilleure méthode
        elif search_method == 'supabase_fallback':
            score += 20  # Fallback fonctionnel
        elif search_method == 'fallback':
            score += 10  # Fallback d'urgence
        
        # 2. Extraction d'entités (25 points)
        entities_count = self._count_entities_in_context(context_used)
        if entities_count >= 10:
            score += 25
        elif entities_count >= 5:
            score += 20
        elif entities_count >= 3:
            score += 15
        elif entities_count >= 1:
            score += 10
        
        # 3. Richesse du contexte (20 points)
        context_length = len(context_used)
        if context_length >= 2000:
            score += 20
        elif context_length >= 1000:
            score += 15
        elif context_length >= 500:
            score += 10
        elif context_length >= 100:
            score += 5
        
        # 4. Confiance du système (15 points)
        confidence = rag_result.get('confidence', 0.0)
        score += confidence * 15
        
        # 5. Détection de patterns regex (10 points)
        if '[REGEX' in context_used:
            regex_patterns = context_used.count('[REGEX')
            score += min(10, regex_patterns * 2)
        
        return min(100, score)
    
    def _calculate_performance_score(self, processing_time: float, search_method: str) -> float:
        """⚡ Calcule le score de performance (0-100)"""
        score = 0.0
        
        # 1. Temps de traitement (70 points)
        if processing_time <= 2000:  # < 2s
            score += 70
        elif processing_time <= 5000:  # < 5s
            score += 60
        elif processing_time <= 10000:  # < 10s
            score += 50
        elif processing_time <= 15000:  # < 15s
            score += 40
        elif processing_time <= 20000:  # < 20s
            score += 30
        else:  # > 20s
            score += 20
        
        # 2. Efficacité de la méthode (20 points)
        if search_method == 'meilisearch':
            score += 20  # Méthode optimale
        elif search_method == 'supabase_fallback':
            score += 15  # Fallback acceptable
        else:
            score += 10  # Autres méthodes
        
        # 3. Bonus stabilité (10 points)
        if processing_time > 0:  # Pas d'erreur
            score += 10
        
        return min(100, score)
    
    def _count_entities_in_context(self, context: str) -> int:
        """📊 Compte les entités extraites dans le contexte"""
        if not context:
            return 0
        
        # Compter les patterns [REGEX ...] 
        regex_count = context.count('[REGEX')
        
        # Compter les entités métier connues
        entity_patterns = [
            'montant_fcfa', 'zone_geographique', 'tarif_livraison', 'delai_livraison',
            'acompte', 'phone', 'whatsapp', 'email', 'zones_couvertes', 'modes_paiement',
            'condition_commande', 'pourcentage', 'assistant_ia', 'secteur_activite'
        ]
        
        entity_count = sum(1 for pattern in entity_patterns if pattern in context)
        
        return max(regex_count, entity_count)
    
    def _calculate_global_metrics(self, results: List[BenchmarkResult], total_time: float) -> Dict[str, Any]:
        """📈 Calcule les métriques globales du benchmark"""
        if not results:
            return {}
        
        # Métriques de base
        total_tests = len(results)
        successful_tests = len([r for r in results if r.overall_score > 0])
        
        # Scores moyens
        avg_relevance = sum(r.relevance_score for r in results) / total_tests
        avg_sophistication = sum(r.sophistication_score for r in results) / total_tests
        avg_performance = sum(r.performance_score for r in results) / total_tests
        avg_overall = sum(r.overall_score for r in results) / total_tests
        
        # Temps de traitement
        avg_processing_time = sum(r.processing_time_ms for r in results) / total_tests
        min_processing_time = min(r.processing_time_ms for r in results)
        max_processing_time = max(r.processing_time_ms for r in results)
        
        # Méthodes de recherche
        search_methods = {}
        for result in results:
            method = result.search_method
            search_methods[method] = search_methods.get(method, 0) + 1
        
        # Entités extraites
        total_entities = sum(r.entities_extracted for r in results)
        avg_entities = total_entities / total_tests
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": (successful_tests / total_tests) * 100,
            "scores": {
                "relevance": avg_relevance,
                "sophistication": avg_sophistication,
                "performance": avg_performance,
                "overall": avg_overall
            },
            "timing": {
                "total_time": total_time,
                "avg_processing_time": avg_processing_time,
                "min_processing_time": min_processing_time,
                "max_processing_time": max_processing_time
            },
            "search_methods": search_methods,
            "entities": {
                "total_extracted": total_entities,
                "avg_per_query": avg_entities
            }
        }
    
    def _generate_final_report(self, results: List[BenchmarkResult], metrics: Dict[str, Any]):
        """📋 Génère le rapport final détaillé"""
        print("\n" + "🏆" + "="*79)
        print("🏆 RAPPORT FINAL - ULTIMATE RAG BENCHMARK")
        print("🏆" + "="*79)
        
        # Résumé exécutif
        print(f"\n📊 RÉSUMÉ EXÉCUTIF:")
        print(f"   • Tests exécutés: {metrics['total_tests']}")
        print(f"   • Taux de succès: {metrics['success_rate']:.1f}%")
        print(f"   • Score global: {metrics['scores']['overall']:.1f}/100")
        print(f"   • Temps total: {metrics['timing']['total_time']:.1f}s")
        
        # Scores détaillés
        print(f"\n🎯 SCORES DÉTAILLÉS:")
        print(f"   • Pertinence métier: {metrics['scores']['relevance']:.1f}/100")
        print(f"   • Sophistication technique: {metrics['scores']['sophistication']:.1f}/100")
        print(f"   • Performance système: {metrics['scores']['performance']:.1f}/100")
        
        # Performance temporelle
        print(f"\n⚡ PERFORMANCE TEMPORELLE:")
        print(f"   • Temps moyen: {metrics['timing']['avg_processing_time']:.0f}ms")
        print(f"   • Temps minimum: {metrics['timing']['min_processing_time']:.0f}ms")
        print(f"   • Temps maximum: {metrics['timing']['max_processing_time']:.0f}ms")
        
        # Méthodes de recherche
        print(f"\n🔍 MÉTHODES DE RECHERCHE:")
        for method, count in metrics['search_methods'].items():
            percentage = (count / metrics['total_tests']) * 100
            print(f"   • {method}: {count} fois ({percentage:.1f}%)")
        
        # Extraction d'entités
        print(f"\n🧠 EXTRACTION D'ENTITÉS:")
        print(f"   • Total extraites: {metrics['entities']['total_extracted']}")
        print(f"   • Moyenne par requête: {metrics['entities']['avg_per_query']:.1f}")
        
        # Top 3 des meilleurs résultats
        print(f"\n🥇 TOP 3 MEILLEURS RÉSULTATS:")
        sorted_results = sorted(results, key=lambda x: x.overall_score, reverse=True)[:3]
        for i, result in enumerate(sorted_results, 1):
            print(f"   {i}. Score: {result.overall_score:.1f}/100 - {result.question[:50]}...")
        
        # Top 3 des moins bons résultats
        print(f"\n🔴 TOP 3 RÉSULTATS À AMÉLIORER:")
        worst_results = sorted(results, key=lambda x: x.overall_score)[:3]
        for i, result in enumerate(worst_results, 1):
            print(f"   {i}. Score: {result.overall_score:.1f}/100 - {result.question[:50]}...")
        
        print(f"\n🎯 RECOMMANDATIONS:")
        if metrics['scores']['performance'] < 70:
            print("   • Optimiser les temps de réponse (< 5s recommandé)")
        if metrics['scores']['sophistication'] < 70:
            print("   • Améliorer l'extraction d'entités et l'enrichissement du contexte")
        if metrics['scores']['relevance'] < 70:
            print("   • Affiner la pertinence métier des réponses")
        if metrics['success_rate'] < 90:
            print("   • Renforcer la robustesse du système (gestion d'erreurs)")
        
        print(f"\n✅ BENCHMARK TERMINÉ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """🚀 Point d'entrée principal"""
    company_id = sys.argv[1] if len(sys.argv) > 1 else "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    
    benchmark = UltimateRAGBenchmark(company_id)
    results = await benchmark.run_ultimate_benchmark()
    
    # Sauvegarde des résultats
    output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Résultats sauvegardés dans: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
