import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from openai import OpenAI
import sys
import json

# Adicionar o diretório pai ao path para importar agentes
sys.path.append(str(Path(__file__).parent.parent))
from agentes.emprestimo_agent import EmprestimoAgent
from agentes.analise_risco_agent import AnaliseRiscoAgent
from agentes.web_search_agent import WebSearchAgent
from agentes.file_search_agent import FileSearchAgent
from utils.historico_manager import HistoricoManager


class FunctionCallHandler:
    """Handler para gerenciar function calling da OpenAI"""
    
    # Constantes para mensagens de erro
    ERRO_CPF_VAZIO = "[ERRO] CPF não pode ser vazio"
    ERRO_VALOR_POSITIVO = "[ERRO] Valor deve ser positivo"
    ERRO_PARCELAS_POSITIVAS = "[ERRO] Quantidade de parcelas deve ser positiva"
    ERRO_PERGUNTA_VAZIA = "[ERRO] Pergunta não pode ser vazia"
    
    def __init__(self, client: OpenAI):
        self.client = client
        
        # Instanciar gerenciador de histórico
        self.historico_manager = HistoricoManager(limite_mensagens_por_agente=5)
        
        # Instanciar agentes
        self.emprestimo_agent = EmprestimoAgent()
        self.analise_risco_agent = AnaliseRiscoAgent()
        self.web_search_agent = WebSearchAgent(client)  # Precisa do client para busca web
        self.file_search_agent = FileSearchAgent()  # Análise direta, não precisa de client
        
        # Configurar tools disponíveis
        self.tools = [
            self.emprestimo_agent.get_tool_definition(),
            self.analise_risco_agent.get_tool_definition(),
            self.web_search_agent.get_tool_definition(),
            self.file_search_agent.get_tool_definition()
        ]
        
        # Mapeamento de funções disponíveis
        self.available_functions = {
            "emprestimo_agent": self._processar_emprestimo,
            "analise_risco_agent": self._processar_analise_risco,
            "web_search_agent": self._processar_web_search,
            "file_search_agent": self._processar_file_search
        }
    
    def _processar_emprestimo(self, args: Dict[str, Any], base_usuarios: Dict) -> Dict[str, Any]:
        """Processa chamada do agente de empréstimo"""
        return self.emprestimo_agent.processar(
            args["cpf"],
            args["valor"],
            args["qtd_parcelas"],
            base_usuarios
        )
    
    def _processar_analise_risco(self, args: Dict[str, Any], base_usuarios: Dict, historico: List[Dict] = None) -> Dict[str, Any]:
        """Processa chamada do agente de análise de risco"""
        incluir_historico = args.get("incluir_historico", True)
        historico_para_analise = historico if incluir_historico else None
        
        return self.analise_risco_agent.processar(
            args["cpf"],
            base_usuarios,
            historico_para_analise
        )
    
    def _processar_web_search(self, args: Dict[str, Any], base_usuarios: Dict, historico: List[Dict] = None) -> Dict[str, Any]:
        """Processa chamada do agente de busca web"""
        return self.web_search_agent.processar(
            args["pergunta"],
            args.get("localizacao")
        )
    
    def _processar_file_search(self, args: Dict[str, Any], base_usuarios: Dict, historico: List[Dict] = None) -> Dict[str, Any]:
        """Processa chamada do agente de busca em arquivos"""
        return self.file_search_agent.processar(
            args["cpf"],
            args["pergunta"]
        )
    
    def _validate_arguments(self, function_name: str, args: Dict[str, Any]) -> bool:
        """Valida argumentos da função antes da execução"""
        if function_name == "emprestimo_agent":
            required_keys = ["cpf", "valor", "qtd_parcelas"]
            
            # Verificar se todas as chaves obrigatórias estão presentes
            if not all(k in args for k in required_keys):
                print(f"[ERRO] Argumentos faltando para {function_name}: {required_keys}")
                return False
            
            # Validações específicas
            try:
                cpf = str(args["cpf"]).strip()
                valor = float(args["valor"])
                qtd_parcelas = int(args["qtd_parcelas"])
                
                if not cpf:
                    print("[ERRO] CPF não pode ser vazio")
                    return False
                
                if valor <= 0:
                    print("[ERRO] Valor deve ser positivo")
                    return False
                
                if qtd_parcelas <= 0:
                    print("[ERRO] Quantidade de parcelas deve ser positiva")
                    return False
                
                return True
                
            except (ValueError, TypeError) as e:
                print(f"[ERRO] Erro na validação dos argumentos: {e}")
                return False
        
        elif function_name == "analise_risco_agent":
            required_keys = ["cpf"]
            
            if not all(k in args for k in required_keys):
                print(f"[ERRO] Argumentos faltando para {function_name}: {required_keys}")
                return False
            
            try:
                cpf = str(args["cpf"]).strip()
                if not cpf:
                    print("[ERRO] CPF não pode ser vazio")
                    return False
                return True
                
            except (ValueError, TypeError) as e:
                print(f"[ERRO] Erro na validação dos argumentos: {e}")
                return False
        
        elif function_name == "web_search_agent":
            required_keys = ["pergunta"]
            
            if not all(k in args for k in required_keys):
                print(f"[ERRO] Argumentos faltando para {function_name}: {required_keys}")
                return False
            
            try:
                pergunta = str(args["pergunta"]).strip()
                if not pergunta:
                    print("[ERRO] Pergunta não pode ser vazia")
                    return False
                
                # Validar se é uma pergunta bancária relevante
                if not self.web_search_agent.validar_pergunta(pergunta):
                    print("[AVISO] Pergunta pode não ser relacionada a temas bancários")
                    # Não bloquear, apenas avisar
                
                return True
                
            except (ValueError, TypeError) as e:
                print(f"[ERRO] Erro na validação dos argumentos: {e}")
                return False
        
        elif function_name == "file_search_agent":
            required_keys = ["cpf", "pergunta"]
            
            if not all(k in args for k in required_keys):
                print(f"[ERRO] Argumentos faltando para {function_name}: {required_keys}")
                return False
            
            try:
                cpf = str(args["cpf"]).strip()
                pergunta = str(args["pergunta"]).strip()
                
                if not cpf:
                    print("[ERRO] CPF não pode ser vazio")
                    return False
                
                if not pergunta:
                    print("[ERRO] Pergunta não pode ser vazia")
                    return False
                
                # Verificar se existe histórico para este CPF
                if not self.file_search_agent.verificar_historico_disponivel(cpf):
                    print(f"[AVISO] Não existe histórico de transações para CPF {cpf}")
                    # Não bloquear, deixar o agente retornar a mensagem apropriada
                
                return True
                
            except (ValueError, TypeError) as e:
                print(f"[ERRO] Erro na validação dos argumentos: {e}")
                return False
        
        return False
    
    def _execute_function(self, function_name: str, args: Dict[str, Any], base_usuarios: Dict, historico: List[Dict] = None) -> Dict[str, Any]:
        try:
            print(f"[DEBUG] Executando {function_name} com argumentos: {args}")
            
            if not self._validate_arguments(function_name, args):
                return {
                    "erro": True,
                    "mensagem": f"Argumentos inválidos para {function_name}"
                }
            
            if function_name in self.available_functions:
                if function_name == "analise_risco_agent":
                    resultado = self.available_functions[function_name](args, base_usuarios, historico)
                elif function_name == "web_search_agent":
                    resultado = self.available_functions[function_name](args, base_usuarios, historico)
                elif function_name == "file_search_agent":
                    resultado = self.available_functions[function_name](args, base_usuarios, historico)
                else:
                    resultado = self.available_functions[function_name](args, base_usuarios)
                
                print(f"[DEBUG] Resultado da função: {resultado}")
                return resultado
            else:
                return {
                    "erro": True,
                    "mensagem": f"Função {function_name} não encontrada"
                }
                
        except Exception as e:
            print(f"[ERRO] Erro ao executar função {function_name}: {e}")
            return {
                "erro": True,
                "mensagem": f"Erro interno ao executar {function_name}: {str(e)}"
            }
    
    def processar_resposta_com_tools(self, mensagens: List[Dict], cpf: str, base_usuarios: Dict) -> Tuple[str, str]:
        """Processa resposta usando function calling com validações e fallbacks"""
        agentes_usados = []
        try:
            print(f"[DEBUG] Processando resposta com tools para CPF: {cpf}")
            
            resposta = self.client.chat.completions.create(
                model="gpt-4o",
                messages=mensagens,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            resposta_message = resposta.choices[0].message
            print(f"[DEBUG] Modelo retornou tool_calls: {bool(resposta_message.tool_calls)}")
            
            if resposta_message.tool_calls:
                mensagens.append({
                    "role": "assistant",
                    "content": resposta_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in resposta_message.tool_calls
                    ]
                })
                
                for tool_call in resposta_message.tool_calls:
                    function_name = tool_call.function.name
                    agentes_usados.append(function_name)
                    print(f"[DEBUG] Processando tool_call: {function_name}")
                    
                    try:
                        # Parse dos argumentos
                        args = json.loads(tool_call.function.arguments)
                        print(f"[DEBUG] Argumentos parseados: {args}")
                        
                        # Executar função (passando histórico para análise de risco)
                        historico_chat = [msg for msg in mensagens if msg.get("role") in ["user", "assistant"]]
                        resultado = self._execute_function(function_name, args, base_usuarios, historico_chat)
                        
                        # Adicionar resultado da tool à conversa
                        mensagens.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(resultado, ensure_ascii=False)
                        })
                        
                    except json.JSONDecodeError as e:
                        print(f"[ERRO] Erro ao parsear argumentos JSON: {e}")
                        # Fallback para erro de parsing
                        mensagens.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps({
                                "erro": True,
                                "mensagem": "Erro ao processar argumentos da função"
                            }, ensure_ascii=False)
                        })
                
                print("[DEBUG] Solicitando resposta final do modelo")
                resposta_final = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=mensagens,
                    temperature=0.1
                )
                
                resultado_texto = resposta_final.choices[0].message.content
                print(f"\nAssistente: {resultado_texto}\n")
                
                # Determinar agente principal usado
                agente_principal = agentes_usados[0] if agentes_usados else "assistant_geral"
                return resultado_texto, agente_principal
            
            # Resposta normal sem tool calls
            resposta_texto = resposta_message.content
            print(f"\nAssistente: {resposta_texto}\n")
            return resposta_texto, "assistant_geral"
            
        except Exception as e:
            print(f"[ERRO] Erro ao processar resposta com tools: {e}")
            return "Desculpe, ocorreu um erro interno. Tente novamente.", "assistant_erro"
