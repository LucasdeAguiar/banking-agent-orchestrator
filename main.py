import os
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from utils.file_utils import carregar_usuarios, validar_cpf, carregar_historico, salvar_historico
from utils.chat_manager import ChatManager

# Configuração
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

HISTORY_DIR = Path("chat_history")


def main():
    """Função principal do sistema de chat"""
    print("=== Sistema de Atendimento Caixa ===\n")
    
    # Carregar base de usuários
    base_usuarios = carregar_usuarios()
    if not base_usuarios:
        print("Não foi possível carregar a base de usuários. Encerrando.")
        return
    
    # Solicitar e validar CPF
    cpf = input("Digite seu CPF: ").strip()
    
    if not validar_cpf(cpf, base_usuarios):
        print("CPF não encontrado na base de dados. Encerrando.")
        return
    
    nome = base_usuarios[cpf]["nome"]
    
    # Inicializar chat manager
    chat_manager = ChatManager(client, HISTORY_DIR)
    historico = carregar_historico(cpf, HISTORY_DIR)
    
    # Gerenciar boas-vindas e contexto
    if not historico:
        historico.append({"role": "system", "content": f"O CPF do usuário para esta sessão é {cpf}."})
        chat_manager.enviar_boas_vindas(nome, historico)
        salvar_historico(cpf, historico, HISTORY_DIR)
    else:
        chat_manager.preparar_historico_para_sessao(historico, cpf)
        print(f"\nAssistente: Olá novamente, {nome}! Como posso ajudá-lo hoje? 😊\n")
    
    # Loop principal da conversa
    try:
        while True:
            pergunta = input("Você: ").strip()
            if pergunta.lower() in ["sair", "exit", "quit"]:
                print("Encerrando conversa.")
                break
            
            # Processar mensagem
            resposta_texto, agente_usado = chat_manager.processar_mensagem(
                pergunta, historico, cpf, base_usuarios
            )
            
            # Atualizar histórico
            historico.extend([
                {"role": "user", "content": pergunta},
                {"role": "assistant", "content": resposta_texto, "agent": agente_usado}
            ])
            
            # Salvar histórico
            salvar_historico(cpf, historico, HISTORY_DIR)
            
    except KeyboardInterrupt:
        print("\nSistema encerrado pelo usuário.")
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")


if __name__ == "__main__":
    main()
