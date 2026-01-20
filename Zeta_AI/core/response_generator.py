"""
Module de génération de réponses pour le chatbot.
Gère la construction et le formatage des réponses du RAG.
"""
from typing import Dict, Any, Optional
import json

class ResponseGenerator:
    """
    Classe utilitaire pour générer des réponses structurées pour le chatbot.
    """
    
    @staticmethod
    def generate_response(
        query: str,
        context: str = "",
        sources: list = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère une réponse structurée pour l'API.
        
        Args:
            query: La requête utilisateur d'origine
            context: Le contexte généré par le RAG
            sources: Liste des sources/document utilisés
            metadata: Métadonnées supplémentaires
            status: Statut de la réponse (success/error)
            error: Message d'erreur si applicable
            
        Returns:
            Un dictionnaire contenant la réponse formatée
        """
        if sources is None:
            sources = []
            
        if metadata is None:
            metadata = {}
            
        response = {
            "status": status,
            "query": query,
            "response": context,
            "sources": sources,
            "metadata": metadata
        }
        
        if error:
            response["error"] = error
            
        return response
    
    @staticmethod
    def format_sources(sources: list) -> str:
        """
        Formate les sources pour l'affichage.
        
        Args:
            sources: Liste des sources/documents
            
        Returns:
            Chaîne formatée des sources
        """
        if not sources:
            return ""
            
        formatted = []
        for i, source in enumerate(sources, 1):
            if isinstance(source, dict):
                # Format pour les documents avec métadonnées
                title = source.get("title", f"Document {i}")
                url = source.get("url", "")
                page = source.get("page", "")
                
                if url:
                    formatted.append(f"{i}. [{title}]({url})" + (f" (page {page})" if page else ""))
                else:
                    formatted.append(f"{i}. {title}" + (f" (page {page})" if page else ""))
            else:
                # Format pour les sources simples
                formatted.append(f"{i}. {source}")
                
        return "\n".join(formatted)
    
    @staticmethod
    def error_response(
        query: str,
        error_message: str,
        error_type: str = "processing_error",
        status_code: int = 400
    ) -> Dict[str, Any]:
        """
        Génère une réponse d'erreur standardisée.
        
        Args:
            query: La requête utilisateur d'origine
            error_message: Message d'erreur détaillé
            error_type: Type d'erreur pour le traitement côté client
            status_code: Code HTTP de statut
            
        Returns:
            Un dictionnaire contenant la réponse d'erreur formatée
        """
        return {
            "status": "error",
            "query": query,
            "error": error_message,
            "error_type": error_type,
            "status_code": status_code,
            "response": "",
            "sources": []
        }
