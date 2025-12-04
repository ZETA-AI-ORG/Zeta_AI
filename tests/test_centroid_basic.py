import os
import logging

from pathlib import Path
import sys

# Ajouter la racine du projet au path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.centroid_router import CentroidRouter

logging.basicConfig(level=logging.INFO)


def test_router_initialization():
    router = CentroidRouter()
    assert len(router.centroids) == 12


def test_route_basic_intent_fields():
    router = CentroidRouter()
    result = router.route("Bjr vs ete ou ?")

    assert "intent_id" in result
    assert "intent_name" in result
    assert "prompt_target" in result
    assert "score" in result
    assert "confidence" in result
    assert result["method"] == "centroid_cosine"


def test_route_empty_message_returns_clarification_or_default():
    router = CentroidRouter()
    result = router.route("")

    assert "intent_id" in result
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
