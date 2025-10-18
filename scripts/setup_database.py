#!/usr/bin/env python3
"""
🗄️ SCRIPT DE CONFIGURATION BASE DE DONNÉES
Configuration automatique des tables et données initiales
"""

import asyncio
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent.parent))

from database.supabase_client import get_supabase_client
from core.company_config_manager import CompanyConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_company_config_table():
    """Crée la table company_configurations si elle n'existe pas"""
    
    # Lire le script SQL
    sql_file = Path(__file__).parent.parent / "database" / "create_company_config_table.sql"
    
    if not sql_file.exists():
        logger.error(f"Fichier SQL non trouvé: {sql_file}")
        return False
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        supabase = get_supabase_client()
        
        # Diviser le script en commandes individuelles
        commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
        
        for i, command in enumerate(commands):
            if command:
                logger.info(f"Exécution commande {i+1}/{len(commands)}")
                try:
                    result = supabase.rpc('execute_sql', {'sql_query': command}).execute()
                    logger.info(f"✅ Commande {i+1} exécutée avec succès")
                except Exception as cmd_error:
                    logger.warning(f"⚠️ Commande {i+1} échouée (peut-être déjà existante): {str(cmd_error)}")
        
        logger.info("✅ Configuration de la base de données terminée")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur configuration base de données: {str(e)}")
        return False

async def setup_default_company_configs():
    """Configure les configurations par défaut pour les entreprises de test"""
    
    config_manager = CompanyConfigManager()
    
    # Configuration pour Rue du Gros (exemple réel)
    rue_du_gros_config = {
        "business_rules": {
            "allow_pricing": False,
            "allow_promotions": False,
            "require_uncertainty": True,
            "max_product_claims": 5
        },
        "product_catalog": {
            "categories": ["couches", "lingettes", "soins bébé", "puériculture"],
            "sizes": ["1", "2", "3", "4", "5", "6"],
            "services": ["livraison", "conseil", "support", "retour"]
        },
        "validation_rules": {
            "dangerous_sizes": r"[789]\d*",
            "price_patterns": r"\d+[,.]?\d*\s*(?:€|FCFA|EUR)",
            "promo_patterns": r"\d+%"
        },
        "response_templates": {
            "unknown_product": "Je ne trouve pas ce produit dans notre catalogue de puériculture. Puis-je vous aider avec autre chose ?",
            "no_pricing": "Je n'ai pas accès aux prix en temps réel. Je vous recommande de consulter notre site web ou de contacter notre service client.",
            "no_promotion": "Je ne peux pas confirmer les promotions en cours. Pour connaître nos offres actuelles, consultez notre site web.",
            "uncertainty": "Je n'ai pas cette information précise dans ma base de connaissances. Puis-je vous orienter vers notre service client ?",
            "invalid_size": "Je ne trouve pas cette taille dans notre gamme. Nos couches sont disponibles en tailles 1 à 6. Puis-je vous aider à trouver la taille adaptée à votre bébé ?"
        }
    }
    
    # Configuration pour TechMega Store (exemple test)
    techmega_config = {
        "business_rules": {
            "allow_pricing": True,
            "allow_promotions": True,
            "require_uncertainty": False,
            "max_product_claims": 10
        },
        "product_catalog": {
            "categories": ["smartphones", "laptops", "consoles", "accessoires", "électronique"],
            "sizes": ["S", "M", "L", "XL", "32GB", "64GB", "128GB", "256GB", "512GB"],
            "services": ["livraison", "installation", "garantie", "réparation"]
        },
        "validation_rules": {
            "dangerous_sizes": r"999\d*",
            "price_patterns": r"\d+[,.]?\d*\s*(?:€|EUR|\$|USD)",
            "promo_patterns": r"\d+%|\-\d+€"
        },
        "response_templates": {
            "unknown_product": "Ce produit n'est pas disponible dans notre catalogue électronique. Puis-je vous proposer une alternative ?",
            "no_pricing": "Consultez notre site web pour les prix les plus récents ou contactez notre service commercial.",
            "no_promotion": "Vérifiez nos promotions actuelles sur notre site web ou inscrivez-vous à notre newsletter.",
            "uncertainty": "Pour des informations techniques précises, je vous recommande de contacter notre support technique.",
            "invalid_size": "Cette configuration n'est pas disponible. Consultez les spécifications disponibles sur notre site."
        }
    }
    
    # Sauvegarder les configurations
    companies = [
        ("MpfnlSbqwaZ6F4HvxQLRL9du0yG3", rue_du_gros_config),  # Rue du Gros
        ("XkCn8fjNWEWwqiiKMgJX7OcQrUJ4", techmega_config),     # TechMega Store
    ]
    
    for company_id, config in companies:
        try:
            success = await config_manager.update_company_config(company_id, config)
            if success:
                logger.info(f"✅ Configuration sauvegardée pour {company_id}")
            else:
                logger.error(f"❌ Échec sauvegarde pour {company_id}")
        except Exception as e:
            logger.error(f"❌ Erreur configuration {company_id}: {str(e)}")

async def test_database_connection():
    """Test la connexion à la base de données"""
    try:
        supabase = get_supabase_client()
        
        # Test simple de connexion
        result = supabase.table('company_rag_configs').select('count', count='exact').execute()
        
        logger.info(f"✅ Connexion base de données OK - {result.count} configurations trouvées")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur connexion base de données: {str(e)}")
        return False

async def main():
    """Script principal de configuration"""
    logger.info("🚀 Démarrage configuration base de données...")
    
    # 1. Test connexion
    logger.info("1️⃣ Test de connexion...")
    if not await test_database_connection():
        logger.error("❌ Impossible de se connecter à la base de données")
        return
    
    # 2. Création des tables
    logger.info("2️⃣ Création des tables...")
    if not await create_company_config_table():
        logger.error("❌ Échec création des tables")
        return
    
    # 3. Configuration des entreprises par défaut
    logger.info("3️⃣ Configuration des entreprises par défaut...")
    await setup_default_company_configs()
    
    # 4. Vérification finale
    logger.info("4️⃣ Vérification finale...")
    config_manager = CompanyConfigManager()
    
    for company_id in ["MpfnlSbqwaZ6F4HvxQLRL9du0yG3", "XkCn8fjNWEWwqiiKMgJX7OcQrUJ4"]:
        config = await config_manager.get_company_config(company_id)
        if config:
            logger.info(f"✅ Configuration {company_id}: {len(config.get('product_catalog', {}).get('categories', []))} catégories")
        else:
            logger.warning(f"⚠️ Configuration {company_id} non trouvée")
    
    logger.info("🎉 Configuration base de données terminée avec succès!")

if __name__ == "__main__":
    asyncio.run(main())
