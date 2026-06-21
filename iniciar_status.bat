@echo off
:: Altera a codificação do prompt de comando para UTF-8 (corrige acentuações e ç)
chcp 65001 > nul

echo ======================================================
echo    Iniciando Monitor de Status de Comunicação
echo ======================================================
echo.

:: Navega até a pasta do projeto
cd /d "C:\Projetos em Python\Status de Comunicação"

:: Executa o orquestrador principal
python main.py

pause