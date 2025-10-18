from qdrant_client import QdrantClient

# Adapter la dimension à ton embedding CLIP (512 ou 768)
VECTOR_SIZE = 512  # Modifie à 768 si tu utilises open-clip ViT-B-32

client = QdrantClient("localhost", port=6333)
client.recreate_collection(
    collection_name="product_images",
    vectors_config={
        "size": VECTOR_SIZE,
        "distance": "Cosine"
    }
)
print(f"Collection 'product_images' créée avec succès (dimension: {VECTOR_SIZE}) !")
