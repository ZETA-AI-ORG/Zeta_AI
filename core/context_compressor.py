"""
🗜️ CONTEXT COMPRESSOR - Compression intelligente du contexte
Réduit encore plus le contexte en supprimant redondances et infos inutiles
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def compress_context(docs: List[Dict[str, Any]], max_chars: int = 3000) -> List[Dict[str, Any]]:
    """
    Compresse le contexte en supprimant redondances
    
    Args:
        docs: Documents extraits
        max_chars: Limite de caractères totale
        
    Returns:
        Documents compressés
    """
    if not docs:
        return []
    
    total_chars = sum(len(doc.get("content", "")) for doc in docs)
    
    if total_chars <= max_chars:
        logger.info(f"📊 [COMPRESSION] Pas nécessaire ({total_chars} <= {max_chars})")
        return docs
    
    logger.info(f"🗜️ [COMPRESSION] Réduction {total_chars} → {max_chars} chars...")
    
    compressed_docs = []
    current_chars = 0
    seen_content = set()  # Détecter doublons
    
    for doc in docs:
        content = doc.get("content", "")
        
        # 1. Supprimer lignes vides multiples
        content = re.sub(r'\n\n+', '\n\n', content)
        
        # 2. Supprimer espaces inutiles
        content = re.sub(r' +', ' ', content)
        
        # 3. Détecter contenu dupliqué (similarité simple)
        content_hash = _get_content_hash(content)
        if content_hash in seen_content:
            logger.debug(f"🗜️ [COMPRESSION] Doublon détecté, skip")
            continue
        seen_content.add(content_hash)
        
        # 4. Tronquer si nécessaire
        remaining_chars = max_chars - current_chars
        if len(content) > remaining_chars:
            content = content[:remaining_chars] + "..."
            logger.debug(f"🗜️ [COMPRESSION] Tronqué à {remaining_chars} chars")
        
        doc_copy = doc.copy()
        doc_copy["content"] = content
        doc_copy["compressed"] = True
        compressed_docs.append(doc_copy)
        
        current_chars += len(content)
        
        if current_chars >= max_chars:
            logger.info(f"🗜️ [COMPRESSION] Limite atteinte ({current_chars}/{max_chars})")
            break
    
    reduction = ((total_chars - current_chars) / total_chars * 100) if total_chars > 0 else 0
    logger.info(f"✅ [COMPRESSION] {len(docs)} → {len(compressed_docs)} docs, -{reduction:.1f}% chars")
    
    return compressed_docs


def _get_content_hash(content: str) -> str:
    """Hash simple pour détecter doublons"""
    # Normaliser et hasher les 100 premiers caractères
    normalized = re.sub(r'\s+', ' ', content.lower())[:100]
    return str(hash(normalized))


def remove_redundant_info(content: str) -> str:
    """
    Supprime infos redondantes dans un document
    
    Exemples:
    - Headers répétés
    - Notes en double
    - Sections vides
    """
    lines = content.split("\n")
    cleaned_lines = []
    seen_lines = set()
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip lignes vides
        if not line_stripped:
            continue
        
        # Skip lignes répétées
        line_normalized = re.sub(r'\s+', ' ', line_stripped.lower())
        if line_normalized in seen_lines:
            continue
        seen_lines.add(line_normalized)
        
        # Skip headers génériques répétés
        if re.match(r'^(PRODUIT|LIVRAISON|PAIEMENT|CONTACT):?\s*$', line_stripped, re.IGNORECASE):
            continue
        
        cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)


def smart_truncate(text: str, max_length: int) -> str:
    """
    Tronque intelligemment (coupe à la phrase)
    """
    if len(text) <= max_length:
        return text
    
    # Chercher dernière phrase complète
    truncated = text[:max_length]
    
    # Chercher dernier point/retour ligne
    last_period = max(truncated.rfind('.'), truncated.rfind('\n'))
    
    if last_period > max_length * 0.7:  # Au moins 70% du texte
        return truncated[:last_period + 1]
    
    # Sinon couper brutalement
    return truncated + "..."


# ═══════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_docs = [
        {
            "content": """PRODUIT: Couches à pression


Taille 3 - 6 à 11 kg - 300 couches | 22.900 F CFA
   - Prix: 22 900 FCFA
   - Quantité: 300 pcs


NOTES IMPORTANTES:
Vendu par lot de 300 minimum"""
        },
        {
            "content": """LIVRAISON - ZONES CENTRALES


- Angré : 1 500 FCFA
- Cocody : 1 500 FCFA


Délais: Livraison le jour même si commande avant 13h"""
        }
    ]
    
    compressed = compress_context(test_docs, max_chars=200)
    
    print("📊 AVANT:")
    for doc in test_docs:
        print(f"  - {len(doc['content'])} chars")
    
    print("\n📊 APRÈS:")
    for doc in compressed:
        print(f"  - {len(doc['content'])} chars")
        print(f"    {doc['content'][:50]}...")
