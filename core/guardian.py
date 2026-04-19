"""
🛡️ GUARDIAN - ZETA AI V2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rôle : porte d'entrée de sécurité du botlive.

Vérifications (dans l'ordre) :
1. Statut d'abonnement (Découverte / Starter / Pro / Elite) — expiration temporelle
2. Quota d'utilisation — current_usage vs usage_limit
3. Session Limiter — nombre de messages par client WhatsApp par fenêtre

Si KO → short-circuit de la boucle botlive (pas d'appel LLM facturé),
avec réponse humanisée via message_registry.

Intégration : appelé en tête de BotliveRAGHybrid.process_request().
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

try:
    from .message_registry import get_system_response, get_company_tone
except Exception:
    def get_system_response(category: str, tone: str = "formal", **kwargs) -> str:
        return "Une erreur est survenue, veuillez réessayer plus tard."
    def get_company_tone(company_id=None) -> str:
        return "formal"

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ Configuration (surchargeable via env)
# ═══════════════════════════════════════════════════════════════════════════════

# Session limiter par client WhatsApp (par fenêtre)
GUARDIAN_SESSION_WINDOW_MIN = int(os.getenv("GUARDIAN_SESSION_WINDOW_MIN", "60"))
GUARDIAN_SESSION_MAX_DISCOVERY = int(os.getenv("GUARDIAN_SESSION_MAX_DISCOVERY", "10"))
GUARDIAN_SESSION_MAX_STARTER = int(os.getenv("GUARDIAN_SESSION_MAX_STARTER", "15"))
GUARDIAN_SESSION_MAX_PRO = int(os.getenv("GUARDIAN_SESSION_MAX_PRO", "25"))
GUARDIAN_SESSION_MAX_ELITE = int(os.getenv("GUARDIAN_SESSION_MAX_ELITE", "25"))

# Flag global d'activation (permet de désactiver en cas de bug sans rollback)
GUARDIAN_ENABLED = os.getenv("GUARDIAN_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 Dataclass résultat
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GuardianVerdict:
    """Verdict du Guardian — consommé par botlive_rag_hybrid."""
    allowed: bool
    reason: str                # "OK" | "ABONNEMENT_EXPIRE" | "QUOTA_EPUISE" | "SESSION_LIMIT" | "ERROR"
    message: str               # message à renvoyer au client si allowed=False
    metadata: Dict[str, Any]   # debug (plan, dates, usage)


# ═══════════════════════════════════════════════════════════════════════════════
# 🗓️ Helpers date (ISO 8601 tolérant)
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_iso(value: Any) -> Optional[datetime]:
    """Parse un champ ISO (Supabase PostgREST), aware UTC. Retourne None si invalide."""
    if not value:
        return None
    s = str(value).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ GUARDIAN (stateless, safe-by-default)
# ═══════════════════════════════════════════════════════════════════════════════

class Guardian:
    """Porte d'entrée sécurité du botlive — vérifications en cascade."""

    def __init__(self, session_store: Optional[Any] = None):
        """
        Args:
            session_store: store optionnel pour le session limiter. Doit exposer :
                           - count_recent_messages(user_id, window_min) -> int
                           Si None, le session limiter est désactivé.
        """
        self.session_store = session_store

    # ───────────────────────────────────────────────────────────────────────────
    # Entrée principale
    # ───────────────────────────────────────────────────────────────────────────

    def check_access(
        self,
        *,
        company_info: Dict[str, Any],
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> GuardianVerdict:
        """
        Exécute les 3 vérifications dans l'ordre : expiration → quota → session.

        Retourne un GuardianVerdict. Si allowed=False, le message est déjà prêt
        à être renvoyé au client (humanisé via message_registry).
        """
        if not GUARDIAN_ENABLED:
            return GuardianVerdict(True, "DISABLED", "", {"guardian": "disabled"})

        info = company_info or {}
        plan = str(info.get("plan_name") or "starter").strip().lower()
        subscription = info.get("subscription") or {}
        tone = get_company_tone(company_id)

        # 1) Expiration temporelle
        ok, reason, meta = self._check_temporal_access(plan, subscription)
        if not ok:
            msg = get_system_response("subscription_expired", tone=tone, **meta)
            logger.warning(f"🛡️ [GUARDIAN] company={company_id} user={user_id} → {reason} (plan={plan})")
            return GuardianVerdict(False, reason, msg, meta)

        # 2) Quota d'utilisation
        ok, reason, meta = self._check_usage_quota(subscription)
        if not ok:
            msg = get_system_response("quota_reached", tone=tone, **meta)
            logger.warning(f"🛡️ [GUARDIAN] company={company_id} user={user_id} → {reason}")
            return GuardianVerdict(False, reason, msg, meta)

        # 3) Session limiter (client WhatsApp)
        ok, reason, meta = self._check_session_limit(plan=plan, user_id=user_id)
        if not ok:
            msg = get_system_response("session_limit", tone=tone, **meta)
            logger.info(f"🛡️ [GUARDIAN] company={company_id} user={user_id} → {reason}")
            return GuardianVerdict(False, reason, msg, meta)

        return GuardianVerdict(True, "OK", "", {"plan": plan})

    # ───────────────────────────────────────────────────────────────────────────
    # 1) Expiration temporelle
    # ───────────────────────────────────────────────────────────────────────────

    def _check_temporal_access(
        self, plan: str, subscription: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Règles :
        - Découverte : accès limité dans le temps (trial_ends_at)
        - Starter / Pro / Elite : accès si status=active, sinon vérifier next_billing_date
        """
        status = str(subscription.get("status") or "").strip().lower()
        now = _now_utc()

        # Cas Découverte : période d'essai
        if plan in {"decouverte", "découverte"}:
            trial_end = _parse_iso(subscription.get("pro_trial_ends_at"))
            if trial_end and now > trial_end:
                return (
                    False,
                    "ABONNEMENT_EXPIRE",
                    {"plan": plan, "trial_ended_at": trial_end.isoformat()},
                )
            return (True, "OK", {"plan": plan, "trial_end": trial_end.isoformat() if trial_end else None})

        # Cas payants : status "active" ou "trialing" = OK
        if status in {"active", "trialing"}:
            return (True, "OK", {"plan": plan, "status": status})

        # Sinon vérifier next_billing_date (tolérance jusqu'à la date)
        next_billing = _parse_iso(subscription.get("next_billing_date"))
        if next_billing and now <= next_billing:
            return (True, "OK", {"plan": plan, "status": status, "next_billing": next_billing.isoformat()})

        # Pas de souscription valide
        return (
            False,
            "ABONNEMENT_EXPIRE",
            {"plan": plan, "status": status, "next_billing": next_billing.isoformat() if next_billing else None},
        )

    # ───────────────────────────────────────────────────────────────────────────
    # 2) Quota d'utilisation
    # ───────────────────────────────────────────────────────────────────────────

    def _check_usage_quota(
        self, subscription: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Bloque si current_usage >= usage_limit (quand les champs existent)."""
        try:
            current = int(subscription.get("current_usage") or 0)
            limit = int(subscription.get("usage_limit") or 0)
        except Exception:
            current, limit = 0, 0

        # Si pas de limite définie, on considère "illimité"
        if limit <= 0:
            return (True, "OK", {"usage": current, "limit": "unlimited"})

        if current >= limit:
            return (
                False,
                "QUOTA_EPUISE",
                {"usage": current, "limit": limit},
            )
        return (True, "OK", {"usage": current, "limit": limit})

    # ───────────────────────────────────────────────────────────────────────────
    # 3) Session limiter (messages par client WhatsApp)
    # ───────────────────────────────────────────────────────────────────────────

    def _check_session_limit(
        self, *, plan: str, user_id: Optional[str]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Limite le nombre de messages par client dans une fenêtre glissante."""
        if not user_id or self.session_store is None:
            return (True, "OK", {"session_store": "disabled"})

        # Seuil selon le plan
        if plan in {"decouverte", "découverte"}:
            max_msgs = GUARDIAN_SESSION_MAX_DISCOVERY
        elif plan == "starter":
            max_msgs = GUARDIAN_SESSION_MAX_STARTER
        elif plan == "pro":
            max_msgs = GUARDIAN_SESSION_MAX_PRO
        elif plan == "elite":
            max_msgs = GUARDIAN_SESSION_MAX_ELITE
        else:
            max_msgs = GUARDIAN_SESSION_MAX_STARTER

        try:
            recent = int(self.session_store.count_recent_messages(
                user_id=user_id,
                window_min=GUARDIAN_SESSION_WINDOW_MIN,
            ))
        except Exception as e:
            logger.debug(f"[GUARDIAN] session_store indisponible: {e}")
            return (True, "OK", {"session_store": "unreachable"})

        if recent >= max_msgs:
            return (
                False,
                "SESSION_LIMIT",
                {"recent": recent, "max": max_msgs, "window_min": GUARDIAN_SESSION_WINDOW_MIN},
            )
        return (True, "OK", {"recent": recent, "max": max_msgs})


# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 Instance globale (singleton léger)
# ═══════════════════════════════════════════════════════════════════════════════

_global_guardian: Optional[Guardian] = None


def get_guardian() -> Guardian:
    """Retourne l'instance globale du Guardian (singleton)."""
    global _global_guardian
    if _global_guardian is None:
        _global_guardian = Guardian()
    return _global_guardian


if __name__ == "__main__":
    # Test rapide
    g = Guardian()

    # Cas 1 : Découverte expirée
    info = {
        "plan_name": "decouverte",
        "subscription": {
            "status": "trialing",
            "pro_trial_ends_at": "2024-01-01T00:00:00Z",
        },
    }
    v = g.check_access(company_info=info, user_id="+225xxx", company_id="test")
    print(f"1. Découverte expirée → allowed={v.allowed}, reason={v.reason}")

    # Cas 2 : Pro actif + quota OK
    info = {
        "plan_name": "pro",
        "subscription": {
            "status": "active",
            "current_usage": 100,
            "usage_limit": 10000,
        },
    }
    v = g.check_access(company_info=info)
    print(f"2. Pro actif → allowed={v.allowed}, reason={v.reason}")

    # Cas 3 : Quota épuisé
    info = {
        "plan_name": "starter",
        "subscription": {
            "status": "active",
            "current_usage": 5000,
            "usage_limit": 5000,
        },
    }
    v = g.check_access(company_info=info)
    print(f"3. Quota épuisé → allowed={v.allowed}, reason={v.reason}")
