"""
🏢 TENANT CONFIG MANAGER - SYSTÈME MULTI-ENTREPRISES SCALABLE
Gestion dynamique des configurations par entreprise (1 à 1000+)
"""
import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

from utils import log3


@dataclass
class SearchConfig:
    """Configuration de recherche par tenant"""
    # MeiliSearch
    meili_enabled: bool = True
    meili_max_docs_per_index: int = 10
    meili_max_total_docs: int = 20
    meili_timeout_ms: int = 500
    meili_boost_exact: float = 5.0
    meili_boost_fuzzy: float = 0.5
    meili_boost_id: float = 10.0
    
    # Supabase (fallback sémantique)
    supabase_enabled: bool = True
    supabase_similarity_threshold: float = 0.7
    supabase_max_docs: int = 15
    supabase_timeout_ms: int = 1000
    
    # Reranking
    rerank_enabled: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_top_k: int = 5
    
    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    cache_max_entries: int = 1000


@dataclass
class LLMConfig:
    """Configuration LLM par tenant"""
    provider: str = "groq"  # groq, openai, deepseek
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.3
    max_tokens: int = 500
    timeout_seconds: int = 30
    max_retries: int = 3
    
    # Coûts et quotas
    max_requests_per_minute: int = 100
    max_tokens_per_day: int = 100000
    cost_per_1k_tokens: float = 0.0005


@dataclass
class BusinessConfig:
    """Configuration métier par tenant"""
    company_name: str
    industry: str = "general"
    language: str = "fr"
    timezone: str = "Africa/Abidjan"
    
    # Mots-clés spécifiques à l'entreprise
    company_keywords: List[str] = None
    stop_words_custom: List[str] = None
    synonyms: Dict[str, List[str]] = None
    
    # Prompts personnalisés
    system_prompt_override: Optional[str] = None
    greeting_message: str = "Bonjour ! Comment puis-je vous aider ?"
    
    def __post_init__(self):
        if self.company_keywords is None:
            self.company_keywords = []
        if self.stop_words_custom is None:
            self.stop_words_custom = []
        if self.synonyms is None:
            self.synonyms = {}


@dataclass
class TenantConfig:
    """Configuration complète d'un tenant"""
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    
    # Configurations par domaine
    search: SearchConfig
    llm: LLMConfig
    business: BusinessConfig
    
    # Métadonnées
    version: str = "1.0"
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour stockage"""
        return {
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'search': asdict(self.search),
            'llm': asdict(self.llm),
            'business': asdict(self.business),
            'version': self.version,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TenantConfig':
        """Crée depuis un dictionnaire"""
        return cls(
            tenant_id=data['tenant_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            search=SearchConfig(**data['search']),
            llm=LLMConfig(**data['llm']),
            business=BusinessConfig(**data['business']),
            version=data.get('version', '1.0'),
            active=data.get('active', True)
        )


class TenantConfigManager:
    """
    🏢 GESTIONNAIRE DE CONFIGURATION MULTI-TENANT
    
    Fonctionnalités:
    - Configuration par entreprise (pas de hardcode)
    - Chargement dynamique depuis fichiers/DB
    - Cache en mémoire pour performance
    - Validation et migration automatique
    - Templates par industrie
    """
    
    def __init__(self, config_dir: str = "config/tenants"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache en mémoire
        self._cache: Dict[str, TenantConfig] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Templates par industrie
        self._industry_templates = self._load_industry_templates()
        
        log3("[TENANT_CONFIG]", "✅ Gestionnaire multi-tenant initialisé")
    
    def _load_industry_templates(self) -> Dict[str, Dict[str, Any]]:
        """Charge les templates par industrie"""
        templates = {
            "ecommerce": {
                "search": {
                    "meili_boost_exact": 6.0,  # Plus de poids sur correspondances exactes
                    "meili_max_total_docs": 25,  # Plus de contexte pour produits
                },
                "business": {
                    "company_keywords": ["prix", "livraison", "commande", "stock", "taille"],
                    "synonyms": {
                        "prix": ["coût", "tarif", "montant"],
                        "livraison": ["envoi", "expédition", "transport"],
                        "commande": ["achat", "réservation"]
                    }
                }
            },
            "support": {
                "search": {
                    "meili_max_total_docs": 15,  # Moins de contexte, plus de précision
                    "rerank_enabled": True,  # Reranking pour support technique
                },
                "llm": {
                    "temperature": 0.1,  # Plus factuel pour support
                }
            },
            "general": {
                # Configuration par défaut
            }
        }
        return templates
    
    def get_config(self, tenant_id: str) -> TenantConfig:
        """
        Récupère la configuration d'un tenant
        
        Args:
            tenant_id: ID unique de l'entreprise
            
        Returns:
            Configuration complète du tenant
        """
        # Check cache
        if self._is_cached_valid(tenant_id):
            return self._cache[tenant_id]
        
        # Charger depuis fichier
        config = self._load_from_file(tenant_id)
        if config is None:
            # Créer configuration par défaut
            config = self._create_default_config(tenant_id)
            self._save_to_file(config)
        
        # Mettre en cache
        self._cache[tenant_id] = config
        self._cache_timestamps[tenant_id] = datetime.now().timestamp()
        
        return config
    
    def _is_cached_valid(self, tenant_id: str) -> bool:
        """Vérifie si le cache est valide"""
        if tenant_id not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(tenant_id, 0)
        return (datetime.now().timestamp() - timestamp) < self.cache_ttl
    
    def _load_from_file(self, tenant_id: str) -> Optional[TenantConfig]:
        """Charge la config depuis un fichier YAML"""
        config_file = self.config_dir / f"{tenant_id}.yaml"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return TenantConfig.from_dict(data)
        except Exception as e:
            log3("[TENANT_CONFIG]", f"⚠️ Erreur chargement {tenant_id}: {e}")
            return None
    
    def _save_to_file(self, config: TenantConfig):
        """Sauvegarde la config dans un fichier YAML"""
        config_file = self.config_dir / f"{config.tenant_id}.yaml"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
            
            log3("[TENANT_CONFIG]", f"✅ Config sauvegardée: {config.tenant_id}")
        except Exception as e:
            log3("[TENANT_CONFIG]", f"⚠️ Erreur sauvegarde {config.tenant_id}: {e}")
    
    def _create_default_config(self, tenant_id: str, industry: str = "general") -> TenantConfig:
        """Crée une configuration par défaut"""
        now = datetime.now()
        
        # Configuration de base
        search_config = SearchConfig()
        llm_config = LLMConfig()
        business_config = BusinessConfig(
            company_name=f"Company_{tenant_id[:8]}",
            industry=industry
        )
        
        # Appliquer template industrie
        if industry in self._industry_templates:
            template = self._industry_templates[industry]
            
            # Merger search config
            if 'search' in template:
                for key, value in template['search'].items():
                    if hasattr(search_config, key):
                        setattr(search_config, key, value)
            
            # Merger business config
            if 'business' in template:
                for key, value in template['business'].items():
                    if hasattr(business_config, key):
                        setattr(business_config, key, value)
            
            # Merger LLM config
            if 'llm' in template:
                for key, value in template['llm'].items():
                    if hasattr(llm_config, key):
                        setattr(llm_config, key, value)
        
        config = TenantConfig(
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            search=search_config,
            llm=llm_config,
            business=business_config
        )
        
        log3("[TENANT_CONFIG]", f"✅ Config par défaut créée: {tenant_id} ({industry})")
        return config
    
    def update_config(self, tenant_id: str, updates: Dict[str, Any]) -> TenantConfig:
        """
        Met à jour la configuration d'un tenant
        
        Args:
            tenant_id: ID du tenant
            updates: Dictionnaire des mises à jour
            
        Returns:
            Configuration mise à jour
        """
        config = self.get_config(tenant_id)
        config.updated_at = datetime.now()
        
        # Appliquer les mises à jour
        for section, section_updates in updates.items():
            if hasattr(config, section):
                section_obj = getattr(config, section)
                for key, value in section_updates.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
        
        # Sauvegarder
        self._save_to_file(config)
        
        # Invalider cache
        if tenant_id in self._cache:
            del self._cache[tenant_id]
            del self._cache_timestamps[tenant_id]
        
        log3("[TENANT_CONFIG]", f"✅ Config mise à jour: {tenant_id}")
        return config
    
    def create_tenant(self, tenant_id: str, company_name: str, industry: str = "general") -> TenantConfig:
        """
        Crée un nouveau tenant
        
        Args:
            tenant_id: ID unique
            company_name: Nom de l'entreprise
            industry: Secteur d'activité
            
        Returns:
            Configuration du nouveau tenant
        """
        if self._load_from_file(tenant_id) is not None:
            raise ValueError(f"Tenant {tenant_id} existe déjà")
        
        config = self._create_default_config(tenant_id, industry)
        config.business.company_name = company_name
        
        self._save_to_file(config)
        
        log3("[TENANT_CONFIG]", f"✅ Nouveau tenant créé: {tenant_id} ({company_name})")
        return config
    
    def list_tenants(self) -> List[str]:
        """Liste tous les tenants configurés"""
        config_files = list(self.config_dir.glob("*.yaml"))
        return [f.stem for f in config_files]
    
    def get_tenant_stats(self) -> Dict[str, Any]:
        """Statistiques des tenants"""
        tenants = self.list_tenants()
        
        stats = {
            "total_tenants": len(tenants),
            "cached_tenants": len(self._cache),
            "industries": {},
            "active_tenants": 0
        }
        
        for tenant_id in tenants:
            try:
                config = self.get_config(tenant_id)
                if config.active:
                    stats["active_tenants"] += 1
                
                industry = config.business.industry
                stats["industries"][industry] = stats["industries"].get(industry, 0) + 1
            except Exception:
                continue
        
        return stats


# Instance globale
_tenant_manager: Optional[TenantConfigManager] = None

def get_tenant_manager() -> TenantConfigManager:
    """Récupère l'instance globale du gestionnaire"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantConfigManager()
    return _tenant_manager

def get_tenant_config(tenant_id: str) -> TenantConfig:
    """Raccourci pour récupérer une config"""
    return get_tenant_manager().get_config(tenant_id)
