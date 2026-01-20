#!/usr/bin/env python3
"""
💾 CONVERSATION CHECKPOINT - Sauvegarde centralisée des données
Objectif: Centraliser toutes les données collectées pour traçabilité complète
Architecture: Snapshot complet de l'état de la conversation
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from pathlib import Path
from utils import log3


class ConversationCheckpoint:
    """
    💾 Gestionnaire de checkpoints de conversation
    Sauvegarde l'état complet: thinking, notepad, historique, métriques
    """
    
    def __init__(self, storage_dir: str = "data/checkpoints"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        log3("[CHECKPOINT]", f"💾 Checkpoint manager initialisé: {storage_dir}")
    
    def create_checkpoint(
        self,
        user_id: str,
        company_id: str,
        thinking_data: Optional[Dict[str, Any]] = None,
        notepad_data: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        📸 Créer un checkpoint complet de la conversation
        
        Args:
            user_id: ID utilisateur
            company_id: ID entreprise
            thinking_data: Données du thinking parsé
            notepad_data: État du notepad
            conversation_history: Historique des messages
            metrics: Métriques (confiance, complétude, etc.)
            metadata: Métadonnées additionnelles
            
        Returns:
            checkpoint_id: ID unique du checkpoint
        """
        timestamp = datetime.now()
        checkpoint_id = f"{user_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "user_id": user_id,
            "company_id": company_id,
            "timestamp": timestamp.isoformat(),
            
            # Données collectées
            "thinking": thinking_data or {},
            "notepad": notepad_data or {},
            "conversation_history": conversation_history or [],
            
            # Métriques
            "metrics": metrics or {
                "confiance_score": 0,
                "completude": "0/5",
                "phase_qualification": "decouverte"
            },
            
            # Métadonnées
            "metadata": metadata or {}
        }
        
        # Calculer des statistiques
        checkpoint["statistics"] = self._calculate_statistics(checkpoint)
        
        # ⚡ OPTIMISATION: Sauvegarder en arrière-plan (non-bloquant)
        try:
            from config_performance import ASYNC_CHECKPOINT
            if ASYNC_CHECKPOINT:
                import asyncio
                import threading
                # Lancer la sauvegarde dans un thread séparé pour ne pas bloquer
                thread = threading.Thread(
                    target=self._save_checkpoint,
                    args=(checkpoint_id, checkpoint),
                    daemon=True
                )
                thread.start()
                log3("[CHECKPOINT]", f"⚡ Checkpoint en cours (async): {checkpoint_id}")
            else:
                self._save_checkpoint(checkpoint_id, checkpoint)
                log3("[CHECKPOINT]", f"✅ Checkpoint créé: {checkpoint_id}")
        except ImportError:
            # Fallback si config non disponible
            self._save_checkpoint(checkpoint_id, checkpoint)
            log3("[CHECKPOINT]", f"✅ Checkpoint créé: {checkpoint_id}")
        
        log3("[CHECKPOINT]", f"   📊 Confiance: {checkpoint['metrics'].get('confiance_score', 0)}%")
        log3("[CHECKPOINT]", f"   📊 Complétude: {checkpoint['metrics'].get('completude', '0/5')}")
        
        return checkpoint_id
    
    def _calculate_statistics(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        📊 Calculer des statistiques sur le checkpoint
        
        Args:
            checkpoint: Données du checkpoint
            
        Returns:
            Statistiques calculées
        """
        notepad = checkpoint.get("notepad", {})
        thinking = checkpoint.get("thinking", {})
        history = checkpoint.get("conversation_history", [])
        
        # Compter les champs remplis dans le notepad
        notepad_fields = ["produit", "quantite", "zone", "telephone", "paiement", "frais_livraison"]
        filled_fields = sum(1 for field in notepad_fields if notepad.get(field))
        
        stats = {
            "notepad_completude": f"{filled_fields}/{len(notepad_fields)}",
            "notepad_completude_pct": (filled_fields / len(notepad_fields) * 100) if notepad_fields else 0,
            "conversation_length": len(history),
            "thinking_parsed": bool(thinking.get("success")),
            "deja_collecte_count": len(thinking.get("deja_collecte", {})) if thinking else 0,
            "nouvelles_donnees_count": len(thinking.get("nouvelles_donnees", [])) if thinking else 0
        }
        
        return stats
    
    def _save_checkpoint(self, checkpoint_id: str, checkpoint: Dict[str, Any]):
        """
        💾 Sauvegarder le checkpoint sur disque
        
        Args:
            checkpoint_id: ID du checkpoint
            checkpoint: Données à sauvegarder
        """
        filepath = self.storage_dir / f"{checkpoint_id}.json"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            log3("[CHECKPOINT]", f"💾 Sauvegardé: {filepath}")
        except Exception as e:
            log3("[CHECKPOINT]", f"❌ Erreur sauvegarde: {e}")
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        📂 Charger un checkpoint depuis le disque
        
        Args:
            checkpoint_id: ID du checkpoint
            
        Returns:
            Données du checkpoint ou None
        """
        filepath = self.storage_dir / f"{checkpoint_id}.json"
        
        if not filepath.exists():
            log3("[CHECKPOINT]", f"⚠️ Checkpoint introuvable: {checkpoint_id}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            log3("[CHECKPOINT]", f"✅ Checkpoint chargé: {checkpoint_id}")
            return checkpoint
        except Exception as e:
            log3("[CHECKPOINT]", f"❌ Erreur chargement: {e}")
            return None
    
    def list_checkpoints(
        self,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        📋 Lister les checkpoints disponibles
        
        Args:
            user_id: Filtrer par user_id (optionnel)
            company_id: Filtrer par company_id (optionnel)
            limit: Nombre max de résultats
            
        Returns:
            Liste des checkpoints (métadonnées uniquement)
        """
        checkpoints = []
        
        for filepath in sorted(self.storage_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                
                # Filtrer par user_id si spécifié
                if user_id and checkpoint.get("user_id") != user_id:
                    continue
                
                # Filtrer par company_id si spécifié
                if company_id and checkpoint.get("company_id") != company_id:
                    continue
                
                # Ajouter métadonnées uniquement (pas tout le contenu)
                checkpoints.append({
                    "checkpoint_id": checkpoint["checkpoint_id"],
                    "user_id": checkpoint["user_id"],
                    "company_id": checkpoint["company_id"],
                    "timestamp": checkpoint["timestamp"],
                    "statistics": checkpoint.get("statistics", {}),
                    "metrics": checkpoint.get("metrics", {})
                })
                
                if len(checkpoints) >= limit:
                    break
                    
            except Exception as e:
                log3("[CHECKPOINT]", f"⚠️ Erreur lecture {filepath.name}: {e}")
                continue
        
        log3("[CHECKPOINT]", f"📋 {len(checkpoints)} checkpoints trouvés")
        return checkpoints
    
    def get_latest_checkpoint(
        self,
        user_id: str,
        company_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        🔍 Récupérer le dernier checkpoint d'un utilisateur
        
        Args:
            user_id: ID utilisateur
            company_id: ID entreprise (optionnel)
            
        Returns:
            Dernier checkpoint ou None
        """
        checkpoints = self.list_checkpoints(user_id, company_id, limit=1)
        
        if not checkpoints:
            log3("[CHECKPOINT]", f"⚠️ Aucun checkpoint pour user {user_id}")
            return None
        
        # Charger le checkpoint complet
        return self.load_checkpoint(checkpoints[0]["checkpoint_id"])
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        🗑️ Supprimer un checkpoint
        
        Args:
            checkpoint_id: ID du checkpoint
            
        Returns:
            True si supprimé, False sinon
        """
        filepath = self.storage_dir / f"{checkpoint_id}.json"
        
        if not filepath.exists():
            log3("[CHECKPOINT]", f"⚠️ Checkpoint introuvable: {checkpoint_id}")
            return False
        
        try:
            filepath.unlink()
            log3("[CHECKPOINT]", f"🗑️ Checkpoint supprimé: {checkpoint_id}")
            return True
        except Exception as e:
            log3("[CHECKPOINT]", f"❌ Erreur suppression: {e}")
            return False
    
    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """
        🧹 Nettoyer les checkpoints de plus de X jours
        
        Args:
            days: Nombre de jours à conserver
            
        Returns:
            Nombre de checkpoints supprimés
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for filepath in self.storage_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                
                checkpoint_date = datetime.fromisoformat(checkpoint["timestamp"])
                
                if checkpoint_date < cutoff_date:
                    filepath.unlink()
                    deleted_count += 1
                    
            except Exception as e:
                log3("[CHECKPOINT]", f"⚠️ Erreur nettoyage {filepath.name}: {e}")
                continue
        
        log3("[CHECKPOINT]", f"🧹 {deleted_count} checkpoints supprimés (>{days} jours)")
        return deleted_count


# Instance globale singleton
_checkpoint_manager = None

def get_checkpoint_manager() -> ConversationCheckpoint:
    """🎯 Singleton pour le gestionnaire de checkpoints"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = ConversationCheckpoint()
        log3("[CHECKPOINT]", "🚀 ConversationCheckpoint initialisé")
    return _checkpoint_manager
