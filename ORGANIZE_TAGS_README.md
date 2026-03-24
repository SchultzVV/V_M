# 🏷️ Comando `make organize-tags` 

## O que faz?

Reorganiza os **tags/categorias** dos produtos no `staging` baseado nas palavras-chave do **título** do produto.

### Fluxo:
1. **Lê** todos os arquivos JSON em `/app/staging`
2. **Detecta** a categoria ideal analisando o título (PET, E, CD, ME, ou geral)
3. **Move** o arquivo para a pasta correta
4. **Atualiza** o JSON com a tag correta

---

## Uso

### ⭐ Modo Interativo (padrão)
```bash
make organize-tags
```
**Comportamento:**
- Detecta categoria automaticamente se a confiança > 80%
- Para produtos com baixa confiança (< 80%), **pergunta ao usuário**:
  1. Mostra o título e as informações do produto
  2. Lista as categorias disponíveis
  3. Também pergunta qual subcategoria (brinquedos, caes, gatos, etc)
  4. Move o produto para o local correto

**Exemplo de interação:**
```
❓ INCERTO: E (50%)

────────────────────────────────────────────────────────────
📦 produto_20260312.json
   Localização: eletronicos/smartphone-samsung.json
   Título: Samsung Galaxy S24 com casinha para gato
   Tag atual: geral

🏷️  ESCOLHA A CATEGORIA DO PRODUTO
=====================================
📋 Categorias disponíveis:
  1. PET - PetShop
  2. E - Eletrônicos
  3. CD - Casa & Decoração
  4. ME - Moda & Estilo
  5. geral - Categoria Geral

💡 Sugestão baseada no título: E (opção 2)

Digite o número da categoria [Enter para usar a sugestão]: 
```

### 🤖 Modo Automático
```bash
make organize-tags-auto
```
**Comportamento:**
- Apenas move produtos com **confiança alta (≥ 80%)**
- Não pergunta nada, é silencioso
- Produtos com baixa confiança são **pulados** (permanecem onde estão)
- Útil para **reorganizar rapidamente** apenas os produtos óbvios

---

## Fluxo Recomendado (antes de `make stage`)

```bash
# 1️⃣  Prepara os produtos (detecta dados + OCR + imagens)
make prepare-ml URL=https://mercadolivre.com/...

# 2️⃣  NOVO: Organiza as tags dos produtos por categoria
make organize-tags                    # Modo interativo
# OU
make organize-tags-auto               # Marca apenas os óbvios

# 3️⃣  Publica os produtos no site + banco de dados
make stage
```

---

## Exemplo Prático

### Cenário 1: Produto com ALTA confiança
```
[1/50] ✅ DETECTADO: PET (95%)

────────────────────────────────────────────────────────────
📦 racao_premium_10kg_20260312.json
   Localização: geral/racao-gato.json
   Título: Ração para Gato Premium 10kg
   Tag atual: geral

   ✅ Movido para PET/
```

### Cenário 2: Produto com BAIXA confiança
```
[2/50] ❓ INCERTO: E (50%)

────────────────────────────────────────────────────────────
📦 smartwatch_xyz_20260312.json
   Localização: geral/smartwatch.json
   Título: Smartwatch com coleira para cachorro integrada
   Tag atual: geral

# Sistema pergunta qual categoria é correta
# Você responde: 1 (PET) ou 2 (E)?
```

---

## Categorias de Tags

| Tag | Descrição | Subcategorias |
|-----|-----------|--|
| **PET** | PetShop | caes, gatos, racao, brinquedos, higiene, acessorios, saude |
| **E** | Eletrônicos | smartphones, computadores, audio, tv, games, cameras, smartwatch, acessorios |
| **CD** | Casa & Decoração | banheiro, sala, quarto, cozinha, corredor, garagem, sacada, area-servico |
| **ME** | Moda & Estilo | feminino, masculino, infantil, calcados, acessorios, bolsas, relogios |
| **geral** | General | (sem subcategorias) |

---

## Palavras-chave Detectadas Automaticamente

### PET
- ração, gato, cachorro, pet, animal, coleira, comedouro, areia, petisco, aquario, hamster, peixe, felino, canino, antipulgas

### E (Eletrônicos)
- celular, smartphone, notebook, computador, tablet, fone, mouse, teclado, monitor, televisão, câmera, drone, console, xbox, switch, carregador, ssd, smartwatch

### CD (Casa & Decoração)
- pote, vaso, quadro, cortina, tapete, almofada, luminária, espelho, organizador, estante, prateleira, jogo de cama, toalha, banheiro, cozinha

### ME (Moda & Estilo)
- roupa, camisa, camiseta, calça, vestido, sapato, tênis, bolsa, relógio, óculos, jaqueta, casaco, short, saia, meia, blusa

---

## Resumo Final

Após executar `make organize-tags`, você verá um resumo:

```
════════════════════════════════════════════════════════════════
📊 RESUMO
════════════════════════════════════════════════════════════════
✅ Movidos automaticamente: 42
⏭️  Já estavam corretos: 8
❓ Necessitam revisão manual: 3
════════════════════════════════════════════════════════════════
```

---

## ⚠️ Notas Importantes

1. **Confiança > 80%**: Move automaticamente sem perguntar
2. **Confiança < 80%**: Modo interativo pergunta ao usuário
3. **Arquivos já no lugar certo**: São pulados automaticamente
4. **Subcategorias customizadas**: Se criar uma nova subcategoria na interação, o sistema cria a pasta automaticamente
5. **Execute ANTES de `make stage`**: Assim todos os produtos já estarão com as tags corretas no banco de dados

---

## Próximos Passos

```bash
# Após organizar as tags:
make organize-tags

# Verifique se ficou correto:
make organize-tags-auto  # Tenta mover apenas os óbvios

# Publique no site e no banco:
make stage
```

---

**Created**: 2026-03-24  
**Script**: `services/site/scripts/organize_tags.py`  
**Makefile**: `make organize-tags` + `make organize-tags-auto`
