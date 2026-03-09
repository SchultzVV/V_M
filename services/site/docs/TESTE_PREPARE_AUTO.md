# 🧪 Como Testar o `make prepare-auto`

## ✅ Links Válidos

O comando funciona com os seguintes tipos de links do Mercado Livre:

### 1. Link direto do produto
```bash
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-1234567890-nome-do-produto"
```

### 2. Link curto de afiliado (que redireciona para um produto)
```bash
make prepare-auto URL="https://mercadolivre.com/sec/ABC123"
```

### 3. Link com permalink
```bash
make prepare-auto URL="https://www.mercadolivre.com.br/p/MLB1234567890"
```

## ❌ Links Inválidos

Estes tipos de links **NÃO funcionam**:

- ❌ Links de perfil de vendedor: `https://www.mercadolivre.com.br/social/usuario`
- ❌ Links de busca: `https://lista.mercadolivre.com.br/...`
- ❌ Links expirados de afiliado

## 🔍 Como Obter um Link Válido

### Opção 1: Da página do produto
1. Acesse qualquer produto no Mercado Livre
2. Copie a URL da barra de endereços
3. Use no comando

### Opção 2: Criar link de afiliado
1. Entre no [Mercado Livre Afiliados](https://www.mercadolivre.com.br/afiliados)
2. Busque um produto
3. Clique em "Gerar link"
4. Use o link gerado

## 📝 Exemplo Completo

```bash
# 1. Preparar produto
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-3712345678-airfryer-philips-5l"

# Saída esperada:
# 🔗 Seguindo link de afiliado...
#    URL inicial: https://produto.mercadolivre.com.br/MLB-3712345678-...
#    URL final: https://produto.mercadolivre.com.br/MLB-3712345678-...
# 
# 🆔 ID do produto encontrado: MLB-3712345678
# 🌐 Consultando API do Mercado Livre...
# 
# ✅ Dados obtidos com sucesso via API!
# 📦 Produto: Airfryer Philips 5L...
# 💰 Preço: R$ 599.90
# 🖼️  Imagens encontradas: 8
#
# 📥 Baixando 8 imagens...
#   ✅ img_01.jpg (234.5 KB)
#   ...
#
# 🏷️  ESCOLHA A CATEGORIA DO PRODUTO
# ...

# 2. Publicar no site
make stage
```

## 🐛 Troubleshooting

### Erro: "redirecionou para um perfil de vendedor"
**Causa:** O link é de um vendedor, não de um produto específico.  
**Solução:** Use um link direto do produto.

### Erro: "Não foi possível extrair o ID do produto"
**Causa:** O link pode estar mal formatado ou expirado.  
**Solução:** Use um link direto do produto da página.

### Erro: "404 Not Found"
**Causa:** O produto foi removido ou o link expirou.  
**Solução:** Busque o produto novamente no Mercado Livre e use o novo link.
