from typing import Dict, Any, Optional, List
from openai import OpenAI
from pathlib import Path
import json
import os
from .base_agent import BaseAgent


class FileSearchAgent(BaseAgent):
    """Agente especializado em busca de informações em histórico de transações do cliente"""
    
    def __init__(self, client: Optional[OpenAI] = None):
        super().__init__(
            nome="File Search Agent",
            descricao="Busca informações detalhadas no histórico de transações bancárias do cliente usando análise direta"
        )
        self.client = client
        self.transaction_dir = Path("transaction_history")
    
    def processar(self, cpf: str, pergunta: str, **kwargs) -> Dict[str, Any]:
        """
        Processa uma busca no histórico de transações do cliente
        
        Args:
            cpf: CPF do cliente para buscar o histórico
            pergunta: Pergunta sobre as transações
            
        Returns:
            Dict com resultado da busca no histórico
        """
        try:
            # Verificar se existe histórico para este CPF
            arquivo_historico = self.transaction_dir / f"{cpf}.json"
            
            if not arquivo_historico.exists():
                return {
                    "erro": True,
                    "mensagem": f"Não foi encontrado histórico de transações para o CPF {cpf}.",
                    "cpf": cpf,
                    "resultado": None
                }
            
            print(f"[DEBUG] Analisando histórico de transações para CPF: {cpf}")
            
            # Carregar e analisar o histórico diretamente
            with open(arquivo_historico, "r", encoding="utf-8") as f:
                transacoes = json.load(f)
            
            # Analisar as transações baseado na pergunta
            resultado_analise = self._analisar_transacoes(transacoes, pergunta, cpf)
            
            return {
                "erro": False,
                "cpf": cpf,
                "pergunta_original": pergunta,
                "resultado": resultado_analise,
                "mensagem": self._formatar_resultado_busca(cpf, pergunta, resultado_analise)
            }
            
        except Exception as e:
            print(f"[ERRO] Erro na busca do histórico: {e}")
            return {
                "erro": True,
                "cpf": cpf,
                "mensagem": f"Não foi possível buscar no histórico de transações. Erro: {str(e)}",
                "resultado": None
            }
    
    
    def _analisar_transacoes(self, transacoes: List[Dict], pergunta: str, cpf: str) -> str:
        """Analisa as transações baseado na pergunta do usuário"""
        
        pergunta_lower = pergunta.lower()
        
        # Análise de gastos com compras
        if any(palavra in pergunta_lower for palavra in ["compra", "compras", "gastei", "gasto"]):
            return self._analisar_gastos_compras(transacoes, pergunta_lower)
        
        # Análise de empréstimos
        elif any(palavra in pergunta_lower for palavra in ["empréstimo", "emprestimo", "consignado", "parcela"]):
            return self._analisar_emprestimos(transacoes)
        
        # Análise de FGTS
        elif "fgts" in pergunta_lower:
            return self._analisar_fgts(transacoes)
        
        # Análise de transferências/PIX
        elif any(palavra in pergunta_lower for palavra in ["transferência", "transferencia", "pix", "ted"]):
            return self._analisar_transferencias(transacoes)
        
        # Análise de padrões de gastos
        elif any(palavra in pergunta_lower for palavra in ["padrão", "padrao", "habito", "comportamento"]):
            return self._analisar_padroes_gastos(transacoes)
        
        # Resumo geral
        elif any(palavra in pergunta_lower for palavra in ["resumo", "relatório", "relatorio", "historico", "histórico"]):
            return self._gerar_resumo_geral(transacoes)
        
        # Análise de saldo
        elif any(palavra in pergunta_lower for palavra in ["saldo", "evolução", "evolucao"]):
            return self._analisar_evolucao_saldo(transacoes)
        
        # Busca específica por palavras-chave
        elif any(palavra in pergunta_lower for palavra in ["faculdade", "educação", "educacao"]):
            return self._buscar_transacao_especifica(transacoes, "faculdade")
        
        elif any(palavra in pergunta_lower for palavra in ["devolução", "devolucao", "estorno"]):
            return self._buscar_transacao_especifica(transacoes, "devolução")
        
        # Busca geral
        else:
            return self._buscar_informacao_geral(transacoes, pergunta)
    
    def _analisar_gastos_compras(self, transacoes: List[Dict], pergunta: str) -> str:
        """Analisa gastos com compras"""
        compras = [t for t in transacoes if t["tipo"] == "compra" and t["valor"] < 0]
        
        if not compras:
            return "Não foram encontradas transações de compra no seu histórico."
        
        total_compras = sum(abs(t["valor"]) for t in compras)
        
        # Se pergunta menciona "último mês" ou período específico
        if "último mês" in pergunta or "ultimo mes" in pergunta:
            # Pegar as transações mais recentes
            compras_recentes = compras[-10:] if len(compras) > 10 else compras
            total_recente = sum(abs(t["valor"]) for t in compras_recentes)
            
            detalhes = "\n".join([
                f"• {t['data'][:10]}: {t['descricao']} - R$ {abs(t['valor']):.2f}"
                for t in compras_recentes
            ])
            
            return f"""**Gastos com Compras (Período Recente):**

**Total gasto em compras recentes:** R$ {total_recente:.2f}
**Número de compras:** {len(compras_recentes)}
**Valor médio por compra:** R$ {total_recente/len(compras_recentes):.2f}

**Detalhamento das compras:**
{detalhes}

**Total geral de todas as compras no histórico:** R$ {total_compras:.2f} ({len(compras)} transações)"""
        
        # Análise geral de compras
        detalhes_todas = "\n".join([
            f"• {t['data'][:10]}: {t['descricao']} - R$ {abs(t['valor']):.2f}"
            for t in compras
        ])
        
        return f"""**Análise Completa dos Gastos com Compras:**

**Total gasto:** R$ {total_compras:.2f}
**Número de compras:** {len(compras)}
**Valor médio por compra:** R$ {total_compras/len(compras):.2f}

**Detalhamento de todas as compras:**
{detalhes_todas}"""
    
    def _analisar_emprestimos(self, transacoes: List[Dict]) -> str:
        """Analisa histórico de empréstimos"""
        emprestimos = [t for t in transacoes if t["tipo"] == "empréstimo"]
        
        if not emprestimos:
            return "Não foram encontradas transações de empréstimo no seu histórico."
        
        aprovados = [t for t in emprestimos if t["valor"] > 0]
        recusados = [t for t in emprestimos if t["valor"] == 0]
        parcelas = [t for t in transacoes if "empréstimo consignado" in t["descricao"].lower()]
        
        resultado = "**Análise do Histórico de Empréstimos:**\n\n"
        
        if aprovados:
            for emp in aprovados:
                resultado += f"✅ **Empréstimo Aprovado:** {emp['data'][:10]}\n"
                resultado += f"   • {emp['descricao']}\n"
                resultado += f"   • Valor: R$ {emp['valor']:.2f}\n\n"
        
        if recusados:
            for emp in recusados:
                resultado += f"❌ **Empréstimo Recusado:** {emp['data'][:10]}\n"
                resultado += f"   • {emp['descricao']}\n\n"
        
        if parcelas:
            total_parcelas = sum(abs(t["valor"]) for t in parcelas)
            resultado += "💳 **Parcelas Pagas:**\n"
            resultado += f"   • Total pago em parcelas: R$ {total_parcelas:.2f}\n"
            resultado += f"   • Número de parcelas pagas: {len(parcelas)}\n"
            resultado += f"   • Valor médio das parcelas: R$ {total_parcelas/len(parcelas):.2f}\n\n"
            
            for parcela in parcelas:
                resultado += f"   • {parcela['data'][:10]}: R$ {abs(parcela['valor']):.2f}\n"
        
        return resultado
    
    def _analisar_fgts(self, transacoes: List[Dict]) -> str:
        """Analisa movimentações do FGTS"""
        fgts_transacoes = [t for t in transacoes if t["tipo"] == "FGTS"]
        
        if not fgts_transacoes:
            return "Não foram encontradas movimentações de FGTS no seu histórico."
        
        total_fgts = sum(t["valor"] for t in fgts_transacoes)
        
        resultado = f"""**Análise das Movimentações FGTS:**

**Total recebido:** R$ {total_fgts:.2f}
**Número de movimentações:** {len(fgts_transacoes)}

**Detalhamento:**
"""
        
        for fgts in fgts_transacoes:
            resultado += f"• {fgts['data'][:10]}: {fgts['descricao']} - R$ {fgts['valor']:.2f}\n"
        
        return resultado
    
    def _analisar_transferencias(self, transacoes: List[Dict]) -> str:
        """Analisa transferências e PIX"""
        transferencias = [t for t in transacoes if t["tipo"] == "transferência"]
        
        if not transferencias:
            return "Não foram encontradas transferências no seu histórico."
        
        recebidas = [t for t in transferencias if t["valor"] > 0]
        enviadas = [t for t in transferencias if t["valor"] < 0]
        
        total_recebido = sum(t["valor"] for t in recebidas)
        total_enviado = sum(abs(t["valor"]) for t in enviadas)
        
        resultado = f"""**Análise de Transferências:**

**Transferências Recebidas:** {len(recebidas)} - Total: R$ {total_recebido:.2f}
**Transferências Enviadas:** {len(enviadas)} - Total: R$ {total_enviado:.2f}

**Transferências Recebidas:**
"""
        
        for t in recebidas:
            resultado += f"• {t['data'][:10]}: {t['descricao']} - R$ {t['valor']:.2f}\n"
        
        if enviadas:
            resultado += "\n**Transferências Enviadas:**\n"
            for t in enviadas:
                resultado += f"• {t['data'][:10]}: {t['descricao']} - R$ {abs(t['valor']):.2f}\n"
        
        return resultado
    
    def _analisar_padroes_gastos(self, transacoes: List[Dict]) -> str:
        """Analisa padrões de gastos do cliente"""
        gastos = [t for t in transacoes if t["valor"] < 0]
        receitas = [t for t in transacoes if t["valor"] > 0]
        
        total_gastos = sum(abs(t["valor"]) for t in gastos)
        total_receitas = sum(t["valor"] for t in receitas)
        
        # Agrupar por tipo
        tipos_gastos = {}
        for t in gastos:
            tipo = t["tipo"]
            tipos_gastos[tipo] = tipos_gastos.get(tipo, 0) + abs(t["valor"])
        
        tipos_receitas = {}
        for t in receitas:
            tipo = t["tipo"]
            tipos_receitas[tipo] = tipos_receitas.get(tipo, 0) + t["valor"]
        
        resultado = f"""**Análise de Padrões Financeiros:**

**Resumo Geral:**
• Total de gastos: R$ {total_gastos:.2f}
• Total de receitas: R$ {total_receitas:.2f}
• Saldo líquido: R$ {total_receitas - total_gastos:.2f}

**Distribuição dos Gastos por Categoria:**
"""
        
        for tipo, valor in sorted(tipos_gastos.items(), key=lambda x: x[1], reverse=True):
            percentual = (valor / total_gastos) * 100
            resultado += f"• {tipo.title()}: R$ {valor:.2f} ({percentual:.1f}%)\n"
        
        resultado += "\n**Distribuição das Receitas por Tipo:**\n"
        
        for tipo, valor in sorted(tipos_receitas.items(), key=lambda x: x[1], reverse=True):
            percentual = (valor / total_receitas) * 100
            resultado += f"• {tipo.title()}: R$ {valor:.2f} ({percentual:.1f}%)\n"
        
        return resultado
    
    def _gerar_resumo_geral(self, transacoes: List[Dict]) -> str:
        """Gera um resumo geral do histórico"""
        if not transacoes:
            return "Nenhuma transação encontrada no histórico."
        
        saldo_inicial = transacoes[0]["saldo"] - transacoes[0]["valor"]
        saldo_final = transacoes[-1]["saldo"]
        primeira_data = transacoes[0]["data"][:10]
        ultima_data = transacoes[-1]["data"][:10]
        
        gastos = [t for t in transacoes if t["valor"] < 0]
        receitas = [t for t in transacoes if t["valor"] > 0]
        
        total_gastos = sum(abs(t["valor"]) for t in gastos)
        total_receitas = sum(t["valor"] for t in receitas)
        
        return f"""**Resumo Completo do Histórico Financeiro:**

**Período:** {primeira_data} a {ultima_data}
**Total de transações:** {len(transacoes)}

**Evolução do Saldo:**
• Saldo inicial: R$ {saldo_inicial:.2f}
• Saldo final: R$ {saldo_final:.2f}
• Variação: R$ {saldo_final - saldo_inicial:.2f}

**Movimentação Financeira:**
• Total de receitas: R$ {total_receitas:.2f} ({len(receitas)} transações)
• Total de gastos: R$ {total_gastos:.2f} ({len(gastos)} transações)
• Saldo líquido do período: R$ {total_receitas - total_gastos:.2f}

**Transação de Maior Valor:**
• Receita: R$ {max([t["valor"] for t in receitas], default=0):.2f}
• Gasto: R$ {max([abs(t["valor"]) for t in gastos], default=0):.2f}

**Média por Transação:**
• Receitas: R$ {total_receitas/len(receitas) if receitas else 0:.2f}
• Gastos: R$ {total_gastos/len(gastos) if gastos else 0:.2f}"""
    
    def _analisar_evolucao_saldo(self, transacoes: List[Dict]) -> str:
        """Analisa a evolução do saldo ao longo do tempo"""
        if not transacoes:
            return "Nenhuma transação encontrada para análise de saldo."
        
        saldo_min = min(t["saldo"] for t in transacoes)
        saldo_max = max(t["saldo"] for t in transacoes)
        saldo_inicial = transacoes[0]["saldo"] - transacoes[0]["valor"]
        saldo_final = transacoes[-1]["saldo"]
        
        # Encontrar quando teve maior e menor saldo
        data_saldo_max = next(t["data"][:10] for t in transacoes if t["saldo"] == saldo_max)
        data_saldo_min = next(t["data"][:10] for t in transacoes if t["saldo"] == saldo_min)
        
        # Determinar tendência
        if saldo_final > saldo_inicial:
            tendencia = "📈 Crescimento"
        elif saldo_final < saldo_inicial:
            tendencia = "📉 Redução"
        else:
            tendencia = "🔄 Estável"
        
        return f"""**Evolução do Saldo Bancário:**

**Saldo inicial:** R$ {saldo_inicial:.2f}
**Saldo final:** R$ {saldo_final:.2f}
**Variação total:** R$ {saldo_final - saldo_inicial:.2f}

**Extremos do período:**
• **Maior saldo:** R$ {saldo_max:.2f} (em {data_saldo_max})
• **Menor saldo:** R$ {saldo_min:.2f} (em {data_saldo_min})
• **Amplitude:** R$ {saldo_max - saldo_min:.2f}

**Tendência:** {tendencia}"""
    
    def _buscar_transacao_especifica(self, transacoes: List[Dict], termo: str) -> str:
        """Busca transações específicas por termo"""
        transacoes_encontradas = []
        
        for t in transacoes:
            if termo.lower() in t["descricao"].lower():
                transacoes_encontradas.append(t)
        
        if not transacoes_encontradas:
            return f"Não foram encontradas transações relacionadas a '{termo}' no seu histórico."
        
        total_valor = sum(t["valor"] for t in transacoes_encontradas)
        
        resultado = f"**Transações relacionadas a '{termo.title()}':**\n\n"
        resultado += f"**Total de transações:** {len(transacoes_encontradas)}\n"
        resultado += f"**Valor total:** R$ {total_valor:.2f}\n\n"
        resultado += "**Detalhamento:**\n"
        
        for t in transacoes_encontradas:
            resultado += f"• **{t['data'][:10]}** - {t['tipo'].title()}\n"
            resultado += f"  {t['descricao']}\n"
            resultado += f"  Valor: R$ {t['valor']:.2f} | Saldo após: R$ {t['saldo']:.2f}\n\n"
        
        return resultado
    
    def _buscar_informacao_geral(self, transacoes: List[Dict], pergunta: str) -> str:
        """Busca informações gerais baseadas na pergunta"""
        # Buscar palavras-chave na pergunta
        palavras_chave = pergunta.lower().split()
        
        transacoes_relevantes = []
        for t in transacoes:
            descricao_lower = t["descricao"].lower()
            if any(palavra in descricao_lower for palavra in palavras_chave):
                transacoes_relevantes.append(t)
        
        if not transacoes_relevantes:
            return f"Não foram encontradas transações relacionadas à sua consulta: '{pergunta}'"
        
        resultado = f"**Transações encontradas para '{pergunta}':**\n\n"
        
        for t in transacoes_relevantes:
            resultado += f"• **{t['data'][:10]}** - {t['tipo'].title()}\n"
            resultado += f"  {t['descricao']}\n"
            resultado += f"  Valor: R$ {t['valor']:.2f} | Saldo após: R$ {t['saldo']:.2f}\n\n"
        
        return resultado
    
    def _formatar_resultado_busca(self, cpf: str, pergunta: str, resultado: str) -> str:
        """Formata o resultado da busca para apresentação ao usuário"""
        
        return f"""📊 **Análise do Histórico de Transações**

**CPF:** {cpf}
**Consulta:** {pergunta}

{resultado}

---
*Informações baseadas no histórico de transações bancárias do cliente*"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Retorna a definição da tool para o function calling"""
        return {
            "type": "function",
            "function": {
                "name": "file_search_agent",
                "description": self.descricao,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cpf": {
                            "type": "string",
                            "description": "CPF do cliente para buscar histórico de transações"
                        },
                        "pergunta": {
                            "type": "string",
                            "description": "Pergunta sobre o histórico de transações, padrões de gastos, empréstimos ou movimentações bancárias"
                        }
                    },
                    "required": ["cpf", "pergunta"],
                    "additionalProperties": False
                }
            }
        }
    
    def listar_cpfs_disponiveis(self) -> List[str]:
        """Lista os CPFs que possuem histórico de transações disponível"""
        if not self.transaction_dir.exists():
            return []
        
        cpfs = []
        for arquivo in self.transaction_dir.glob("*.json"):
            cpf = arquivo.stem
            if cpf.isdigit() and len(cpf) == 11:  # Validação básica de CPF
                cpfs.append(cpf)
        
        return cpfs
    
    def verificar_historico_disponivel(self, cpf: str) -> bool:
        """Verifica se existe histórico para o CPF especificado"""
        arquivo_historico = self.transaction_dir / f"{cpf}.json"
        return arquivo_historico.exists()
    
    def obter_resumo_transacoes(self, cpf: str) -> Optional[Dict[str, Any]]:
        """Obtém resumo básico das transações sem usar file search"""
        arquivo_historico = self.transaction_dir / f"{cpf}.json"
        
        if not arquivo_historico.exists():
            return None
        
        try:
            with open(arquivo_historico, "r", encoding="utf-8") as f:
                transacoes = json.load(f)
            
            if not transacoes:
                return None
            
            total_transacoes = len(transacoes)
            primeira_data = transacoes[0]["data"]
            ultima_data = transacoes[-1]["data"]
            saldo_atual = transacoes[-1]["saldo"]
            
            # Contar tipos de transação
            tipos = {}
            for t in transacoes:
                tipo = t["tipo"]
                tipos[tipo] = tipos.get(tipo, 0) + 1
            
            return {
                "total_transacoes": total_transacoes,
                "primeira_transacao": primeira_data,
                "ultima_transacao": ultima_data,
                "saldo_atual": saldo_atual,
                "tipos_transacao": tipos
            }
            
        except Exception as e:
            print(f"[ERRO] Erro ao ler resumo: {e}")
            return None
    
    def cleanup_vector_stores(self):
        """Método mantido para compatibilidade (não faz nada na versão direta)"""
        print("[DEBUG] Método cleanup_vector_stores chamado - versão direta não usa vector stores")
