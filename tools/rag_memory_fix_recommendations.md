# 🔥 RECOMMANDATIONS URGENTES - FIX MÉMOIRE CONVERSATIONNELLE

## 🚨 PROBLÈMES CRITIQUES IDENTIFIÉS

### 1. MÉMOIRE CONVERSATIONNELLE DÉFAILLANTE
- Score de cohérence: **10%** (catastrophique)
- Le système oublie tout entre les échanges
- Informations client perdues (poids bébé, adresse, quantités)

### 2. RATE LIMITING GROQ NON GÉRÉ
- **28% d'échec** (12 erreurs 429 sur 43 échanges)
- Aucun retry mechanism
- Pas de fallback sur erreur

### 3. CALCULS INCOHÉRENTS
- Prix contradictoires (0 FCFA, 90 FCFA, 5500 FCFA)
- Récapitulatifs erronés
- Pas de validation des calculs

## 🎯 SOLUTIONS PRIORITAIRES

### A. IMPLÉMENTER VRAIE MÉMOIRE CONVERSATIONNELLE

```python
# core/conversation_memory_v2.py
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

class ConversationMemoryManager:
    def __init__(self, db_path: str = "conversation_memory.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données de mémoire"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_context (
                user_id TEXT,
                company_id TEXT,
                context_key TEXT,
                context_value TEXT,
                timestamp DATETIME,
                PRIMARY KEY (user_id, company_id, context_key)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                company_id TEXT,
                question TEXT,
                response TEXT,
                timestamp DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_context(self, user_id: str, company_id: str, key: str, value: Any):
        """Sauvegarde une information contextuelle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO conversation_context 
            (user_id, company_id, context_key, context_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, company_id, key, json.dumps(value), datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_context(self, user_id: str, company_id: str, key: str) -> Optional[Any]:
        """Récupère une information contextuelle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT context_value FROM conversation_context
            WHERE user_id = ? AND company_id = ? AND context_key = ?
        ''', (user_id, company_id, key))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def get_full_context(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Récupère tout le contexte utilisateur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT context_key, context_value FROM conversation_context
            WHERE user_id = ? AND company_id = ?
        ''', (user_id, company_id))
        
        results = cursor.fetchall()
        conn.close()
        
        context = {}
        for key, value in results:
            context[key] = json.loads(value)
        
        return context
    
    def save_exchange(self, user_id: str, company_id: str, question: str, response: str):
        """Sauvegarde un échange de conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_history 
            (user_id, company_id, question, response, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, company_id, question, response, datetime.now()))
        
        conn.commit()
        conn.close()
```

### B. GESTION RATE LIMITING AVEC RETRY

```python
# core/llm_client_robust.py
import asyncio
import time
from typing import Optional

class RobustLLMClient:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def complete_with_retry(self, prompt: str) -> str:
        """Appel LLM avec retry automatique sur rate limiting"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Tentative d'appel LLM
                response = await self.llm_client.complete(prompt)
                return response
                
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Si c'est du rate limiting (429)
                if "429" in error_str or "too many requests" in error_str:
                    if attempt < self.max_retries - 1:
                        # Backoff exponentiel
                        delay = self.base_delay * (2 ** attempt)
                        print(f"Rate limiting détecté, retry dans {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                
                # Autres erreurs, pas de retry
                break
        
        # Fallback si tous les retries échouent
        return self.generate_fallback_response(prompt, last_exception)
    
    def generate_fallback_response(self, prompt: str, error: Exception) -> str:
        """Génère une réponse de fallback en cas d'échec LLM"""
        return f"""
        🚨 **SERVICE TEMPORAIREMENT INDISPONIBLE**
        
        Nous rencontrons actuellement des difficultés techniques.
        
        📞 **Contactez-nous directement** :
        • Téléphone : +2250787360757
        • WhatsApp : +2250160924560
        
        Nous vous répondrons dans les plus brefs délais.
        
        **Erreur technique** : {str(error)[:100]}...
        """
```

### C. SYSTÈME DE VALIDATION DES CALCULS

```python
# core/price_calculator.py
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class OrderItem:
    product_type: str
    size: str
    quantity: int
    unit_price: float
    
@dataclass
class OrderSummary:
    items: List[OrderItem]
    subtotal: float
    delivery_fee: float
    total: float
    delivery_zone: str
    
class PriceCalculator:
    def __init__(self):
        self.delivery_rates = {
            "cocody": 1500,
            "yopougon": 1500,
            "plateau": 1500,
            "marcory": 2000,
            "default": 1500
        }
    
    def calculate_order(self, items: List[OrderItem], delivery_zone: str) -> OrderSummary:
        """Calcule le total d'une commande avec validation"""
        subtotal = sum(item.quantity * item.unit_price for item in items)
        delivery_fee = self.delivery_rates.get(delivery_zone.lower(), self.delivery_rates["default"])
        total = subtotal + delivery_fee
        
        # Validation
        if subtotal < 0:
            raise ValueError("Sous-total négatif impossible")
        if total < delivery_fee:
            raise ValueError("Total inférieur aux frais de livraison")
        
        return OrderSummary(
            items=items,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            delivery_zone=delivery_zone
        )
```

### D. INTÉGRATION DANS RAG ENGINE

```python
# Modifications dans universal_rag_engine.py

class UniversalRAGEngine:
    def __init__(self):
        # ... existing code ...
        self.memory_manager = ConversationMemoryManager()
        self.price_calculator = PriceCalculator()
        self.robust_llm = RobustLLMClient()
    
    async def generate_response(self, query: str, search_results: Dict[str, Any], 
                              company_id: str, company_name: str, user_id: str) -> str:
        
        # 1. Récupérer le contexte utilisateur
        user_context = self.memory_manager.get_full_context(user_id, company_id)
        
        # 2. Extraire les informations de la requête
        extracted_info = self.extract_user_info(query)
        
        # 3. Mettre à jour le contexte
        for key, value in extracted_info.items():
            if value:
                self.memory_manager.save_context(user_id, company_id, key, value)
        
        # 4. Enrichir le prompt avec le contexte
        enriched_prompt = self.build_context_aware_prompt(
            query, search_results, user_context, company_name
        )
        
        # 5. Appel LLM robuste
        response = await self.robust_llm.complete_with_retry(enriched_prompt)
        
        # 6. Sauvegarder l'échange
        self.memory_manager.save_exchange(user_id, company_id, query, response)
        
        return response
    
    def extract_user_info(self, query: str) -> Dict[str, Any]:
        """Extrait les informations utilisateur de la requête"""
        info = {}
        
        # Extraction du poids
        import re
        weight_match = re.search(r'(\d+)\s*kg', query.lower())
        if weight_match:
            info['baby_weight'] = f"{weight_match.group(1)}kg"
        
        # Extraction de l'adresse
        zones = ['cocody', 'yopougon', 'plateau', 'marcory']
        for zone in zones:
            if zone in query.lower():
                info['delivery_address'] = zone
                break
        
        # Extraction des quantités
        qty_match = re.search(r'(\d+)\s*paquet', query.lower())
        if qty_match:
            info['quantity'] = int(qty_match.group(1))
        
        return info
```

## 🎯 PLAN D'IMPLÉMENTATION

### Phase 1 - URGENT (24h)
1. ✅ Implémenter ConversationMemoryManager
2. ✅ Ajouter retry mechanism pour Groq
3. ✅ Système de fallback sur erreur

### Phase 2 - CRITIQUE (48h)
1. ✅ PriceCalculator avec validation
2. ✅ Extraction automatique d'informations
3. ✅ Tests de cohérence automatiques

### Phase 3 - OPTIMISATION (72h)
1. ✅ Interface de monitoring
2. ✅ Métriques de performance
3. ✅ Tests de régression

## 🚀 TESTS DE VALIDATION

```bash
# Test de mémoire conversationnelle
python3 tools/test_memory_persistence.py

# Test de robustesse rate limiting
python3 tools/test_rate_limiting_resilience.py

# Test de cohérence des calculs
python3 tools/test_price_calculation_accuracy.py
```

**PRIORITÉ ABSOLUE** : Sans ces fixes, le système est inutilisable en production !
