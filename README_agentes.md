# Sistema de Tags de Agentes - Documentação

## Visão Geral

O sistema foi atualizado para incluir identificação de agentes nas mensagens do assistente, permitindo consultas específicas por tipo de agente no histórico de conversas.

## Tipos de Agentes

### Agentes Principais
- **`assistant_inicial`** - Mensagens de boas-vindas
- **`assistant_geral`** - Respostas gerais sem uso de ferramentas
- **`emprestimo_agent`** - Simulações e aprovações de empréstimos
- **`analise_risco_agent`** - Análises de risco creditício
- **`web_search_agent`** - Buscas na web (cotações, informações externas)
- **`file_search_agent`** - Consultas ao histórico de transações
- **`guardrail`** - Mensagens bloqueadas por guardrails
- **`assistant_erro`** - Mensagens de erro do sistema

## Formato do Histórico

### Antes (sem agente)
```json
{
  "role": "assistant",
  "content": "Olá! Como posso ajudar?"
}
```

### Depois (com agente)
```json
{
  "role": "assistant",
  "content": "Olá! Como posso ajudar?",
  "agent": "assistant_inicial"
}
```

## Funções Disponíveis

### 1. Buscar mensagens por agente
```python
from utils.file_utils import buscar_mensagens_por_agente

# Buscar todas as mensagens do agente de empréstimo
mensagens = buscar_mensagens_por_agente("19104630785", "emprestimo_agent")
```

### 2. Listar agentes utilizados
```python
from utils.file_utils import listar_agentes_usados

# Lista todos os agentes que já foram usados
agentes = listar_agentes_usados("19104630785")
# Retorna: ['assistant_inicial', 'emprestimo_agent', 'web_search_agent']
```

### 3. Estatísticas de uso
```python
from utils.file_utils import estatisticas_agentes

# Conta quantas mensagens cada agente enviou
stats = estatisticas_agentes("19104630785")
# Retorna: {'assistant_geral': 5, 'emprestimo_agent': 2, 'web_search_agent': 1}
```

## Consultas no Banco de Dados

### MongoDB/Cosmos DB

#### Buscar mensagens de um agente específico
```javascript
db.chat_history.find({
  "cpf": "19104630785",
  "historico": {
    "$elemMatch": {
      "role": "assistant",
      "agent": "emprestimo_agent"
    }
  }
})
```

#### Listar agentes únicos por CPF
```javascript
db.chat_history.aggregate([
  {"$match": {"cpf": "19104630785"}},
  {"$unwind": "$historico"},
  {"$match": {
    "historico.role": "assistant",
    "historico.agent": {"$exists": true}
  }},
  {"$group": {"_id": "$historico.agent"}},
  {"$sort": {"_id": 1}}
])
```

#### Estatísticas de uso dos agentes
```javascript
db.chat_history.aggregate([
  {"$match": {"cpf": "19104630785"}},
  {"$unwind": "$historico"},
  {"$match": {
    "historico.role": "assistant",
    "historico.agent": {"$exists": true}
  }},
  {"$group": {
    "_id": "$historico.agent",
    "count": {"$sum": 1}
  }},
  {"$sort": {"count": -1}}
])
```

## Exemplos de Uso

### Script de Consulta Simples
```python
#!/usr/bin/env python3
from utils.file_utils import buscar_mensagens_por_agente

def consultar_emprestimos(cpf):
    """Consulta todas as interações sobre empréstimos"""
    mensagens = buscar_mensagens_por_agente(cpf, "emprestimo_agent")
    
    print(f"=== Histórico de Empréstimos - CPF: {cpf} ===")
    for i, msg in enumerate(mensagens, 1):
        print(f"{i}. {msg['content']}")

# Uso
consultar_emprestimos("19104630785")
```

### Relatório de Atividades por Agente
```python
def relatorio_atividades(cpf):
    """Gera relatório de atividades por agente"""
    from utils.file_utils import estatisticas_agentes, listar_agentes_usados
    
    print(f"=== Relatório de Atividades - CPF: {cpf} ===")
    
    # Estatísticas gerais
    stats = estatisticas_agentes(cpf)
    total_mensagens = sum(stats.values())
    
    print(f"Total de mensagens do assistente: {total_mensagens}")
    print("\nDistribuição por agente:")
    
    for agente, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        percentual = (count / total_mensagens) * 100
        print(f"  {agente}: {count} mensagens ({percentual:.1f}%)")

# Uso
relatorio_atividades("19104630785")
```

## Migração de Dados Existentes

Para dados existentes sem tags de agente, as mensagens podem ser categorizadas retroativamente:

```python
def migrar_historico_existente(cpf):
    """Adiciona tags de agente ao histórico existente"""
    from utils.file_utils import carregar_historico, salvar_historico
    from pathlib import Path
    
    historico = carregar_historico(cpf, Path("chat_history"))
    
    for mensagem in historico:
        if mensagem.get("role") == "assistant" and "agent" not in mensagem:
            # Lógica para determinar o agente baseado no conteúdo
            content = mensagem["content"].lower()
            
            if "bem-vindo" in content or "olá" in content[:50]:
                mensagem["agent"] = "assistant_inicial"
            elif "empréstimo" in content and ("aprovado" in content or "parcela" in content):
                mensagem["agent"] = "emprestimo_agent"
            elif "transação" in content or "saldo" in content:
                mensagem["agent"] = "file_search_agent"
            elif "cotação" in content or "dólar" in content:
                mensagem["agent"] = "web_search_agent"
            else:
                mensagem["agent"] = "assistant_geral"
    
    salvar_historico(cpf, historico, Path("chat_history"))
```

## Benefícios

1. **Análise de Comportamento**: Identificar quais funcionalidades os usuários mais utilizam
2. **Melhoria de Agentes**: Focar no desenvolvimento dos agentes mais utilizados
3. **Relatórios Específicos**: Gerar relatórios por tipo de serviço
4. **Debugging**: Facilitar a identificação de problemas em agentes específicos
5. **Personalização**: Adaptar respostas baseadas no histórico de uso de agentes

## Scripts Utilitários

Execute `consulta_agentes.py` para ver exemplos práticos:

```bash
python consulta_agentes.py
```

Este script demonstra todas as funcionalidades de consulta por agente implementadas.
