"""
Serviço de Geração de Imagens para Instagram
Cria imagens promocionais com preço e informações do produto
"""
import os
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import textwrap
from datetime import datetime


class InstagramImageGenerator:
    """
    Serviço responsável por gerar imagens otimizadas para Instagram
    com overlays de preço, título e informações promocionais
    """
    
    # Dimensões padrão do Instagram
    INSTAGRAM_SQUARE = (1080, 1080)
    INSTAGRAM_PORTRAIT = (1080, 1350)
    INSTAGRAM_LANDSCAPE = (1080, 566)
    
    def __init__(self, output_dir: str = "uploads/instagram"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Tenta carregar fontes do sistema
        self.fonts = self._load_fonts()
    
    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Carrega fontes disponíveis no sistema"""
        fonts = {}
        
        # Caminhos comuns de fontes
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        
        try:
            # Tenta carregar fontes em diferentes tamanhos
            for path in font_paths:
                if os.path.exists(path):
                    fonts['title'] = ImageFont.truetype(path, 72)
                    fonts['price'] = ImageFont.truetype(path, 96)
                    fonts['subtitle'] = ImageFont.truetype(path, 48)
                    fonts['small'] = ImageFont.truetype(path, 36)
                    print(f"✅ Fontes carregadas de: {path}")
                    break
        except Exception as e:
            print(f"⚠️  Erro ao carregar fontes: {e}")
            # Fallback para fonte padrão
            fonts['title'] = ImageFont.load_default()
            fonts['price'] = ImageFont.load_default()
            fonts['subtitle'] = ImageFont.load_default()
            fonts['small'] = ImageFont.load_default()
        
        return fonts
    
    def generate_product_image(
        self,
        product_data: Dict[str, Any],
        layout: str = "square",
        style: str = "modern"
    ) -> str:
        """
        Gera imagem promocional do produto
        
        Args:
            product_data: Dados enriquecidos do produto
            layout: 'square', 'portrait' ou 'landscape'
            style: 'modern', 'minimal', 'bold'
        
        Returns:
            Caminho do arquivo de imagem gerado
        """
        # Define dimensões baseado no layout
        dimensions = {
            'square': self.INSTAGRAM_SQUARE,
            'portrait': self.INSTAGRAM_PORTRAIT,
            'landscape': self.INSTAGRAM_LANDSCAPE
        }
        size = dimensions.get(layout, self.INSTAGRAM_SQUARE)
        
        # Carrega imagem do produto se disponível
        base_image = self._load_product_image(product_data, size)
        
        # Aplica estilo
        if style == "modern":
            final_image = self._apply_modern_style(base_image, product_data, size)
        elif style == "minimal":
            final_image = self._apply_minimal_style(base_image, product_data, size)
        elif style == "bold":
            final_image = self._apply_bold_style(base_image, product_data, size)
        else:
            final_image = self._apply_modern_style(base_image, product_data, size)
        
        # Salva imagem
        filename = self._generate_filename(product_data)
        output_path = os.path.join(self.output_dir, filename)
        final_image.save(output_path, quality=95, optimize=True)
        
        print(f"✅ Imagem gerada: {output_path}")
        return output_path
    
    def _load_product_image(
        self,
        product_data: Dict[str, Any],
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """Carrega e redimensiona imagem do produto"""
        images_local = product_data.get('images_local', '')
        images = product_data.get('images', [])
        
        # Tenta carregar primeira imagem local
        if images_local:
            local_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                images_local
            )
            
            if os.path.exists(local_path) and os.path.isdir(local_path):
                image_files = [
                    f for f in os.listdir(local_path)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
                ]
                
                if image_files:
                    try:
                        img_path = os.path.join(local_path, image_files[0])
                        img = Image.open(img_path)
                        img = img.convert('RGB')
                        
                        # Redimensiona mantendo aspecto e centralizando
                        img = self._resize_and_center(img, target_size)
                        return img
                    except Exception as e:
                        print(f"⚠️  Erro ao carregar imagem: {e}")
        
        # Fallback: cria imagem com gradiente
        return self._create_gradient_background(target_size)
    
    def _resize_and_center(
        self,
        img: Image.Image,
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """Redimensiona imagem mantendo proporção e centraliza"""
        # Calcula novo tamanho mantendo proporção
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # Cria canvas do tamanho alvo
        canvas = Image.new('RGB', target_size, (255, 255, 255))
        
        # Centraliza imagem no canvas
        offset = (
            (target_size[0] - img.size[0]) // 2,
            (target_size[1] - img.size[1]) // 2
        )
        canvas.paste(img, offset)
        
        return canvas
    
    def _create_gradient_background(
        self,
        size: Tuple[int, int],
        color1: Tuple[int, int, int] = (67, 97, 238),
        color2: Tuple[int, int, int] = (220, 66, 129)
    ) -> Image.Image:
        """Cria background com gradiente"""
        base = Image.new('RGB', size, color1)
        top = Image.new('RGB', size, color2)
        mask = Image.new('L', size)
        mask_data = []
        
        for y in range(size[1]):
            mask_data.extend([int(255 * (y / size[1]))] * size[0])
        
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        
        return base
    
    def _apply_modern_style(
        self,
        base_image: Image.Image,
        product_data: Dict[str, Any],
        size: Tuple[int, int]
    ) -> Image.Image:
        """Aplica estilo moderno com overlay gradiente"""
        # Escurece um pouco a imagem base
        enhancer = ImageEnhance.Brightness(base_image)
        base_image = enhancer.enhance(0.7)
        
        # Cria overlay
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Desenha retângulo semi-transparente no topo
        draw.rectangle(
            [(0, 0), (size[0], size[1] // 3)],
            fill=(0, 0, 0, 180)
        )
        
        # Desenha retângulo para preço no canto inferior
        price_height = size[1] // 4
        draw.rectangle(
            [(0, size[1] - price_height), (size[0], size[1])],
            fill=(255, 59, 48, 230)  # Vermelho vibrante
        )
        
        # Combina base com overlay
        base_image = base_image.convert('RGBA')
        base_image = Image.alpha_composite(base_image, overlay)
        
        # Adiciona textos
        draw = ImageDraw.Draw(base_image)
        
        # Título no topo
        title = product_data.get('original_title', 'Produto')
        title_wrapped = textwrap.wrap(title, width=25)
        y_text = 40
        
        for line in title_wrapped[:2]:  # Máximo 2 linhas
            bbox = draw.textbbox((0, 0), line, font=self.fonts['title'])
            text_width = bbox[2] - bbox[0]
            x_text = (size[0] - text_width) // 2
            
            # Sombra
            draw.text((x_text + 3, y_text + 3), line, font=self.fonts['title'], fill=(0, 0, 0, 255))
            # Texto
            draw.text((x_text, y_text), line, font=self.fonts['title'], fill=(255, 255, 255, 255))
            y_text += 85
        
        # Preço no rodapé
        price = product_data.get('price', 0)
        price_text = f"R$ {price:.2f}"
        
        bbox = draw.textbbox((0, 0), price_text, font=self.fonts['price'])
        text_width = bbox[2] - bbox[0]
        x_price = (size[0] - text_width) // 2
        y_price = size[1] - price_height // 2 - 60
        
        draw.text((x_price, y_price), price_text, font=self.fonts['price'], fill=(255, 255, 255, 255))
        
        # CTA
        cta = "🛒 LINK NA BIO"
        bbox = draw.textbbox((0, 0), cta, font=self.fonts['subtitle'])
        text_width = bbox[2] - bbox[0]
        x_cta = (size[0] - text_width) // 2
        y_cta = y_price + 110
        
        draw.text((x_cta, y_cta), cta, font=self.fonts['subtitle'], fill=(255, 255, 255, 255))
        
        return base_image.convert('RGB')
    
    def _apply_minimal_style(
        self,
        base_image: Image.Image,
        product_data: Dict[str, Any],
        size: Tuple[int, int]
    ) -> Image.Image:
        """Aplica estilo minimalista"""
        # Adiciona texto de forma minimalista
        draw = ImageDraw.Draw(base_image)
        
        # Preço grande no centro
        price = product_data.get('price', 0)
        price_text = f"R$ {price:.2f}"
        
        bbox = draw.textbbox((0, 0), price_text, font=self.fonts['price'])
        text_width = bbox[2] - bbox[0]
        x = (size[0] - text_width) // 2
        y = (size[1] - 100) // 2
        
        # Sombra sutil
        draw.text((x + 2, y + 2), price_text, font=self.fonts['price'], fill=(0, 0, 0, 128))
        draw.text((x, y), price_text, font=self.fonts['price'], fill=(255, 255, 255, 255))
        
        return base_image
    
    def _apply_bold_style(
        self,
        base_image: Image.Image,
        product_data: Dict[str, Any],
        size: Tuple[int, int]
    ) -> Image.Image:
        """Aplica estilo bold/chamativo"""
        # Similar ao modern mas com cores mais vibrantes
        return self._apply_modern_style(base_image, product_data, size)
    
    def _generate_filename(self, product_data: Dict[str, Any]) -> str:
        """Gera nome de arquivo único"""
        product_id = product_data.get('external_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"instagram_{product_id}_{timestamp}.jpg"
    
    def generate_carousel_images(
        self,
        product_data: Dict[str, Any],
        num_images: int = 3
    ) -> List[str]:
        """Gera múltiplas imagens para carousel do Instagram"""
        images = []
        styles = ['modern', 'minimal', 'bold']
        
        for i in range(min(num_images, len(styles))):
            img_path = self.generate_product_image(
                product_data,
                layout='square',
                style=styles[i]
            )
            images.append(img_path)
        
        return images
