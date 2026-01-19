"""
Serviço Simplificado de Geração de Imagens para Instagram
Usa OpenCV (cv2) para adicionar texto nas imagens
"""
import os
import cv2
import numpy as np
from typing import Dict, Any, Tuple
from datetime import datetime


class InstagramImageGenerator:
    """
    Serviço responsável por gerar imagens otimizadas para Instagram
    com overlays de preço usando OpenCV
    """
    
    # Dimensões padrão do Instagram
    INSTAGRAM_SQUARE = (1080, 1080)
    
    def __init__(self, output_dir: str = "uploads/instagram"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_product_image(
        self,
        product_data: Dict[str, Any],
        layout: str = "square",
        style: str = "modern"
    ) -> str:
        """
        Gera imagem promocional do produto com OpenCV
        
        Args:
            product_data: Dados enriquecidos do produto
            layout: 'square' (padrão)
            style: 'modern' (padrão)
        
        Returns:
            Caminho do arquivo de imagem gerado
        """
        size = self.INSTAGRAM_SQUARE
        
        # Carrega imagem do produto
        base_image = self._load_product_image(product_data, size)
        
        if base_image is None:
            print("⚠️  Não foi possível carregar imagem, criando background")
            base_image = self._create_solid_background(size)
        
        # Adiciona overlays com OpenCV
        final_image = self._add_text_overlays(base_image, product_data)
        
        # Salva imagem
        filename = self._generate_filename(product_data)
        output_path = os.path.join(self.output_dir, filename)
        cv2.imwrite(output_path, final_image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        print(f"✅ Imagem gerada: {output_path}")
        return output_path
    
    def _load_product_image(
        self,
        product_data: Dict[str, Any],
        target_size: Tuple[int, int]
    ) -> np.ndarray:
        """Carrega e redimensiona primeira imagem do produto"""
        images_local = product_data.get('images_local', '')
        
        if not images_local:
            return None
        
        # Caminho completo para pasta de uploads
        local_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            images_local
        )
        
        if not os.path.exists(local_path) or not os.path.isdir(local_path):
            print(f"⚠️  Pasta não encontrada: {local_path}")
            return None
        
        # Lista imagens na pasta
        image_files = [
            f for f in os.listdir(local_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ]
        
        if not image_files:
            print(f"⚠️  Nenhuma imagem encontrada em: {local_path}")
            return None
        
        # Pega primeira imagem
        img_path = os.path.join(local_path, image_files[0])
        
        try:
            # Carrega com OpenCV
            img = cv2.imread(img_path)
            
            if img is None:
                print(f"⚠️  Erro ao carregar: {img_path}")
                return None
            
            # Redimensiona mantendo aspecto
            img_resized = self._resize_and_center(img, target_size)
            
            return img_resized
            
        except Exception as e:
            print(f"⚠️  Erro ao processar imagem: {e}")
            return None
    
    def _resize_and_center(
        self,
        img: np.ndarray,
        target_size: Tuple[int, int]
    ) -> np.ndarray:
        """Redimensiona imagem mantendo proporção e centraliza"""
        h, w = img.shape[:2]
        target_w, target_h = target_size
        
        # Calcula escala
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Redimensiona
        img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Cria canvas branco
        canvas = np.ones((target_h, target_w, 3), dtype=np.uint8) * 255
        
        # Centraliza
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = img_resized
        
        return canvas
    
    def _create_solid_background(self, size: Tuple[int, int]) -> np.ndarray:
        """Cria background sólido"""
        # Background azul
        bg = np.ones((size[1], size[0], 3), dtype=np.uint8)
        bg[:] = (238, 97, 67)  # BGR: Laranja/vermelho
        return bg
    
    def _add_text_overlays(
        self,
        img: np.ndarray,
        product_data: Dict[str, Any]
    ) -> np.ndarray:
        """Adiciona overlays de texto com OpenCV"""
        h, w = img.shape[:2]
        
        # Cria overlay semi-transparente no topo
        overlay = img.copy()
        
        # Retângulo preto no topo (para título)
        cv2.rectangle(overlay, (0, 0), (w, h // 4), (0, 0, 0), -1)
        
        # Retângulo vermelho no rodapé (para preço)
        cv2.rectangle(overlay, (0, h - h // 4), (w, h), (48, 59, 255), -1)
        
        # Mistura com transparência
        alpha = 0.7
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        
        # Adiciona título
        title = product_data.get('original_title', 'Produto')
        title_lines = self._wrap_text(title, 30)
        
        y_text = 60
        for line in title_lines[:2]:  # Max 2 linhas
            # Texto com borda para legibilidade
            self._put_text_with_border(
                img, line,
                (w // 2, y_text),
                font_scale=1.2,
                color=(255, 255, 255),
                thickness=2
            )
            y_text += 70
        
        # Adiciona preço
        price = product_data.get('price', 0)
        price_text = f"R$ {price:.2f}"
        
        self._put_text_with_border(
            img, price_text,
            (w // 2, h - h // 4 + 80),
            font_scale=2.5,
            color=(255, 255, 255),
            thickness=4
        )
        
        # Adiciona CTA
        cta = "🛒 LINK NA BIO"
        self._put_text_with_border(
            img, cta,
            (w // 2, h - 60),
            font_scale=1.0,
            color=(255, 255, 255),
            thickness=2
        )
        
        return img
    
    def _put_text_with_border(
        self,
        img: np.ndarray,
        text: str,
        position: Tuple[int, int],
        font_scale: float = 1.0,
        color: Tuple[int, int, int] = (255, 255, 255),
        thickness: int = 2
    ):
        """Adiciona texto centralizado com borda preta"""
        font = cv2.FONT_HERSHEY_BOLD
        
        # Calcula tamanho do texto
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Posição centralizada
        x = position[0] - text_w // 2
        y = position[1] + text_h // 2
        
        # Borda preta (sombra)
        cv2.putText(img, text, (x + 3, y + 3), font, font_scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        
        # Texto principal
        cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    def _wrap_text(self, text: str, max_chars: int) -> list:
        """Quebra texto em múltiplas linhas"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _generate_filename(self, product_data: Dict[str, Any]) -> str:
        """Gera nome de arquivo único"""
        product_id = product_data.get('external_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"instagram_{product_id}_{timestamp}.jpg"
