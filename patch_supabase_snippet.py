#!/usr/bin/env python3
"""
Script de patch pour intégrer extract_snippet dans _format_supabase_context
"""
import re

file_path = "core/universal_rag_engine.py"

# Lire le fichier
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Patch 1: Modifier la signature de _format_supabase_context
old_signature = "def _format_supabase_context(self, supabase_docs: List[Dict]) -> str:"
new_signature = "def _format_supabase_context(self, supabase_docs: List[Dict], question: str = \"\") -> str:"
content = content.replace(old_signature, new_signature)

# Patch 2: Ajouter l'import et modifier la boucle de formatage
old_loop = """        for i, doc in enumerate(supabase_docs, 1):
            content = doc.get('content', '')[:200]
            score = doc.get('similarity_score', 0)
            stars = self._get_star_rating(int(score * 10))
            
            formatted_context += f"{stars} DOCUMENT SÉMANTIQUE #{i} (Score: {score:.3f})\\n"
            formatted_context += f"📊 Similarité cosinus: {score*100:.1f}%\\n"
            formatted_context += f"📝 Contenu: {content}...\\n\\n\""""

new_loop = """        from core.extract_snippet import extract_relevant_snippet
        for i, doc in enumerate(supabase_docs, 1):
            content = doc.get('content', '')
            score = doc.get('similarity_score', 0)
            stars = self._get_star_rating(int(score * 10))
            snippet = extract_relevant_snippet(question, content)
            formatted_context += f"{stars} DOCUMENT SÉMANTIQUE #{i} (Score: {score:.3f})\\n"
            formatted_context += f"📊 Similarité cosinus: {score*100:.1f}%\\n"
            formatted_context += f"📝 Extrait pertinent: {snippet}\\n\\n\""""

content = content.replace(old_loop, new_loop)

# Patch 3: Mettre à jour l'appel dans search_sequential_sources
old_call = "supabase_context = self._format_supabase_context(supabase_docs)"
new_call = "supabase_context = self._format_supabase_context(supabase_docs, query)"
content = content.replace(old_call, new_call)

# Écrire le fichier modifié
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Patch appliqué avec succès!")
print("📝 Modifications:")
print("  1. Signature _format_supabase_context modifiée")
print("  2. Import extract_snippet ajouté")
print("  3. Extraction intelligente activée")
print("  4. Appel mis à jour avec la question")
