import time
import datetime
from robot.data_processor import processar_planilhas_consolidadas

def obter_segundos_ate_proximo_minuto_15():
    """Calcula os segundos restantes até o minuto 15 da próxima hora (ou da hora atual se ainda não passou)."""
    agora = datetime.datetime.now()
    alvo = agora.replace(minute=15, second=0, microsecond=0)
    
    # Se já passou do minuto 15 da hora atual, agenda para a próxima hora
    if alvo <= agora:
        alvo += datetime.timedelta(hours=1)
        
    segundos = (alvo - agora).total_seconds()
    return segundos, alvo

def main():
    print("======================================================")
    print("      Iniciando Monitor de Arquivos Gool System")
    print("======================================================")
    
    # --- ETAPA 1: Varredura de Inicialização Imediata (Catch-up de pendências) ---
    print("\n[INICIALIZAÇÃO] Executando varredura imediata de pendências no OneDrive...")
    while True:
        # Processa as pastas pendentes acumuladas de ontem ou hoje cedo, uma por uma
        processou = processar_planilhas_consolidadas()
        if not processou:
            # Quando retornar False, significa que não há mais nenhuma pasta pendente no OneDrive
            break
        # Curta pausa de segurança antes de processar a próxima pasta pendente encontrada
        time.sleep(3)
        
    print("[INICIALIZAÇÃO] Todas as pendências do mês estão consolidadas e em dia!")
    
    # --- ETAPA 2: Loop Agendado Inteligente (Alinhado com o minuto 15) ---
    while True:
        segundos_espera, proximo_horario = obter_segundos_ate_proximo_minuto_15()
        print(f"\n[AGENDADO] Próxima verificação programada para: {proximo_horario.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"O script aguardará silenciosamente por {int(segundos_espera // 60)} minutos e {int(segundos_espera % 60)} segundos...")
        
        # Hiberna silenciosamente sem gastar processamento
        time.sleep(segundos_espera)
        
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Acordando para verificar novos arquivos do Power Automate...")
        
        # Executa a verificação direta (já que no minuto 15 todos os arquivos do minuto 07 já sincronizaram)
        processou = processar_planilhas_consolidadas()
        if processou:
            print("Novo horário processado e integrado com sucesso!")
        else:
            print("Nenhum arquivo novo para processar ou pasta de hora não localizada.")

if __name__ == "__main__":
    main()