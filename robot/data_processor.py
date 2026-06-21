import os
import glob
import pandas as pd
import json
import subprocess
from datetime import datetime

def processar_planilhas_consolidadas():
    base_onedrive = r"C:\Users\Note Acer Aspire 5\OneDrive\Status de Comunicação"
    pasta_web = r"C:\Projetos em Python\Status de Comunicação"
    
    agora = datetime.now()
    ano = agora.strftime("%Y")
    mes = agora.strftime("%m-%Y") # Pasta do mês atual (ex: 06-2026)
    
    # Aponta para a pasta do mês inteiro, em vez de focar apenas no dia atual
    pasta_mes_atual = os.path.join(base_onedrive, ano, mes)
    
    if not os.path.exists(pasta_mes_atual):
        print(f"A pasta do mês atual não existe ou está vazia: {pasta_mes_atual}")
        return False
        
    # Busca de forma cumulativa e profunda todas as planilhas do mês atual
    todos_arquivos = glob.glob(os.path.join(pasta_mes_atual, "**", "*.xls*"), recursive=True)
    
    # Filtro rigoroso: garante que o arquivo está inserido na árvore correta (dia -> hora -> arquivos)
    arquivos = []
    for f in todos_arquivos:
        pasta_pai = os.path.basename(os.path.dirname(f)) # Ex: "19h"
        pasta_avo = os.path.basename(os.path.dirname(os.path.dirname(f))) # Ex: "20-06-26"
        
        # Validação: pasta pai direta é hora (termina com "h") e pasta avô contém hífen (data)
        if pasta_pai.endswith("h") and pasta_pai[:-1].isdigit() and "-" in pasta_avo:
            arquivos.append(f)
            
    if not arquivos:
        print("Nenhum arquivo de planilha válido foi localizado no diretório do mês atual.")
        return False
        
    print(f"Iniciando consolidação acumulativa de {len(arquivos)} planilhas no mês...")
    lista_dfs = []
    
    for arquivo in arquivos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            
            # Extrai dinamicamente a Hora e a Data a partir da árvore de diretórios do OneDrive
            nome_pasta_hora = os.path.basename(os.path.dirname(arquivo)) # Ex: "19h"
            nome_pasta_dia = os.path.basename(os.path.dirname(os.path.dirname(arquivo))) # Ex: "20-06-26"
            
            # Formata a data de "20-06-26" para "20/06/26"
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
        
    # Consolida todos os dados acumulados de todos os dias e horas
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

    # ======================================================================
    # ENVIO AUTOMÁTICO PARA O GITHUB (ATUALIZAÇÃO DO CLOUDFLARE PAGES)
    # ======================================================================
    try:
        print("Enviando dados atualizados para o GitHub...")
        subprocess.run(["git", "add", "web/dados.json"], check=True)
        # O commit usa o horário atual da consolidação na mensagem
        subprocess.run(["git", "commit", "-m", "Atualizacao automatica: dados historicos do mes"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("GitHub atualizado! O Cloudflare Pages atualizará o site online em instantes.")
    except Exception as e:
        print(f"Não foi possível fazer o push automático para o GitHub: {e}")
    # ======================================================================

    return True

if __name__ == "__main__":
    processar_planilhas_consolidadas()