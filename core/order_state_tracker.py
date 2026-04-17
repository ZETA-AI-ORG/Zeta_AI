#!/usr/bin/env python3
"""
🎯 ORDER STATE TRACKER - Suivi flexible des données collectées
Permet collecte dans n'importe quel ordre, finalise quand tout est complet
✅ PERSISTANCE SQLite avec auto-nettoyage 7 jours
"""

import logging
import sqlite3
import json
import os
import threading
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# 🔒 AUDIT PRE-PROD: Lock par user_id pour éviter les race conditions SQLite
_user_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()


def _get_user_lock(user_id: str) -> threading.Lock:
    """Retourne un lock dédié à un user_id (créé si inexistant)."""
    with _global_lock:
        if user_id not in _user_locks:
            _user_locks[user_id] = threading.Lock()
        return _user_locks[user_id]

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrderState:
    """État de collecte d'une commande"""
    user_id: str
    produit: Optional[str] = None
    produit_details: Optional[str] = None
    quantite: Optional[str] = None
    paiement: Optional[str] = None
    zone: Optional[str] = None
    numero: Optional[str] = None

    def _is_paiement_valid(self) -> bool:
        try:
            p = str(self.paiement or "").strip()
            if not p:
                return False
            p_up = p.upper()
            # Méthode seule (ex: "WAVE") ne doit pas compter comme paiement.
            if p_up in {"WAVE", "ORANGE", "ORANGE MONEY", "MTN", "MTN MONEY", "MOBILE MONEY"}:
                return False
            # Paiement validé par verdict
            if p_up.startswith("VALIDÉ_") or p_up.startswith("VALIDE_") or p_up.startswith("VALIDE"):
                return True
            # Montant explicite (fallback)
            digits = "".join(ch for ch in p if ch.isdigit())
            if digits:
                try:
                    amt = int(digits)
                except Exception:
                    amt = 0
                return amt >= 2000
            return False
        except Exception:
            return False
    
    def get_missing_fields(self, company_id: Optional[str] = None) -> Set[str]:
        """Retourne les champs manquants.
        
        SPECS est manquant si produit_details est vide.
        NOTE: produit_details ne contient JAMAIS une variante seule (fixé dans CART_SYNC).
        Il contient uniquement des specs réels (ex: 'Pression T1') ou est vide.
        """
        missing = set()
        if not self.produit:
            missing.add("PRODUIT")
        if not str(self.produit_details or "").strip():
            missing.add("SPECS")
        if not self.quantite:
            missing.add("QUANTITÉ")
        if not self._is_paiement_valid():
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
        collected = 6 - len(self.get_missing_fields())
        return collected / 6.0
    
    def to_notepad_format(self) -> str:
        """Convertit en format notepad"""
        parts = []
        if self.produit:
            parts.append(f"✅PRODUIT:{self.produit}")
        if self.produit_details:
            parts.append(f"✅SPECS:{self.produit_details}")
        if self.quantite:
            parts.append(f"✅QUANTITÉ:{self.quantite}")
        if self._is_paiement_valid():
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
        env_db_path = str(os.getenv("ORDER_STATE_DB_PATH") or "").strip()
        if env_db_path:
            db_path = env_db_path
        else:
            # Default for Docker: writable, persistent mount
            db_path = "/data/state/order_states.db"

        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            db_path = "/tmp/order_states.db"
            try:
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        self.db_path = db_path
        self._init_database()
        self._cleanup_old_entries()
        logger.info(f"✅ State Tracker initialisé avec persistance: {db_path}")
    
    def _init_database(self):
        """Initialise la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 🔒 AUDIT PRE-PROD: WAL mode pour meilleure concurrence
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_states (
                user_id TEXT PRIMARY KEY,
                produit TEXT,
                produit_details TEXT,
                quantite TEXT,
                paiement TEXT,
                zone TEXT,
                numero TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_state_meta (
                user_id TEXT PRIMARY KEY,
                turn INTEGER DEFAULT 0,
                ask_counts_json TEXT,
                last_asked_json TEXT,
                slot_meta_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            cursor.execute("PRAGMA table_info(order_states)")
            cols = [str(r[1]) for r in (cursor.fetchall() or [])]
            if "produit_details" not in cols:
                cursor.execute("ALTER TABLE order_states ADD COLUMN produit_details TEXT")
            if "quantite" not in cols:
                cursor.execute("ALTER TABLE order_states ADD COLUMN quantite TEXT")
        except Exception as e:
            logger.debug(f"[ORDER_STATE] Migration colonne produit_details ignorée: {e}")

        conn.commit()
        conn.close()

    def _get_meta(self, user_id: str) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT turn, ask_counts_json, last_asked_json, slot_meta_json
            FROM order_state_meta
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"turn": 0, "ask_counts": {}, "last_asked": {}, "slot_meta": {}}

        try:
            ask_counts = json.loads(row[1]) if row[1] else {}
        except Exception:
            ask_counts = {}
        try:
            last_asked = json.loads(row[2]) if row[2] else {}
        except Exception:
            last_asked = {}
        try:
            slot_meta = json.loads(row[3]) if row[3] else {}
        except Exception:
            slot_meta = {}

        return {
            "turn": int(row[0] or 0),
            "ask_counts": ask_counts if isinstance(ask_counts, dict) else {},
            "last_asked": last_asked if isinstance(last_asked, dict) else {},
            "slot_meta": slot_meta if isinstance(slot_meta, dict) else {},
        }

    def _save_meta(self, user_id: str, meta: Dict) -> None:
        turn = int((meta or {}).get("turn") or 0)
        ask_counts = (meta or {}).get("ask_counts")
        last_asked = (meta or {}).get("last_asked")
        slot_meta = (meta or {}).get("slot_meta")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO order_state_meta
            (user_id, turn, ask_counts_json, last_asked_json, slot_meta_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                turn,
                json.dumps(ask_counts or {}, ensure_ascii=False),
                json.dumps(last_asked or {}, ensure_ascii=False),
                json.dumps(slot_meta or {}, ensure_ascii=False),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def bump_turn(self, user_id: str) -> int:
        meta = self._get_meta(user_id)
        meta["turn"] = int(meta.get("turn") or 0) + 1
        self._save_meta(user_id, meta)
        return int(meta["turn"])

    def record_asked(self, user_id: str, field_name: str, turn: int) -> None:
        f = str(field_name or "").upper().strip()
        if not f:
            return
        meta = self._get_meta(user_id)
        ask_counts = meta.get("ask_counts") if isinstance(meta.get("ask_counts"), dict) else {}
        last_asked = meta.get("last_asked") if isinstance(meta.get("last_asked"), dict) else {}
        ask_counts[f] = int(ask_counts.get(f) or 0) + 1
        last_asked[f] = int(turn or 0)
        meta["ask_counts"] = ask_counts
        meta["last_asked"] = last_asked
        self._save_meta(user_id, meta)

    def get_slot_meta(self, user_id: str) -> Dict:
        meta = self._get_meta(user_id)
        return {
            "turn": int(meta.get("turn") or 0),
            "ask_counts": meta.get("ask_counts") if isinstance(meta.get("ask_counts"), dict) else {},
            "last_asked": meta.get("last_asked") if isinstance(meta.get("last_asked"), dict) else {},
            "slot_meta": meta.get("slot_meta") if isinstance(meta.get("slot_meta"), dict) else {},
        }

    def get_custom_meta(self, user_id: str, key: str, default=None):
        try:
            k = str(key or "").strip()
            if not k:
                return default
            meta = self._get_meta(user_id)
            slot_meta = meta.get("slot_meta") if isinstance(meta.get("slot_meta"), dict) else {}
            custom = slot_meta.get("__custom__") if isinstance(slot_meta.get("__custom__"), dict) else {}
            return custom.get(k, default)
        except Exception:
            return default

    def set_custom_meta(self, user_id: str, key: str, value) -> None:
        try:
            k = str(key or "").strip()
            if not k:
                return
            meta = self._get_meta(user_id)
            slot_meta = meta.get("slot_meta") if isinstance(meta.get("slot_meta"), dict) else {}
            custom = slot_meta.get("__custom__") if isinstance(slot_meta.get("__custom__"), dict) else {}
            custom[k] = value
            slot_meta["__custom__"] = custom
            meta["slot_meta"] = slot_meta
            self._save_meta(user_id, meta)
        except Exception:
            return

    def get_flag(self, user_id: str, flag_name: str) -> bool:
        v = self.get_custom_meta(user_id, f"flag:{flag_name}", default=False)
        return bool(v)

    def set_flag(self, user_id: str, flag_name: str, value: bool) -> None:
        self.set_custom_meta(user_id, f"flag:{flag_name}", bool(value))

    def set_slot_meta(self, user_id: str, field_name: str, *, source: str, confidence: float) -> None:
        f = str(field_name or "").upper().strip()
        if not f:
            return
        meta = self._get_meta(user_id)
        slot_meta = meta.get("slot_meta") if isinstance(meta.get("slot_meta"), dict) else {}
        slot_meta[f] = {
            "source": str(source or "").strip() or "UNKNOWN",
            "confidence": float(confidence) if confidence is not None else None,
            "updated_at": datetime.now().isoformat(),
        }
        meta["slot_meta"] = slot_meta
        self._save_meta(user_id, meta)
    
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

            # Best-effort: nettoyer aussi les metas orphelines
            try:
                cursor.execute("""
                    DELETE FROM order_state_meta
                    WHERE user_id NOT IN (SELECT user_id FROM order_states)
                """)
            except Exception:
                pass

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
            SELECT produit, produit_details, quantite, paiement, zone, numero 
            FROM order_states 
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return OrderState(
                user_id=user_id,
                produit=row[0],
                produit_details=row[1],
                quantite=row[2],
                paiement=row[3],
                zone=row[4],
                numero=row[5]
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
            (user_id, produit, produit_details, quantite, paiement, zone, numero, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.user_id,
            state.produit,
            state.produit_details,
            state.quantite,
            state.paiement,
            state.zone,
            state.numero,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    
    def update_produit(self, user_id: str, produit: str, source: str = "USER_TEXT", confidence: float = 1.0) -> OrderState:
        """Met à jour le produit"""
        with _get_user_lock(user_id):
            state = self.get_state(user_id)
            state.produit = produit
            self._save_state(state)
            self.set_slot_meta(user_id, "PRODUIT", source=source, confidence=confidence)
            logger.info(f"[{user_id}] PRODUIT collecté: {produit}")
            return state

    def update_produit_details(self, user_id: str, produit_details: str, source: str = "USER_TEXT", confidence: float = 1.0) -> OrderState:
        """Met à jour les détails produit (sans valider le champ produit)"""
        with _get_user_lock(user_id):
            state = self.get_state(user_id)
            state.produit_details = produit_details
            self._save_state(state)
            self.set_slot_meta(user_id, "SPECS", source=source, confidence=confidence)
            logger.info(f"[{user_id}] PRODUIT_DETAILS mémorisés: {produit_details}")
            return state

    def update_quantite(self, user_id: str, quantite: str, source: str = "USER_TEXT", confidence: float = 1.0) -> OrderState:
        """Met à jour la quantité"""
        with _get_user_lock(user_id):
            state = self.get_state(user_id)
            state.quantite = quantite
            self._save_state(state)
            self.set_slot_meta(user_id, "QUANTITÉ", source=source, confidence=confidence)
            logger.info(f"[{user_id}] QUANTITÉ collectée: {quantite}")
            return state
    
    def update_paiement(self, user_id: str, paiement: str, source: str = "USER_TEXT", confidence: float = 1.0) -> OrderState:
        """Met à jour le paiement"""
        with _get_user_lock(user_id):
            return self._update_paiement_locked(user_id, paiement, source, confidence)

    def _update_paiement_locked(self, user_id: str, paiement: str, source: str, confidence: float) -> OrderState:
        """Implémentation interne de update_paiement (appelée sous lock)."""
        state = self.get_state(user_id)

        new_p = str(paiement or "").strip()
        old_p = str(state.paiement or "").strip()
        new_up = new_p.upper()
        old_up = old_p.upper()

        # Niveaux / priorités (du plus faible au plus fort)
        # - MÉTHODE: "WAVE" / "ORANGE" / ... (déclaratif)
        # - VERDICT NON-VALIDANT: "INSUFFISANT_XXXF" / "REFUSÉ" (preuve négative)
        # - VERDICT VALIDANT: "VALIDÉ_XXXXF" (preuve positive)
        method_values = {"WAVE", "ORANGE", "ORANGE MONEY", "MTN", "MTN MONEY", "MOOV", "MOBILE MONEY"}

        def _is_method(v_up: str) -> bool:
            return v_up in method_values

        def _is_validated(v_up: str) -> bool:
            return v_up.startswith("VALIDÉ_") or v_up.startswith("VALIDE_") or v_up.startswith("VALIDE")

        def _is_negative_verdict(v_up: str) -> bool:
            return v_up.startswith("INSUFFISANT") or v_up.startswith("REFUS") or v_up.startswith("REJET")

        # Règles de protection :
        # 1) Ne jamais écraser un paiement validé par un état plus faible.
        if _is_validated(old_up) and not _is_validated(new_up):
            logger.info(f"[{user_id}] PAIEMENT inchangé (déjà validé): {old_p}")
            return state

        # 2) Ne jamais écraser un verdict négatif par une simple méthode.
        if _is_negative_verdict(old_up) and _is_method(new_up):
            logger.info(f"[{user_id}] PAIEMENT inchangé (verdict existant): {old_p}")
            return state

        # 3) Si nouvelle valeur vide, ne rien faire.
        if not new_p:
            return state

        state.paiement = new_p
        self._save_state(state)
        self.set_slot_meta(user_id, "PAIEMENT", source=source, confidence=confidence)
        logger.info(f"[{user_id}] PAIEMENT collecté: {new_p}")
        return state
    
    def update_zone(self, user_id: str, zone: str, source: str = "USER_TEXT", confidence: float = 1.0) -> OrderState:
        """Met à jour la zone"""
        with _get_user_lock(user_id):
            state = self.get_state(user_id)
            state.zone = zone
            self._save_state(state)
            self.set_slot_meta(user_id, "ZONE", source=source, confidence=confidence)
            logger.info(f"[{user_id}] ZONE collectée: {zone}")
            return state
    
    def update_numero(self, user_id: str, numero: str, source: str = "USER_TEXT", confidence: float = 1.0) -> OrderState:
        """Met à jour le numéro"""
        with _get_user_lock(user_id):
            state = self.get_state(user_id)
            state.numero = numero
            self._save_state(state)
            self.set_slot_meta(user_id, "NUMÉRO", source=source, confidence=confidence)
            logger.info(f"[{user_id}] NUMÉRO collecté: {numero}")
            return state
    
    def can_finalize(self, user_id: str) -> bool:
        """Vérifie si la commande peut être finalisée"""
        state = self.get_state(user_id)
        return state.is_complete()
    
    def get_next_required_field(self, user_id: str, current_turn: Optional[int] = None, company_id: Optional[str] = None) -> Optional[str]:
        """Retourne le prochain champ requis (ou None si complet)"""
        state = self.get_state(user_id)
        missing = state.get_missing_fields(company_id=company_id)
        
        if not missing:
            return None

        # Si un verdict négatif est présent (paiement insuffisant/refusé),
        # il faut traiter le paiement en priorité (demander le complément / nouvelle preuve)
        # avant de poursuivre la collecte du reste.
        try:
            p_up = str(getattr(state, "paiement", "") or "").strip().upper()
        except Exception:
            p_up = ""

        payment_is_blocking = bool(p_up) and (
            p_up.startswith("INSUFFISANT")
            or p_up.startswith("REFUS")
            or p_up.startswith("REJET")
        )

        if payment_is_blocking:
            priority = ["PAIEMENT", "PRODUIT", "SPECS", "QUANTITÉ", "ZONE", "NUMÉRO"]
        else:
            # Anti-répétition: on alterne la collecte (ex: produit puis quantité)
            # pour éviter de re-demander PRODUIT à chaque tour quand l'utilisateur fournit
            # d'autres infos (zone/téléphone/paiement).
            priority = ["PRODUIT", "QUANTITÉ", "SPECS", "ZONE", "NUMÉRO", "PAIEMENT"]

        slot_meta = self.get_slot_meta(user_id)
        last_asked = slot_meta.get("last_asked") if isinstance(slot_meta.get("last_asked"), dict) else {}
        turn = int(current_turn or slot_meta.get("turn") or 0)

        cooldowns = {
            # Les champs de collecte principaux doivent éviter le bégaiement.
            # Si on vient de poser la question, on laisse 1-2 tours pour que le client réponde.
            "PRODUIT": 2,
            "SPECS": 2,
            "QUANTITÉ": 2,
            "ZONE": 1,
            "NUMÉRO": 2,
            # Paiement: doit pouvoir être redemandé immédiatement quand c'est bloquant.
            "PAIEMENT": 0,
        }

        def _cooldown_active(f: str) -> bool:
            last = int(last_asked.get(f) or 0)
            cd = int(cooldowns.get(f) or 0)
            if cd <= 0:
                return False
            if last <= 0:
                return False
            return (turn - last) < cd

        for field in priority:
            if field in missing and not _cooldown_active(field):
                return field

        for field in priority:
            if field in missing:
                return field

        return list(missing)[0]
    
    def get_minutes_since_last_progress(self, user_id: str) -> float:
        """Retourne le nombre de minutes depuis la dernière mise à jour de l'état (last progress)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT updated_at FROM order_states WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if not row or not row[0]:
                return 0.0
            updated_at = datetime.fromisoformat(str(row[0]))
            delta = datetime.now() - updated_at
            return delta.total_seconds() / 60.0
        except Exception:
            return 0.0

    def get_bot_relance_count(self, user_id: str) -> int:
        """Retourne le nombre de relances bot (max des ask_counts par slot).
        Proxy fiable pour savoir combien de fois le bot a relancé sans progrès."""
        try:
            meta = self._get_meta(user_id)
            ask_counts = meta.get("ask_counts")
            if not isinstance(ask_counts, dict) or not ask_counts:
                return 0
            return max(int(v or 0) for v in ask_counts.values())
        except Exception:
            return 0

    def get_ocr_fail_count(self, user_id: str) -> int:
        """Retourne le nombre d'échecs OCR consécutifs pour cet utilisateur."""
        try:
            v = self.get_custom_meta(user_id, "ocr_fail_count", default=0)
            return int(v or 0)
        except Exception:
            return 0

    def increment_ocr_fail_count(self, user_id: str) -> int:
        """Incrémente le compteur d'échecs OCR et retourne la nouvelle valeur."""
        try:
            current = self.get_ocr_fail_count(user_id)
            new_val = current + 1
            self.set_custom_meta(user_id, "ocr_fail_count", new_val)
            return new_val
        except Exception:
            return 0

    def reset_ocr_fail_count(self, user_id: str) -> None:
        """Remet le compteur d'échecs OCR à 0 (sur succès OCR)."""
        try:
            self.set_custom_meta(user_id, "ocr_fail_count", 0)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════
    # 🚦 BARRIÈRE DE CONVERSION — Compteur de messages par session
    # Protège le marchand contre les "pousseurs de cailloux" (clients
    # qui posent 40 questions sans jamais acheter).
    # Configurable via rag_behavior.max_bot_messages (défaut 15, max 25)
    # ══════════════════════════════════════════════════════════════

    def get_session_msg_count(self, user_id: str) -> int:
        """Retourne le nombre de messages traités dans la session courante."""
        try:
            v = self.get_custom_meta(user_id, "session_msg_count", default=0)
            return int(v or 0)
        except Exception:
            return 0

    def increment_session_msg_count(self, user_id: str) -> int:
        """Incrémente le compteur de session et retourne la nouvelle valeur."""
        try:
            current = self.get_session_msg_count(user_id)
            new_val = current + 1
            self.set_custom_meta(user_id, "session_msg_count", new_val)
            return new_val
        except Exception:
            return 0

    def reset_session_msg_count(self, user_id: str) -> None:
        """Remet le compteur de session à 0 (après commande confirmée ou nouvelle session)."""
        try:
            self.set_custom_meta(user_id, "session_msg_count", 0)
        except Exception:
            pass

    def get_progress_message(self, user_id: str) -> str:
        """Génère un message de progression"""
        state = self.get_state(user_id)
        missing = state.get_missing_fields()
        
        if not missing:
            return "✅ Toutes les informations collectées !"
        
        completion = state.get_completion_rate()
        collected = int(completion * 6)
        
        missing_list = ", ".join(missing)
        return f"📊 {collected}/6 collectées. Manque: {missing_list}"
    
    def finalize_order(self, user_id: str) -> Dict:
        """Finalise la commande et retourne les données"""
        state = self.get_state(user_id)
        
        if not state.is_complete():
            raise ValueError(f"Commande incomplète: {state.get_missing_fields()}")
        
        order_data = {
            "user_id": user_id,
            "produit": state.produit,
            "quantite": state.quantite,
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
        try:
            cursor.execute("DELETE FROM order_state_meta WHERE user_id = ?", (user_id,))
        except Exception:
            pass
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
