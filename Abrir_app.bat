@echo off
echo Iniciando o Dashboard Financeiro...
echo.

:: O comando "python -m" garante que o Streamlit seja executado
:: usando o interpretador Python correto.
python -m streamlit run App_controle_pessoal.py

echo.
echo Dashboard encerrado. Pressione qualquer tecla para fechar esta janela.
pause > nul