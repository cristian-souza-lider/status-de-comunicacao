import time
import datetime
from robot.web_robot import executar_robot
from robot.data_processor import processar_planilhas_consolidadas

def obter_segundos_ate_proximo_minuto_10():
    """Calcula quantos segundos faltam para o minuto 10 da próxima hora."""
    agora = datetime.datetime.now()
    
    # Define o alvo para o minuto 10 da hora atual
    proximo_alvo = agora.replace(minute=10, second=0, microsecond=0)
    
    # Se já passamos do minuto 10 da hora atual, agenda para a próxima hora
    if proximo_alvo <= agora:
        proximo_alvo += datetime.timedelta(hours=1)
        
    segundos_espera = (proximo_alvo - agora).total_seconds()
    return segundos_espera, proximo_alvo

def rodar_ciclo_completo():
    print(f"\n--- Iniciando Ciclo: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ---")
    try:
        # 1. Executa o robô para fazer downloads das empresas
        executar_robot()
        
        # 2. Consolida as planilhas baixadas no dados.json
        processar_planilhas_consolidadas()
    except Exception as e:
        print(f"Erro detectado durante o ciclo: {str(e)}")
    print("--- Ciclo finalizado com sucesso ---")

def main():
    print("Iniciando o sistema Status de Comunicação...")
    
    # Primeira execução imediata
    rodar_ciclo_completo()
    
    # Loop de agendamento contínuo
    while True:
        segundos, proxima_corrida = obter_segundos_ate_proximo_minuto_10()
        print(f"\n[AGENDADO] Próxima execução programada para: {proxima_corrida.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"O script aguardará {int(segundos // 60)} minutos e {int(segundos % 60)} segundos.")
        
        # Aguarda até o minuto 10 planejado
        time.sleep(segundos)
        
        # Executa o ciclo novamente
        rodar_ciclo_completo()

if __name__ == "__main__":
    main()