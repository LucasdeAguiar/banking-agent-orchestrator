from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI
from .moderation import ModerationManager


class GuardRailsManager:
    """Gerenciador de guardrails para validação de conteúdo"""
    
    def __init__(self, client: OpenAI = None, debug: bool = False):
        if client is None:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
            client = OpenAI(api_key=api_key)
            
        self.client = client
        self.debug = debug
        self.guardrails_dir = Path("guardrails")
        self.guardrails_dir.mkdir(exist_ok=True)
        
        # Inicializar sistema de moderação OpenAI
        self.moderation_manager = ModerationManager(client, debug=debug)
    
    def _carregar_prompt_guardrail(self, nome_arquivo: str) -> Optional[str]:
        """Carrega o prompt de um arquivo de guardrail"""
        try:
            caminho = self.guardrails_dir / nome_arquivo
            if caminho.exists():
                with open(caminho, "r", encoding="utf-8") as f:
                    return f.read().strip()
            else:
                print(f"[AVISO] Arquivo de guardrail não encontrado: {nome_arquivo}")
                return None
        except Exception as e:
            print(f"[ERRO] Erro ao carregar guardrail {nome_arquivo}: {e}")
            return None
    
    def verificar_conteudo_alimentar(self, mensagem_usuario: str) -> bool:
        """
        Verifica se a mensagem contém conteúdo relacionado a comida
        Retorna True se detectar conteúdo alimentar, False caso contrário
        """
        try:
            prompt_guardrail = self._carregar_prompt_guardrail("FoodGuardRails.txt")
            if not prompt_guardrail:
                print("[AVISO] Guardrail de comida não disponível, permitindo mensagem")
                return False
            
            mensagens = [
                {"role": "system", "content": prompt_guardrail},
                {"role": "user", "content": mensagem_usuario}
            ]
            
            resposta = self.client.chat.completions.create(
                model="gpt-4o",
                messages=mensagens,
                max_tokens=1,
                temperature=0.0
            )
            
            resultado = resposta.choices[0].message.content.strip().upper()
            
            if self.debug:
                print(f"[DEBUG] Guardrail Food - Entrada: '{mensagem_usuario[:50]}...'")
                print(f"[DEBUG] Guardrail Food - Resposta: '{resultado}'")
            
            return resultado == "S"
            
        except Exception as e:
            print(f"[ERRO] Erro no guardrail de comida: {e}")
            return False
    
    def aplicar_guardrails(self, mensagem_usuario: str) -> tuple[bool, str]:
        """
        Aplica todos os guardrails disponíveis incluindo moderação OpenAI
        Retorna (bloqueado, mensagem_erro)
        """
        try:
            bloqueado, mensagem_mod, _ = self.moderation_manager.moderar_conteudo(mensagem_usuario)
            if bloqueado:
                return True, mensagem_mod
            
            if self.verificar_conteudo_alimentar(mensagem_usuario):
                return True, (
                    "Desculpe, não posso ajudar com questões relacionadas a comida ou alimentação. "
                    "Estou aqui para auxiliar com serviços bancários, FGTS e empréstimos da Caixa. "
                    "Como posso ajudá-lo com nossos produtos financeiros? 😊"
                )
            
            return False, ""
            
        except Exception as e:
            print(f"[ERRO] Erro ao aplicar guardrails: {e}")
            return False, ""
    
    def configurar_moderacao(self, **kwargs) -> None:
        """Permite configurar o sistema de moderação"""
        if 'thresholds' in kwargs:
            self.moderation_manager.configurar_thresholds(kwargs['thresholds'])
        
        if 'adicionar_categoria_critica' in kwargs:
            self.moderation_manager.adicionar_categoria_critica(kwargs['adicionar_categoria_critica'])
        
        if 'remover_categoria_critica' in kwargs:
            self.moderation_manager.remover_categoria_critica(kwargs['remover_categoria_critica'])
    
    def obter_relatorio_moderacao(self, detalhes_moderacao: dict) -> str:
        """Obtém relatório detalhado da moderação para debug"""
        return self.moderation_manager.obter_estatisticas_moderacao(detalhes_moderacao)
