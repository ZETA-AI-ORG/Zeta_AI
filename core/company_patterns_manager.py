#!/usr/bin/env python3
"""
🎯 GESTIONNAIRE DE PATTERNS PAR COMPANY - SCALABLE
Gère les patterns regex spécifiques à chaque entreprise de manière automatique

ARCHITECTURE SCALABLE:
- Chaque company a ses propres patterns
- Auto-apprentissage depuis les documents
- Stockage Redis avec TTL
- Fallback patterns génériques
- Zero maintenance manuelle
"""

import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ✅ PATTERNS GÉNÉRIQUES (fonctionnent pour toutes les entreprises)
GENERIC_PATTERNS = {
    # Prix (toute devise)
    "prix_generic": r"(\d{1,3}(?:[.,\s]\d{3})*|\d+(?:[.,]\d+)?)\s*([A-Z€$£¥]{1,4}|fcfa|euros?|dollars?)",
    
    # Quantités (universel)
    "quantite_generic": r"(\d+)\s*(paquets?|unités?|pièces?|articles?|kg|litres?|m[²³]?)",
    
    # Contacts (format international)
    "contact_generic": r"(?:\+\d{1,4}[\s-]?)?\d{8,15}",
    "email_generic": r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
    
    # Conditions temporelles
    "delai_generic": r"(\d+)\s*(minutes?|heures?|jours?|semaines?|mois)",
    "horaire_generic": r"\d{1,2}h\d{0,2}",
    
    # Pourcentages
    "pourcentage_generic": r"(\d{1,3})%",
    
    # Adresses
    "adresse_generic": r"(?:rue|avenue|boulevard|av\.|bd\.)\s+([^\n,]+)",
    
    # Prix avec quantité (pattern avancé)
    "prix_quantite_generic": r"(\d+)\s*(paquets?|unités?|pièces?)[:\s-]*(\d{1,3}(?:[.,\s]\d{3})*|\d+)",
}

class CompanyPatternsManager:
    """
    🎯 Gestionnaire de patterns par entreprise
    
    WORKFLOW:
    1. Récupère patterns depuis Redis (cache)
    2. Si non trouvé, génère depuis documents
    3. Fallback sur patterns génériques
    4. Stocke pour réutilisation
    """
    
    def __init__(self, redis_db: int = 4):
        self.redis_client = None
        self.redis_db = redis_db
        self.cache_ttl = 60 * 60 * 24 * 7  # 7 jours
        
        # Cache mémoire (évite appels Redis répétés)
        self.memory_cache: Dict[str, Dict] = {}
        
        self._init_redis()
    
    def _init_redis(self):
        """Initialise connexion Redis"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=self.redis_db,
                    decode_responses=True
                )
                self.redis_client.ping()
                print(f"✅ CompanyPatternsManager: Redis DB {self.redis_db} connecté")
            except Exception as e:
                self.redis_client = None
                print(f"⚠️ CompanyPatternsManager: Redis non disponible: {e}")
    
    def _get_cache_key(self, company_id: str) -> str:
        """Génère clé Redis pour une company"""
        return f"patterns:v2:{company_id}"
    
    def get_company_patterns(self, company_id: str) -> Dict[str, str]:
        """
        Récupère les patterns d'une company
        
        Ordre de priorité:
        1. Cache mémoire
        2. Redis
        3. Patterns génériques
        """
        # 1. Cache mémoire
        if company_id in self.memory_cache:
            print(f"✅ Patterns depuis cache mémoire: {company_id}")
            return self.memory_cache[company_id]
        
        # 2. Redis
        if self.redis_client:
            try:
                cache_key = self._get_cache_key(company_id)
                cached = self.redis_client.get(cache_key)
                
                if cached:
                    patterns = json.loads(cached)
                    self.memory_cache[company_id] = patterns
                    print(f"✅ Patterns depuis Redis: {company_id} ({len(patterns)} patterns)")
                    return patterns
            except Exception as e:
                print(f"⚠️ Erreur lecture Redis: {e}")
        
        # 3. Fallback: patterns génériques
        print(f"ℹ️ Utilisation patterns génériques pour: {company_id}")
        return GENERIC_PATTERNS.copy()
    
    def store_company_patterns(self, company_id: str, patterns: Dict[str, str]):
        """
        Stocke les patterns d'une company
        
        Stocke dans:
        1. Cache mémoire
        2. Redis (avec TTL)
        """
        # 1. Cache mémoire
        self.memory_cache[company_id] = patterns
        
        # 2. Redis
        if self.redis_client:
            try:
                cache_key = self._get_cache_key(company_id)
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(patterns)
                )
                print(f"💾 Patterns stockés pour {company_id}: {len(patterns)} patterns (TTL: 7j)")
            except Exception as e:
                print(f"⚠️ Erreur écriture Redis: {e}")
    
    def clear_company_patterns(self, company_id: str):
        """Supprime les patterns d'une company (force re-apprentissage)"""
        # Mémoire
        if company_id in self.memory_cache:
            del self.memory_cache[company_id]
        
        # Redis
        if self.redis_client:
            try:
                cache_key = self._get_cache_key(company_id)
                self.redis_client.delete(cache_key)
                print(f"🗑️ Patterns supprimés pour: {company_id}")
            except Exception as e:
                print(f"⚠️ Erreur suppression Redis: {e}")
    
    async def learn_from_documents(self, company_id: str, documents: List[Dict]) -> Dict[str, str]:
        """
        Apprend automatiquement les patterns depuis les documents d'une company
        
        Args:
            company_id: ID de l'entreprise
            documents: Liste des documents de l'entreprise
            
        Returns:
            Patterns détectés
        """
        print(f"\n🧠 Auto-apprentissage patterns pour: {company_id}")
        print(f"📄 Analyse de {len(documents)} documents...")
        
        try:
            from .dynamic_pattern_learner import DynamicPatternLearner
            
            # Créer learner temporaire (pas de fichier)
            learner = DynamicPatternLearner(patterns_file_path=None)
            
            # Détecter patterns potentiels
            detected = learner.detect_potential_patterns(documents)
            
            # Générer patterns regex
            new_patterns = learner.generate_regex_patterns(detected)
            
            # Combiner avec patterns génériques (génériques = base, spécifiques = override)
            combined_patterns = {**GENERIC_PATTERNS, **new_patterns}
            
            print(f"✅ Patterns détectés:")
            print(f"   - Génériques: {len(GENERIC_PATTERNS)}")
            print(f"   - Spécifiques: {len(new_patterns)}")
            print(f"   - Total: {len(combined_patterns)}")
            
            # Stocker
            self.store_company_patterns(company_id, combined_patterns)
            
            return combined_patterns
            
        except Exception as e:
            print(f"❌ Erreur apprentissage: {e}")
            # Fallback: patterns génériques
            self.store_company_patterns(company_id, GENERIC_PATTERNS)
            return GENERIC_PATTERNS
    
    def get_stats(self) -> Dict:
        """Statistiques du gestionnaire"""
        stats = {
            "companies_in_memory": len(self.memory_cache),
            "redis_available": self.redis_client is not None,
            "cache_ttl_days": self.cache_ttl / (60 * 60 * 24),
            "generic_patterns_count": len(GENERIC_PATTERNS)
        }
        
        # Stats Redis
        if self.redis_client:
            try:
                pattern = "patterns:v2:*"
                keys = self.redis_client.keys(pattern)
                stats["companies_in_redis"] = len(keys)
            except:
                stats["companies_in_redis"] = 0
        
        return stats


# Singleton global
_global_manager = None

def get_company_patterns_manager() -> CompanyPatternsManager:
    """Retourne l'instance globale du gestionnaire"""
    global _global_manager
    if _global_manager is None:
        _global_manager = CompanyPatternsManager()
    return _global_manager


# Fonctions utilitaires pour intégration facile
async def get_patterns_for_company(company_id: str) -> Dict[str, str]:
    """Récupère patterns pour une company (API simple)"""
    manager = get_company_patterns_manager()
    return manager.get_company_patterns(company_id)

async def learn_patterns_for_company(company_id: str, documents: List[Dict]) -> Dict[str, str]:
    """Apprend patterns pour une company (API simple)"""
    manager = get_company_patterns_manager()
    return await manager.learn_from_documents(company_id, documents)

async def refresh_company_patterns(company_id: str):
    """Force le re-apprentissage des patterns d'une company"""
    manager = get_company_patterns_manager()
    manager.clear_company_patterns(company_id)
    print(f"🔄 Patterns invalidés pour {company_id}, seront ré-appris au prochain appel")
