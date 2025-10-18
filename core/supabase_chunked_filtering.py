def split_supabase_doc(content: str) -> list:
    """
    Découpe un doc Supabase en sous-docs (par variante, section, ou bloc).
    Retourne une liste de sous-docs (str).
    """
    import re
    pattern = r'(\n\d+\. .+?)(?=\n\d+\. |\Z)'
    matches = re.findall(pattern, content, flags=re.DOTALL)
    if matches:
        return [m.strip() for m in matches if len(m.strip()) > 20]
    return [p.strip() for p in content.split('\n\n') if len(p.strip()) > 20]

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))
from vector_store_clean_v2 import _calculate_smart_score_v2

async def search_documents_chunked(self, query: str, company_id: str, limit: int = 5) -> list:
    print(f"🔍 Recherche Supabase CHUNKED: '{query}' pour company {company_id}")
    query_embedding = self.generate_embedding(query)
    documents = await self._fetch_documents(company_id)
    print(f"📄 Documents récupérés: {len(documents)}")
    if not documents:
        print("❌ Aucun document trouvé")
        return []
    all_chunks = []
    for doc in documents:
        content = doc.get('content', '')
        for subdoc in split_supabase_doc(content):
            all_chunks.append({'content': subdoc, 'parent_id': doc.get('id'), 'metadata': doc.get('metadata', {})})
    print(f"🪓 Chunks extraits: {len(all_chunks)}")
    if not all_chunks:
        return []
    all_corpus = [c['content'] for c in all_chunks]
    scored = []
    for chunk in all_chunks:
        scoring = _calculate_smart_score_v2(chunk['content'], query, all_corpus)
        chunk.update(scoring)
        scored.append(chunk)
    scored = [c for c in scored if c['score'] > 2]
    scored.sort(key=lambda x: x['score'], reverse=True)
    print(f"🏆 Chunks retenus: {len(scored)} (score > 2)")
    return scored[:limit]
