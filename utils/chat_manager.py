from typing import Dict, List
from pathlib import Path
from openai import OpenAI
from utils.file_utils import carregar_prompt, adicionar_cpf_ao_contexto
from utils.guardrails import GuardRailsManager
from utils.historico_manager import HistoricoManager

import sys
sys.path.append(str(Path(__file__).parent.parent))
from agents_openai import run_agent_loop


class ChatManager:
    """Gerenciador principal do chat com function calling"""
    
    def __init__(self, client: OpenAI, history_dir: Path = None):
        self.client = client
        self.history_dir = history_dir or Path("chat_history")
        self.history_dir.mkdir(exist_ok=True)
       
        self.guardrails = GuardRailsManager(client)
        self.historico_manager = HistoricoManager(limite_mensagens_por_agente=5)
    
    def enviar_boas_vindas(self, nome: str, historico: List[Dict]) -> None:
        """Gera mensagem de boas-vindas personalizada"""
        prompt_base = carregar_prompt()
        mensagem_trigger = f"PRIMEIRA_INTERACAO: {nome}"
        
        try:
            mensagens = [
                {"role": "system", "content": prompt_base},
                {"role": "system", "content": mensagem_trigger}
            ]
            
            resposta = self.client.chat.completions.create(
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
    
    def processar_mensagem(self, pergunta: str, historico: List[Dict], cpf: str, 
                          base_usuarios: Dict) -> tuple[str, str]:
        """Processa uma mensagem do usuário e retorna a resposta"""
        try:
            # Aplicar guardrails antes do processamento
            bloqueado, mensagem_erro = self.guardrails.aplicar_guardrails(pergunta)
            if bloqueado:
                print(f"\n[GUARDRAIL] Mensagem bloqueada: {mensagem_erro}\n")
                return mensagem_erro, "guardrail"
            
            # APLICAR LIMITAÇÃO DE HISTÓRICO POR AGENTE usando HistoricoManager
            # Usar o HistoricoManager que já existe em vez de reimplementar
            context_data = {
                "cpf": cpf, 
                "base_usuarios": base_usuarios, 
                "historico": historico  # Usar histórico completo, agents_openai já aplica limitação
            }
            
            # Usar o sistema OpenAI Agents com handoff/orchestration
            resposta_texto, agente_usado = run_agent_loop(pergunta, context_data)
            
            return resposta_texto, agente_usado
            
        except Exception as e:
            print(f"[ERRO] Erro ao processar mensagem: {e}")
            return "Desculpe, ocorreu um erro. Tente novamente.", "assistant_erro"
    
    def preparar_historico_para_sessao(self, historico: List[Dict], cpf: str) -> None:
        """Prepara o histórico adicionando o CPF ao contexto se necessário"""
        adicionar_cpf_ao_contexto(historico, cpf)
