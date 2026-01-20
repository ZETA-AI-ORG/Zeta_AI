#!/usr/bin/env python3
"""
🔥 TEST HARDCORE LITE - AUTO-DIAGNOSTIC
Version intelligente qui s'arrête au premier bug et analyse la cause

FONCTIONNALITÉS:
1. Arrêt immédiat en cas d'erreur
2. Diagnostic automatique de la cause racine
3. Validation des tools (Bloc-note, Calculatrice)
4. Analyse de la mémoire conversationnelle
5. Rapport détaillé avec recommandations
"""

import asyncio
import sys
import os
import re
from datetime import datetime
from typing import Dict, Any, List

# Ajouter le répertoire parent au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 🎯 SCÉNARIO CRITIQUE: 10 ÉCHANGES ESSENTIELS
HARDCORE_LITE_SCENARIO = [
    {
        "user_message": "couches",
        "expected_in_response": ["couches"],  # Juste vérifier qu'il parle de couches
        "expected_in_thinking": ["Bloc-note: ajouter info"],
        "phase": "exploration",
        "critical": True
    },
    {
        "user_message": "culottes",
        "expected_in_response": ["culottes"],  # Juste vérifier qu'il comprend
        "expected_in_thinking": ["Bloc-note: ajouter info"],
        "phase": "exploration",
        "critical": True
    },
    {
        "user_message": "lot 150",
        "expected_in_response": ["13500", "13 500"],
        "expected_in_thinking": ["Bloc-note: ajouter info", "produit", "lot 150"],
        "expected_in_notepad": {"produit": "culottes"},  # Vérifier que le produit est stocké (flexible)
        "expected_in_notepad_contains": ["150", "13"],  # Vérifier que lot 150 et prix sont mentionnés
        "phase": "produit",
        "critical": True
    },
    {
        "user_message": "taille 5",
        "expected_in_response": ["taille"],  # Juste vérifier qu'il parle de taille
        "expected_in_thinking": ["Bloc-note: ajouter info"],
        "expected_in_notepad_contains": ["5", "taille"],  # Vérifier que taille 5 est stockée
        "phase": "produit",
        "critical": True
    },
    {
        "user_message": "Cocody",
        "expected_in_response": ["Cocody"],  # Juste vérifier qu'il comprend
        "expected_in_thinking": ["Bloc-note: ajouter info"],
        "expected_in_notepad_contains": ["Cocody", "1500"],  # Vérifier zone + frais stockés
        "phase": "livraison",
        "critical": True
    },
    {
        "user_message": "total avec livraison",
        "expected_in_response": ["15000", "15 000"],
        "expected_in_thinking": ["Calculatrice"],
        "expected_calculation": "13500 + 1500",
        "phase": "calcul",
        "critical": True
    },
    {
        "user_message": "0787360757",
        "expected_in_response": ["787360757"],  # Juste vérifier qu'il reconnaît le numéro
        "expected_in_thinking": ["Bloc-note: ajouter info"],
        "expected_in_notepad_contains": ["0787360757"],  # Vérifier que le téléphone est stocké
        "phase": "contact",
        "critical": True
    },
    {
        "user_message": "rappel commande",
        "expected_in_response": ["lot 150", "taille 5", "Cocody"],
        "expected_in_thinking": ["Bloc-note: tout afficher"],
        "test_memory": True,
        "phase": "memoire",
        "critical": True
    },
    {
        "user_message": "prix total",
        "expected_in_response": ["15000", "15 000", "13500", "1500"],
        "test_memory": True,
        "phase": "memoire",
        "critical": True
    },
    {
        "user_message": "je confirme",
        "expected_in_response": ["acompte", "2000", "Wave", "0787360757"],
        "expected_in_thinking": ["Bloc-note: ajouter info", "statut"],
        "phase": "confirmation",
        "critical": True
    }
]

class HardcoreLiteDiagnostic:
    def __init__(self):
        self.exchange_number = 0
        self.total_exchanges = len(HARDCORE_LITE_SCENARIO)
        self.errors = []
        self.warnings = []
        self.notepad_state = {}
        self.tools_executed = []
        
    def analyze_thinking(self, thinking: str, expected_actions: List[str]) -> Dict[str, Any]:
        """Analyse le <thinking> pour vérifier les actions"""
        analysis = {
            "actions_found": [],
            "actions_missing": [],
            "tools_detected": []
        }
        
        # DEBUG: Afficher le thinking reçu
        print(f"\n[DEBUG] Thinking reçu ({len(thinking)} chars):")
        print(f"[DEBUG] Premiers 200 chars: {thinking[:200]}")
        
        # Détecter les outils utilisés (avec ou sans "Action :" et avec ou sans tiret)
        # Pattern flexible qui accepte: "Bloc-note: ajouter info" OU "- Action : Bloc-note: ajouter info"
        pattern_detect = r'(?:-\s*)?(?:Action\s*:\s*)?Bloc-note:\s*ajouter\s+info'
        if re.search(pattern_detect, thinking):
            print(f"[DEBUG] ✅ Pattern détecté!")
            analysis["tools_detected"].append("bloc-note-add")
            # Extraire les clés ajoutées (pattern flexible)
            pattern_extract = r'(?:-\s*)?(?:Action\s*:\s*)?Bloc-note:\s*ajouter\s+info\s*\(\s*([^,\)]+?)\s*,\s*"([^"]+)"\)'
            matches = re.findall(pattern_extract, thinking)
            print(f"[DEBUG] Matches trouvés: {len(matches)}")
            for key, value in matches:
                key = key.strip().strip('"')  # Enlever guillemets si présents
                print(f"[DEBUG] Extraction: {key} = {value}")
                analysis["actions_found"].append(f"add:{key}={value}")
                self.notepad_state[key] = value
        else:
            print(f"[DEBUG] ❌ Pattern NON détecté!")
        
        if "Bloc-note: tout afficher" in thinking:
            analysis["tools_detected"].append("bloc-note-display")
        
        if "Calculatrice" in thinking:
            analysis["tools_detected"].append("calculatrice")
            # Extraire le calcul
            calc_match = re.search(r'Calculatrice.*?(\d+\s*[+\-*/]\s*\d+)', thinking)
            if calc_match:
                analysis["actions_found"].append(f"calc:{calc_match.group(1)}")
        
        # Vérifier les actions attendues
        print(f"\n[DEBUG] Vérification des actions attendues: {expected_actions}")
        for expected in expected_actions:
            # Chercher avec ou sans "- Action :"
            pattern_check = rf'(?:-\s*)?(?:Action\s*:\s*)?{re.escape(expected)}'
            if re.search(pattern_check, thinking, re.IGNORECASE):
                print(f"[DEBUG] ✅ Action '{expected}' trouvée")
            else:
                print(f"[DEBUG] ❌ Action '{expected}' NON trouvée")
                analysis["actions_missing"].append(expected)
        
        return analysis
    
    def analyze_response(self, response: str, expected_keywords: List[str]) -> Dict[str, Any]:
        """Analyse la <response> pour vérifier le contenu"""
        analysis = {
            "keywords_found": [],
            "keywords_missing": [],
            "score": 0
        }
        
        response_lower = response.lower()
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                analysis["keywords_found"].append(keyword)
            else:
                analysis["keywords_missing"].append(keyword)
        
        analysis["score"] = len(analysis["keywords_found"]) / len(expected_keywords) * 100 if expected_keywords else 100
        
        return analysis
    
    def verify_notepad(self, expected_notepad: Dict[str, str], expected_contains: List[str] = None) -> Dict[str, Any]:
        """Vérifie l'état du bloc-note"""
        analysis = {
            "correct": [],
            "missing": [],
            "incorrect": []
        }
        
        # Vérifier les clés/valeurs exactes
        for key, expected_value in expected_notepad.items():
            if key in self.notepad_state:
                if expected_value.lower() in self.notepad_state[key].lower():
                    analysis["correct"].append(f"{key}={self.notepad_state[key]}")
                else:
                    analysis["incorrect"].append(f"{key}: expected '{expected_value}', got '{self.notepad_state[key]}'")
            else:
                analysis["missing"].append(f"{key}={expected_value}")
        
        # Vérifier que certaines valeurs sont présentes quelque part dans le notepad
        if expected_contains:
            notepad_str = " ".join(str(v).lower() for v in self.notepad_state.values())
            for value in expected_contains:
                if value.lower() in notepad_str:
                    analysis["correct"].append(f"contains:{value}")
                else:
                    analysis["missing"].append(f"contains:{value}")
        
        return analysis
    
    def diagnose_failure(self, exchange_data: Dict[str, Any], llm_response: str, thinking: str, response: str) -> str:
        """Diagnostic automatique de la cause d'échec"""
        diagnosis = []
        
        diagnosis.append(f"\n{'='*100}")
        diagnosis.append(f"🚨 ÉCHEC DÉTECTÉ À L'ÉCHANGE {self.exchange_number}/{self.total_exchanges}")
        diagnosis.append(f"{'='*100}\n")
        
        diagnosis.append(f"📍 PHASE: {exchange_data['phase'].upper()}")
        diagnosis.append(f"💬 MESSAGE USER: {exchange_data['user_message']}")
        diagnosis.append(f"\n{'─'*100}\n")
        
        # Analyse du thinking
        if exchange_data.get("expected_in_thinking"):
            thinking_analysis = self.analyze_thinking(thinking, exchange_data["expected_in_thinking"])
            
            diagnosis.append("🧠 ANALYSE DU <THINKING>:")
            diagnosis.append(f"   ✅ Outils détectés: {', '.join(thinking_analysis['tools_detected']) or 'AUCUN'}")
            diagnosis.append(f"   ✅ Actions trouvées: {', '.join(thinking_analysis['actions_found']) or 'AUCUNE'}")
            
            if thinking_analysis["actions_missing"]:
                diagnosis.append(f"   ❌ Actions manquantes: {', '.join(thinking_analysis['actions_missing'])}")
                self.errors.append(f"Actions manquantes dans thinking: {thinking_analysis['actions_missing']}")
        
        # Analyse de la response
        if exchange_data.get("expected_in_response"):
            response_analysis = self.analyze_response(response, exchange_data["expected_in_response"])
            
            diagnosis.append(f"\n💬 ANALYSE DE LA <RESPONSE>:")
            diagnosis.append(f"   ✅ Mots-clés trouvés: {', '.join(response_analysis['keywords_found']) or 'AUCUN'}")
            diagnosis.append(f"   📊 Score: {response_analysis['score']:.1f}%")
            
            if response_analysis["keywords_missing"]:
                diagnosis.append(f"   ❌ Mots-clés manquants: {', '.join(response_analysis['keywords_missing'])}")
                self.errors.append(f"Mots-clés manquants: {response_analysis['keywords_missing']}")
        
        # Vérification du bloc-note
        if exchange_data.get("expected_in_notepad"):
            notepad_analysis = self.verify_notepad(exchange_data["expected_in_notepad"])
            
            diagnosis.append(f"\n📋 ANALYSE DU BLOC-NOTE:")
            diagnosis.append(f"   ✅ Correct: {', '.join(notepad_analysis['correct']) or 'AUCUN'}")
            
            if notepad_analysis["missing"]:
                diagnosis.append(f"   ❌ Manquant: {', '.join(notepad_analysis['missing'])}")
                self.errors.append(f"Données manquantes dans bloc-note: {notepad_analysis['missing']}")
            
            if notepad_analysis["incorrect"]:
                diagnosis.append(f"   ⚠️  Incorrect: {', '.join(notepad_analysis['incorrect'])}")
                self.errors.append(f"Données incorrectes dans bloc-note: {notepad_analysis['incorrect']}")
        
        # Diagnostic de la cause racine
        diagnosis.append(f"\n{'─'*100}\n")
        diagnosis.append("🔍 DIAGNOSTIC DE LA CAUSE RACINE:\n")
        
        if "Bloc-note: ajouter info" not in thinking and exchange_data.get("expected_in_thinking") and "Bloc-note" in str(exchange_data["expected_in_thinking"]):
            diagnosis.append("   🐛 CAUSE #1: Le LLM ne génère PAS les actions Bloc-note dans <thinking>")
            diagnosis.append("      → Le prompt ne force pas assez l'utilisation des outils")
            diagnosis.append("      → Ou le LLM ignore les instructions d'outils")
        
        if "Bloc-note: ajouter info" in thinking and exchange_data.get("expected_in_notepad"):
            notepad_analysis = self.verify_notepad(exchange_data["expected_in_notepad"])
            if notepad_analysis["missing"]:
                diagnosis.append("   🐛 CAUSE #2: Le LLM génère les actions MAIS elles ne sont PAS exécutées")
                diagnosis.append("      → execute_tools_in_response() ne fonctionne pas")
                diagnosis.append("      → Ou les patterns regex ne matchent pas")
                diagnosis.append("      → Vérifier les logs '[TOOL EXEC]'")
        
        if exchange_data.get("test_memory") and response_analysis.get("score", 100) < 50:
            diagnosis.append("   🐛 CAUSE #3: MÉMOIRE CONVERSATIONNELLE DÉFAILLANTE")
            diagnosis.append("      → Le système ne retient pas les informations précédentes")
            diagnosis.append("      → EnhancedMemory ou UniversalConversationSynthesis ne fonctionne pas")
            diagnosis.append("      → Vérifier les logs '[ENHANCED_MEMORY]' et '[SYNTHESIS]'")
        
        diagnosis.append(f"\n{'─'*100}\n")
        diagnosis.append("📊 ÉTAT DU BLOC-NOTE ACTUEL:")
        if self.notepad_state:
            for key, value in self.notepad_state.items():
                diagnosis.append(f"   • {key}: {value}")
        else:
            diagnosis.append("   ⚠️  VIDE (aucune donnée enregistrée)")
        
        diagnosis.append(f"\n{'─'*100}\n")
        diagnosis.append("🎯 RECOMMANDATIONS:\n")
        
        if not thinking:
            diagnosis.append("   1. Le LLM ne génère pas de <thinking> → Vérifier le prompt")
        elif "Bloc-note" not in thinking and exchange_data.get("expected_in_thinking"):
            diagnosis.append("   1. Renforcer les instructions d'outils dans le prompt")
            diagnosis.append("   2. Ajouter des exemples concrets d'utilisation des outils")
        elif self.notepad_state == {} and "Bloc-note: ajouter info" in thinking:
            diagnosis.append("   1. URGENT: Corriger execute_tools_in_response()")
            diagnosis.append("   2. Vérifier que la fonction est bien importée et appelée")
            diagnosis.append("   3. Ajouter des logs pour tracer l'exécution des outils")
        
        diagnosis.append(f"\n{'='*100}\n")
        
        return "\n".join(diagnosis)

async def run_hardcore_lite_test():
    """Lance le test hardcore lite avec auto-diagnostic"""
    print(f"🔥 TEST HARDCORE LITE - AUTO-DIAGNOSTIC")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(HARDCORE_LITE_SCENARIO)} échanges critiques")
    print(f"{'='*100}\n")
    
    # Désactiver logs verbeux
    import logging
    logging.getLogger("database.vector_store_clean_v2").setLevel(logging.ERROR)
    logging.getLogger("core.context_extractor").setLevel(logging.ERROR)
    logging.getLogger("core.delivery_zone_extractor").setLevel(logging.ERROR)
    logging.getLogger("core.universal_rag_engine").setLevel(logging.WARNING)
    logging.getLogger("app").setLevel(logging.ERROR)
    logging.getLogger("core.conversation_notepad").setLevel(logging.WARNING)
    logging.getLogger("core.rag_tools_integration").setLevel(logging.ERROR)
    logging.getLogger("core.order_state_tracker").setLevel(logging.ERROR)
    logging.getLogger("core.rag_performance_tracker").setLevel(logging.ERROR)
    
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()
    diagnostic = HardcoreLiteDiagnostic()
    
    # Paramètres de test
    COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "test_hardcore_lite_001"
    
    for i, exchange_data in enumerate(HARDCORE_LITE_SCENARIO, 1):
        diagnostic.exchange_number = i
        user_message = exchange_data["user_message"]
        
        print(f"{'='*100}")
        print(f"🔥 ÉCHANGE {i}/{len(HARDCORE_LITE_SCENARIO)} - {exchange_data['phase'].upper()}")
        print(f"{'='*100}")
        print(f"👤 USER: {user_message}")
        
        try:
            # Recherche et génération
            search_results = await rag.search_sequential_sources(user_message, COMPANY_ID)
            search_results['conversation_history'] = user_message if 'conversation_history' not in search_results else search_results['conversation_history']
            
            response = await rag.generate_response(
                user_message, search_results, COMPANY_ID, COMPANY_NAME, USER_ID
            )
            
            # Récupérer thinking et response depuis le RAG engine
            thinking = getattr(rag, '_last_thinking', "")
            full_response = getattr(rag, '_last_full_response', response)
            response_clean = response
            
            # Fallback: extraction manuelle si pas disponible
            if not thinking and "<thinking>" in full_response:
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', full_response, re.DOTALL | re.IGNORECASE)
                if thinking_match:
                    thinking = thinking_match.group(1).strip()
            
            print(f"\n🤖 RESPONSE:")
            print(f"   {response_clean[:200]}{'...' if len(response_clean) > 200 else ''}")
            
            # ========== VALIDATION CRITIQUE ==========
            has_error = False
            
            # 1. Vérifier le thinking
            if exchange_data.get("expected_in_thinking"):
                thinking_analysis = diagnostic.analyze_thinking(thinking, exchange_data["expected_in_thinking"])
                if thinking_analysis["actions_missing"]:
                    has_error = True
                    print(f"\n❌ ERREUR: Actions manquantes dans <thinking>: {thinking_analysis['actions_missing']}")
            
            # 2. Vérifier la response
            if exchange_data.get("expected_in_response"):
                response_analysis = diagnostic.analyze_response(response_clean, exchange_data["expected_in_response"])
                if response_analysis["score"] < 50:
                    has_error = True
                    print(f"\n❌ ERREUR: Mots-clés manquants (score {response_analysis['score']:.1f}%): {response_analysis['keywords_missing']}")
            
            # 3. Vérifier le bloc-note
            if exchange_data.get("expected_in_notepad") or exchange_data.get("expected_in_notepad_contains"):
                expected_notepad = exchange_data.get("expected_in_notepad", {})
                expected_contains = exchange_data.get("expected_in_notepad_contains", None)
                notepad_analysis = diagnostic.verify_notepad(
                    expected_notepad,
                    expected_contains
                )
                if notepad_analysis["missing"] or notepad_analysis["incorrect"]:
                    has_error = True
                    print(f"\n❌ ERREUR: Bloc-note incorrect")
                    if notepad_analysis["missing"]:
                        print(f"   Manquant: {notepad_analysis['missing']}")
                    if notepad_analysis["incorrect"]:
                        print(f"   Incorrect: {notepad_analysis['incorrect']}")
            
            # ========== ARRÊT SI ERREUR CRITIQUE ==========
            if has_error and exchange_data.get("critical"):
                print(f"\n{'🚨'*50}")
                print(f"ARRÊT IMMÉDIAT - ERREUR CRITIQUE DÉTECTÉE")
                print(f"{'🚨'*50}\n")
                
                # Afficher le diagnostic complet
                diagnosis_report = diagnostic.diagnose_failure(exchange_data, response, thinking, response_clean)
                print(diagnosis_report)
                
                # Afficher la réponse LLM complète pour debug
                print(f"\n{'─'*100}")
                print("📄 RÉPONSE LLM COMPLÈTE (pour debug):")
                print(f"{'─'*100}")
                print(response[:2000] + "..." if len(response) > 2000 else response)
                print(f"{'─'*100}\n")
                
                # Résumé final
                print(f"{'='*100}")
                print(f"📊 RÉSUMÉ DU TEST")
                print(f"{'='*100}")
                print(f"✅ Échanges réussis: {i-1}/{len(HARDCORE_LITE_SCENARIO)}")
                print(f"❌ Échec à l'échange: {i}")
                print(f"📍 Phase d'échec: {exchange_data['phase']}")
                print(f"🐛 Erreurs détectées: {len(diagnostic.errors)}")
                for error in diagnostic.errors:
                    print(f"   • {error}")
                print(f"{'='*100}\n")
                
                return False
            
            print(f"✅ Échange {i} validé\n")
            
        except Exception as e:
            print(f"\n{'🚨'*50}")
            print(f"EXCEPTION PYTHON DÉTECTÉE")
            print(f"{'🚨'*50}\n")
            print(f"❌ Erreur: {type(e).__name__}: {str(e)}")
            print(f"\n📍 Phase: {exchange_data['phase']}")
            print(f"💬 Message: {user_message}")
            
            import traceback
            print(f"\n{'─'*100}")
            print("🔍 STACK TRACE:")
            print(f"{'─'*100}")
            traceback.print_exc()
            print(f"{'─'*100}\n")
            
            return False
    
    # ========== SUCCÈS TOTAL ==========
    print(f"\n{'🎉'*50}")
    print(f"SUCCÈS TOTAL - TOUS LES ÉCHANGES VALIDÉS")
    print(f"{'🎉'*50}\n")
    
    print(f"{'='*100}")
    print(f"📊 RAPPORT FINAL")
    print(f"{'='*100}")
    print(f"✅ Échanges réussis: {len(HARDCORE_LITE_SCENARIO)}/{len(HARDCORE_LITE_SCENARIO)}")
    print(f"📋 État du bloc-note final:")
    for key, value in diagnostic.notepad_state.items():
        print(f"   • {key}: {value}")
    print(f"🎯 Score: 100%")
    print(f"{'='*100}\n")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(run_hardcore_lite_test())
    sys.exit(0 if success else 1)
