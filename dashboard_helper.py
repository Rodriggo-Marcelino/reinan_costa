import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import captacao_e_geracao_dados as dados

# ============================
# 5. Métodos para Geração de Gráficos
# ============================
# ----------------------------
# 5.1 - Funções BASE para COMPONENTES DE LAYOUT
# ----------------------------

def card_compacto(label, valor,
                  unidade="", prefixo="",
                  cor_texto="#FFFFFF", cor_fundo=None,
                  cor_borda=None):
    # Formatação personalizada do valor
    try:
        valor_float = float(valor)
        parte_inteira, parte_decimal = f"{valor_float:,.2f}".split(".")
        parte_inteira_br = parte_inteira.replace(",", ".")  # Formata milhares com pontos
        valor_formatado = f"{parte_inteira_br},{parte_decimal}"
    except:
        valor_formatado = str(valor)
    
    # Estilos dinâmicos
    style_color = f"color: {cor_texto};" if cor_texto else "color: var(--text-color);"
    style_bg = f"background-color: {cor_fundo};" if cor_fundo else "background-color: var(--secondary-background-color);"
    style_border = f"border: 1px solid {cor_borda};" if cor_borda else "border: 1px solid var(--border-color);"

    return f"""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        {style_bg}
        {style_border}
        border-radius: 12px;
        padding: 15px 20px;
        margin: 5px;
        min-width: 140px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
    "
    onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.15)';"
    onmouseout="this.style.transform=''; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)';"
    >
        <div style="font-size: 0.9rem; color: var(--text-secondary-color); margin-bottom: 5px;">{label}</div>
        <div style="font-size: 1.6rem; font-weight: 600; {style_color}">
            {prefixo}{valor_formatado}<span style="font-size: 0.9rem; color: var(--text-secondary-color);">{unidade}</span>
        </div>
    </div>
    """

# ----------------------------
# 5.2 - Funções BASE para tipos de gráfico
# ----------------------------

def plot_pie_base(df, names_col, values_col, title="", **kwargs):
    fig = px.pie(df, names=names_col, values=values_col, title=title, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_bar_base(df, x_col, y_col,
                  title="", labels=None,
                  orientation="v", barmode=None,
                  color_col=None ,**kwargs):
    params = {
        "x": x_col,
        "y": y_col,
        "title": title,
        "labels": labels or {},
        "orientation": orientation,
    }
    if color_col:
        params["color"] = color_col
    if barmode:
        params["barmode"] = barmode
        
    fig = px.bar(df, **params, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_line_base(df, x_col, y_col, title="", labels=None, **kwargs):
    fig = px.line(df, x=x_col, y=y_col, title=title, labels=labels or {}, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_area_base(df, x_col, y_col, title="", labels=None, **kwargs):
    fig = px.area(df, x=x_col, y=y_col, title=title, labels=labels or {}, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_scatter_base(df, x_col, y_col, size_col=None,
                      color_col=None, hover_name=None,
                      hover_data=None, title="",
                      labels=None, **kwargs):
    fig = px.scatter(df, x=x_col, y=y_col,
                    size=size_col, color=color_col,
                    hover_name=hover_name, hover_data=hover_data,
                    title=title, labels=labels or {}, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_funnel_base(df, x_col, y_col, title="", **kwargs):
    fig = px.funnel(df, x=x_col, y=y_col, title=title, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_line_polar_base(df, r_col, theta_col, title="", **kwargs):
    fig = px.line_polar(df, r=r_col, theta=theta_col, line_close=True, title=title, **kwargs)
    st.plotly_chart(fig, use_container_width=True)

def plot_treemap_base(df, path_cols, value_col, title="", **kwargs):
    fig = px.treemap(df, path=path_cols, values=value_col, title=title, **kwargs)
    st.plotly_chart(fig, use_container_width=True)
    
def plot_gauge_base(valor, titulo="Indicador", unidade="", cor_barra="darkblue", faixa=None):
    faixa = faixa or [0, max(10, valor + 1)]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={"text": f"{titulo}"},
        gauge={
            "axis": {"range": faixa},
            "bar": {"color": cor_barra}
        },
        number={"suffix": f" {unidade}" if unidade else ""}
    ))
    st.plotly_chart(fig, use_container_width=True)

def plot_gauge_indicador_base(valor, titulo="Indicador", unidade="", cor_barra="darkblue", faixa=None, fator_ampliacao=1.5):
    """
    Cria um gauge plot com range automático baseado no valor.
    
    Parâmetros:
    valor (float): Valor a ser exibido no gauge
    titulo (str): Título do gráfico
    unidade (str): Unidade de medida (ex: "R$", "%")
    cor_barra (str): Cor da barra do gauge
    faixa (list): Range manual [min, max] (opcional)
    fator_ampliacao (float): Fator para cálculo automático do range superior (valor * fator)
    """
    
    # Calcula o range automático se não for fornecido
    if faixa is None:
        faixa_superior = max(valor * fator_ampliacao, 10)  # Garante um mínimo de 10 para evitar ranges muito pequenos
        faixa = [0, faixa_superior]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={
            "text": f"{titulo}",
            "font": {"size": 16}  # Tamanho de fonte personalizável
        },
        gauge={
            "axis": {"range": faixa},
            "bar": {"color": cor_barra},
            "steps": [
                {"range": [0, faixa[1]*0.5], "color": "lightgray"},
                {"range": [faixa[1]*0.5, faixa[1]*0.8], "color": "gray"},
                {"range": [faixa[1]*0.8, faixa[1]], "color": "darkgray"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": faixa[1]*0.9
            }
        },
        number={
            "suffix": f" {unidade}",
            "font": {"size": 24},
            "valueformat": ".2f"  # Mostra 2 casas decimais
        }
    ))
    
    # Ajustes de layout responsivo
    fig.update_layout(
        margin=dict(t=50, b=10),  # Margens superior/inferior
        height=300  # Altura fixa para melhor responsividade
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
# ============================
# 5.3 - Funções Específicas para Relatórios
# ============================

# BAR ------------------------------------------

def plot_bar_composicao_fretes(df):
    df_plot = df[["frete_ida", "frete_volta", "frete_extra"]].sum().reset_index()
    df_plot.columns = ["tipo", "valor"]
    plot_bar_base(df_plot, x_col="tipo", y_col="valor", title="Composição de Fretes", labels={"tipo":"Tipo de Frete","valor":"Valor (R$)"})

def plot_bar_capex_mensal(df):
    plot_bar_base(df, x_col="data", y_col="capex", title="CAPEX Mensal", labels={"data":"Mês","capex":"Valor (R$)"})

def plot_bar_margem_liquida_mensal(df):
    plot_bar_base(df, x_col="data", y_col="margem_lucro_liquido", title="Margem Líquida Mensal", labels={"data":"Mês","margem_lucro_liquido":"Margem"})

def plot_bar_lucro_por_km_veiculo(df):
    plot_bar_base(df, x_col="veiculo", y_col="Lucro/km", title="Lucro por Km Rodado", labels={"veiculo":"Veículo", "Lucro/km":"Lucro por Km"})

def plot_bar_eficiencia_motoristas(df):
    """Plot otimizado com tratamento de valores negativos e formatação monetária"""
    
    # Criar coluna de cor condicional
    df['cor'] = df['eficiencia'].apply(lambda x: '#00C853' if x >= 0 else '#FF1744')
    
    # Ordenar por eficiência
    df = df.sort_values('eficiencia', ascending=True).round(2)
    
    # Formatar valores monetários
    hover_data = {
        'Receita Bruta': ':.2f',
        'Custo Variável': ':.2f', 
        'Custo Fixo': ':.2f',
        'Lucro Líquido': ':.2f',
        'Km Total': ':.0f'
    }
    
    fig = px.bar(
        df,
        x='eficiencia',
        y='motorista',
        orientation='h',
        color='cor',
        color_discrete_map="identity",
        title='Eficiência Operacional por Motorista (R$/km)',
        labels={'eficiencia': 'Lucro Líquido por Km', 'motorista': ''},
        hover_data={
            'eficiencia': ':.2f',
            'receita_bruta': hover_data['Receita Bruta'],
            'custo_variavel': hover_data['Custo Variável'],
            'custo_fixo': hover_data['Custo Fixo'],
            'lucro_liquido': hover_data['Lucro Líquido'],
            'km_total': hover_data['Km Total'],
            'cor': False
        }
    )
    
    # Ajustes finais de layout
    fig.update_layout(
        showlegend=False,
        xaxis_tickprefix='R$ ',
        xaxis_tickformat=',.2f',
        hoverlabel=dict(
            bgcolor="#2A2A2A",
            font_size=14,
            font_family="Arial",
            font_color="white",
            bordercolor="#FFFFFF"
        ),
        margin=dict(l=150, r=20, t=45, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False)
    )
    
    fig.update_traces(
        hovertemplate=(
            "<span style='font-size:16px; color:#00FFAA'><b>%{y}</b></span><br>"
            "----------------------------------------<br>"
            "<span style='color:#7FFFD4'>Eficiência:</span> R$ %{x:.2f}/km<br>"
            "<span style='color:#98FB98'>Receita Bruta:</span> R$ %{customdata[0]:,.2f}<br>"
            "<span style='color:#FFB6C1'>Custo Variável:</span> R$ %{customdata[1]:,.2f}<br>"
            "<span style='color:#FFA07A'>Custo Fixo:</span> R$ %{customdata[2]:,.2f}<br>"
            "<span style='color:#00FF00'>Lucro Líquido:</span> R$ %{customdata[3]:,.2f}<br>"
            "<span style='color:#87CEEB'>KM Total:</span> %{customdata[4]:,.0f}"
        )
    )
    
    # Adicionar linha de referência no zero
    fig.add_vline(
        x=0, 
        line_width=1.5, 
        line_dash="dot", 
        line_color="rgba(255,255,255,0.5)"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_bar_custo_manutencao_por_km(df):
    plot_bar_base(df, x_col="veiculo", y_col="custo_manut_km", title="Custo de Manutenção por Km", labels={"veiculo": "Veículo", "custo_manut_km": "R$/Km"})

def plot_bar_freq_manutencao_por_veiculo(df_viagem, df_fixas):
    df_proc = dados.preparar_df_manutencao_por_veiculo(df_viagem, df_fixas)
    
    cores = {
        "MANUTENCAO":      "#1f77b4",
        "BORRACHARIA":     "#ff7f0e",
        "LAVAGEM":         "#2ca02c",
        "PLANO MANUTENCAO": "#d62728",
        "MECANICO":        "#9467bd",
        "PNEU":            "#8c564b",
        "FILTROS":         "#17becf",  
        "PNEU COBERTO":    "#7f7f7f" 
    }
    
    fig = px.bar(
        df_proc,
        x="veiculo",
        y="qtd_manutencoes",
        color="categoria",
        color_discrete_map=cores,
        title="Frequência de Manutenções por Veículo e Categoria",
        labels={"veiculo": "Veículo", "qtd_manutencoes": "Quantidade"}
    )
    
    fig.update_layout(barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
    
def plot_bar_consumo_km_por_litro(df):
    df_proc = dados.preparar_df_consumo_km_por_litro(df)
    plot_bar_base(df_proc, x_col="veiculo", y_col="km_por_litro", title="Consumo Médio (Km/L) por Veículo", labels={"veiculo": "Veículo", "km_por_litro": "Km/L"})

def plot_bar_custo_combustivel_por_km(df):
    df_proc = dados.preparar_df_custo_combustivel_por_km(df)
    plot_bar_base(df_proc, x_col="veiculo", y_col="custo_comb_km", title="Custo de Combustível por Km", labels={"veiculo": "Veículo", "custo_comb_km": "R$/Km"})

# PIE -------------------------------------
def plot_pie_distribuicao_categorias(df):
    plot_pie_base(df, names_col="categoria", values_col="valor", title="Distribuição de Categorias")
    
# LINE -----------------------------------
def plot_line_faturamento_vs_despesas(df, x_col="data_ida"):
    plot_line_base(df, x_col=x_col, y_col=["frete_ida", "total_despesas_viagem"],
                   title="Faturamento vs Despesas",
                   labels={"value": "Valor (R$)", "variable": "Tipo", x_col: "Data"})
    
def plot_line_polar_lucro_por_veiculo(df):
    plot_line_polar_base(df, r_col="lucro_bruto", theta_col="veiculo", title="Comparação Radial de Lucro")
    
def plot_line_preco_medio_combustivel(df, x_col="data"):
    df_proc = dados.preparar_df_preco_medio_combustivel(df)
    plot_line_base(df_proc, x_col=x_col, y_col="preco_medio_combustivel",
                   title="Preço Médio do Combustível ao Longo do Tempo",
                   labels={x_col: "Data", "preco_medio_combustivel": "R$/Litro"})
    
def plot_line_manutencoes_ao_longo_do_tempo(df_viagem, df_fixas):
    """
    Plota manutenções ao longo do tempo com opção de escala logarítmica.
    """
    df_proc = dados.preparar_df_manutencao_ao_longo_do_tempo(df_viagem, df_fixas)
    
    # Widget para seleção de escala
    usar_log = st.toggle("Usar escala logarítmica (Y)", value=False)
    
    fig = px.line(
        df_proc,
        x="data",
        y="qtd_manutencoes",
        title="Manutenções ao Longo do Tempo",
        labels={"data": "Data", "qtd_manutencoes": "Quantidade"},
        markers=True
    )
    
    if usar_log:
        fig.update_layout(yaxis_type="log", yaxis_title="Quantidade (log)")
        fig.update_yaxes(tickvals=[0, 1, 10, 30], ticktext=["0", "1", "10", "30"])  # Personalize conforme seus dados
    
    st.plotly_chart(fig, use_container_width=True)
    
# Scatter ---------------------------------

def plot_scatter_custo_vs_lucro_motoristas(df):
    plot_scatter_base(
        df,
        x_col="lucro_bruto", 
        y_col="total_despesas_viagem",  
        size_col="km_total",
        color_col="motorista",
        title="Custo vs Lucro por Motorista",
        labels={
            "lucro_bruto":"Lucro (R$)",
            "total_despesas_viagem":"Custos (R$)",
            } 
    )

def plot_scatter_custo_vs_lucro_veiculo(df):
    plot_scatter_base(
        df, 
        x_col="lucro_bruto", 
        y_col="total_despesas_viagem", 
        size_col="km_total",
        color_col="veiculo", 
        hover_name="identificador",
        hover_data=["destinos_ida", "destinos_volta", "destinos_extra"],
        title="Custo vs Lucro por Veículo", 
        labels={
            "lucro_bruto":"Lucro (R$)",
            "total_despesas_viagem":"Custos (R$)",
            "identificador" : "Viagem",
            "destinos_ida": "Saiu de",
            "destinos_volta": "Voltou por",
            "destinos_extra": "Extra (Bode)"
            } 
    )
    
def plot_scatter_custo_manutencao_vs_km(df):
    df_proc = dados.preparar_df_manutencao_vs_km(df)
    plot_scatter_base(
        df_proc,
        x_col="km_total",
        y_col="valor",
        size_col="qtd_manutencoes",
        color_col="veiculo",
        title="Custo de Manutenção vs Km Rodado",
        labels={"km_total": "Km Total", "valor": "Custo (R$)"})

# AREA ----------------------------------------

def plot_area_evolucao_financeira(df, y_cols, x_col="data", stacked=False, **kwargs):
    df = df.sort_values(x_col)

    if stacked:
        # comportamento atual: áreas empilhadas
        fig = px.area(
            df,
            x=x_col,
            y=y_cols,
            title="Evolução Financeira",
            labels={"value": "Valor (R$)", x_col: "Data"},
            **kwargs
        )
    else:
        # áreas independentes (não empilhadas)
        fig = go.Figure()
        for col in y_cols:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[col],
                fill='tozeroy',
                name=col,
                mode='none'  # sem linha, só área
            ))
        fig.update_layout(
            title="Evolução Financeira",
            xaxis_title="Data",
            yaxis_title="Valor (R$)",
            **kwargs
        )

    st.plotly_chart(fig, use_container_width=True)

# TREEMAP ----------------------------------------
def plot_treemap_faturamento_por_veiculo(df):
    plot_treemap_base(df, path_cols=["veiculo"], value_col="frete_ida", title="Participação no Faturamento por Veículo")

# BOX ---------------------------------------------
def plot_box_lucro_motoristas(df):
    fig = px.box(df, y="lucro_bruto", title="Distribuição de Lucratividade")
    st.plotly_chart(fig, use_container_width=True)

# FUNNEL -------------------------------------------
def plot_funnel_ranking_lucro_motoristas(df):
    plot_funnel_base(df, x_col="lucro_bruto", y_col="motorista", title="Ranking de Lucratividade por Motorista")

# GAUGE ------------------------------------------
def plot_gauge_media_consumo_combustivel(valor):
    plot_gauge_base(valor, titulo="Consumo Médio de Combustível (Km/L)", unidade="Km/L", cor_barra="darkblue")

# def plot_gauge_otar(valor):
#     plot_gauge_base(valor, titulo="OTAR (%) - Entregas no Horário", unidade="%", cor_barra="green", faixa=[0, 100])

# def plot_bar_infracoes_por_veiculo(df):
#     plot_bar_base(df, x_col="veiculo", y_col="qtd_infracoes", title="Infrações por Veículo", labels={"veiculo": "Veículo", "qtd_infracoes": "Quantidade de Infrações"})

# def plot_bar_sinistros_por_motorista(df):
#     plot_bar_base(df, x_col="motorista", y_col="qtd_sinistros", title="Sinistros por Motorista", labels={"motorista": "Motorista", "qtd_sinistros": "Quantidade de Sinistros"})
