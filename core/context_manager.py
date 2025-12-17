# Stub minimal pour neutraliser le ContextManager
from __future__ import annotations
from types import SimpleNamespace

class ContextManager:
    async def get_or_create_context(self, user_id: str, company_id: str, notepad_snapshot=None):
        # Renvoie un objet avec un attribut checklist attendu par l'appelant
        checklist = SimpleNamespace(photo=None, paiement=None, zone=None, telephone=None)
        return SimpleNamespace(checklist=checklist)

    async def add_user_message(self, ctx, message: str):
        return None

    async def add_assistant_message(self, ctx, message: str):
        return None
