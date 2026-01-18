"""
Base Agent - Classe abstrata base para todos os agentes
Segue princípios SOLID (Single Responsibility e Open/Closed)
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
import redis
import json
import hashlib
from datetime import datetime


class BaseAgent(ABC):
    """Classe base abstrata para agentes do sistema"""
    
    def __init__(
        self,
        name: str,
        redis_client: redis.Redis,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ):
        self.name = name
        self.redis_client = redis_client
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.memory_key = f"agent:{name}:memory"
        
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Método principal que cada agente deve implementar"""
        pass
    
    def _save_to_memory(self, data: Dict[str, Any]) -> None:
        """Salva interação na memória do Redis"""
        timestamp = datetime.now().isoformat()
        memory_entry = {
            "timestamp": timestamp,
            "agent": self.name,
            "data": data
        }
        self.redis_client.lpush(
            self.memory_key,
            json.dumps(memory_entry, ensure_ascii=False)
        )
        # Mantém apenas as últimas 100 interações
        self.redis_client.ltrim(self.memory_key, 0, 99)
    
    def _get_memory(self, limit: int = 10) -> list:
        """Recupera memórias do Redis"""
        memories = self.redis_client.lrange(self.memory_key, 0, limit - 1)
        return [json.loads(m.decode('utf-8')) for m in memories]
    
    def _semantic_cache_key(self, query: str) -> str:
        """Gera chave para cache semântico"""
        return f"cache:{self.name}:{hashlib.md5(query.encode()).hexdigest()}"
    
    def _check_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Verifica se existe resultado em cache"""
        cache_key = self._semantic_cache_key(query)
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached.decode('utf-8'))
        return None
    
    def _save_to_cache(self, query: str, result: Dict[str, Any], ttl: int = 3600) -> None:
        """Salva resultado no cache com TTL (padrão: 1 hora)"""
        cache_key = self._semantic_cache_key(query)
        self.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(result, ensure_ascii=False)
        )
    
    def invoke_with_cache(self, query: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Invoca o agente com suporte a cache semântico
        
        Args:
            query: Consulta ou input para o agente
            force_refresh: Se True, ignora cache e força nova execução
        """
        if not force_refresh:
            cached_result = self._check_cache(query)
            if cached_result:
                print(f"✅ Cache hit para agente {self.name}")
                return cached_result
        
        # Executa o agente
        result = self.execute({"query": query})
        
        # Salva no cache
        self._save_to_cache(query, result)
        
        # Salva na memória
        self._save_to_memory({"query": query, "result": result})
        
        return result
