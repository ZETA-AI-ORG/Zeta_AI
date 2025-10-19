#!/usr/bin/env python3
"""
🔍 TEST DIAGNOSTIC MÉMOIRE CONVERSATIONNELLE
============================================
Analyse précise de ce qui se passe avec la persistance du contexte
"""

import asyncio
import time
from core.enhanced_rag_with_semantic_cache import EnhancedRAGWithSemanticCache
from core.universal_rag_engine import UniversalRAGEngine

class MemoryDiagnosticTest:
    """🧪 Test diagnostic pour analyser la mémoire conversationnelle"""
    
    def __init__(self):
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.user_id = "testuser_memory"
        
        # Initialisation du RAG (CACHE DÉSACTIVÉ)
        self.base_rag = UniversalRAGEngine()
        self.enhanced_rag = EnhancedRAGWithSemanticCache(self.base_rag)
        self.enhanced_rag.enable_cache(False)
        
        # Historique de conversation pour test
        self.conversation_context = ""
        
    async def run_memory_diagnostic(self):
        """🚀 Lance le diagnostic complet de mémoire"""
        print("🔍 DIAGNOSTIC MÉMOIRE CONVERSATIONNELLE")
        print("=" * 60)
        print(f"🏢 Company ID: {self.company_id}")
        print(f"👤 User ID: {self.user_id}")
        print(f"🚫 Cache: DÉSACTIVÉ")
        print()
        
        # Test 1: Vérifier le contexte initial
        await self._test_1_contexte_initial()
        
        # Test 2: Ajouter information et vérifier persistance
        await self._test_2_ajout_information()
        
        # Test 3: Nouvelle requête avec contexte
        await self._test_3_persistance_contexte()
        
        # Test 4: Analyser le prompt final envoyé au LLM
        await self._test_4_analyse_prompt_llm()
        
    async def _test_1_contexte_initial(self):
        """Test 1: Analyser le contexte initial"""
        print("🧪 TEST 1: CONTEXTE INITIAL")
        print("-" * 40)
        
        query = "Bonjour, je suis à Cocody"
        
        print(f"📝 Requête: {query}")
        print(f"🧠 Contexte avant: '{self.conversation_context}'")
        print(f"📏 Taille contexte: {len(self.conversation_context)} caractères")
        print()
        
        # 🔍 LOGS MÉMOIRE AVANT APPEL RAG
        print(f"🔍 [MEMORY_LOG] AVANT APPEL RAG:")
        print(f"🔍 [MEMORY_LOG] conversation_history transmis: '{self.conversation_context}'")
        print(f"🔍 [MEMORY_LOG] Taille: {len(self.conversation_context)} chars")
        print()
        
        # Appel RAG
        response_data = await self.enhanced_rag.process_query(
            query=query,
            company_id=self.company_id,
            user_id=self.user_id,
            conversation_history=self.conversation_context
        )
        
        # Mise à jour du contexte (simulation)
        self._update_conversation_context(query, response_data.get("response", ""))
        
        print(f"🤖 Réponse: {response_data.get('response', 'VIDE')[:100]}...")
        print(f"🧠 Contexte après: '{self.conversation_context}'")
        print(f"📏 Nouvelle taille: {len(self.conversation_context)} caractères")
        print()
        
    async def _test_2_ajout_information(self):
        """Test 2: Ajouter information et vérifier"""
        print("🧪 TEST 2: AJOUT INFORMATION")
        print("-" * 40)
        
        query = "Je veux des couches culottes 3 paquets"
        
        print(f"📝 Requête: {query}")
        print(f"🧠 Contexte avant: '{self.conversation_context}'")
        print(f"🔍 Contient 'Cocody': {'Cocody' in self.conversation_context}")
        print()
        
        # 🔍 LOGS MÉMOIRE AVANT APPEL RAG #2
        print(f"🔍 [MEMORY_LOG] AVANT APPEL RAG #2:")
        print(f"🔍 [MEMORY_LOG] conversation_history: '{self.conversation_context}'")
        print(f"🔍 [MEMORY_LOG] Contient Cocody: {'Cocody' in self.conversation_context}")
        print()
        
        # Appel RAG avec contexte enrichi
        response_data = await self.enhanced_rag.process_query(
            query=query,
            company_id=self.company_id,
            user_id=self.user_id,
            conversation_history=self.conversation_context
        )
        
        # Mise à jour du contexte
        self._update_conversation_context(query, response_data.get("response", ""))
        
        print(f"🤖 Réponse: {response_data.get('response', 'VIDE')[:100]}...")
        print(f"🧠 Contexte après: '{self.conversation_context}'")
        print(f"🔍 Contient toujours 'Cocody': {'Cocody' in self.conversation_context}")
        print(f"🔍 Contient '3 paquets': {'3 paquets' in self.conversation_context}")
        print()
        
    async def _test_3_persistance_contexte(self):
        """Test 3: Vérifier persistance dans nouvelle requête"""
        print("🧪 TEST 3: PERSISTANCE CONTEXTE")
        print("-" * 40)
        
        query = "Ça coûte combien la livraison ?"
        
        print(f"📝 Requête: {query}")
        print(f"🧠 Contexte transmis: '{self.conversation_context}'")
        print(f"🔍 Informations disponibles:")
        print(f"   - Cocody: {'Cocody' in self.conversation_context}")
        print(f"   - Couches: {'couches' in self.conversation_context.lower()}")
        print(f"   - 3 paquets: {'3 paquets' in self.conversation_context}")
        print()
        
        # 🔍 LOGS MÉMOIRE CRITIQUE AVANT APPEL RAG #3
        print(f"🔍 [MEMORY_LOG] APPEL CRITIQUE RAG #3:")
        print(f"🔍 [MEMORY_LOG] conversation_history COMPLET:")
        print(f"🔍 [MEMORY_LOG] '{self.conversation_context}'")
        print(f"🔍 [MEMORY_LOG] Éléments critiques présents:")
        print(f"🔍 [MEMORY_LOG]   - Cocody: {'Cocody' in self.conversation_context}")
        print(f"🔍 [MEMORY_LOG]   - couches: {'couches' in self.conversation_context.lower()}")
        print(f"🔍 [MEMORY_LOG]   - 3 paquets: {'3 paquets' in self.conversation_context}")
        print()
        
        # Appel RAG - LE SYSTÈME DEVRAIT UTILISER LE CONTEXTE
        response_data = await self.enhanced_rag.process_query(
            query=query,
            company_id=self.company_id,
            user_id=self.user_id,
            conversation_history=self.conversation_context
        )
        
        response = response_data.get("response", "")
        
        print(f"🤖 Réponse: {response}")
        print()
        print(f"🔍 ANALYSE RÉPONSE:")
        print(f"   - Mentionne Cocody: {'Cocody' in response or 'cocody' in response.lower()}")
        print(f"   - Mentionne zone centrale: {'centrale' in response.lower()}")
        print(f"   - Mentionne 1500 FCFA: {'1500' in response}")
        print(f"   - Utilise contexte: {self._analyze_context_usage(response)}")
        print()
        
    async def _test_4_analyse_prompt_llm(self):
        """Test 4: Analyser le prompt envoyé au LLM"""
        print("🧪 TEST 4: ANALYSE PROMPT LLM")
        print("-" * 40)
        
        # Intercepter le prompt (simulation)
        print(f"🎯 CONTEXTE FINAL TRANSMIS AU RAG:")
        print(f"📏 Taille: {len(self.conversation_context)} caractères")
        print(f"📝 Contenu complet:")
        print(f"'{self.conversation_context}'")
        print()
        
        print(f"🔍 ANALYSE STRUCTURE:")
        lines = self.conversation_context.split('\n')
        print(f"   - Nombre de lignes: {len(lines)}")
        print(f"   - Messages utilisateur: {self.conversation_context.count('USER:')}")
        print(f"   - Réponses assistant: {self.conversation_context.count('ASSISTANT:')}")
        print()
        
        print(f"🎯 ÉLÉMENTS CRITIQUES:")
        critical_elements = {
            "Cocody": "Cocody" in self.conversation_context,
            "couches": "couches" in self.conversation_context.lower(),
            "3 paquets": "3 paquets" in self.conversation_context,
            "prix": "prix" in self.conversation_context.lower(),
            "livraison": "livraison" in self.conversation_context.lower()
        }
        
        for element, present in critical_elements.items():
            status = "✅" if present else "❌"
            print(f"   {status} {element}: {present}")
        
        print()
        
    def _update_conversation_context(self, query: str, response: str):
        """Met à jour le contexte conversationnel"""
        print(f"🔍 [MEMORY_UPDATE] MISE À JOUR CONTEXTE:")
        print(f"🔍 [MEMORY_UPDATE] Contexte AVANT: '{self.conversation_context}'")
        
        # Ajouter le message utilisateur
        self.conversation_context += f"USER: {query}\n"
        print(f"🔍 [MEMORY_UPDATE] Après ajout USER: '{self.conversation_context}'")
        
        # Ajouter la réponse (tronquée si trop longue)
        response_truncated = response[:200] + "..." if len(response) > 200 else response
        self.conversation_context += f"ASSISTANT: {response_truncated}\n"
        print(f"🔍 [MEMORY_UPDATE] Après ajout ASSISTANT: '{self.conversation_context}'")
        
        # Limiter la taille totale du contexte
        if len(self.conversation_context) > 1000:
            lines = self.conversation_context.split('\n')
            # Garder les 10 dernières lignes
            old_context = self.conversation_context
            self.conversation_context = '\n'.join(lines[-10:])
            print(f"🔍 [MEMORY_UPDATE] TRONCATURE APPLIQUÉE:")
            print(f"🔍 [MEMORY_UPDATE] Ancien: '{old_context}'")
            print(f"🔍 [MEMORY_UPDATE] Nouveau: '{self.conversation_context}'")
        
        print(f"🔍 [MEMORY_UPDATE] Contexte FINAL: '{self.conversation_context}'")
        print(f"🔍 [MEMORY_UPDATE] Taille finale: {len(self.conversation_context)} chars")
        print()
    
    def _analyze_context_usage(self, response: str) -> str:
        """Analyse si la réponse utilise le contexte"""
        context_indicators = []
        
        if "Cocody" in response or "cocody" in response.lower():
            context_indicators.append("Localisation")
        
        if "1500" in response:
            context_indicators.append("Prix zone centrale")
            
        if "couches" in response.lower():
            context_indicators.append("Produit mentionné")
            
        if context_indicators:
            return f"OUI ({', '.join(context_indicators)})"
        else:
            return "NON - Réponse générique"

async def main():
    """Point d'entrée principal"""
    test = MemoryDiagnosticTest()
    await test.run_memory_diagnostic()
    
    print("🎯 CONCLUSION:")
    print("Ce test révèle exactement où la mémoire conversationnelle échoue.")
    print("Analysez les résultats pour identifier les points de défaillance.")

if __name__ == "__main__":
    asyncio.run(main())
