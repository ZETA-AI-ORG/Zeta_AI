#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC LOGGER - Logs détaillés pour debugging RAG
Module dédié aux logs de diagnostic pour analyser le routing des documents
"""

import time
from typing import Dict, List, Any, Optional

class DiagnosticLogger:
    """Logger spécialisé pour le diagnostic du système RAG"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.session_start = time.time()
    
    def log_query_combinations(self, query_combinations: List[str], total_queries: int):
        """Log des combinaisons de requêtes générées"""
        if not self.enabled:
            return
            
        print(f"\n{'🔄'*40}")
        print(f"🔍 COMBINAISONS DE REQUÊTES GÉNÉRÉES")
        print(f"📊 TOTAL: {total_queries} requêtes")
        print(f"{'🔄'*40}")
        
        for i, combo in enumerate(query_combinations[:10], 1):  # Afficher les 10 premières
            print(f"   {i:2d}. '{combo}'")
        
        if len(query_combinations) > 10:
            print(f"   ... et {len(query_combinations) - 10} autres")
        
        print(f"{'🔄'*40}\n")
    
    def log_index_detailed_results(self, index_name: str, query: str, results: List[Dict], hits_count: int):
        """Log détaillé des résultats par index avec contenu complet"""
        if not self.enabled:
            return
            
        print(f"\n{'='*80}")
        print(f"🔍 INDEX DÉTAILLÉ: {index_name}")
        print(f"🔎 QUERY: '{query}'")
        print(f"📊 HITS BRUTS: {hits_count}")
        print(f"📊 DOCUMENTS ANALYSÉS: {len(results)}")
        print(f"{'='*80}")
        
        if not results:
            print("   ❌ Aucun document trouvé")
            print(f"{'='*80}\n")
            return
        
        for i, doc in enumerate(results, 1):
            print(f"\n📄 DOCUMENT {i}/{len(results)}")
            print(f"   🆔 ID: {doc.get('id', 'N/A')}")
            print(f"   ⭐ SCORE: {doc.get('_score', doc.get('score', 'N/A'))}")
            print(f"   🏷️ TYPE: {doc.get('type', 'N/A')}")
            print(f"   📝 CONTENU COMPLET:")
            print(f"   {'-'*60}")
            
            # Afficher le contenu complet du document
            content = doc.get('searchable_text', doc.get('content', 'Contenu non disponible'))
            print(f"   {content}")
            print(f"   {'-'*60}")
            
            # Métadonnées additionnelles
            metadata = {k: v for k, v in doc.items() 
                       if k not in ['searchable_text', 'content', '_score', 'score']}
            if metadata:
                print(f"   📋 MÉTADONNÉES: {metadata}")
        
        print(f"\n{'='*80}\n")
    
    def log_document_scoring_process(self, all_docs_by_index: Dict[str, List[Dict]]):
        """Log du processus de scoring et filtrage par index"""
        if not self.enabled:
            return
            
        print(f"\n{'📈'*40}")
        print(f"🧮 PROCESSUS DE SCORING ET FILTRAGE")
        print(f"{'📈'*40}")
        
        for index_name, docs in all_docs_by_index.items():
            if docs:
                scores = [doc.get('_score', doc.get('score', 0)) for doc in docs]
                avg_score = sum(scores) / len(scores) if scores else 0
                max_score = max(scores) if scores else 0
                min_score = min(scores) if scores else 0
                
                print(f"\n📊 INDEX: {index_name}")
                print(f"   📄 Documents: {len(docs)}")
                print(f"   ⭐ Score moyen: {avg_score:.3f}")
                print(f"   🏆 Score max: {max_score:.3f}")
                print(f"   ⬇️ Score min: {min_score:.3f}")
                
                # Analyse de pertinence par index
                self._analyze_index_relevance(index_name, docs, avg_score)
        
        print(f"\n{'📈'*40}\n")
    
    def _analyze_index_relevance(self, index_name: str, docs: List[Dict], avg_score: float):
        """Analyse la pertinence d'un index pour une requête"""
        index_type = self._get_index_type(index_name)
        
        if index_type == 'products' and avg_score > 3:
            relevance = "✅ TRÈS PERTINENT"
        elif index_type in ['delivery', 'localisation', 'support'] and avg_score < 1:
            relevance = "⚠️ SUSPECT - Score trop faible"
        elif index_type in ['delivery', 'localisation', 'support'] and avg_score < 2:
            relevance = "🟡 DOUTEUX - Vérifier pertinence"
        else:
            relevance = "🟢 ACCEPTABLE"
        
        print(f"   🎯 PERTINENCE: {relevance}")
        
        # Suggestions d'amélioration
        if "SUSPECT" in relevance or "DOUTEUX" in relevance:
            print(f"   💡 SUGGESTION: Revoir le routing pour {index_type}")
    
    def _get_index_type(self, index_name: str) -> str:
        """Détermine le type d'index"""
        if 'products' in index_name:
            return 'products'
        elif 'delivery' in index_name:
            return 'delivery'
        elif 'localisation' in index_name:
            return 'localisation'
        elif 'support' in index_name:
            return 'support'
        else:
            return 'unknown'
    
    def log_final_selection(self, selected_docs: List[Dict], total_found: int, query: str):
        """Log des documents finalement sélectionnés pour le LLM"""
        if not self.enabled:
            return
            
        print(f"\n{'🎯'*50}")
        print(f"📤 SÉLECTION FINALE POUR LE LLM")
        print(f"📊 SÉLECTIONNÉS: {len(selected_docs)} / {total_found} trouvés")
        print(f"🔍 REQUÊTE: '{query}'")
        print(f"{'🎯'*50}")
        
        if not selected_docs:
            print("   ❌ Aucun document sélectionné")
            print(f"{'🎯'*50}\n")
            return
        
        for i, doc in enumerate(selected_docs, 1):
            print(f"\n✅ DOCUMENT SÉLECTIONNÉ {i}")
            print(f"   🏷️ INDEX SOURCE: {doc.get('index_name', 'N/A')}")
            print(f"   🆔 ID: {doc.get('id', 'N/A')}")
            print(f"   ⭐ SCORE FINAL: {doc.get('score', 'N/A')}")
            print(f"   🔍 REQUÊTE ORIGINE: {doc.get('search_query', 'N/A')}")
            print(f"   📏 TAILLE: {len(doc.get('content', ''))} chars")
            print(f"   📝 EXTRAIT (150 premiers chars):")
            content = doc.get('content', '')[:150]
            print(f"   '{content}...'")
            
            # Analyse de la sélection
            self._analyze_selection_reason(doc, query)
        
        print(f"\n{'🎯'*50}\n")
    
    def _analyze_selection_reason(self, doc: Dict, query: str):
        """Analyse pourquoi un document a été sélectionné"""
        category = doc.get('category', '')
        score = doc.get('score', 0)
        content = doc.get('content', '').lower()
        query_lower = query.lower()
        
        # Analyser les mots-clés de la requête dans le contenu
        query_words = query_lower.split()
        found_words = [word for word in query_words if word in content]
        
        reasons = []
        
        if score > 3:
            reasons.append("Score élevé")
        
        if len(found_words) > 0:
            reasons.append(f"Mots-clés trouvés: {', '.join(found_words)}")
        
        if category == 'produits' and any(word in content for word in ['paquet', 'couche', 'prix', 'fcfa']):
            reasons.append("Contenu produit pertinent")
        elif category in ['delivery', 'localisation', 'support'] and score < 1:
            reasons.append("⚠️ Score faible - Routing suspect")
        
        if not reasons:
            reasons.append("Raison inconnue")
        
        print(f"   🎯 RAISON SÉLECTION: {' | '.join(reasons)}")
    
    def log_routing_analysis(self, query: str, results_by_index: Dict[str, List]):
        """Analyse globale du routing pour une requête"""
        if not self.enabled:
            return
            
        print(f"\n{'🧭'*40}")
        print(f"🧭 ANALYSE ROUTING GLOBAL")
        print(f"🔍 REQUÊTE: '{query}'")
        print(f"{'🧭'*40}")
        
        query_lower = query.lower()
        
        # Analyser le type de requête
        if any(word in query_lower for word in ['prix', 'coût', 'combien', 'tarif', 'fcfa']):
            expected_indexes = ['products']
            query_type = "PRIX/PRODUIT"
        elif any(word in query_lower for word in ['livraison', 'livrer', 'délai', 'transport']):
            expected_indexes = ['delivery', 'products']
            query_type = "LIVRAISON"
        elif any(word in query_lower for word in ['adresse', 'localisation', 'où', 'zone']):
            expected_indexes = ['localisation', 'delivery']
            query_type = "LOCALISATION"
        elif any(word in query_lower for word in ['paiement', 'payer', 'wave', 'mobile money']):
            expected_indexes = ['support']
            query_type = "PAIEMENT"
        else:
            expected_indexes = ['products']
            query_type = "GÉNÉRAL"
        
        print(f"   🎯 TYPE DÉTECTÉ: {query_type}")
        print(f"   📋 INDEX ATTENDUS: {', '.join(expected_indexes)}")
        
        # Analyser les index qui ont retourné des résultats
        actual_indexes = list(results_by_index.keys())
        print(f"   📊 INDEX ACTIVÉS: {', '.join(actual_indexes) if actual_indexes else 'Aucun'}")
        
        # Évaluer la pertinence du routing
        relevant_count = sum(1 for idx in actual_indexes if any(exp in idx for exp in expected_indexes))
        irrelevant_count = len(actual_indexes) - relevant_count
        
        if irrelevant_count == 0:
            routing_quality = "✅ EXCELLENT"
        elif irrelevant_count <= 1:
            routing_quality = "🟡 ACCEPTABLE"
        else:
            routing_quality = "❌ PROBLÉMATIQUE"
        
        print(f"   🎯 QUALITÉ ROUTING: {routing_quality}")
        print(f"   📊 Index pertinents: {relevant_count}/{len(actual_indexes)}")
        
        if irrelevant_count > 0:
            print(f"   ⚠️ RECOMMANDATION: Implémenter filtrage par score de pertinence")
        
        print(f"{'🧭'*40}\n")

# Instance globale
diagnostic_logger = DiagnosticLogger(enabled=True)

def enable_diagnostic_logs():
    """Active les logs de diagnostic"""
    diagnostic_logger.enabled = True

def disable_diagnostic_logs():
    """Désactive les logs de diagnostic"""
    diagnostic_logger.enabled = False
