import time
from datetime import datetime
from robot.data_processor import processar_planilhas_consolidadas

def main():
    print("======================================================")
    print("      Iniciando Monitor de Arquivos Gool System")
    print("    Aguardando sincronização do Power Automate...")
    print("======================================================")
    
    while True:
        # Executa o processador. Se houver 14 arquivos, ele os processa, limpa a pasta e faz o push.
        processou = processar_planilhas_consolidadas()
        
        if processou:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Ciclo concluído. Aguardando novos arquivos do próximo horário...")
            # Aguarda 10 minutos de pausa de segurança antes de reiniciar a escuta ativa
            time.sleep(600)
        else:
            # Aguarda 20 segundos antes de verificar novamente
            time.sleep(20)

if __name__ == "__main__":
    main()