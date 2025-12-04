import os
from dotenv import load_dotenv

# Charge explicitement le fichier .env du projet (racine de CHATBOT2.0)
# Cela évite les erreurs lorsque le CWD ne pointe pas sur la racine du projet
_ROOT_DIR = os.path.dirname(__file__)
_ENV_PATH = os.path.join(_ROOT_DIR, ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# Variables d'environnement principales
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
MEILI_URL = os.getenv('MEILI_URL')
MEILI_API_KEY = os.getenv('MEILI_API_KEY')  # Utilise MEILI_API_KEY du .env (standard Meilisearch)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')  # GROQ (pas GROK) dans le .env
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"  # URL fixe Groq
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Log concis pour confirmer le chargement des clés Supabase
try:
    _sk = SUPABASE_KEY or ''
    _sk_masked = (_sk[:4] + "..." + _sk[-2:]) if len(_sk) >= 6 else ("set" if _sk else "empty")
    logger.info(f"[ENV] Loaded .env | SUPABASE_URL={SUPABASE_URL} | SUPABASE_KEY={_sk_masked}")
except Exception:
    pass

# Variables Google/Firebase
GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID')
GOOGLE_PRIVATE_KEY = os.getenv('GOOGLE_PRIVATE_KEY')
GOOGLE_CLIENT_EMAIL = os.getenv('GOOGLE_CLIENT_EMAIL')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

# Compatibilité avec l'ancien code (alias)
GROK_API_KEY = GROQ_API_KEY  # Alias pour compatibilité
GROK_API_URL = GROQ_API_URL  # Alias pour compatibilité

# Configuration Firebase
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH', 'serviceAccountKey.json')

# Chaîne de connexion PostgreSQL
PG_CONNECTION_STRING = os.getenv('PG_CONNECTION_STRING')

# Logger par défaut (fallback)
import logging
logger = logging.getLogger("chatbot_default")

# Log concis pour confirmer le chargement de l'environnement Meilisearch
try:
    _mk = os.getenv('MEILI_API_KEY') or os.getenv('MEILI_MASTER_KEY') or ''
    _mk_masked = (_mk[:4] + "..." + _mk[-2:]) if len(_mk) >= 6 else ("set" if _mk else "empty")
    logger.info(f"[ENV] Loaded .env at {_ENV_PATH} | MEILI_URL={MEILI_URL} | MEILI_KEY={_mk_masked}")
except Exception:
    pass

# Clé maître Meilisearch (fallback) - DÉJÀ DÉFINIE CI-DESSUS
# MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY', MEILI_API_KEY)

# Nom de l'embedder Meilisearch (fallback)
MEILI_EMBEDDER_NAME = os.getenv('MEILI_EMBEDDER_NAME', '')

# Modèle Hugging Face Meilisearch (fallback)
MEILI_HUGGING_FACE_MODEL = os.getenv('MEILI_HUGGING_FACE_MODEL', '')

# Variables Messenger
MESSENGER_VERIFY_TOKEN = os.getenv('MESSENGER_VERIFY_TOKEN')
MESSENGER_APP_SECRET = os.getenv('MESSENGER_APP_SECRET')
MESSENGER_ACCESS_TOKEN = os.getenv('MESSENGER_ACCESS_TOKEN')

# Variables N8N
N8N_OUTBOUND_WEBHOOK_URL = os.getenv('N8N_OUTBOUND_WEBHOOK_URL')
N8N_API_KEY = os.getenv('N8N_API_KEY')
N8N_PRODUCTION_WEBHOOK_URL_FIXE = os.getenv('N8N_PRODUCTION_WEBHOOK_URL_FIXE')
N8N_TEST_WEBHOOK_URL_FIXE = os.getenv('N8N_TEST_WEBHOOK_URL_FIXE')
N8N_DEBUG_MODE = os.getenv('N8N_DEBUG_MODE', 'False').lower() == 'true'

# Variables Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Variable pour sécuriser les webhooks
WEBHOOK_CLIENT_ID_SECRET = os.getenv('WEBHOOK_CLIENT_ID_SECRET')

# WhatsApp Cloud API (Meta)
WHATSAPP_API_BASE = os.getenv('WHATSAPP_API_BASE', 'https://graph.facebook.com/v19.0')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
WHATSAPP_AUTO_REPLY_ENABLED = os.getenv('WHATSAPP_AUTO_REPLY_ENABLED', 'false').lower() == 'true'
WHATSAPP_DEFAULT_COMPANY_ID = os.getenv('WHATSAPP_DEFAULT_COMPANY_ID', 'default')