import os
import glob
import pandas as pd
import json
import shutil
import subprocess
from datetime import datetime

def processar_planilhas_consolidadas():
    # Caminho do OneDrive corporativo conforme solicitado
    base_onedrive = r"C:\Users\cristian.souza\OneDrive - Nossa Senhora do Ó Participações S.A\Status de Comunicação"
    pasta_web = r"C:\Projetos em Python\Status de Comunicação\web"
    
    # 1. Verifica se já existem os 14 arquivos sincronizados na raiz do OneDrive pelo Power Automate
    arquivos_novos = glob.glob(os.path.join(base_onedrive, "*.xls*"))
    
    if len(arquivos_novos) < 14:
        # Se houver menos de 14 arquivos, aguarda o Power Automate terminar
        return False
        
    print(f"\nSincronização detectada! {len(arquivos_novos)} arquivos carregados na raiz do OneDrive pelo Power Automate.")
    
    # 2. Cria a estrutura cronológica para organizar e arquivar os arquivos brutos
    agora = datetime.now()
    ano = agora.strftime("%Y")
    mes = agora.strftime("%m-%Y")
    dia = agora.strftime("%d-%m-%y")
    hora = agora.strftime("%Hh")
    
    pasta_arquivamento = os.path.join(base_onedrive, ano, mes, dia, hora)
    os.makedirs(pasta_arquivamento, exist_ok=True)
    
    # 3. Move os arquivos novos da raiz para a pasta cronológica para limpar a raiz do OneDrive
    for arquivo in arquivos_novos:
        nome_arquivo = os.path.basename(arquivo)
        destino = os.path.join(pasta_arquivamento, nome_arquivo)
        shutil.move(arquivo, destino)
        
    print(f"Arquivos consolidados movidos e organizados em: {pasta_arquivamento}")
    
    # 4. Faz a consolidação acumulada de todos os arquivos históricos do mês atual
    pasta_mes_atual = os.path.join(base_onedrive, ano, mes)
    todos_arquivos = glob.glob(os.path.join(pasta_mes_atual, "**", "*.xls*"), recursive=True)
    
    # Filtro rigoroso de segurança de caminhos
    arquivos_historicos = []
    for f in todos_arquivos:
        pasta_pai = os.path.basename(os.path.dirname(f))
        pasta_avo = os.path.basename(os.path.dirname(os.path.dirname(f)))
        if pasta_pai.endswith("h") and pasta_pai[:-1].isdigit() and "-" in pasta_avo:
            arquivos_historicos.append(f)
            
    if not arquivos_historicos:
        print("Nenhum arquivo histórico foi localizado no diretório do mês atual.")
        return False
        
    print(f"Consolidando histórico completo do mês ({len(arquivos_historicos)} planilhas)...")
    lista_dfs = []
    
    for arquivo in arquivos_historicos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            nome_pasta_hora = os.path.basename(os.path.dirname(arquivo))
            nome_pasta_dia = os.path.basename(os.path.dirname(os.path.dirname(arquivo)))
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
                df["_data_pasta"] = data_formatada
                df["_hora_pasta"] = nome_pasta_hora
                lista_dfs.append(df)
                
        except Exception as e:
            print(f"Erro ao processar o arquivo {arquivo}: {str(e)}")
            
    if not lista_dfs:
        print("Nenhum dado válido pôde ser extraído das planilhas.")
        return False
        
    # Consolida os dados em um único DataFrame
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
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

    # 5. Sincronização automática com o GitHub (Netlify/Cloudflare)
    try:
        print("Enviando dados atualizados para o GitHub...")
        subprocess.run(["git", "add", "web/dados.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Atualizacao automatica: consolidacao mensal"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("GitHub atualizado! O Cloudflare Pages atualizará o site online em instantes.")
    except Exception as e:
        print(f"Não foi possível fazer o push automático para o GitHub: {e}")
        
    return True