
# Refatoração: arquitetura handoff + orchestrator (OpenAI Agents SDK)
import os
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from utils.file_utils import carregar_usuarios, validar_cpf, carregar_historico, salvar_historico, adicionar_cpf_ao_contexto
from agents_openai import run_agent_loop, enviar_boas_vindas

# Configuração
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
HISTORY_DIR = Path("chat_history")

def main():
    print("=== Sistema de Atendimento Caixa ===\n")
    base_usuarios = carregar_usuarios()
    if not base_usuarios:
        print("Não foi possível carregar a base de usuários. Encerrando.")
        return
    cpf = input("Digite seu CPF: ").strip()
    if not validar_cpf(cpf, base_usuarios):
        print("CPF não encontrado na base de dados. Encerrando.")
        return
    nome = base_usuarios[cpf]["nome"]
    historico = carregar_historico(cpf, HISTORY_DIR)
    if not historico:
        historico.append({"role": "system", "content": f"O CPF do usuário para esta sessão é {cpf}."})
        enviar_boas_vindas(nome, historico)
        salvar_historico(cpf, historico, HISTORY_DIR)
    else:
        adicionar_cpf_ao_contexto(historico, cpf)
        print(f"\nAssistente: Olá novamente, {nome}! Como posso ajudá-lo hoje? 😊\n")
    try:
        while True:
            pergunta = input("Você: ").strip()
            if pergunta.lower() in ["sair", "exit", "quit"]:
                print("Encerrando conversa.")
                break
            
            print("\n🔄 [MAIN] Processando mensagem via OpenAI Agents...")
            
            # Usar agents_openai diretamente com guardrails e histórico integrados
            context_data = {"cpf": cpf, "nome": nome, "base_usuarios": base_usuarios, "historico": historico}
            resposta_texto, agente_usado = run_agent_loop(pergunta, context_data)
            
            print(f"💾 [MAIN] Salvando no histórico com agent: {agente_usado}")
            print(f"\nAssistente: {resposta_texto}\n")
            
            # Atualizar histórico com o agente correto
            historico.extend([
                {"role": "user", "content": pergunta},
                {"role": "assistant", "content": resposta_texto, "agent": agente_usado}
            ])
            
            # Salvar histórico
            salvar_historico(cpf, historico, HISTORY_DIR)
            print(f"✅ [MAIN] Histórico salvo com {len(historico)} mensagens")
    except KeyboardInterrupt:
        print("\nSistema encerrado pelo usuário.")
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")

if __name__ == "__main__":
    main()
