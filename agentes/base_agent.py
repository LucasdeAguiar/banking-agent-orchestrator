from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Clase base abstrata para todos os agentes do sistema"""
    
    def __init__(self, nome: str, descricao: str):
        self.nome = nome
        self.descricao = descricao
    
    @abstractmethod
    def processar(self, *args, **kwargs) -> Dict[str, Any]:
        """Método principal para processar a requisição do agente"""
        pass
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Retorna a definição da tool para o function calling"""
        pass
    
    def validar_cpf(self, cpf: str, usuarios_db: Dict) -> bool:
        """Validação padrão de CPF na base de dados"""
        return cpf in usuarios_db
    
    def obter_usuario(self, cpf: str, usuarios_db: Dict) -> Dict[str, Any]:
        """Obtém dados do usuário pela base de dados"""
        return usuarios_db.get(cpf)
