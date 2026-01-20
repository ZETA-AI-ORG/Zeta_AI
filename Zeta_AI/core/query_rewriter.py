from utils import log3
from core.llm_client import GroqLLMClient

class QueryRewriter:
    def __init__(self, llm_client: GroqLLMClient):
        self.llm_client = llm_client

    async def rewrite(self, user_query: str, conversation_history: list) -> str:
        """
        Réécrit la requête utilisateur en une question autonome en utilisant l'historique de la conversation.
        Retourne la requête originale si l'historique est court ou si la réécriture échoue.
        """
        if not conversation_history or len(conversation_history) < 2: # Pas assez de contexte pour réécrire
            log3("[REWRITER] Historique trop court, pas de réécriture.", user_query)
            return user_query

        # Formatage de l'historique pour le prompt
        formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        
        prompt_template = f"""En te basant sur l'historique de conversation ci-dessous, réécris la dernière question de l'utilisateur ('user') pour qu'elle soit une question autonome et complète, sans ajouter d'informations qui ne sont pas dans l'historique. Si la question est déjà autonome, retourne-la telle quelle.

Historique:
{formatted_history}

Dernière question: {user_query}

Question réécrite:"""

        log3("[REWRITER] Lancement de la réécriture de la requête...", prompt_template)

        try:
            rewritten_query = await self.llm_client.generate_response(
                prompt=prompt_template,
                temperature=0.0, # Déterministe
                max_tokens=100
            )
            
            # Nettoyage de la réponse du LLM
            rewritten_query = rewritten_query.strip()
            if rewritten_query:
                log3("[REWRITER] Requête réécrite avec succès", rewritten_query)
                return rewritten_query
            else:
                log3("[REWRITER] La réécriture a retourné une chaîne vide, fallback.", user_query)
                return user_query

        except Exception as e:
            log3(f"[REWRITER] Erreur lors de la réécriture: {e}", "Fallback sur la requête originale.")
            return user_query
