import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_KEY or not SUPABASE_URL:
    print(f"[SUPABASE][CRITIQUE] Variable SUPABASE_KEY ou SUPABASE_URL absente !")

import logging
import httpx
import sys
import os

# Ajouter le répertoire parent au path pour importer app_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import log3, timing_metric

# Logger standard comme fallback
logger = logging.getLogger(__name__)
async def get_company_system_prompt(company_id: str) -> str:
    """
    Récupère le prompt système avec cache optimisé
    Gain de performance: 2.1s → 0.01s (cache hit)
    """
    # Utiliser le cache unifié pour récupérer le prompt
    from core.unified_cache_system import get_unified_cache_system
    cache_system = get_unified_cache_system()
    cached_prompt = await cache_system.get_cached_prompt(company_id)
    if cached_prompt:
        return cached_prompt
    # Cache miss - récupérer depuis Supabase et mettre en cache
    return await _fetch_prompt_from_database(company_id)


async def get_botlive_prompt(company_id: str) -> str:
    """
    Récupère le prompt Botlive spécifique à l'entreprise depuis Supabase.
    Fallback sur un prompt par défaut en cas d'erreur ou de champ vide.
    """
    try:
        # Utilisation du même accès direct que _fetch_prompt_from_database pour robustesse
        supabase_url = "https://ilbihprkxcgsigvueeme.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        url = f"{supabase_url}/rest/v1/company_rag_configs"
        params = {
            "company_id": f"eq.{company_id}",
            "select": "prompt_botlive_groq_70b"
        }
        
        print(f"🔍 [BOTLIVE_PROMPT] Requête Supabase pour company_id={company_id}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            print(f"🔍 [BOTLIVE_PROMPT] Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json() or []
                print(f"🔍 [BOTLIVE_PROMPT] Données reçues: {len(data)} ligne(s)")
                
                if data:
                    prompt = data[0].get("prompt_botlive_groq_70b", "")
                    print(f"🔍 [BOTLIVE_PROMPT] Taille prompt: {len(prompt)} chars")
                    print(f"🔍 [BOTLIVE_PROMPT] Contient '═══ 1. ANALYSE': {'═══ 1. ANALYSE' in prompt}")
                    print(f"🔍 [BOTLIVE_PROMPT] Premiers 200 chars: {prompt[:200]}")
                    
                    if not prompt:
                        print("❌ [BOTLIVE_PROMPT] PROMPT VIDE dans Supabase!")
                        return "Vous êtes un assistant de vente en direct. Analysez les images et guidez les clients à travers les étapes de commande. Soyez concis et professionnel."
                    
                    return prompt
            else:
                logger.warning(f"[SUPABASE][BOTLIVE_PROMPT] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log3("[SUPABASE][BOTLIVE_PROMPT_EXC]", f"{type(e).__name__}: {e}")
    
    print("❌ [BOTLIVE_PROMPT] FALLBACK utilisé!")
    return "Vous êtes un assistant de vente en direct. Analysez les images et guidez les clients à travers les étapes de commande. Soyez concis et professionnel."


async def _fetch_prompt_from_database(company_id: str) -> str:
    """
    Récupère le prompt depuis la base de données Supabase (clé et URL HARDCODÉES pour robustesse)
    """
    try:
        # Clé et URL service_role HARDCODÉES (comme dans l’archive)
        supabase_url = "https://ilbihprkxcgsigvueeme.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        url = f"{supabase_url}/rest/v1/company_rag_configs"
        params = {
            "company_id": f"eq.{company_id}",
            "select": "system_prompt_template"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    prompt = data[0].get("system_prompt_template", "")
                    if prompt and len(prompt.strip()) > 0:
                        print(f"[SUPABASE] Prompt récupéré ({len(prompt)} chars)")
                        from core.unified_cache_system import get_unified_cache_system
                        cache_system = get_unified_cache_system()
                        await cache_system.prompt_cache.set_prompt(company_id, prompt)
                        return prompt
                    else:
                        print(f"[SUPABASE] Prompt vide pour company_id: {company_id}")
                        return ""
                else:
                    print(f"[SUPABASE] Aucune configuration trouvée pour company_id: {company_id}")
                    return ""
            else:
                print(f"[SUPABASE] Erreur HTTP {response.status_code}: {response.text}")
                return ""
    except Exception as e:
        print(f"[SUPABASE] Erreur lors de la récupération du prompt: {e}")
        return ""

async def search_supabase_semantic(query: str, company_id: str) -> str:
    """
    Recherche sémantique Supabase.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/semantic_data",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={"query": query, "company_id": company_id}
        )
        print(f" [SUPABASE] Requête semantic_data status={response.status_code}")
        
    if response.status_code == 200:
        data = response.json()
        print(f" [SUPABASE] {len(data)} résultats")
        
        return "\n".join([item['content'] for item in data])
    else:
        print(f" [SUPABASE] ❌ Erreur HTTP {response.status_code}: {response.text}")
        return ""


async def get_company_context(company_id: str) -> dict:
    """
    Récupère le contexte complet d'une entreprise depuis la table company_rag_configs.
    Retourne un dict avec tous les champs disponibles ou {} si non trouvé.
    """
    url = f"{SUPABASE_URL}/rest/v1/company_rag_configs"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    params = {
        "company_id": f"eq.{company_id}",
        "select": "*"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    company_data = data[0]
                    # Mapper les champs Supabase vers le format attendu
                    context = {
                        'companyName': company_data.get('company_name', 'Entreprise inconnue'),
                        'aiName': company_data.get('ai_name', 'Assistant'),
                        'sector': company_data.get('secteur_activite', ''),
                        'mission': company_data.get('mission_principale', ''),
                        'objectif_final': company_data.get('objectif_final', ''),
                        'system_prompt_template': company_data.get('system_prompt_template', ''),
                        'rag_enabled': company_data.get('rag_enabled', True),
                        'fallback_message': company_data.get('fallback_to_human_message', ''),
                        # Ajouter tous les autres champs disponibles
                        **{k: v for k, v in company_data.items() if k not in ['company_name', 'ai_name', 'secteur_activite', 'mission_principale', 'objectif_final']}
                    }
                    log3("[SUPABASE] Contexte entreprise", f"Chargé pour {context.get('companyName', 'N/A')}")
                    return context
                else:
                    log3("[SUPABASE] Contexte entreprise", f"Aucune donnée pour company_id: {company_id}")
                    return {}
            else:
                log3("[SUPABASE] Erreur contexte", f"HTTP {resp.status_code} pour company_id: {company_id}")
                return {}
    except Exception as e:
        log3("[SUPABASE] Exception contexte", f"{type(e).__name__}: {str(e)}")
        return {}

@timing_metric("supabase_company_context_semantic")
async def get_semantic_company_context(embedding: list, company_id: str, top_k: int = 3, score_threshold: float = 0.4) -> str:
    """
    Récupère les chunks de contexte d'entreprise les plus pertinents via une recherche sémantique.
    Appelle une RPC Supabase dédiée et retourne un contexte textuel formaté.
    """
    url = f"{SUPABASE_URL}/rest/v1/rpc/search_company_context_chunks"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "embedding": embedding,
        "company_id_match": company_id,
        "top_k": top_k,
        "score_threshold": score_threshold
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code == 200:
            results = response.json()
            if not results:
                log3("[CONTEXT SEMANTIC] Aucun chunk trouvé pour", company_id)
                return ""
            
            # Concaténer le contenu des chunks pertinents
            formatted_context = "\n\n---\n\n".join([chunk['content'] for chunk in results])
            log3("[CONTEXT SEMANTIC] Contexte sémantique assemblé", f"{len(results)} chunks, {len(formatted_context)} chars")
            return formatted_context
        else:
            log3("[CONTEXT SEMANTIC] Erreur Supabase", f"HTTP {response.status_code}: {response.text}")
            return ""
    except Exception as e:
        log3("[CONTEXT SEMANTIC] Exception", f"{type(e).__name__}: {e}")
        return ""

async def delete_all_chunks_for_company(company_id: str) -> int:
    """
    Supprime tous les chunks d'une entreprise (company_id) dans documents.
    Retourne le nombre de suppressions.
    """
    import asyncio
    client = get_supabase_client()
    
    log3("[SUPABASE][DELETE]", f"🎯 SUPPRESSION DANS TABLE 'documents' pour company_id={company_id}")
    
    # D'abord, compter les chunks existants
    try:
        log3("[SUPABASE][DELETE]", f"🔍 Comptage dans table 'documents'...")
        count_result = await asyncio.to_thread(
            lambda: client.table("documents")
                .select("id", count="exact")
                .eq("company_id", company_id)
                .execute()
        )
        existing_count = getattr(count_result, 'count', 0)
        log3("[SUPABASE][DELETE]", f"📊 Chunks existants dans 'documents' pour company_id={company_id}: {existing_count}")
        
        if existing_count == 0:
            log3("[SUPABASE][DELETE]", f"✅ Aucun chunk à supprimer pour company_id={company_id}")
            return 0
            
    except Exception as count_e:
        log3("[SUPABASE][DELETE]", f"❌ Erreur comptage: {str(count_e)}")
        existing_count = -1
    
    # Suppression
    try:
        log3("[SUPABASE][DELETE]", f"🗑️  SUPPRESSION EN COURS dans table 'documents' pour company_id={company_id}...")
        result = await asyncio.to_thread(
            lambda: client.table("documents")
                .delete()
                .eq("company_id", company_id)
                .execute()
        )
        
        log3("[SUPABASE][DELETE]", f"📊 Réponse suppression reçue de table 'documents'")
        
        # Vérifier le résultat
        deleted_data = getattr(result, 'data', [])
        deleted_count = len(deleted_data) if deleted_data else 0
        
        log3("[SUPABASE][DELETE]", f"✅ SUPPRESSION TERMINÉE dans 'documents': {deleted_count} chunks supprimés pour company_id={company_id}")
        
        # Vérification post-suppression
        log3("[SUPABASE][DELETE]", f"🔍 Vérification post-suppression dans table 'documents'...")
        verify_result = await asyncio.to_thread(
            lambda: client.table("documents")
                .select("id", count="exact")
                .eq("company_id", company_id)
                .execute()
        )
        remaining_count = getattr(verify_result, 'count', -1)
        log3("[SUPABASE][DELETE]", f"📊 Vérification 'documents': {remaining_count} chunks restants pour company_id={company_id}")
        
        if remaining_count > 0:
            log3("[SUPABASE][DELETE]", f"⚠️  ATTENTION: {remaining_count} chunks non supprimés!")
            
        return deleted_count
        
    except Exception as e:
        log3("[SUPABASE][EXCEPTION DELETE]", f"❌ {type(e).__name__}: {str(e)}")
        return 0

def get_supabase_client():
    """
    Retourne une instance client Supabase configurée.
    Fonction utilitaire pour l'initialisation du client.
    """
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def onboard_company_to_supabase(
    company_id: str,
    company_name: str,
    ai_name: str,
    secteur_activite: str,
    mission_principale: str,
    objectif_final: str,
    system_prompt_template: str,
    rag_enabled: bool = True,
    fallback_to_human_message: str = "J'ai du mal à vous suivre. Pouvez-vous reformuler ou préférez-vous que je vous redirige vers un conseiller ?",
    ai_objective: str = None,
    prompt_botlive_groq_70b: str = None,
    prompt_botlive_deepseek_v3: str = None
) -> dict:
    """
    Upsert dans company_rag_configs: crée la ligne si elle n'existe pas, met à jour sinon.
    Retourne toujours la ligne résultante (grâce à select("*")).
    """
    from datetime import datetime
    import asyncio

    client = get_supabase_client()
    now = datetime.utcnow().isoformat()

    company_data = {
        "company_id": company_id,
        "company_name": company_name,
        "ai_name": ai_name,
        "secteur_activite": secteur_activite,
        "mission_principale": mission_principale,
        "objectif_final": objectif_final,
        "system_prompt_template": system_prompt_template,
        "rag_enabled": rag_enabled,
        "rag_behavior": "always",  # Valeur par défaut pour respecter la contrainte check
        "fallback_to_human_message": fallback_to_human_message,
        "meili_config": {},
        "searchable_attributes": {},
        "filterable_attributes": {},
        "sortable_attributes": {},
        "document_template_fields": {},
        "updated_at": now,
    }
    
    # Ajouter les champs optionnels s'ils sont fournis
    if ai_objective:
        company_data["ai_objective"] = ai_objective
    if prompt_botlive_groq_70b:
        company_data["prompt_botlive_groq_70b"] = prompt_botlive_groq_70b
    if prompt_botlive_deepseek_v3:
        company_data["prompt_botlive_deepseek_v3"] = prompt_botlive_deepseek_v3

    try:
        log3("[SUPABASE][ONBOARD]", f"⬆️ Upsert company_id={company_id} ...")
        # created_at envoyé pour insertion initiale; updated_at pour toute écriture
        company_data_with_created = {**company_data, "created_at": now}

        # 1) Upsert simple (sans chainage select)
        upsert_result = await asyncio.to_thread(
            lambda: client
            .table("company_rag_configs")
            .upsert(company_data_with_created, on_conflict="company_id")
            .execute()
        )

        # Certaines versions renvoient data vide si aucune modif; dans ce cas on relit
        if hasattr(upsert_result, "data") and upsert_result.data:
            log3("[SUPABASE][ONBOARD]", "✅ Upsert OK (data inline)")
            # upsert peut retourner une liste
            return (upsert_result.data[0] if isinstance(upsert_result.data, list) else upsert_result.data)

        log3("[SUPABASE][ONBOARD]", "ℹ️ Upsert sans payload retourné, lecture explicite ...")
        fetched = await asyncio.to_thread(
            lambda: client.table("company_rag_configs").select("*").eq("company_id", company_id).execute()
        )
        if hasattr(fetched, "data") and fetched.data:
            return fetched.data[0]

        # Fallback 2: tentative directe via PostgREST (service_role) avec Prefer: resolution=merge-duplicates
        try:
            log3("[SUPABASE][ONBOARD]", "↪️ Fallback HTTP PostgREST upsert ...")
            url = f"{SUPABASE_URL}/rest/v1/company_rag_configs"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation"
            }
            async with httpx.AsyncClient(timeout=20) as http:
                resp = await http.post(url, headers=headers, json=company_data_with_created)
                if 200 <= resp.status_code < 300:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        log3("[SUPABASE][ONBOARD]", "✅ HTTP upsert OK")
                        return data[0]
                    elif isinstance(data, dict) and data:
                        log3("[SUPABASE][ONBOARD]", "✅ HTTP upsert OK (dict)")
                        return data
                log3("[SUPABASE][ONBOARD]", f"❌ HTTP upsert status={resp.status_code}: {resp.text}")
        except Exception as http_fallback_e:
            log3("[SUPABASE][ONBOARD]", f"❌ HTTP fallback error: {type(http_fallback_e).__name__}: {str(http_fallback_e)}")

        # Si aucune donnée n'est retournée, cela peut être dû aux policies RLS (SELECT non autorisé)
        log3("[SUPABASE][ONBOARD]", "⚠️ Aucune donnée lue après upsert. Suspect RLS (SELECT). Retour des valeurs upsertées en fallback.")
        return company_data_with_created

    except Exception as e:
        import traceback
        log3("[SUPABASE][ONBOARD]", f"❌ Erreur upsert: {type(e).__name__}: {str(e)}")
        log3("[SUPABASE][ONBOARD]", f"Stack: {traceback.format_exc()}")
        raise


async def insert_text_chunk_in_supabase(chunks: list) -> list:
    """
    Insère un chunk texte dans la table documents avec embedding 384 dim + float16.
    
    🎯 STRATÉGIE OPTIMISÉE:
    - Génération: float32 (384 dim) - Précision max
    - Conversion: float16 - Économie mémoire
    - Stockage: embedding_384_half (halfvec) - Production
    """
    import asyncio
    import numpy as np
    from embedding_models import embed_text, DEFAULT_EMBEDDING_MODEL
    
    client = get_supabase_client()
    
    log3("[SUPABASE][INSERT]", f"🎯 TENTATIVE INSERTION DANS TABLE 'documents'")
    log3("[SUPABASE][INSERT]", f"📊 Nombre de chunks à insérer: {len(chunks)}")
    
    # Générer embeddings 384 dim + float16 pour chaque chunk
    processed_chunks = []
    for i, chunk in enumerate(chunks):
        try:
            content = chunk.get('content', '')
            if not content:
                log3("[SUPABASE][INSERT]", f"⚠️ Chunk {i} sans contenu, ignoré")
                continue
            
            # 1. Générer embedding 384 dim en float32 (précision max)
            log3("[SUPABASE][INSERT]", f"🔄 Génération embedding 384 dim pour chunk {i}...")
            embedding_float32 = await embed_text(
                content, 
                key=DEFAULT_EMBEDDING_MODEL,  # minilm-l6-v2 = 384 dim
                use_cache=True,
                return_float16=False  # Générer en float32 d'abord
            )
            
            # 2. Convertir en float16 pour stockage (économie)
            embedding_float16 = np.array(embedding_float32, dtype=np.float16)
            
            # 3. Préparer chunk avec embedding_384_half
            import uuid
            from datetime import datetime
            
            processed_chunk = {
                'company_id': chunk.get('company_id'),
                'content': content,
                'embedding_384_half': embedding_float16.tolist(),  # halfvec(384)
                'metadata': chunk.get('metadata', {}),
                'created_at': chunk.get('created_at') or datetime.utcnow().isoformat()
            }
            
            # Ajouter ID seulement si fourni (sinon Supabase auto-génère)
            if chunk.get('id'):
                processed_chunk['id'] = chunk.get('id')
            
            processed_chunks.append(processed_chunk)
            log3("[SUPABASE][INSERT]", f"✅ Chunk {i} traité: 384 dim float16 ({len(embedding_float16)} valeurs)")
            
        except Exception as chunk_error:
            log3("[SUPABASE][INSERT]", f"❌ Erreur traitement chunk {i}: {chunk_error}")
            continue
    
    if not processed_chunks:
        log3("[SUPABASE][INSERT]", f"❌ Aucun chunk valide à insérer")
        return []
    
    # Log du premier chunk pour debug
    if processed_chunks:
        first_chunk = processed_chunks[0]
        log3("[SUPABASE][INSERT]", f"📋 Premier chunk - ID: {first_chunk.get('id', 'N/A')}")
        log3("[SUPABASE][INSERT]", f"📋 Premier chunk - company_id: {first_chunk.get('company_id', 'N/A')}")
        log3("[SUPABASE][INSERT]", f"📋 Premier chunk - embedding_384_half: {len(first_chunk.get('embedding_384_half', []))} dim")
        log3("[SUPABASE][INSERT]", f"📋 Clés disponibles: {list(first_chunk.keys())}")
    
    try:
        log3("[SUPABASE][INSERT]", f"🔄 Exécution insertion vers table 'documents'...")
        result = await asyncio.to_thread(
            client.table("documents").insert(processed_chunks).execute
        )
        
        log3("[SUPABASE][INSERT]", f"✅ Réponse Supabase reçue")
        log3("[SUPABASE][INSERT]", f"📊 Type résultat: {type(result)}")
        
        if hasattr(result, 'data') and result.data:
            inserted_count = len(result.data)
            log3("[SUPABASE][INSERT]", f"🎉 SUCCÈS: {inserted_count} chunks insérés dans TABLE 'documents'")
            log3("[SUPABASE][INSERT]", f"💎 Format: 384 dimensions + float16 (4x plus léger!)")
            
            # Log des IDs insérés
            inserted_ids = [item.get('id') for item in result.data if item.get('id')]
            log3("[SUPABASE][INSERT]", f"📝 IDs insérés: {inserted_ids[:5]}{'...' if len(inserted_ids) > 5 else ''}")
            
            return result.data
        else:
            log3("[SUPABASE][INSERT]", f"❌ ÉCHEC: Aucune donnée insérée dans 'documents'")
            log3("[SUPABASE][INSERT]", f"🔍 Résultat brut: {result}")
            return []
            
    except Exception as e:
        log3("[SUPABASE][INSERT]", f"💥 ERREUR INSERTION dans 'documents': {type(e).__name__}: {str(e)}")
        import traceback
        log3("[SUPABASE][INSERT]", f"📚 Traceback: {traceback.format_exc()}")
        return []


def upload_image_to_supabase(path: str, file_bytes: bytes) -> str:
    """
    Upload un fichier binaire à Supabase Storage dans le bucket 'product-images' et retourne l’URL publique.
    """
    client = get_supabase_client()
    bucket = "product-images"
    try:
        # Upload le fichier (remplace si déjà existant)
        res = client.storage.from_(bucket).upload(path, file_bytes, {'upsert': 'true', 'content-type': 'image/jpeg'})
        if not res:
            log3("[SUPABASE] Upload", f"Echec upload {path}")
            raise Exception("Erreur upload Supabase")
        # Génère l’URL publique
        url = client.storage.from_(bucket).get_public_url(path)
        log3("[SUPABASE] Upload", f"Fichier uploadé: {url}")
        return url
    except Exception as e:
        log3("[SUPABASE] Exception upload", f"{type(e).__name__}: {str(e)}")
        raise

# --- NEW: RPC helper for unified semantic search ---
async def match_documents_via_rpc(embedding: list, company_id: str, top_k: int = 5, min_score: float = 0.0, filter_metadata: dict | None = None, original_query: str = None) -> list:
    """
    🚀 RECHERCHE VECTORIELLE SUPABASE OPTIMISÉE
    Utilise le nouveau module optimisé pour la recherche sémantique
    """
    try:
        # Import du nouveau module optimisé
        from core.supabase_vector_search import supabase_semantic_search
        
        # CORRECTION CRITIQUE: Utiliser la vraie question si fournie
        log3("[SUPABASE][DEBUG]", f"🔍 original_query reçu: '{original_query}'")
        log3("[SUPABASE][DEBUG]", f"🔍 Type: {type(original_query)}")
        log3("[SUPABASE][DEBUG]", f"🔍 Booléen: {bool(original_query)}")
        
        if original_query and original_query.strip():
            query_text = original_query.strip()
            log3("[SUPABASE][QUERY_FIX]", f"✅ Utilisation de la vraie question: '{query_text[:50]}...'")
        else:
            query_text = f"recherche_vectorielle_{company_id}"  # Fallback
            log3("[SUPABASE][QUERY_FALLBACK]", f"⚠️ Utilisation du fallback: '{query_text}'")
        
        # Utilisation du nouveau moteur optimisé
        results_dict, formatted_context = await supabase_semantic_search(
            query=query_text,
            company_id=company_id,
            top_k=top_k,
            min_score=min_score,
            enable_reranking=True
        )
        
        log3("[SUPABASE][OPTIMIZED]", f"✅ Nouveau moteur utilisé: {len(results_dict)} résultats")
        return results_dict
        
    except ImportError:
        # Fallback vers l'ancienne méthode si le nouveau module n'est pas disponible
        log3("[SUPABASE][FALLBACK]", "⚠️ Fallback vers ancienne méthode")
        return await _legacy_match_documents(embedding, company_id, top_k, min_score)
    except Exception as e:
        log3("[SUPABASE][OPTIMIZED_ERROR]", f"💥 Erreur nouveau moteur: {str(e)}")
        return await _legacy_match_documents(embedding, company_id, top_k, min_score)

async def _legacy_match_documents(embedding: list, company_id: str, top_k: int = 5, min_score: float = 0.0) -> list:
    """Méthode legacy pour compatibilité"""
    try:
        # Convertir l'embedding en format PostgreSQL vector
        embedding_str = f"[{','.join(map(str, embedding))}]"
        
        # Requête SQL directe avec similarité cosinus
        url = f"{SUPABASE_URL}/rest/v1/documents"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Paramètres de requête avec similarité vectorielle pgvector
        params = {
            "company_id": f"eq.{company_id}",
            "select": "id,content,metadata,company_id,embedding",
            "limit": "50"  # Récupérer jusqu'à 50 documents pour tri local
        }
        
        log3("[SUPABASE][LEGACY]", f"🔍 Recherche legacy (company_id={company_id}, top_k={top_k})")
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)
            
        if resp.status_code == 200:
            import numpy as np
            def cosine_similarity(a, b):
                a = np.array(a, dtype=np.float32)
                b = np.array(b, dtype=np.float32)
                if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
                    return 0.0
                return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

            data = resp.json() or []
            # Calculer la similarité cosinus avec l'embedding de la requête
            for doc in data:
                try:
                    doc_emb = doc.get('embedding')
                    if isinstance(doc_emb, str):
                        doc_emb = [float(x) for x in doc_emb.strip('[]').split(',')]
                    doc['score'] = cosine_similarity(embedding, doc_emb)
                except Exception:
                    doc['score'] = 0.0
            # Trier par similarité décroissante et retourner les top_k
            data = sorted(data, key=lambda d: d['score'], reverse=True)[:top_k]
            log3("[SUPABASE][LEGACY]", f"✅ {len(data)} documents trouvés et triés par similarité cosinus")
            return data
        else:
            log3("[SUPABASE][LEGACY]", f"❌ HTTP {resp.status_code}: {resp.text}")
            return []
            
    except Exception as e:
        log3("[SUPABASE][LEGACY_EXC]", f"{type(e).__name__}: {e}")
        return []