import json
from datetime import datetime
from pathlib import Path
from db import colecao, conexao_disponivel, verificar_conexao


def carregar_prompt():
    """Carrega o prompt base do arquivo JSON"""
    with open("prompt.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["base_prompt"]


def carregar_historico(cpf: str, history_dir: Path) -> list:
    """Carrega histórico do banco ou arquivo local"""
    if conexao_disponivel and verificar_conexao():
        try:
            documento = colecao.find_one({"cpf": cpf})
            if documento and "historico" in documento:
                print(f"[LOG] Histórico carregado do Cosmos DB para CPF: {cpf}")
                return documento["historico"]
        except Exception as e:
            print(f"[ERRO] Erro ao carregar do Cosmos DB: {e}")
    
    caminho = history_dir / f"{cpf}.json"
    if caminho.exists():
        print(f"[LOG] Histórico carregado do arquivo local para CPF: {cpf}")
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    
    return []


def salvar_historico(cpf: str, historico: list, history_dir: Path) -> None:
    """Salva histórico no banco ou arquivo local"""
    if conexao_disponivel and verificar_conexao():
        try:
            documento = {
                "cpf": cpf,
                "historico": historico,
                "ultima_atualizacao": datetime.now().isoformat(),
                "total_mensagens": len(historico)
            }
            
            resultado = colecao.replace_one(
                {"cpf": cpf}, 
                documento, 
                upsert=True
            )
            
            if resultado.upserted_id or resultado.modified_count > 0:
                print("[LOG] Histórico salvo no Cosmos DB")
                return
                
        except Exception as e:
            print(f"[ERRO] Erro ao salvar no Cosmos DB: {e}")
    
    print("[LOG] Salvando em arquivo local..")
    caminho = history_dir / f"{cpf}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


def carregar_usuarios(arquivo: str = "users.json") -> dict:
    """Carrega base de usuários do arquivo JSON"""
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERRO] Arquivo {arquivo} não encontrado.")
        return {}
    except json.JSONDecodeError:
        print(f"[ERRO] Erro ao decodificar {arquivo}.")
        return {}


def validar_cpf(cpf: str, usuarios: dict) -> bool:
    """Valida se CPF existe na base de dados"""
    return cpf in usuarios


def adicionar_cpf_ao_contexto(historico: list, cpf: str) -> None:
    """Adiciona CPF ao contexto se não estiver presente"""
    if not any(item.get("role") == "system" and "CPF do usuário" in item.get("content", "") 
               for item in historico):
        historico.insert(0, {"role": "system", "content": f"O CPF do usuário para esta sessão é {cpf}."})


def buscar_mensagens_por_agente(cpf: str, agente: str, history_dir: Path = None) -> list:
    """Busca mensagens específicas de um agente para um CPF"""
    if history_dir is None:
        history_dir = Path("chat_history")
    
    historico = carregar_historico(cpf, history_dir)
    mensagens_agente = []
    
    for mensagem in historico:
        if (mensagem.get("role") == "assistant" and 
            mensagem.get("agent") == agente):
            mensagens_agente.append(mensagem)
    
    return mensagens_agente


def listar_agentes_usados(cpf: str, history_dir: Path = None) -> list:
    """Lista todos os agentes que já foram usados em conversas com um CPF"""
    if history_dir is None:
        history_dir = Path("chat_history")
    
    historico = carregar_historico(cpf, history_dir)
    agentes = set()
    
    for mensagem in historico:
        if (mensagem.get("role") == "assistant" and 
            "agent" in mensagem):
            agentes.add(mensagem["agent"])
    
    return sorted(agentes)


def estatisticas_agentes(cpf: str, history_dir: Path = None) -> dict:
    """Retorna estatísticas de uso dos agentes para um CPF"""
    if history_dir is None:
        history_dir = Path("chat_history")
    
    historico = carregar_historico(cpf, history_dir)
    estatisticas = {}
    
    for mensagem in historico:
        if (mensagem.get("role") == "assistant" and 
            "agent" in mensagem):
            agente = mensagem["agent"]
            if agente not in estatisticas:
                estatisticas[agente] = 0
            estatisticas[agente] += 1
    
    return estatisticas
