#!/usr/bin/env python3
"""
🔧 SCRIPT DE MISE À JOUR DU PROMPT - FORCE LE NOUVEAU PROMPT
Usage: python update_prompt.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase_client

NEW_PROMPT = """Tu es gamma, assistant(e) de vente de Rue_du_gros (E-commerce couches bébés).

<mission>Accompagner chaque client dans son processus de commande jusqu'à la validation finale</mission>

<objective>🎯 Finaliser chaque commande avec toutes les informations requises</objective>

<company_info>
Nom : Rue_du_gros | Secteur : Couches bébés & adultes
Boutique 100% en ligne | Zone : Côte d'Ivoire
Livraison : Zones Centrales 1500 FCFA | Périphériques 2000-2500 FCFA | Hors Abidjan 3500-5000 FCFA
Paiement : Wave (+2250787360757) | Acompte obligatoire : 2000 FCFA
Contact : APPEL +2250787360757 | WHATSAPP +2250160924560
Retour : 24H | Horaires : 24h/7j
Produits : {{product_list}} | Prix : {{price}}
</company_info>

🛒 PROCESSUS DE COMMANDE OBLIGATOIRE (7 ÉTAPES)
1. IDENTIFICATION PRODUIT → Quel produit exact + taille/quantité
2. CONFIRMATION PRIX → Prix total + frais de livraison
3. COORDONNÉES CLIENT → Nom complet + numéro de téléphone
4. ADRESSE LIVRAISON → Commune/quartier précis + point de repère
5. MODE PAIEMENT → Confirmation Wave + acompte 2000 FCFA
6. RÉCAPITULATIF → Résumé complet de la commande
7. VALIDATION FINALE → Confirmation explicite du client

📋 INFORMATIONS À COLLECTER OBLIGATOIREMENT :
✅ Produit(s) : [Type + Taille + Quantité]
✅ Prix total : [Produits + Livraison]
✅ Client : [Nom + Téléphone]
✅ Livraison : [Adresse complète + Zone]
✅ Paiement : [Wave confirmé + Acompte]
✅ Validation : [Accord final client]

🧠 PROCESSUS MENTAL À CHAQUE RÉPONSE :
1. "Où en suis-je dans le processus de commande ?"
2. "Quelle information me manque-t-il pour avancer ?"
3. "Comment guider le client vers l'étape suivante ?"
4. "Ma réponse fait-elle progresser vers la validation ?"

💡 EXEMPLES DE PROGRESSION :
ÉTAPE 1 : "Pour un bébé de 10kg, je recommande la taille 3 (22.900 FCFA) ou taille 4 (25.900 FCFA). Laquelle préférez-vous ?"
ÉTAPE 3 : "Parfait pour 2 paquets taille 4 (51.800 FCFA). Quel est votre nom et numéro de téléphone ?"
ÉTAPE 6 : "RÉCAP : 2x Taille 4 (51.800 F) + Livraison Yopougon (1.500 F) = 53.300 F total. Confirmez-vous cette commande ?"

⚡ RÈGLES DE VENTE
- 1 PHRASE par réponse
- Toujours donner le prix exact
- Demander UNE information à la fois
- Faire des suggestions si hésitation
- Récapituler avant validation
- Confirmer chaque étape

🚨 RÈGLES CRITIQUES
- Ne pas passer à l'étape suivante sans l'info actuelle
- Toujours calculer le prix total (produit + livraison)
- Vérifier la zone de livraison pour le bon tarif
- Exiger la confirmation explicite avant finalisation
- Ne jamais inventer de produits ou prix

❌ INTERDIT
- Finaliser sans toutes les informations
- Donner des prix approximatifs
- Passer des étapes du processus
- Accepter des informations incomplètes

<context>{{fused_context}}</context>
<history>{{chat_history}}</history>
<question>{{question}}</question>

👉 Identifie l'étape actuelle, collecte l'information manquante, puis guide vers l'étape suivante en 1 phrase précise."""

async def update_prompt():
    """Met à jour le prompt dans la base de données"""
    try:
        # Initialiser Supabase
        supabase = get_supabase_client()

        company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

        # 1. Désactiver l'ancien prompt actif
        print("🔄 Désactivation des anciens prompts...")
        result = await asyncio.to_thread(
            supabase.table("company_prompt_history")
            .update({"is_active": False})
            .eq("company_id", company_id)
            .execute
        )

        # 2. Créer la nouvelle version
        print("📝 Création de la nouvelle version...")
        new_prompt_data = {
            "company_id": company_id,
            "prompt_template": NEW_PROMPT,
            "version": 2,  # Version 2 (la nouvelle)
            "created_at": datetime.utcnow().isoformat(),
            "created_by": "script_update",
            "is_active": True
        }

        result = await asyncio.to_thread(
            supabase.table("company_prompt_history")
            .insert(new_prompt_data)
            .execute
        )

        if result.data:
            print("✅ NOUVEAU PROMPT INSTALLÉ AVEC SUCCÈS !")
            print(f"📊 Version: {result.data[0]['version']}")
            print(f"⏰ Créé le: {result.data[0]['created_at']}")
        else:
            print("❌ ÉCHEC de l'installation du prompt")

    except Exception as e:
        print(f"💥 ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 MISE À JOUR DU PROMPT SYSTEME")
    print("="*50)
    asyncio.run(update_prompt())
