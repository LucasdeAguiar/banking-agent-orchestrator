import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, AutoReconnect

load_dotenv()

MONGO_URI        = os.getenv("MONGO_URI")
MONGO_DB         = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

client = None
db = None
colecao = None
conexao_disponivel = False

def inicializar_conexao():
    """Tenta inicializar a conexão com o Cosmos DB"""
    global client, db, colecao, conexao_disponivel
    
    try:
        client = MongoClient(MONGO_URI, 
                           serverSelectionTimeoutMS=10000,
                           connectTimeoutMS=10000,
                           socketTimeoutMS=10000)
        client.admin.command("ping")
        db = client[MONGO_DB]
        colecao = db[MONGO_COLLECTION]
        conexao_disponivel = True
        print("Conectado ao CosmosDB")
        return True
    except Exception as e:
        print(f"[AVISO] Cosmos DB não disponível: {str(e)[:100]}...")
        print("[LOG] Sistema funcionará apenas com arquivos locais.")
        conexao_disponivel = False
        return False

def verificar_conexao():
    global conexao_disponivel
    if not conexao_disponivel:
        return False
    
    try:
        client.admin.command("ping")
        return True
    except Exception:
        print("[AVISO] Conexão com Cosmos DB perdida.")
        conexao_disponivel = False
        return False

def buscar_mensagens_por_agente_db(cpf: str, agente: str) -> list:
    """Busca mensagens de um agente específico no Cosmos DB"""
    if not verificar_conexao():
        return []
    
    try:
        # Buscar documento do CPF
        documento = colecao.find_one({"cpf": cpf})
        if not documento or "historico" not in documento:
            return []
        
        # Filtrar mensagens do agente
        mensagens_agente = []
        for mensagem in documento["historico"]:
            if (mensagem.get("role") == "assistant" and 
                mensagem.get("agent") == agente):
                mensagens_agente.append(mensagem)
        
        return mensagens_agente
        
    except Exception as e:
        print(f"[ERRO] Erro ao buscar mensagens por agente: {e}")
        return []


def listar_agentes_usados_db(cpf: str) -> list:
    """Lista agentes usados para um CPF no Cosmos DB"""
    if not verificar_conexao():
        return []
    
    try:
        # Usar agregação para extrair agentes únicos
        pipeline = [
            {"$match": {"cpf": cpf}},
            {"$unwind": "$historico"},
            {"$match": {
                "historico.role": "assistant",
                "historico.agent": {"$exists": True}
            }},
            {"$group": {"_id": "$historico.agent"}},
            {"$sort": {"_id": 1}}
        ]
        
        resultado = colecao.aggregate(pipeline)
        agentes = [doc["_id"] for doc in resultado]
        
        return agentes
        
    except Exception as e:
        print(f"[ERRO] Erro ao listar agentes: {e}")
        return []


def estatisticas_agentes_db(cpf: str) -> dict:
    """Retorna estatísticas de uso dos agentes no Cosmos DB"""
    if not verificar_conexao():
        return {}
    
    try:
        pipeline = [
            {"$match": {"cpf": cpf}},
            {"$unwind": "$historico"},
            {"$match": {
                "historico.role": "assistant",
                "historico.agent": {"$exists": True}
            }},
            {"$group": {
                "_id": "$historico.agent",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        resultado = colecao.aggregate(pipeline)
        estatisticas = {doc["_id"]: doc["count"] for doc in resultado}
        
        return estatisticas
        
    except Exception as e:
        print(f"[ERRO] Erro ao obter estatísticas: {e}")
        return {}


inicializar_conexao()
