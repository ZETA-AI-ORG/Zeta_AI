# Stub minimal pour neutraliser RuleOverrides
from __future__ import annotations

class RuleOverrides:
    @staticmethod
    def should_trigger_before_router(message: str, ctx) -> tuple[bool, str]:
        return False, ""

    @staticmethod
    def get_override_action(reason: str, message: str, ctx):
        return None
