from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from core.setfit_intent_router import route_botlive_intent, BotliveRoutingResult
from core.semantic_cache import semantic_cache_decorator, is_cache_enabled
from core.model_router import choose_model

logger = logging.getLogger(__name__)

class ProductionPipeline:
    def __init__(self):
        self.cache_enabled = is_cache_enabled()
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total": 0,
        }

    @semantic_cache_decorator
    async def route_with_cache(self, *args, **kwargs) -> BotliveRoutingResult:
        return await route_botlive_intent(*args, **kwargs)

    async def route_message(self, *args, **kwargs) -> Dict[str, Any]:
        self.stats["total"] += 1
        cache_hit = False
        result: Optional[BotliveRoutingResult] = None
        if self.cache_enabled:
            try:
                result = await self.route_with_cache(*args, **kwargs)
                # GPTCache sets a special attribute if hit; check via result.debug if needed
                cache_hit = getattr(result, "_from_cache", False) or result.debug.get("from_cache", False)
            except Exception as e:
                logger.error(f"[PRODUCTION_PIPELINE] Cache error: {e}")
                result = await route_botlive_intent(*args, **kwargs)
        else:
            result = await route_botlive_intent(*args, **kwargs)
        if cache_hit:
            self.stats["cache_hits"] += 1
        else:
            self.stats["cache_misses"] += 1

        model_choice = choose_model(getattr(result, "intent", None), kwargs.get("complexity"))
        return {
            "result": result,
            "cache_hit": cache_hit,
            "llm_model": model_choice.model,
            "llm_routing_reason": model_choice.reason,
            "stats": self.stats.copy(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()
