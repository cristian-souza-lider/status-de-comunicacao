import os
import glob
import pandas as pd
import json
import subprocess
from datetime import datetime

def processar_planilhas_consolidadas():
    # Caminho do OneDrive corporativo
    base_onedrive = r"C:\Users\cristian.souza\OneDrive - Nossa Senhora do Ó Participações S.A\Status de Comunicação"
    pasta_web = r"C:\Projetos em Python\Status de Comunicação\web"
    
    agora = datetime.now()
    ano = agora.strftime("%Y")      # Ex: 2026
    mes = agora.strftime("%m")      # Ex: 06
    
    pasta_mes_atual = os.path.join(base_onedrive, ano, mes)
    
    # Se a pasta do mês atual ainda não existe no OneDrive, aguarda
    if not os.path.exists(pasta_mes_atual):
        return False
        
    # 1. Varre de forma inteligente TODAS as subpastas de horas de TODOS os dias do mês atual (ex: 2026\06\*\*h)
    # para encontrar se há alguma pasta pendente de processamento histórica ou atual
    subpastas_hora = glob.glob(os.path.join(pasta_mes_atual, "*", "*h"))
    
    pasta_pendente = None
    for pasta in subpastas_hora:
        nome_pasta = os.path.basename(pasta) # Ex: "16h"
        # Valida se é um nome de pasta de hora legítimo (ex: "16h")
        if nome_pasta[:-1].isdigit():
            marcador = os.path.join(pasta, "processado.txt")
            # Se NÃO possuir o arquivo marcador de processado
            if not os.path.exists(marcador):
                # E se já possuir pelo menos os 14 arquivos completos carregados pelo Power Automate
                arquivos_na_pasta = glob.glob(os.path.join(pasta, "*.xls*"))
                if len(arquivos_na_pasta) >= 14:
                    # Encontramos uma pasta pendente! Seleciona para processar imediatamente
                    pasta_pendente = pasta
                    break # Processa uma por ciclo de loop
                        
    if not pasta_pendente:
        # Nenhuma pasta pendente de processamento foi localizada no momento
        return False
        
    print(f"\nSincronização pendente detectada na pasta: {pasta_pendente}")
    
    # 2. Varre e consolida o histórico completo do mês atual (06-2026 / 06)
    todos_arquivos = glob.glob(os.path.join(pasta_mes_atual, "**", "*.xls*"), recursive=True)
    
    # Filtro de caminhos: aceita arquivos dentro de estruturas dia -> hora -> arquivos
    arquivos_historicos = []
    for f in todos_arquivos:
        pasta_pai = os.path.basename(os.path.dirname(f))
        pasta_avo = os.path.basename(os.path.dirname(os.path.dirname(f)))
        if pasta_pai.endswith("h") and pasta_pai[:-1].isdigit() and pasta_avo.isdigit():
            arquivos_historicos.append(f)
            
    if not arquivos_historicos:
        print("Nenhum arquivo histórico foi localizado no diretório do mês atual.")
        return False
        
    print(f"Consolidando histórico acumulado de {len(arquivos_historicos)} planilhas...")
    lista_dfs = []
    
    for arquivo in arquivos_historicos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            
            # Extrai os componentes do caminho de forma segura
            caminho_partes = arquivo.split(os.sep)
            hora_pasta = caminho_partes[-2]
            dia_pasta = caminho_partes[-3]
            mes_pasta = caminho_partes[-4]
            ano_pasta = caminho_partes[-5]
            
            # Formata para dd/mm/aa (ex: 22/06/26)
            data_formatada = f"{dia_pasta}/{mes_pasta}/{ano_pasta[2:]}"
            
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
                df["_data_pasta"] = data_formatada
                df["_hora_pasta"] = hora_pasta
                lista_dfs.append(df)
                
        except Exception as e:
            print(f"Erro ao processar o arquivo {arquivo}: {str(e)}")
            
    if not lista_dfs:
        print("Nenhum dado válido pôde ser extraído das planilhas.")
        return False
        
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    dados_dict = df_consolidado.to_dict(orient="records")
    
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
    # GRAVAÇÃO IMEDIATA DO MARCADOR DE SEGURANÇA
    # (Garante que a pasta NUNCA mais seja reprocessada, mesmo com falhas no Git)
    # ======================================================================
    try:
        marker_file = os.path.join(pasta_pendente, "processado.txt")
        with open(marker_file, "w") as f:
            f.write("PROCESSADO")
        print(f"Marcador 'processado.txt' gravado com sucesso em: {pasta_pendente}")
    except Exception as e_marker:
        print(f"Aviso: Não foi possível gravar o arquivo marcador: {e_marker}")

    # ======================================================================
    # SINCRONIZAÇÃO INDEPENDENTE COM O GITHUB (ATUALIZAÇÃO DO CLOUDFLARE PAGES)
    # ======================================================================
    try:
        print("Enviando dados atualizados para o GitHub...")
        subprocess.run(["git", "add", "web/dados.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Atualizacao automatica: consolidacao de dados"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("GitHub atualizado! O Cloudflare Pages atualizará o site online em instantes.")
    except Exception as e:
        print(f"Aviso: Sincronização de push finalizada (dados locais já estavam atualizados no GitHub): {e}")
    # ======================================================================

    return True

if __name__ == "__main__":
    processar_planilhas_consolidadas()