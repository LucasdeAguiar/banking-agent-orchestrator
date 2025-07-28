from agents import Agent, handoff, Runner, function_tool
from agentes.emprestimo_agent import EmprestimoAgent
from agentes.analise_risco_agent import AnaliseRiscoAgent
from agentes.web_search_agent import WebSearchAgent
from agentes.file_search_agent import FileSearchAgent
from utils.historico_manager import HistoricoManager
from utils.guardrails import GuardRailsManager
from utils.file_utils import carregar_prompt
from openai import OpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

# Configuração para instanciar agentes legados
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Instanciar gerenciadores centralizados
historico_manager = HistoricoManager(limite_mensagens_por_agente=5)
guardrails_manager = GuardRailsManager(client, debug=True)

# Instanciar agentes legados
emprestimo_legacy = EmprestimoAgent()
analise_risco_legacy = AnaliseRiscoAgent()
web_search_legacy = WebSearchAgent(client)
file_search_legacy = FileSearchAgent(client)

# Ferramentas (function_tool) conectadas às implementações reais
@function_tool
def emprestimo_tool(cpf: str, valor: float, qtd_parcelas: int) -> str:
    """Simula empréstimo usando a lógica real do EmprestimoAgent"""
    print(f"🏦 [EMPRESTIMO_AGENT] Processando empréstimo: CPF={cpf}, Valor=R${valor}, Parcelas={qtd_parcelas}")
    base_usuarios = _context_data.get('base_usuarios', {})
    result = emprestimo_legacy.processar(cpf, valor, qtd_parcelas, base_usuarios)
    print(f"🏦 [EMPRESTIMO_AGENT] Resultado: {result.get('aprovado', 'N/A')}")
    # Salvar informação do agente usado
    _context_data['last_agent_used'] = 'emprestimo_agent'
    return result["mensagem"]

@function_tool
def analise_risco_tool(cpf: str) -> str:
    """Analisa risco usando a lógica real do AnaliseRiscoAgent"""
    print(f"📊 [ANALISE_RISCO_AGENT] Analisando risco para CPF={cpf}")
    base_usuarios = _context_data.get('base_usuarios', {})
    historico = _context_data.get('historico', None)
    result = analise_risco_legacy.processar(cpf, base_usuarios, historico)
    print(f"📊 [ANALISE_RISCO_AGENT] Nível de risco: {result.get('analise', {}).get('nivel_risco', 'N/A')}")
    # Salvar informação do agente usado
    _context_data['last_agent_used'] = 'analise_risco_agent'
    return result["mensagem"]

@function_tool
def web_search_tool(pergunta: str) -> str:
    """Busca web usando a lógica real do WebSearchAgent"""
    print(f"🌐 [WEB_SEARCH_AGENT] Buscando na web: {pergunta[:50]}...")
    result = web_search_legacy.processar(pergunta)
    print("🌐 [WEB_SEARCH_AGENT] Busca realizada com sucesso")
    # Salvar informação do agente usado
    _context_data['last_agent_used'] = 'web_search_agent'
    return result.get("mensagem", "Busca realizada com sucesso")

@function_tool
def file_search_tool(cpf: str, pergunta: str) -> str:
    """Busca no histórico usando a lógica real do FileSearchAgent"""
    print(f"📁 [FILE_SEARCH_AGENT] Buscando no histórico: CPF={cpf}, Pergunta={pergunta[:50]}...")
    result = file_search_legacy.processar(cpf, pergunta)
    print("📁 [FILE_SEARCH_AGENT] Busca no histórico realizada")
    # Salvar informação do agente usado
    _context_data['last_agent_used'] = 'file_search_agent'
    return result.get("mensagem", "Busca no histórico realizada")

# Agentes especialistas
emprestimo_agent = Agent(
    name="Especialista em Empréstimos",
    instructions="""Você é especialista em empréstimos consignados da Caixa Econômica Federal. 
    Quando receber uma solicitação de empréstimo, use a ferramenta emprestimo_tool com CPF, valor e quantidade de parcelas.
    Sempre forneça informações claras sobre aprovação/reprovação e condições do empréstimo.""",
    tools=[emprestimo_tool],
)

analise_risco_agent = Agent(
    name="Especialista em Análise de Risco", 
    instructions="""Você é especialista em análise de risco bancário.
    Use a ferramenta analise_risco_tool para analisar o perfil do cliente baseado no CPF e histórico.
    Forneça análises detalhadas sobre score, fatores de risco e recomendações.""",
    tools=[analise_risco_tool],
)

web_search_agent = Agent(
    name="Especialista em Busca Web",
    instructions="""Você é especialista em buscar informações bancárias atualizadas na internet.
    Use a ferramenta web_search_tool para buscar informações sobre taxas, regulamentações, notícias bancárias.
    Sempre cite que as informações são atualizadas da web.""",
    tools=[web_search_tool],
)

file_search_agent = Agent(
    name="Especialista em Histórico de Transações",
    instructions="""Você é especialista em analisar o histórico de transações bancárias do cliente.
    Use a ferramenta file_search_tool para buscar informações sobre extratos, gastos e movimentações.
    Forneça análises claras e organizadas sobre o histórico financeiro.""",
    tools=[file_search_tool],
)

# Orquestrador (triage) com handoffs
triage_agent = Agent(
    name="Triage Agent",
    instructions="""Você é um assistente jurídico especializado em FGTS e empréstimos consignados da Caixa Econômica Federal.

    Analise a solicitação do usuário e faça handoff para o agente especialista adequado:
    
    - Para empréstimos: pergunte valor e parcelas, depois faça handoff para o Especialista em Empréstimos
    - Para análise de risco/perfil creditício: faça handoff para o Especialista em Análise de Risco  
    - Para informações atualizadas (taxas, notícias, regulamentações): faça handoff para o Especialista em Busca Web
    - Para histórico de transações/extratos: faça handoff para o Especialista em Histórico de Transações
    
    Sempre mantenha o contexto bancário e seja cordial com o cliente.""",
    handoffs=[
        handoff(emprestimo_agent),
        handoff(analise_risco_agent), 
        handoff(web_search_agent),
        handoff(file_search_agent),
    ],
)

# Instanciar gerenciador de histórico
historico_manager = HistoricoManager(limite_mensagens_por_agente=5)

def enviar_boas_vindas(nome: str, historico: list) -> None:
    """Gera mensagem de boas-vindas personalizada usando o prompt base"""
    prompt_base = carregar_prompt()
    mensagem_trigger = f"PRIMEIRA_INTERACAO: {nome}"
    
    try:
        mensagens = [
            {"role": "system", "content": prompt_base},
            {"role": "system", "content": mensagem_trigger}
        ]
        
        resposta = client.chat.completions.create(
            model="gpt-4o",
            messages=mensagens,
            temperature=0.3
        )
        
        mensagem_boas_vindas = resposta.choices[0].message.content.strip()
        print(f"\nAssistente: {mensagem_boas_vindas}\n")
        
        historico.append({
            "role": "assistant",
            "content": mensagem_boas_vindas,
            "agent": "assistant_inicial"
        })
        
    except Exception as e:
        print(f"[ERRO] Erro ao gerar boas-vindas: {e}")
        mensagem_fallback = f"Olá {nome}, seja bem-vindo(a) ao atendimento Caixa! Como posso ajudá-lo hoje? 😊"
        print(f"\nAssistente: {mensagem_fallback}\n")
        
        historico.append({
            "role": "assistant", 
            "content": mensagem_fallback,
            "agent": "assistant_inicial"
        })

# Função para rodar o loop do agente com contexto
def run_agent_loop(user_message: str, context_data: dict = None):
    """Executa o loop do agente com guardrails, limitação de histórico e contexto da sessão"""
    try:
        # 1. APLICAR GUARDRAILS ANTES DO PROCESSAMENTO
        print("🛡️ [GUARDRAILS] Verificando segurança da mensagem...")
        bloqueado, mensagem_erro = guardrails_manager.aplicar_guardrails(user_message)
        if bloqueado:
            print(f"🚫 [GUARDRAIL] Mensagem bloqueada: {mensagem_erro}")
            return mensagem_erro, "guardrail"
        
        # 2. PREPARAR CONTEXTO GLOBAL PARA AS FERRAMENTAS
        global _context_data
        _context_data = context_data or {}
        _context_data['last_agent_used'] = 'triage_agent'  # Inicializar com triage
        
        print(f"🎯 [TRIAGE_AGENT] Processando mensagem: {user_message[:50]}...")
        
        # 3. APLICAR LIMITAÇÃO DE HISTÓRICO USANDO HISTORICO_MANAGER
        historico_original = _context_data.get('historico', [])
        
        # Usar HistoricoManager para aplicar limitação por agente
        if len(historico_original) > 15:  # Se histórico muito grande
            print("⚠️ [HISTORICO] Histórico grande detectado, aplicando limitação via HistoricoManager...")
            # Aqui podemos usar o HistoricoManager para contexto específico por agente quando necessário
            print(f"📊 [HISTORICO] Histórico disponível: {len(historico_original)} mensagens")
        else:
            print(f"📊 [HISTORICO] Histórico OK: {len(historico_original)} mensagens")
        
        # 4. ADICIONAR CONTEXTO DA SESSÃO
        if context_data:
            context_message = f"Contexto da sessão: CPF={context_data.get('cpf', '')}, Nome={context_data.get('nome', '')}"
            full_message = f"{context_message}\n\nUsuário: {user_message}"
        else:
            full_message = user_message
            
        # 5. EXECUTAR AGENTE COM HANDOFF/ORCHESTRATION
        result = Runner.run_sync(triage_agent, full_message)
        
        # 6. DETERMINAR QUAL AGENTE FOI EFETIVAMENTE USADO
        agent_used = _context_data.get('last_agent_used', 'triage_agent')
        print(f"✅ [RESULTADO] Agente usado: {agent_used}")
        
        return result.final_output, agent_used
        
    except Exception as e:
        print(f"[ERRO] Erro no run_agent_loop: {e}")
        return "Desculpe, ocorreu um erro interno. Tente novamente.", "assistant_erro"

# Variável global para passar contexto para as ferramentas
_context_data = {}
