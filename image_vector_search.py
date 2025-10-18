import open_clip
import torch
from PIL import Image
from qdrant_client import QdrantClient

# Initialisation du modèle CLIP
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')

def get_image_embedding(image_path):
    image = preprocess(Image.open(image_path)).unsqueeze(0)
    with torch.no_grad():
        embedding = model.encode_image(image)
    return embedding.cpu().numpy().flatten()

client = QdrantClient("localhost", port=6333)

def index_image(image_path, product_id, product_name):
    vec = get_image_embedding(image_path)
    client.upsert(
        collection_name="products",
        points=[{"id": product_id, "vector": vec, "payload": {"name": product_name}}]
    )
    print(f"Image {image_path} indexée avec l'id {product_id} et le nom '{product_name}'.")

def search_similar(image_path, top_k=5):
    vec = get_image_embedding(image_path)
    hits = client.search(collection_name="products", query_vector=vec, limit=top_k)
    print(f"Résultats similaires pour {image_path} :")
    for hit in hits:
        print(f"- {hit.payload['name']} (score: {hit.score:.4f})")
    return hits

if __name__ == "__main__":
    # Exemple d'utilisation
    # 1. Indexer des images
    index_image("images/casque1.jpg", 1, "Casque Moto Rouge")
    index_image("images/casque2.jpg", 2, "Casque Moto Bleu")
    index_image("images/tshirt1.jpg", 3, "T-shirt Blanc")

    # 2. Rechercher par similarité
    search_similar("images/casque_test.jpg", top_k=3)
