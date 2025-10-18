from langchain.agents import initialize_agent, Tool
from langchain.tools import PythonREPLTool
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI

# Bloc-note structuré (JSON/dict)
class NotepadTool:
    def __init__(self):
        self.notes = {}
    def add(self, key, value):
        self.notes[key] = value
        return f"Ajouté: {key} = {value}"
    def get(self, key):
        return self.notes.get(key, "Non trouvé")
    def show(self):
        return self.notes

notepad = NotepadTool()
def add_note(key: str, value: str):
    return notepad.add(key, value)
def get_note(key: str):
    return notepad.get(key)
def show_notes():
    return notepad.show()

tools = [
    Tool(
        name="Calculatrice Python",
        func=PythonREPLTool().run,
        description="Effectue des calculs mathématiques avancés."
    ),
    Tool(
        name="Bloc-note: ajouter info",
        func=add_note,
        description="Ajoute une info clé (produit, zone, livraison, paiement) dans le bloc-note."
    ),
    Tool(
        name="Bloc-note: lire info",
        func=get_note,
        description="Récupère une info clé du bloc-note."
    ),
    Tool(
        name="Bloc-note: tout afficher",
        func=show_notes,
        description="Affiche toutes les infos du bloc-note."
    )
]

llm = OpenAI(temperature=0)
memory = ConversationBufferMemory(memory_key="chat_history")

agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    memory=memory,
    verbose=True
)

# Exemple d'appel : agent.run("Ajoute produit: Couches taille 2")
# Le LLM pourra utiliser les outils pour stocker, relire, calculer, etc.
