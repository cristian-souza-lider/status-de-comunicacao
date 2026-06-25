import os
import glob
import pandas as pd
import json
import subprocess
from datetime import datetime, timedelta

def processar_planilhas_consolidadas():
    # Caminho do OneDrive corporativo e diretório web
    base_onedrive = r"C:\Users\cristian.souza\OneDrive - Nossa Senhora do Ó Participações S.A\Status de Comunicação"
    pasta_web = r"C:\Projetos em Python\Status de Comunicação\web"
    
    pasta_pendente = None
    agora = datetime.now()
    
    # Varre o mês atual e o mês anterior para garantir transições de data sem perda de histórico
    meses_para_varrer = [agora, agora - timedelta(days=15)]
    subpastas_hora = []
    
    for dt_referencia in meses_para_varrer:
        ano = dt_referencia.strftime("%Y")
        mes = dt_referencia.strftime("%m")
        pasta_mes = os.path.join(base_onedrive, ano, mes)
        
        if os.path.exists(pasta_mes):
            encontradas = glob.glob(os.path.join(pasta_mes, "*", "*h"))
            subpastas_hora.extend(encontradas)
            
    # Identifica a primeira pasta pendente com arquivos de integração
    for pasta in subpastas_hora:
        nome_pasta = os.path.basename(pasta)
        if nome_pasta[:-1].isdigit():
            marcador = os.path.join(pasta, "processado.txt")
            if not os.path.exists(marcador):
                arquivos_na_pasta = glob.glob(os.path.join(pasta, "*.xls*"))
                if len(arquivos_na_pasta) >= 1:
                    pasta_pendente = pasta
                    break
                        
    if not pasta_pendente:
        return False
        
    print(f"\nSincronização pendente detectada na pasta: {pasta_pendente}")
    
    # Coleta de todos os arquivos do histórico recente dos meses ativos
    todos_arquivos = []
    for dt_referencia in meses_para_varrer:
        ano = dt_referencia.strftime("%Y")
        mes = dt_referencia.strftime("%m")
        pasta_mes = os.path.join(base_onedrive, ano, mes)
        if os.path.exists(pasta_mes):
            encontrados = glob.glob(os.path.join(pasta_mes, "**", "*.xls*"), recursive=True)
            todos_arquivos.extend(encontrados)
    
    arquivos_historicos = []
    for f in todos_arquivos:
        pasta_pai = os.path.basename(os.path.dirname(f))
        pasta_avo = os.path.basename(os.path.dirname(os.path.dirname(f)))
        if pasta_pai.endswith("h") and pasta_pai[:-1].isdigit() and pasta_avo.isdigit():
            arquivos_historicos.append(f)
            
    if not arquivos_historicos:
        print("Nenhum arquivo histórico foi localizado nos diretórios ativos.")
        return False
        
    print(f"Consolidando histórico acumulado de {len(arquivos_historicos)} planilhas...")
    lista_dfs = []
    
    for arquivo in arquivos_historicos:
        try:
            nome_arquivo = os.path.basename(arquivo)
            caminho_partes = arquivo.split(os.sep)
            
            hora_pasta = caminho_partes[-2]
            dia_pasta = caminho_partes[-3]
            mes_pasta = caminho_partes[-4]
            ano_pasta = caminho_partes[-5]
            
            ano_curto = ano_pasta[2:] if len(ano_pasta) >= 4 else ano_pasta
            data_formatada = f"{dia_pasta}/{mes_pasta}/{ano_curto}"
            
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
    
    # --- OTIMIZAÇÃO 1: Remoção de duplicidades redundantes ---
    subset_duplicados = [col for col in ["Prefixo", "_data_pasta", "_hora_pasta"] if col in df_consolidado.columns]
    if subset_duplicados:
        df_consolidado = df_consolidado.drop_duplicates(subset=subset_duplicados)
    
    # Seleciona apenas as colunas consumidas pelo app.js
    colunas_essenciais = [
        "Empresa", "Linha", "Prefixo", "Situação", "Fab", "Status", 
        "Não Conformidade", "Status GPS", "Estado Validador", 
        "Hora estado validador", "Última Transmissão", "Último GPS",
        "_data_pasta", "_hora_pasta"
    ]
    
    colunas_presentes = [col for col in colunas_essenciais if col in df_consolidado.columns]
    df_consolidado = df_consolidado[colunas_presentes]
    
    dados_totais = df_consolidado.to_dict(orient="records")
    
    # --- OTIMIZAÇÃO 2: Determinação dinâmica da data limite (Últimos 3 Dias com base nos dados) ---
    datas_encontradas = []
    for registro in dados_totais:
        data_str = registro.get("_data_pasta")
        if data_str:
            try:
                partes = data_str.split("/")
                dia_reg = int(partes[0])
                mes_reg = int(partes[1])
                ano_reg = int(partes[2])
                if ano_reg < 100:
                    ano_reg += 2000
                datas_encontradas.append(datetime(ano_reg, mes_reg, dia_reg))
            except Exception:
                continue
                
    max_data = max(datas_encontradas) if datas_encontradas else agora
    limite_data = max_data - timedelta(days=3)
    print(f"Filtrando dados a partir de: {limite_data.strftime('%d/%m/%Y')} (Referência mais recente: {max_data.strftime('%d/%m/%Y')})")
    
    dados_filtrados = []
    for registro in dados_totais:
        data_str = registro.get("_data_pasta")
        if data_str:
            try:
                partes = data_str.split("/")
                dia_reg = int(partes[0])
                mes_reg = int(partes[1])
                ano_reg = int(partes[2])
                
                if ano_reg < 100:
                    ano_reg += 2000
                    
                dt_registro = datetime(ano_reg, mes_reg, dia_reg)
                
                if dt_registro >= limite_data:
                    for chave, valor in registro.items():
                        if pd.isna(valor):
                            registro[chave] = None
                    dados_filtrados.append(registro)
            except Exception:
                continue
                
    os.makedirs(pasta_web, exist_ok=True)
    caminho_json = os.path.join(pasta_web, "dados.json")
    
    # Salva o JSON minificado (sem identação/espaços em branco)
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(dados_filtrados, f, ensure_ascii=False, separators=(',', ':'))
        
    print(f"Consolidação concluída. {len(dados_filtrados)} registros dos últimos 3 dias salvos em: {caminho_json}")

    # Gravação do arquivo marcador
    try:
        marker_file = os.path.join(pasta_pendente, "processado.txt")
        with open(marker_file, "w") as f:
            f.write("PROCESSADO")
        print(f"Marcador 'processado.txt' gravado com sucesso em: {pasta_pendente}")
    except Exception as e_marker:
        print(f"Aviso: Não foi possível gravar o arquivo marcador: {e_marker}")

    # Pipeline de deploy automático com validação de status
    try:
        print("Verificando alterações no repositório local...")
        resultado_status = subprocess.run(
            ["git", "status", "--porcelain", "web/dados.json"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        if resultado_status.stdout.strip():
            print("Alterações detectadas. Enviando dados atualizados para o GitHub...")
            subprocess.run(["git", "add", "web/dados.json"], check=True)
            subprocess.run(["git", "commit", "-m", "Atualizacao automatica: consolidacao de dados"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("GitHub atualizado com sucesso!")
        else:
            print("Nenhuma modificação nos dados consolidados. Upload ignorado.")
            
    except subprocess.CalledProcessError as e_git:
        print(f"Aviso: Ocorreu uma inconformidade durante comandos do Git: {e_git}")
    except Exception as e_geral:
        print(f"Aviso: Falha geral na execução do pipeline de sincronização remota: {e_geral}")

    return True

if __name__ == "__main__":
    processar_planilhas_consolidadas()