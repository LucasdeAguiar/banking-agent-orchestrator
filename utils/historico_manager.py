from typing import Dict, List, Optional
from pathlib import Path
from utils.file_utils import carregar_historico


class HistoricoManager:
    """Gerenciador de histórico com limitação por agente"""
    
    def __init__(self, limite_mensagens_por_agente: int = 5):
        self.limite_mensagens_por_agente = limite_mensagens_por_agente
    
    def obter_historico_limitado_por_agente(self, cpf: str, agente: str, 
                                          history_dir: Path = None) -> List[Dict]:
        """
        Obtém as últimas N mensagens de um agente específico para um CPF
        
        Args:
            cpf: CPF do usuário
            agente: Nome do agente (ex: 'emprestimo_agent')
            history_dir: Diretório do histórico
            
        Returns:
            Lista com as últimas mensagens do agente limitadas
        """
        if history_dir is None:
            history_dir = Path("chat_history")
        
        historico_completo = carregar_historico(cpf, history_dir)
        
        # Filtrar mensagens do agente específico (apenas assistant)
        mensagens_agente = []
        
        for mensagem in historico_completo:
            if (mensagem.get("role") == "assistant" and 
                mensagem.get("agent") == agente):
                mensagens_agente.append(mensagem)
        
        # Retornar apenas as últimas N mensagens
        return mensagens_agente[-self.limite_mensagens_por_agente:]
    
    def obter_contexto_relevante_para_agente(self, cpf: str, agente: str, 
                                           pergunta_atual: str,
                                           history_dir: Path = None) -> List[Dict]:
        """
        Obtém contexto relevante para um agente, incluindo:
        - Mensagens system
        - Últimas N mensagens do agente específico
        - Pergunta atual do usuário
        """
        if history_dir is None:
            history_dir = Path("chat_history")
        
        historico_completo = carregar_historico(cpf, history_dir)
        contexto = []
        
        # 1. Adicionar mensagens system
        contexto.extend(self._extrair_mensagens_system(historico_completo))
        
        # 2. Adicionar últimas mensagens do agente com suas perguntas
        contexto.extend(self._obter_mensagens_agente_com_contexto(
            cpf, agente, historico_completo, history_dir
        ))
        
        # 3. Adicionar pergunta atual
        contexto.append({"role": "user", "content": pergunta_atual})
        
        return contexto
    
    def _extrair_mensagens_system(self, historico: List[Dict]) -> List[Dict]:
        """Extrai mensagens system do histórico"""
        return [msg for msg in historico if msg.get("role") == "system"]
    
    def _obter_mensagens_agente_com_contexto(self, cpf: str, agente: str, 
                                           historico_completo: List[Dict],
                                           history_dir: Path) -> List[Dict]:
        """Obtém mensagens do agente com suas perguntas anteriores"""
        mensagens_agente = self.obter_historico_limitado_por_agente(
            cpf, agente, history_dir
        )
        
        contexto = []
        for msg_agente in mensagens_agente:
            pergunta_anterior = self._encontrar_pergunta_anterior(
                msg_agente, agente, historico_completo
            )
            if pergunta_anterior:
                contexto.extend([pergunta_anterior, msg_agente])
        
        return contexto
    
    def _encontrar_pergunta_anterior(self, msg_agente: Dict, agente: str, 
                                   historico_completo: List[Dict]) -> Optional[Dict]:
        """Encontra a pergunta do usuário que gerou uma resposta do agente"""
        for i, msg in enumerate(historico_completo):
            if (self._mensagem_corresponde(msg, msg_agente, agente) and 
                i > 0 and 
                historico_completo[i - 1].get("role") == "user"):
                return historico_completo[i - 1]
        return None
    
    def _mensagem_corresponde(self, msg: Dict, msg_agente: Dict, agente: str) -> bool:
        """Verifica se duas mensagens correspondem"""
        return (msg.get("content") == msg_agente.get("content") and 
                msg.get("role") == "assistant" and 
                msg.get("agent") == agente)
    
    def obter_estatisticas_agente(self, cpf: str, agente: str, 
                                history_dir: Path = None) -> Dict:
        """
        Obtém estatísticas específicas de um agente para um CPF
        
        Args:
            cpf: CPF do usuário
            agente: Nome do agente
            history_dir: Diretório do histórico
            
        Returns:
            Dicionário com estatísticas do agente
        """
        if history_dir is None:
            history_dir = Path("chat_history")
        
        mensagens_agente = self.obter_historico_limitado_por_agente(
            cpf, agente, history_dir
        )
        
        historico_completo = carregar_historico(cpf, history_dir)
        total_mensagens_agente = sum(
            1 for msg in historico_completo 
            if msg.get("role") == "assistant" and msg.get("agent") == agente
        )
        
        return {
            "agente": agente,
            "total_mensagens": total_mensagens_agente,
            "mensagens_recentes": len(mensagens_agente),
            "limite_configurado": self.limite_mensagens_por_agente,
            "primeira_mensagem": mensagens_agente[0]["content"][:100] + "..." if mensagens_agente else None,
            "ultima_mensagem": mensagens_agente[-1]["content"][:100] + "..." if mensagens_agente else None
        }
    
    def configurar_limite(self, novo_limite: int) -> None:
        """Configura novo limite de mensagens por agente"""
        if novo_limite <= 0:
            raise ValueError("Limite deve ser maior que zero")
        self.limite_mensagens_por_agente = novo_limite
        print(f"[CONFIG] Limite de mensagens por agente alterado para: {novo_limite}")
