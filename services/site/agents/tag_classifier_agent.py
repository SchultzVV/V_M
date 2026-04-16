"""
tag_classifier_agent.py
Usa o LLM via hsmart para decidir tag + subtag de cada produto,
depois aplica a mesma lógica de movimentação de organize_tags.py.

Modos:
  --staging        Processa todos os JSONs em /app/staging (padrão)
  --db             Processa produtos do banco sem tag/com tag "geral"
  --product-id ID  Produto específico pelo ID do banco
  --dry-run        Só mostra decisão, não move/atualiza

Uso:
  python3 agents/tag_classifier_agent.py
  python3 agents/tag_classifier_agent.py --db --dry-run
  make tag-classify
  make tag-classify-db
"""
import os
import sys
import json
import logging
import argparse
import requests
from pathlib import Path
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# ─── Path setup ────────────────────────────────────────────────────────────
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS_DIR = os.path.join(_APP_DIR, "scripts")
for _p in (_APP_DIR, _SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from category_selector import CATEGORIES, TAG_FOLDERS, STAGING_BASE  # type: ignore

# ─── Config ────────────────────────────────────────────────────────────────
_HSMART_URL = os.environ.get(
    "HSMART_RETRIEVAL_URL",
    os.environ.get("HSMART_URL", "http://hsmart:5005"),
)
# Ollama direto — usado quando hsmart/RAG retorna vazio
_OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://ollama:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")

# ─── Hints de subtag por categoria (usados pelo LLM e pelo fallback) ───────
# IMPORTANTE: A ordem define a prioridade — subtags mais específicos vêm primeiro.
_SUBTAG_HINTS: dict[str, dict[str, list[str]]] = {
    "E":  {
        # games antes de tv/smartphones (PS5/Xbox são inequívocos)
        "games":        ["playstation","xbox","nintendo","ps5","ps4","videogame","jogo físico","super smash","zelda","mario","switch nintendo"],
        # tv antes de smartphones — "samsung tv", "aiwa", and palavras de polegadas afastam falsos-positivos
        "tv":           ["smart tv","polegadas","televisão","televisao","led tv","oled tv","qled tv","full hd tv","4k tv"],
        "computadores": ["notebook","computador","laptop","desktop","macbook","ultrabook"],
        "audio":        ["fone","headphone","headset","speaker","caixa som","soundbar","airpods","jbl","earphone"],
        "cameras":      ["câmera","camera","gopro","drone","lente fotográfica"],
        "smartwatch":   ["smartwatch","smartband","relógio inteligente","apple watch"],
        # acessorios pega eletrodomésticos antes de smartphones
        "acessorios":   ["ar condicionado","ar-condicionado","split inverter","split hi wall",
                         "microondas","geladeira","lavadora","máquina lavar","secadora","refrigerador",
                         "airfryer","fritadeira","aspirador","ventilador","climatizador",
                         "carregador","cabo usb","ssd","pendrive","mouse","teclado","monitor",
                         "desk converter","sit stand","standing desk"],
        # smartphones por último — termos específicos de telefone
        "smartphones":  ["celular","smartphone","iphone","redmi","poco","galaxy s","galaxy a","moto g",
                         "motorola edge","xiaomi","5g dual sim","dual sim","128gb","256gb","512gb"],
    },
    "CD": {
        # banheiro primeiro (chuveiro, torneira são inequívocos)
        "banheiro": ["chuveiro","torneira","vaso sanitário","toalha banho","tapete banheiro","cortina chuveiro","lorenzetti","ducha"],
        "quarto":   ["guarda-roupa","jogo de cama","cômoda","colcha","lençol","criado-mudo","armário quarto","cama casal","cama solteiro"],
        "cozinha":  ["panela","frigideira","faca","prato","tigela","mesa jantar","mesa cozinha","pia","utensílio"],
        "sala":     ["sofá","sofa","poltrona","cristaleira","rack","painel tv","mesa sala","aparador","mesa de centro"],
        "area-servico":["sabão","sabao","detergente","limpeza","desinfetante","amaciante",
                        "lava roupas","tira manchas","multiuso","água sanitária","agua sanitaria",
                        "omo","ariel","downy","comfort","veja","ajax","mr musculo",
                        "esponja","pano de chão","rodo","balde","bacia","cesto"],
        "acessorios":["luminária","vaso decorativo","espelho","quadro","decoração","tapete sala","almofada","cortina",
                      "escrivaninha","escritório","escritorio","home office","cadeira escritório",
                      "prateleira","estante","mesa lateral","sit-stand","sit stand","standing desk"],
    },
    "ME": {
        # calcados antes de feminino/masculino para sapatos gerais sem marcador de gênero
        "calcados":  ["sapato","tênis","tenis","bota","chinelo","mocassim","calçado","loafer","scarpin"],
        "bolsas":    ["bolsa","mochila","carteira","necessaire"],
        "relogios":  ["relógio","relogio"],
        "feminino":  ["vestido","saia","blusa","top feminino","feminino","feminina"],
        "masculino": ["masculino","masculina","bermuda","camisa polo","polo masculin","camisa masculin"],
    },
    "PET": {
        "racao":      ["ração","racao","petisco","alimento pet","pasta gatos","pasta pet","sachê"],
        "gatos":      ["gato","cat","kitten","felino","gatinho"],
        "caes":       ["cachorro","cão","dog","puppy","canino"],
        "higiene":    ["shampoo pet","antipulgas","vermifugo","higiene pet"],
        "acessorios": ["coleira","comedouro","cama pet","brinquedo pet","aquário","gaiola"],
    },
}


def _subtag_from_keywords(tag: str, title: str) -> str:
    """Seleciona a melhor subtag usando correspondência de keywords. Retorna '' se nenhuma."""
    t = title.lower()
    hints = _SUBTAG_HINTS.get(tag, {})
    for subtag, kws in hints.items():
        if any(kw in t for kw in kws):
            return subtag
    return ""


# ─── Catálogo JSON para o prompt ───────────────────────────────────────────
_CAT_LINES = "\n".join(
    f'  "{tag}": {{"nome": "{info[0]}", "subtags": {info[2]}}}'
    for tag, info in CATEGORIES.items()
    if tag != "geral"
)
_CATALOG_JSON = "{\n" + _CAT_LINES + "\n}"


# ═══════════════════════════════════════════════════════════════════════════
# LLM call
# ═══════════════════════════════════════════════════════════════════════════

_TAG_OPTIONS = {tag: info[0] for tag, info in CATEGORIES.items() if tag != "geral"}
# ex: {"PET": "PetShop", "E": "Eletrônicos", "CD": "Casa & Decoração", "ME": "Moda & Estilo"}


def _query(question: str) -> str:
    """
    1. Tenta hsmart /query (RAG com contexto do Qdrant).
    2. Se resposta vazia, cai direto no Ollama (geração pura).
    """
    # Tentativa 1 — hsmart RAG
    try:
        resp = requests.post(
            f"{_HSMART_URL}/query",
            json={"question": question},
            timeout=30,
        )
        resp.raise_for_status()
        text = (resp.json().get("response") or resp.json().get("result") or "").strip()
        if text and text.lower() not in ("empty response", ""):
            return text
    except Exception as exc:
        logger.debug("hsmart falhou: %s", exc)

    # Tentativa 2 — Ollama direto
    try:
        resp = requests.post(
            f"{_OLLAMA_URL}/api/generate",
            json={"model": _OLLAMA_MODEL, "prompt": question, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return (resp.json().get("response") or "").strip()
    except Exception as exc:
        logger.warning("Ollama direto falhou: %s", exc)

    return ""


def _ask_llm(title: str, description: str = "") -> Tuple[str, str, float]:
    """
    LLM chamado APENAS para títulos ambíguos (conf keyword < 0.62).

    Estratégia focada:
    1. Calcula scores de keyword para todas as categorias.
    2. Pega as top-2 candidatas (as que tiveram mais keyword hits).
    3. Faz UMA única pergunta ao LLM com só essas 2 opções + "outro".
       → prompt curto, modelo pequeno responde bem a escolhas binárias/ternárias.
    4. Subtag via keyword (determinístico).

    Retorna (tag, subtag, confidence).
    """
    import re

    # ── Calcular top-2 candidatas por score de keyword ─────────────────────
    t = title.lower()
    scores: dict[str, int] = {
        cat: sum(1 for w in words if w in t)
        for cat, words in _KW.items()
    }
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    # top-2 com pelo menos 1 hit; se nenhuma tem hit, pega as 2 primeiras mesmo
    top2 = [c for c, s in ranked[:2] if s > 0] or [ranked[0][0], ranked[1][0]]

    if len(top2) < 2:
        top2 = [ranked[0][0], ranked[1][0]]

    # Labels para o prompt
    _LABELS = {"PET": "pet/animal", "E": "eletrônico/eletrodoméstico", "CD": "casa/decoração", "ME": "moda/roupa"}
    opt_a = _LABELS.get(top2[0], top2[0])
    opt_b = _LABELS.get(top2[1], top2[1])

    ctx = title[:80]
    if description:
        ctx += f" — {description[:40]}"

    question = (
        f'Produto: "{ctx}"\n'
        f'Categoria: A={opt_a}  B={opt_b}  C=outro\n'
        f'Responda apenas: A, B ou C'
    )

    raw = (_query(question) or "").strip()
    logger.debug("LLM top2 [%s/%s] raw: %r", top2[0], top2[1], raw)

    # Parse: procura A ou B na resposta (C = outro = geral)
    match = re.search(r'\b([ABCabc])\b', raw)
    if match:
        letter = match.group(1).upper()
        if letter == "A":
            tag = top2[0]
        elif letter == "B":
            tag = top2[1]
        else:
            return "geral", "", 0.0
    else:
        return "geral", "", 0.0

    subtag = _subtag_from_keywords(tag, title)
    if not subtag and CATEGORIES.get(tag, ("", "", []))[2]:
        subtag = CATEGORIES[tag][2][0]

    return tag, subtag, 0.75




# ═══════════════════════════════════════════════════════════════════════════
# Fallback: regex keywords
# ═══════════════════════════════════════════════════════════════════════════

_KW: dict[str, list[str]] = {
    "PET": ["ração","racao","gato","gatos","gata","cachorro","cão","cães","cao","caes",
            "dog","cat","pet","animal","coleira","comedouro","areia","petisco",
            "aquario","hamster","passaro","peixe","felino","canino",
            "antipulgas","vermifugo","shampoo pet","brinquedo pet",
            "golden","labrador","poodle","bulldog","labrador","shih tzu",
            "premier","whiskas","pedigree","royal canin","hills"],
    "E":   ["celular","smartphone","iphone","samsung","galaxy","xiaomi","redmi","poco",
            "motorola","moto g","moto e","edge","tablet","ipad","notebook",
            "computador","laptop","desktop","macbook","headset","headphone",
            "fone","speaker","caixa som","soundbar","televisão","televisao",
            "tv","smart tv","oled","qled","uhd","4k","polegadas","console",
            "playstation","xbox","switch","nintendo","videogame","ps5","ps4",
            "camera","câmera","gopro","drone","smartwatch","smartband","alexa",
            "echo dot","kindle","chromecast","carregador","cabo","ssd","nvme",
            "pendrive","mouse","teclado","monitor","airfryer","fritadeira",
            "aspirador","ventilador","climatizador","microondas","geladeira",
            "máquina lavar","secadora","refrigerador","ar condicionado",
            "ar-condicionado","split","inverter","chuveiro","lorenzetti","ducha",
            "256gb","128gb","512gb","1tb","2tb","dual sim","5g",
            "brastemp","electrolux","consul","whirlpool","panasonic","lg","sony",
            "philips","bosch","frost free","inox inverter","eletrodoméstico",
            "lava e seca","lava-louça","lavadora"],
    "CD":  ["sofá","sofa","poltrona","mesa","cadeira","cômoda","comoda",
            "guarda-roupa","guarda roupa","armário","armario","prateleira",
            "estante","aparador","cristaleira","rack","painel tv","escrivaninha",
            "bancada","quadro","espelho","cortina","almofada","jogo de cama",
            "lençol","lencol","colcha","toalha","tapete","luminária","luminaria",
            "vaso","panela","frigideira","faca","prato","tigela","mop","vassoura",
            "decoração","decoracao","sala","quarto","cozinha","lar","casa",
            "escritório","escritorio","home office",
            "sabão","sabao","detergente","limpeza","desinfetante","amaciante",
            "lava roupas","tira manchas","multiuso","água sanitária","agua sanitaria",
            "omo","ariel","downy","comfort","veja","ajax","mr musculo",
            "esponja","pano de chão","rodo","balde","bacia","cesto"],
    "ME":  ["vestido","saia","calça","calca","blusa","camisa","camiseta","top",
            "jaqueta","casaco","moletom","moleton","legging","short","bermuda",
            "sapato","tênis","tenis","bota","botina","chinelo","sandália","sandalia",
            "scarpin","mocassim","loafer","bolsa","mochila","carteira",
            "relógio","relogio","óculos","oculos","pulseira","colar","brinco",
            "moda","roupa","feminino","feminina","masculino","masculina","infantil",
            "calçado","calcado","jeans","skinny","slim","cropped",
            "nike","adidas","mizuno","olympikus","fila","polo wear","reserva","hering"],
}


def _fallback_tag(title: str) -> Tuple[str, str, float]:
    """
    Fallback keyword-based. Usa _KW para categoria e _SUBTAG_HINTS para subtag.
    Retorna (tag, subtag, confidence).
    """
    t = title.lower()

    scores: dict[str, int] = {}
    for cat, words in _KW.items():
        scores[cat] = sum(1 for w in words if w in t)

    if not any(scores.values()):
        return "geral", "", 0.2

    best = max(scores, key=lambda k: scores[k])
    count = scores[best]
    conf = min(0.45 + count * 0.10, 0.72)  # caps em 0.72 (LLM tem prioridade acima de 0.4)

    subtag = _subtag_from_keywords(best, title)
    if not subtag:
        cats = CATEGORIES.get(best, ("", "", []))[2]
        subtag = cats[0] if cats else ""

    return best, subtag, conf


def _classify(title: str, description: str = "") -> Tuple[str, str, float, str]:
    """
    Classificação em duas camadas:

    1. Regex/keywords (rápido, determinístico):
       - Tenta _fallback_tag primeiro
       - Se conf >= 0.62 → aceita direto, sem tocar o LLM
         (conf 0.62 = pelo menos 2 keywords fortes no título)
    2. LLM (lento, ~3s/produto):
       - Só chamado quando keywords dão conf < 0.62 (título ambíguo)
       - Se LLM também falhar → usa o resultado das keywords mesmo

    Retorna (tag, subtag, conf, source) onde source = "keyword" | "llm" | "fallback"
    """
    # ── Camada 1: keywords ─────────────────────────────────────────────────
    kw_tag, kw_subtag, kw_conf = _fallback_tag(title)
    if kw_conf >= 0.72:
        # Confiante o suficiente — não precisa de LLM
        return kw_tag, kw_subtag, kw_conf, "keyword"

    # ── Camada 2: LLM (só para títulos ambíguos) ───────────────────────────
    llm_tag, llm_subtag, llm_conf = _ask_llm(title, description)
    if llm_tag != "geral" and llm_conf >= 0.4:
        return llm_tag, llm_subtag, llm_conf, "llm"

    # ── Fallback: resultado de keywords, mesmo com conf baixa ─────────────
    if kw_tag != "geral":
        return kw_tag, kw_subtag, kw_conf, "fallback"

    return "geral", "", 0.2, "fallback"




def _move_staging_product(json_path: Path, tag: str, subtag: str, dry_run: bool) -> bool:
    """Move o arquivo para a pasta correta e atualiza o JSON."""
    folder = TAG_FOLDERS.get(tag, "geral")
    target_dir = STAGING_BASE / folder / subtag if subtag else STAGING_BASE / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / json_path.name

    if target == json_path:
        return True  # já está no lugar certo

    if dry_run:
        return True

    try:
        import shutil
        # Atualiza tag/subtag no JSON
        with open(json_path) as f:
            data = json.load(f)
        data["tag"]    = tag
        data["subtag"] = subtag
        with open(json_path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        shutil.move(str(json_path), str(target))
        return True
    except Exception as exc:
        logger.error("Erro ao mover %s: %s", json_path, exc)
        return False


def classify_staging(dry_run: bool = False) -> dict:
    stats = {"total": 0, "moved": 0, "already_ok": 0, "llm_ok": 0, "fallback": 0, "errors": 0}

    jsons = list(STAGING_BASE.rglob("*.json"))
    jsons = [p for p in jsons if p.parent.name != "short_link"]

    print(f"\n{'━'*62}")
    print(f"🏷️  TAG CLASSIFIER — {len(jsons)} arquivo(s) em staging")
    if dry_run:
        print("   modo: DRY-RUN")
    print(f"{'━'*62}\n")

    for i, json_path in enumerate(jsons, 1):
        try:
            with open(json_path) as f:
                data = json.load(f)
        except Exception:
            stats["errors"] += 1
            continue

        title = data.get("title") or data.get("nome") or data.get("name") or ""
        desc  = data.get("description") or ""
        stats["total"] += 1

        current_tag = (data.get("tag") or "").upper()

        tag, subtag, conf, source = _classify(title, desc)

        if source == "llm":
            stats["llm_ok"] += 1
        else:
            stats["fallback"] += 1

        # Verifica se já está correto
        expected_dir = TAG_FOLDERS.get(tag, "geral")
        already_ok = expected_dir in str(json_path) and current_tag == tag

        prefix = f"[{i:>3}/{len(jsons)}]"
        short_title = title[:45] or json_path.stem[:45]
        icon = "🤖" if source == "llm" else "🔤"

        if already_ok:
            print(f"  ✓  {prefix} {short_title[:45]}")
            print(f"           → {tag}/{subtag} (conf={conf:.2f}) já ok")
            stats["already_ok"] += 1
        else:
            ok = _move_staging_product(json_path, tag, subtag, dry_run)
            verb = "moveria →" if dry_run else "→"
            status = "✅" if ok else "❌"
            print(f"  {status} {icon} {prefix} {short_title}")
            print(f"           {verb} {tag}/{subtag} (conf={conf:.2f}, {source})")
            if ok:
                stats["moved"] += 1
            else:
                stats["errors"] += 1

    return stats


# ═══════════════════════════════════════════════════════════════════════════
# Aplicar ao banco (Products sem tag ou com tag "geral")
# ═══════════════════════════════════════════════════════════════════════════

def classify_db(dry_run: bool = False, product_id: Optional[str] = None) -> dict:
    stats = {"total": 0, "updated": 0, "already_ok": 0, "llm_ok": 0, "fallback": 0, "errors": 0}

    try:
        from database import SessionLocal
        from models.product import Product
    except ImportError as exc:
        logger.error("Import falhou (rode dentro do container site): %s", exc)
        sys.exit(1)

    session = SessionLocal()
    try:
        q = session.query(Product)
        if product_id:
            q = q.filter(Product.id == product_id)
        else:
            # só produtos sem tag definida ou com tag "geral"/""/None
            q = q.filter(
                (Product.tag.is_(None)) |
                (Product.tag == "") |
                (Product.tag == "geral")
            )
        products = q.all()
    except Exception as exc:
        # coluna tag pode não existir
        logger.warning("Query por tag falhou (%s) — processando todos", exc)
        q = session.query(Product)
        if product_id:
            q = q.filter(Product.id == product_id)
        products = q.all()

    print(f"\n{'━'*62}")
    print(f"🏷️  TAG CLASSIFIER (banco) — {len(products)} produto(s)")
    if dry_run:
        print("   modo: DRY-RUN")
    print(f"{'━'*62}\n")

    for i, product in enumerate(products, 1):
        title = (
            getattr(product, "nome", None) or
            getattr(product, "title", None) or
            getattr(product, "name", None) or
            product.external_id or "?"
        )
        desc = getattr(product, "description", "") or ""
        stats["total"] += 1

        tag, subtag, conf, source = _classify(title, desc)

        if source == "llm":
            stats["llm_ok"] += 1
        else:
            stats["fallback"] += 1

        icon = "🤖" if source == "llm" else "🔤"
        prefix = f"[{i:>3}/{len(products)}]"
        short = title[:45]

        if not dry_run:
            try:
                if hasattr(product, "tag"):
                    product.tag = tag
                if hasattr(product, "subtag"):
                    product.subtag = subtag
                session.commit()
                stats["updated"] += 1
                print(f"  ✅ {icon} {prefix} {short}")
                print(f"           → {tag}/{subtag} (conf={conf:.2f}, {source})")
            except Exception as exc:
                session.rollback()
                logger.error("Erro ao salvar %s: %s", product.id, exc)
                stats["errors"] += 1
        else:
            print(f"  🔍 {icon} {prefix} {short}")
            print(f"           → {tag}/{subtag} (conf={conf:.2f}, {source})")
            stats["updated"] += 1

    session.close()
    return stats


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def _print_summary(stats: dict, dry_run: bool):
    print(f"\n{'━'*62}")
    print(f"✅ Concluído: {stats['total']} produto(s)")
    print(f"   🤖 Via LLM     : {stats['llm_ok']}")
    print(f"   🔤 Via fallback: {stats['fallback']}")
    moved_key = "moved" if "moved" in stats else "updated"
    print(f"   ✅ {'Movidos' if moved_key == 'moved' else 'Atualizados'}: {stats[moved_key]}")
    print(f"   ✓  Já corretos : {stats.get('already_ok', 0)}")
    print(f"   ❌ Erros       : {stats['errors']}")
    if dry_run:
        print("   ⚠️  DRY-RUN — nenhuma alteração foi gravada")
    print(f"{'━'*62}\n")


def main():
    parser = argparse.ArgumentParser(description="Tag Classifier Agent — LLM decide tag/subtag")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staging",    action="store_true", default=True,
                      help="Processa JSONs em /app/staging (padrão)")
    mode.add_argument("--db",         action="store_true",
                      help="Processa produtos do banco sem tag ou com tag geral")
    parser.add_argument("--product-id", metavar="ID",
                        help="ID específico no banco (requer --db)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Só mostra decisão, não aplica")
    args = parser.parse_args()

    if args.db or args.product_id:
        stats = classify_db(dry_run=args.dry_run, product_id=args.product_id)
    else:
        stats = classify_staging(dry_run=args.dry_run)

    _print_summary(stats, args.dry_run)


if __name__ == "__main__":
    main()
