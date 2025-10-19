#!/usr/bin/env python3
"""
🔄 DATA CHANGE TRACKER - Suivi des modifications de données
Objectif: Logger clairement tous les changements de données collectées
Architecture: Comparaison avant/après + logs détaillés
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from utils import log3


class DataChangeTracker:
    """
    🔄 Tracker des changements de données collectées
    Compare l'état avant/après et log les modifications
    """
    
    # Métadonnées internes à ignorer dans les logs
    INTERNAL_METADATA = {
        'created_at', 'last_updated', 'conversation_count',
        'products', 'quantities', 'calculated_totals',
        'confirmation'  # Métadonnée technique
    }
    
    def __init__(self):
        self.changes_history: List[Dict[str, Any]] = []
        self.current_state: Dict[str, Any] = {}
    
    def compare_and_log(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        source: str = "unknown"
    ) -> Dict[str, Any]:
        """
        🔍 Compare deux états et log les changements
        
        Args:
            old_data: Données avant
            new_data: Données après
            source: Source du changement (thinking, regex, notepad, etc.)
            
        Returns:
            Dict des changements détectés
        """
        changes = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "modifications": [],
            "additions": [],
            "deletions": []
        }
        
        # Détecter les modifications et additions
        for key, new_value in new_data.items():
            # Ignorer les métadonnées internes
            if key in self.INTERNAL_METADATA:
                continue
                
            old_value = old_data.get(key)
            
            if old_value is None and new_value is not None:
                # Nouvelle donnée ajoutée
                changes["additions"].append({
                    "field": key,
                    "value": new_value
                })
                log3("[DATA_CHANGE]", f"➕ AJOUT: {key} = {new_value} (source: {source})")
                
            elif old_value != new_value and new_value is not None:
                # Donnée modifiée (ÉCRASEMENT)
                changes["modifications"].append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
                log3("[DATA_CHANGE]", f"🔄 MODIF: {key} = {old_value} → {new_value} (source: {source})")
        
        # Détecter les suppressions
        for key, old_value in old_data.items():
            # Ignorer les métadonnées internes
            if key in self.INTERNAL_METADATA:
                continue
                
            if key not in new_data and old_value is not None:
                changes["deletions"].append({
                    "field": key,
                    "old_value": old_value
                })
                log3("[DATA_CHANGE]", f"➖ SUPPRESSION: {key} = {old_value} (source: {source})")
        
        # Sauvegarder dans l'historique
        if changes["modifications"] or changes["additions"] or changes["deletions"]:
            self.changes_history.append(changes)
            self._log_summary(changes)
        else:
            log3("[DATA_CHANGE]", f"✅ Aucun changement détecté (source: {source})")
        
        return changes
    
    def _log_summary(self, changes: Dict[str, Any]):
        """📊 Log un résumé des changements"""
        total = (
            len(changes["modifications"]) +
            len(changes["additions"]) +
            len(changes["deletions"])
        )
        
        log3("[DATA_CHANGE]", f"📊 RÉSUMÉ: {total} changements détectés")
        log3("[DATA_CHANGE]", f"   ├─ Modifications: {len(changes['modifications'])}")
        log3("[DATA_CHANGE]", f"   ├─ Ajouts: {len(changes['additions'])}")
        log3("[DATA_CHANGE]", f"   └─ Suppressions: {len(changes['deletions'])}")
    
    def track_thinking_changes(
        self,
        thinking_data: Dict[str, Any],
        current_notepad: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🧠 Track les changements depuis le thinking parsé
        
        Args:
            thinking_data: Données extraites du <thinking>
            current_notepad: État actuel du notepad
            
        Returns:
            Nouvelles données à appliquer
        """
        log3("[DATA_CHANGE]", "🧠 Analyse changements depuis <thinking>...")
        
        # Extraire deja_collecte du thinking
        deja_collecte = thinking_data.get("deja_collecte", {})
        
        # Convertir en format notepad
        new_data = {}
        
        if deja_collecte.get("type_produit"):
            new_data["produit"] = deja_collecte["type_produit"]
        
        if deja_collecte.get("quantite"):
            new_data["quantite"] = deja_collecte["quantite"]
        
        if deja_collecte.get("zone"):
            new_data["zone"] = deja_collecte["zone"]
        
        if deja_collecte.get("telephone"):
            new_data["telephone"] = deja_collecte["telephone"]
        
        if deja_collecte.get("paiement"):
            new_data["paiement"] = deja_collecte["paiement"]
        
        # Comparer avec l'état actuel
        changes = self.compare_and_log(current_notepad, new_data, source="thinking_yaml")
        
        return new_data
    
    def track_regex_changes(
        self,
        regex_data: Dict[str, Any],
        current_notepad: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🔍 Track les changements depuis les regex (livraison, etc.)
        
        Args:
            regex_data: Données extraites par regex
            current_notepad: État actuel du notepad
            
        Returns:
            Nouvelles données à appliquer
        """
        log3("[DATA_CHANGE]", "🔍 Analyse changements depuis regex...")
        
        changes = self.compare_and_log(current_notepad, regex_data, source="regex_extraction")
        
        return regex_data
    
    def get_changes_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        📜 Récupère l'historique des changements
        
        Args:
            limit: Nombre max de changements à retourner
            
        Returns:
            Liste des derniers changements
        """
        return self.changes_history[-limit:]
    
    def log_current_state(self, state: Dict[str, Any], label: str = "État actuel"):
        """
        📊 Log l'état complet des données collectées
        
        Args:
            state: État à logger
            label: Label pour le log
        """
        log3("[DATA_STATE]", f"📊 {label}:")
        
        for key, value in state.items():
            if value is not None:
                log3("[DATA_STATE]", f"   ✅ {key}: {value}")
            else:
                log3("[DATA_STATE]", f"   ⚠️ {key}: NON COLLECTÉ")
        
        # Calculer complétude
        total_fields = len(state)
        filled_fields = sum(1 for v in state.values() if v is not None)
        completude = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        log3("[DATA_STATE]", f"📊 Complétude: {filled_fields}/{total_fields} ({completude:.0f}%)")
    
    def merge_sources(
        self,
        thinking_data: Dict[str, Any],
        regex_data: Dict[str, Any],
        notepad_data: Dict[str, Any],
        priority: str = "thinking"
    ) -> Dict[str, Any]:
        """
        🔀 Fusionne les données de plusieurs sources avec priorité
        
        Args:
            thinking_data: Données du thinking YAML
            regex_data: Données des regex
            notepad_data: Données du notepad
            priority: Source prioritaire ("thinking", "regex", "notepad")
            
        Returns:
            Données fusionnées
        """
        log3("[DATA_MERGE]", f"🔀 Fusion des sources (priorité: {priority})...")
        
        # Définir l'ordre de priorité
        if priority == "thinking":
            sources = [thinking_data, regex_data, notepad_data]
            labels = ["thinking", "regex", "notepad"]
        elif priority == "regex":
            sources = [regex_data, thinking_data, notepad_data]
            labels = ["regex", "thinking", "notepad"]
        else:  # notepad
            sources = [notepad_data, thinking_data, regex_data]
            labels = ["notepad", "thinking", "regex"]
        
        # Fusionner avec priorité
        merged = {}
        source_map = {}  # Pour tracker d'où vient chaque donnée
        
        for source, label in zip(sources, labels):
            for key, value in source.items():
                if value is not None and key not in merged:
                    merged[key] = value
                    source_map[key] = label
        
        # Logger la source de chaque donnée
        log3("[DATA_MERGE]", "📋 Sources des données fusionnées:")
        for key, value in merged.items():
            source = source_map.get(key, "unknown")
            log3("[DATA_MERGE]", f"   {key}: {value} (source: {source})")
        
        return merged
    
    def clear_history(self):
        """🧹 Nettoie l'historique des changements"""
        count = len(self.changes_history)
        self.changes_history.clear()
        log3("[DATA_CHANGE]", f"🧹 Historique nettoyé: {count} entrées supprimées")


# Instance globale singleton
_data_change_tracker = None

def get_data_change_tracker() -> DataChangeTracker:
    """🎯 Singleton pour le tracker de changements"""
    global _data_change_tracker
    if _data_change_tracker is None:
        _data_change_tracker = DataChangeTracker()
        log3("[DATA_CHANGE]", "🚀 DataChangeTracker initialisé")
    return _data_change_tracker
