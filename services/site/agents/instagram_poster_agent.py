"""
Agente Postador Instagram
Gera imagens e posta automaticamente no Instagram
"""
from typing import Any, Dict, List, Optional
from langchain.prompts import ChatPromptTemplate
from agents import BaseAgent
from services.instagram_image_service import InstagramImageGenerator
import os
import time


class InstagramPosterAgent(BaseAgent):
    """
    Agente responsável por gerar imagens e postar no Instagram
    """
    
    def __init__(self, redis_client, image_generator: InstagramImageGenerator = None):
        super().__init__(
            name="instagram_poster",
            redis_client=redis_client,
            temperature=0.5
        )
        
        self.image_generator = image_generator or InstagramImageGenerator()
        
        # Credenciais do Instagram (devem estar nas variáveis de ambiente)
        self.instagram_username = os.getenv('INSTAGRAM_USERNAME')
        self.instagram_password = os.getenv('INSTAGRAM_PASSWORD')
        
        # Cliente Instagram (lazy loading)
        self._insta_client = None
    
    @property
    def insta_client(self):
        """Lazy loading do cliente Instagram"""
        if self._insta_client is None:
            try:
                from instagrapi import Client
                self._insta_client = Client()
                
                # Verifica se já tem sessão salva
                session_file = "config/instagram_session.json"
                if os.path.exists(session_file):
                    try:
                        self._insta_client.load_settings(session_file)
                        print("✅ Sessão Instagram carregada")
                    except Exception as e:
                        print(f"⚠️  Erro ao carregar sessão: {e}")
                        self._login()
                else:
                    self._login()
                    
            except ImportError:
                print("⚠️  instagrapi não instalado. Modo simulação ativado.")
                self._insta_client = None
        
        return self._insta_client
    
    def _login(self):
        """Faz login no Instagram"""
        if not self.instagram_username or not self.instagram_password:
            print("⚠️  Credenciais Instagram não configuradas")
            return False
        
        try:
            self._insta_client.login(self.instagram_username, self.instagram_password)
            
            # Salva sessão
            session_file = "config/instagram_session.json"
            os.makedirs(os.path.dirname(session_file), exist_ok=True)
            self._insta_client.dump_settings(session_file)
            
            print(f"✅ Login Instagram realizado: @{self.instagram_username}")
            return True
        except Exception as e:
            print(f"❌ Erro no login Instagram: {e}")
            return False
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera imagem e posta no Instagram
        
        Args:
            input_data: Dict contendo:
                - enriched_product: produto enriquecido
                - post_type: 'photo' (padrão) ou 'carousel'
                - simulate: se True, não posta de verdade (para testes)
                - custom_caption: legenda personalizada opcional
        
        Returns:
            Dict com resultado da postagem
        """
        enriched_product = input_data.get('enriched_product')
        
        if not enriched_product:
            return {
                "success": False,
                "error": "Produto enriquecido não fornecido",
                "post_url": None
            }
        
        post_type = input_data.get('post_type', 'photo')
        simulate = input_data.get('simulate', False)
        
        try:
            # Gera imagem(ns)
            if post_type == 'carousel':
                image_paths = self.image_generator.generate_carousel_images(enriched_product)
            else:
                image_path = self.image_generator.generate_product_image(enriched_product)
                image_paths = [image_path]
            
            # Prepara legenda completa
            caption = self._prepare_caption(enriched_product, input_data.get('custom_caption'))
            
            # Posta no Instagram (ou simula)
            if simulate or not self.insta_client:
                print("🎭 MODO SIMULAÇÃO - Post não enviado ao Instagram")
                post_url = f"https://instagram.com/p/SIMULATED_{int(time.time())}"
                media_id = f"simulated_{int(time.time())}"
            else:
                if len(image_paths) == 1:
                    media = self.insta_client.photo_upload(
                        image_paths[0],
                        caption
                    )
                else:
                    media = self.insta_client.album_upload(
                        image_paths,
                        caption
                    )
                
                post_url = f"https://instagram.com/p/{media.code}"
                media_id = media.id
                print(f"✅ Postado no Instagram: {post_url}")
            
            # Salva na memória e histórico
            post_data = {
                "product_id": enriched_product.get('external_id'),
                "post_url": post_url,
                "media_id": media_id,
                "caption": caption,
                "image_paths": image_paths,
                "simulated": simulate
            }
            
            self._save_to_memory(post_data)
            self._save_post_history(post_data)
            
            return {
                "success": True,
                "post_url": post_url,
                "media_id": media_id,
                "image_paths": image_paths,
                "caption": caption,
                "product_id": enriched_product.get('external_id')
            }
            
        except Exception as e:
            print(f"❌ Erro ao postar no Instagram: {e}")
            return {
                "success": False,
                "error": str(e),
                "post_url": None
            }
    
    def _prepare_caption(
        self,
        enriched_product: Dict[str, Any],
        custom_caption: Optional[str] = None
    ) -> str:
        """Prepara legenda completa para o post"""
        if custom_caption:
            caption = custom_caption
        else:
            caption = enriched_product.get('caption', '')
        
        # Adiciona hashtags
        hashtags = enriched_product.get('hashtags', [])
        if hashtags:
            caption += "\n\n"
            caption += " ".join(f"#{tag.replace('#', '')}" for tag in hashtags)
        
        # Adiciona CTA
        cta = enriched_product.get('call_to_action', '')
        if cta:
            caption += f"\n\n{cta}"
        
        return caption
    
    def _save_post_history(self, post_data: Dict[str, Any]) -> None:
        """Salva histórico de posts no Redis"""
        history_key = "instagram:post_history"
        self.redis_client.lpush(history_key, str(post_data))
        # Mantém últimos 1000 posts
        self.redis_client.ltrim(history_key, 0, 999)
    
    def schedule_post(
        self,
        enriched_product: Dict[str, Any],
        scheduled_time: int
    ) -> Dict[str, Any]:
        """
        Agenda um post para horário futuro
        
        Args:
            enriched_product: produto enriquecido
            scheduled_time: timestamp unix para agendamento
        
        Returns:
            Dict com confirmação do agendamento
        """
        schedule_key = f"instagram:scheduled:{scheduled_time}"
        
        schedule_data = {
            "enriched_product": enriched_product,
            "scheduled_time": scheduled_time,
            "created_at": int(time.time())
        }
        
        import json
        self.redis_client.setex(
            schedule_key,
            scheduled_time - int(time.time()) + 3600,  # TTL até 1h após agendamento
            json.dumps(schedule_data, ensure_ascii=False)
        )
        
        return {
            "success": True,
            "scheduled": True,
            "scheduled_time": scheduled_time,
            "schedule_key": schedule_key
        }
    
    def get_post_analytics(self, media_id: str) -> Dict[str, Any]:
        """
        Busca analytics de um post (se disponível)
        
        Args:
            media_id: ID do post no Instagram
        
        Returns:
            Dict com métricas do post
        """
        if not self.insta_client:
            return {
                "success": False,
                "error": "Cliente Instagram não disponível"
            }
        
        try:
            media_info = self.insta_client.media_info(media_id)
            
            return {
                "success": True,
                "likes": media_info.like_count,
                "comments": media_info.comment_count,
                "views": getattr(media_info, 'view_count', 0),
                "caption": media_info.caption_text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
