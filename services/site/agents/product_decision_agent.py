"""
Agente Decisor de Produto
Seleciona o melhor produto do staging para postar no Instagram
baseado em critérios como engajamento potencial, preço, disponibilidade, etc.
"""
import os
import json
import glob
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from agents import BaseAgent


class ProductDecisionAgent(BaseAgent):
    """
    Agente responsável por decidir qual produto do staging deve ser postado
    no Instagram com base em critérios estratégicos.
    """
    
    def __init__(self, redis_client, staging_dir: str = "staging"):
        super().__init__(
            name="product_decision",
            redis_client=redis_client,
            temperature=0.3  # Baixa temperatura para decisões mais consistentes
        )
        self.staging_dir = staging_dir
        
    def _load_staging_products(self) -> List[Dict[str, Any]]:
        """Carrega todos os produtos do diretório staging"""
        staging_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.staging_dir
        )
        
        products = []
        json_files = glob.glob(os.path.join(staging_path, "*.json"))
        
        for json_file in json_files:
            # Ignora arquivos de controle
            if json_file.endswith(".processed"):
                continue
                
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    product = json.load(f)
                    product['_file'] = os.path.basename(json_file)
                    products.append(product)
            except Exception as e:
                print(f"⚠️  Erro ao carregar {json_file}: {e}")
        
        return products
    
    def _get_posted_history(self) -> List[str]:
        """Recupera histórico de produtos já postados no Instagram"""
        history_key = "instagram:posted_products"
        posted = self.redis_client.lrange(history_key, 0, -1)
        return [p.decode('utf-8') for p in posted]
    
    def _mark_as_posted(self, product_id: str) -> None:
        """Marca produto como já postado"""
        history_key = "instagram:posted_products"
        self.redis_client.lpush(history_key, product_id)
        # Mantém histórico dos últimos 500 produtos
        self.redis_client.ltrim(history_key, 0, 499)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seleciona o melhor produto para postar no Instagram
        
        Args:
            input_data: Pode conter filtros opcionais como:
                - tag: filtrar por tag específica
                - min_price: preço mínimo
                - max_price: preço máximo
                - force_product_id: forçar produto específico
        
        Returns:
            Dict com produto selecionado e justificativa
        """
        # Carrega produtos do staging
        products = self._load_staging_products()
        
        if not products:
            return {
                "success": False,
                "error": "Nenhum produto encontrado no staging",
                "selected_product": None
            }
        
        # Filtra produtos já postados
        posted_history = self._get_posted_history()
        available_products = [
            p for p in products 
            if p.get('external_id') not in posted_history
        ]
        
        if not available_products:
            # Se todos já foram postados, reseta e usa todos novamente
            print("♻️  Todos os produtos já foram postados. Resetando histórico.")
            available_products = products
        
        # Aplica filtros se fornecidos
        if input_data.get('tag'):
            available_products = [
                p for p in available_products
                if p.get('tag') == input_data['tag']
            ]
        
        if input_data.get('min_price'):
            available_products = [
                p for p in available_products
                if p.get('price', 0) >= input_data['min_price']
            ]
        
        if input_data.get('max_price'):
            available_products = [
                p for p in available_products
                if p.get('price', float('inf')) <= input_data['max_price']
            ]
        
        # Se foi especificado um produto, usa ele
        if input_data.get('force_product_id'):
            forced = [
                p for p in available_products
                if p.get('external_id') == input_data['force_product_id']
            ]
            if forced:
                selected = forced[0]
                return {
                    "success": True,
                    "selected_product": selected,
                    "reason": "Produto forçado pelo usuário",
                    "method": "forced"
                }
        
        # Usa LLM para escolher o melhor produto
        selected = self._llm_select_product(available_products, input_data)
        
        # Marca como postado
        if selected.get('external_id'):
            self._mark_as_posted(selected['external_id'])
        
        return {
            "success": True,
            "selected_product": selected,
            "reason": selected.get('_selection_reason'),
            "method": "llm_selection",
            "total_available": len(available_products)
        }
    
    def _llm_select_product(
        self,
        products: List[Dict[str, Any]],
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Usa LLM para selecionar o melhor produto"""
        
        # Cria resumo dos produtos para o LLM
        products_summary = []
        for i, p in enumerate(products, 1):
            products_summary.append({
                "index": i,
                "id": p.get('external_id'),
                "title": p.get('title'),
                "price": p.get('price'),
                "tag": p.get('tag'),
                "platform": p.get('platform'),
                "disponivel": p.get('disponivel', True)
            })
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em marketing de produtos no Instagram.
            Sua tarefa é selecionar o MELHOR produto para postar baseado em:
            
            1. Apelo visual potencial
            2. Preço atraente (nem muito caro, nem muito barato)
            3. Relevância para a audiência
            4. Variedade (evitar postar produtos similares consecutivamente)
            5. Disponibilidade
            
            Analise os produtos e retorne APENAS o número do index do produto escolhido
            seguido de uma breve justificativa (max 50 palavras).
            
            Formato: INDEX|Justificativa
            Exemplo: 3|Produto com excelente relação custo-benefício e alto apelo visual para Instagram"""),
            ("user", "Produtos disponíveis:\n{products}\n\nCritérios adicionais: {criteria}\n\nQual produto você escolhe?")
        ])
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "products": json.dumps(products_summary, ensure_ascii=False, indent=2),
            "criteria": json.dumps(criteria, ensure_ascii=False)
        })
        
        # Parse da resposta
        response_text = response.content.strip()
        try:
            parts = response_text.split('|', 1)
            selected_index = int(parts[0].strip()) - 1
            reason = parts[1].strip() if len(parts) > 1 else "Selecionado pelo agente"
            
            selected_product = products[selected_index].copy()
            selected_product['_selection_reason'] = reason
            
            return selected_product
        except (ValueError, IndexError) as e:
            # Fallback: retorna o primeiro produto
            print(f"⚠️  Erro ao parsear resposta do LLM: {e}")
            fallback = products[0].copy()
            fallback['_selection_reason'] = "Seleção automática (fallback)"
            return fallback
