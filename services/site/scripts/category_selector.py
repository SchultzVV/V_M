#!/usr/bin/env python3
"""
category_selector.py — Módulo compartilhado de seleção de categoria/subcategoria.

Usado por: prepare_ml_best.py, shopee_prepare_best.py, amazon_prepare_best.py

Categorias do site:
  PET  → /secao4  PetShop
  E    → /secao3  Eletrônicos
  CD   → /secao1  Casa & Decoração
  ME   → /secao2  Moda & Estilo
  geral           Categoria Geral
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Mapeamento canônico:  código → (nome exibição, pasta-staging, subcategorias)
# As subcategorias espelham os botões existentes nos HTMLs do site.
# ─────────────────────────────────────────────────────────────────────────────
CATEGORIES: dict[str, tuple[str, str, list[str]]] = {
    "PET":  ("PetShop",         "petshop",       ["caes", "gatos", "racao", "brinquedos", "higiene", "acessorios", "saude"]),
    "E":    ("Eletrônicos",     "eletronicos",    ["smartphones", "computadores", "audio", "tv", "games", "cameras", "smartwatch", "acessorios"]),
    "CD":   ("Casa & Decoração","casa-decoracao", ["banheiro", "sala", "quarto", "cozinha", "corredor", "garagem", "sacada", "area-servico"]),
    "ME":   ("Moda & Estilo",   "moda-estilo",    ["feminino", "masculino", "infantil", "calcados", "acessorios", "bolsas", "relogios"]),
    "ES":   ("Esportes",        "esportes",       ["futebol", "corrida", "academia", "natacao", "ciclismo", "tenis", "esportes-radicais", "acessorios"]),
    "geral":("Categoria Geral", "geral",          []),
}

# Ordem de exibição nos menus
CATEGORY_ORDER = ["PET", "E", "CD", "ME", "ES", "geral"]

# Atalho: tag → nome da pasta no staging
TAG_FOLDERS: dict[str, str] = {tag: info[1] for tag, info in CATEGORIES.items()}

# Raiz do staging dentro do container
STAGING_BASE = Path("/app/staging")


# ─────────────────────────────────────────────────────────────────────────────
# Detecção automática de categoria por palavras-chave no título
# ─────────────────────────────────────────────────────────────────────────────
def detect_product_category(title: str) -> str:
    """Detecta a categoria mais provável a partir do título do produto."""
    t = title.lower()

    pet_kw    = ["ração", "racao", "gato", "gatos", "cachorro", "pet", "animal",
                 "coleira", "comedouro", "areia", "petisco", "aquario",
                 "hamster", "passaro", "peixe", "felino", "canino", "antipulgas"]
    eletro_kw = ["celular", "smartphone", "notebook", "computador", "tablet",
                 "fone", "mouse", "teclado", "monitor", "televisão", "camera",
                 "câmera", "drone", "console", "playstation", "xbox", "switch",
                 "airfryer", "fritadeira", "aspirador", "robô", "smartwatch",
                 "carregador", "cabo usb", "ssd", "memória ram"]
    casa_kw   = ["pote", "vaso", "quadro", "cortina", "tapete", "almofada",
                 "luminária", "espelho", "organizador", "estante", "prateleira",
                 "jogo de cama", "toalha", "porta", "cozinha", "banheiro"]
    moda_kw   = ["roupa", "camisa", "camiseta", "calça", "vestido", "sapato",
                 "tênis", "bolsa", "relógio", "óculos", "jaqueta", "casaco",
                 "short", "saia", "meia", "cueca", "sutiã", "blusa"]

    for kw in pet_kw:
        if kw in t:
            return "PET"
    for kw in eletro_kw:
        if kw in t:
            return "E"
    for kw in casa_kw:
        if kw in t:
            return "CD"
    for kw in moda_kw:
        if kw in t:
            return "ME"

    esportes_kw = ["futebol", "chuteira", "bola de futebol", "corrida", "academia",
                   "musculação", "musculacao", "haltere", "kettlebell", "bicicleta", "bike",
                   "natação", "natacao", "raquete", "volei", "basquete", "handebol",
                   "skate", "patins", "yoga", "pilates", "crossfit", "whey protein",
                   "creatina", "suplemento esportivo", "roupa esportiva", "tênis esportivo",
                   "tenis esportivo", "bermuda esportiva", "legging esportiva", "fitness"]
    for kw in esportes_kw:
        if kw in t:
            return "ES"
    return "geral"


# ─────────────────────────────────────────────────────────────────────────────
# Seleção interativa de categoria
# ─────────────────────────────────────────────────────────────────────────────
def ask_user_category(suggested: str = None) -> str:
    """
    Exibe o menu de categorias e retorna a tag escolhida.

    Args:
        suggested: tag sugerida (ex: 'PET') — se fornecida, é exibida como padrão.

    Returns:
        Tag normalizada (ex: 'PET', 'E', 'CD', 'ME', 'ES', 'geral')
    """
    print("\n" + "=" * 70)
    print("🏷️  ESCOLHA A CATEGORIA DO PRODUTO")
    print("=" * 70)
    print("\n📋 Categorias disponíveis:")
    for i, tag in enumerate(CATEGORY_ORDER, 1):
        name = CATEGORIES[tag][0]
        print(f"  {i}. {tag} - {name}")

    # Aceita número (1-N) ou código direto (PET, E, CD, ME, ES, geral)
    num_map = {str(i + 1): tag for i, tag in enumerate(CATEGORY_ORDER)}
    tag_map = {**num_map, **{t: t for t in CATEGORIES}, **{t.lower(): t for t in CATEGORIES}}

    # Sugestão (opcional — usada pelo ML que detecta por palavras-chave do título)
    has_suggestion = suggested and suggested.upper() in CATEGORIES
    if has_suggestion:
        suggested_upper = suggested.upper()
        suggested_num   = str(CATEGORY_ORDER.index(suggested_upper) + 1)
        print(f"\n💡 Sugestão baseada no título: {suggested_upper} (opção {suggested_num})")
        prompt = f"\nDigite o número da categoria [Enter para usar a sugestão]: "
    else:
        suggested_upper = None
        prompt = "\nDigite o número ou código (1-6, PET/E/CD/ME/ES/geral): "

    while True:
        choice = input(prompt).strip()

        if not choice and has_suggestion:
            selected = suggested_upper
            break

        if not choice:
            print("   ❌ Por favor escolha uma categoria")
            continue

        selected = tag_map.get(choice) or tag_map.get(choice.upper())
        if selected:
            break
        print("   ❌ Inválido! Use 1-6 ou PET/E/CD/ME/ES/geral")

    print(f"✅ Categoria selecionada: {selected}")
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# Seleção interativa de subcategoria
# ─────────────────────────────────────────────────────────────────────────────
def ask_user_subcategory(tag: str) -> str:
    """
    Exibe as subcategorias da tag escolhida (das HTMLs + eventuais pastas já
    existentes no staging) e retorna a escolhida ou uma nova digitada.

    Args:
        tag: tag da categoria (ex: 'PET')

    Returns:
        Nome da subcategoria (ex: 'saude') ou string vazia se nenhuma.
    """
    tag = tag.upper()
    if tag not in CATEGORIES or tag == "geral":
        return ""

    tag_folder = TAG_FOLDERS[tag]
    tag_path   = STAGING_BASE / tag_folder

    # Subcategorias padrão do site (das HTMLs)
    default_subs = CATEGORIES[tag][2]

    # Subpastas já existentes no staging (pode ter novas criadas pelo usuário)
    existing = sorted([d.name for d in tag_path.iterdir() if d.is_dir()]) if tag_path.exists() else []

    # Merge mantendo ordem: defaults primeiro, extras no final, sem repetição
    seen: set[str] = set()
    merged: list[str] = []
    for s in default_subs + existing:
        if s not in seen:
            seen.add(s)
            merged.append(s)

    print(f"\n📁 Subcategorias em '{tag_folder}':")
    for i, sub in enumerate(merged, 1):
        print(f"   {i:2}. {sub}")
    print(f"\n   Digite o número, o nome de uma NOVA subcategoria, ou Enter para nenhuma")

    sub_input = input("📁 Subcategoria: ").strip().lower()

    if not sub_input:
        print("⚠️  Nenhuma subcategoria definida")
        return ""

    if sub_input.isdigit():
        idx = int(sub_input) - 1
        if 0 <= idx < len(merged):
            subcat = merged[idx]
            print(f"   ✅ Subcategoria: {subcat}")
            return subcat
        else:
            print("⚠️  Número inválido, sem subcategoria")
            return ""

    # Texto livre → nova subcategoria
    print(f"   ✅ Nova subcategoria: {sub_input}")
    return sub_input
