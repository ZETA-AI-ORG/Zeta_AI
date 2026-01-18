import redis
import hashlib
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisCache:
    def __init__(self, url=REDIS_URL, default_ttl=600):
        self.client = redis.Redis.from_url(url)
        self.default_ttl = default_ttl

    def make_key(self, question, company_id, prompt_version, user_id=None):
        user_part = str(user_id or "").strip()
        base = f"{company_id}::{prompt_version}::{user_part}::{question}"
        return f"rag_response::{hashlib.sha256(base.encode('utf-8')).hexdigest()}"

    def make_key_for_context(self, question, company_id):
        base = f"{company_id}::{question}"
        return f"rag_context::{hashlib.sha256(base.encode('utf-8')).hexdigest()}"

    def generic_get(self, key: str):
        val = self.client.get(key)
        if val:
            return json.loads(val)
        return None

    def generic_set(self, key: str, value, ttl=None):
        to_store = json.dumps(value)
        self.client.setex(key, ttl or self.default_ttl, to_store)

    def get(self, question, company_id, prompt_version, user_id=None):
        key = self.make_key(question, company_id, prompt_version, user_id=user_id)
        val = self.client.get(key)
        if val:
            return json.loads(val)
        return None

    def set(self, question, company_id, prompt_version, value, ttl=None, user_id=None):
        key = self.make_key(question, company_id, prompt_version, user_id=user_id)
        to_store = json.dumps(value)
        self.client.setex(key, ttl or self.default_ttl, to_store)

    def flush_all(self):
        self.client.flushdb()
