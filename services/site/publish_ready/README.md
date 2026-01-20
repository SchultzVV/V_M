# 🎨 Imagens Prontas para Publicação no Instagram

Este diretório contém imagens geradas automaticamente a partir dos produtos do staging, prontas para publicação manual no Instagram.

## 📸 Características das Imagens

✅ **Formato**: 1080x1080px (padrão Instagram)  
✅ **Qualidade**: JPEG 95%  
✅ **Encoding**: UTF-8 completo (todos os acentos corretos)  
✅ **QR Code**: Link direto para compra do produto  

## 🎯 Layout das Imagens

Cada imagem contém:

1. **Cabeçalho** (180px)
   - Título do produto (até 3 linhas)
   - Fundo com gradiente suave

2. **Imagem do Produto** (500px)
   - Segunda imagem do MinIO (fallback: primeira imagem ou local)
   - Centralizada com borda
   - Dimensionada proporcionalmente

3. **Seção de Preço** (120px)
   - Preço antigo (riscado)
   - Preço atual em destaque verde

4. **Informações + QR Code** (200px)
   - Plataforma de origem
   - Categoria/Tag
   - QR Code escaneável
   - Link encurtado

5. **Rodapé com CTA** (80px)
   - Call-to-action: "GARANTA JÁ O SEU! 🛒"

## 🚀 Como Usar

### Gerar Imagens

```bash
# Gerar imagens de todos os produtos do staging
make prepare-publish

# Ou dentro do container
docker exec -it site python3 scripts/prepare_publish_images.py --all
```

### Publicar no Instagram

1. Acesse a pasta `publish_ready/`
2. Escolha a(s) imagem(ns) desejada(s)
3. Faça upload manual no Instagram
4. **Dica**: Use o QR code no post - seguidores podem escanear para comprar!

## 📝 Formato do Nome dos Arquivos

```
{slug-do-produto}_{data-staging}_{data-geracao}.jpg
```

Exemplo:
```
iphone-16e-128-gb-branco_20260113_212310_20260120_175927.jpg
```

## 🔄 Atualização

As imagens são geradas sob demanda. Para regerar:

```bash
# Limpar imagens antigas
docker exec -it site rm -f publish_ready/*.jpg

# Gerar novas
make prepare-publish
```

## 🎨 Customização

Para ajustar o layout, edite:
```
services/site/scripts/prepare_publish_images.py
```

Principais configurações:
- `IMG_SIZE`: Dimensões da imagem (padrão 1080x1080)
- `COLOR_*`: Paleta de cores
- Seções individuais: `_add_header()`, `_add_product_image()`, etc.
