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

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

historico_manager = HistoricoManager(limite_mensagens_por_agente=5)
guardrails_manager = GuardRailsManager(client, debug=True)

emprestimo_agent = EmprestimoAgent()
analise_risco_agent = AnaliseRiscoAgent()
web_search_agent = WebSearchAgent(client)
file_search_agent = FileSearchAgent(client)

@function_tool
def emprestimo_tool(cpf: str, valor: float, qtd_parcelas: int) -> str:
    """Simula empréstimo usando a lógica real do EmprestimoAgent"""
    try:
        print(f"🏦 [EMPRESTIMO_AGENT] Processando empréstimo: CPF={cpf}, Valor=R${valor}, Parcelas={qtd_parcelas}")
        base_usuarios = _context_data.get('base_usuarios', {})
        if not base_usuarios:
            print("❌ [EMPRESTIMO_AGENT] Base de usuários não encontrada no contexto")
            return "Erro interno: base de usuários não disponível."
        
        result = emprestimo_agent.processar(cpf, valor, qtd_parcelas, base_usuarios)
        print(f"🏦 [EMPRESTIMO_AGENT] Resultado: {result.get('aprovado', 'N/A')}")
     
        _context_data['last_agent_used'] = 'emprestimo_agent'
        return result["mensagem"]
    except Exception as e:
        print(f"❌ [EMPRESTIMO_AGENT] Erro: {e}")
        import traceback
        traceback.print_exc()
        return f"Erro ao processar empréstimo: {str(e)}"

@function_tool
def analise_risco_tool(cpf: str) -> str:
    """Analisa risco usando a lógica real do AnaliseRiscoAgent"""
    print(f"📊 [ANALISE_RISCO_AGENT] Analisando risco para CPF={cpf}")
    base_usuarios = _context_data.get('base_usuarios', {})
    historico = _context_data.get('historico', None)
    result = analise_risco_agent.processar(cpf, base_usuarios, historico)
    print(f"📊 [ANALISE_RISCO_AGENT] Nível de risco: {result.get('analise', {}).get('nivel_risco', 'N/A')}")
  
    _context_data['last_agent_used'] = 'analise_risco_agent'
    return result["mensagem"]

@function_tool
def web_search_tool(pergunta: str) -> str:
    """Busca web usando a lógica real do WebSearchAgent"""
    try:
        print(f"🌐 [WEB_SEARCH_AGENT] Buscando na web: {pergunta[:50]}...")
        result = web_search_agent.processar(pergunta)
        print("🌐 [WEB_SEARCH_AGENT] Busca realizada com sucesso")
       
        _context_data['last_agent_used'] = 'web_search_agent'
        return result.get("mensagem", "Busca realizada com sucesso")
    except Exception as e:
        print(f"❌ [WEB_SEARCH_AGENT] Erro: {e}")
        import traceback
        traceback.print_exc()
        return f"Erro ao realizar busca web: {str(e)}"

@function_tool
def file_search_tool(cpf: str, pergunta: str) -> str:
    """Busca no histórico usando a lógica real do FileSearchAgent"""
    try:
        print(f"📁 [FILE_SEARCH_AGENT] Buscando no histórico: CPF={cpf}, Pergunta={pergunta[:50]}...")
        result = file_search_agent.processar(cpf, pergunta)
        print("📁 [FILE_SEARCH_AGENT] Busca no histórico realizada")
       
        _context_data['last_agent_used'] = 'file_search_agent'
        return result.get("mensagem", "Busca no histórico realizada")
    except Exception as e:
        print(f"❌ [FILE_SEARCH_AGENT] Erro: {e}")
        import traceback
        traceback.print_exc()
        return f"Erro ao buscar no histórico: {str(e)}"

emprestimo_openai_agent = Agent(
    name="Especialista em Empréstimos",
    instructions="""Você é especialista em empréstimos consignados da Caixa Econômica Federal. 
    Quando receber uma solicitação de empréstimo, use a ferramenta emprestimo_tool com CPF, valor e quantidade de parcelas.
    Sempre forneça informações claras sobre aprovação/reprovação e condições do empréstimo.""",
    tools=[emprestimo_tool],
)

analise_risco_openai_agent = Agent(
    name="Especialista em Análise de Risco", 
    instructions="""Você é especialista em análise de risco bancário.
    Use a ferramenta analise_risco_tool para analisar o perfil do cliente baseado no CPF e histórico.
    Forneça análises detalhadas sobre score, fatores de risco e recomendações.""",
    tools=[analise_risco_tool],
)

web_search_openai_agent = Agent(
    name="Especialista em Busca Web",
    instructions="""Você é especialista em buscar informações bancárias atualizadas na internet.
    Use a ferramenta web_search_tool para buscar informações sobre taxas, regulamentações, notícias bancárias.
    Sempre cite que as informações são atualizadas da web.""",
    tools=[web_search_tool],
)

file_search_openai_agent = Agent(
    name="Especialista em Histórico de Transações",
    instructions="""Você é especialista em analisar o histórico de transações bancárias do cliente.
    Use a ferramenta file_search_tool para buscar informações sobre extratos, gastos e movimentações.
    Forneça análises claras e organizadas sobre o histórico financeiro.""",
    tools=[file_search_tool],
)

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
        handoff(emprestimo_openai_agent),
        handoff(analise_risco_openai_agent), 
        handoff(web_search_openai_agent),
        handoff(file_search_openai_agent),
    ],
)

historico_manager = HistoricoManager(limite_mensagens_por_agente=5)

def run_agent_loop(user_message: str, context_data: dict = None):
    """Executa o loop do agente com guardrails, limitação de histórico e contexto da sessão"""
    try:
        print("🛡️ [GUARDRAILS] Verificando segurança da mensagem...")
        bloqueado, mensagem_erro = guardrails_manager.aplicar_guardrails(user_message)
        if bloqueado:
            print(f"🚫 [GUARDRAIL] Mensagem bloqueada: {mensagem_erro}")
            return mensagem_erro, "guardrail"
        
        global _context_data
        _context_data = context_data or {}
        _context_data['last_agent_used'] = 'triage_agent' 
        
        print(f"🎯 [TRIAGE_AGENT] Processando mensagem: {user_message[:50]}...")
        
        historico_original = _context_data.get('historico', [])
        
        if len(historico_original) > 15:  
            print("⚠️ [HISTORICO] Histórico grande detectado, aplicando limitação via HistoricoManager...")
            print(f"📊 [HISTORICO] Histórico disponível: {len(historico_original)} mensagens")
        else:
            print(f"📊 [HISTORICO] Histórico OK: {len(historico_original)} mensagens")
        
        if context_data:
            context_message = f"Contexto da sessão: CPF={context_data.get('cpf', '')}, Nome={context_data.get('nome', '')}"
            full_message = f"{context_message}\n\nUsuário: {user_message}"
        else:
            full_message = user_message
            
        result = Runner.run_sync(triage_agent, full_message)
        
        agent_used = _context_data.get('last_agent_used', 'triage_agent')
        print(f"✅ [RESULTADO] Agente usado: {agent_used}")
        
        return result.final_output, agent_used
        
    except Exception as e:
        print(f"[ERRO] Erro no run_agent_loop: {e}")
        import traceback
        traceback.print_exc()
        return "Desculpe, ocorreu um erro interno. Tente novamente.", "assistant_erro"

_context_data = {}
