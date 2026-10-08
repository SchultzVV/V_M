#!/usr/bin/env python3
"""
Backfill subcategory for products missing it, using title keyword matching.
"""
import sys
import unicodedata
sys.path.insert(0, '/app')
from database import SessionLocal
from models import Product

SUBTAG_KEYWORDS = {
    'PET': {
        'gatos':    ['gato', 'felino', 'macrogard'],
        'higiene':  ['higienico', 'tapete high', 'areia', 'pipicat', 'antiodor', 'petlike',
                     'sanol dog', 'york dogs', 'lenco umedecido'],
        'caes':     ['cachorro', 'canino', 'pet clean', 'dogs care'],
        'racao':    ['ração', 'racao', 'alimento', 'petisco', 'gran plus', 'bionatural',
                     'quatree', 'premier', 'golden', 'dog chow', 'royal canin',
                     'formula natural', 'fresh meat'],
        'brinquedos': ['brinquedo', 'mordedor', 'kong', 'teaser'],
        'acessorios': ['comedouro', 'bebedouro', 'fonte', 'coleira', 'peitoral',
                       'caminha', 'iglu', 'toca', 'cama'],
        'saude':    ['suplemento', 'promun', 'organnact', 'antipulga', 'pipeta',
                     'nexgard', 'bravecto', 'frontline'],
    },
    'E': {
        'smartphones':  ['smartphone', 'celular', 'iphone', 'galaxy', 'redmi', 'xiaomi'],
        'audio':        ['fone', 'headset', 'headphone', 'caixa de som', 'airpods', 'qcy', 'zealot'],
        'computadores': ['teclado', 'mouse', 'notebook', 'computador', 'monitor', '4pcs u fork'],
        'tv':           ['smart tv', 'televisao'],
        'games':        ['playstation', 'dualsense', 'joystick', 'xbox',
                         'nintendo switch', 'super smash', 'gamer'],
        'cameras':      ['segurança wifi', 'câmera de segurança', 'camera de seguranca',
                         'tapo', 'icsee', 'mercusys'],
        'climatizacao': ['ar condicionado', 'ar-condicionado'],
        'smartwatch':   ['smartwatch', 'mi band', 'galaxy watch'],
        'acessorios':   ['cabo usb', 'carregador turbo', 'base carregamento'],
    },
    'ES': {
        'futebol': ['futebol', 'chuteira', 'bola'],
        'corrida': ['corrida', 'running', 'tenis de corrida'],
        'academia': ['academia', 'musculacao', 'musculação', 'halter', 'kettlebell'],
        'natacao': ['natacao', 'natação', 'oculos de natacao'],
        'ciclismo': ['ciclismo', 'bicicleta', 'bike', 'capacete ciclismo'],
        'tenis': ['raquete', 'bola de tenis', 'tenis de quadra'],
        'esportes-radicais': ['skate', 'patins', 'escalada', 'radical'],
        'acessorios': ['garrafa termica', 'luva esportiva', 'faixa', 'acessorio fitness'],
    },
    'CD': {
        'area-servico': ['varal'],
        'limpeza':      ['chuveiro', 'lava-roupas', 'banho a seco', 'toalhas umedecidas'],
        'banheiro':     ['cesto de roupa', 'cesto duplo', 'kontuz', 'vittak',
                         'colmeia organizad'],
        'sala':         ['sofa', 'sofa', 'cristaleira', 'tapete', 'passadeira',
                         'plafon', 'luminaria de teto'],
        'quarto':       ['organizador de gaveta', 'suporte cama', 'cabeceira'],
        'cozinha':      ['porta-tempero', 'tempero', 'organizador cozinha',
                         'organizador modular', 'kit 25 organizador', 'kit 2 organizadores',
                         'estante de cocina', 'especiero', 'servilletero', 'toallero'],
        'sacada':       ['vaso', 'planta', 'autoirrigavel', 'self watering'],
        'garagem':      ['ferramentas', 'soquete'],
        'corredor':     ['sapateira', 'gorras'],
        'moveis':       ['armario', 'cadeira escritorio', 'cadeira ergonom'],
        'audio_cd':     ['caixa amplificada', 'caixa som', 'connect lights', 'zealot ze21'],
        'mochila':      ['commuter bag', 'bolsa trabalho'],
        'organizacao':  ['organizador de maquiagem', 'organizador maquiagem'],
    },
    'ME': {
        'calcados':      ['tenis', 'sapato', 'sandalia', 'sapatilha',
                          'chuck taylor', 'nike court'],
        'roupas':        ['bermuda', 'camiseta', 'vestido', 'jeans'],
        'oculos':        ['oculos'],
        'bolsas':        ['bolsa', 'tiracolo', 'arezzo', 'mochila'],
        'cintos':        ['cinto'],
        'carteiras':     ['carteira', 'porta-cartao'],
        'relogios':      ['relogio', 'quartz', 'pulsera', 'cuarzo'],
        'acessorios_me': ['cesto de roupa', 'cesto duplo', 'cesto bambu', 'kontuz', 'vittak',
                          'colmeia organizadora', 'organizador de calcinhas', 'organizadora gaveta'],
        'masculino':     ['masculino'],
        'feminino':      ['feminino'],
        'utilitarios':   ['varal'],
    },
}

def _fold(s: str) -> str:
    return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode('ascii')

def classify_subtag(title: str, tag: str) -> str:
    t = _fold(title)
    for subtag, keywords in SUBTAG_KEYWORDS.get(tag, {}).items():
        for kw in keywords:
            if _fold(kw) in t:
                return subtag
    return ''

s = SessionLocal()
updated = 0
skipped = 0

for tag_name in ['PET', 'E', 'CD', 'ME', 'ES']:
    ps = s.query(Product).filter(
        Product.tags.like(f'%"{tag_name}"%'),
        Product.subcategory == ''
    ).all()
    print(f'\n{tag_name}: {len(ps)} produto(s) sem subcategory')
    for p in ps:
        sub = classify_subtag(p.title or '', tag_name)
        if sub:
            p.subcategory = sub
            updated += 1
            print(f'  ✅ {p.title[:50]} → {sub}')
        else:
            skipped += 1

s.commit()
s.close()
print(f'\nAtualizado : {updated}')
print(f'Sem match  : {skipped}')
