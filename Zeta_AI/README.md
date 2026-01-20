# CHATBOT2.0 – RAG LLM Multi-Entreprise 🤖

Système de chatbot intelligent avec pipeline RAG hybride, HyDE structuré et ingestion automatisée.

## 🛡️ SYSTÈME ANTI-DÉRIVE IA ACTIVÉ

Ce projet utilise un **système de protection contre les modifications IA non contrôlées** (Windsurf, Cursor, etc.).

📚 **Lire le guide complet**: [GUIDE_ANTI_DERIVE_IA.md](./GUIDE_ANTI_DERIVE_IA.md)

### 🔄 Routine Quotidienne

```powershell
# Avant session IA
powershell ./scripts/auto_backup.ps1
git checkout ia

# Après session IA
powershell ./scripts/check_ia_changes.ps1
```

### 🌳 Branches

- **main** → Production (protégée)
- **dev** → Développement manuel
- **ia** → Zone de travail IA (Windsurf/Cursor)

## Lancement rapide

1. **Installer les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

2. **Lancer l'API :**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Tester le chatbot :**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
        -H "Content-Type: application/json" \
        -d '{"company_id":"test", "user_id":"user1", "message":"Bonjour"}'
   ```

## Architecture

```
CHATBOT2.0/
├── app.py                    # API FastAPI principale
├── config.py                 # Configuration centralisée
├── requirements.txt          # Dépendances Python
├── utils.py                  # Fonctions utilitaires
├── core/                     # Logique métier
│   ├── models.py            # Modèles Pydantic
│   ├── rag_engine.py        # Pipeline RAG + HyDE
│   ├── llm_client.py        # Client Grok API
│   ├── preprocessing.py     # Preprocessing universel
│   ├── conversation.py      # Historique conversationnel
│   └── structured_hyde.py   # HyDE structuré multi-hypothèses
├── database/                 # Accès aux données
│   ├── supabase_client.py   # Client Supabase/PGVector
│   └── vector_store.py      # Client Meilisearch
└── ingestion/               # Système d'ingestion
    ├── ingestion_pipeline.py # Pipeline complet
    ├── ingestion_api.py     # API REST d'ingestion
    └── batch_ingestion.py   # Ingestion en lot
```

## Fonctionnalités

### Pipeline RAG Hybride
- **Recherche textuelle** : Meilisearch (mots-clés)
- **Recherche sémantique** : Supabase/PGVector (embeddings 768d)
- **HyDE structuré** : Génération multi-hypothèses avec scoring
- **Fusion contextuelle** : Combinaison intelligente des résultats

### Système d'ingestion
- **Pipeline automatisé** : Découpage Markdown + embeddings
- **API REST complète** : Endpoints d'ingestion, suppression, réindexation
- **Ingestion en lot** : Traitement de fichiers/répertoires
- **Configurations prédéfinies** : Par type de document

### Gestion conversationnelle
- **Historique persistant** : Stockage Supabase
- **Contexte dynamique** : Récupération automatique
- **Multi-entreprise** : Isolation par company_id

## API Endpoints

### Chat
- `POST /chat` - Conversation avec le chatbot

### Ingestion
- `POST /ingestion/ingest` - Ingérer un document
- `DELETE /ingestion/clear` - Supprimer données entreprise
- `POST /ingestion/reindex` - Réindexer complètement
- `GET /ingestion/status/{company_id}` - Vérifier le statut

## Configuration

Variables d'environnement requises (fichier `.env`) :

```env
# Grok API
GROK_API_KEY=gsk_...

# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...

# Meilisearch
MEILI_URL=http://localhost:7700
MEILI_API_KEY=...
```

## Tests

### Test du pipeline RAG
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"company_id":"XkCn8fjNWEWwqiiKMgJX7OcQrUJ3", "user_id":"test", "message":"Quels sont vos produits ?"}'
```

### Test d'ingestion
```bash
curl -X POST "http://localhost:8000/ingestion/ingest" \
     -H "Content-Type: application/json" \
     -d '{"company_id":"test", "markdown_content":"# Produits\n\nNous vendons des couches."}'
```

## Monitoring

- **Logs structurés** : Traçabilité complète de la pipeline
- **Métriques** : Temps de réponse, scores de pertinence
- **Statut d'ingestion** : Vérification de l'état des données

## Production

1. **Sécurité** : Vérifier les clés API et CORS
2. **Performance** : Configurer le cache et la limitation de taux
3. **Monitoring** : Logs centralisés et alertes
4. **Backup** : Sauvegarde automatique des données