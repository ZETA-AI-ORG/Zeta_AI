def extract_text_documents_from_global_payload(global_payload):
    """
    Convertit un payload global (company_info, products, service_info, etc.) en une liste de text_documents utilisable pour /ingest-text.
    Chaque document extrait aura les champs : content, file_name, metadata.
    """
    text_documents = []
    # Company Info
    if 'company_info' in global_payload:
        ci = global_payload['company_info']
        text_documents.append({
            "content": ci.get("searchable_content", ""),
            "file_name": "company_info.txt",
            "metadata": ci.get("structured_data", {})
        })
    # Products
    for idx, prod in enumerate(global_payload.get('products', [])):
        text_documents.append({
            "content": prod.get("searchable_content", ""),
            "file_name": f"product_{idx}.txt",
            "metadata": prod.get("structured_data", {})
        })
    # Service Info
    if 'service_info' in global_payload:
        si = global_payload['service_info']
        text_documents.append({
            "content": si.get("searchable_content", ""),
            "file_name": "service_info.txt",
            "metadata": si.get("structured_data", {})
        })
    return text_documents

# Exemple d'utilisation :
# global_payload = {...} # ton payload complet
# text_docs = extract_text_documents_from_global_payload(global_payload)
# payload_ingest = {"company_id": "...", "text_documents": text_docs}
