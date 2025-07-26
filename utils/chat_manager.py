from typing import Dict, List
from pathlib import Path
from openai import OpenAI
from utils.file_utils import carregar_prompt, adicionar_cpf_ao_contexto
from utils.function_handler import FunctionCallHandler
from utils.guardrails import GuardRailsManager


class ChatManager:
    """Gerenciador principal do chat com function calling"""
    
    def __init__(self, client: OpenAI, history_dir: Path = None):
        self.client = client
        self.history_dir = history_dir or Path("chat_history")
        self.history_dir.mkdir(exist_ok=True)
        self.function_handler = FunctionCallHandler(client)
        self.guardrails = GuardRailsManager(client)
    
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
            
            prompt_base = carregar_prompt()
            mensagens = [{"role": "system", "content": prompt_base}]
            
            for item in historico:
                mensagens.append(item)
            
            mensagens.append({"role": "user", "content": pergunta})
            
            # Processar resposta com function calling
            resposta_texto, agente_usado = self.function_handler.processar_resposta_com_tools(
                mensagens, cpf, base_usuarios
            )
            
            return resposta_texto, agente_usado
            
        except Exception as e:
            print(f"[ERRO] Erro ao processar mensagem: {e}")
            return "Desculpe, ocorreu um erro. Tente novamente.", "assistant_erro"
    
    def preparar_historico_para_sessao(self, historico: List[Dict], cpf: str) -> None:
        """Prepara o histórico adicionando o CPF ao contexto se necessário"""
        adicionar_cpf_ao_contexto(historico, cpf)
