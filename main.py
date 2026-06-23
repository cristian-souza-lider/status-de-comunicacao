import time
import datetime
from robot.data_processor import processar_planilhas_consolidadas

def obter_segundos_ate_proximo_minuto_10():
    """Calcula os segundos restantes até o minuto 10 da próxima hora (ou da hora atual se ainda não passou)."""
    agora = datetime.datetime.now()
    alvo = agora.replace(minute=10, second=0, microsecond=0)
    
    # Se já passou do minuto 10 da hora atual, agenda para a próxima hora
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
            # Quando retornar False, significa que não há mais nenhuma pasta pendente atrasada
            break
        # Curta pausa de segurança antes de processar a próxima pasta pendente encontrada
        time.sleep(3)
        
    print("[INICIALIZAÇÃO] Todas as pendências do mês estão consolidadas e em dia!")
    
    # --- ETAPA 2: Loop Agendado Inteligente (Alinhado com o minuto 07 do Power Automate) ---
    while True:
        segundos_espera, proximo_horario = obter_segundos_ate_proximo_minuto_10()
        print(f"\n[AGENDADO] Próxima verificação programada para: {proximo_horario.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"O script aguardará silenciosamente por {int(segundos_espera // 60)} minutos e {int(segundos_espera % 60)} segundos...")
        
        # Hiberna silenciosamente sem gastar processamento
        time.sleep(segundos_espera)
        
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Acordando para verificar novos arquivos do Power Automate...")
        
        # Loop inteligente de segurança caso a sincronização do OneDrive demore um pouco mais
        tentativas = 0
        sucesso = False
        while tentativas < 15:  # Tenta por até ~11 minutos (15 tentativas x 45 segundos)
            processou = processar_planilhas_consolidadas()
            if processou:
                print("Novo horário processado e integrado com sucesso!")
                sucesso = True
                break
            else:
                # Se não processou, a pasta existe mas a sincronização dos 14 arquivos ainda está em andamento
                print(f"Aguardando sincronização completa dos 14 arquivos no OneDrive (Tentativa {tentativas + 1}/15)...")
                time.sleep(45)
                tentativas += 1
                
        if not sucesso:
            print("[AVISO] Tempo limite de sincronização expirou. O script tentará consolidar estes arquivos no próximo ciclo agendado.")

if __name__ == "__main__":
    main()