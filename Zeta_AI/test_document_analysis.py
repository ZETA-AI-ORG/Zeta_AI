#!/usr/bin/env python3
"""
🔍 TEST DIAGNOSTIC AVANCÉ - ANALYSE DES DOCUMENTS RAG
Détermine si les hallucinations viennent de documents non pertinents
ou d'un problème de génération LLM
"""

import asyncio
import json
import time
import requests
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class DocumentAnalysis:
    """Analyse d'un document trouvé par RAG"""
    question: str
    method_used: str
    documents_found: List[Dict]
    context_provided: str
    llm_response: str
    processing_time: float
    relevance_score: float
    hallucination_detected: bool
    document_quality: str

class RAGDocumentAnalyzer:
    """Analyseur de documents RAG pour détecter les causes d'hallucination"""
    
    def __init__(self):
        self.api_url = "http://127.0.0.1:8001/chat"
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.user_id = "testuser135"
        
        # Questions critiques qui ont échoué
        self.critical_questions = [
            {
                "question": "Quel est le prix exact de la taille 3 couches à pression?",
                "expected_answer": "22.900 FCFA",
                "category": "prix_exact"
            },
            {
                "question": "Avez-vous des couches de couleur rouge en stock?",
                "expected_answer": "Pas de couleurs spécifiques disponibles",
                "category": "hallucination_trap"
            },
            {
                "question": "Acceptez-vous les paiements par carte bancaire?",
                "expected_answer": "Wave uniquement",
                "category": "hallucination_trap"
            },
            {
                "question": "Comment puis-je économiser sur l'achat de couches culottes?",
                "expected_answer": "12 paquets à 48.000 FCFA ou 1 colis à 168.000 FCFA",
                "category": "optimisation"
            },
            {
                "question": "Quelle est votre mission en tant qu'entreprise?",
                "expected_answer": "Faciliter l'accès aux couches fiables et confortables en Côte d'Ivoire",
                "category": "mission"
            }
        ]
    
    async def send_question_with_debug(self, question: str) -> Dict[str, Any]:
        """Envoie une question avec debug activé pour voir les documents"""
        try:
            payload = {
                "message": question,
                "company_id": self.company_id,
                "user_id": self.user_id,
                "debug": True  # Activer le debug pour voir les documents
            }
            
            start_time = time.time()
            response = requests.post(self.api_url, json=payload, timeout=60)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("response", ""),
                    "method_used": data.get("search_method", "unknown"),
                    "confidence": data.get("confidence", 0.0),
                    "context": data.get("context", ""),
                    "documents": data.get("documents", []),
                    "debug_info": data.get("debug", {}),
                    "processing_time": processing_time
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "processing_time": processing_time
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0
            }
    
    def analyze_document_relevance(self, question: str, documents: List[Dict], expected_answer: str) -> Tuple[float, str]:
        """Analyse la pertinence des documents trouvés"""
        if not documents:
            return 0.0, "AUCUN_DOCUMENT"
        
        relevance_score = 0.0
        quality_issues = []
        
        # Analyser chaque document
        for doc in documents:
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            
            # Vérifier si le document contient des informations pertinentes
            question_lower = question.lower()
            expected_lower = expected_answer.lower()
            
            # Score basé sur la présence de mots-clés de la question
            question_words = question_lower.split()
            content_words = content.split()
            
            matches = sum(1 for word in question_words if word in content_words)
            if len(question_words) > 0:
                relevance_score += matches / len(question_words)
            
            # Vérifier si le document contient la réponse attendue
            if any(word in content for word in expected_lower.split()):
                relevance_score += 0.5
        
        # Normaliser le score
        if len(documents) > 0:
            relevance_score = relevance_score / len(documents)
        
        # Déterminer la qualité
        if relevance_score >= 0.8:
            quality = "EXCELLENT"
        elif relevance_score >= 0.6:
            quality = "BON"
        elif relevance_score >= 0.4:
            quality = "MOYEN"
        elif relevance_score >= 0.2:
            quality = "FAIBLE"
        else:
            quality = "TRÈS_FAIBLE"
        
        return relevance_score, quality
    
    def detect_hallucination_source(self, question: str, context: str, response: str, expected: str) -> Dict[str, Any]:
        """Détecte la source des hallucinations"""
        # Gérer les types dict/string
        if isinstance(context, dict):
            context = str(context)
        if isinstance(response, dict):
            response = response.get("response", str(response))
        if isinstance(expected, dict):
            expected = str(expected)
            
        context_lower = str(context).lower()
        response_lower = str(response).lower()
        expected_lower = str(expected).lower()
        
        analysis = {
            "context_contains_answer": any(word in context_lower for word in expected_lower.split()),
            "response_matches_expected": any(word in response_lower for word in expected_lower.split()),
            "hallucination_words": [],
            "missing_info": [],
            "context_quality": "UNKNOWN"
        }
        
        # Détecter les mots hallucinés (dans la réponse mais pas dans le contexte)
        response_words = set(response_lower.split())
        context_words = set(context_lower.split())
        
        # Mots suspects (couleurs, paiements, etc.)
        suspect_words = ["rouge", "bleu", "vert", "carte", "visa", "mastercard", "magasin", "boutique"]
        
        for word in suspect_words:
            if word in response_lower and word not in context_lower:
                analysis["hallucination_words"].append(word)
        
        # Vérifier les informations manquantes
        expected_words = expected_lower.split()
        for word in expected_words:
            if word not in context_lower:
                analysis["missing_info"].append(word)
        
        # Évaluer la qualité du contexte
        if len(context) < 100:
            analysis["context_quality"] = "TROP_COURT"
        elif len(analysis["missing_info"]) > len(expected_words) / 2:
            analysis["context_quality"] = "INCOMPLET"
        elif analysis["context_contains_answer"]:
            analysis["context_quality"] = "BON"
        else:
            analysis["context_quality"] = "INADÉQUAT"
        
        return analysis
    
    async def run_document_analysis(self) -> List[DocumentAnalysis]:
        """Lance l'analyse complète des documents"""
        print("🔍 ANALYSE DIAGNOSTIC AVANCÉE - DOCUMENTS RAG")
        print("=" * 80)
        print("Objectif: Identifier la cause racine des hallucinations")
        print("Méthode: Analyser les documents trouvés vs réponses LLM")
        print("=" * 80)
        
        analyses = []
        
        for i, test_case in enumerate(self.critical_questions, 1):
            question = test_case["question"]
            expected = test_case["expected_answer"]
            category = test_case["category"]
            
            print(f"\n🧪 ANALYSE {i}/{len(self.critical_questions)}: {category.upper()}")
            print(f"📝 Question: {question}")
            print(f"🎯 Réponse attendue: {expected}")
            print("-" * 70)
            
            # Envoyer la question avec debug
            result = await self.send_question_with_debug(question)
            
            if result["success"]:
                # Extraire les informations
                documents = result.get("documents", [])
                context = result.get("context", "")
                response = result.get("response", "")
                method_used = result.get("method_used", "unknown")
                
                print(f"🔍 Méthode utilisée: {method_used}")
                print(f"📄 Documents trouvés: {len(documents)}")
                print(f"📏 Taille contexte: {len(context)} caractères")
                
                # DIAGNOSTIC CRITIQUE : Aucun document trouvé
                if len(documents) == 0:
                    print(f"🚨 ALERTE CRITIQUE: AUCUN DOCUMENT TROUVÉ !")
                    print(f"   → C'est la CAUSE RACINE des hallucinations")
                    print(f"   → Le LLM génère sans contexte factuel")
                    print(f"   → Problème: Recherche RAG défaillante")
                
                # Analyser la pertinence des documents
                relevance_score, quality = self.analyze_document_relevance(question, documents, expected)
                print(f"📊 Score pertinence: {relevance_score:.2f} ({quality})")
                
                # Analyser les documents individuellement
                if documents:
                    print(f"\n📋 DÉTAIL DES DOCUMENTS:")
                    for j, doc in enumerate(documents[:3], 1):  # Top 3 documents
                        title = doc.get("title", "Sans titre")[:50]
                        content_preview = doc.get("content", "")[:100]
                        score = doc.get("score", 0)
                        source = doc.get("source", "unknown")
                        
                        print(f"   📄 Doc {j}: {title}...")
                        print(f"      Score: {score:.3f} | Source: {source}")
                        print(f"      Contenu: {content_preview}...")
                
                # Détecter la source des hallucinations (seulement si on a une réponse)
                if len(documents) == 0 and len(context) == 0:
                    # Cas spécial : aucun document trouvé
                    hallucination_analysis = {
                        "context_contains_answer": False,
                        "response_matches_expected": False,
                        "hallucination_words": ["TOUTE_LA_RÉPONSE"],
                        "missing_info": expected.split(),
                        "context_quality": "AUCUN_CONTEXTE"
                    }
                else:
                    hallucination_analysis = self.detect_hallucination_source(question, context, response, expected)
                
                print(f"\n🚨 ANALYSE HALLUCINATION:")
                print(f"   ✅ Contexte contient réponse: {hallucination_analysis['context_contains_answer']}")
                print(f"   ✅ Réponse correspond: {hallucination_analysis['response_matches_expected']}")
                print(f"   🎭 Mots hallucinés: {hallucination_analysis['hallucination_words']}")
                print(f"   ❌ Info manquantes: {hallucination_analysis['missing_info']}")
                print(f"   📊 Qualité contexte: {hallucination_analysis['context_quality']}")
                
                print(f"\n🤖 RÉPONSE LLM:")
                # Gérer le cas où response est un dict
                if isinstance(response, dict):
                    response_text = str(response)
                else:
                    response_text = str(response)
                print(f"   {response_text[:200]}...")
                
                # Créer l'analyse
                analysis = DocumentAnalysis(
                    question=question,
                    method_used=method_used,
                    documents_found=documents,
                    context_provided=context,
                    llm_response=response,
                    processing_time=result["processing_time"],
                    relevance_score=relevance_score,
                    hallucination_detected=len(hallucination_analysis['hallucination_words']) > 0,
                    document_quality=quality
                )
                
                analyses.append(analysis)
                
            else:
                print(f"❌ ERREUR: {result.get('error', 'Unknown')}")
        
        return analyses
    
    def generate_diagnostic_report(self, analyses: List[DocumentAnalysis]):
        """Génère le rapport diagnostic final"""
        print(f"\n" + "=" * 80)
        print("📊 RAPPORT DIAGNOSTIC FINAL")
        print("=" * 80)
        
        if not analyses:
            print("❌ Aucune analyse disponible")
            return
        
        # Statistiques globales
        total_analyses = len(analyses)
        hallucinations = sum(1 for a in analyses if a.hallucination_detected)
        avg_relevance = sum(a.relevance_score for a in analyses) / total_analyses
        avg_time = sum(a.processing_time for a in analyses) / total_analyses
        
        # Analyse par méthode
        methods_used = {}
        for analysis in analyses:
            method = analysis.method_used
            if method not in methods_used:
                methods_used[method] = {"count": 0, "hallucinations": 0, "avg_relevance": 0}
            methods_used[method]["count"] += 1
            methods_used[method]["avg_relevance"] += analysis.relevance_score
            if analysis.hallucination_detected:
                methods_used[method]["hallucinations"] += 1
        
        for method in methods_used:
            if methods_used[method]["count"] > 0:
                methods_used[method]["avg_relevance"] /= methods_used[method]["count"]
        
        # Analyse par qualité de documents
        quality_distribution = {}
        for analysis in analyses:
            quality = analysis.document_quality
            if quality not in quality_distribution:
                quality_distribution[quality] = 0
            quality_distribution[quality] += 1
        
        print(f"📊 STATISTIQUES GLOBALES:")
        print(f"   📝 Total analyses: {total_analyses}")
        print(f"   🚨 Hallucinations: {hallucinations}/{total_analyses} ({hallucinations/total_analyses*100:.1f}%)")
        print(f"   📊 Pertinence moyenne: {avg_relevance:.3f}")
        print(f"   ⏱️  Temps moyen: {avg_time:.2f}s")
        
        print(f"\n📈 PERFORMANCE PAR MÉTHODE:")
        for method, stats in methods_used.items():
            print(f"   🔍 {method.upper()}:")
            print(f"      - Analyses: {stats['count']}")
            print(f"      - Hallucinations: {stats['hallucinations']}")
            print(f"      - Pertinence: {stats['avg_relevance']:.3f}")
        
        print(f"\n📋 QUALITÉ DES DOCUMENTS:")
        for quality, count in quality_distribution.items():
            print(f"   📄 {quality}: {count} cas")
        
        # Diagnostic des causes
        print(f"\n🔍 DIAGNOSTIC DES CAUSES:")
        
        low_relevance = sum(1 for a in analyses if a.relevance_score < 0.4)
        if low_relevance > 0:
            print(f"   ⚠️  {low_relevance} cas avec pertinence faible (<0.4)")
            print(f"      → Problème: Documents non pertinents trouvés")
        
        no_docs = sum(1 for a in analyses if len(a.documents_found) == 0)
        if no_docs > 0:
            print(f"   ❌ {no_docs} cas sans documents trouvés")
            print(f"      → Problème: Recherche défaillante")
        
        if hallucinations > 0:
            print(f"   🚨 {hallucinations} hallucinations détectées")
            print(f"      → Problème: LLM génère des infos non présentes dans le contexte")
        
        print(f"\n💡 RECOMMANDATIONS:")
        if avg_relevance < 0.5:
            print(f"   📈 Améliorer la pertinence des documents (score: {avg_relevance:.2f})")
        if hallucinations > total_analyses / 2:
            print(f"   🚨 Renforcer la validation anti-hallucination")
        if no_docs > 0:
            print(f"   🔍 Optimiser les algorithmes de recherche")

async def main():
    """Fonction principale"""
    analyzer = RAGDocumentAnalyzer()
    analyses = await analyzer.run_document_analysis()
    analyzer.generate_diagnostic_report(analyses)
    
    print(f"\n🏁 DIAGNOSTIC TERMINÉ !")
    print("Maintenant nous savons exactement d'où viennent les hallucinations !")

if __name__ == "__main__":
    asyncio.run(main())
