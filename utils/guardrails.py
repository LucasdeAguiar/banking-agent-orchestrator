from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI
from .moderation import ModerationManager


class GuardrailResult:
    """Resultado de um guardrail seguindo padrão OpenAI"""
    
    def __init__(self, passed: bool, message: str = "", details: Optional[Dict] = None):
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.tripwire_triggered = not passed


class InputGuardrail:
    """Guardrail para entrada do usuário seguindo padrão OpenAI"""
    
    def __init__(self, name: str, client: OpenAI, debug: bool = False):
        self.name = name
        self.client = client
        self.debug = debug
    
    def validate(self, user_input: str) -> GuardrailResult:
        """Valida entrada do usuário - deve ser implementado pelas subclasses"""
        raise NotImplementedError("Subclasses devem implementar validate()")


class OutputGuardrail:
    """Guardrail para saída do assistente seguindo padrão OpenAI"""
    
    def __init__(self, name: str, client: OpenAI, debug: bool = False):
        self.name = name
        self.client = client
        self.debug = debug
    
    def validate(self, assistant_output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """Valida saída do assistente - deve ser implementado pelas subclasses"""
        raise NotImplementedError("Subclasses devem implementar validate()")


class ModerationInputGuardrail(InputGuardrail):
    """Guardrail de moderação OpenAI para entrada"""
    
    def __init__(self, client: OpenAI, debug: bool = False):
        super().__init__("openai_moderation", client, debug)
        self.moderation_manager = ModerationManager(client, debug)
    
    def validate(self, user_input: str) -> GuardrailResult:
        """Valida entrada usando OpenAI Moderation API"""
        try:
            blocked, message, details = self.moderation_manager.moderar_conteudo(user_input)
            
            if blocked:
                return GuardrailResult(
                    passed=False,
                    message=message,
                    details={"moderation_details": details}
                )
            
            return GuardrailResult(passed=True, message="Conteúdo aprovado pela moderação")
            
        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro no guardrail de moderação: {e}")
            # Em caso de erro, permitir (fail-open)
            return GuardrailResult(passed=True, message="Erro na moderação - permitindo")


class FoodContentInputGuardrail(InputGuardrail):
    """Guardrail para detectar conteúdo sobre comida"""
    
    def __init__(self, client: OpenAI, guardrails_dir: Path, debug: bool = False):
        super().__init__("food_content", client, debug)
        self.guardrails_dir = guardrails_dir
    
    def validate(self, user_input: str) -> GuardrailResult:
        """Valida se entrada contém conteúdo sobre comida"""
        try:
            prompt_path = self.guardrails_dir / "FoodGuardRails.txt"
            if not prompt_path.exists():
                if self.debug:
                    print(f"[AVISO] Arquivo {prompt_path} não encontrado")
                return GuardrailResult(passed=True, message="Guardrail não configurado")
            
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_guardrail = f.read().strip()
            
            mensagens = [
                {"role": "system", "content": prompt_guardrail},
                {"role": "user", "content": user_input}
            ]
            
            resposta = self.client.chat.completions.create(
                model="gpt-4o",
                messages=mensagens,
                max_tokens=1,
                temperature=0.0
            )
            
            resultado = resposta.choices[0].message.content.strip().upper()
            
            if self.debug:
                print(f"[DEBUG] Food Guardrail - Input: '{user_input[:50]}...'")
                print(f"[DEBUG] Food Guardrail - Result: '{resultado}'")
            
            if resultado == "S":
                return GuardrailResult(
                    passed=False,
                    message=(
                        "Desculpe, não posso ajudar com questões relacionadas a comida ou alimentação. "
                        "Estou aqui para auxiliar com serviços bancários, FGTS e empréstimos da Caixa. "
                        "Como posso ajudá-lo com nossos produtos financeiros? 😊"
                    ),
                    details={"detected_food_content": True}
                )
            
            return GuardrailResult(passed=True, message="Não detectado conteúdo sobre comida")
            
        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro no guardrail de comida: {e}")
            return GuardrailResult(passed=True, message="Erro no guardrail - permitindo")


class GuardRailsManager:
    """Gerenciador de guardrails modernizado seguindo padrão OpenAI"""
    
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
        
        # Inicializar guardrails de entrada
        self.input_guardrails = [
            ModerationInputGuardrail(client, debug),
            FoodContentInputGuardrail(client, self.guardrails_dir, debug)
        ]
        
        # Guardrails de saída (expandir conforme necessário)
        self.output_guardrails = []
    
    def aplicar_guardrails_entrada(self, user_input: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Aplica todos os guardrails de entrada
        
        Returns:
            Tuple: (bloqueado, mensagem_erro, detalhes)
        """
        all_details = {}
        
        for guardrail in self.input_guardrails:
            try:
                resultado = guardrail.validate(user_input)
                
                all_details[guardrail.name] = {
                    "passed": resultado.passed,
                    "message": resultado.message,
                    "details": resultado.details
                }
                
                if resultado.tripwire_triggered:
                    if self.debug:
                        print(f"[GUARDRAIL] {guardrail.name} bloqueou entrada")
                    return True, resultado.message, all_details
                
            except Exception as e:
                if self.debug:
                    print(f"[ERRO] Erro ao executar guardrail {guardrail.name}: {e}")
                all_details[guardrail.name] = {
                    "passed": True,  # fail-open
                    "message": f"Erro no guardrail: {e}",
                    "details": {}
                }
        
        return False, "", all_details
    
    def aplicar_guardrails_saida(self, assistant_output: str, 
                                context: Optional[Dict] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Aplica todos os guardrails de saída
        
        Returns:
            Tuple: (bloqueado, mensagem_erro, detalhes)
        """
        all_details = {}
        
        for guardrail in self.output_guardrails:
            try:
                resultado = guardrail.validate(assistant_output, context)
                
                all_details[guardrail.name] = {
                    "passed": resultado.passed,
                    "message": resultado.message,
                    "details": resultado.details
                }
                
                if resultado.tripwire_triggered:
                    if self.debug:
                        print(f"[GUARDRAIL] {guardrail.name} bloqueou saída")
                    return True, resultado.message, all_details
                
            except Exception as e:
                if self.debug:
                    print(f"[ERRO] Erro ao executar guardrail {guardrail.name}: {e}")
                all_details[guardrail.name] = {
                    "passed": True,  # fail-open
                    "message": f"Erro no guardrail: {e}",
                    "details": {}
                }
        
        return False, "", all_details
    
    # Manter compatibilidade com código existente
    def aplicar_guardrails(self, mensagem_usuario: str) -> Tuple[bool, str]:
        """Método de compatibilidade com código existente"""
        bloqueado, mensagem, _ = self.aplicar_guardrails_entrada(mensagem_usuario)
        return bloqueado, mensagem
    
    def adicionar_guardrail_entrada(self, guardrail: InputGuardrail) -> None:
        """Adiciona um novo guardrail de entrada"""
        self.input_guardrails.append(guardrail)
        if self.debug:
            print(f"[CONFIG] Guardrail de entrada adicionado: {guardrail.name}")
    
    def adicionar_guardrail_saida(self, guardrail: OutputGuardrail) -> None:
        """Adiciona um novo guardrail de saída"""
        self.output_guardrails.append(guardrail)
        if self.debug:
            print(f"[CONFIG] Guardrail de saída adicionado: {guardrail.name}")
