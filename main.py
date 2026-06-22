import time
from datetime import datetime
from robot.data_processor import processar_planilhas_consolidadas

def main():
    print("======================================================")
    print("      Iniciando Monitor de Arquivos Gool System")
    print("    Aguardando sincronização do Power Automate...")
    print("======================================================")
    
    while True:
        # Se houver 14 arquivos e nenhum marcador de processado, consolida e cria o marcador
        processou = processar_planilhas_consolidadas()
        
        if processou:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Ciclo concluído. Aguardando novos arquivos do próximo horário...")
            
        # Verifica a pasta a cada 15 segundos para agilizar a exibição
        time.sleep(15)

if __name__ == "__main__":
    main()