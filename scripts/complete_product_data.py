#!/usr/bin/env python3
"""
Script pour compléter les données produits manquantes dans MeiliSearch
Ajoute des produits de test complets pour améliorer les scores de recherche
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.meili_client import MeiliClient
from utils import log3

class ProductDataCompleter:
    def __init__(self):
        self.meili_client = MeiliClient()
        
    async def add_complete_product_data(self, company_id: str = "RUE_DU_GROS"):
        """Ajoute des données produits complètes pour améliorer les scores"""
        
        # Données produits complètes avec tous les champs
        complete_products = [
            {
                "id": "casque_moto_integral_001",
                "searchable_text": "Casque moto intégral noir mat taille M L XL protection maximale homologué ECE sécurité route circuit sport touring",
                "product_name": "CASQUE MOTO INTÉGRAL NOIR MAT",
                "category": "Auto & Moto",
                "subcategory": "Casques",
                "price": 6500,
                "currency": "FCFA",
                "stock": 15,
                "availability": "En stock",
                "color": "Noir mat",
                "size": "M, L, XL",
                "brand": "SHARK",
                "model": "RSI",
                "features": ["Homologué ECE", "Visière anti-buée", "Ventilation", "Doublure amovible"],
                "description": "Casque moto intégral haute protection avec visière claire, système de ventilation optimisé et doublure lavable. Homologué ECE 22.05 pour une sécurité maximale.",
                "weight": "1.4kg",
                "material": "Polycarbonate",
                "company_id": company_id,
                "index_name": "products",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "casque_moto_jet_002", 
                "searchable_text": "Casque moto jet ouvert blanc brillant taille S M L vintage rétro scooter urbain léger confortable",
                "product_name": "CASQUE MOTO JET BLANC BRILLANT",
                "category": "Auto & Moto",
                "subcategory": "Casques",
                "price": 4500,
                "currency": "FCFA", 
                "stock": 8,
                "availability": "En stock",
                "color": "Blanc brillant",
                "size": "S, M, L",
                "brand": "BELL",
                "model": "Custom 500",
                "features": ["Style vintage", "Léger", "Confortable", "Homologué"],
                "description": "Casque jet style vintage pour scooter et moto urbaine. Design rétro avec finition brillante et confort optimal.",
                "weight": "1.1kg",
                "material": "Fibre de verre",
                "company_id": company_id,
                "index_name": "products",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "gants_moto_cuir_003",
                "searchable_text": "Gants moto cuir noir protection articulations CE homologués touring sport route hiver été respirant",
                "product_name": "GANTS MOTO CUIR PROTECTION CE",
                "category": "Auto & Moto", 
                "subcategory": "Gants",
                "price": 2800,
                "currency": "FCFA",
                "stock": 12,
                "availability": "En stock",
                "color": "Noir",
                "size": "S, M, L, XL",
                "brand": "ALPINESTARS",
                "model": "SMX-1 Air",
                "features": ["Protection CE", "Cuir véritable", "Respirant", "Tactile"],
                "description": "Gants moto en cuir avec protections CE aux articulations. Compatible écran tactile avec ventilation pour le confort.",
                "weight": "0.3kg",
                "material": "Cuir + Textile",
                "company_id": company_id,
                "index_name": "products", 
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "blouson_moto_textile_004",
                "searchable_text": "Blouson moto textile noir imperméable protections CE touring adventure route hiver doublure thermique",
                "product_name": "BLOUSON MOTO TEXTILE IMPERMÉABLE",
                "category": "Auto & Moto",
                "subcategory": "Vêtements",
                "price": 12500,
                "currency": "FCFA",
                "stock": 6,
                "availability": "En stock",
                "color": "Noir",
                "size": "M, L, XL, XXL", 
                "brand": "DAINESE",
                "model": "Tempest 2",
                "features": ["Imperméable", "Protections CE", "Doublure thermique", "Ventilation"],
                "description": "Blouson moto textile 3 saisons avec membrane imperméable et protections CE. Doublure thermique amovible.",
                "weight": "1.8kg",
                "material": "Textile technique",
                "company_id": company_id,
                "index_name": "products",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "bottes_moto_cuir_005",
                "searchable_text": "Bottes moto cuir noir protection cheville CE touring sport route imperméable semelle antidérapante",
                "product_name": "BOTTES MOTO CUIR PROTECTION CE",
                "category": "Auto & Moto",
                "subcategory": "Chaussures",
                "price": 8900,
                "currency": "FCFA",
                "stock": 10,
                "availability": "En stock",
                "color": "Noir",
                "size": "39, 40, 41, 42, 43, 44, 45",
                "brand": "TCX",
                "model": "Street Ace",
                "features": ["Protection CE", "Imperméable", "Antidérapant", "Respirant"],
                "description": "Bottes moto en cuir avec protection cheville CE. Membrane imperméable et semelle antidérapante haute adhérence.",
                "weight": "1.2kg",
                "material": "Cuir pleine fleur",
                "company_id": company_id,
                "index_name": "products",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        try:
            # Ingestion dans MeiliSearch
            log3("[PRODUCT_DATA]", f"Ajout de {len(complete_products)} produits complets")
            
            result = await self.meili_client.add_documents(
                index_name="products",
                documents=complete_products
            )
            
            log3("[PRODUCT_DATA]", f"✅ Ingestion réussie: {result}")
            
            # Vérification des données ajoutées
            search_result = await self.meili_client.search(
                index_name="products", 
                query="casque moto",
                limit=3
            )
            
            log3("[PRODUCT_DATA]", f"✅ Vérification: {len(search_result.get('hits', []))} produits trouvés")
            
            return {
                "success": True,
                "products_added": len(complete_products),
                "verification_results": len(search_result.get('hits', []))
            }
            
        except Exception as e:
            log3("[PRODUCT_DATA]", f"❌ Erreur: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

async def main():
    """Point d'entrée principal"""
    completer = ProductDataCompleter()
    
    print("🚀 Démarrage de la complétion des données produits...")
    
    result = await completer.add_complete_product_data()
    
    if result["success"]:
        print(f"✅ SUCCÈS: {result['products_added']} produits ajoutés")
        print(f"✅ VÉRIFICATION: {result['verification_results']} produits trouvés")
        print("🎯 Données produits complétées avec succès!")
    else:
        print(f"❌ ÉCHEC: {result['error']}")
        
if __name__ == "__main__":
    asyncio.run(main())
