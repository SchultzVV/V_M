import os
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory

# Redis config from .env
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

def get_conversation_memory(session_id: str):
    """Cria memória persistente usando Redis para uma sessão de conversa"""
    history = RedisChatMessageHistory(
        url=REDIS_URL,
        session_id=session_id,
    )
    memory = ConversationBufferMemory(
        chat_memory=history,
        memory_key="chat_history",
        input_key="question",
        return_messages=True
    )
    return memory
