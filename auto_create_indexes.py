#!/usr/bin/env python3
"""
🚀 AUTO-CRÉATION DES 5 INDEX COMPLETS AVEC DONNÉES
Intégré directement dans le backend - Opération 100%
"""

import meilisearch
import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Configuration
MEILI_URL = "http://localhost:7700"
MEILI_KEY = "Bac2018mado@2066"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

def create_all_company_indexes(company_id: str) -> Dict[str, bool]:
    """
    Crée automatiquement tous les 5 index avec données complètes
    """
    client = meilisearch.Client(MEILI_URL, MEILI_KEY)
    results = {}
    
    # 1. INDEX PRODUCTS
    try:
        index_name = f"products_{company_id}"
        index = client.index(index_name)
        
        # Créer l'index
        client.create_index(index_name, {"primaryKey": "id"})
        
        # Configuration
        settings = {
            "searchableAttributes": ["name", "description", "color", "category", "subcategory", "product_name"],
            "filterableAttributes": ["company_id", "price", "stock", "category", "subcategory", "color"],
            "sortableAttributes": ["price", "stock"],
        }
        index.update_settings(settings)
        
        # Données produits
        products = [
            {
                "id": "prod_001",
                "company_id": company_id,
                "name": "Samsung Galaxy S24 Ultra",
                "product_name": "Samsung Galaxy S24 Ultra 256GB",
                "description": "Smartphone premium Samsung Galaxy S24 Ultra 256GB. Écran Dynamic AMOLED 6.8 pouces. Appareil photo 200MP zoom 100x. Processeur Snapdragon 8 Gen 3. Batterie 5000mAh charge rapide 45W.",
                "category": "smartphones",
                "subcategory": "android",
                "color": "noir",
                "price": 650000,
                "stock": 25,
                "searchable_text": "samsung galaxy s24 ultra smartphone noir 256gb ecran photo zoom processeur batterie"
            },
            {
                "id": "prod_002", 
                "company_id": company_id,
                "name": "iPhone 15 Pro Max",
                "product_name": "Apple iPhone 15 Pro Max 512GB",
                "description": "Apple iPhone 15 Pro Max 512GB couleur bleu titane. Puce A17 Pro performance exceptionnelle. Appareil photo 48MP ProRAW ProRes. Écran Super Retina XDR 6.7 pouces ProMotion.",
                "category": "smartphones",
                "subcategory": "ios",
                "color": "bleu",
                "price": 950000,
                "stock": 15,
                "searchable_text": "iphone 15 pro max apple bleu titane 512gb puce photo ecran retina"
            },
            {
                "id": "prod_003",
                "company_id": company_id,
                "name": "Casque JBL Tune 760NC",
                "product_name": "JBL Tune 760NC Bluetooth Rouge",
                "description": "Casque audio JBL Tune 760NC bluetooth sans fil réduction bruit active. Couleur rouge vif. Autonomie 35h charge rapide USB-C. Son premium JBL Pure Bass.",
                "category": "audio",
                "subcategory": "casques",
                "color": "rouge",
                "price": 45000,
                "stock": 80,
                "searchable_text": "casque jbl tune bluetooth rouge sans fil bruit autonomie usb son bass"
            }
        ]
        
        task = index.add_documents(products)
        client.wait_for_task(task.task_uid)
        results["products"] = True
        
    except Exception as e:
        print(f"❌ Erreur products: {e}")
        results["products"] = False
    
    # 2. INDEX DELIVERY
    try:
        index_name = f"delivery_{company_id}"
        index = client.index(index_name)
        
        client.create_index(index_name, {"primaryKey": "id"})
        
        settings = {
            "searchableAttributes": ["zone", "price", "delay"],
            "filterableAttributes": ["company_id", "zone"],
        }
        index.update_settings(settings)
        
        delivery_data = [
            {
                "id": "delivery_001",
                "company_id": company_id,
                "zone": "Cocody",
                "price": "Gratuite",
                "delay": "24h",
                "details": "Livraison gratuite Cocody Riviera Golf Angré. Délai 24h ouvrées. Livraison express 2h disponible.",
                "searchable_text": "cocody riviera golf angre livraison gratuite 24h express"
            },
            {
                "id": "delivery_002",
                "company_id": company_id,
                "zone": "Yopougon",
                "price": "1000 FCFA",
                "delay": "24h",
                "details": "Livraison Yopougon Marché Siporex Selmer. Frais 1000 FCFA. Délai 24h ouvrées.",
                "searchable_text": "yopougon marche siporex selmer livraison 1000 fcfa 24h"
            },
            {
                "id": "delivery_003",
                "company_id": company_id,
                "zone": "Banlieue",
                "price": "2000-5000 FCFA",
                "delay": "48h",
                "details": "Livraison banlieue Bingerville Anyama Grand Bassam. Frais 2000-5000 FCFA selon distance. Délai 48h.",
                "searchable_text": "banlieue bingerville anyama grand bassam livraison 2000 5000 fcfa 48h distance"
            }
        ]
        
        task = index.add_documents(delivery_data)
        client.wait_for_task(task.task_uid)
        results["delivery"] = True
        
    except Exception as e:
        print(f"❌ Erreur delivery: {e}")
        results["delivery"] = False
    
    # 3. INDEX SUPPORT_PAIEMENT
    try:
        index_name = f"support_paiement_{company_id}"
        index = client.index(index_name)
        
        client.create_index(index_name, {"primaryKey": "id"})
        
        settings = {
            "searchableAttributes": ["type", "phone", "hours", "method", "details", "store_type", "payment_method", "payment_type"],
            "filterableAttributes": ["company_id", "type", "method", "store_type", "payment_method"],
        }
        index.update_settings(settings)
        
        support_payment_data = [
            {
                "id": "support_001",
                "company_id": company_id,
                "type": "support_technique",
                "method": "whatsapp",
                "phone": "+2250787360757",
                "hours": "8h-18h",
                "details": "Support technique WhatsApp +225 07 87 36 07 57. Assistance installation réparation diagnostic. Horaires lundi-vendredi 8h-18h samedi 9h-15h.",
                "store_type": "technique",
                "searchable_text": "support technique whatsapp assistance installation reparation diagnostic horaires"
            },
            {
                "id": "payment_001",
                "company_id": company_id,
                "type": "paiement",
                "payment_method": "wave_money",
                "payment_type": "mobile_money",
                "details": "Paiement Wave Money sécurisé rapide. Numéro Wave: +225 07 XX XX XX XX. Confirmation instantanée par SMS.",
                "searchable_text": "paiement wave money securise rapide numero confirmation sms"
            },
            {
                "id": "payment_002",
                "company_id": company_id,
                "type": "paiement",
                "payment_method": "cash_on_delivery",
                "payment_type": "especes",
                "details": "Paiement à la livraison COD. Réglez en espèces au livreur. Frais COD: 1000 FCFA. Monnaie rendue si nécessaire.",
                "searchable_text": "paiement livraison cod especes livreur frais 1000 fcfa monnaie"
            },
            {
                "id": "payment_003",
                "company_id": company_id,
                "type": "paiement",
                "payment_method": "carte_bancaire",
                "payment_type": "carte",
                "details": "Paiement carte bancaire Visa Mastercard. Terminal sécurisé magasin. Paiement en ligne site web sécurisé SSL.",
                "searchable_text": "paiement carte bancaire visa mastercard terminal securise magasin ligne ssl"
            }
        ]
        
        task = index.add_documents(support_payment_data)
        client.wait_for_task(task.task_uid)
        results["support_paiement"] = True
        
    except Exception as e:
        print(f"❌ Erreur support_paiement: {e}")
        results["support_paiement"] = False
    
    # 4. INDEX LOCALISATION
    try:
        index_name = f"localisation_{company_id}"
        index = client.index(index_name)
        
        client.create_index(index_name, {"primaryKey": "id"})
        
        settings = {
            "searchableAttributes": ["zone", "address", "store_type", "delivery_zone", "location_type"],
            "filterableAttributes": ["company_id", "zone", "store_type", "location_type"],
        }
        index.update_settings(settings)
        
        location_data = [
            {
                "id": "location_001",
                "company_id": company_id,
                "zone": "Cocody",
                "address": "Riviera Golf près pharmacie du Golf",
                "store_type": "boutique_principale",
                "location_type": "magasin_physique",
                "details": "Boutique principale Cocody Riviera Golf près pharmacie du Golf. Parking gratuit. Essai produits sur place. Conseil personnalisé.",
                "searchable_text": "boutique principale cocody riviera golf pharmacie parking essai conseil personnalise"
            },
            {
                "id": "location_002",
                "company_id": company_id,
                "zone": "Plateau",
                "address": "Centre commercial Playce Palmeraie niveau 2",
                "store_type": "showroom",
                "location_type": "magasin_physique",
                "details": "Showroom Plateau centre commercial Playce Palmeraie niveau 2. Exposition complète gamme produits. Démonstration sur rendez-vous.",
                "searchable_text": "showroom plateau playce palmeraie niveau exposition gamme demonstration rendez-vous"
            },
            {
                "id": "location_003",
                "company_id": company_id,
                "zone": "En ligne",
                "address": "Site web et application mobile",
                "store_type": "boutique_en_ligne",
                "location_type": "e_commerce",
                "details": "Boutique en ligne 24h/7j. Site web sécurisé. Application mobile Android iOS. Commande simple rapide. Chat support temps réel.",
                "searchable_text": "boutique en ligne 24h site web application mobile android ios commande chat support"
            }
        ]
        
        task = index.add_documents(location_data)
        client.wait_for_task(task.task_uid)
        results["localisation"] = True
        
    except Exception as e:
        print(f"❌ Erreur localisation: {e}")
        results["localisation"] = False
    
    # 5. INDEX COMPANY_DOCS
    try:
        index_name = f"company_docs_{company_id}"
        index = client.index(index_name)
        
        client.create_index(index_name, {"primaryKey": "id"})
        
        settings = {
            "searchableAttributes": ["title", "content", "searchable_text", "category"],
            "filterableAttributes": ["company_id", "category", "type"],
        }
        index.update_settings(settings)
        
        company_docs = [
            {
                "id": "doc_001",
                "company_id": company_id,
                "title": "Présentation Entreprise - RueduGrossiste",
                "category": "entreprise",
                "type": "presentation",
                "content": "RueduGrossiste spécialiste vente électronique Abidjan. Smartphones tablettes ordinateurs accessoires. Service client professionnel. Livraison rapide toutes zones. Garantie constructeur. Prix compétitifs. Financement disponible.",
                "searchable_text": "ruedugrossiste specialiste electronique abidjan smartphones tablettes ordinateurs service client livraison garantie prix financement"
            },
            {
                "id": "doc_002",
                "company_id": company_id,
                "title": "Conditions Générales de Vente",
                "category": "juridique",
                "type": "conditions",
                "content": "Conditions générales vente RueduGrossiste. Garantie 2 ans pièces main-d'œuvre. Retour gratuit 7 jours. Échange possible 14 jours. Service après-vente professionnel. Réparation agréée constructeurs.",
                "searchable_text": "conditions generales vente garantie 2 ans pieces main oeuvre retour echange service apres vente reparation agree"
            },
            {
                "id": "doc_003",
                "company_id": company_id,
                "title": "Guide d'Utilisation - Commande en Ligne",
                "category": "aide",
                "type": "guide",
                "content": "Guide commande en ligne RueduGrossiste. Créer compte client. Ajouter panier. Choisir livraison. Sélectionner paiement. Confirmer commande. Suivi temps réel. Notification SMS WhatsApp.",
                "searchable_text": "guide commande en ligne creer compte panier livraison paiement confirmer suivi notification sms whatsapp"
            }
        ]
        
        task = index.add_documents(company_docs)
        client.wait_for_task(task.task_uid)
        results["company_docs"] = True
        
    except Exception as e:
        print(f"❌ Erreur company_docs: {e}")
        results["company_docs"] = False
    
    return results

def main():
    """Exécution automatique complète"""
    print("🚀 AUTO-CRÉATION DES 5 INDEX COMPLETS")
    print("=" * 50)
    
    results = create_all_company_indexes(COMPANY_ID)
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"\n📊 RÉSULTATS: {success_count}/{total_count} index créés")
    
    for index_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {index_name}_{COMPANY_ID}")
    
    if success_count == total_count:
        print(f"\n🎉 SUCCÈS TOTAL! Tous les index sont opérationnels")
        print(f"🔥 Système prêt pour ingestion N8N et analyse HyDE")
    else:
        print(f"\n⚠️ {total_count - success_count} index ont échoué")

if __name__ == "__main__":
    main()
