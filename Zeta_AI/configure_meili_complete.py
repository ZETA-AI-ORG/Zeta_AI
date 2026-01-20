#!/usr/bin/env python3
"""
🔧 CONFIGURATION COMPLÈTE MEILISEARCH
Configure tous les attributs searchable, filterable, sortable pour tous les index
SCALABLE: Fonctionne pour 1 comme pour 1000 entreprises
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List, Set
import meilisearch
import re

# Configuration
MEILI_URL = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
MEILI_API_KEY = os.getenv("MEILI_MASTER_KEY", "")

# Couleurs
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 📊 CONFIGURATION OPTIMALE POUR TOUS LES TYPES
# ==========================================

OPTIMAL_SETTINGS = {
    "searchableAttributes": [
        # Texte principal
        "searchable_text",
        "content",
        "content_fr",
        "text",
        
        # Produits
        "product_name",
        "name",
        "description",
        "brand",
        
        # Attributs produit
        "color",
        "category",
        "subcategory",
        "size",
        "tags",
        
        # Livraison
        "zone",
        "zone_name",
        "zone_group",
        "city",
        "commune",
        "quartier",
        
        # Paiement
        "method",
        "payment_method",
        "contact_info",
        
        # Localisation
        "address",
        "location",
        "location_name",
        
        # Support
        "question",
        "answer",
        "faq_question",
        "faq_answer",
        
        # Général
        "title",
        "details",
        "notes",
        "slug"
    ],
    
    "filterableAttributes": [
        # Identifiants
        "company_id",
        "id",
        "type",
        "doc_type",
        
        # Produits
        "category",
        "subcategory",
        "color",
        "brand",
        "size",
        "stock",
        "in_stock",
        "available",
        
        # Prix
        "price",
        "min_price",
        "max_price",
        "currency",
        "fee",
        "delivery_fee",
        
        # Livraison
        "zone",
        "zone_group",
        "city",
        "free_delivery",
        "express_available",
        
        # Paiement
        "method",
        "payment_method",
        "payment_accepted",
        
        # Conditions
        "acompte_required",
        "prepaid_only",
        "policy_kind",
        
        # Métadonnées
        "tags",
        "section",
        "language",
        "is_active",
        "visibility",
        
        # Dates
        "created_at",
        "updated_at",
        "last_modified"
    ],
    
    "sortableAttributes": [
        # Prix
        "price",
        "min_price",
        "max_price",
        "fee",
        "delivery_fee",
        
        # Stock
        "stock",
        "quantity",
        
        # Dates
        "created_at",
        "updated_at",
        "last_modified",
        
        # Priorité
        "priority",
        "order",
        "rank",
        "popularity"
    ],
    
    "displayedAttributes": [
        "*"  # Afficher tous les attributs
    ],
    
    "rankingRules": [
        "words",
        "typo",
        "proximity",
        "attribute",
        "sort",
        "exactness"
    ],
    
    "typoTolerance": {
        "enabled": True,
        "minWordSizeForTypos": {
            "oneTypo": 4,
            "twoTypos": 8
        },
        "disableOnWords": [],
        "disableOnAttributes": []
    },
    
    "synonyms": {
        # Villes
        "cocody": ["cocody-angré", "cocody-danga", "cocody-riviera"],
        "yopougon": ["yop", "yopougon-niangon", "yopougon-selmer"],
        "abidjan": ["cocody", "yopougon", "plateau", "marcory", "treichville", "abobo", "adjamé"],
        
        # Produits génériques
        "couche": ["couches", "pampers", "huggies"],
        "culotte": ["culottes"],
        "bebe": ["bébé", "enfant", "nourrisson"],
        
        # Couleurs
        "noir": ["black", "noire"],
        "bleu": ["blue", "bleue"],
        "rouge": ["red"],
        "blanc": ["white", "blanche"],
        "gris": ["gray", "grey", "grise"],
        "vert": ["green", "verte"],
        "jaune": ["yellow"],
        "rose": ["pink"],
        
        # Paiement
        "wave": ["waveci", "orange money", "om"],
        "paiement": ["payment", "payement"],
        "acompte": ["accompte", "avance", "arrhes"],
        
        # Livraison
        "livraison": ["delivery", "shipping", "expedition"],
        "gratuit": ["free", "gratuite"],
        "express": ["rapide", "urgent"]
    },
    
    "stopWords": [
        "le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux",
        "en", "pour", "sur", "par", "avec", "sans", "ce", "cette", "ces", "son", "sa",
        "mon", "ma", "ton", "ta", "notre", "votre", "leur", "il", "elle", "nous", "vous"
    ],
    
    "faceting": {
        "maxValuesPerFacet": 200
    },
    
    "pagination": {
        "maxTotalHits": 2000
    },
    
    "separatorTokens": [
        "|", "/", "\\", ":", ";", ",", ".", "!", "?", "-", "_", "(", ")", "[", "]", "{", "}", "<", ">", "\"", "'", "`"
    ],
    
    "nonSeparatorTokens": [
        "@", "#", "$", "%", "&", "+", "="
    ]
}


def extract_company_id_from_index(index_name: str) -> str:
    """Extrait le company_id d'un nom d'index"""
    # Format attendu: type_company_id
    # Ex: company_docs_MpfnlSbqwaZ6F4HvxQLRL9du0yG3
    parts = index_name.split('_', 2)  # Split en max 3 parties
    if len(parts) >= 3:
        return parts[2]  # Retourne tout après le deuxième underscore
    elif len(parts) == 2:
        return parts[1]  # Format simple: type_id
    return ""


def get_all_company_ids(client: meilisearch.Client) -> Set[str]:
    """Récupère tous les company_id depuis les index existants"""
    logger.info(f"\n{Colors.CYAN}🔍 Détection automatique des entreprises...{Colors.END}")
    
    company_ids = set()
    
    try:
        # Récupérer tous les index
        indexes = client.get_indexes()
        
        logger.info(f"   📊 {len(indexes['results'])} index trouvés")
        
        # Extraire les company_id
        for index_info in indexes['results']:
            index_name = index_info.uid
            
            # Vérifier si c'est un index d'entreprise (contient un underscore)
            if '_' in index_name:
                # Extraire le company_id
                company_id = extract_company_id_from_index(index_name)
                
                if company_id and len(company_id) > 10:  # Filtre: company_id valide
                    company_ids.add(company_id)
                    logger.info(f"   ✅ Entreprise détectée: {company_id[:8]}...")
        
        logger.info(f"\n   {Colors.GREEN}🎯 Total: {len(company_ids)} entreprise(s) détectée(s){Colors.END}")
        
    except Exception as e:
        logger.error(f"   {Colors.RED}❌ Erreur lors de la détection: {e}{Colors.END}")
    
    return company_ids


def get_index_name(base: str, company_id: str) -> str:
    """Construit le nom d'index selon la convention"""
    return f"{base}_{company_id}"


def configure_index(client: meilisearch.Client, index_name: str) -> Dict[str, Any]:
    """Configure un index avec les paramètres optimaux"""
    logger.info(f"\n{Colors.CYAN}🔧 Configuration de l'index: {Colors.BOLD}{index_name}{Colors.END}")
    
    try:
        # Récupérer l'index
        index = client.index(index_name)
        
        # Vérifier qu'il existe
        try:
            stats = index.get_stats()
            doc_count = stats.number_of_documents
            logger.info(f"   📊 Documents actuels: {doc_count}")
        except Exception as e:
            logger.warning(f"   ⚠️  Index n'existe pas encore: {e}")
            return {"success": False, "error": "Index non trouvé", "index": index_name}
        
        # Appliquer les settings
        logger.info(f"   ⚙️  Application des paramètres...")
        task = index.update_settings(OPTIMAL_SETTINGS)
        logger.info(f"   ✅ Task ID: {task.task_uid}")
        
        # Vérifier les settings appliqués
        import time
        time.sleep(2)  # Attendre que la tâche se termine
        
        settings = index.get_settings()
        
        return {
            "success": True,
            "index": index_name,
            "task_uid": task.task_uid,
            "searchable_count": len(settings.get("searchableAttributes", [])),
            "filterable_count": len(settings.get("filterableAttributes", [])),
            "sortable_count": len(settings.get("sortableAttributes", [])),
            "documents": doc_count
        }
        
    except Exception as e:
        logger.error(f"   {Colors.RED}❌ Erreur: {e}{Colors.END}")
        return {"success": False, "error": str(e), "index": index_name}


def configure_all_companies(client: meilisearch.Client, company_ids: Set[str], verbose: bool = False) -> List[Dict[str, Any]]:
    """Configure tous les index pour toutes les entreprises"""
    
    # Liste des index à configurer
    index_types = [
        "company_docs",  # Index unifié principal
        "products",
        "delivery",
        "support_paiement",
        "localisation"
    ]
    
    all_results = []
    
    print(f"\n{Colors.BOLD}🔄 Configuration pour {len(company_ids)} entreprise(s)...{Colors.END}\n")
    
    for i, company_id in enumerate(sorted(company_ids), 1):
        print(f"\n{Colors.MAGENTA}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}[{i}/{len(company_ids)}] Entreprise: {company_id[:12]}...{Colors.END}")
        print(f"{Colors.MAGENTA}{'='*80}{Colors.END}")
        
        company_results = []
        
        for base_type in index_types:
            index_name = get_index_name(base_type, company_id)
            
            if verbose:
                result = configure_index(client, index_name)
            else:
                # Mode silencieux: juste configurer sans logs détaillés
                try:
                    index = client.index(index_name)
                    stats = index.get_stats()
                    task = index.update_settings(OPTIMAL_SETTINGS)
                    result = {
                        "success": True,
                        "index": index_name,
                        "task_uid": task.task_uid,
                        "documents": stats.number_of_documents
                    }
                    print(f"   {Colors.GREEN}✅{Colors.END} {base_type:<20} ({stats.number_of_documents} docs)")
                except Exception as e:
                    result = {"success": False, "error": str(e), "index": index_name}
                    print(f"   {Colors.RED}❌{Colors.END} {base_type:<20} (erreur)")
            
            company_results.append(result)
        
        all_results.extend(company_results)
    
    return all_results


def main():
    """Configuration principale"""
    
    # Arguments ligne de commande
    parser = argparse.ArgumentParser(
        description="Configure MeiliSearch pour une ou plusieurs entreprises",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  
  # Configurer TOUTES les entreprises (auto-détection)
  python configure_meili_complete.py --all
  
  # Configurer une entreprise spécifique
  python configure_meili_complete.py --company MpfnlSbqwaZ6F4HvxQLRL9du0yG3
  
  # Configurer plusieurs entreprises
  python configure_meili_complete.py --company ID1 --company ID2
  
  # Mode verbeux (logs détaillés)
  python configure_meili_complete.py --all --verbose
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Configurer toutes les entreprises (auto-détection)"
    )
    
    parser.add_argument(
        "--company",
        action="append",
        dest="companies",
        help="ID d'une entreprise spécifique (peut être répété)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Mode verbeux avec logs détaillés"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║           🔧 CONFIGURATION COMPLÈTE MEILISEARCH                      ║")
    print("║              SCALABLE: 1 à 1000+ entreprises                         ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    print(f"\n{Colors.YELLOW}📊 Configuration:{Colors.END}")
    print(f"   URL: {MEILI_URL}")
    
    # Connexion à MeiliSearch
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)
        version = client.get_version()
        print(f"   {Colors.GREEN}✅ Connecté à MeiliSearch {version['pkgVersion']}{Colors.END}")
    except Exception as e:
        print(f"   {Colors.RED}❌ Erreur de connexion: {e}{Colors.END}")
        sys.exit(1)
    
    # Déterminer les entreprises à configurer
    company_ids = set()
    
    if args.all:
        # Auto-détection de toutes les entreprises
        company_ids = get_all_company_ids(client)
        if not company_ids:
            print(f"\n{Colors.RED}❌ Aucune entreprise détectée{Colors.END}")
            sys.exit(1)
    
    elif args.companies:
        # Entreprises spécifiques
        company_ids = set(args.companies)
        print(f"\n{Colors.CYAN}🎯 Entreprises sélectionnées: {len(company_ids)}{Colors.END}")
        for cid in company_ids:
            print(f"   • {cid}")
    
    else:
        # Mode par défaut: demander à l'utilisateur
        print(f"\n{Colors.YELLOW}⚠️  Aucune option spécifiée{Colors.END}")
        print(f"\nOptions disponibles:")
        print(f"  1. Configurer TOUTES les entreprises (auto-détection)")
        print(f"  2. Entrer un company_id manuellement")
        print(f"  3. Quitter")
        
        choice = input(f"\n{Colors.BOLD}Votre choix (1-3): {Colors.END}").strip()
        
        if choice == "1":
            company_ids = get_all_company_ids(client)
            if not company_ids:
                print(f"\n{Colors.RED}❌ Aucune entreprise détectée{Colors.END}")
                sys.exit(1)
        elif choice == "2":
            cid = input(f"{Colors.BOLD}Company ID: {Colors.END}").strip()
            if cid:
                company_ids.add(cid)
            else:
                print(f"{Colors.RED}❌ Company ID invalide{Colors.END}")
                sys.exit(1)
        else:
            print(f"{Colors.YELLOW}👋 Au revoir !{Colors.END}")
            sys.exit(0)
    
    # Configuration
    results = configure_all_companies(client, company_ids, verbose=args.verbose)
    
    # ==========================================
    # 📊 RAPPORT FINAL
    # ==========================================
    print(f"\n\n{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                       📊 RAPPORT FINAL                                ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    success_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    total_docs = sum(r.get("documents", 0) for r in results if r.get("success"))
    
    print(f"{Colors.BOLD}📈 Résultats globaux:{Colors.END}")
    print(f"   Entreprises traitées: {len(company_ids)}")
    print(f"   Total index: {total_count}")
    print(f"   {Colors.GREEN}✅ Configurés: {success_count}{Colors.END}")
    print(f"   {Colors.RED}❌ Échoués: {total_count - success_count}{Colors.END}")
    print(f"   📄 Documents totaux: {total_docs:,}")
    
    # Statistiques par entreprise
    if len(company_ids) > 1:
        print(f"\n{Colors.BOLD}📊 Par entreprise:{Colors.END}")
        
        company_stats = {}
        for result in results:
            if result.get("success"):
                index_name = result.get("index", "")
                company_id = extract_company_id_from_index(index_name)
                
                if company_id not in company_stats:
                    company_stats[company_id] = {"success": 0, "failed": 0, "docs": 0}
                
                company_stats[company_id]["success"] += 1
                company_stats[company_id]["docs"] += result.get("documents", 0)
        
        for company_id in sorted(company_ids):
            if company_id in company_stats:
                stats = company_stats[company_id]
                print(f"   • {company_id[:12]}... → {stats['success']} index, {stats['docs']:,} docs")
    
    # Mode verbeux: détails par index
    if args.verbose:
        print(f"\n{Colors.BOLD}📋 Détails par index:{Colors.END}\n")
        
        for result in results:
            if result.get("success"):
                icon = f"{Colors.GREEN}✅{Colors.END}"
                print(f"   {icon} {Colors.BOLD}{result['index']}{Colors.END}")
                if result.get('searchable_count'):
                    print(f"      Searchable: {result.get('searchable_count', 0)} attributs")
                    print(f"      Filterable: {result.get('filterable_count', 0)} attributs")
                    print(f"      Sortable: {result.get('sortable_count', 0)} attributs")
                print(f"      Documents: {result.get('documents', 0)}")
                print()
            else:
                icon = f"{Colors.RED}❌{Colors.END}"
                print(f"   {icon} {Colors.BOLD}{result['index']}{Colors.END}")
                print(f"      Erreur: {result.get('error', 'Unknown')}")
                print()
    
    print(f"\n{Colors.BOLD}✨ Configuration appliquée:{Colors.END}")
    print(f"   • {len(OPTIMAL_SETTINGS['searchableAttributes'])} attributs searchable")
    print(f"   • {len(OPTIMAL_SETTINGS['filterableAttributes'])} attributs filterable")
    print(f"   • {len(OPTIMAL_SETTINGS['sortableAttributes'])} attributs sortable")
    print(f"   • {len(OPTIMAL_SETTINGS['synonyms'])} groupes de synonymes")
    print(f"   • Typo tolerance: activée")
    print(f"   • Stop words: {len(OPTIMAL_SETTINGS['stopWords'])} mots")
    
    # Note finale
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    if success_rate == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 CONFIGURATION COMPLÈTE RÉUSSIE !{Colors.END}")
        print(f"{Colors.GREEN}   {len(company_ids)} entreprise(s), {success_count} index configurés{Colors.END}\n")
    elif success_rate >= 80:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  CONFIGURATION PARTIELLE{Colors.END}")
        print(f"{Colors.YELLOW}   {success_rate:.1f}% de réussite{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ ÉCHEC PARTIEL{Colors.END}")
        print(f"{Colors.RED}   Seulement {success_rate:.1f}% configurés{Colors.END}\n")


if __name__ == "__main__":
    main()
