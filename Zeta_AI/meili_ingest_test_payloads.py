# Test payloads for /meili/ingest endpoint
# These are ready-to-use examples for manual or automated testing

# 1. n8n-style object (dict) payload
n8n_dict_payload = {
    "company_id": "test_company_1",
    "docs": {
        "doc1": {"id": "doc1", "content": "Document 1 content", "metadata": {"type": "faq"}},
        "doc2": {"id": "doc2", "content": "Document 2 content", "metadata": {"type": "info"}}
    }
}

# 2. Standard list payload
standard_list_payload = {
    "company_id": "test_company_2",
    "docs": [
        {"id": "doc3", "content": "Document 3 content", "metadata": {"type": "faq"}},
        {"id": "doc4", "content": "Document 4 content", "metadata": {"type": "info"}}
    ]
}

# 3. Minimal valid payload (list)
minimal_list_payload = {
    "company_id": "test_company_3",
    "docs": [
        {"content": "Minimal doc content"}
    ]
}

# 4. Minimal valid payload (dict)
minimal_dict_payload = {
    "company_id": "test_company_4",
    "docs": {
        "doc5": {"content": "Minimal doc content"}
    }
}

# Save as JSON for curl/postman/manual tests
import json
with open("meili_ingest_test_payloads.json", "w", encoding="utf-8") as f:
    json.dump({
        "n8n_dict_payload": n8n_dict_payload,
        "standard_list_payload": standard_list_payload,
        "minimal_list_payload": minimal_list_payload,
        "minimal_dict_payload": minimal_dict_payload
    }, f, ensure_ascii=False, indent=2)
