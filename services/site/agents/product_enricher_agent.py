"""
Agente Enriquecedor de Produto
Enriquece os dados do produto com informações adicionais e
prepara descrição otimizada para Instagram
"""
from typing import Any, Dict
from langchain.prompts import ChatPromptTemplate
from agents import BaseAgent
import os


class ProductEnricherAgent(BaseAgent):
    """
    Agente responsável por enriquecer os dados do produto
    e preparar conteúdo otimizado para Instagram
    """
    
    def __init__(self, redis_client):
        super().__init__(
            name="product_enricher",
            redis_client=redis_client,
            temperature=0.7  # Temperatura moderada para criatividade
        )
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece os dados do produto
        
        Args:
            input_data: Dict contendo:
                - selected_product: produto selecionado pelo agente decisor
                - custom_context: contexto adicional opcional
        
        Returns:
            Dict com produto enriquecido incluindo:
                - caption: legenda para Instagram
                - hashtags: lista de hashtags relevantes
                - call_to_action: CTA personalizado
                - visual_suggestions: sugestões para composição visual
        """
        product = input_data.get('selected_product')
        
        if not product:
            return {
                "success": False,
                "error": "Produto não fornecido",
                "enriched_product": None
            }
        
        # Verifica cache primeiro
        cache_key = f"enriched:{product.get('external_id')}"
        cached = self._check_cache(cache_key)
        if cached and not input_data.get('force_refresh'):
            print(f"✅ Usando dados enriquecidos do cache")
            return cached
        
        # Enriquece o produto usando LLM
        enriched = self._enrich_with_llm(product, input_data.get('custom_context'))
        
        result = {
            "success": True,
            "enriched_product": enriched,
            "original_product": product
        }
        
        # Salva no cache por 24 horas
        self._save_to_cache(cache_key, result, ttl=86400)
        self._save_to_memory({"product_id": product.get('external_id'), "enriched": True})
        
        return result
    
    def _enrich_with_llm(
        self,
        product: Dict[str, Any],
        custom_context: str = None
    ) -> Dict[str, Any]:
        """Usa LLM para enriquecer os dados do produto"""
        
        title = product.get('title', '')
        price = product.get('price', 0)
        platform = product.get('platform', 'mercadolivre')
        link = product.get('link', '')
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em marketing digital para Instagram.
            Sua tarefa é criar conteúdo engajador para posts de produtos.
            
            IMPORTANTE:
            - A legenda deve ser atraente e criar desejo
            - Use emojis de forma estratégica (mas não exagere)
            - Inclua benefícios claros do produto
            - Crie senso de urgência quando apropriado
            - Mantenha tom conversacional e amigável
            - Legenda deve ter entre 100-200 caracteres
            
            Retorne um JSON com:
            - caption: legenda principal (string)
            - hashtags: lista de 8-12 hashtags relevantes (array)
            - call_to_action: chamada para ação (string)
            - visual_suggestions: sugestões para a imagem (string)
            - key_features: 3-4 características principais (array)
            """),
            ("user", """Produto:
Título: {title}
Preço: R$ {price}
Plataforma: {platform}
Link: {link}

Contexto adicional: {context}

Crie o conteúdo otimizado para Instagram.""")
        ])
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "title": title,
            "price": f"{price:.2f}",
            "platform": platform,
            "link": link if link else "Link na bio",
            "context": custom_context or "Produto de alta qualidade com ótimo custo-benefício"
        })
        
        # Parse do JSON retornado
        import json
        try:
            # Tenta extrair JSON da resposta
            response_text = response.content.strip()
            
            # Remove markdown code blocks se existirem
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            enriched_data = json.loads(response_text)
            
            # Adiciona dados originais
            enriched_data['original_title'] = title
            enriched_data['price'] = price
            enriched_data['platform'] = platform
            enriched_data['link'] = link
            enriched_data['external_id'] = product.get('external_id')
            enriched_data['images_local'] = product.get('images_local')
            enriched_data['images'] = product.get('images', [])
            enriched_data['_file'] = product.get('_file')
            
            return enriched_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Erro ao parsear JSON do LLM: {e}")
            print(f"Resposta: {response.content[:200]}")
            
            # Fallback com dados básicos
            return {
                "caption": f"🔥 {title}\n\n💰 Por apenas R$ {price:.2f}\n\n✨ Aproveite!",
                "hashtags": ["#oferta", "#promocao", "#comprasonline", "#deals"],
                "call_to_action": "🛒 Link na bio!",
                "visual_suggestions": "Imagem destacando o produto com preço em evidência",
                "key_features": ["Qualidade garantida", "Melhor preço", "Entrega rápida"],
                "original_title": title,
                "price": price,
                "platform": platform,
                "link": link,
                "external_id": product.get('external_id'),
                "images_local": product.get('images_local'),
                "images": product.get('images', []),
                "_file": product.get('_file')
            }
    
    def generate_alternative_captions(
        self,
        product: Dict[str, Any],
        num_alternatives: int = 3
    ) -> list:
        """Gera legendas alternativas para testes A/B"""
        alternatives = []
        
        for i in range(num_alternatives):
            custom_context = f"Versão {i+1}: "
            if i == 0:
                custom_context += "Tom mais promocional e urgente"
            elif i == 1:
                custom_context += "Tom mais informativo e educativo"
            else:
                custom_context += "Tom mais descontraído e divertido"
            
            enriched = self._enrich_with_llm(product, custom_context)
            alternatives.append(enriched)
        
        return alternatives
