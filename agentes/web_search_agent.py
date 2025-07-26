from typing import Dict, Any, Optional
from openai import OpenAI
from .base_agent import BaseAgent


class WebSearchAgent(BaseAgent):
    """Agente especializado em busca web para informações bancárias atualizadas"""
    
    def __init__(self, client: OpenAI):
        super().__init__(
            nome="Web Search Agent",
            descricao="Busca informações públicas e atualizadas na internet sobre temas bancários, FGTS, taxas de juros, notícias e regras relevantes para empréstimos e consignados"
        )
        self.client = client
    
    def processar(self, pergunta: str, localizacao: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Processa uma busca web para informações bancárias
        
        Args:
            pergunta: Pergunta/consulta para buscar na web
            localizacao: País, cidade ou região para contextualizar a busca (opcional)
            
        Returns:
            Dict com resultado da busca web
        """
        try:
            # Construir a pergunta com contexto bancário
            pergunta_contextualizada = self._construir_pergunta_contextualizada(pergunta, localizacao)
            
            print(f"[DEBUG] Executando busca web: {pergunta_contextualizada}")
            
            # Executar busca usando gpt-4o-search-preview
            completion = self.client.chat.completions.create(
                model="gpt-4o-search-preview",
                web_search_options={
                    "search_context_size": "low",  # Opções: "low", "medium", "high"
                },
                messages=[{
                    "role": "user",
                    "content": pergunta_contextualizada,
                }],
            )
            
            resposta = completion.choices[0].message.content
            
            return {
                "erro": False,
                "pergunta_original": pergunta,
                "pergunta_processada": pergunta_contextualizada,
                "localizacao": localizacao,
                "resultado": resposta,
                "mensagem": self._formatar_resultado_busca(pergunta, resposta)
            }
            
        except Exception as e:
            print(f"[ERRO] Erro na busca web: {e}")
            return {
                "erro": True,
                "pergunta_original": pergunta,
                "mensagem": f"Não foi possível realizar a busca web. Erro: {str(e)}",
                "resultado": None
            }
    
    def _construir_pergunta_contextualizada(self, pergunta: str, localizacao: Optional[str]) -> str:
        """Constrói pergunta com contexto bancário brasileiro"""
        
        # Contexto base para busca bancária
        contexto_bancario = (
            "Busque informações atualizadas sobre temas bancários, financeiros e do sistema financeiro. "
            "Foque em: Caixa Econômica Federal, bancos brasileiros, FGTS, empréstimos consignados, "
            "taxas de juros, regulamentações bancárias, Banco Central do Brasil, e legislação financeira."
        )
        
        # Adicionar localização se fornecida
        if localizacao:
            contexto_localizacao = f" Contextualize as informações para: {localizacao}."
        else:
            contexto_localizacao = " Foque em informações do Brasil e sistema bancário brasileiro."
        
        pergunta_final = f"{contexto_bancario}{contexto_localizacao}\n\nPergunta: {pergunta}"
        
        return pergunta_final
    
    def _formatar_resultado_busca(self, pergunta: str, resultado: str) -> str:
        """Formata o resultado da busca para apresentação ao usuário"""
        
        return f"""🔍 **Busca Web - Informações Atualizadas**

**Consulta:** {pergunta}

**Resultado:**
{resultado}

---
*Informações obtidas através de busca web atualizada*"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Retorna a definição da tool para o function calling"""
        return {
            "type": "function",
            "function": {
                "name": "web_search_agent",
                "description": self.descricao,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pergunta": {
                            "type": "string",
                            "description": "Pergunta ou consulta sobre temas bancários, FGTS, taxas de juros, empréstimos ou assuntos financeiros"
                        },
                        "localizacao": {
                            "type": "string",
                            "description": "País, cidade ou região para contextualizar a busca (opcional, padrão: Brasil)",
                            "default": "Brasil"
                        }
                    },
                    "required": ["pergunta"],
                    "additionalProperties": False
                }
            }
        }
    
    def validar_pergunta(self, pergunta: str) -> bool:
        """Valida se a pergunta é adequada para busca bancária"""
        if not pergunta or not pergunta.strip():
            return False
        
        # Lista de termos relevantes para busca bancária
        termos_bancarios = [
            'banco', 'bancário', 'bancaria', 'caixa', 'fgts', 'empréstimo', 'emprestimo',
            'consignado', 'juros', 'taxa', 'crédito', 'credito', 'financiamento',
            'poupança', 'poupanca', 'conta', 'cartão', 'cartao', 'financeiro',
            'financeira', 'central', 'bacen', 'cdb', 'investimento', 'aposentadoria',
            'pensão', 'pensao', 'saque', 'transferência', 'transferencia', 'pix'
        ]
        
        pergunta_lower = pergunta.lower()
        return any(termo in pergunta_lower for termo in termos_bancarios)
    
    def obter_temas_sugeridos(self) -> list:
        """Retorna lista de temas sugeridos para busca"""
        return [
            "Taxas de juros atuais do Banco Central",
            "Novas regras do FGTS em 2025",
            "Condições de empréstimo consignado",
            "Mudanças na legislação bancária",
            "Taxas de financiamento imobiliário",
            "Novidades da Caixa Econômica Federal",
            "Regulamentações sobre PIX",
            "Investimentos em poupança e CDB",
            "Direitos do consumidor bancário",
            "Portabilidade de crédito consignado"
        ]
