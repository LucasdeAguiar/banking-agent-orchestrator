from typing import Dict, List, Any
import json
from .base_agent import BaseAgent


class AnaliseRiscoAgent(BaseAgent):
    """Agente especializado em análise de risco de cliente"""
    
    # Constantes para níveis de risco
    RISCO_BAIXO = "BAIXO"
    RISCO_MEDIO = "MÉDIO"
    RISCO_ALTO = "ALTO"
    
    def __init__(self):
        super().__init__(
            nome="Análise de Risco Agent",
            descricao="Analisa o perfil de risco do cliente baseado em histórico de mensagens, empréstimos e informações cadastrais"
        )
    
    def processar(self, cpf: str, usuarios_db: Dict, historico_chat: List[Dict] = None) -> Dict[str, Any]:
        """
        Processa uma análise de risco do cliente
        
        Args:
            cpf: CPF do cliente
            usuarios_db: Base de dados dos usuários
            historico_chat: Histórico de mensagens do chat (opcional)
            
        Returns:
            Dict com análise de risco do cliente
        """
        usuario = usuarios_db.get(cpf)
        if not usuario:
            return {
                "erro": True,
                "mensagem": f"CPF {cpf} não encontrado na base para análise de risco.",
                "analise": None
            }
        
        nome = usuario["nome"]
        nome_sujo = usuario.get("nome_sujo", False)
        
        # Análise básica do perfil
        perfil_risco = self._analisar_perfil_basico(nome_sujo)
        
        # Análise do histórico de chat se disponível
        if historico_chat:
            historico_analise = self._analisar_historico_chat(historico_chat)
            perfil_risco.update(historico_analise)
        
        # Gerar recomendações
        recomendacoes = self._gerar_recomendacoes(perfil_risco, nome_sujo)
        
        return {
            "erro": False,
            "cliente": {
                "nome": nome,
                "cpf": cpf,
                "nome_sujo": nome_sujo
            },
            "analise": {
                "nivel_risco": perfil_risco["nivel_risco"],
                "score_risco": perfil_risco["score_risco"],
                "fatores_risco": perfil_risco["fatores_risco"],
                "fatores_positivos": perfil_risco["fatores_positivos"],
                "recomendacoes": recomendacoes
            },
            "mensagem": self._formatar_mensagem_analise(nome, perfil_risco, recomendacoes)
        }
    
    def _analisar_perfil_basico(self, nome_sujo: bool) -> Dict[str, Any]:
        """Análise básica baseada nas informações cadastrais"""
        fatores_risco = []
        fatores_positivos = []
        score_risco = 0
        
        if nome_sujo:
            fatores_risco.append("Cliente com restrições creditícias (nome sujo)")
            score_risco += 40
        else:
            fatores_positivos.append("Cliente sem restrições no CPF")
            score_risco -= 10
        
        # Determinar nível de risco
        if score_risco >= 50:
            nivel_risco = self.RISCO_ALTO
        elif score_risco >= 20:
            nivel_risco = self.RISCO_MEDIO
        else:
            nivel_risco = self.RISCO_BAIXO
        
        return {
            "nivel_risco": nivel_risco,
            "score_risco": max(0, min(100, score_risco)),
            "fatores_risco": fatores_risco,
            "fatores_positivos": fatores_positivos
        }
    
    def _analisar_historico_chat(self, historico: List[Dict]) -> Dict[str, Any]:
        """Análisa o histórico de mensagens para identificar padrões"""
        updates = {
            "fatores_risco": [],
            "fatores_positivos": [],
            "score_risco_adicional": 0
        }
        
        # Contar mensagens do usuário
        mensagens_usuario = [msg for msg in historico if msg.get("role") == "user"]
        total_mensagens = len(mensagens_usuario)
        
        # Analisar conteúdo das mensagens
        emprestimos_solicitados = 0
        mencoes_urgencia = 0
        
        for msg in mensagens_usuario:
            content = msg.get("content", "").lower()
            
            # Detectar solicitações de empréstimo
            if any(palavra in content for palavra in ["empréstimo", "emprestimo", "dinheiro", "valor", "financiamento"]):
                emprestimos_solicitados += 1
            
            # Detectar urgência
            if any(palavra in content for palavra in ["urgente", "rapido", "rápido", "preciso agora", "emergência"]):
                mencoes_urgencia += 1
        
        # Avalizar padrões
        if emprestimos_solicitados > 2:
            updates["fatores_risco"].append("Múltiplas solicitações de empréstimo na conversa")
            updates["score_risco_adicional"] += 15
        
        if mencoes_urgencia > 1:
            updates["fatores_risco"].append("Demonstra urgência excessiva nas solicitações")
            updates["score_risco_adicional"] += 10
        
        if total_mensagens > 0 and emprestimos_solicitados == 0:
            updates["fatores_positivos"].append("Cliente demonstra interesse em outros serviços além de empréstimos")
            updates["score_risco_adicional"] -= 5
        
        return updates
    
    def _gerar_recomendacoes(self, perfil_risco: Dict, nome_sujo: bool) -> List[str]:
        """Gera recomendações baseadas no perfil de risco"""
        recomendacoes = []
        
        nivel_risco = perfil_risco["nivel_risco"]
        
        if nome_sujo:
            recomendacoes.extend([
                "Considere quitar suas pendências para melhorar seu score",
                "Empréstimos limitados a R$ 500,00 devido às restrições",
                "Explore produtos de recuperação de crédito da Caixa"
            ])
        
        if nivel_risco == self.RISCO_ALTO:
            recomendacoes.extend([
                "Recomendamos cautela com novos compromissos financeiros",
                "Busque orientação financeira antes de contratar empréstimos",
                "Considere renegociar dívidas existentes"
            ])
        elif nivel_risco == self.RISCO_MEDIO:
            recomendacoes.extend([
                "Mantenha suas contas em dia para melhorar seu perfil",
                "Considere empréstimos com parcelas menores",
                "Avalie sua capacidade de pagamento antes de se comprometer"
            ])
        else:  # RISCO_BAIXO
            recomendacoes.extend([
                "Você tem um bom perfil creditício",
                "Pode ser elegível para melhores condições de empréstimo",
                "Continue mantendo suas contas em dia"
            ])
        
        return recomendacoes
    
    def _formatar_mensagem_analise(self, nome: str, perfil_risco: Dict, recomendacoes: List[str]) -> str:
        """Formata a mensagem de análise para o usuário"""
        nivel_risco = perfil_risco["nivel_risco"]
        score = perfil_risco["score_risco"]
        
        emoji_risco = {self.RISCO_BAIXO: "🟢", self.RISCO_MEDIO: "🟡", self.RISCO_ALTO: "🔴"}
        
        mensagem = f"""📊 **Análise de Risco - {nome}**

{emoji_risco[nivel_risco]} **Nível de Risco:** {nivel_risco} (Score: {score}/100)

"""
        
        if perfil_risco["fatores_positivos"]:
            mensagem += "✅ **Pontos Positivos:**\n"
            for fator in perfil_risco["fatores_positivos"]:
                mensagem += f"• {fator}\n"
            mensagem += "\n"
        
        if perfil_risco["fatores_risco"]:
            mensagem += "⚠️ **Fatores de Atenção:**\n"
            for fator in perfil_risco["fatores_risco"]:
                mensagem += f"• {fator}\n"
            mensagem += "\n"
        
        mensagem += "💡 **Recomendações:**\n"
        for rec in recomendacoes:
            mensagem += f"• {rec}\n"
        
        return mensagem
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Retorna a definição da tool para o function calling"""
        return {
            "type": "function",
            "function": {
                "name": "analise_risco_agent",
                "description": self.descricao,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cpf": {"type": "string", "description": "CPF do cliente para análise"},
                        "incluir_historico": {"type": "boolean", "description": "Se deve incluir análise do histórico de chat", "default": True}
                    },
                    "required": ["cpf"],
                    "additionalProperties": False
                }
            }
        }
