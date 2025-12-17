# Stub minimal pour neutraliser ConfidenceGating
from __future__ import annotations

class ConfidenceGating:
    @staticmethod
    def should_gate(question_text: str, images: list, router_result, ctx) -> tuple[bool, str, str]:
        # should_gate, gating_path, gating_reason
        return False, "standard", "disabled"
