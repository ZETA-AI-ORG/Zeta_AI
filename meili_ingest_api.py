from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import os
import logging
import uuid

# ETL dédié Meilisearch
from ingestion.meili_etl import transform, push_to_meili

router = APIRouter(prefix="/meili", tags=["meilisearch"])

class MeiliDoc(BaseModel):
    id: Optional[str] = None
    content: str
    metadata: Optional[dict] = Field(default_factory=dict)

class MeiliIngestRequest(BaseModel):
    company_id: str
    # Accepts docs as either a list or a dict (object), to match n8n and standard
    docs: Optional[Union[List[MeiliDoc], Dict[str, Any]]] = Field(None, alias='docs')
    docS: Optional[Union[List[MeiliDoc], Dict[str, Any]]] = Field(None, alias='docS')

    @validator('docS', 'docs', pre=True, always=True)
    def ensure_docs(cls, v, values, **kwargs):
        # Accept both dict (object) and list for docs/docS
        if v is None and 'docs' not in values and 'docS' not in values:
            raise ValueError("Au moins un des champs 'docs' ou 'docS' doit être fourni")
        if isinstance(v, dict):
            # Convert dict of docs to list of MeiliDoc
            return [MeiliDoc(**doc) if isinstance(doc, dict) else doc for doc in v.values()]
        return v


async def delete_meili_index(meili_client, index_name):
    """Supprime complètement l'index Meilisearch s'il existe"""
    try:
        meili_client.delete_index(index_name)
        logging.info(f"[MEILISEARCH] Suppression de l'index {index_name}")
        return True
    except Exception as e:
        # Ignorer l'erreur si l'index n'existe pas
        if "index_not_found" in str(e):
            logging.info(f"[MEILISEARCH] L'index {index_name} n'existe pas encore")
        else:
            logging.error(f"[MEILISEARCH] Erreur lors de la suppression de l'index {index_name}: {str(e)}")
        return False

@router.post("/ingest")
async def ingest_meili_docs(request: MeiliIngestRequest):
    try:
        import meilisearch
        meili_client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"),
            os.environ.get("MEILI_API_KEY", "")
        )
        index_name = f"company_docs_{request.company_id}"
        
        # Supprimer complètement l'index avant la nouvelle ingestion
        await delete_meili_index(meili_client, index_name)
        
        # Utiliser docS si fourni, sinon utiliser docs
        documents = request.docS or request.docs or []
        logging.info(f"[MEILISEARCH] Réception de {len(documents)} documents pour company_id={request.company_id}")
        try:
            meili_client.create_index(index_name, {"primaryKey": "id"})
        except Exception as e:
            logging.info(f"[MEILISEARCH] Index déjà existant ou erreur mineure: {e}")
        logging.info(f"[MEILI][DEBUG] Nombre de documents reçus: {len(documents)}")
        docs_for_meili = []
        for idx, doc in enumerate(documents):
            if not doc.content.strip():
                logging.warning(f"[MEILI][SKIP] Document {idx} ignoré car content vide")
                continue
                
            doc_id = doc.id or str(uuid.uuid4())
            base = {
                "id": doc_id,
                "company_id": request.company_id,
                "content": doc.content,
            }
            if doc.metadata:
                base.update(doc.metadata)
            docs_for_meili.append(base)
            
        logging.info(f"[MEILI][DEBUG] {len(docs_for_meili)} documents prêts pour l'indexation")
        if docs_for_meili:
            resp = meili_client.index(index_name).add_documents(docs_for_meili)
            logging.info(f"[MEILISEARCH] {len(docs_for_meili)} documents envoyés à Meili pour company_id={request.company_id} | Task: {resp['taskUid'] if isinstance(resp, dict) and 'taskUid' in resp else resp}")
            return {"indexed": len(docs_for_meili), "task": resp}
        else:
            return {"indexed": 0, "message": "Aucun document à indexer"}
    except Exception as e:
        logging.exception("[MEILISEARCH][INSERT][ERREUR]")
        raise HTTPException(status_code=500, detail=str(e))


# ================== ETL avancé: POST /meili/ingest-etl ==================
class MeiliETLRequest(BaseModel):
    company_id: str
    text: Optional[str] = None
    text_documents: Optional[List[Dict[str, Any]]] = None
    purge_before: Optional[bool] = True


def _safe_uid(base: str, company_id: str) -> str:
    import re
    s = f"{base}_{company_id}"
    s = re.sub(r"[^A-Za-z0-9_-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:200]


def _normalize_text_from_docs(docs: List[Dict[str, Any]]) -> str:
    """Construire un texte conforme au parseur transform() à partir de docs structurés.
    Sections générées:
    - ### IDENTITÉ ENTREPRISE ###
    - ### CATALOGUE / OFFRES ###
    - ### CONDITIONS & LIVRAISON ###
    - ### SUPPORT ###
    """
    company_lines: List[str] = []
    product_blocks: List[str] = []
    delivery_zones: List[str] = []
    delays: List[str] = []
    support_lines: List[str] = []
    payment_bullets: List[str] = []

    def _get(d: Dict[str, Any], *keys):
        cur = d
        for k in keys:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    # Dispatcher
    for d in docs or []:
        meta = d.get("metadata", {}) if isinstance(d, dict) else {}
        dtype = (meta.get("type") or meta.get("document_type") or "").lower()

        if dtype == "company":
            name = meta.get("name")
            ai_name = meta.get("ai_name")
            sector = meta.get("sector")
            desc = meta.get("description")
            mission = meta.get("mission")
            objective = meta.get("objective")
            zone = meta.get("zone")
            if name:
                company_lines.append(f"Nom de l'Entreprise : {name}")
            if ai_name:
                company_lines.append(f"Nom de l'IA : {ai_name}")
            if sector:
                company_lines.append(f"Secteur d'activité : {sector}")
            if desc:
                company_lines.append(f"Description de l'Entreprise : {desc}")
            if mission:
                company_lines.append(f"Mission : {mission}")
            if objective:
                company_lines.append(f"Objectif de l'IA : {objective}")
            if zone:
                company_lines.append(f"Zone d’activité : {zone}")

        elif dtype == "product":
            product_name = meta.get("product_name") or meta.get("name")
            category = meta.get("category")
            subcat = meta.get("subcategory")
            description = meta.get("description")
            color = meta.get("color") or _get(meta, "attributes_canonical", "color")
            price = meta.get("price") or meta.get("min_price") or _get(meta, "variants", 0, "prix")
            stock = meta.get("stock") or _get(meta, "variants", 0, "stock")

            block: List[str] = []
            if product_name:
                block.append(f"Produit : {product_name}")
            if description:
                block.append(f"Description : {description}")
            if category:
                block.append(f"Catégorie : {category}")
            if subcat:
                block.append(f"Sous-catégorie : {subcat}")
            # Variante synthétique
            if color or price or stock:
                col = color or ""
                block.append(f"Variante (Couleur : {col}) :")
                if price is not None:
                    block.append(f"Prix : {price}")
                if stock is not None:
                    block.append(f"Stock : {stock}")
                if description:
                    block.append(f"Description : {description}")
            product_blocks.append("\n".join(block))

        elif dtype == "delivery":
            zone = meta.get("zone") or meta.get("zone_slug")
            price_raw = _get(meta, "price", "raw") or meta.get("price")
            if zone and price_raw:
                delivery_zones.append(f"{zone} : {price_raw}")
            # Délais consolidés
            abj = _get(meta, "delay", "abidjan")
            hors = _get(meta, "delay", "hors_abidjan")
            if abj or hors:
                parts = []
                if abj:
                    parts.append(f"Abidjan: {abj}")
                if hors:
                    parts.append(f"Hors Abidjan: {hors}")
                delays.append(" ".join(parts))

        elif dtype == "support":
            phone = meta.get("phone_e164") or meta.get("phone_raw")
            hours = meta.get("hours")
            store_type = meta.get("store_type")
            if phone:
                support_lines.append(f"Contact du support : {phone}")
            if hours:
                support_lines.append(f"Horaires d'ouverture : {hours}")
            if store_type:
                support_lines.append(f"Type de boutique : {store_type}")

        elif dtype == "payment":
            method = meta.get("method")
            details = meta.get("details")
            if method and details:
                payment_bullets.append(f"- {method}: {details}")

    # Assembler sections
    out_parts: List[str] = []
    if company_lines:
        out_parts.append("### IDENTITÉ ENTREPRISE ###")
        out_parts.extend(company_lines)
        out_parts.append("")

    if product_blocks:
        out_parts.append("### CATALOGUE / OFFRES ###")
        out_parts.append("\n\n".join(product_blocks))
        out_parts.append("")

    if delivery_zones or delays:
        out_parts.append("### CONDITIONS & LIVRAISON ###")
        if delivery_zones:
            out_parts.append("Zones et Frais :")
            out_parts.extend(delivery_zones)
        if delays:
            out_parts.append(f"Délais : {' '.join(delays)}")
        out_parts.append("")

    if support_lines or payment_bullets:
        out_parts.append("### SUPPORT ###")
        out_parts.extend(support_lines)
        if payment_bullets:
            out_parts.append("Modes de paiement acceptés :")
            out_parts.extend(payment_bullets)
        out_parts.append("")

    return "\n".join(out_parts).strip()


def _build_structured_from_docs(company_id: str, docs: List[Dict[str, Any]] | None) -> Dict[str, List[Dict[str, Any]]]:
    """Construire directement les documents Meilisearch par index à partir des métadonnées.
    - Exploite les champs déjà structurés (products, delivery, support, company, payment)
    - Effectue un léger flattening pour la livraison (price_min/max/currency/raw)
    - Retourne aussi un index combiné (company_docs)
    """
    products: List[Dict[str, Any]] = []
    deliveries: List[Dict[str, Any]] = []
    supports: List[Dict[str, Any]] = []
    companies: List[Dict[str, Any]] = []

    for d in docs or []:
        meta = d.get("metadata", {}) if isinstance(d, dict) else {}
        dtype = (meta.get("type") or meta.get("document_type") or "").lower()

        if dtype == "product":
            prod = {
                "id": meta.get("id") or meta.get("id_slug") or meta.get("document_id") or str(uuid.uuid4()),
                "type": "product",
                "company_id": company_id,
                "product_name": meta.get("product_name") or meta.get("name"),
                "name": meta.get("name") or meta.get("product_name"),
                "description": meta.get("description"),
                "category": meta.get("category"),
                "subcategory": meta.get("subcategory"),
                "color": meta.get("color") or ((meta.get("attributes_canonical") or {}).get("color")),
                "price": meta.get("price"),
                "min_price": meta.get("min_price"),
                "max_price": meta.get("max_price"),
                "stock": meta.get("stock"),
                "total_stock": meta.get("total_stock"),
                "currency": meta.get("currency"),
                "facet_tags": meta.get("facet_tags"),
                "facets": meta.get("facets"),
                "variants": meta.get("variants"),
                "variant_list": meta.get("variant_list"),
                "available_attributes": meta.get("available_attributes"),
                "available_attribute_list": meta.get("available_attribute_list"),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "id_raw": meta.get("id_raw"),
                "id_slug": meta.get("id_slug"),
            }
            products.append(prod)

        elif dtype == "delivery":
            price = meta.get("price") or {}
            delay = meta.get("delay") or {}
            deliveries.append({
                "id": meta.get("id") or meta.get("id_slug") or meta.get("document_id") or str(uuid.uuid4()),
                "type": "delivery",
                "company_id": company_id,
                "zone": meta.get("zone"),
                "zone_slug": meta.get("zone_slug"),
                "zone_group": meta.get("zone_group"),
                "city": meta.get("city"),
                "country": meta.get("country"),
                "group": meta.get("group"),
                # flatten prix
                "price_min": price.get("min"),
                "price_max": price.get("max"),
                "price_currency": price.get("currency"),
                "price_raw": price.get("raw") or (price if isinstance(price, str) else None),
                # flatten délais
                "delay_abidjan": delay.get("abidjan"),
                "delay_hors_abidjan": delay.get("hors_abidjan"),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "id_raw": meta.get("id_raw"),
                "id_slug": meta.get("id_slug"),
            })

        elif dtype == "support":
            supports.append({
                "id": meta.get("id") or meta.get("id_slug") or meta.get("document_id") or str(uuid.uuid4()),
                "type": "support",
                "company_id": company_id,
                "phone_e164": meta.get("phone_e164"),
                "phone_raw": meta.get("phone_raw"),
                "hours": meta.get("hours"),
                "channels": meta.get("channels"),
                "store_type": meta.get("store_type"),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "id_raw": meta.get("id_raw"),
                "id_slug": meta.get("id_slug"),
            })

        elif dtype == "payment":
            supports.append({
                "id": meta.get("id") or meta.get("id_slug") or meta.get("document_id") or str(uuid.uuid4()),
                "type": "payment",
                "company_id": company_id,
                "method": meta.get("method"),
                "details": meta.get("details"),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "id_raw": meta.get("id_raw"),
                "id_slug": meta.get("id_slug"),
            })

        elif dtype == "company":
            companies.append({
                "id": meta.get("id") or meta.get("id_slug") or meta.get("document_id") or "business_identity",
                "type": "company",
                "company_id": company_id,
                "name": meta.get("name"),
                "ai_name": meta.get("ai_name"),
                "sector": meta.get("sector"),
                "description": meta.get("description"),
                "mission": meta.get("mission"),
                "objective": meta.get("objective"),
                "zone": meta.get("zone"),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "id_raw": meta.get("id_raw"),
                "id_slug": meta.get("id_slug"),
            })

    combined = []
    combined.extend(products)
    combined.extend(deliveries)
    combined.extend(supports)
    combined.extend(companies)

    return {
        "products": products,
        "delivery": deliveries,
        "support": supports,
        "company": companies,
        "combined": combined,
    }


@router.post("/ingest-etl")
async def ingest_meili_via_etl(payload: Any = Body(...)):
    try:
        # Supporter un tableau (batch) ou un objet unique
        if isinstance(payload, list):
            if not payload:
                raise HTTPException(status_code=400, detail="Payload batch vide")
            raw_req = payload[0]
        elif isinstance(payload, dict):
            raw_req = payload
        else:
            raise HTTPException(status_code=400, detail="Payload invalide (attendu objet ou tableau)")

        # Valider/convertir vers MeiliETLRequest
        req = MeiliETLRequest(**raw_req)

        data: Dict[str, List[Dict[str, Any]]]
        if req.text_documents:
            # Fast-path: construit directement depuis les métadonnées
            data = _build_structured_from_docs(req.company_id, req.text_documents)
            # Si totalement vide (introuvable), fallback texte -> transform()
            if not any(len(data.get(k, [])) for k in ("products","delivery","support","company")):
                # Construire la source texte et passer par transform()
                raw_text = _normalize_text_from_docs(req.text_documents)
                if not raw_text:
                    parts = []
                    for d in req.text_documents:
                        c = str(d.get("content", ""))
                        c = c.replace("=== ", "### ").replace(" ===", " ###")
                        parts.append(c)
                    raw_text = "\n\n".join(parts)
                data = transform(raw_text)
        elif req.text and isinstance(req.text, str) and req.text.strip():
            data = transform(req.text)
        else:
            raise HTTPException(status_code=400, detail="Fournir 'text' ou 'text_documents'")

        # Purge systématique des indexes dédiés
        import meilisearch
        meili_client = meilisearch.Client(
            os.environ.get("MEILI_URL", "http://127.0.0.1:7700"),
            os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        )
        bases = ["products", "delivery", "support", "company", "company_docs"]
        if req.purge_before:
            for b in bases:
                uid = _safe_uid(b, req.company_id)
                try:
                    meili_client.delete_index(uid)
                    logging.info(f"[MEILI][PURGE] {uid} supprimé")
                except Exception as e:
                    if "index_not_found" not in str(e):
                        logging.warning(f"[MEILI][PURGE] {uid} non supprimé: {e}")

        # Push avec settings dynamiques + synonyms/stopwords
        push_to_meili(data, company_id=req.company_id)

        resp = {
            "status": "ok",
            "company_id": req.company_id,
            "indexes": {b: _safe_uid(b, req.company_id) for b in bases},
            "counts": {
                "products": len(data.get("products", [])),
                "delivery": len(data.get("delivery", [])),
                "support": len(data.get("support", [])),
                "company": len(data.get("company", [])),
                "company_docs": len(data.get("combined", [])),
            },
        }
        logging.info(f"[MEILI][INGEST-ETL] counts={resp['counts']}")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("[MEILI][INGEST-ETL][ERROR]")
        raise HTTPException(status_code=500, detail=str(e))
