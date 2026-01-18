# -*- coding: utf-8 -*-
"""
SUGGESTION LOGGER V6.5 - Logging des cas haute confiance pour review humaine

RÈGLES :
- Log uniquement si similarité >= 0.82
- NE MODIFIE PAS les règles automatiquement
- Format JSONL pour analyse facile
- Inclut prototype matché pour traçabilité
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class SuggestionLoggerV65:
    """
    Log les cas à haute confiance embeddings pour review humaine.
    
    Objectif : Identifier les patterns récurrents à promouvoir en V6/V5 keywords.
    
    IMPORTANT : Pas d'auto-learning, uniquement logging pour décision humaine.
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        if log_dir:
            self.log_file = Path(log_dir) / "embeddings_suggestions_v6_5.jsonl"
        else:
            self.log_file = Path("logs/embeddings_suggestions_v6_5.jsonl")
        
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.suggestion_threshold = 0.82
    
    def log_high_confidence_case(
        self,
        message: str,
        intent: str,
        similarity: float,
        matched_prototype: str,
        v6_checked: bool = True,
        v5_checked: bool = True,
    ) -> bool:
        """
        Log un cas si similarité >= 0.82 (seuil suggestion).
        
        Args:
            message: Message utilisateur original
            intent: Intent détecté par embeddings
            similarity: Score similarité cosine
            matched_prototype: Prototype le plus proche
            v6_checked: True si V6 a été vérifié avant
            v5_checked: True si V5 a été vérifié avant
            
        Returns:
            True si loggé, False sinon
        """
        if similarity < self.suggestion_threshold:
            return False
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "intent": intent,
            "similarity": round(similarity, 4),
            "confidence": round(min(similarity, 0.88), 4),
            "prototype": matched_prototype,
            "status": "pending_review",
            "v6_miss": v6_checked,
            "v5_miss": v5_checked,
            "action_taken": None,
            "reviewed_by": None,
            "reviewed_at": None,
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            logger.info(
                f"[EMBEDDINGS_V6.5][SUGGESTION] Loggé: sim={similarity:.3f} "
                f"intent={intent} msg='{message[:50]}...'"
            )
            return True
            
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5][SUGGESTION] Erreur log: {e}")
            return False
    
    def get_pending_suggestions(self, limit: int = 100) -> list:
        """Récupère les suggestions en attente de review."""
        if not self.log_file.exists():
            return []
        
        pending = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("status") == "pending_review":
                        pending.append(entry)
                        if len(pending) >= limit:
                            break
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur lecture suggestions: {e}")
        
        return pending
    
    def mark_reviewed(
        self,
        message: str,
        action: str,
        reviewer: str = "human"
    ) -> bool:
        """
        Marque une suggestion comme reviewée.
        
        Args:
            message: Message original à retrouver
            action: "approved" (ajouter en V6/V5), "rejected" (ignorer), "deferred"
            reviewer: Identifiant du reviewer
        """
        if not self.log_file.exists():
            return False
        
        updated_lines = []
        found = False
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("message") == message and entry.get("status") == "pending_review":
                        entry["status"] = action
                        entry["action_taken"] = action
                        entry["reviewed_by"] = reviewer
                        entry["reviewed_at"] = datetime.now().isoformat()
                        found = True
                    updated_lines.append(json.dumps(entry, ensure_ascii=False))
            
            if found:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(updated_lines) + '\n')
            
            return found
            
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur update suggestion: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Statistiques des suggestions."""
        if not self.log_file.exists():
            return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
        
        stats = {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "deferred": 0}
        by_intent = {}
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    stats["total"] += 1
                    status = entry.get("status", "pending_review")
                    if status == "pending_review":
                        stats["pending"] += 1
                    elif status == "approved":
                        stats["approved"] += 1
                    elif status == "rejected":
                        stats["rejected"] += 1
                    else:
                        stats["deferred"] += 1
                    
                    intent = entry.get("intent", "UNKNOWN")
                    by_intent[intent] = by_intent.get(intent, 0) + 1
            
            stats["by_intent"] = by_intent
            
        except Exception as e:
            logger.error(f"[EMBEDDINGS_V6.5] Erreur stats: {e}")
        
        return stats
