#!/usr/bin/env python3
"""
organize_tags.py — Reorganiza produtos no staging por categoria/tag

FUNCIONALIDADE:
1. Varre TODO o /app/staging (todos os produtos em suas pastas)
2. Para cada produto, detecta a categoria baseada no título
3. LÓGICA DE CONFIANÇA:
   - >= 75%: Move automaticamente (✅ DETECTADO)
   - 50%-75%: Move automaticamente (🤖 AUTO-CADASTRO)
   - < 50%: Pede confirmação ao usuário (❓ INCERTO)
4. Atualiza o JSON com a tag correta

USO:
  make organize-tags          # Modo inteligente (auto-cadastro + pergunta baixa confiança)
  make organize-tags-auto     # Modo automático silencioso (só auto-cadastra, sem perguntar)

Equivalent to:
  python scripts/organize_tags.py [--auto]
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Optional, Tuple
import argparse

# Importar funções de category_selector
sys.path.insert(0, os.path.dirname(__file__))
from category_selector import (
    detect_product_category,
    ask_user_category,
    ask_user_subcategory,
    CATEGORIES,
    TAG_FOLDERS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────
STAGING_BASE = Path("/app/staging")
# Thresholds de confiança
CONFIDENCE_AUTO_SURE = 0.75      # AutoMove com confiança alta
CONFIDENCE_AUTO_UNCERTAIN = 0.50  # AutoMove mesmo com incerteza média
CONFIDENCE_ASK_USER = 0.50        # Abaixo disso, pede ao usuário


# ─────────────────────────────────────────────────────────────────────────────
# Detecção com confiança
# ─────────────────────────────────────────────────────────────────────────────
def detect_category_with_confidence(title: str) -> Tuple[str, float]:
    """
    Detecta categoria e retorna (categoria, confiança).
    Confiança é um valor entre 0.0 e 1.0.

    Estratégia:
    - Se encontra múltiplas palavras-chave da mesma categoria → confiança alta (0.9+)
    - Se encontra 1-2 palavras-chave → confiança média (0.6-0.8)
    - Se não encontra nada ou encontra múltiplas categorias → confiança baixa (0.3)
    """
    t = title.lower()

    # Mapeamento de categoria → palavras-chave (EXPANDIDO)
    keywords = {
        "PET": [
            # Alimentos
            "ração", "racao", "alimento", "comida", "petisco", "snack para pet", "ração gato", "ração cachorro",
            # Animais
            "gato", "gatos", "cachorro", "cão", "cao", "puppy", "kitten", "pet", 
            "animal", "cão", "cães", "caes", "filhote", "dog", "cat",
            # Acessórios e higiene
            "coleira", "guia", "comedouro", "bebedouro", "areia", "cama pet", 
            "higiene pet", "shampoo pet", "antipulgas", "vermífugo", "vacina pet", "brinquedo pet",
            # Ambiente
            "aquario", "terrário", "viveiro", "hamster", "passaro", "peixe", 
            "felino", "canino", "reptil", "tartaruga",
            # Padrões genéricos
            "para cachorro", "para gato", "para pet", "para cão"
        ],
        "E": [
            # Celulares e tablets
            "celular", "smartphone", "iphone", "samsung", "xiaomi", "motorola", "nokia", "lg", 
            "tablet", "ipad", "telefone", "redmi", "galaxy", "a15", "s24", "mate", "poco", "moto g", "oneplus",
            # Computadores
            "notebook", "computador", "laptop", "desktop", "pc", "macbook", "ultrabook",
            # Periféricos
            "mouse", "teclado", "monitor", "webcam", "headset", "headphone", "fone de ouvido",
            # Áudio
            "fone", "speaker", "caixa som", "soundbar", "fone", "headphone", "airpods", "jbl", "beats",
            # Vídeo e TV
            "televisão", "television", "tv", "smart tv", "led", "oled", "player hdmi", "roku",
            # Gaming
            "console", "playstation", "xbox", "switch", "nintendo", "videogame", "ps5", "ps4", "xbox series",
            "joystick", "controle", "game", "nintendo switch",
            # Câmeras
            "camera", "câmera", "fotografia", "gopro", "drone", "dji",
            # Casa Inteligente
            "smartwatch", "smartband", "pulseira inteligente", "relógio inteligente", "apple watch", "wear os",
            "lâmpada inteligente", "alexa", "google home", "alexa", "echo",
            # Carregadores e Cabos
            "carregador", "cabo", "cabo usb", "tomada inteligente", "bateria", "carregador wireless",
            # Armazenamento
            "ssd", "hd", "memória ram", "pendrive", "cartão memória", "nvme",
            # Eletrodomésticos
            "airfryer", "fritadeira", "aspirador", "robô", "ventilador", "climatizador",
            "microondas", "forno", "geladeira", "máquina lavar", "secadora", "refrigerador",
            # Padrões genéricos
            "eletrônico", "eletronico", "tech", "gadget", "eletrônicos"
        ],
        "CD": [
            # Móveis
            "sofá", "sofa", "poltrona", "mesa", "cadeira", "cômoda", "comoda", "guarda-roupa",
            "armário", "armario", "prateleira", "estante", "aparador", "criado", "painel",
            # Decoração
            "quadro", "quadro decorativo", "painel", "moldura", "espelho", "adesivo decorativo",
            # Têxteis
            "cortina", "cortinado", "almofada", "almofadão", "jogo de cama",
            "lençol", "colcha", "toalha", "pano", "pano de prato", "tapete",
            # Organização
            "pote", "potinho", "caixa", "organizador", "gaveta organizadora",
            "suporte", "pendurador", "varal", "nicho", "nichos", "prateleira",
            # Iluminação
            "luminária", "luminaria", "abajur", "lâmpada", "pendurador", "arandela",
            # Decoração diversa
            "vaso", "vasilha", "base", "suporte", "decoração", "decoracao",
            # Cozinha
            "panela", "panelinha", "frigideira", "panela elétrica", "ralador",
            "faca", "garfo", "colher", "jogo de louça", "prato", "tigela", "panelão",
            # Banheiro
            "banheiro", "chuveiro", "tapetinho banheiro", "toalhas", "cortina chuveiro",
            "tapete banheiro", "acessório banheiro",
            # Limpeza
            "limpeza", "rodo", "penteador", "mop", "vassoura", "escova",
            # Padrões genéricos
            "casa", "decoração", "decoracao", "lar", "home", "interior", "cristaleira", "cozinha", "sala"
        ],
        "ME": [
            # Roupas Femininas
            "vestido", "saia", "calça", "calca", "blusa", "camisa", "camiseta", "top",
            "regata", "jaqueta", "casaco", "moletom", "legging", "short", "bermuda",
            # Roupas Masculinas
            "calça masculina", "camisa masculina", "camiseta masculina", "bermuda", "polo",
            "short masculino", "moletom masculino", "jaqueta masculina",
            # Sapatos e Calçados
            "sapato", "sapata", "tênis", "tenis", "bota", "chinelo", "sandália", "sandalia",
            "mocassim", "oxford", "scarpin", "salto", "sapatilha", "bota", "tamanco",
            # Acessórios
            "bolsa", "mochila", "carteira", "cinturão", "relógio", "relogio",
            "óculos", "oculos", "pulseira", "colar", "brinco", "anel", "bracelete",
            # Básicos
            "meia", "cueca", "sutiã", "sutia", "lingerie", "biquíni", "biquini",
            "roupa íntima", "roupa intima", "calcinha",
            # Padrões genéricos
            "roupa", "roupinha", "vestuário", "vestimenta", "fashion", "moda",
            "estilo", "casual", "esporte", "feminino", "masculino", "infantil",
            # Especiais
            "festa", "casamento", "social", "formal", "praia", "piscina", "surf"
        ],
        "ES": [
            # Futebol
            "futebol", "chuteira", "bola de futebol", "caneleira", "goleiro",
            # Corrida e caminhada
            "corrida", "tênis de corrida", "tenis de corrida", "maratona", "trilha",
            # Academia e musculação
            "academia", "musculação", "musculacao", "haltere", "kettlebell", "anilha",
            "barra musculação", "banco supino", "colchonete", "corda pular",
            # Ciclismo
            "bicicleta", "bike", "ciclismo", "capacete bike", "luva ciclismo",
            # Natação
            "natação", "natacao", "óculos natação", "touca natacao", "prancha natação",
            # Raquetes
            "raquete", "tênis esportivo", "tenis esportivo", "beach tennis", "badminton",
            # Outros esportes
            "volei", "vôlei", "basquete", "handebol", "skate", "patins", "surf",
            # Bem-estar
            "yoga", "pilates", "crossfit", "funcional",
            # Suplementos
            "whey protein", "creatina", "suplemento esportivo", "proteína", "pré-treino",
            # Vestuário esportivo
            "roupa esportiva", "bermuda esportiva", "legging esportiva", "camiseta treino",
            # Padrões genéricos
            "esporte", "fitness", "treino", "esportivo", "esportiva",
        ],
    }

    # Contar matches por categoria
    matches = {}
    for cat, words in keywords.items():
        count = sum(1 for word in words if word in t)
        if count > 0:
            matches[cat] = count

    if not matches:
        return "geral", 0.2  # Reduzido de 0.3 para 0.2 para forçar mais perguntas

    # Categoria com mais matches
    best_cat = max(matches, key=lambda k: matches[k])
    best_count = matches[best_cat]

    # Calcular confiança baseada no número de matches
    if best_count >= 4:
        confidence = 0.98
    elif best_count == 3:
        confidence = 0.90
    elif best_count == 2:
        confidence = 0.75
    else:  # best_count == 1
        confidence = 0.55

    # Se há múltiplas categorias com matches, reduzir confiança
    if len(matches) > 1:
        second_best = sorted(matches.items(), key=lambda x: x[1], reverse=True)[1][1]
        # Se a diferença entre as duas categorias é pequena, reduzir confiança
        if best_count - second_best <= 1:
            confidence *= 0.6

    return best_cat, min(confidence, 0.98)


# ─────────────────────────────────────────────────────────────────────────────
# Leitura de produtos
# ─────────────────────────────────────────────────────────────────────────────
def find_all_products() -> list[Tuple[Path, dict]]:
    """
    Encontra todos os JSONs de produtos em /app/staging.
    Retorna lista de (caminho, dados_json).
    """
    products = []

    if not STAGING_BASE.exists():
        print(f"⚠️  {STAGING_BASE} não existe")
        return products

    # Procura recursivamente por JSONs
    for json_file in STAGING_BASE.rglob("*.json"):
        # Pula arquivos especiais (short_link/links.json)
        if json_file.parent.name == "short_link":
            continue

        try:
            with open(json_file) as f:
                data = json.load(f)
            products.append((json_file, data))
        except Exception as e:
            print(f"⚠️  Erro ao ler {json_file}: {e}")

    return products


# ─────────────────────────────────────────────────────────────────────────────
# Movimentação de produtos
# ─────────────────────────────────────────────────────────────────────────────
def move_product(current_path: Path, new_tag: str, new_subcategory: str = "") -> bool:
    """
    Move o produto de current_path para o diretório correto baseado em tag+subcategoria.
    Atualiza o JSON com a tag correta.
    """
    if new_tag not in TAG_FOLDERS:
        print(f"   ❌ Tag inválida: {new_tag}")
        return False

    tag_folder = TAG_FOLDERS[new_tag]

    if new_subcategory:
        new_dir = STAGING_BASE / tag_folder / new_subcategory
    else:
        new_dir = STAGING_BASE / tag_folder

    new_dir.mkdir(parents=True, exist_ok=True)

    # Novo caminho do arquivo
    new_path = new_dir / current_path.name

    # Se arquivo já existe no destino, não sobrescreve
    if new_path.exists():
        print(f"   ⚠️  Arquivo já existe em {new_path}, pulando")
        return False

    try:
        # Lê JSON
        with open(current_path) as f:
            data = json.load(f)

        # Atualiza a tag no JSON
        data["tag"] = new_tag.upper()
        if "subcategory" not in data:
            data["subcategory"] = ""
        if new_subcategory:
            data["subcategory"] = new_subcategory

        # Move arquivo
        shutil.move(str(current_path), str(new_path))

        # Sobrescreve com JSON atualizado
        with open(new_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Movido para {new_tag}/{new_subcategory if new_subcategory else ''}")
        return True

    except Exception as e:
        print(f"   ❌ Erro ao mover: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Processamento
# ─────────────────────────────────────────────────────────────────────────────
def print_product_info(path: Path, data: dict) -> None:
    """Exibe informações do produto de forma legível."""
    print(f"\n{'─' * 80}")
    print(f"📦 {path.name}")
    print(f"   Localização: {path.relative_to(STAGING_BASE)}")
    print(f"   Título: {data.get('title', 'N/A')[:70]}")
    if data.get("subcategory"):
        print(f"   Subcategoria atual: {data.get('subcategory')}")
    print(f"   Tag atual: {data.get('tag', 'geral')}")


def process_products(auto_only: bool = False) -> dict:
    """
    Processa todos os produtos do staging.

    Lógica de confiança:
    - >= 0.75: Move automaticamente (confiante)
    - 0.50-0.75: Move automaticamente (auto-cadastro)
    - < 0.50: Pede confirmação ao usuário (muita incerteza)

    Args:
        auto_only: se True, apenas move automaticamente (sem perguntar)

    Returns:
        Dict com estatísticas: {moved: int, skipped: int, asked: int}
    """
    products = find_all_products()

    if not products:
        print("⚠️  Nenhum produto encontrado no staging")
        return {"moved": 0, "skipped": 0, "asked": 0}

    print("\n" + "=" * 80)
    print(f"🏷️  ORGANIZADOR DE TAGS — {len(products)} produtos encontrados")
    print("=" * 80)

    stats = {"moved": 0, "skipped": 0, "asked": 0}

    for idx, (path, data) in enumerate(products, 1):
        title = data.get("title", "Sem título")
        current_tag = data.get("tag", "geral").upper()
        current_subcategory = data.get("subcategory", "")

        # Detecta categoria com confiança
        detected_tag, confidence = detect_category_with_confidence(title)

        # Se já está na pasta correta E confiança é boa, pula
        if detected_tag == current_tag and confidence > 0.7:
            stats["skipped"] += 1
            continue

        print(f"\n[{idx}/{len(products)}]", end=" ")

        # AUTO-CADASTRO: confiança >= 50% → move automaticamente
        if confidence >= CONFIDENCE_AUTO_UNCERTAIN:
            symbol = "✅" if confidence >= CONFIDENCE_AUTO_SURE else "🤖"
            print(f"{symbol} AUTO-MOVE: {detected_tag} ({confidence:.0%})")
            if move_product(path, detected_tag):
                stats["moved"] += 1
            continue

        # Se auto_only ativado, não pergunta
        if auto_only:
            print(f"⏭️  INCERTO: {detected_tag} ({confidence:.0%}) — pulando")
            stats["asked"] += 1
            continue

        # MUITA INCERTEZA (< 50%): Pergunta ao usuário
        print(f"❓ INCERTO: {detected_tag} ({confidence:.0%})")
        print_product_info(path, data)
        
        print("")
        print("💡 DICA: Todo produto deve ter uma palavra que identifique a categoria!")
        print(f"   Se o título '{title[:60]}' não tiver uma palavra de categoria,")
        print("   escolha 'geral' ou revise o título do produto no marketplace.")
        print("")

        # Pergunta tag
        tag = ask_user_category(suggested=detected_tag)

        # Pergunta subcategoria
        subcat = ask_user_subcategory(tag)

        # Move
        if move_product(path, tag, subcat):
            stats["moved"] += 1
        else:
            stats["asked"] += 1

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Reorganiza produtos no staging por categoria/tag"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Apenas move produtos com alta confiança (sem perguntar)",
    )

    args = parser.parse_args()
    auto_only = args.auto

    # Processa produtos
    stats = process_products(auto_only=auto_only)

    # Resumo
    print("\n" + "=" * 80)
    print("📊 RESUMO")
    print("=" * 80)
    print(f"✅ Movidos automaticamente: {stats['moved']}")
    print(f"⏭️  Já estavam corretos: {stats['skipped']}")
    if not auto_only:
        print(f"❓ Requer confirmação do usuário: {stats['asked']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
