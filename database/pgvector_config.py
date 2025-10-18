import os

# Configuration pour la connexion PGVector/PostgreSQL
PG_CONNECTION_STRING = os.getenv("PG_CONNECTION_STRING", "postgresql+psycopg2://user:password@localhost:5432/yourdb")

# Utiliser une variable d'environnement pour la sécurité et la portabilité
# Exemple :
# export PG_CONNECTION_STRING="postgresql+psycopg2://user:password@host:port/dbname"
