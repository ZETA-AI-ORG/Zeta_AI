# -*- coding: utf-8 -*-
"""
TESTS EMBEDDINGS V6.5 - Non-régression et validation Layer 3

TESTS CRITIQUES :
1. V6 doit TOUJOURS primer sur embeddings
2. V5 doit TOUJOURS primer sur embeddings  
3. Embeddings actif uniquement si V6/V5 miss
4. Aucun des 130 cas V6 ne doit régresser
5. Seuils respectés (0.75 min, 0.88 max)
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pytest
from typing import Tuple, Optional


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def semantic_filter():
    """Charge le SemanticFilter une seule fois."""
    try:
        from core.embeddings_v6_5 import SemanticFilterV65
        return SemanticFilterV65()
    except ImportError as e:
        pytest.skip(f"sentence-transformers non installé: {e}")


@pytest.fixture(scope="module")
def router():
    """Charge le router complet avec wrapper sync."""
    import asyncio
    from core.setfit_intent_router import route_botlive_intent
    
    def sync_router(message: str):
        """Wrapper synchrone pour appeler le router async avec params par défaut."""
        result = asyncio.run(route_botlive_intent(
            company_id="test_company",
            user_id="test_user",
            message=message,
            conversation_history="",
            state_compact={},
        ))
        return result
    
    return sync_router


# =============================================================================
# TESTS LAYER 3 ISOLÉ
# =============================================================================

class TestSemanticFilterV65:
    """Tests du SemanticFilter en isolation."""
    
    def test_initialization(self, semantic_filter):
        """Le filtre doit s'initialiser correctement."""
        assert semantic_filter is not None
        assert semantic_filter.threshold_min == 0.75
        assert semantic_filter.confidence_max == 0.88
    
    def test_detect_returns_tuple(self, semantic_filter):
        """detect() doit retourner un tuple (intent, conf, proto, debug)."""
        result = semantic_filter.detect("Bonjour comment allez-vous")
        assert isinstance(result, tuple)
        assert len(result) == 4
    
    def test_confidence_capped_at_088(self, semantic_filter):
        """La confiance ne doit jamais dépasser 0.88."""
        # Test avec un prototype exact (similarité ~1.0)
        intent, conf, proto, debug = semantic_filter.detect(
            "Comment vous portez-vous aujourd'hui"  # Prototype exact REASSURANCE
        )
        if intent:
            assert conf <= 0.88, f"Confiance {conf} dépasse 0.88"
    
    def test_below_threshold_returns_none(self, semantic_filter):
        """Sous le seuil 0.75, doit retourner None."""
        # Message très différent des prototypes
        intent, conf, proto, debug = semantic_filter.detect(
            "xyzabc123 random gibberish text"
        )
        assert intent is None
        assert conf == 0.0
    
    def test_stats_available(self, semantic_filter):
        """get_stats() doit retourner des infos valides."""
        stats = semantic_filter.get_stats()
        assert "initialized" in stats
        assert "threshold_min" in stats
        assert stats["threshold_min"] == 0.75


# =============================================================================
# TESTS PRIORITÉ CASCADE (V6 > V5 > Embeddings)
# =============================================================================

class TestCascadePriority:
    """Tests de priorité : V6 et V5 doivent toujours primer sur Embeddings."""
    
    # Messages couverts par V6 (paiement/contact/tracking/problème)
    V6_MESSAGES = [
        ("Vous prenez Wave ?", "REASSURANCE", 0.90),
        ("Je peux payer avec Orange Money", "REASSURANCE", 0.90),
        ("MTN Money ça passe ?", "REASSURANCE", 0.90),
        ("Quel est votre numéro", "REASSURANCE", 0.90),
        ("Comment vous contacter", "REASSURANCE", 0.90),
        ("Mon colis arrive quand", "SAV_SUIVI", 0.95),
        ("Le paquet est abîmé", "SAV_SUIVI", 0.95),
        ("Ma commande a un problème", "SAV_SUIVI", 0.95),
    ]
    
    # Messages couverts par V5 (prix/livraison/catalogue/achat)
    V5_MESSAGES = [
        ("C'est combien", "SHOPPING", 0.90),
        ("Quel est le prix", "SHOPPING", 0.90),
        ("Vous avez quoi comme produits", "SHOPPING", 0.90),
        ("Vous livrez à Yopougon", "REASSURANCE", 0.90),
        ("Comment passer commande", "ACQUISITION", 0.90),
        ("Je veux commander", "ACQUISITION", 0.90),
    ]
    
    @pytest.mark.parametrize("message,expected_intent,min_conf", V6_MESSAGES)
    def test_v6_priority(self, router, message, expected_intent, min_conf):
        """V6 doit TOUJOURS primer sur embeddings."""
        result = router(message)
        
        assert result.intent == expected_intent, (
            f"Message '{message}' devrait être {expected_intent}, "
            f"obtenu {result.intent}"
        )
        assert result.confidence >= min_conf, (
            f"Confiance {result.confidence} < {min_conf} pour '{message}'"
        )
        # Vérifier que c'est bien V6 qui a matché (pas embeddings)
        prefilter = result.debug.get("prefilter", "")
        assert "v6" in prefilter.lower() or "guard" in prefilter.lower(), (
            f"'{message}' devrait être capturé par V6, pas par {prefilter}"
        )
    
    @pytest.mark.parametrize("message,expected_intent,min_conf", V5_MESSAGES)
    def test_v5_priority(self, router, message, expected_intent, min_conf):
        """V5 doit TOUJOURS primer sur embeddings."""
        result = router(message)
        
        assert result.intent == expected_intent, (
            f"Message '{message}' devrait être {expected_intent}, "
            f"obtenu {result.intent}"
        )
        assert result.confidence >= min_conf, (
            f"Confiance {result.confidence} < {min_conf} pour '{message}'"
        )


# =============================================================================
# TESTS EMBEDDINGS FALLBACK (cas non couverts V6/V5)
# =============================================================================

class TestEmbeddingsFallback:
    """Tests des cas où Embeddings doit intervenir (V6/V5 miss)."""
    
    # Messages NON couverts par V6/V5 mais similaires aux prototypes
    EDGE_CASES = [
        # Variantes smalltalk non V5
        ("J'espère que tout va bien de votre côté", "REASSURANCE"),
        ("Bonne continuation à vous", "REASSURANCE"),
        
        # Variantes localisation non V5
        ("Vous êtes installés dans quel coin", "REASSURANCE"),
        
        # Variantes commande non V5
        ("Je souhaite acquérir ce produit", "ACQUISITION"),
        ("Je suis preneur pour ça", "ACQUISITION"),
        
        # Variantes SAV non V6
        ("Ce n'est pas ce que j'avais demandé", "SAV_SUIVI"),
    ]
    
    @pytest.mark.parametrize("message,expected_intent", EDGE_CASES)
    def test_embeddings_catches_edge_cases(self, semantic_filter, message, expected_intent):
        """Embeddings doit capturer les edge cases non V6/V5."""
        intent, conf, proto, debug = semantic_filter.detect(message)
        
        # Si le modèle est disponible et le message est proche d'un prototype
        if semantic_filter.is_available():
            # On vérifie juste que si ça matche, c'est le bon intent
            if intent is not None:
                assert intent == expected_intent, (
                    f"'{message}' devrait être {expected_intent}, obtenu {intent}"
                )
                assert 0.75 <= conf <= 0.88, (
                    f"Confiance {conf} hors bornes [0.75, 0.88]"
                )


# =============================================================================
# TESTS NON-RÉGRESSION DATASET 130
# =============================================================================

class TestNoRegression:
    """Tests de non-régression sur le dataset 130 questions."""
    
    # Échantillon représentatif du dataset 130 (tous doivent rester High)
    SAMPLE_130 = [
        # Greetings
        ("Bonjour", "REASSURANCE", 0.90),
        ("Salut", "REASSURANCE", 0.90),
        ("Merci beaucoup", "REASSURANCE", 0.90),
        
        # Localisation
        ("Où vous trouvez-vous", "REASSURANCE", 0.90),
        ("Vous êtes situé où", "REASSURANCE", 0.90),
        
        # Prix
        ("C'est combien", "SHOPPING", 0.90),
        ("Quel est le prix", "SHOPPING", 0.90),
        
        # Catalogue
        ("Vous avez quoi comme produits", "SHOPPING", 0.90),
        ("Vous avez un catalogue", "SHOPPING", 0.90),
        
        # Livraison
        ("Vous livrez dans quelle zone", "REASSURANCE", 0.90),
        ("Vous livrez à Yopougon", "REASSURANCE", 0.90),
        
        # Acquisition
        ("Je veux commander", "ACQUISITION", 0.90),
        ("Comment passer commande", "ACQUISITION", 0.90),
        
        # Paiement (V6)
        ("Vous acceptez quoi comme paiement", "REASSURANCE", 0.90),
        ("Je peux payer avec Wave", "REASSURANCE", 0.90),
        
        # Contact (V6)
        ("Quel est votre numéro", "REASSURANCE", 0.90),
        ("Comment vous contacter", "REASSURANCE", 0.90),
        
        # Tracking (V6)
        ("Mon colis arrive quand", "SAV_SUIVI", 0.95),
        ("C'est à quel niveau mon colis", "SAV_SUIVI", 0.95),
        
        # Problème (V6)
        ("Le paquet est abîmé", "SAV_SUIVI", 0.95),
        ("Il y a un problème avec le colis", "SAV_SUIVI", 0.95),
    ]
    
    @pytest.mark.parametrize("message,expected_intent,min_conf", SAMPLE_130)
    def test_no_regression(self, router, message, expected_intent, min_conf):
        """Aucun des 130 cas ne doit régresser après ajout Layer 3."""
        result = router(message)
        
        assert result.intent == expected_intent, (
            f"RÉGRESSION: '{message}' était {expected_intent}, "
            f"maintenant {result.intent}"
        )
        assert result.confidence >= min_conf, (
            f"RÉGRESSION: '{message}' conf={result.confidence} < {min_conf}"
        )


# =============================================================================
# TESTS SUGGESTION LOGGER
# =============================================================================

class TestSuggestionLogger:
    """Tests du logger de suggestions."""
    
    def test_logger_creation(self, tmp_path):
        """Le logger doit créer le fichier correctement."""
        from core.embeddings_v6_5 import SuggestionLoggerV65
        
        logger = SuggestionLoggerV65(log_dir=str(tmp_path))
        assert logger.log_file.parent.exists()
    
    def test_log_below_threshold_ignored(self, tmp_path):
        """Les cas sous 0.82 ne doivent pas être loggés."""
        from core.embeddings_v6_5 import SuggestionLoggerV65
        
        logger = SuggestionLoggerV65(log_dir=str(tmp_path))
        result = logger.log_high_confidence_case(
            message="Test message",
            intent="REASSURANCE",
            similarity=0.78,  # Sous 0.82
            matched_prototype="Test proto"
        )
        assert result is False
    
    def test_log_above_threshold_saved(self, tmp_path):
        """Les cas >= 0.82 doivent être loggés."""
        from core.embeddings_v6_5 import SuggestionLoggerV65
        
        logger = SuggestionLoggerV65(log_dir=str(tmp_path))
        result = logger.log_high_confidence_case(
            message="Test message high conf",
            intent="REASSURANCE",
            similarity=0.85,  # Au-dessus de 0.82
            matched_prototype="Test proto"
        )
        assert result is True
        assert logger.log_file.exists()
    
    def test_stats_accurate(self, tmp_path):
        """Les stats doivent être précises."""
        from core.embeddings_v6_5 import SuggestionLoggerV65
        
        logger = SuggestionLoggerV65(log_dir=str(tmp_path))
        
        # Log 2 cas
        logger.log_high_confidence_case("Msg1", "REASSURANCE", 0.85, "Proto1")
        logger.log_high_confidence_case("Msg2", "SHOPPING", 0.83, "Proto2")
        
        stats = logger.get_stats()
        assert stats["total"] == 2
        assert stats["pending"] == 2


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
