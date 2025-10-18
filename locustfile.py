from locust import HttpUser, task, between
import random
import uuid

COMPANY_ID = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3abcd"  # company_id fourni par l'utilisateur
USER_IDS = [str(uuid.uuid4()) for _ in range(100)]
MESSAGES = [
    "Bonjour, avez-vous des couches taille 3 ?",
    "Quels sont vos produits en promo ?",
    "Je cherche des conseils pour un bébé qui dort mal.",
    "Avez-vous des lingettes hypoallergéniques ?",
    "Quel est le prix des couches Pampers ?",
    "Quels sont les horaires d'ouverture ?",
    "Puis-je avoir la liste de vos produits pour bébé ?"
]

class ChatbotUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task
    def chat(self):
        user_id = random.choice(USER_IDS)
        message = random.choice(MESSAGES)
        payload = {
            "company_id": COMPANY_ID,
            "user_id": user_id,
            "message": message
        }
        with self.client.post("/chat", json=payload, catch_response=True) as response:
            if response.status_code == 200 and "response" in response.json():
                response.success()
            else:
                response.failure(f"Erreur {response.status_code}: {response.text}")
