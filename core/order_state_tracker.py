#!/usr/bin/env python3
"""
🎯 ORDER STATE TRACKER - Suivi flexible des données collectées
Permet collecte dans n'importe quel ordre, finalise quand tout est complet
✅ PERSISTANCE SQLite avec auto-nettoyage 7 jours
"""

import logging
import sqlite3
import json
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrderState:
    """État de collecte d'une commande"""
    user_id: str
    produit: Optional[str] = None
    paiement: Optional[str] = None
    zone: Optional[str] = None
    numero: Optional[str] = None
    
    def get_missing_fields(self) -> Set[str]:
        """Retourne les champs manquants"""
        missing = set()
        if not self.produit:
            missing.add("PRODUIT")
        if not self.paiement:
            missing.add("PAIEMENT")
        if not self.zone:
            missing.add("ZONE")
        if not self.numero:
            missing.add("NUMÉRO")
        return missing
    
    def is_complete(self) -> bool:
        """Vérifie si toutes les données sont collectées"""
        return len(self.get_missing_fields()) == 0
    
    def get_completion_rate(self) -> float:
        """Retourne le taux de complétion (0.0 à 1.0)"""
        collected = 4 - len(self.get_missing_fields())
        return collected / 4.0
    
    def to_notepad_format(self) -> str:
        """Convertit en format notepad"""
        parts = []
        if self.produit:
            parts.append(f"✅PRODUIT:{self.produit}")
        if self.paiement:
            parts.append(f"✅PAIEMENT:{self.paiement}")
        if self.zone:
            parts.append(f"✅ZONE:{self.zone}")
        if self.numero:
            parts.append(f"✅NUMÉRO:{self.numero}")
        return " | ".join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 STATE TRACKER PERSISTANT
# ═══════════════════════════════════════════════════════════════════════════════

class OrderStateTracker:
    """
    Suivi flexible de l'état des commandes avec persistance SQLite
    - Permet collecte dans n'importe quel ordre
    - Auto-nettoyage après 168 heures (7 jours)
    """
    
    def __init__(self, db_path: str = "data/order_states.db"):
        # Créer le dossier data si nécessaire
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_database()
        self._cleanup_old_entries()
        logger.info(f"✅ State Tracker initialisé avec persistance: {db_path}")
    
    def _init_database(self):
        """Initialise la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_states (
                user_id TEXT PRIMARY KEY,
                produit TEXT,
                paiement TEXT,
                zone TEXT,
                numero TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def _cleanup_old_entries(self):
        """Supprime les entrées de plus de 168 heures (7 jours)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(hours=168)
            cursor.execute("""
                DELETE FROM order_states 
                WHERE updated_at < ?
            """, (cutoff.isoformat(),))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted > 0:
                logger.info(f"🗑️ {deleted} commandes expirées supprimées (>7 jours)")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
    
    def get_state(self, user_id: str) -> OrderState:
        """Récupère ou crée l'état pour un utilisateur depuis la DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT produit, paiement, zone, numero 
            FROM order_states 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return OrderState(
                user_id=user_id,
                produit=row[0],
                paiement=row[1],
                zone=row[2],
                numero=row[3]
            )
        else:
            # Créer une nouvelle entrée
            return OrderState(user_id=user_id)
    
    def _save_state(self, state: OrderState):
        """Sauvegarde l'état dans la DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO order_states 
            (user_id, produit, paiement, zone, numero, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            state.user_id,
            state.produit,
            state.paiement,
            state.zone,
            state.numero,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    
    def update_produit(self, user_id: str, produit: str) -> OrderState:
        """Met à jour le produit"""
        state = self.get_state(user_id)
        state.produit = produit
        self._save_state(state)
        logger.info(f"[{user_id}] PRODUIT collecté: {produit}")
        return state
    
    def update_paiement(self, user_id: str, paiement: str) -> OrderState:
        """Met à jour le paiement"""
        state = self.get_state(user_id)
        state.paiement = paiement
        self._save_state(state)
        logger.info(f"[{user_id}] PAIEMENT collecté: {paiement}")
        return state
    
    def update_zone(self, user_id: str, zone: str) -> OrderState:
        """Met à jour la zone"""
        state = self.get_state(user_id)
        state.zone = zone
        self._save_state(state)
        logger.info(f"[{user_id}] ZONE collectée: {zone}")
        return state
    
    def update_numero(self, user_id: str, numero: str) -> OrderState:
        """Met à jour le numéro"""
        state = self.get_state(user_id)
        state.numero = numero
        self._save_state(state)
        logger.info(f"[{user_id}] NUMÉRO collecté: {numero}")
        return state
    
    def can_finalize(self, user_id: str) -> bool:
        """Vérifie si la commande peut être finalisée"""
        state = self.get_state(user_id)
        return state.is_complete()
    
    def get_next_required_field(self, user_id: str) -> Optional[str]:
        """Retourne le prochain champ requis (ou None si complet)"""
        state = self.get_state(user_id)
        missing = state.get_missing_fields()
        
        if not missing:
            return None
        
        # Ordre de priorité suggéré (mais pas obligatoire)
        priority = ["PRODUIT", "PAIEMENT", "ZONE", "NUMÉRO"]
        for field in priority:
            if field in missing:
                return field
        
        return list(missing)[0]
    
    def get_progress_message(self, user_id: str) -> str:
        """Génère un message de progression"""
        state = self.get_state(user_id)
        missing = state.get_missing_fields()
        
        if not missing:
            return "✅ Toutes les informations collectées !"
        
        completion = state.get_completion_rate()
        collected = int(completion * 4)
        
        missing_list = ", ".join(missing)
        return f"📊 {collected}/4 collectées. Manque: {missing_list}"
    
    def finalize_order(self, user_id: str) -> Dict:
        """Finalise la commande et retourne les données"""
        state = self.get_state(user_id)
        
        if not state.is_complete():
            raise ValueError(f"Commande incomplète: {state.get_missing_fields()}")
        
        order_data = {
            "user_id": user_id,
            "produit": state.produit,
            "paiement": state.paiement,
            "zone": state.zone,
            "numero": state.numero,
            "status": "FINALIZED"
        }
        
        logger.info(f"[{user_id}] Commande finalisée: {order_data}")
        
        # Nettoyer l'état après finalisation
        self.clear_state(user_id)
        
        return order_data
    
    def clear_state(self, user_id: str):
        """Efface l'état d'un utilisateur de la DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM order_states WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"[{user_id}] État effacé de la DB")

# ═══════════════════════════════════════════════════════════════════════════════
# 🌍 INSTANCE GLOBALE
# ═══════════════════════════════════════════════════════════════════════════════

# Instance globale partagée
order_tracker = OrderStateTracker()

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_flexible_order():
    """Test de collecte dans ordre non-linéaire"""
    tracker = OrderStateTracker()
    user_id = "test_user"
    
    print("🧪 TEST: Collecte flexible")
    print("="*50)
    
    # Collecte dans ordre non-standard
    print("\n1. Zone d'abord (inhabituel)")
    tracker.update_zone(user_id, "Yopougon-1500F")
    print(tracker.get_progress_message(user_id))
    
    print("\n2. Numéro ensuite")
    tracker.update_numero(user_id, "0709876543")
    print(tracker.get_progress_message(user_id))
    
    print("\n3. Produit")
    tracker.update_produit(user_id, "lingettes[VISION]")
    print(tracker.get_progress_message(user_id))
    
    print("\n4. Paiement (dernier)")
    tracker.update_paiement(user_id, "2020F[TRANSACTIONS]")
    print(tracker.get_progress_message(user_id))
    
    print(f"\n✅ Peut finaliser? {tracker.can_finalize(user_id)}")
    
    if tracker.can_finalize(user_id):
        order = tracker.finalize_order(user_id)
        print(f"\n🎉 Commande finalisée: {order}")

if __name__ == "__main__":
    test_flexible_order()
