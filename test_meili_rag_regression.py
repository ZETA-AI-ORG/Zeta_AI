import requests
import json

COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser313"
CHAT_URL = "http://127.0.0.1:8001/chat"

QUESTIONS = [
    # Test 1: Produit unique, prix unique (culottes toutes tailles)
    "Quel est le prix d'un lot de 150 couches culottes taille 5 ?",
    # Test 2: Produit à variantes, taille numérique spécifique
    "Prix d’un lot de 300 couches à pression taille 4 ?",
    # Test 3: Question piégeuse, mélange de mots-clés et de quantités
    "Combien coûtent 300 couches culottes pour un bébé de 11kg ?"
]

def ask_question(question):
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": question
    }
    resp = requests.post(CHAT_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text}
    print(f"\n=== QUESTION: {question}\n--- RÉPONSE: {json.dumps(result, indent=2, ensure_ascii=False)}\n")

if __name__ == "__main__":
    for q in QUESTIONS:
        ask_question(q)
