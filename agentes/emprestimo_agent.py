from typing import Dict, Any
from .base_agent import BaseAgent


class EmprestimoAgent(BaseAgent):
    """Agente especializado em simulação e aprovação de empréstimos"""
    
    def __init__(self):
        super().__init__(
            nome="Empréstimo Agent",
            descricao="Calcula aprovação/reprovação de empréstimo baseado no CPF, valor e parcelas do usuário"
        )
    
    def processar(self, cpf: str, valor: float, qtd_parcelas: int, usuarios_db: Dict) -> Dict[str, Any]:
        """
        Processa uma solicitação de empréstimo
        
        Args:
            cpf: CPF do solicitante
            valor: Valor solicitado para o empréstimo
            qtd_parcelas: Número de parcelas para pagamento
            usuarios_db: Base de dados dos usuários
            
        Returns:
            Dict com resultado da análise do empréstimo
        """
        usuario = usuarios_db.get(cpf)
        if not usuario:
            return {
                "aprovado": False,
                "mensagem": f"CPF {cpf} não encontrado na base.",
                "valor_simulado": None
            }
        
        nome = usuario["nome"]
        nome_sujo = usuario.get("nome_sujo", False)
        
        # Regra de negócio: clientes com nome sujo só podem pedir até R$ 500
        if nome_sujo and valor > 500:
            return {
                "aprovado": False,
                "mensagem": (
                    f"Empréstimo recusado para {nome} (CPF {cpf}): valor de R${valor:.2f} "
                    f"acima do permitido para clientes com restrições (máximo R$500,00)."
                ),
                "valor_simulado": None
            }
        
        # Calcular valor da parcela
        valor_parcela = valor / qtd_parcelas
        
        return {
            "aprovado": True,
            "mensagem": (
                f"Empréstimo aprovado para {nome} (CPF {cpf}) no valor de R${valor:.2f} "
                f"em {qtd_parcelas} parcelas de R${valor_parcela:.2f}."
            ),
            "valor_simulado": {
                "valor_total": valor,
                "qtd_parcelas": qtd_parcelas,
                "valor_parcela": round(valor_parcela, 2)
            }
        }
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Retorna a definição da tool para o function calling"""
        return {
            "type": "function",
            "function": {
                "name": "emprestimo_agent",
                "description": self.descricao,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cpf": {"type": "string", "description": "CPF do solicitante"},
                        "valor": {"type": "number", "description": "Valor solicitado para o empréstimo"},
                        "qtd_parcelas": {"type": "integer", "description": "Número de parcelas para pagamento"}
                    },
                    "required": ["cpf", "valor", "qtd_parcelas"],
                    "additionalProperties": False
                }
            }
        }
