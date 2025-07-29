from typing import Dict, Tuple, Optional
from openai import OpenAI

class ModerationManager:  
    def __init__(self, client: OpenAI, debug: bool = False):
        self.client = client
        self.debug = debug
    
    def moderar_conteudo(self, texto: str) -> Tuple[bool, str, Optional[Dict]]:
        try:
            if self.debug:
                print(f"[DEBUG] Moderando: '{texto[:50]}...'")

            response = self.client.moderations.create(
                model="omni-moderation-latest",
                input=texto
            )
            
            resultado = response.results[0]
            
            # Se foi flagged, bloquear
            if resultado.flagged:
                if self.debug:
                    categorias_ativas = [k for k, v in resultado.categories.__dict__.items() if v]
                    print(f"[MODERATION] Bloqueado - Categorias: {categorias_ativas}")
                
                return True, self._gerar_mensagem_bloqueio(resultado), response.model_dump()
            
            if self.debug:
                print("[MODERATION] Aprovado")
            
            return False, "", None
            
        except Exception as e:
            print(f"[ERRO] Erro na moderação: {e}")
            return False, "", None 
    
    def _gerar_mensagem_bloqueio(self, resultado) -> str:
        """Gera mensagem de bloqueio simples"""
        
        categorias_graves = ["violence", "harassment_threatening", "hate_threatening", "sexual_minors"]
        categorias_ativas = [k for k, v in resultado.categories.__dict__.items() if v]
        
        categoria_encontrada = None
        for categoria in categorias_graves:
            if categoria in categorias_ativas:
                categoria_encontrada = categoria
                break
        
        mensagens = {
            "violence": "conteúdo violento",
            "harassment": "assédio ou intimidação", 
            "harassment_threatening": "ameaças",
            "hate": "discurso de ódio",
            "sexual": "conteúdo sexual inapropriado",
            "illicit": "atividades ilegais",
            "illicit_violent": "atividades ilegais violentas", 
            "self_harm": "conteúdo relacionado a autolesão"
        }
        
        # Encontrar descrição ou usar genérica
        DESCRICAO_PADRAO = "conteúdo inapropriado"
        descricao = DESCRICAO_PADRAO
        if categoria_encontrada:
            descricao = mensagens.get(categoria_encontrada, DESCRICAO_PADRAO)
        elif categorias_ativas:
            primeira_categoria = categorias_ativas[0]
            descricao = mensagens.get(primeira_categoria, DESCRICAO_PADRAO)
        
        return f"""🚫 **Conteúdo Bloqueado**

Sua mensagem foi bloqueada por conter {descricao}.

Este é um sistema de atendimento bancário profissional. Por favor, mantenha suas perguntas relacionadas aos serviços da Caixa Econômica Federal.

Como posso ajudá-lo com questões sobre empréstimos, FGTS ou outros serviços bancários?"""
    
    def obter_detalhes_moderacao(self, response_dict: Dict) -> str:
        """Gera relatório simples para debug (opcional)"""
        if not response_dict:
            return "Nenhum dado disponível"
        
        resultado = response_dict['results'][0]
        flagged = resultado['flagged']
        
        if not flagged:
            return "✅ Conteúdo aprovado"
        
        categorias_ativas = [k for k, v in resultado['categories'].items() if v]
        
        return f"""📊 Moderação: {'🚫 Bloqueado' if flagged else '✅ Aprovado'}
Categorias ativas: {', '.join(categorias_ativas) if categorias_ativas else 'Nenhuma'}"""
