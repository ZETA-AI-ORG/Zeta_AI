#!/usr/bin/env python3
"""
🏗️ CRÉATION DES NOUVEAUX INDEX MEILISEARCH
Crée les index support_paiement et localisation pour l'entreprise
"""

import meilisearch
import json
from datetime import datetime

# Configuration
MEILI_URL = "http://localhost:7700"
MEILI_KEY = "Bac2018mado@2066"
COMPANY_ID = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"

def log_creation(message, data=None):
    """Log formaté pour la création"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[CREATE_INDEX][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

def create_support_paiement_index():
    """
    Crée l'index support_paiement avec données d'exemple
    """
    client = meilisearch.Client(MEILI_URL, MEILI_KEY)
    index_name = f"support_paiement_{COMPANY_ID}"
    
    log_creation(f"🏗️ CRÉATION INDEX: {index_name}")
    
    try:
        # Créer l'index
        index = client.index(index_name)
        
        # Documents d'exemple pour support + paiement
        documents = [
            {
                "id": "support_001",
                "title": "Support Technique - Assistance Client",
                "category": "support",
                "content": "Support technique professionnel équipe qualifiée. Assistance installation configuration produits électroniques. Réparation smartphones tablettes ordinateurs portables. Diagnostic gratuit devis transparent. Pièces détachées originales garanties. Intervention domicile entreprise sur rendez-vous. Horaires: lundi vendredi 8h-18h samedi 9h-15h. Contact: WhatsApp +225 07 XX XX XX XX email support@entreprise.ci. Formation utilisation produits incluse achat. Garantie étendue disponible tous produits.",
                "searchable_text": "support technique assistance client réparation diagnostic intervention domicile whatsapp email formation garantie",
                "type": "support_info"
            },
            {
                "id": "paiement_001", 
                "title": "Moyens de Paiement - Toutes Options",
                "category": "paiement",
                "content": "Paiement sécurisé multiple options. Mobile Money: Wave Money Moov Money Orange Money MTN Mobile Money. Virement bancaire: UBA Ecobank SGCI BICICI Coris Bank. Paiement comptant magasin espèces. Carte bancaire Visa Mastercard terminal sécurisé. Financement crédit: Advans Microcred Orabank partenaires. Paiement échelonné 3 6 12 mois sans frais. Facture électronique envoyée email WhatsApp. Support paiement 24h/7j assistance technique.",
                "searchable_text": "paiement wave money moov orange mtn mobile money virement bancaire visa mastercard financement crédit échelonné facture",
                "type": "payment_info"
            },
            {
                "id": "paiement_002",
                "title": "Paiement à la Livraison - Cash on Delivery",
                "category": "paiement",
                "content": "Paiement à la livraison COD cash on delivery disponible. Réglez votre commande directement au livreur en espèces. Service sécurisé et pratique. Frais COD: 1000 FCFA supplémentaires. Disponible toutes zones Abidjan et banlieue. Monnaie rendue si nécessaire. Reçu de paiement fourni. Retour gratuit si produit non conforme. Vérification produit avant paiement autorisée.",
                "searchable_text": "paiement livraison cod cash delivery espèces livreur frais reçu retour vérification",
                "type": "payment_delivery"
            }
        ]
        
        # Ajouter les documents
        task = index.add_documents(documents)
        client.wait_for_task(task.task_uid)
        
        log_creation(f"✅ INDEX CRÉÉ: {index_name}", {
            "documents_ajoutés": len(documents)
        })
        
        return True
        
    except Exception as e:
        log_creation(f"❌ ERREUR CRÉATION {index_name}: {e}")
        return False

def create_localisation_index():
    """
    Crée l'index localisation avec infos géographiques
    """
    client = meilisearch.Client(MEILI_URL, MEILI_KEY)
    index_name = f"localisation_{COMPANY_ID}"
    
    log_creation(f"🏗️ CRÉATION INDEX: {index_name}")
    
    try:
        # Créer l'index
        index = client.index(index_name)
        
        # Documents d'exemple pour localisation
        documents = [
            {
                "id": "location_001",
                "title": "Magasins Physiques - Emplacements",
                "category": "magasin_physique",
                "content": "Magasins physiques Abidjan. Boutique principale Cocody Riviera Golf près pharmacie du Golf. Showroom Plateau centre commercial Playce Palmeraie niveau 2. Point de vente Yopougon Marché Siporex face station Total. Magasin Marcory Zone 4 carrefour Génie 2000. Horaires: lundi samedi 9h-19h dimanche 10h-16h. Parking gratuit disponible. Essai produits sur place. Conseil personnalisé vendeurs qualifiés.",
                "searchable_text": "magasin physique boutique cocody plateau yopougon marcory riviera golf playce siporex génie parking essai conseil",
                "type": "physical_store"
            },
            {
                "id": "location_002",
                "title": "Zones de Livraison - Couverture Géographique", 
                "category": "livraison_zones",
                "content": "Zones livraison Abidjan et banlieue. Livraison gratuite: Cocody Plateau Yopougon Marcory Treichville Adjamé Koumassi Abobo Riviera Golf Angré Port-Bouët. Banlieue payante: Bingerville Anyama Songon Grand Bassam Dabou Bonoua Alépé. Délais: 24h Abidjan 48h banlieue. Livraison express 2h zones centrales. Frais banlieue: 2000-5000 FCFA selon distance. Suivi temps réel WhatsApp SMS.",
                "searchable_text": "livraison zones abidjan cocody plateau yopougon marcory bingerville anyama songon bassam délais express frais suivi",
                "type": "delivery_zones"
            },
            {
                "id": "location_003",
                "title": "Boutique en Ligne - E-commerce",
                "category": "boutique_en_ligne", 
                "content": "Boutique en ligne 24h/7j. Site web sécurisé catalogue complet. Application mobile Android iOS téléchargement gratuit. Commande en ligne simple rapide. Panier sauvegardé compte client. Notifications promotions exclusives. Chat support temps réel. Comparateur produits avis clients. Wishlist favoris recommandations personnalisées. Interface multilingue français anglais.",
                "searchable_text": "boutique en ligne site web application mobile android ios commande panier compte chat support comparateur wishlist interface",
                "type": "online_store"
            }
        ]
        
        # Ajouter les documents
        task = index.add_documents(documents)
        client.wait_for_task(task.task_uid)
        
        log_creation(f"✅ INDEX CRÉÉ: {index_name}", {
            "documents_ajoutés": len(documents)
        })
        
        return True
        
    except Exception as e:
        log_creation(f"❌ ERREUR CRÉATION {index_name}: {e}")
        return False

def main():
    """
    Fonction principale de création des index
    """
    print("🏗️ CRÉATION DES NOUVEAUX INDEX MEILISEARCH")
    print("=" * 60)
    
    success_count = 0
    
    # Créer l'index support_paiement
    if create_support_paiement_index():
        success_count += 1
    
    # Créer l'index localisation  
    if create_localisation_index():
        success_count += 1
    
    print(f"\n🎉 RÉSULTAT: {success_count}/2 index créés avec succès")
    
    if success_count == 2:
        print("✅ Tous les nouveaux index sont prêts!")
        print("📋 Index disponibles:")
        print(f"  - support_paiement_{COMPANY_ID}")
        print(f"  - localisation_{COMPANY_ID}")
    else:
        print("⚠️ Certains index n'ont pas pu être créés")

if __name__ == "__main__":
    main()
