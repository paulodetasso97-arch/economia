import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import date
import logging

# Configuração de logging para o terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. FUNÇÃO DE CARREGAMENTO E PROCESSAMENTO DE DADOS ---
def load_and_process_data():
    """
    Lê todos os arquivos CSV e XLSX nas subpastas,
    padroniza as colunas e combina os dados.
    """
    
    all_dataframes = []
    
    # Dicionário de mapeamento para padronizar nomes de colunas
    col_mapping = {
        'data': 'Data',
        'Data': 'Data',
        'date': 'Data',
        'valor': 'Valor',
        'Valor': 'Valor',
        'amount': 'Valor',
        'descri\xc3\xa7\xc3\xa3o': 'Descricao',
        'DescriÃ§Ã£o': 'Descricao',
        'descrição': 'Descricao',
        'descriçao': 'Descricao',
        'title': 'Descricao',
        'description': 'Descricao'
    }

    # Procura por subpastas com os nomes 'extrato' ou 'fatura'
    found_folders = []
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            dir_lower = d.lower()
            if 'extrato' in dir_lower or 'fatura' in dir_lower:
                found_folders.append(d)

    if not found_folders:
        st.error("Nenhuma pasta chamada 'extrato' ou 'fatura' foi encontrada.")
        st.stop()
        
    for folder_path in found_folders:
        all_files = [f for f in os.listdir(folder_path) if f.endswith('.csv') or f.endswith('.xlsx')]
        
        if not all_files:
            st.warning(f"Nenhum arquivo CSV ou XLSX encontrado na pasta '{folder_path}'.")
            continue

        for file in all_files:
            file_path = os.path.join(folder_path, file)
            df = None
            
            logging.info(f"Tentando ler o arquivo: {file_path}")
            
            # Tenta ler com base na extensão do arquivo e codificação/delimitador
            try:
                if file.endswith('.csv'):
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8', delimiter=',')
                    except:
                        df = pd.read_csv(file_path, encoding='ISO-8859-1', delimiter=';')
                elif file.endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                
                if df is None or df.empty:
                    logging.warning(f"O arquivo {file} foi lido, mas está vazio ou em um formato desconhecido.")
                    continue

                # Normaliza e padroniza os nomes das colunas
                original_cols = df.columns
                df.columns = df.columns.str.strip().str.lower()
                df = df.rename(columns=col_mapping)
                
                # Verifica se as colunas essenciais foram encontradas
                if 'Data' in df.columns and 'Valor' in df.columns:
                    # Garante que a coluna 'Descricao' exista
                    if 'Descricao' not in df.columns:
                        df['Descricao'] = 'N/A'
                    
                    df_standardized = df[['Data', 'Valor', 'Descricao']]
                    all_dataframes.append(df_standardized)
                    logging.info(f"Arquivo {file} lido com sucesso.")
                else:
                    logging.warning(f"O arquivo '{file}' foi ignorado. Colunas necessárias ('Data' e 'Valor') não encontradas. Colunas encontradas: {list(original_cols)}")
            
            except Exception as e:
                logging.error(f"Erro ao ler o arquivo {file_path}: {e}")

    if not all_dataframes:
        st.error("Nenhum dado válido foi carregado. Verifique os arquivos nas pastas.")
        st.stop()

    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Usa 'infer_datetime_format=True' para tentar detectar automaticamente o formato
    final_df = combined_df.copy()
    final_df['Data'] = pd.to_datetime(final_df['Data'], errors='coerce', dayfirst=True, infer_datetime_format=True)
    final_df = final_df.dropna(subset=['Data'])
    
    # Remove a informação de fuso horário, se existir
    final_df['Data'] = final_df['Data'].dt.tz_localize(None)

    final_df['Tipo_Transacao'] = 'Movimentação'
    final_df['Categoria'] = 'N/A'
    
    return final_df.sort_values(by='Data', ascending=False)

# --- FUNÇÕES DE NARRATIVA E ANÁLISE ---
def generate_narrative(df):
    """Gera uma narrativa baseada nos dados do dashboard."""
    total_spent = abs(df[df['Valor'] < 0]['Valor'].sum())
    total_received = df[df['Valor'] > 0]['Valor'].sum()
    net_flow = total_received - total_spent
    
    if total_spent == 0:
        return "Nenhum gasto registrado no período selecionado. Excelente controle financeiro!"

    narrative = f"### Análise Rápida da sua IA Financeira \n\n"
    narrative += f"**Visão Geral:** No período selecionado, você gastou R$ {total_spent:,.2f} e recebeu R$ {total_received:,.2f}, resultando em um saldo líquido de **R$ {net_flow:,.2f}**.\n\n"
    
    # Análise de Top Gastos
    top_establishments = df[df['Valor'] < 0].groupby('Descricao')['Valor'].sum().nsmallest(3).index.tolist()
    
    # Verifica o número de estabelecimentos antes de exibi-los
    if len(top_establishments) == 1:
        narrative += f"**Principal Gasto:** O seu maior gasto foi com **{top_establishments[0]}**. Fique de olho neste estabelecimento para otimizar seus gastos. \n\n"
    elif len(top_establishments) == 2:
        narrative += f"**Principais Gastos:** Os seus maiores gastos foram com **{top_establishments[0]}** e **{top_establishments[1]}**. Fique de olho nestes estabelecimentos para otimizar seus gastos. \n\n"
    elif len(top_establishments) >= 3:
        narrative += f"**Principais Gastos:** Os seus maiores gastos foram com **{top_establishments[0]}**, **{top_establishments[1]}** e **{top_establishments[2]}**. Fique de olho nestes estabelecimentos para otimizar seus gastos. \n\n"
    else:
        narrative += "**Principais Gastos:** Não há gastos suficientes para exibir uma análise detalhada. \n\n"

    # Sugestões
    if net_flow < 0:
        narrative += "**Recomendação:** Seu saldo líquido está negativo. Tente revisar os gastos nos estabelecimentos principais para encontrar oportunidades de economia."
    else:
        narrative += "**Recomendação:** Seu saldo líquido está positivo! Ótimo trabalho controlando suas finanças. Continue assim para alcançar seus objetivos financeiros."
    
    return narrative

# --- FUNÇÕES DE CRIAÇÃO DE GRÁFICOS ---
def create_total_by_month_plot(df):
    """Cria um gráfico de barras dos gastos totais por mês."""
    df_filtered = df[df['Valor'] < 0].copy()
    if df_filtered.empty:
        return go.Figure().update_layout(title="Sem dados de gastos para o período")
    df_filtered['Mes'] = df_filtered['Data'].dt.to_period('M').astype(str)
    monthly_spends = df_filtered.groupby('Mes')['Valor'].sum().reset_index()
    monthly_spends['Valor'] = monthly_spends['Valor'].abs()
    fig = px.bar(monthly_spends, x='Mes', y='Valor', 
                 title='Gastos Totais por Mês', 
                 labels={'Valor': 'Valor (R$)', 'Mes': 'Mês'},
                 text='Valor')
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    return fig

def create_top_establishments_plot(df):
    """Cria um gráfico de barras dos top 10 estabelecimentos."""
    df_filtered = df[df['Valor'] < 0].copy()
    if df_filtered.empty:
        return go.Figure().update_layout(title="Sem dados de gastos para o período")
    top_establishments = df_filtered.groupby('Descricao')['Valor'].sum().nsmallest(10).reset_index()
    top_establishments['Valor'] = top_establishments['Valor'].abs()
    fig = px.bar(top_establishments, x='Valor', y='Descricao', 
                 title='Top 10 Estabelecimentos de Gastos', 
                 orientation='h', 
                 labels={'Valor': 'Valor (R$)', 'Descricao': 'Estabelecimento'})
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    return fig

def create_ranking_by_description(df):
    """Cria um ranking de gastos por descrição."""
    df_filtered = df[df['Valor'] < 0].copy()
    if df_filtered.empty:
        return pd.DataFrame({'Estabelecimento': ['N/A'], 'Valor': [0]})

    ranking = df_filtered.groupby('Descricao')['Valor'].sum().reset_index()
    ranking['Valor'] = ranking['Valor'].abs()
    ranking = ranking.sort_values(by='Valor', ascending=False)
    ranking.columns = ['Estabelecimento', 'Valor (R$)']
    return ranking.reset_index(drop=True)


def create_category_distribution_plot(df):
    """Cria um gráfico de pizza da distribuição de gastos por categoria."""
    df_filtered = df[(df['Valor'] < 0) & (df['Tipo_Transacao'] != 'Pagamento')].copy()
    if df_filtered.empty:
        return go.Figure().update_layout(title="Sem dados de gastos para o período")
    category_spends = df_filtered.groupby('Categoria')['Valor'].sum().reset_index()
    category_spends['Valor'] = category_spends['Valor'].abs()
    fig = px.pie(category_spends, values='Valor', names='Categoria', 
                 title='Distribuição de Gastos por Categoria')
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_flow_plot(df):
    """Cria um gráfico de linhas do fluxo de entrada e saída."""
    df_filtered = df.copy()
    if df_filtered.empty:
        return go.Figure().update_layout(title="Sem dados de fluxo para o período")
    df_filtered['Data'] = df_filtered['Data'].dt.date
    daily_flow = df_filtered.groupby('Data')['Valor'].sum().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_flow['Data'], y=daily_flow['Valor'],
                             mode='lines+markers', name='Fluxo Financeiro'))
    
    fig.update_layout(title='Fluxo de Entrada e Saída (Diário)',
                      xaxis_title='Data',
                      yaxis_title='Valor (R$)'),
    return fig

# --- 3. FUNÇÃO PRINCIPAL DO DASHBOARD STREAMLIT ---
def main():
    st.set_page_config(layout="wide", page_title="Dashboard Financeiro Nubank")

    # CSS para barra superior fixa, cartões animados e botões
    st.markdown("""
        <style>
        /* Barra superior fixa */
        .top-bar {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            background: #5d2054;
            color: #fff;
            z-index: 1000;
            padding: 18px 0 12px 0;
            box-shadow: 0 2px 8px 0 rgba(93,32,84,0.10);
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .top-bar form {
            display: flex;
            gap: 24px;
            align-items: center;
        }
        .top-bar label {
            font-weight: 600;
            margin-right: 6px;
        }
        .stApp {
            padding-top: 90px !important;
        }
        .kpi-card {
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px 0 rgba(93,32,84,0.10);
            padding: 24px;
            margin-bottom: 16px;
            transition: transform 0.2s;
        }
        .kpi-card:hover {
            transform: scale(1.03);
            box-shadow: 0 8px 32px 0 rgba(93,32,84,0.15);
        }
        .kpi-green {
            color: #2ecc40;
            font-weight: bold;
            font-size: 1.5em;
        }
        .kpi-red {
            color: #e74c3c;
            font-weight: bold;
            font-size: 1.5em;
        }
        .kpi-label {
            color: #5d2054;
            font-size: 1em;
            font-weight: 600;
        }
        .stButton>button {
            color: #fff;
            background: #5d2054;
            border-radius: 8px;
            transition: background 0.2s, transform 0.2s;
        }
        .stButton>button:hover {
            background: #a8327e;
            transform: scale(1.05);
        }
        </style>
    """, unsafe_allow_html=True)

    df = load_and_process_data()

    # ----------- BARRA SUPERIOR FIXA COM FILTROS -----------
    min_date = df['Data'].min().date()
    max_date = df['Data'].max().date()

    # Usando o container para simular barra superior fixa
    with st.container():
        st.markdown(
            f"""
            <div class="top-bar">
                <form>
                    <label>Data de início:</label>
                    <input type="date" id="start_date" name="start_date" min="{min_date}" max="{max_date}" value="{min_date}">
                    <label>Data de fim:</label>
                    <input type="date" id="end_date" name="end_date" min="{min_date}" max="{max_date}" value="{max_date}">
                </form>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Filtros interativos (abaixo da barra superior)
    col_f1, col_f2, col_f3, col_f4 = st.columns([2,2,3,3])
    with col_f1:
        start_date = st.date_input("Data de início", min_value=min_date, max_value=max_date, value=min_date, key="start_date_input")
    with col_f2:
        end_date = st.date_input("Data de fim", min_value=min_date, max_value=max_date, value=max_date, key="end_date_input")
    with col_f3:
        transaction_types = ['Todos'] + sorted(list(df['Tipo_Transacao'].unique()))
        selected_type = st.selectbox("Tipo de Transação", transaction_types, key="tipo_transacao")
    with col_f4:
        establishments = ['Todos'] + sorted(list(df['Descricao'].unique()))
        selected_establishment = st.selectbox("Estabelecimento", establishments, key="estabelecimento")

    # Validação de datas
    if start_date > end_date:
        st.warning("A data de início não pode ser maior que a data de fim.")
        df_filtered = df.copy()
    else:
        df_filtered = df[(df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)]

    # Remove transações de valor zero
    df_filtered = df_filtered[df_filtered['Valor'] != 0]

    if selected_type != 'Todos':
        df_filtered = df_filtered[df_filtered['Tipo_Transacao'] == selected_type]
    if selected_establishment != 'Todos':
        df_filtered = df_filtered[df_filtered['Descricao'] == selected_establishment]

    min_val, max_val = float(df['Valor'].min()), float(df['Valor'].max())
    val_range = st.slider(
        "Faixa de Valor (R$)",
        min_val, max_val,
        (min_val, max_val),
        key="valor_slider"
    )
    df_filtered = df_filtered[(df_filtered['Valor'] >= val_range[0]) & (df_filtered['Valor'] <= val_range[1])]

    # ------------------ KPIs EM CARTÕES ANIMADOS ------------------
    st.title("💸 Dashboard Financeiro Nubank")
    st.markdown("Análise das suas transações em um só lugar.")

    st.markdown("---")
    st.subheader("Resumo das Transações")

    total_spent = df_filtered[df_filtered['Valor'] < 0]['Valor'].sum()
    total_received = df_filtered[df_filtered['Valor'] > 0]['Valor'].sum()
    avg_spent = df_filtered[df_filtered['Valor'] < 0]['Valor'].mean()
    num_transactions = df_filtered.shape[0]
    saldo_liquido = total_received + total_spent

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Gasto</div>
            <div class="kpi-red">R$ {abs(total_spent):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Recebido</div>
            <div class="kpi-green">R$ {total_received:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Valor Médio Gasto</div>
            <div class="kpi-red">R$ {abs(avg_spent):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Nº de Transações</div>
            <div class="kpi-green">{num_transactions}</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        cor = "kpi-green" if saldo_liquido >= 0 else "kpi-red"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Saldo Líquido</div>
            <div class="{cor}">R$ {saldo_liquido:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Botão animado para exportar dados filtrados
    st.markdown("---")
    st.markdown("### Exportar Dados")
    st.download_button("Exportar para CSV", df_filtered.to_csv(index=False).encode('utf-8'), "dados_filtrados.csv", "text/csv")

    # Análise Narrativa da IA
    st.markdown("---")
    st.markdown(generate_narrative(df_filtered))

    # ------------------ MAIS ANÁLISES E EFEITOS ------------------
    st.markdown("---")
    st.subheader("Análises Gráficas e Detalhadas")

    colg1, colg2 = st.columns(2)
    with colg1:
        st.plotly_chart(create_total_by_month_plot(df_filtered), use_container_width=True, key="total_plot")
    with colg2:
        st.plotly_chart(create_top_establishments_plot(df_filtered), use_container_width=True, key="establishments_plot")

    st.markdown("### Ranking de Gastos por Estabelecimento")
    st.dataframe(create_ranking_by_description(df_filtered), use_container_width=True)

    colg3, colg4 = st.columns(2)
    with colg3:
        st.plotly_chart(create_category_distribution_plot(df_filtered), use_container_width=True, key="category_plot")
    with colg4:
        st.plotly_chart(create_flow_plot(df_filtered), use_container_width=True, key="flow_plot")

    # NOVA ANÁLISE: Evolução do saldo acumulado
    st.markdown("### Evolução do Saldo Acumulado")
    saldo_acumulado = df_filtered.sort_values('Data').copy()
    saldo_acumulado['Saldo Acumulado'] = saldo_acumulado['Valor'].cumsum()
    fig_saldo = px.line(saldo_acumulado, x='Data', y='Saldo Acumulado', title='Saldo Acumulado ao Longo do Tempo')
    st.plotly_chart(fig_saldo, use_container_width=True)

    # NOVA ANÁLISE: Distribuição dos valores das transações
    st.markdown("### Distribuição dos Valores das Transações")
    fig_hist = px.histogram(df_filtered, x='Valor', nbins=30, title='Distribuição dos Valores das Transações')
    st.plotly_chart(fig_hist, use_container_width=True)

    # ------------------ TABELA DINÂMICA ------------------
    st.markdown("---")
    st.subheader("Detalhes das Transações")
    st.dataframe(df_filtered.sort_values(by='Data', ascending=False), use_container_width=True)

if __name__ == '__main__':
    main()
