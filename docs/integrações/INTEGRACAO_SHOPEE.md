# 🛍️ Integração com Shopee - Guia Completo

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Diferenças entre API Oficial e Scraping](#diferenças-entre-api-oficial-e-scraping)
3. [Como Usar](#como-usar)
4. [Exemplos de URLs Suportadas](#exemplos-de-urls-suportadas)
5. [Dados Coletados](#dados-coletados)
6. [Troubleshooting](#troubleshooting)
7. [Roadmap: API Oficial](#roadmap-api-oficial)

---

## Visão Geral

Este guia explica como integrar produtos da Shopee ao seu sistema, similar à integração existente com o Mercado Livre.

**Status Atual:**
- ✅ **Scraping via HTML**: Totalmente funcional
- ⏳ **API Oficial**: Planejado para vendedores autorizados

**Comando Principal:**
```bash
make shopee-prepare-product URL="https://shopee.com.br/produto/..."
```

---

## Diferenças entre API Oficial e Scraping

### 🔄 Scraping (Implementado)

**Vantagens:**
- ✅ Funciona com **qualquer produto** da Shopee
- ✅ Não requer autenticação ou credenciais
- ✅ Suporta **links de afiliado**
- ✅ Rápido para testar e usar
- ✅ Não há limites de requisições (uso moderado)

**Limitações:**
- ⚠️ Depende da estrutura HTML da página
- ⚠️ Pode quebrar se a Shopee mudar o layout
- ⚠️ Dados podem estar desatualizados (cache do site)

### 🔑 API Oficial (Não Implementado)

**Vantagens:**
- ✅ Dados sempre atualizados em tempo real
- ✅ Suporte oficial da Shopee
- ✅ Acesso a dados adicionais (pedidos, estatísticas, etc.)
- ✅ Webhooks para notificações automáticas

**Requisitos:**
- 🔒 Ser **vendedor registrado** na Shopee
- 🔒 Registrar aplicação no [Shopee Open Platform](https://open.shopee.com)
- 🔒 Obter **Partner ID** e **Partner Key**
- 🔒 Autorização OAuth por loja (Shop Authorization)

**Limitações:**
- ❌ Só funciona com **seus próprios produtos**
- ❌ Processo de aprovação complexo
- ❌ Requer shop_id e item_id específicos

---

## Como Usar

### Pré-requisitos

1. **Container Docker rodando:**
   ```bash
   docker-compose up -d
   ```

2. **Dependências Python instaladas** (já incluídas no Dockerfile):
   - requests
   - beautifulsoup4
   - python-slugify

### Preparar Produto da Shopee

**Sintaxe:**
```bash
make shopee-prepare-product URL="<URL_DO_PRODUTO>"
```

**Exemplo Real:**
```bash
make shopee-prepare-product URL="https://shopee.com.br/Smartphone-Samsung-Galaxy-A54-5G-256GB-i.123456.7890123456"
```

**Fluxo de Execução:**
1. 🔗 Resolve links de afiliado ou encurtados
2. 🔍 Extrai shop_id e item_id da URL
3. 📥 Faz scraping da página do produto
4. 📊 Extrai dados completos (título, preço, estoque, avaliações, imagens)
5. 🖼️ Baixa todas as imagens em alta qualidade
6. 💾 Gera JSON no formato padrão do sistema
7. ✅ Salva em `list_to_prepare_and_stage/`

---

## Exemplos de URLs Suportadas

### ✅ URLs Válidas

**Formato 1: URL Direta**
```
https://shopee.com.br/product/123456/7890123456
```

**Formato 2: URL com Nome do Produto**
```
https://shopee.com.br/Smartphone-Samsung-Galaxy-A54-5G-256GB-i.123456.7890123456
```

**Formato 3: Link Encurtado**
```
https://shope.ee/ABC123
```

**Formato 4: Link de Afiliado**
```
https://s.shopee.com.br/xyz789
```

### ❌ URLs Não Suportadas

- Links de categorias: `https://shopee.com.br/Eletronicos-cat.123`
- Links de busca: `https://shopee.com.br/search?keyword=celular`
- Links de lojas: `https://shopee.com.br/shop/123456`

---

## Dados Coletados

O script coleta as seguintes informações do produto:

### 📦 Informações Básicas
```json
{
  "nome_produto": "Smartphone Samsung Galaxy A54 5G 256GB",
  "descricao": "Smartphone com câmera de 50MP, tela Super AMOLED...",
  "categoria": "geral",
  "condicao": "new",
  "origem": "shopee"
}
```

### 💰 Preços e Descontos
```json
{
  "preco": 1799.99,
  "preco_original": 2499.99,
  "desconto_percentual": 28.0
}
```

### 📊 Estoque e Vendas
```json
{
  "estoque": 156,
  "vendidos": 2543
}
```

### ⭐ Avaliações
```json
{
  "avaliacao": 4.8,
  "total_avaliacoes": 1256
}
```

### 🔗 Metadados
```json
{
  "shop_id": "123456",
  "item_id": "7890123456",
  "link_original": "https://shopee.com.br/...",
  "pasta_imagens": "/app/uploads/smartphone-samsung-galaxy-a54",
  "timestamp": "20260122_143052",
  "data_coleta": "2026-01-22T14:30:52.123456"
}
```

---

## Troubleshooting

### ❌ Erro: "Não foi possível coletar dados do produto"

**Possíveis Causas:**
1. URL incorreta ou produto inexistente
2. Produto removido/esgotado
3. Estrutura HTML da Shopee mudou
4. Bloqueio por rate limiting

**Soluções:**
```bash
# 1. Verifique se a URL está correta
curl -I "https://shopee.com.br/product/123456/7890123456"

# 2. Tente acessar manualmente no navegador

# 3. Verifique os logs do container
docker logs site | grep -i shopee

# 4. Execute o script diretamente para debug
docker exec -it site python3 scripts/shopee_prepare.py "URL"
```

### ⚠️ Imagens não baixadas

**Causa:** URLs de imagem inválidas ou timeout

**Solução:**
```bash
# Verifique conectividade com CDN da Shopee
curl -I "https://cf.shopee.com.br/file/..."

# Aumente o timeout no script (se necessário)
# Editar: services/site/scripts/shopee_prepare.py
# Linha: response = requests.get(img_url, timeout=15)
# Alterar para: timeout=30
```

### 🐛 JSON não criado

**Causa:** Permissões ou diretório inexistente

**Solução:**
```bash
# Verificar permissões
docker exec site ls -la /app/list_to_prepare_and_stage/

# Criar diretório se não existir
docker exec site mkdir -p /app/list_to_prepare_and_stage/

# Verificar logs
docker exec site tail -f /app/logs/shopee_prepare.log
```

---

## Roadmap: API Oficial

Para implementar a API oficial da Shopee no futuro:

### 1️⃣ Registrar como Partner

1. Acesse: **https://open.shopee.com/developer-guide/4**
2. Crie conta no Shopee Open Platform
3. Registre sua aplicação
4. Aguarde aprovação

### 2️⃣ Obter Credenciais

Após aprovação, você receberá:
```env
SHOPEE_PARTNER_ID=123456
SHOPEE_PARTNER_KEY=abc123def456...
SHOPEE_REDIRECT_URI=https://seu-dominio.com/auth/shopee/callback
```

### 3️⃣ Implementar Autenticação

**Fluxo OAuth 2.0 da Shopee:**
```
1. Usuário → Shop Authorization URL
   ↓
2. Shopee → Tela de autorização
   ↓
3. Usuário → Autoriza a aplicação
   ↓
4. Shopee → Redireciona com code + shop_id
   ↓
5. Backend → Troca code por access_token
   ↓
6. Sistema → Salva tokens
```

**URL de Autorização:**
```
https://partner.shopeemobile.com/api/v2/shop/auth_partner
?partner_id={PARTNER_ID}
&redirect={REDIRECT_URI}
&sign={HMAC_SHA256_SIGNATURE}
&timestamp={UNIX_TIMESTAMP}
```

### 4️⃣ Endpoints Disponíveis

**Listar Produtos:**
```bash
GET /api/v2/product/get_item_list
```

**Detalhes do Produto:**
```bash
GET /api/v2/product/get_item_base_info
```

**Parâmetros Comuns:**
- `partner_id`: ID do partner
- `timestamp`: Unix timestamp (válido por 5 minutos)
- `access_token`: Token OAuth
- `shop_id`: ID da loja autorizada
- `sign`: Assinatura HMAC-SHA256

### 5️⃣ Geração de Assinatura

```python
import hmac
import hashlib
import time

def generate_sign(partner_id, api_path, timestamp, access_token, shop_id, partner_key):
    """
    Gera assinatura HMAC-SHA256 para requisições da Shopee API.
    """
    # Concatenar parâmetros na ordem específica
    base_string = f"{partner_id}{api_path}{timestamp}{access_token}{shop_id}"
    
    # Calcular HMAC-SHA256
    signature = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

# Exemplo de uso
partner_id = 123456
api_path = '/api/v2/product/get_item_list'
timestamp = int(time.time())
access_token = 'abc123...'
shop_id = 600000
partner_key = 'your_partner_key'

sign = generate_sign(partner_id, api_path, timestamp, access_token, shop_id, partner_key)
```

---

## Comparação: Shopee vs Mercado Livre

| Recurso | Mercado Livre | Shopee |
|---------|---------------|--------|
| **Scraping** | ✅ Funcional | ✅ Funcional |
| **API Oficial** | ✅ Implementado | ⏳ Planejado |
| **OAuth** | ✅ Sim | ⏳ Futuro |
| **Webhooks** | ✅ Sim | ⏳ Futuro |
| **Links de Afiliado** | ✅ Sim | ✅ Sim |
| **Dados em Tempo Real** | ✅ Via API | 🔄 Via Scraping |
| **Complexidade** | Média | Baixa (scraping) / Alta (API) |

---

## Exemplos de Uso Completo

### Exemplo 1: Produto Individual

```bash
# Preparar produto da Shopee
make shopee-prepare-product URL="https://shopee.com.br/Notebook-Dell-i.123.456"

# Verificar JSON gerado
cat services/site/list_to_prepare_and_stage/notebook-dell_*.json

# Ver imagens baixadas
ls -lh services/site/uploads/notebook-dell/
```

### Exemplo 2: Múltiplos Produtos

```bash
# Criar lista de URLs
cat > shopee_urls.txt << EOF
https://shopee.com.br/produto1
https://shopee.com.br/produto2
https://shopee.com.br/produto3
EOF

# Processar em lote
while read url; do
  make shopee-prepare-product URL="$url"
  sleep 2  # Evitar rate limiting
done < shopee_urls.txt
```

### Exemplo 3: Integração com Pipeline

```bash
# 1. Preparar produto
make shopee-prepare-product URL="https://shopee.com.br/produto"

# 2. Enviar para staging
make stage-products

# 3. Gerar postagem Instagram
make instagram-auto-post
```

---

## Limitações e Boas Práticas

### ⚠️ Limitações

1. **Rate Limiting**: Evite fazer muitas requisições em curto período
2. **Estrutura HTML**: Pode mudar sem aviso prévio
3. **Dados Dinâmicos**: Alguns dados carregam via JavaScript assíncrono
4. **Geolocalização**: Preços podem variar por região

### ✅ Boas Práticas

1. **Intervalo entre requisições**: Aguarde 2-5 segundos entre produtos
2. **User-Agent realista**: Use headers de navegador real
3. **Tratamento de erros**: Sempre validar dados coletados
4. **Backup de estrutura**: Manter múltiplas estratégias de parsing
5. **Logs detalhados**: Registrar sucessos e falhas

---

## Suporte e Contribuição

### 📚 Documentação Oficial

- [Shopee Open Platform](https://open.shopee.com)
- [API Documentation](https://open.shopee.com/documents)
- [Developer Guide](https://open.shopee.com/developer-guide)
- [FAQ](https://open.shopee.com/faq)

### 🐛 Reportar Problemas

Se encontrar bugs ou tiver sugestões:
1. Verifique os logs: `docker logs site | grep shopee`
2. Teste manualmente a URL no navegador
3. Abra uma issue com detalhes completos

### 🤝 Contribuir

Para contribuir com melhorias:
1. Fork o repositório
2. Crie branch: `git checkout -b feature/shopee-improvement`
3. Commit: `git commit -m "Melhoria no scraping da Shopee"`
4. Push: `git push origin feature/shopee-improvement`
5. Abra Pull Request

---

## Resumo Rápido

**Para usar agora (Scraping):**
```bash
make shopee-prepare-product URL="https://shopee.com.br/produto/123/456"
```

**Para usar no futuro (API Oficial):**
1. Registrar no Shopee Open Platform
2. Obter Partner ID e Partner Key
3. Implementar OAuth e assinatura HMAC
4. Usar endpoints oficiais

**Diferença principal:**
- **Scraping**: Qualquer produto, sem autenticação ✅
- **API**: Apenas seus produtos, requer autorização 🔐

---

**🎉 Integração com Shopee implementada com sucesso via scraping!**
