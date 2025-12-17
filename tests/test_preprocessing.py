from pathlib import Path
import sys

# Ajouter la racine du projet au path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.text_preprocessing import preprocess_for_routing, should_skip_preprocessing


def test_remove_greeting_with_question():
    assert preprocess_for_routing("Bonjour, vous êtes où?") == "vous etes ou"
    assert preprocess_for_routing("Salut, c'est combien?") == "c est combien"


def test_remove_politeness_phrases():
    assert (
        preprocess_for_routing("Bonjour j'espère que ça va, vous livrez où?")
        == "vous livrez ou"
    )
    assert (
        preprocess_for_routing("Salut j'espère la famille va bien, c'est combien?")
        == "c est combien"
    )


def test_keep_pure_greetings():
    assert should_skip_preprocessing("Bonjour") is True
    assert should_skip_preprocessing("Merci") is True
    assert should_skip_preprocessing("Bonjour, vous êtes où?") is False


def test_preserve_command_verbs():
    assert preprocess_for_routing("Je veux commander") == "je veux commander"
    assert preprocess_for_routing("Bonjour, je veux commander") == "je veux commander"
