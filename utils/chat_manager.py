from typing import Dict, List
from pathlib import Path
from openai import OpenAI
from utils.file_utils import carregar_prompt, adicionar_cpf_ao_contexto
from utils.function_handler import FunctionCallHandler
from utils.guardrails import GuardRailsManager
from utils.historico_manager import HistoricoManager


class ChatManager:
    """Gerenciador principal do chat com function calling"""
    
    def __init__(self, client: OpenAI, history_dir: Path = None):
        self.client = client
        self.history_dir = history_dir or Path("chat_history")
        self.history_dir.mkdir(exist_ok=True)
        self.function_handler = FunctionCallHandler(client)
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
            
            prompt_base = carregar_prompt()
            
            # APLICAR LIMITAÇÃO DE HISTÓRICO POR AGENTE
            # Em vez de usar o histórico completo, usar versão limitada
            historico_limitado = self._aplicar_limitacao_historico(historico, cpf)
            
            mensagens = [{"role": "system", "content": prompt_base}]
            
            for item in historico_limitado:
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
    
    def _aplicar_limitacao_historico(self, historico: List[Dict], cpf: str) -> List[Dict]:
        """Aplica limitação de histórico por agente mantendo apenas as últimas N mensagens de cada agente"""
        print(f"[DEBUG] Aplicando limitação de histórico para CPF: {cpf}")
        
        # Separar mensagens por tipo
        mensagens_system = [msg for msg in historico if msg.get("role") == "system"]
        mensagens_limitadas = mensagens_system.copy()  # Sempre manter system messages
        
        # Obter agentes únicos no histórico
        agentes_encontrados = set()
        for msg in historico:
            if msg.get("role") == "assistant" and msg.get("agent"):
                agentes_encontrados.add(msg["agent"])
        
        print(f"[DEBUG] Agentes encontrados: {agentes_encontrados}")
        
        # Para cada agente, obter apenas as últimas N interações
        for agente in agentes_encontrados:
            # Obter últimas mensagens do agente com contexto (pergunta + resposta)
            contexto_agente = self._obter_ultimas_interacoes_agente(historico, agente, limite=5)
            mensagens_limitadas.extend(contexto_agente)
        
        # Ordenar por ordem cronológica (se houver timestamp) ou manter ordem original
        mensagens_limitadas_ordenadas = sorted(
            mensagens_limitadas, 
            key=lambda x: historico.index(x) if x in historico else 0
        )
        
        print(f"[DEBUG] Histórico original: {len(historico)} mensagens")
        print(f"[DEBUG] Histórico limitado: {len(mensagens_limitadas_ordenadas)} mensagens")
        
        return mensagens_limitadas_ordenadas
    
    def _obter_ultimas_interacoes_agente(self, historico: List[Dict], agente: str, limite: int = 5) -> List[Dict]:
        """Obtém as últimas N interações (pergunta + resposta) de um agente específico"""
        interacoes = []
        
        # Encontrar todas as respostas do agente
        for i, msg in enumerate(historico):
            if (msg.get("role") == "assistant" and msg.get("agent") == agente):
                # Encontrar a pergunta anterior
                pergunta_anterior = None
                for j in range(i-1, -1, -1):
                    if historico[j].get("role") == "user":
                        pergunta_anterior = historico[j]
                        break
                
                # Adicionar par pergunta-resposta
                if pergunta_anterior:
                    interacoes.append((pergunta_anterior, msg))
        
        # Pegar apenas as últimas N interações
        ultimas_interacoes = interacoes[-limite:]
        
        # Converter para lista plana
        mensagens_resultado = []
        for pergunta, resposta in ultimas_interacoes:
            mensagens_resultado.extend([pergunta, resposta])
        
        print(f"[DEBUG] Agente {agente}: {len(interacoes)} total, {len(ultimas_interacoes)} limitadas")
        
        return mensagens_resultado
    
    def preparar_historico_para_sessao(self, historico: List[Dict], cpf: str) -> None:
        """Prepara o histórico adicionando o CPF ao contexto se necessário"""
        adicionar_cpf_ao_contexto(historico, cpf)
