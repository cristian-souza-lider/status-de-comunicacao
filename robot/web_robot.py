import os
import re
import time
import glob
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

def limpar_nome_arquivo(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()

def obter_caminho_onedrive():
    base_onedrive = r"C:\Users\cristian.souza\OneDrive - Nossa Senhora do Ó Participações S.A\Status de Comunicação"
    agora = datetime.now()
    ano = agora.strftime("%Y")
    mes = agora.strftime("%m-%Y")
    dia = agora.strftime("%d-%m-%y")
    hora = agora.strftime("%Hh")
    return os.path.join(base_onedrive, ano, mes, dia, hora)

def clicar_com_seguranca(driver, elemento):
    """Tenta clicar de forma padrão; caso falhe por sobreposição, força via JavaScript."""
    try:
        elemento.click()
    except Exception:
        driver.execute_script("arguments[0].click();", elemento)

def aguardar_e_mover_download(temp_dir, pasta_destino, novo_nome):
    """Monitora a pasta temporária a cada 0.5 segundos e move o arquivo assim que qualquer download terminar."""
    timeout = 45
    intervalo = 0.5
    limite_loops = int(timeout / intervalo)
    
    for _ in range(limite_loops):
        todos_arquivos = glob.glob(os.path.join(temp_dir, "*"))
        
        # Filtra extensões temporárias comuns de download do Chrome/Edge (.crdownload, .tmp)
        downloads_em_andamento = [f for f in todos_arquivos if f.endswith(".crdownload") or f.endswith(".tmp") or f.endswith(".download")]
        arquivos_prontos = [f for f in todos_arquivos if not f.endswith(".crdownload") and not f.endswith(".tmp") and not f.endswith(".download") and os.path.isfile(f)]
        
        # Se não houver downloads incompletos e houver ao menos um arquivo pronto
        if not downloads_em_andamento and arquivos_prontos:
            arquivo_detectado = max(arquivos_prontos, key=os.path.getmtime)
            
            # Detecta e preserva a extensão original exportada pelo site (.xls, .xlsx, etc.)
            _, extensao = os.path.splitext(arquivo_detectado)
            if not extensao:
                extensao = ".xlsx"  # Fallback padrão
                
            os.makedirs(pasta_destino, exist_ok=True)
            caminho_final = os.path.join(pasta_destino, f"{novo_nome}{extensao}")
            
            # Move e renomeia o arquivo
            shutil.move(arquivo_detectado, caminho_final)
            print(f"Download concluído: {novo_nome}{extensao}")
            return True
            
        time.sleep(intervalo)
        
    print(f"Aviso: Tempo limite excedido ao baixar o relatório para {novo_nome}.")
    return False

def executar_loop_empresas(driver, situacao_nome, temp_download_dir):
    select_empresa_element = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_contentFiltroPesquisa_ddlEmpresa"))
    )
    select_empresa = Select(select_empresa_element)
    
    opcoes = []
    for opt in select_empresa.options:
        valor = opt.get_attribute("value")
        texto = opt.text
        if valor and valor != "0":
            opcoes.append((valor, texto))
            
    print(f"Total de empresas para '{situacao_nome}': {len(opcoes)}")
    
    for valor, texto in opcoes:
        nome_empresa_limpo = limpar_nome_arquivo(texto)
        print(f"\n--- Processando: {texto} ({situacao_nome}) ---")
        
        try:
            # 1. Seleciona a empresa
            select_emp_dinamico = Select(WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_contentFiltroPesquisa_ddlEmpresa"))
            ))
            select_emp_dinamico.select_by_value(valor)
            time.sleep(2)  # Aguarda o postback de seleção da empresa se estabilizar
            
            # 2. Clica em Pesquisar
            btn_pesquisar = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//p[contains(@class, 'iconePesquisar') and text()='Pesquisar']"))
            )
            clicar_com_seguranca(driver, btn_pesquisar)
            
            # Pausa para que a página/grid termine de carregar as novas informações
            print("Aguardando carregamento da página...")
            time.sleep(3.5)
            
            # 3. Localiza e clica no botão de exportação (Excel) se houver dados
            try:
                btn_excel = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[src*="icon-doc-excel.gif"]'))
                )
                # Garante visibilidade física na tela
                WebDriverWait(driver, 5).until(EC.visibility_of(btn_excel))
                
                clicar_com_seguranca(driver, btn_excel)
                print("Exportação iniciada. Monitorando download...")
                
                # 4. Monitoramento ativo até concluir o download completo
                pasta_destino = obter_caminho_onedrive()
                nome_final_arquivo = f"{nome_empresa_limpo} - {situacao_nome}"
                aguardar_e_mover_download(temp_download_dir, pasta_destino, nome_final_arquivo)
                
            except TimeoutException:
                # Verificação extra rápida para casos de lentidão do servidor
                time.sleep(1.5)
                botoes = driver.find_elements(By.CSS_SELECTOR, 'input[src*="icon-doc-excel.gif"]')
                if botoes:
                    clicar_com_seguranca(driver, botoes[0])
                    print("Exportação iniciada (atrasada). Monitorando download...")
                    pasta_destino = obter_caminho_onedrive()
                    nome_final_arquivo = f"{nome_empresa_limpo} - {situacao_nome}"
                    aguardar_e_mover_download(temp_download_dir, pasta_destino, nome_final_arquivo)
                else:
                    print("Nenhum dado encontrado para esta pesquisa.")
                    
        except Exception as e:
            print(f"Erro inesperado durante o processamento da empresa {texto}: {str(e)}")
            
        # 5. Intervalo obrigatório de 5 segundos entre a conclusão de uma empresa e o início da próxima
        print("Aguardando 5 segundos para descompressão antes do próximo registro...")
        time.sleep(5)

def executar_robot():
    temp_download_dir = os.path.abspath(r"C:\Projetos em Python\Status de Comunicação\temp_downloads")
    
    if os.path.exists(temp_download_dir):
        shutil.rmtree(temp_download_dir)
    os.makedirs(temp_download_dir)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--proxy-server=direct://")
    chrome_options.add_argument("--proxy-bypass-list=*")  
    chrome_options.add_argument("--remote-allow-origins=*")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    try:
        # Abertura do site
        driver.get("https://gool.cittati.com.br/Login.aspx?ReturnUrl=%2f")
        
        # 1º Passo: Clicar no ícone Urbano
        btn_urbano = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "ucTrocarModulo_btnIconeUrbano"))
        )
        time.sleep(1) # Intervalo para o modal de seleção carregar na tela
        clicar_com_seguranca(driver, btn_urbano)
        
        # 2º Passo: Preencher Login (Aguardando Visibilidade real)
        input_login = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "ucLogarUsuario_txtLogin"))
        )
        input_login.clear()
        input_login.send_keys("status.nso")
        
        # 3º Passo: Preencher Senha e pressionar ENTER (Aguardando Visibilidade real)
        input_senha = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "ucLogarUsuario_txtSenha"))
        )
        input_senha.clear()
        input_senha.send_keys("@Cmi123")
        time.sleep(0.5)
        input_senha.send_keys(Keys.ENTER)
        
        # 4º Passo: Clicar no menu Status de Comunicação
        btn_menu = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//span[@title="Status de Comunicação"]'))
        )
        clicar_com_seguranca(driver, btn_menu)
        
        # Primeiro Loop: Operando
        executar_loop_empresas(driver, "Operando", temp_download_dir)
        
        # Configuração para o segundo Loop
        print("\nAlterando situação para 'Em Manutenção'...")
        select_situacao_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_contentFiltroPesquisa_ddlSituacaoVeiculo"))
        )
        select_situacao = Select(select_situacao_element)
        select_situacao.select_by_value("M")
        time.sleep(2)
        
        # Segundo Loop: Em Manutenção
        executar_loop_empresas(driver, "Em Manutenção", temp_download_dir)
        
        print("\nEfetuando logoff...")
        btn_logoff = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "Img2"))
        )
        clicar_com_seguranca(driver, btn_logoff)
        time.sleep(1.5)

    except Exception as e:
        print(f"Erro na execução do robô: {str(e)}")
        
    finally:
        driver.quit()
        if os.path.exists(temp_download_dir):
            try:
                shutil.rmtree(temp_download_dir)
            except Exception:
                pass

if __name__ == "__main__":
    executar_robot()