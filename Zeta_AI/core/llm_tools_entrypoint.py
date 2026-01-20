# Intégration agent LangChain avec outils dans le pipeline principal
from core.llm_tools_agent import agent as tools_agent

def run_llm_with_tools(user_message, chat_history=None):
    # Le LLM LangChain agent utilisera automatiquement les outils disponibles
    # Optionnel: passer l'historique si besoin
    if chat_history:
        return tools_agent.run(user_message, chat_history=chat_history)
    else:
        return tools_agent.run(user_message)
