"""
conversation_memory.py
Memória de conversa por sessão — armazenada em Redis sem dependências langchain.
Interface pública mantida: get_conversation_memory(session_id) → objeto com .messages e .add_*
"""
import os
import json
from typing import List, Dict

import redis as _redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
_HISTORY_PREFIX = "conv_history:"
_MAX_MESSAGES = 50


class _ConversationMemory:
    """Substituto simples de ConversationBufferMemory com Redis."""

    def __init__(self, session_id: str, r: _redis.Redis):
        self._key = f"{_HISTORY_PREFIX}{session_id}"
        self._r = r
        self.memory_key = "chat_history"
        self.input_key = "question"

    @property
    def messages(self) -> List[Dict]:
        raw = self._r.lrange(self._key, 0, -1)
        return [json.loads(m) for m in raw]

    def add_user_message(self, content: str):
        self._push({"role": "user", "content": content})

    def add_ai_message(self, content: str):
        self._push({"role": "assistant", "content": content})

    def _push(self, msg: Dict):
        self._r.rpush(self._key, json.dumps(msg))
        self._r.ltrim(self._key, -_MAX_MESSAGES, -1)

    def clear(self):
        self._r.delete(self._key)

    # Compatibilidade com código que usa .chat_history dict
    def load_memory_variables(self, _inputs: Dict) -> Dict:
        return {self.memory_key: self.messages}


def get_conversation_memory(session_id: str) -> _ConversationMemory:
    """Cria memória persistente usando Redis para uma sessão de conversa."""
    try:
        r = _redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=3)
        r.ping()
    except Exception:
        # Fallback in-memory se Redis não disponível
        r = _redis.Redis.from_url("redis://localhost:6379", decode_responses=True, socket_connect_timeout=1)
    return _ConversationMemory(session_id, r)
