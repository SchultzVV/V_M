#!/usr/bin/env python3
"""
Script para preparar imagens de produtos do staging para publicação no Instagram.
Gera imagens profissionais com todas as informações do produto + QR code para o link.

Uso:
    python prepare_publish_images.py [--file arquivo.json] [--all]
    
Exemplos:
    python prepare_publish_images.py --all              # Processa todos os JSONs do staging
    python prepare_publish_images.py --file produto.json # Processa um único JSON
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFont


class InstagramImageGenerator:
    """Gerador de imagens profissionais para publicação no Instagram."""
    
    # Dimensões padrão do Instagram
    IMG_SIZE = (1080, 1080)
    
    # Cores (BGR format para OpenCV)
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLACK = (0, 0, 0)
    COLOR_RED = (0, 0, 255)
    COLOR_GREEN = (0, 200, 0)
    COLOR_BLUE = (200, 100, 0)
    COLOR_GRAY = (100, 100, 100)
    COLOR_BG = (245, 245, 245)
    
    def __init__(self, staging_dir: str, output_dir: str, uploads_dir: str):
        """
        Inicializa o gerador de imagens.
        
        Args:
            staging_dir: Diretório com os JSONs dos produtos
            output_dir: Diretório de saída para as imagens geradas
            uploads_dir: Diretório com as imagens dos produtos
        """
        self.staging_dir = Path(staging_dir)
        self.output_dir = Path(output_dir)
        self.uploads_dir = Path(uploads_dir)
        
        # Criar diretório de saída se não existir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def process_all_products(self) -> List[str]:
        """
        Processa todos os JSONs da pasta staging.
        
        Returns:
            Lista com os caminhos das imagens geradas
        """
        json_files = list(self.staging_dir.glob("*.json"))
        
        if not json_files:
            print(f"⚠️  Nenhum arquivo JSON encontrado em {self.staging_dir}")
            return []
        
        print(f"📦 Encontrados {len(json_files)} produtos no staging")
        print(f"🎨 Gerando imagens para publicação...\n")
        
        generated_images = []
        
        for json_file in json_files:
            try:
                image_path = self.process_product_file(json_file)
                if image_path:
                    generated_images.append(image_path)
            except Exception as e:
                print(f"❌ Erro ao processar {json_file.name}: {e}")
                
        return generated_images
    
    def process_product_file(self, json_path: Path) -> Optional[str]:
        """
        Processa um único arquivo JSON e gera a imagem.
        
        Args:
            json_path: Caminho para o arquivo JSON do produto
            
        Returns:
            Caminho da imagem gerada ou None se falhar
        """
        try:
            # Carregar dados do produto
            with open(json_path, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            
            print(f"📸 Processando: {product_data.get('title', 'Sem título')[:50]}...")
            
            # Gerar a imagem
            image_path = self.generate_product_image(product_data, json_path.stem)
            
            if image_path:
                print(f"✅ Imagem gerada: {image_path}")
                return image_path
            else:
                print(f"⚠️  Falha ao gerar imagem para {json_path.name}")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao processar {json_path.name}: {e}")
            return None
    
    def generate_product_image(self, product: Dict, filename: str) -> Optional[str]:
        """
        Gera imagem completa do produto para Instagram.
        
        Args:
            product: Dicionário com dados do produto
            filename: Nome base para o arquivo de saída
            
        Returns:
            Caminho da imagem gerada
        """
        # Criar canvas branco
        canvas = np.ones((self.IMG_SIZE[1], self.IMG_SIZE[0], 3), dtype=np.uint8) * 255
        
        # Layout:
        # - Topo: Cabeçalho com título (180px)
        # - Meio: Imagem do produto (500px)
        # - Baixo: Informações + QR Code (400px)
        
        y_offset = 0
        
        # 1. CABEÇALHO COM TÍTULO
        y_offset = self._add_header(canvas, product, y_offset)
        
        # 2. IMAGEM DO PRODUTO
        y_offset = self._add_product_image(canvas, product, y_offset)
        
        # 3. SEÇÃO DE PREÇO E DESCONTO
        y_offset = self._add_price_section(canvas, product, y_offset)
        
        # 4. INFORMAÇÕES E QR CODE
        y_offset = self._add_info_and_qr(canvas, product, y_offset)
        
        # 5. RODAPÉ COM CTA
        self._add_footer(canvas, y_offset)
        
        # Salvar imagem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{filename}_{timestamp}.jpg"
        output_path = self.output_dir / output_filename
        
        cv2.imwrite(str(output_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        return str(output_path)
    
    def _add_header(self, canvas: np.ndarray, product: Dict, y_start: int) -> int:
        """Adiciona cabeçalho com título do produto."""
        header_height = 180
        
        # Fundo gradiente para o header
        for i in range(header_height):
            alpha = i / header_height
            color = tuple(int(245 - alpha * 45) for _ in range(3))  # Gradiente cinza claro
            cv2.line(canvas, (0, y_start + i), (self.IMG_SIZE[0], y_start + i), color, 1)
        
        # Título do produto
        title = product.get('title', 'Produto sem título')
        
        # Quebrar título em múltiplas linhas se necessário
        lines = self._wrap_text(title, max_width=900, font_scale=1.0, thickness=2, font=cv2.FONT_HERSHEY_DUPLEX)
        
        y_text = y_start + 40
        for line in lines[:3]:  # Máximo 3 linhas
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_DUPLEX, 1.0, 2)[0]
            x_text = (self.IMG_SIZE[0] - text_size[0]) // 2
            
            # Sombra
            cv2.putText(canvas, line, (x_text + 2, y_text + 2), 
                       cv2.FONT_HERSHEY_DUPLEX, 1.0, self.COLOR_GRAY, 2)
            # Texto principal
            cv2.putText(canvas, line, (x_text, y_text), 
                       cv2.FONT_HERSHEY_DUPLEX, 1.0, self.COLOR_BLACK, 2)
            
            y_text += 45
        
        return y_start + header_height
    
    def _add_product_image(self, canvas: np.ndarray, product: Dict, y_start: int) -> int:
        """Adiciona imagem principal do produto."""
        image_height = 500
        
        # Tentar carregar imagem do produto
        product_img = self._load_product_image(product)
        
        if product_img is not None:
            # Redimensionar mantendo proporção
            img_h, img_w = product_img.shape[:2]
            target_size = 480  # Tamanho máximo da imagem
            
            if img_h > img_w:
                new_h = target_size
                new_w = int(img_w * (target_size / img_h))
            else:
                new_w = target_size
                new_h = int(img_h * (target_size / img_w))
            
            product_img = cv2.resize(product_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Centralizar imagem
            x_offset = (self.IMG_SIZE[0] - new_w) // 2
            y_offset = y_start + (image_height - new_h) // 2
            
            # Adicionar borda branca
            border = 10
            cv2.rectangle(canvas, 
                         (x_offset - border, y_offset - border),
                         (x_offset + new_w + border, y_offset + new_h + border),
                         self.COLOR_GRAY, 2)
            
            # Colar imagem
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = product_img
        else:
            # Placeholder se não houver imagem
            placeholder_text = "Imagem não disponível"
            text_size = cv2.getTextSize(placeholder_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)[0]
            x_text = (self.IMG_SIZE[0] - text_size[0]) // 2
            y_text = y_start + image_height // 2
            
            cv2.putText(canvas, placeholder_text, (x_text, y_text),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, self.COLOR_GRAY, 2)
        
        return y_start + image_height
    
    def _add_price_section(self, canvas: np.ndarray, product: Dict, y_start: int) -> int:
        """Adiciona seção com preço e desconto."""
        section_height = 120
        
        # Fundo colorido para destacar
        cv2.rectangle(canvas, (0, y_start), (self.IMG_SIZE[0], y_start + section_height),
                     (240, 250, 240), -1)  # Verde claro
        
        # Extrair preços
        price = product.get('price', 'Consulte')
        old_price = product.get('oldPrice', '')
        
        y_text = y_start + 45
        
        # Preço antigo (riscado)
        if old_price:
            text = f"De: {old_price}"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            x_text = (self.IMG_SIZE[0] - text_size[0]) // 2
            
            cv2.putText(canvas, text, (x_text, y_text),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.COLOR_GRAY, 2)
            # Linha sobre o preço (riscado)
            cv2.line(canvas, (x_text, y_text - 10), (x_text + text_size[0], y_text - 10),
                    self.COLOR_RED, 2)
            
            y_text += 40
        
        # Preço atual (destaque)
        price_text = f"POR: {price}"
        text_size = cv2.getTextSize(price_text, cv2.FONT_HERSHEY_DUPLEX, 1.8, 3)[0]
        x_text = (self.IMG_SIZE[0] - text_size[0]) // 2
        
        # Sombra
        cv2.putText(canvas, price_text, (x_text + 3, y_text + 3),
                   cv2.FONT_HERSHEY_DUPLEX, 1.8, self.COLOR_GRAY, 3)
        # Preço em verde
        cv2.putText(canvas, price_text, (x_text, y_text),
                   cv2.FONT_HERSHEY_DUPLEX, 1.8, self.COLOR_GREEN, 3)
        
        return y_start + section_height
    
    def _add_info_and_qr(self, canvas: np.ndarray, product: Dict, y_start: int) -> int:
        """Adiciona informações do produto e QR code."""
        section_height = 200
        
        # Dividir em duas colunas: info (esquerda) e QR code (direita)
        
        # QR CODE (direita)
        qr_size = 180
        link = product.get('link', '')
        
        if link:
            qr_img = self._generate_qr_code(link, qr_size)
            x_qr = self.IMG_SIZE[0] - qr_size - 40
            y_qr = y_start + 10
            
            # Adicionar QR code
            canvas[y_qr:y_qr+qr_size, x_qr:x_qr+qr_size] = cv2.cvtColor(qr_img, cv2.COLOR_RGB2BGR)
            
            # Texto "Escaneie para comprar"
            qr_text = "Escaneie aqui"
            text_size = cv2.getTextSize(qr_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            x_text = x_qr + (qr_size - text_size[0]) // 2
            y_text = y_qr + qr_size + 20
            
            cv2.putText(canvas, qr_text, (x_text, y_text),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_BLACK, 1)
        
        # INFORMAÇÕES (esquerda)
        x_info = 40
        y_info = y_start + 30
        
        # Platform/Tag
        platform = product.get('platform', '').upper()
        tag = product.get('tag', '')
        
        info_text = f"Origem: {platform}"
        cv2.putText(canvas, info_text, (x_info, y_info),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_BLACK, 1)
        
        y_info += 35
        
        if tag:
            tag_text = f"Categoria: {tag}"
            cv2.putText(canvas, tag_text, (x_info, y_info),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_BLACK, 1)
            y_info += 35
        
        # Link encurtado (se couber)
        if link:
            # Encurtar link para exibição
            display_link = link[:40] + "..." if len(link) > 40 else link
            cv2.putText(canvas, "Link:", (x_info, y_info),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_GRAY, 1)
            y_info += 25
            cv2.putText(canvas, display_link, (x_info, y_info),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_BLUE, 1)
        
        return y_start + section_height
    
    def _add_footer(self, canvas: np.ndarray, y_start: int):
        """Adiciona rodapé com call-to-action."""
        footer_height = self.IMG_SIZE[1] - y_start
        
        # Fundo escuro para o footer
        cv2.rectangle(canvas, (0, y_start), (self.IMG_SIZE[0], self.IMG_SIZE[1]),
                     (50, 50, 50), -1)
        
        # Texto CTA
        cta_text = "GARANTA JÁ O SEU! 🛒"
        text_size = cv2.getTextSize(cta_text, cv2.FONT_HERSHEY_DUPLEX, 1.2, 2)[0]
        x_text = (self.IMG_SIZE[0] - text_size[0]) // 2
        y_text = y_start + footer_height // 2 + 10
        
        cv2.putText(canvas, cta_text, (x_text, y_text),
                   cv2.FONT_HERSHEY_DUPLEX, 1.2, self.COLOR_WHITE, 2)
    
    def _load_product_image(self, product: Dict) -> Optional[np.ndarray]:
        """Carrega a primeira imagem disponível do produto."""
        images_local = product.get('images_local', '')
        
        if not images_local:
            return None
        
        # Tentar carregar da pasta local
        image_dir = self.uploads_dir / images_local
        
        if not image_dir.exists():
            return None
        
        # Pegar primeira imagem disponível
        image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png")) + list(image_dir.glob("*.jpeg"))
        
        if not image_files:
            return None
        
        # Carregar primeira imagem
        try:
            img = cv2.imread(str(image_files[0]))
            return img
        except Exception as e:
            print(f"⚠️  Erro ao carregar imagem: {e}")
            return None
    
    def _generate_qr_code(self, data: str, size: int) -> np.ndarray:
        """Gera QR code com o link do produto."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Criar imagem do QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para numpy array e redimensionar
        qr_array = np.array(qr_img.convert('RGB'))
        qr_resized = cv2.resize(qr_array, (size, size), interpolation=cv2.INTER_NEAREST)
        
        return qr_resized
    
    def _wrap_text(self, text: str, max_width: int, font_scale: float, thickness: int, font=cv2.FONT_HERSHEY_DUPLEX) -> List[str]:
        """Quebra texto em múltiplas linhas para caber na largura."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            text_size = cv2.getTextSize(test_line, font, font_scale, thickness)[0]
            
            if text_size[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Prepara imagens de produtos para publicação no Instagram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  %(prog)s --all                    Processa todos os produtos do staging
  %(prog)s --file produto.json      Processa um produto específico
  %(prog)s --all --output ./custom  Define diretório de saída customizado
        """
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Processar todos os JSONs da pasta staging'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Processar um arquivo JSON específico'
    )
    
    parser.add_argument(
        '--staging-dir',
        type=str,
        default='staging',
        help='Diretório com os JSONs dos produtos (padrão: staging)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='publish_ready',
        help='Diretório de saída para as imagens (padrão: publish_ready)'
    )
    
    parser.add_argument(
        '--uploads-dir',
        type=str,
        default='uploads',
        help='Diretório com as imagens dos produtos (padrão: uploads)'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not args.all and not args.file:
        parser.print_help()
        print("\n❌ Erro: Use --all ou --file para especificar o que processar")
        sys.exit(1)
    
    # Inicializar gerador
    generator = InstagramImageGenerator(
        staging_dir=args.staging_dir,
        output_dir=args.output,
        uploads_dir=args.uploads_dir
    )
    
    print("=" * 70)
    print("🎨 GERADOR DE IMAGENS PARA INSTAGRAM")
    print("=" * 70)
    print()
    
    # Processar produtos
    if args.all:
        generated_images = generator.process_all_products()
    else:
        json_path = Path(args.staging_dir) / args.file
        if not json_path.exists():
            print(f"❌ Arquivo não encontrado: {json_path}")
            sys.exit(1)
        
        image_path = generator.process_product_file(json_path)
        generated_images = [image_path] if image_path else []
    
    # Resumo
    print()
    print("=" * 70)
    print(f"✅ Processamento concluído!")
    print(f"📊 Total de imagens geradas: {len(generated_images)}")
    print(f"📁 Diretório de saída: {args.output}")
    print("=" * 70)
    
    if generated_images:
        print("\n🖼️  Imagens geradas:")
        for img in generated_images:
            print(f"  • {img}")
    
    return 0 if generated_images else 1


if __name__ == '__main__':
    sys.exit(main())
