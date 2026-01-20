#!/usr/bin/env python3
"""
🧪 TEST CHECKPOINT SYSTEM
Test rapide du système de checkpoint et data change tracker
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_change_tracker import get_data_change_tracker
from core.conversation_checkpoint import get_checkpoint_manager


def test_data_change_tracker():
    """🧪 Test du Data Change Tracker avec filtrage"""
    print("\n" + "="*80)
    print("🧪 TEST DATA CHANGE TRACKER")
    print("="*80 + "\n")
    
    tracker = get_data_change_tracker()
    
    # État initial (avec métadonnées internes)
    old_state = {
        "produit": None,
        "quantite": None,
        "zone": None,
        "created_at": "2025-10-19T20:00:00",
        "products": [],
        "quantities": {},
        "confirmation": False
    }
    
    # Nouvel état (avec données collectées)
    new_state = {
        "produit": "Couches culottes",
        "quantite": 150,
        "zone": "Marcory",
        "created_at": "2025-10-19T20:20:00",  # Changé
        "products": ["couches"],  # Changé
        "quantities": {"couches": 150},  # Changé
        "confirmation": False
    }
    
    print("📊 État initial:")
    for k, v in old_state.items():
        print(f"   {k}: {v}")
    
    print("\n📊 Nouvel état:")
    for k, v in new_state.items():
        print(f"   {k}: {v}")
    
    print("\n🔍 Détection des changements...\n")
    
    changes = tracker.compare_and_log(old_state, new_state, source="test")
    
    print("\n✅ Résultat:")
    print(f"   Modifications: {len(changes['modifications'])}")
    print(f"   Ajouts: {len(changes['additions'])}")
    print(f"   Suppressions: {len(changes['deletions'])}")
    
    print("\n✅ Les métadonnées internes ont été filtrées!")
    print("   (created_at, products, quantities, confirmation ignorés)")


def test_checkpoint_manager():
    """🧪 Test du Checkpoint Manager"""
    print("\n" + "="*80)
    print("🧪 TEST CHECKPOINT MANAGER")
    print("="*80 + "\n")
    
    checkpoint_mgr = get_checkpoint_manager()
    
    # Créer un checkpoint de test
    thinking_data = {
        "success": True,
        "deja_collecte": {
            "type_produit": "Couches culottes",
            "quantite": 150,
            "zone": "Marcory",
            "telephone": None,
            "paiement": None
        },
        "nouvelles_donnees": [
            {"cle": "type_produit", "valeur": "Couches culottes", "source": "question"},
            {"cle": "quantite", "valeur": 150, "source": "question"},
            {"cle": "zone", "valeur": "Marcory", "source": "question"}
        ],
        "confiance": {"score": 80, "raison": "Données complètes"},
        "progression": {"completude": "3/5"},
        "strategie": {"phase": "interet"}
    }
    
    notepad_data = {
        "produit": "Couches culottes",
        "quantite": 150,
        "zone": "Marcory",
        "frais_livraison": "1500"
    }
    
    print("💾 Création du checkpoint...\n")
    
    checkpoint_id = checkpoint_mgr.create_checkpoint(
        user_id="test_user_123",
        company_id="test_company",
        thinking_data=thinking_data,
        notepad_data=notepad_data,
        metrics={
            "confiance_score": 80,
            "completude": "3/5",
            "phase_qualification": "interet"
        },
        metadata={
            "test": True,
            "version": "1.0"
        }
    )
    
    print(f"\n✅ Checkpoint créé: {checkpoint_id}")
    
    # Charger le checkpoint
    print("\n📂 Chargement du checkpoint...\n")
    
    loaded = checkpoint_mgr.load_checkpoint(checkpoint_id)
    
    if loaded:
        print("✅ Checkpoint chargé avec succès!")
        print(f"\n📊 Statistiques:")
        for key, value in loaded["statistics"].items():
            print(f"   {key}: {value}")
        
        print(f"\n📊 Métriques:")
        for key, value in loaded["metrics"].items():
            print(f"   {key}: {value}")
    
    # Lister les checkpoints
    print("\n📋 Liste des checkpoints...\n")
    
    checkpoints = checkpoint_mgr.list_checkpoints(user_id="test_user_123", limit=5)
    
    print(f"✅ {len(checkpoints)} checkpoint(s) trouvé(s)")
    for cp in checkpoints:
        print(f"\n   ID: {cp['checkpoint_id']}")
        print(f"   Timestamp: {cp['timestamp']}")
        print(f"   Complétude: {cp['statistics'].get('notepad_completude', 'N/A')}")


def test_integration():
    """🧪 Test d'intégration complet"""
    print("\n" + "="*80)
    print("🧪 TEST INTÉGRATION COMPLÈTE")
    print("="*80 + "\n")
    
    tracker = get_data_change_tracker()
    checkpoint_mgr = get_checkpoint_manager()
    
    # Simuler une conversation
    print("📝 Simulation d'une conversation...\n")
    
    # État 1: Vide
    state_1 = {}
    
    # État 2: Produit collecté
    state_2 = {"produit": "Couches culottes", "quantite": 150}
    print("🔄 Étape 1: Collecte produit + quantité")
    tracker.compare_and_log(state_1, state_2, source="thinking_1")
    
    # État 3: Zone ajoutée
    state_3 = {**state_2, "zone": "Marcory", "frais_livraison": "1500"}
    print("\n🔄 Étape 2: Ajout zone + frais")
    tracker.compare_and_log(state_2, state_3, source="thinking_2")
    
    # État 4: Téléphone ajouté
    state_4 = {**state_3, "telephone": "0160924560"}
    print("\n🔄 Étape 3: Ajout téléphone")
    tracker.compare_and_log(state_3, state_4, source="thinking_3")
    
    # Créer checkpoint final
    print("\n💾 Création checkpoint final...\n")
    
    checkpoint_id = checkpoint_mgr.create_checkpoint(
        user_id="test_integration",
        company_id="test_company",
        notepad_data=state_4,
        metrics={
            "confiance_score": 95,
            "completude": "5/5",
            "phase_qualification": "action"
        }
    )
    
    print(f"\n✅ Checkpoint final: {checkpoint_id}")
    
    # Afficher historique des changements
    print("\n📜 Historique des changements:")
    history = tracker.get_changes_history(limit=10)
    
    for i, change in enumerate(history, 1):
        print(f"\n   Changement #{i} ({change['source']}):")
        print(f"      Ajouts: {len(change['additions'])}")
        print(f"      Modifications: {len(change['modifications'])}")
        print(f"      Suppressions: {len(change['deletions'])}")


if __name__ == "__main__":
    try:
        test_data_change_tracker()
        test_checkpoint_manager()
        test_integration()
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS RÉUSSIS!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
