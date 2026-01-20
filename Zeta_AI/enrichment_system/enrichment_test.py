#!/usr/bin/env python3
"""
🧪 TEST ENRICHISSEMENT LLM - Données pourries → Données propres
Lance l'agent sur des données volontairement mauvaises et évalue les résultats
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from data_quality_agent import get_data_quality_agent
from test_data_generator import generate_messy_test_data

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

class EnrichmentTester:
    """Testeur du système d'enrichissement"""
    
    def __init__(self):
        self.agent = get_data_quality_agent()
        self.results = []
    
    async def run_full_test(self):
        """Lance le test complet sur toutes les données pourries"""
        
        print(f"\n{Colors.BOLD}{'='*100}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}🧪 TEST D'ENRICHISSEMENT LLM - DONNÉES POURRIES{Colors.END}")
        print(f"{Colors.BOLD}{'='*100}{Colors.END}\n")
        
        # Générer données test
        messy_data = generate_messy_test_data()
        print(f"{Colors.YELLOW}📊 Total documents à traiter: {len(messy_data)}{Colors.END}\n")
        
        # Traiter chaque document
        for i, messy_doc in enumerate(messy_data, 1):
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'─'*100}{Colors.END}")
            print(f"{Colors.BOLD}📄 TEST {i}/{len(messy_data)}: {messy_doc['id']}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{'─'*100}{Colors.END}\n")
            
            # Enrichir
            enriched_doc = await self.agent.enrich_document(messy_doc)
            
            # Évaluer
            evaluation = self._evaluate_enrichment(messy_doc, enriched_doc)
            
            # Afficher résultats
            self._display_comparison(messy_doc, enriched_doc, evaluation)
            
            # Sauvegarder
            self.results.append({
                'test_id': messy_doc['id'],
                'original': messy_doc,
                'enriched': enriched_doc,
                'evaluation': evaluation
            })
            
            await asyncio.sleep(0.5)  # Pause pour lisibilité
        
        # Résumé final
        self._display_final_summary()
        
        # Sauvegarder résultats
        self._save_results()
    
    def _evaluate_enrichment(self, original: Dict, enriched: Dict) -> Dict:
        """
        Évalue la qualité de l'enrichissement
        
        Returns:
            {
                'score': float,
                'corrections_count': int,
                'clarifications_count': int,
                'issues_fixed': List[str],
                'issues_remaining': List[str]
            }
        """
        metadata = enriched.get('_metadata', {})
        
        corrections_count = len(metadata.get('corrections', []))
        clarifications_count = len(metadata.get('clarifications', []))
        
        # Vérifier quels problèmes attendus ont été résolus
        expected_issues = original.get('expected_issues', [])
        issues_fixed = []
        issues_remaining = []
        
        for issue in expected_issues:
            if 'Faute:' in issue:
                # Vérifier si faute corrigée
                if corrections_count > 0:
                    issues_fixed.append(issue)
                else:
                    issues_remaining.append(issue)
            elif 'Ambiguïté:' in issue:
                # Vérifier si clarification ajoutée
                if clarifications_count > 0:
                    issues_fixed.append(issue)
                else:
                    issues_remaining.append(issue)
            else:
                # Autres problèmes
                issues_remaining.append(issue)
        
        # Score basé sur problèmes résolus
        if expected_issues:
            score = len(issues_fixed) / len(expected_issues)
        else:
            score = 1.0
        
        # Bonus si confiance élevée
        confidence = metadata.get('confidence', 0)
        score = (score + confidence) / 2
        
        return {
            'score': score,
            'corrections_count': corrections_count,
            'clarifications_count': clarifications_count,
            'issues_fixed': issues_fixed,
            'issues_remaining': issues_remaining,
            'confidence': confidence
        }
    
    def _display_comparison(self, original: Dict, enriched: Dict, evaluation: Dict):
        """Affiche comparaison AVANT/APRÈS"""
        
        print(f"\n{Colors.CYAN}📋 DOCUMENT ORIGINAL:{Colors.END}")
        print(f"{Colors.RED}{'┌' + '─'*98 + '┐'}{Colors.END}")
        print(f"{Colors.RED}│{Colors.END} Nom: {original.get('product_name', 'N/A'):<93}{Colors.RED}│{Colors.END}")
        print(f"{Colors.RED}│{Colors.END} Description: {original.get('description', 'N/A')[:88]:<88}{Colors.RED}│{Colors.END}")
        if len(original.get('description', '')) > 88:
            desc_continue = original.get('description', '')[88:176]
            print(f"{Colors.RED}│{Colors.END}              {desc_continue:<88}{Colors.RED}│{Colors.END}")
        print(f"{Colors.RED}│{Colors.END} Notes: {original.get('notes', 'N/A')[:91]:<91}{Colors.RED}│{Colors.END}")
        print(f"{Colors.RED}└{'─'*98}┘{Colors.END}")
        
        print(f"\n{Colors.GREEN}✨ DOCUMENT ENRICHI:{Colors.END}")
        print(f"{Colors.GREEN}┌{'─'*98}┐{Colors.END}")
        enriched_desc = enriched.get('enriched_description', enriched.get('description', 'N/A'))[:88]
        print(f"{Colors.GREEN}│{Colors.END} Description: {enriched_desc:<88}{Colors.GREEN}│{Colors.END}")
        if len(enriched.get('enriched_description', '')) > 88:
            desc_continue = enriched.get('enriched_description', '')[88:176]
            print(f"{Colors.GREEN}│{Colors.END}              {desc_continue:<88}{Colors.GREEN}│{Colors.END}")
        print(f"{Colors.GREEN}└{'─'*98}┘{Colors.END}")
        
        # Métadonnées
        metadata = enriched.get('_metadata', {})
        print(f"\n{Colors.YELLOW}📊 AMÉLIORATIONS:{Colors.END}")
        print(f"   Corrections orthographe: {Colors.BOLD}{evaluation['corrections_count']}{Colors.END}")
        print(f"   Clarifications ajoutées: {Colors.BOLD}{evaluation['clarifications_count']}{Colors.END}")
        print(f"   Confiance: {Colors.BOLD}{evaluation['confidence']:.2f}{Colors.END}")
        
        # Issues résolus
        if evaluation['issues_fixed']:
            print(f"\n{Colors.GREEN}✅ PROBLÈMES RÉSOLUS: {len(evaluation['issues_fixed'])}{Colors.END}")
            for issue in evaluation['issues_fixed'][:3]:
                print(f"   {Colors.GREEN}•{Colors.END} {issue}")
            if len(evaluation['issues_fixed']) > 3:
                print(f"   {Colors.GREEN}•{Colors.END} ... et {len(evaluation['issues_fixed']) - 3} autres")
        
        # Issues restants
        if evaluation['issues_remaining']:
            print(f"\n{Colors.RED}⚠️ PROBLÈMES RESTANTS: {len(evaluation['issues_remaining'])}{Colors.END}")
            for issue in evaluation['issues_remaining'][:3]:
                print(f"   {Colors.RED}•{Colors.END} {issue}")
            if len(evaluation['issues_remaining']) > 3:
                print(f"   {Colors.RED}•{Colors.END} ... et {len(evaluation['issues_remaining']) - 3} autres")
        
        # Score final
        score_pct = evaluation['score'] * 100
        color = Colors.GREEN if score_pct >= 80 else Colors.YELLOW if score_pct >= 60 else Colors.RED
        print(f"\n{Colors.BOLD}{'─'*100}{Colors.END}")
        print(f"{Colors.BOLD}SCORE ENRICHISSEMENT: {color}{score_pct:.1f}%{Colors.END}")
        print(f"{Colors.BOLD}{'─'*100}{Colors.END}")
    
    def _display_final_summary(self):
        """Affiche le résumé final de tous les tests"""
        
        print(f"\n\n{Colors.BOLD}{Colors.MAGENTA}{'='*100}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}📊 RÉSUMÉ FINAL{Colors.END}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}{'='*100}{Colors.END}\n")
        
        total_tests = len(self.results)
        total_corrections = sum(r['evaluation']['corrections_count'] for r in self.results)
        total_clarifications = sum(r['evaluation']['clarifications_count'] for r in self.results)
        avg_score = sum(r['evaluation']['score'] for r in self.results) / total_tests if total_tests > 0 else 0
        
        # Tests par catégorie de score
        excellent = sum(1 for r in self.results if r['evaluation']['score'] >= 0.9)
        good = sum(1 for r in self.results if 0.7 <= r['evaluation']['score'] < 0.9)
        medium = sum(1 for r in self.results if 0.5 <= r['evaluation']['score'] < 0.7)
        poor = sum(1 for r in self.results if r['evaluation']['score'] < 0.5)
        
        print(f"{Colors.BOLD}📈 STATISTIQUES GLOBALES:{Colors.END}")
        print(f"   Total documents testés: {Colors.BOLD}{total_tests}{Colors.END}")
        print(f"   Total corrections: {Colors.BOLD}{total_corrections}{Colors.END}")
        print(f"   Total clarifications: {Colors.BOLD}{total_clarifications}{Colors.END}")
        print(f"   Score moyen: {Colors.BOLD}{avg_score*100:.1f}%{Colors.END}")
        
        print(f"\n{Colors.BOLD}🎯 RÉPARTITION PAR QUALITÉ:{Colors.END}")
        print(f"   {Colors.GREEN}Excellent (90%+):{Colors.END} {excellent}/{total_tests} {Colors.GREEN}{'█' * excellent}{Colors.END}")
        print(f"   {Colors.CYAN}Bon (70-90%):{Colors.END}     {good}/{total_tests} {Colors.CYAN}{'█' * good}{Colors.END}")
        print(f"   {Colors.YELLOW}Moyen (50-70%):{Colors.END}  {medium}/{total_tests} {Colors.YELLOW}{'█' * medium}{Colors.END}")
        print(f"   {Colors.RED}Faible (<50%):{Colors.END}    {poor}/{total_tests} {Colors.RED}{'█' * poor}{Colors.END}")
        
        # Verdict final
        print(f"\n{Colors.BOLD}{'─'*100}{Colors.END}")
        if avg_score >= 0.9:
            print(f"{Colors.BOLD}{Colors.GREEN}✅ VERDICT: SYSTÈME PRÊT POUR PRODUCTION (≥90%){Colors.END}")
            print(f"{Colors.GREEN}Le LLM gère excellemment les données pourries !{Colors.END}")
        elif avg_score >= 0.7:
            print(f"{Colors.BOLD}{Colors.YELLOW}⚠️ VERDICT: AMÉLIORATION NÉCESSAIRE (70-90%){Colors.END}")
            print(f"{Colors.YELLOW}Le LLM fonctionne bien mais nécessite des ajustements.{Colors.END}")
        else:
            print(f"{Colors.BOLD}{Colors.RED}❌ VERDICT: PAS PRÊT POUR PRODUCTION (<70%){Colors.END}")
            print(f"{Colors.RED}Le LLM nécessite des améliorations significatives.{Colors.END}")
        print(f"{Colors.BOLD}{'─'*100}{Colors.END}\n")
    
    def _save_results(self):
        """Sauvegarde les résultats dans un fichier JSON"""
        
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"enrichment_test_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(self.results),
                'results': self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"{Colors.GREEN}💾 Résultats sauvegardés: {filename}{Colors.END}\n")

async def main():
    """Point d'entrée principal"""
    tester = EnrichmentTester()
    await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())
