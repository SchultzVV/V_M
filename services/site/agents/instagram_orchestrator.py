"""
Orquestrador LangGraph - Sistema de Postagem Automática Instagram
Conecta os três agentes (Decisor, Enriquecedor, Postador) em um fluxo coordenado
"""
from typing import TypedDict, Annotated, Any, Dict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
import operator
from agents.product_decision_agent import ProductDecisionAgent
from agents.product_enricher_agent import ProductEnricherAgent
from agents.instagram_poster_agent import InstagramPosterAgent
from services.instagram_image_service import InstagramImageGenerator
import redis
import os


# Define o estado do grafo
class InstagramPostState(TypedDict):
    """Estado compartilhado entre os nós do grafo"""
    # Inputs
    filters: Dict[str, Any]  # Filtros para seleção de produto
    simulate: bool  # Se True, não posta de verdade
    custom_caption: str  # Legenda customizada opcional
    post_type: str  # 'photo' ou 'carousel'
    
    # Outputs intermediários
    selected_product: Dict[str, Any]
    enriched_product: Dict[str, Any]
    post_result: Dict[str, Any]
    
    # Controle de fluxo
    errors: Annotated[list, operator.add]
    step: str


class InstagramPostOrchestrator:
    """
    Orquestrador principal que gerencia o fluxo completo
    de postagem automática no Instagram usando LangGraph
    """
    
    def __init__(self, redis_url: str = None):
        """
        Inicializa o orquestrador e todos os agentes
        
        Args:
            redis_url: URL de conexão do Redis (ex: redis://localhost:6379)
        """
        # Configura Redis
        redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        
        print(f"🔗 Conectando ao Redis: {redis_url}")
        
        # Inicializa agentes
        self.decision_agent = ProductDecisionAgent(self.redis_client)
        self.enricher_agent = ProductEnricherAgent(self.redis_client)
        
        image_generator = InstagramImageGenerator()
        self.poster_agent = InstagramPosterAgent(self.redis_client, image_generator)
        
        # Constrói o grafo
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        
        print("✅ Orquestrador Instagram inicializado")
    
    def _build_workflow(self) -> StateGraph:
        """Constrói o grafo de workflow com LangGraph"""
        
        workflow = StateGraph(InstagramPostState)
        
        # Adiciona nós (agentes)
        workflow.add_node("decide_product", self._decide_product_node)
        workflow.add_node("enrich_product", self._enrich_product_node)
        workflow.add_node("post_instagram", self._post_instagram_node)
        
        # Define fluxo
        workflow.set_entry_point("decide_product")
        
        workflow.add_edge("decide_product", "enrich_product")
        workflow.add_edge("enrich_product", "post_instagram")
        workflow.add_edge("post_instagram", END)
        
        return workflow
    
    def _decide_product_node(self, state: InstagramPostState) -> InstagramPostState:
        """Nó que executa o Agente Decisor"""
        print("\n🎯 Executando Agente Decisor de Produto...")
        
        try:
            result = self.decision_agent.execute(state.get('filters', {}))
            
            if result.get('success'):
                state['selected_product'] = result['selected_product']
                state['step'] = 'product_selected'
                print(f"✅ Produto selecionado: {result['selected_product'].get('title')[:50]}...")
            else:
                state['errors'].append(f"Decisor: {result.get('error')}")
                state['step'] = 'error'
                
        except Exception as e:
            state['errors'].append(f"Decisor exception: {str(e)}")
            state['step'] = 'error'
        
        return state
    
    def _enrich_product_node(self, state: InstagramPostState) -> InstagramPostState:
        """Nó que executa o Agente Enriquecedor"""
        print("\n🎨 Executando Agente Enriquecedor...")
        
        if state.get('step') == 'error':
            return state
        
        try:
            result = self.enricher_agent.execute({
                'selected_product': state['selected_product']
            })
            
            if result.get('success'):
                state['enriched_product'] = result['enriched_product']
                state['step'] = 'product_enriched'
                print(f"✅ Produto enriquecido com legenda e hashtags")
            else:
                state['errors'].append(f"Enriquecedor: {result.get('error')}")
                state['step'] = 'error'
                
        except Exception as e:
            state['errors'].append(f"Enriquecedor exception: {str(e)}")
            state['step'] = 'error'
        
        return state
    
    def _post_instagram_node(self, state: InstagramPostState) -> InstagramPostState:
        """Nó que executa o Agente Postador"""
        print("\n📸 Executando Agente Postador Instagram...")
        
        if state.get('step') == 'error':
            return state
        
        try:
            result = self.poster_agent.execute({
                'enriched_product': state['enriched_product'],
                'simulate': state.get('simulate', False),
                'post_type': state.get('post_type', 'photo'),
                'custom_caption': state.get('custom_caption')
            })
            
            if result.get('success'):
                state['post_result'] = result
                state['step'] = 'completed'
                print(f"✅ Post criado: {result.get('post_url')}")
            else:
                state['errors'].append(f"Postador: {result.get('error')}")
                state['step'] = 'error'
                
        except Exception as e:
            state['errors'].append(f"Postador exception: {str(e)}")
            state['step'] = 'error'
        
        return state
    
    def run(
        self,
        filters: Dict[str, Any] = None,
        simulate: bool = False,
        custom_caption: str = None,
        post_type: str = 'photo'
    ) -> Dict[str, Any]:
        """
        Executa o fluxo completo de postagem
        
        Args:
            filters: Filtros para seleção de produto (tag, preço, etc)
            simulate: Se True, não posta de verdade (para testes)
            custom_caption: Legenda personalizada
            post_type: 'photo' ou 'carousel'
        
        Returns:
            Dict com resultado completo do fluxo
        """
        print("\n" + "="*60)
        print("🚀 INICIANDO FLUXO DE POSTAGEM INSTAGRAM")
        print("="*60)
        
        # Estado inicial
        initial_state = {
            'filters': filters or {},
            'simulate': simulate,
            'custom_caption': custom_caption,
            'post_type': post_type,
            'selected_product': None,
            'enriched_product': None,
            'post_result': None,
            'errors': [],
            'step': 'init'
        }
        
        # Executa o workflow
        final_state = self.app.invoke(initial_state)
        
        # Prepara resultado
        result = {
            'success': final_state['step'] == 'completed',
            'step': final_state['step'],
            'errors': final_state.get('errors', []),
            'selected_product': final_state.get('selected_product'),
            'enriched_product': final_state.get('enriched_product'),
            'post_result': final_state.get('post_result')
        }
        
        print("\n" + "="*60)
        if result['success']:
            print("✅ FLUXO COMPLETADO COM SUCESSO!")
            print(f"📸 Post URL: {result['post_result'].get('post_url')}")
        else:
            print("❌ FLUXO COMPLETADO COM ERROS")
            for error in result['errors']:
                print(f"   - {error}")
        print("="*60 + "\n")
        
        return result
    
    def run_async_schedule(
        self,
        scheduled_time: int,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Agenda uma postagem para execução futura
        
        Args:
            scheduled_time: timestamp unix do horário desejado
            filters: filtros para seleção de produto
        
        Returns:
            Dict com confirmação do agendamento
        """
        import json
        
        schedule_key = f"instagram:schedule:{scheduled_time}"
        schedule_data = {
            'filters': filters or {},
            'scheduled_time': scheduled_time
        }
        
        # TTL até 1h após o horário agendado
        import time
        ttl = scheduled_time - int(time.time()) + 3600
        
        self.redis_client.setex(
            schedule_key,
            ttl,
            json.dumps(schedule_data, ensure_ascii=False)
        )
        
        print(f"⏰ Postagem agendada para: {scheduled_time}")
        
        return {
            'success': True,
            'scheduled': True,
            'scheduled_time': scheduled_time,
            'schedule_key': schedule_key
        }
    
    def get_workflow_diagram(self) -> str:
        """Retorna representação em texto do workflow"""
        diagram = """
        Fluxo de Postagem Instagram
        ============================
        
        1. [Agente Decisor]
           ↓
           Seleciona produto do staging
           baseado em critérios inteligentes
           ↓
        2. [Agente Enriquecedor]
           ↓
           Enriquece dados com LLM:
           - Gera legenda otimizada
           - Seleciona hashtags
           - Cria CTA
           ↓
        3. [Agente Postador]
           ↓
           - Gera imagem com preço/info
           - Posta no Instagram
           - Registra no histórico
           ↓
        [FIM] ✅
        """
        return diagram


# Singleton global (opcional)
_orchestrator_instance = None

def get_orchestrator(redis_url: str = None) -> InstagramPostOrchestrator:
    """Retorna instância singleton do orquestrador"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = InstagramPostOrchestrator(redis_url)
    
    return _orchestrator_instance
