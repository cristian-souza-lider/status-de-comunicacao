import os
import glob
import pandas as pd
import json
from datetime import datetime

def processar_planilhas_consolidadas():
    base_onedrive = r"C:\Users\Note Acer Aspire 5\OneDrive\Status de Comunicação"
    pasta_web = r"C:\Projetos em Python\Status de Comunicação\web"
    
    agora = datetime.now()
    ano = agora.strftime("%Y")
    mes = agora.strftime("%m-%Y")
    dia = agora.strftime("%d-%m-%y") # Pasta do dia (ex: 20-06-26)
    
    pasta_dia_atual = os.path.join(base_onedrive, ano, mes, dia)
    
    if not os.path.exists(pasta_dia_atual):
        print(f"A pasta do dia atual não existe ou está vazia: {pasta_dia_atual}")
        return False
        
    # Busca de forma cumulativa e profunda (recursiva) todas as planilhas do dia atual
    todos_arquivos = glob.glob(os.path.join(pasta_dia_atual, "**", "*.xls*"), recursive=True)
    
    # Filtro rigoroso: garante que o arquivo está inserido em uma pasta de hora (ex: "16h", "20h")
    arquivos = []
    for f in todos_arquivos:
        pasta_pai = os.path.basename(os.path.dirname(f))
        if pasta_pai.endswith("h") and pasta_pai[:-1].isdigit():
            arquivos.append(f)
            
    if not arquivos:
        print("Nenhum arquivo de planilha válido foi localizado nas pastas de hora do dia atual.")
        return False
        
    print(f"Iniciando consolidação acumulativa de {len(arquivos)} planilhas no dia...")
    lista_dfs = []
    
    for arquivo in arquivos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            
            # Extrai dinamicamente a Hora e a Data a partir da árvore de diretórios do OneDrive
            nome_pasta_hora = os.path.basename(os.path.dirname(arquivo)) # Ex: "19h"
            nome_pasta_dia = os.path.basename(os.path.dirname(os.path.dirname(arquivo))) # Ex: "20-06-26"
            
            # Formata a data "20-06-26" para "20/06/26"
            data_formatada = nome_pasta_dia.replace("-", "/")
            
            df = None
            try:
                df = pd.read_excel(arquivo)
            except Exception:
                try:
                    tabelas_html = pd.read_html(arquivo)
                    if tabelas_html:
                        df = tabelas_html[0]
                except Exception as erro_html:
                    print(f"Não foi possível ler o arquivo {nome_arquivo} como Excel ou HTML: {str(erro_html)}")
                    continue
            
            if df is not None and not df.empty:
                # Injeta a data e hora extraídas das pastas físicas no DataFrame de dados
                df["_data_pasta"] = data_formatada
                df["_hora_pasta"] = nome_pasta_hora
                lista_dfs.append(df)
                
        except Exception as e:
            print(f"Erro ao processar o arquivo {arquivo}: {str(e)}")
            
    if not lista_dfs:
        print("Nenhum dado válido pôde ser extraído das planilhas.")
        return False
        
    # Consolida todos os dados acumulados do dia
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    
    # Converte para dicionário Python padrão (lista de objetos)
    dados_dict = df_consolidado.to_dict(orient="records")
    
    # Limpeza absoluta de NaNs antes de exportar
    for registro in dados_dict:
        for chave, valor in registro.items():
            if pd.isna(valor):
                registro[chave] = None  
                
    os.makedirs(pasta_web, exist_ok=True)
    caminho_json = os.path.join(pasta_web, "dados.json")
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(dados_dict, f, ensure_ascii=False, indent=4)
        
    print(f"Consolidação concluída. {len(dados_dict)} registros acumulados salvos em: {caminho_json}")
    return True

if __name__ == "__main__":
    processar_planilhas_consolidadas()