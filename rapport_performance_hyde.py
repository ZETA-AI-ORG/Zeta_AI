#!/usr/bin/env python3
"""
RAPPORT DE PERFORMANCE SYSTÈME HYDE
Analyse détaillée des données d'ingestion pour évaluer l'efficacité du scoring HyDE
"""

import json
from typing import Dict, List, Set
import asyncio
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.hyde_word_scorer import HydeWordScorer

class HydePerformanceAnalyzer:
    def __init__(self):
        self.scorer = HydeWordScorer()
        
    def extract_business_words(self, ingestion_data: Dict) -> Set[str]:
        """Extrait tous les mots métier des données d'ingestion"""
        business_words = set()
        
        # Extraire des échantillons de documents
        sample_docs = ingestion_data.get("verification", {}).get("sample_documents", {})
        
        for category, docs in sample_docs.items():
            for doc in docs:
                # Extraire les mots clés spécifiques au business
                if "color" in doc:
                    business_words.add(doc["color"].lower())
                if "attributes" in doc:
                    for attr_value in doc["attributes"].values():
                        if isinstance(attr_value, str):
                            business_words.add(attr_value.lower().strip())
                if "tags" in doc:
                    business_words.update([tag.lower() for tag in doc["tags"]])
                if "zone" in doc:
                    business_words.add(doc["zone"].lower())
                if "method" in doc:
                    business_words.add(doc["method"].lower())
                if "sector" in doc:
                    business_words.add(doc["sector"].lower().replace("&", "").replace(" ", "_"))
                
        # Nettoyer les mots génériques
        generic_words = {"product", "document", "company", "location", "payment", "support", "delivery"}
        business_words = business_words - generic_words
        
        return business_words
    
    async def analyze_word_coverage(self, business_words: Set[str]) -> Dict:
        """Analyse la couverture des mots métier par le système HyDE"""
        coverage_analysis = {
            "total_business_words": len(business_words),
            "covered_in_base_cache": 0,
            "scored_by_groq": 0,
            "low_scored_words": [],
            "missing_critical_words": [],
            "score_distribution": {"10": [], "8-9": [], "6-7": [], "3-5": [], "0-2": []},
            "detailed_scores": {}
        }
        
        for word in business_words:
            word_lower = word.lower()
            
            # Vérifier si c'est un stop word (score 0)
            if word_lower in self.scorer.stop_words:
                score = 0
                coverage_analysis["covered_in_base_cache"] += 1
            # Vérifier si c'est un mot critique (score 10)
            elif word_lower in self.scorer.critical_words:
                score = 10
                coverage_analysis["covered_in_base_cache"] += 1
            else:
                # Mot à scorer contextuellement
                word_dict = await self.scorer.score_query_words(word, "e-commerce")
                score = word_dict.get(word, 5)
                coverage_analysis["scored_by_groq"] += 1
            
            coverage_analysis["detailed_scores"][word] = score
            
            # Classification par score
            if score == 10:
                coverage_analysis["score_distribution"]["10"].append(word)
            elif score >= 8:
                coverage_analysis["score_distribution"]["8-9"].append(word)
            elif score >= 6:
                coverage_analysis["score_distribution"]["6-7"].append(word)
            elif score >= 3:
                coverage_analysis["score_distribution"]["3-5"].append(word)
            else:
                coverage_analysis["score_distribution"]["0-2"].append(word)
            
            # Identifier les mots critiques mal scorés
            if score <= 5 and word in ["bleu", "gris", "vert", "jaune", "violet", "rose"]:
                coverage_analysis["missing_critical_words"].append(f"{word}:{score}")
            
            if score <= 3:
                coverage_analysis["low_scored_words"].append(f"{word}:{score}")
        
        return coverage_analysis
    
    def calculate_performance_score(self, coverage_analysis: Dict, ingestion_data: Dict) -> Dict:
        """Calcule une note de performance sur 100"""
        
        # Critères d'évaluation
        criteria = {
            "coverage_rate": 0,      # 25 points - Couverture des mots métier
            "score_accuracy": 0,     # 30 points - Précision des scores
            "critical_words": 0,     # 25 points - Gestion des mots critiques
            "consistency": 0,        # 20 points - Cohérence du système
        }
        
        total_words = coverage_analysis["total_business_words"]
        
        # 1. COUVERTURE (25 points)
        if total_words > 0:
            coverage_rate = (coverage_analysis["covered_in_base_cache"] / total_words) * 100
            if coverage_rate >= 80:
                criteria["coverage_rate"] = 25
            elif coverage_rate >= 60:
                criteria["coverage_rate"] = 20
            elif coverage_rate >= 40:
                criteria["coverage_rate"] = 15
            elif coverage_rate >= 20:
                criteria["coverage_rate"] = 10
            else:
                criteria["coverage_rate"] = 5
        
        # 2. PRÉCISION DES SCORES (30 points)
        high_score_words = len(coverage_analysis["score_distribution"]["10"]) + len(coverage_analysis["score_distribution"]["8-9"])
        low_score_words = len(coverage_analysis["score_distribution"]["0-2"])
        
        if total_words > 0:
            precision_rate = (high_score_words / total_words) * 100
            if precision_rate >= 70:
                criteria["score_accuracy"] = 30
            elif precision_rate >= 50:
                criteria["score_accuracy"] = 25
            elif precision_rate >= 30:
                criteria["score_accuracy"] = 20
            elif precision_rate >= 15:
                criteria["score_accuracy"] = 15
            else:
                criteria["score_accuracy"] = 10
        
        # 3. MOTS CRITIQUES (25 points)
        critical_colors = ["bleu", "gris", "rouge", "noir", "blanc", "vert", "jaune"]
        critical_found = 0
        critical_well_scored = 0
        
        for word in critical_colors:
            if word in coverage_analysis["detailed_scores"]:
                critical_found += 1
                if coverage_analysis["detailed_scores"][word] >= 8:
                    critical_well_scored += 1
        
        if critical_found > 0:
            critical_rate = (critical_well_scored / critical_found) * 100
            if critical_rate >= 90:
                criteria["critical_words"] = 25
            elif critical_rate >= 70:
                criteria["critical_words"] = 20
            elif critical_rate >= 50:
                criteria["critical_words"] = 15
            elif critical_rate >= 30:
                criteria["critical_words"] = 10
            else:
                criteria["critical_words"] = 5
        
        # 4. COHÉRENCE (20 points)
        # Vérifier la cohérence des scores similaires
        color_scores = {}
        for word, score in coverage_analysis["detailed_scores"].items():
            if word in critical_colors:
                color_scores[word] = score
        
        if len(color_scores) > 1:
            scores_values = list(color_scores.values())
            score_variance = max(scores_values) - min(scores_values)
            
            if score_variance <= 2:
                criteria["consistency"] = 20
            elif score_variance <= 4:
                criteria["consistency"] = 15
            elif score_variance <= 6:
                criteria["consistency"] = 10
            else:
                criteria["consistency"] = 5
        else:
            criteria["consistency"] = 15  # Score neutre si pas assez de données
        
        total_score = sum(criteria.values())
        
        return {
            "total_score": total_score,
            "grade": self._get_grade(total_score),
            "criteria_breakdown": criteria,
            "recommendations": self._generate_recommendations(coverage_analysis, criteria)
        }
    
    def _get_grade(self, score: int) -> str:
        """Convertit le score en note littérale"""
        if score >= 90:
            return "A+ (Excellent)"
        elif score >= 80:
            return "A (Très Bien)"
        elif score >= 70:
            return "B+ (Bien)"
        elif score >= 60:
            return "B (Assez Bien)"
        elif score >= 50:
            return "C (Moyen)"
        elif score >= 40:
            return "D (Insuffisant)"
        else:
            return "F (Très Insuffisant)"
    
    def _generate_recommendations(self, coverage_analysis: Dict, criteria: Dict) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        if criteria["coverage_rate"] < 20:
            recommendations.append("🔴 CRITIQUE: Ajouter plus de mots métier au cache de base")
        
        if criteria["score_accuracy"] < 25:
            recommendations.append("🔴 CRITIQUE: Revoir la logique de scoring Groq")
        
        if criteria["critical_words"] < 20:
            recommendations.append("🔴 CRITIQUE: Ajouter toutes les couleurs au cache avec score 10")
            recommendations.append("   → Ajouter: bleu:10, gris:10, vert:10, jaune:10, etc.")
        
        if criteria["consistency"] < 15:
            recommendations.append("🟡 AMÉLIORATION: Harmoniser les scores des mots similaires")
        
        if len(coverage_analysis["missing_critical_words"]) > 0:
            recommendations.append(f"🔴 MOTS CRITIQUES MAL SCORÉS: {', '.join(coverage_analysis['missing_critical_words'])}")
        
        return recommendations

async def main():
    # Données d'ingestion fournies par l'utilisateur
    ingestion_data = {
        "company_id": "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3",
        "success": True,
        "verification": {
            "total_documents": 23,
            "sample_documents": {
                "products": [
                    {"color": "BLEU", "attributes": {"Couleur": "BLEU"}, "tags": ["product", "casques_moto", "bleu"]},
                    {"color": "GRIS", "attributes": {"Couleur": "GRIS"}, "tags": ["product", "casques_moto", "gris"]},
                    {"color": "NOIR", "attributes": {"Couleur": "NOIR"}, "tags": ["product", "casques_moto", "noir"]}
                ],
                "delivery": [
                    {"zone": "Yopougon"}, {"zone": "Cocody"}, {"zone": "Plateau"}
                ],
                "support_paiement": [
                    {"method": "Wave"}, {"method": "Support"}
                ],
                "company_docs": [
                    {"sector": "Auto & Moto", "tags": ["company", "identity", "auto_moto"]}
                ]
            }
        }
    }
    
    analyzer = HydePerformanceAnalyzer()
    
    print("🔍 ANALYSE DE PERFORMANCE SYSTÈME HYDE")
    print("=" * 80)
    
    # 1. Extraction des mots métier
    business_words = analyzer.extract_business_words(ingestion_data)
    print(f"📊 MOTS MÉTIER IDENTIFIÉS: {len(business_words)}")
    print(f"   {', '.join(sorted(business_words))}")
    
    # 2. Analyse de couverture
    print("\n🔍 ANALYSE DE COUVERTURE...")
    coverage_analysis = await analyzer.analyze_word_coverage(business_words)
    
    # 3. Calcul de performance
    performance = analyzer.calculate_performance_score(coverage_analysis, ingestion_data)
    
    # 4. Rapport détaillé
    print(f"\n🎯 NOTE FINALE: {performance['total_score']}/100 - {performance['grade']}")
    print("=" * 80)
    
    print("\n📊 DÉTAIL DES CRITÈRES:")
    for criterion, score in performance['criteria_breakdown'].items():
        max_score = {"coverage_rate": 25, "score_accuracy": 30, "critical_words": 25, "consistency": 20}[criterion]
        print(f"   {criterion.replace('_', ' ').title()}: {score}/{max_score}")
    
    print(f"\n📈 COUVERTURE:")
    print(f"   Cache de base: {coverage_analysis['covered_in_base_cache']}/{coverage_analysis['total_business_words']}")
    print(f"   Scoré par Groq: {coverage_analysis['scored_by_groq']}/{coverage_analysis['total_business_words']}")
    
    print(f"\n🎯 RÉPARTITION DES SCORES:")
    for category, words in coverage_analysis['score_distribution'].items():
        if words:
            print(f"   {category}: {len(words)} mots - {', '.join(words[:5])}{'...' if len(words) > 5 else ''}")
    
    print(f"\n🔴 PROBLÈMES IDENTIFIÉS:")
    if coverage_analysis['missing_critical_words']:
        print(f"   Mots critiques mal scorés: {', '.join(coverage_analysis['missing_critical_words'])}")
    if coverage_analysis['low_scored_words']:
        print(f"   Mots faiblement scorés: {', '.join(coverage_analysis['low_scored_words'][:10])}")
    
    print(f"\n💡 RECOMMANDATIONS:")
    for i, rec in enumerate(performance['recommendations'], 1):
        print(f"   {i}. {rec}")
    
    print(f"\n📋 SCORES DÉTAILLÉS:")
    for word, score in sorted(coverage_analysis['detailed_scores'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {word}: {score}")

if __name__ == "__main__":
    asyncio.run(main())
