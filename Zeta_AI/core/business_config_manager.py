#!/usr/bin/env python3
"""
🏢 GESTIONNAIRE DE CONFIGURATION MÉTIER DYNAMIQUE
Configuration adaptative par entreprise pour système RAG multi-tenant
"""

import asyncio
import json
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum

from database.supabase_client import get_supabase_client
from core.cache_manager import cache_manager
from utils import log3


class BusinessSector(Enum):
    """Secteurs d'activité supportés - CONFIGURATION COMPLÈTE"""
    ELECTRONICS = "electronics"           # 📱 Électronique & Informatique
    HOME_APPLIANCES = "home_appliances"   # 🏠 Maison & Électroménager
    FASHION = "fashion"                   # 👗 Mode & Prêt-à-porter
    BEAUTY = "beauty"                     # 💄 Beauté & Cosmétiques
    BABY_CARE = "baby_care"              # 👶 Bébé & Puériculture
    AUTOMOTIVE = "automotive"             # 🚗 Auto & Moto
    FOOD = "food"                        # 🛒 Épicerie & Alimentation
    OFFICE_SUPPLIES = "office_supplies"  # 📚 Fournitures scolaires & Bureau
    TOYS_GAMES = "toys_games"            # 🎮 Jeux, Jouets, Loisirs
    PETS = "pets"                        # 🐾 Produits pour animaux
    DIGITAL_SERVICES = "digital_services" # 💻 Services numériques & infoproduits
    OTHER = "other"                      # 🏷️ Autres (personnalisé)
    GENERIC = "generic"                  # Générique


@dataclass
class BusinessKeywords:
    """Mots-clés métier par catégorie"""
    products: Set[str]
    services: Set[str] 
    locations: Set[str]
    brands: Set[str]
    attributes: Set[str]
    actions: Set[str]


@dataclass
class BusinessConfig:
    """Configuration complète d'une entreprise"""
    company_id: str
    sector: BusinessSector
    business_name: str
    keywords: BusinessKeywords
    synonyms: Dict[str, List[str]]
    offtopic_threshold: float = 0.7
    cache_ttl_hours: int = 24
    custom_prompts: Dict[str, str] = None


class BusinessConfigManager:
    """
    🎯 GESTIONNAIRE DE CONFIGURATION MÉTIER GÉNÉRIQUE
    
    Fonctionnalités:
    - Configuration dynamique par entreprise
    - Détection automatique du secteur d'activité
    - Mots-clés adaptatifs par domaine
    - Synonymes contextuels configurables
    - Cache intelligent des configurations
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.configs_cache: Dict[str, BusinessConfig] = {}
        
        # Templates de configuration par secteur
        self.sector_templates = self._initialize_sector_templates()
    
    async def get_business_config(self, company_id: str) -> BusinessConfig:
        """Récupération de la configuration métier d'une entreprise"""
        
        # Cache check
        if company_id in self.configs_cache:
            return self.configs_cache[company_id]
        
        # Cache Redis check
        cached_config = cache_manager.get(f"business_config:{company_id}")
        if cached_config:
            try:
                config_data = json.loads(cached_config)
                config = BusinessConfig(**config_data)
                self.configs_cache[company_id] = config
                return config
            except Exception as e:
                log3("[BUSINESS_CONFIG]", f"⚠️ Erreur cache config: {e}")
        
        # Chargement depuis base de données
        config = await self._load_config_from_db(company_id)
        
        # Mise en cache
        self.configs_cache[company_id] = config
        cache_manager.set(
            f"business_config:{company_id}",
            json.dumps(asdict(config), default=str),
            ttl_seconds=config.cache_ttl_hours * 3600
        )
        
        return config
    
    async def _load_config_from_db(self, company_id: str) -> BusinessConfig:
        """Chargement de la configuration - Version simplifiée sans base de données"""
        
        # Pour l'instant, on utilise toujours la config générique
        # Plus tard, on pourra ajouter la détection de secteur basée sur les documents existants
        
        log3("[BUSINESS_CONFIG]", f"📋 Utilisation config générique pour {company_id}")
        return self._create_generic_config(company_id)
    
    async def _detect_business_sector(self, company_id: str, company_data: Dict) -> BusinessSector:
        """Détection automatique du secteur d'activité"""
        
        # Analyse du nom de l'entreprise et des données
        business_name = company_data.get("name", "").lower()
        description = company_data.get("description", "").lower()
        
        # Récupération d'échantillons de produits pour analyse
        products_sample = await self._get_products_sample(company_id)
        
        # Analyse textuelle pour détection du secteur
        all_text = f"{business_name} {description} {' '.join(products_sample)}".lower()
        
        # Mots-clés de détection par secteur - CONFIGURATION EXHAUSTIVE
        sector_indicators = {
            BusinessSector.ELECTRONICS: [
                'électronique', 'téléphone', 'smartphone', 'ordinateur', 'pc', 'laptop', 'tablette', 'ipad',
                'tv', 'télévision', 'écran', 'moniteur', 'casque', 'écouteurs', 'enceinte', 'haut-parleur',
                'console', 'gaming', 'tech', 'digital', 'informatique', 'apple', 'samsung', 'huawei',
                'processeur', 'mémoire', 'disque', 'clavier', 'souris', 'webcam', 'micro', 'chargeur'
            ],
            BusinessSector.HOME_APPLIANCES: [
                'électroménager', 'réfrigérateur', 'frigo', 'cuisinière', 'four', 'micro-ondes', 'lave-linge',
                'lave-vaisselle', 'aspirateur', 'mixeur', 'blender', 'cafetière', 'grille-pain', 'bouilloire',
                'climatiseur', 'ventilateur', 'chauffage', 'meuble', 'canapé', 'lit', 'armoire', 'table',
                'chaise', 'décoration', 'luminaire', 'lampe', 'rideau', 'tapis', 'coussin', 'maison'
            ],
            BusinessSector.FASHION: [
                'mode', 'vêtement', 'habit', 'tenue', 'robe', 'pantalon', 'jean', 'chemise', 'pull',
                'manteau', 'veste', 't-shirt', 'short', 'jupe', 'chaussure', 'basket', 'botte', 'sandale',
                'sac', 'portefeuille', 'ceinture', 'montre', 'bijou', 'collier', 'bracelet', 'bague',
                'lunettes', 'chapeau', 'écharpe', 'gant', 'style', 'tendance', 'fashion', 'prêt-à-porter'
            ],
            BusinessSector.BEAUTY: [
                'beauté', 'cosmétique', 'maquillage', 'fond-de-teint', 'rouge-à-lèvres', 'mascara', 'eye-liner',
                'parfum', 'eau-de-toilette', 'crème', 'sérum', 'lotion', 'shampoing', 'après-shampoing',
                'gel', 'mousse', 'huile', 'masque', 'gommage', 'démaquillant', 'vernis', 'manucure',
                'pédicure', 'soin', 'anti-âge', 'hydratant', 'nettoyant', 'esthétique', 'spa', 'wellness'
            ],
            BusinessSector.BABY_CARE: [
                'bébé', 'couches', 'culottes', 'puériculture', 'enfant', 'nourrisson', 'bambin', 'nouveau-né',
                'pression', 'lingettes', 'biberon', 'tétine', 'sucette', 'poussette', 'landau', 'siège-auto',
                'lit', 'berceau', 'matelas', 'gigoteuse', 'turbulette', 'body', 'pyjama', 'chaussons',
                'jouet', 'peluche', 'hochet', 'tapis-éveil', 'parc', 'chaise-haute', 'transat', 'baignoire'
            ],
            BusinessSector.AUTOMOTIVE: [
                'auto', 'automobile', 'voiture', 'véhicule', 'moto', 'motocyclette', 'scooter', 'quad',
                'casque', 'gants', 'blouson', 'protection', 'équipement', 'pièce', 'moteur', 'pneu',
                'jante', 'amortisseur', 'frein', 'embrayage', 'batterie', 'phare', 'feu', 'rétroviseur',
                'pare-brise', 'essuie-glace', 'huile', 'filtre', 'bougie', 'courroie', 'accessoire', 'tuning'
            ],
            BusinessSector.FOOD: [
                'alimentation', 'épicerie', 'nourriture', 'produit', 'frais', 'surgelé', 'conserve', 'bio',
                'légume', 'fruit', 'viande', 'poisson', 'fromage', 'yaourt', 'lait', 'œuf', 'pain',
                'céréale', 'pâte', 'riz', 'huile', 'sucre', 'sel', 'épice', 'sauce', 'boisson', 'eau',
                'jus', 'soda', 'café', 'thé', 'alcool', 'vin', 'bière', 'snack', 'gâteau', 'chocolat'
            ],
            BusinessSector.OFFICE_SUPPLIES: [
                'fourniture', 'scolaire', 'bureau', 'cahier', 'carnet', 'stylo', 'crayon', 'feutre',
                'marqueur', 'gomme', 'règle', 'équerre', 'compas', 'calculatrice', 'classeur', 'chemise',
                'pochette', 'intercalaire', 'perforatrice', 'agrafeuse', 'cutter', 'ciseaux', 'colle',
                'scotch', 'post-it', 'étiquette', 'papier', 'cartouche', 'encre', 'toner', 'imprimante'
            ],
            BusinessSector.TOYS_GAMES: [
                'jouet', 'jeu', 'peluche', 'poupée', 'figurine', 'lego', 'puzzle', 'construction', 'maquette',
                'voiture', 'train', 'avion', 'robot', 'console', 'jeu-vidéo', 'carte', 'société', 'plateau',
                'éducatif', 'éveil', 'créatif', 'artistique', 'sport', 'extérieur', 'vélo', 'trottinette',
                'ballon', 'raquette', 'piscine', 'toboggan', 'balançoire', 'trampoline', 'loisir', 'récréatif'
            ],
            BusinessSector.PETS: [
                'animal', 'chien', 'chat', 'oiseau', 'poisson', 'rongeur', 'reptile', 'croquette', 'pâtée',
                'alimentation', 'nourriture', 'friandise', 'os', 'jouet', 'balle', 'corde', 'peluche',
                'collier', 'laisse', 'harnais', 'médaille', 'cage', 'aquarium', 'terrarium', 'litière',
                'coussin', 'panier', 'niche', 'gamelle', 'fontaine', 'transport', 'soin', 'shampoing', 'brosse'
            ],
            BusinessSector.DIGITAL_SERVICES: [
                'formation', 'cours', 'e-learning', 'formation-en-ligne', 'webinaire', 'coaching', 'consulting',
                'logiciel', 'application', 'app', 'plateforme', 'saas', 'cloud', 'hébergement', 'domaine',
                'site-web', 'développement', 'design', 'graphisme', 'marketing', 'seo', 'publicité',
                'réseaux-sociaux', 'contenu', 'rédaction', 'traduction', 'montage', 'vidéo', 'audio', 'podcast'
            ]
        }
        
        # Score par secteur
        sector_scores = {}
        for sector, indicators in sector_indicators.items():
            score = sum(1 for indicator in indicators if indicator in all_text)
            if score > 0:
                sector_scores[sector] = score
        
        # Retour du secteur avec le meilleur score
        if sector_scores:
            detected_sector = max(sector_scores, key=sector_scores.get)
            log3("[BUSINESS_CONFIG]", f"🎯 Secteur détecté: {detected_sector.value} (score: {sector_scores[detected_sector]})")
            return detected_sector
        
        return BusinessSector.GENERIC
    
    async def _get_products_sample(self, company_id: str, limit: int = 20) -> List[str]:
        """Récupération d'un échantillon de produits pour analyse"""
        
        try:
            # Récupération depuis documents indexés
            response = self.supabase.table("documents").select("content").eq("company_id", company_id).limit(limit).execute()
            
            if response.data:
                return [doc.get("content", "")[:100] for doc in response.data]
            
            return []
            
        except Exception as e:
            log3("[BUSINESS_CONFIG]", f"⚠️ Erreur récupération échantillon produits: {e}")
            return []
    
    async def _load_custom_keywords(self, company_id: str) -> Dict[str, Set[str]]:
        """Chargement des mots-clés personnalisés - Version simplifiée"""
        
        # Pas de table personnalisée pour l'instant
        return {}
    
    def _create_generic_config(self, company_id: str) -> BusinessConfig:
        """Création d'une configuration générique par défaut"""
        
        generic_template = self.sector_templates[BusinessSector.GENERIC]
        
        return BusinessConfig(
            company_id=company_id,
            sector=BusinessSector.GENERIC,
            business_name="Entreprise",
            keywords=generic_template.keywords,
            synonyms=generic_template.synonyms,
            offtopic_threshold=0.7,
            cache_ttl_hours=24
        )
    
    def _initialize_sector_templates(self) -> Dict[BusinessSector, BusinessConfig]:
        """Initialisation des templates de configuration par secteur"""
        
        templates = {}
        
        # Template Générique
        templates[BusinessSector.GENERIC] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.GENERIC,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'produit', 'article', 'item'},
                services={'service', 'livraison', 'support', 'assistance'},
                locations={'ville', 'région', 'zone'},
                brands={'marque', 'brand'},
                attributes={'prix', 'qualité', 'couleur', 'taille'},
                actions={'acheter', 'commander', 'réserver', 'contacter'}
            ),
            synonyms={
                'produit': ['article', 'item', 'marchandise'],
                'prix': ['coût', 'tarif', 'montant'],
                'qualité': ['bon', 'excellent', 'premium']
            }
        )
        
        # Template Automotive
        templates[BusinessSector.AUTOMOTIVE] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.AUTOMOTIVE,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'véhicule', 'auto', 'moto', 'pièce', 'équipement', 'accessoire'},
                services={'réparation', 'maintenance', 'livraison', 'installation'},
                locations={'garage', 'atelier', 'ville', 'région'},
                brands={'marque', 'constructeur'},
                attributes={'neuf', 'occasion', 'kilomètrage', 'année', 'couleur'},
                actions={'acheter', 'vendre', 'réparer', 'entretenir'}
            ),
            synonyms={
                'véhicule': ['auto', 'voiture', 'automobile'],
                'pièce': ['composant', 'élément', 'partie'],
                'réparation': ['dépannage', 'maintenance', 'service']
            }
        )
        
        # Template Fashion
        templates[BusinessSector.FASHION] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.FASHION,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'vêtement', 'chaussure', 'accessoire', 'sac', 'bijou'},
                services={'retouche', 'livraison', 'échange', 'retour'},
                locations={'boutique', 'magasin', 'ville'},
                brands={'marque', 'créateur', 'designer'},
                attributes={'taille', 'couleur', 'matière', 'style', 'saison'},
                actions={'porter', 'essayer', 'acheter', 'assortir'}
            ),
            synonyms={
                'vêtement': ['habit', 'tenue', 'outfit'],
                'taille': ['pointure', 'dimension'],
                'style': ['look', 'design', 'mode']
            }
        )
        
        # 📱 ÉLECTRONIQUE & INFORMATIQUE
        templates[BusinessSector.ELECTRONICS] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.ELECTRONICS,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'téléphone', 'smartphone', 'iphone', 'samsung', 'huawei', 'ordinateur', 'pc', 'laptop', 
                         'tablette', 'ipad', 'tv', 'télévision', 'écran', 'moniteur', 'casque', 'écouteurs', 
                         'enceinte', 'haut-parleur', 'console', 'playstation', 'xbox', 'nintendo', 'clavier', 
                         'souris', 'webcam', 'micro', 'chargeur', 'câble', 'adaptateur', 'batterie', 'coque'},
                services={'réparation', 'installation', 'configuration', 'dépannage', 'maintenance', 'livraison', 
                         'garantie', 'sav', 'support-technique'},
                locations={'magasin', 'boutique', 'showroom', 'atelier', 'service-client'},
                brands={'apple', 'samsung', 'huawei', 'xiaomi', 'oppo', 'sony', 'lg', 'dell', 'hp', 'asus', 
                        'lenovo', 'acer', 'microsoft', 'google', 'bose', 'jbl', 'beats'},
                attributes={'neuf', 'occasion', 'reconditionné', 'garantie', 'couleur', 'capacité', 'mémoire', 
                          'stockage', 'écran', 'pouces', 'résolution', 'batterie', 'autonomie', 'prix', 'promo'},
                actions={'acheter', 'commander', 'réserver', 'tester', 'comparer', 'échanger', 'réparer'}
            ),
            synonyms={
                'téléphone': ['smartphone', 'mobile', 'portable'],
                'ordinateur': ['pc', 'laptop', 'portable'],
                'télévision': ['tv', 'écran', 'téléviseur'],
                'casque': ['écouteurs', 'headset', 'audio']
            }
        )

        # 🏠 MAISON & ÉLECTROMÉNAGER  
        templates[BusinessSector.HOME_APPLIANCES] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.HOME_APPLIANCES,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'réfrigérateur', 'frigo', 'congélateur', 'cuisinière', 'four', 'micro-ondes', 'lave-linge', 
                         'lave-vaisselle', 'sèche-linge', 'aspirateur', 'nettoyeur', 'mixeur', 'blender', 'robot', 
                         'cafetière', 'expresso', 'grille-pain', 'bouilloire', 'climatiseur', 'ventilateur', 
                         'chauffage', 'radiateur', 'meuble', 'canapé', 'fauteuil', 'lit', 'matelas', 'armoire'},
                services={'livraison', 'installation', 'montage', 'réparation', 'maintenance', 'garantie', 'sav'},
                locations={'magasin', 'showroom', 'entrepôt', 'atelier'},
                brands={'samsung', 'lg', 'bosch', 'siemens', 'whirlpool', 'electrolux', 'candy', 'indesit', 
                        'beko', 'haier', 'ikea', 'conforama', 'but'},
                attributes={'capacité', 'litres', 'programmes', 'classe-énergétique', 'couleur', 'dimensions', 
                          'largeur', 'hauteur', 'profondeur', 'neuf', 'occasion', 'garantie', 'prix', 'promo'},
                actions={'acheter', 'commander', 'livrer', 'installer', 'monter', 'réparer', 'entretenir'}
            ),
            synonyms={
                'réfrigérateur': ['frigo', 'réfrigérateur-congélateur'],
                'lave-linge': ['machine-à-laver', 'lavante'],
                'micro-ondes': ['four-micro-ondes'],
                'aspirateur': ['aspirateur-traîneau', 'aspirateur-balai']
            }
        )

        # 👗 MODE & PRÊT-À-PORTER
        templates[BusinessSector.FASHION] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.FASHION,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'vêtement', 'habit', 'tenue', 'robe', 'pantalon', 'jean', 'chemise', 'chemisier', 'pull', 
                         'pullover', 'sweat', 'hoodie', 'manteau', 'veste', 'blouson', 't-shirt', 'polo', 'short', 
                         'bermuda', 'jupe', 'combinaison', 'costume', 'tailleur', 'chaussure', 'basket', 'sneakers', 
                         'botte', 'bottine', 'sandale', 'escarpin', 'mocassin', 'sac', 'sacoche', 'portefeuille'},
                services={'retouche', 'ajustement', 'livraison', 'échange', 'retour', 'conseil-style'},
                locations={'boutique', 'magasin', 'showroom', 'atelier-retouche'},
                brands={'zara', 'h&m', 'uniqlo', 'nike', 'adidas', 'puma', 'lacoste', 'tommy', 'calvin-klein', 
                        'levi\'s', 'diesel', 'guess', 'armani', 'hugo-boss'},
                attributes={'taille', 'pointure', 'couleur', 'matière', 'coton', 'polyester', 'laine', 'cuir', 
                          'style', 'casual', 'chic', 'sport', 'vintage', 'moderne', 'saison', 'été', 'hiver', 
                          'automne', 'printemps', 'neuf', 'occasion', 'prix', 'promo', 'soldes'},
                actions={'porter', 'essayer', 'acheter', 'commander', 'assortir', 'retoucher', 'échanger'}
            ),
            synonyms={
                'vêtement': ['habit', 'tenue', 'outfit'],
                'chaussure': ['soulier', 'chaussant'],
                'taille': ['pointure', 'dimension'],
                'style': ['look', 'design', 'mode']
            }
        )

        # 💄 BEAUTÉ & COSMÉTIQUES
        templates[BusinessSector.BEAUTY] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.BEAUTY,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'maquillage', 'fond-de-teint', 'concealer', 'poudre', 'blush', 'rouge-à-lèvres', 'gloss', 
                         'mascara', 'eye-liner', 'crayon', 'ombre-à-paupières', 'palette', 'vernis', 'parfum', 
                         'eau-de-toilette', 'eau-de-parfum', 'crème', 'sérum', 'lotion', 'huile', 'masque', 
                         'gommage', 'nettoyant', 'démaquillant', 'tonique', 'hydratant', 'anti-âge', 'anti-rides'},
                services={'conseil-beauté', 'maquillage', 'soin-visage', 'manucure', 'pédicure', 'épilation', 
                         'massage', 'livraison'},
                locations={'institut', 'salon', 'spa', 'parfumerie', 'boutique'},
                brands={'l\'oréal', 'maybelline', 'revlon', 'mac', 'sephora', 'yves-saint-laurent', 'dior', 
                        'chanel', 'lancôme', 'clinique', 'estée-lauder', 'nivea', 'garnier', 'vichy'},
                attributes={'couleur', 'teinte', 'nuance', 'texture', 'mat', 'brillant', 'waterproof', 'longue-tenue', 
                          'bio', 'naturel', 'vegan', 'hypoallergénique', 'tous-types-peau', 'peau-sensible', 
                          'anti-âge', 'hydratant', 'nourrissant', 'prix', 'promo'},
                actions={'maquiller', 'démaquiller', 'hydrater', 'nourrir', 'protéger', 'appliquer', 'acheter'}
            ),
            synonyms={
                'maquillage': ['cosmétique', 'make-up'],
                'parfum': ['fragrance', 'eau-de-toilette'],
                'crème': ['soin', 'lotion'],
                'shampoing': ['lavant', 'nettoyant-capillaire']
            }
        )

        # 👶 BÉBÉ & PUÉRICULTURE
        templates[BusinessSector.BABY_CARE] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.BABY_CARE,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'couches', 'culottes', 'lingettes', 'bébé', 'enfant', 'nourrisson', 'bambin', 'nouveau-né', 
                         'pression', 'biberon', 'tétine', 'sucette', 'lait-infantile', 'céréales', 'petit-pot', 
                         'compote', 'poussette', 'landau', 'siège-auto', 'cosy', 'lit', 'berceau', 'matelas', 
                         'gigoteuse', 'turbulette', 'body', 'pyjama', 'grenouillère', 'chaussons', 'bonnet'},
                services={'livraison', 'conseil', 'support', 'échange', 'retour', 'installation', 'montage'},
                locations={'magasin', 'boutique', 'puériculture', 'pharmacie'},
                brands={'pampers', 'huggies', 'babylove', 'lotus', 'chicco', 'bébé-confort', 'maxi-cosi', 
                        'cybex', 'stokke', 'babybjörn', 'fisher-price', 'vtech', 'sophie-la-girafe'},
                attributes={'taille', 'poids', 'âge', 'mois', 'kg', 'absorption', 'confort', 'douceur', 'hypoallergénique', 
                          'dermatologiquement-testé', 'bio', 'écologique', 'sécurité', 'norme', 'prix', 'promo'},
                actions={'acheter', 'commander', 'choisir', 'utiliser', 'changer', 'nourrir', 'bercer', 'jouer'}
            ),
            synonyms={
                'couches': ['couche', 'lange', 'protection'],
                'taille': ['pointure', 'dimension', 'grandeur'],
                'bébé': ['enfant', 'nourrisson', 'bambin', 'petit'],
                'pression': ['adhésif', 'fermeture', 'scratch']
            }
        )

        # 🚗 AUTO & MOTO
        templates[BusinessSector.AUTOMOTIVE] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.AUTOMOTIVE,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'casque', 'gants', 'blouson', 'protection', 'équipement', 'moto', 'scooter', 'quad', 
                         'voiture', 'auto', 'véhicule', 'pièce', 'moteur', 'pneu', 'jante', 'amortisseur', 
                         'frein', 'embrayage', 'batterie', 'phare', 'feu', 'rétroviseur', 'pare-brise', 
                         'essuie-glace', 'huile', 'filtre', 'bougie', 'courroie', 'accessoire', 'tuning'},
                services={'réparation', 'maintenance', 'installation', 'dépannage', 'contrôle-technique', 'livraison'},
                locations={'garage', 'atelier', 'concessionnaire', 'magasin', 'casse'},
                brands={'yamaha', 'honda', 'kawasaki', 'suzuki', 'bmw', 'ducati', 'harley', 'peugeot', 
                        'renault', 'citroën', 'volkswagen', 'mercedes', 'audi', 'toyota', 'nissan'},
                attributes={'neuf', 'occasion', 'kilométrage', 'année', 'couleur', 'cylindrée', 'puissance', 
                          'carburant', 'essence', 'diesel', 'électrique', 'hybride', 'automatique', 'manuelle'},
                actions={'acheter', 'vendre', 'réparer', 'entretenir', 'réviser', 'contrôler', 'assurer'}
            ),
            synonyms={
                'véhicule': ['auto', 'voiture', 'automobile'],
                'moto': ['motocyclette', 'deux-roues'],
                'pièce': ['composant', 'élément', 'partie'],
                'réparation': ['dépannage', 'maintenance', 'service']
            }
        )

        # 🛒 ÉPICERIE & ALIMENTATION
        templates[BusinessSector.FOOD] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.FOOD,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'légume', 'fruit', 'viande', 'poisson', 'fromage', 'yaourt', 'lait', 'œuf', 'pain', 
                         'céréale', 'pâte', 'riz', 'huile', 'sucre', 'sel', 'épice', 'sauce', 'conserve', 
                         'surgelé', 'frais', 'bio', 'boisson', 'eau', 'jus', 'soda', 'café', 'thé', 
                         'alcool', 'vin', 'bière', 'snack', 'gâteau', 'chocolat', 'bonbon', 'biscuit'},
                services={'livraison', 'commande', 'réservation', 'conseil-nutrition', 'préparation'},
                locations={'épicerie', 'supermarché', 'marché', 'boulangerie', 'boucherie', 'poissonnerie'},
                brands={'nestlé', 'danone', 'coca-cola', 'pepsi', 'ferrero', 'unilever', 'kraft', 
                        'mondelez', 'mars', 'kellogg', 'barilla', 'président', 'yoplait'},
                attributes={'bio', 'naturel', 'frais', 'surgelé', 'conserve', 'local', 'importé', 'saison', 
                          'date-limite', 'calories', 'sans-gluten', 'vegan', 'halal', 'casher', 'prix', 'promo'},
                actions={'manger', 'boire', 'cuisiner', 'préparer', 'conserver', 'acheter', 'commander'}
            ),
            synonyms={
                'légume': ['légumineuse', 'verdure'],
                'viande': ['chair', 'protéine'],
                'boisson': ['breuvage', 'liquide'],
                'épicerie': ['alimentation', 'nourriture']
            }
        )

        # 📚 FOURNITURES SCOLAIRES & BUREAU
        templates[BusinessSector.OFFICE_SUPPLIES] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.OFFICE_SUPPLIES,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'cahier', 'carnet', 'stylo', 'crayon', 'feutre', 'marqueur', 'surligneur', 'gomme', 
                         'règle', 'équerre', 'compas', 'calculatrice', 'classeur', 'chemise', 'pochette', 
                         'intercalaire', 'perforatrice', 'agrafeuse', 'cutter', 'ciseaux', 'colle', 'scotch', 
                         'post-it', 'étiquette', 'papier', 'feuille', 'cartouche', 'encre', 'toner', 'imprimante'},
                services={'livraison', 'commande', 'personnalisation', 'gravure', 'impression'},
                locations={'papeterie', 'librairie', 'bureau', 'école', 'université'},
                brands={'bic', 'stabilo', 'pilot', 'parker', 'waterman', 'oxford', 'clairefontaine', 
                        'rhodia', 'canson', 'hp', 'canon', 'epson', 'brother', 'samsung'},
                attributes={'couleur', 'format', 'grammage', 'qualité', 'recyclé', 'écologique', 'rechargeable', 
                          'effaçable', 'permanent', 'temporaire', 'scolaire', 'professionnel', 'prix', 'lot'},
                actions={'écrire', 'dessiner', 'calculer', 'classer', 'ranger', 'imprimer', 'photocopier'}
            ),
            synonyms={
                'cahier': ['carnet', 'bloc-notes'],
                'stylo': ['bic', 'plume'],
                'fourniture': ['matériel', 'équipement'],
                'bureau': ['office', 'travail']
            }
        )

        # 🎮 JEUX, JOUETS, LOISIRS
        templates[BusinessSector.TOYS_GAMES] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.TOYS_GAMES,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'jouet', 'jeu', 'peluche', 'poupée', 'figurine', 'lego', 'playmobil', 'puzzle', 
                         'construction', 'maquette', 'voiture', 'train', 'avion', 'robot', 'console', 
                         'jeu-vidéo', 'carte', 'société', 'plateau', 'éducatif', 'éveil', 'créatif', 
                         'artistique', 'sport', 'extérieur', 'vélo', 'trottinette', 'ballon', 'raquette'},
                services={'réparation', 'assemblage', 'animation', 'location', 'livraison'},
                locations={'magasin-jouets', 'ludothèque', 'parc', 'centre-loisirs'},
                brands={'lego', 'playmobil', 'mattel', 'hasbro', 'fisher-price', 'vtech', 'nintendo', 
                        'sony', 'microsoft', 'bandai', 'ravensburger', 'djeco', 'janod', 'smoby'},
                attributes={'âge', 'éducatif', 'créatif', 'électronique', 'manuel', 'collectif', 'individuel', 
                          'intérieur', 'extérieur', 'garçon', 'fille', 'mixte', 'sécurité', 'norme', 'prix'},
                actions={'jouer', 'construire', 'créer', 'apprendre', 'découvrir', 'collectionner', 'offrir'}
            ),
            synonyms={
                'jouet': ['jeu', 'ludique'],
                'console': ['gaming', 'jeu-vidéo'],
                'puzzle': ['casse-tête', 'énigme'],
                'loisir': ['divertissement', 'récréation']
            }
        )

        # 🐾 PRODUITS POUR ANIMAUX
        templates[BusinessSector.PETS] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.PETS,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'croquette', 'pâtée', 'friandise', 'os', 'jouet', 'balle', 'corde', 'peluche', 
                         'collier', 'laisse', 'harnais', 'médaille', 'cage', 'aquarium', 'terrarium', 
                         'litière', 'coussin', 'panier', 'niche', 'gamelle', 'fontaine', 'transport', 
                         'shampoing', 'brosse', 'coupe-ongles', 'antiparasitaire', 'vermifuge'},
                services={'toilettage', 'dressage', 'garde', 'pension', 'vétérinaire', 'livraison'},
                locations={'animalerie', 'vétérinaire', 'toiletteur', 'pension', 'refuge'},
                brands={'royal-canin', 'purina', 'hill\'s', 'eukanuba', 'whiskas', 'pedigree', 
                        'friskies', 'felix', 'sheba', 'iams', 'pro-plan', 'advance'},
                attributes={'chien', 'chat', 'oiseau', 'poisson', 'rongeur', 'reptile', 'âge', 'taille', 
                          'race', 'stérilisé', 'senior', 'junior', 'adulte', 'sensible', 'bio', 'premium'},
                actions={'nourrir', 'soigner', 'brosser', 'promener', 'dresser', 'jouer', 'câliner'}
            ),
            synonyms={
                'croquette': ['aliment-sec', 'nourriture'],
                'pâtée': ['aliment-humide', 'conserve'],
                'animal': ['compagnon', 'familier'],
                'vétérinaire': ['véto', 'docteur']
            }
        )

        # 💻 SERVICES NUMÉRIQUES & INFOPRODUITS
        templates[BusinessSector.DIGITAL_SERVICES] = BusinessConfig(
            company_id="template",
            sector=BusinessSector.DIGITAL_SERVICES,
            business_name="Template",
            keywords=BusinessKeywords(
                products={'formation', 'cours', 'e-learning', 'webinaire', 'coaching', 'consulting', 
                         'logiciel', 'application', 'app', 'plateforme', 'saas', 'cloud', 'hébergement', 
                         'domaine', 'site-web', 'template', 'thème', 'plugin', 'extension', 'ebook', 
                         'guide', 'tutoriel', 'vidéo', 'podcast', 'musique', 'photo', 'design'},
                services={'développement', 'design', 'marketing', 'seo', 'publicité', 'réseaux-sociaux', 
                         'rédaction', 'traduction', 'montage', 'support', 'maintenance'},
                locations={'bureau', 'coworking', 'domicile', 'distance', 'ligne'},
                brands={'microsoft', 'google', 'adobe', 'salesforce', 'hubspot', 'mailchimp', 
                        'wordpress', 'shopify', 'zoom', 'slack', 'trello', 'notion'},
                attributes={'en-ligne', 'digital', 'numérique', 'cloud', 'mobile', 'responsive', 
                          'sécurisé', 'évolutif', 'personnalisable', 'multilingue', 'prix', 'abonnement'},
                actions={'apprendre', 'former', 'développer', 'créer', 'optimiser', 'automatiser', 'analyser'}
            ),
            synonyms={
                'formation': ['cours', 'apprentissage'],
                'logiciel': ['software', 'programme'],
                'numérique': ['digital', 'électronique'],
                'en-ligne': ['online', 'web']
            }
        )
        
        return templates
    
    async def update_business_keywords(self, company_id: str, new_keywords: Dict[str, List[str]]):
        """Mise à jour des mots-clés métier d'une entreprise"""
        
        try:
            # Mise à jour en base
            await self.supabase.table("business_keywords").upsert({
                "company_id": company_id,
                **new_keywords
            }).execute()
            
            # Invalidation du cache
            cache_manager.delete(f"business_config:{company_id}")
            if company_id in self.configs_cache:
                del self.configs_cache[company_id]
            
            log3("[BUSINESS_CONFIG]", f"✅ Mots-clés mis à jour pour {company_id}")
            
        except Exception as e:
            log3("[BUSINESS_CONFIG]", f"❌ Erreur mise à jour mots-clés: {e}")


# Instance globale
business_config_manager = BusinessConfigManager()

# API principale
async def get_business_config(company_id: str) -> BusinessConfig:
    """API principale - Récupération de la configuration métier"""
    return await business_config_manager.get_business_config(company_id)
