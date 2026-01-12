# 📚 Melhores Práticas para Coleta de Informações de Produtos

## ✅ Prática Recomendada: Usar a API Oficial do Mercado Livre

### Por que usar a API?

1. **✅ Legal e Autorizado**
   - A API é o método oficial e aprovado pelo Mercado Livre
   - Evita violação de termos de serviço
   - Garante conformidade legal

2. **✅ Dados Confiáveis e Completos**
   - Informações sempre atualizadas
   - Dados estruturados e consistentes
   - Inclui preços, imagens, variações, estoque, etc.

3. **✅ Performance e Estabilidade**
   - Endpoints otimizados
   - Rate limits documentados
   - Multiget para buscar até 20 produtos por vez

4. **✅ Suporte e Documentação**
   - Documentação completa em português
   - Suporte oficial da plataforma
   - Notificações de mudanças via webhooks

## 🔧 Como Implementar

### 1. Obter Informações de um Produto

```bash
# Usando o ID do produto (MLB-123456789)
curl -X GET "https://api.mercadolibre.com/items/MLB-123456789"
```

**Resposta inclui:**
- ✅ Título
- ✅ Preço atual
- ✅ Preço original (se houver desconto)
- ✅ Imagens em alta resolução
- ✅ Vídeos
- ✅ Atributos e variações
- ✅ Estoque disponível
- ✅ Status do produto

### 2. Buscar Múltiplos Produtos (Multiget)

```bash
# Buscar até 20 produtos de uma vez
curl -X GET "https://api.mercadolibre.com/items?ids=MLB-123,MLB-456,MLB-789"
```

### 3. Selecionar Campos Específicos

```bash
# Retornar apenas campos necessários (mais rápido)
curl -X GET "https://api.mercadolibre.com/items?ids=MLB-123&attributes=id,title,price,pictures"
```

## ⚠️ Web Scraping: Quando e Como

### Quando o scraping é aceitável:

1. **Como fallback** se a API falhar
2. **Para dados públicos** não disponíveis na API
3. **Com respeito** aos termos de serviço

### Boas práticas de scraping:

```python
# 1. Respeitar robots.txt
# 2. Usar User-Agent identificável
headers = {
    'User-Agent': 'SeuApp/1.0 (contato@exemplo.com)'
}

# 3. Implementar rate limiting
import time
time.sleep(1)  # Aguardar entre requisições

# 4. Usar cache para evitar requisições repetidas
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_product_info(product_id):
    # ...

# 5. Tratar erros graciosamente
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    logger.error(f"Erro ao buscar produto: {e}")
    return None
```

## 🎯 Nossa Implementação Atual

### ✅ O que está correto:

1. **Priorizar API** - Tentamos usar a API primeiro
2. **Fallback para HTML** - Usamos scraping apenas se API falhar
3. **User-Agent** - Identificamos nossas requisições
4. **Timeout** - Configuramos timeout de 15 segundos
5. **Tratamento de erros** - Capturamos e logamos exceções

### 🔧 Melhorias Sugeridas:

#### 1. Implementar Sistema de Cache

```python
import redis
from functools import wraps

def cache_product_data(ttl=3600):
    """Cache dados do produto por 1 hora"""
    def decorator(func):
        @wraps(func)
        def wrapper(product_id):
            cache_key = f"product:{product_id}"
            
            # Tentar pegar do cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Buscar e cachear
            result = func(product_id)
            if result:
                redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator
```

#### 2. Rate Limiting Inteligente

```python
from time import time, sleep
from collections import deque

class RateLimiter:
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def wait_if_needed(self):
        now = time()
        
        # Remover requisições antigas
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # Aguardar se atingiu o limite
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                sleep(sleep_time)
        
        self.requests.append(now)
```

#### 3. Retry com Backoff Exponencial

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()
    
    retry = Retry(
        total=3,
        backoff_factor=1,  # 1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session
```

#### 4. Usar API do Mercado Livre Primeiro

```python
def get_product_data(product_id):
    """
    Ordem de prioridade:
    1. Cache (se disponível)
    2. API do Mercado Livre
    3. Scraping HTML (fallback)
    """
    
    # 1. Verificar cache
    cached_data = get_from_cache(product_id)
    if cached_data:
        return cached_data
    
    # 2. Tentar API oficial
    try:
        api_url = f"https://api.mercadolibre.com/items/{product_id}"
        response = session.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            processed_data = process_api_data(data)
            save_to_cache(product_id, processed_data)
            return processed_data
    except Exception as e:
        logger.warning(f"API falhou: {e}")
    
    # 3. Fallback: scraping HTML
    try:
        html_data = scrape_product_page(product_id)
        save_to_cache(product_id, html_data)
        return html_data
    except Exception as e:
        logger.error(f"Scraping falhou: {e}")
        return None
```

## 📊 Comparação: API vs Scraping

| Aspecto | API Oficial | Web Scraping |
|---------|-------------|--------------|
| **Legalidade** | ✅ Autorizado | ⚠️ Depende dos ToS |
| **Confiabilidade** | ✅ Alta | ⚠️ Pode quebrar |
| **Performance** | ✅ Rápido | ❌ Mais lento |
| **Dados Completos** | ✅ Todos os campos | ⚠️ Pode faltar |
| **Manutenção** | ✅ Estável | ❌ Requer updates |
| **Rate Limits** | ✅ Documentado | ❌ Desconhecido |

## 🎯 Recomendação Final

### Para nosso caso (Site de Afiliados):

1. **✅ Usar API como fonte principal**
   - Buscar dados via `https://api.mercadolibre.com/items/{ID}`
   - Cachear resultados por 1-6 horas
   - Atualizar via webhooks quando possível

2. **✅ Scraping apenas como fallback**
   - Quando API retornar erro 404 (produto removido)
   - Para validar dados críticos
   - Com rate limiting apropriado

3. **✅ Implementar webhooks**
   - Receber notificações de mudanças de preço
   - Atualizar dados automaticamente
   - Reduzir chamadas desnecessárias

## 📚 Recursos Úteis

- [Documentação API Mercado Livre](https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br)
- [Itens e Buscas](https://developers.mercadolivre.com.br/pt_br/itens-e-buscas)
- [Webhooks](https://developers.mercadolivre.com.br/pt_br/produto-receba-notificacoes)
- [Boas Práticas](https://developers.mercadolivre.com.br/pt_br/boas-praticas-para-usar-a-plataforma)

## 🔒 Considerações de Segurança

1. **Não armazenar tokens em código**
2. **Usar variáveis de ambiente**
3. **Implementar rate limiting**
4. **Respeitar robots.txt**
5. **Identificar seu User-Agent**
6. **Cachear para reduzir requisições**

## ⚡ Próximos Passos

1. ✅ Implementar cache Redis/local
2. ✅ Migrar para API como fonte principal
3. ✅ Adicionar retry com backoff exponencial
4. ✅ Implementar webhooks para atualizações
5. ✅ Monitorar rate limits e erros
