import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import captacao_e_geracao_dados as cgd
import dashboard_helper as dh
import calculos_e_formulas as calculos
from utils_validacao import checar_anomalias
from utils_comissao import calcular_comissao
import config
import unicodedata

# ─── Configurações de login ───────────────────────────────────
USUARIOS = config.USUARIOS

def normalize_username(u: str) -> str:
    """
    Remove espaços em sobra, acentos e coloca em lowercase.
    Ex: ' João  ' → 'joao'
    """
    s = u or ""
    # separa combinação Unicode (acentos) e remove os diacríticos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # trim e lowercase
    return s.strip().lower()

# Estado inicial
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "erro_login" not in st.session_state:
    st.session_state.erro_login = False  # flag para mensagens de erro

def _autenticar():
    raw_user = st.session_state.user
    pwd      = st.session_state.pwd

    user = normalize_username(raw_user)

    if user in USUARIOS and pwd == USUARIOS[user]:
        st.session_state.autenticado = True
    else:
        st.session_state.erro_login = True

# Se ainda não autenticado, mostra tela de login
if not st.session_state.autenticado:
    st.title("🔐 Login")
    st.text_input("Usuário", key="user")
    st.text_input("Senha", type="password", key="pwd")
    st.button("Entrar", on_click=_autenticar)

    if st.session_state.erro_login:
        st.error("Credenciais incorretas")
        st.session_state.erro_login = False  # reseta para próxima tentativa

    st.stop()  # bloqueia execução do resto enquanto não logar
# ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Dashboard", layout="wide")

@st.cache_data
def carregar_dados():
    """Carrega e processa todos os dados necessários"""
    dados_brutos = cgd.carregar_dados_brutos()
    dados_processados = cgd.enriquecer_dados(*dados_brutos)
    return dados_processados

dados_carregados = carregar_dados()

# ============================
# 6. Filtros
# ============================

def filtrar_dados_completos(data_dict, filter_future=True):
    """
    Applies unified filtering across all data sources with relationships maintained
    
    Parameters:
        data_dict (dict): Dictionary of DataFrames from carregar_e_enriquecer_dados()
        filter_future (bool): Whether to exclude future dates
    
    Returns:
        dict: Filtered DataFrames
    """
    # 1. Get unified filter values from all sources
    all_vehicles = pd.concat([
        data_dict["viagens"]["veiculo"],
        data_dict["despesas_fixas"]["veiculo"]
    ]).dropna().unique()
    
    all_drivers = data_dict["viagens"]["motorista"].dropna().unique()
    
    # 2. Create unified filters
    selected_vehicles = st.sidebar.multiselect(
        "Veículos", 
        options=all_vehicles,
        placeholder="Todos veículos"
    )
    
    selected_drivers = st.sidebar.multiselect(
        "Motoristas",
        options=all_drivers,
        placeholder="Todos motoristas"
    )
    
    # 3. Date range (using most inclusive dates)
    min_date = min(
        data_dict["viagens"]["data_ida"].min(),
        data_dict["despesas_fixas"]["data"].min()
    ).date()
    
    max_date = max(
        data_dict["viagens"]["data_volta"].max(),
        data_dict["despesas_fixas"]["data"].max()
    ).date()
    
    date_range = st.sidebar.date_input(
        "Período",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # 4. Future data toggle
    if filter_future:
        incluir_futuras = st.sidebar.toggle(
            "Incluir dados futuros?",
            value=False
        )
    
    # 5. Apply filters to each DataFrame
    filtered_data = {}
    
    # Filter trips first (will affect travel expenses)
    mask_viagem = pd.Series(True, index=data_dict["viagens"].index)
    
    if selected_vehicles:
        mask_viagem &= data_dict["viagens"]["veiculo"].isin(selected_vehicles)
    if selected_drivers:
        mask_viagem &= data_dict["viagens"]["motorista"].isin(selected_drivers)
    if len(date_range) == 2:
        inicio, fim = map(pd.to_datetime, date_range)
        mask_viagem &= data_dict["viagens"]["data_ida"].between(inicio, fim)
    if filter_future and not incluir_futuras:
        mask_viagem &= (data_dict["viagens"]["data_ida"] <= pd.Timestamp.now())
    
    filtered_data["viagens"] = data_dict["viagens"][mask_viagem].copy()
    
    # Filter travel expenses based on filtered trips
    filtered_data["despesas_viagem"] = data_dict["despesas_viagem"][
        data_dict["despesas_viagem"]["viagem_id"].isin(filtered_data["viagens"]["id"])
    ].copy()
    
    # Filter fixed expenses
    mask_fixas = pd.Series(True, index=data_dict["despesas_fixas"].index)
    
    if selected_vehicles:
        mask_fixas &= data_dict["despesas_fixas"]["veiculo"].isin(selected_vehicles)
    if len(date_range) == 2:
        inicio, fim = map(pd.to_datetime, date_range)
        mask_fixas &= data_dict["despesas_fixas"]["data"].between(inicio, fim)
    if filter_future and not incluir_futuras:
        mask_fixas &= (data_dict["despesas_fixas"]["data"] <= pd.Timestamp.now())
    
    filtered_data["despesas_fixas"] = data_dict["despesas_fixas"][mask_fixas].copy()
    
    return filtered_data

with st.sidebar:
    st.header("🔍 Filtros Integrados")
    dados_filtrados = filtrar_dados_completos(dados_carregados)
    
# ============================
# 5.1. Validacao
# ============================
with st.sidebar:
    st.header("🔔 Qualidade dos Dados")
    avisos = checar_anomalias(dados_filtrados)
    if avisos:
        for a in avisos:
            container = {
                "error":   st.error,
                "warning": st.warning,
                "info":    st.info
            }.get(a["nivel"], st.info)

            with st.expander(f"{a['msg']}  ({a['qtd']})"):
                container(a["msg"])
                st.write("**Exemplos:**")
                for linha in a["detalhes"]:
                    st.text("• " + linha)
                st.caption(f"Sugestão: {a['sugestao']}")
    else:
        st.success("Nenhuma anomalia relevante encontrada.")
# ============================
# 6. Metricas
# ============================
    
def calcular_metricas_gerais(df_viagens, df_desp_viagem, df_desp_fixa):
    """
    Consolida todos os indicadores financeiros e operacionais,
    já ordenados por correlação (do mais fundamental ao derivado).
    """
    # ────────────────────────────────────────────
    # Pré-cálculos fundamentais (usados por vários KPIs)
    # ────────────────────────────────────────────
    km_total           = calculos.km_total(df_viagens)
    receita_bruta_tot  = calculos.calcular_receita_bruta(df_viagens)
    custo_var_tot      = calculos.custo_variavel_total(df_desp_viagem)
    custo_fixo_tot     = calculos.despesa_fixa_total(df_desp_fixa)
    lucro_bruto_tot    = receita_bruta_tot - custo_var_tot
    lucro_liq_tot      = lucro_bruto_tot - custo_fixo_tot

    # Séries mensais (DataFrame)
    df_lucro_mensal = calculos.calcular_faturamento_por_mes(
        df_viagens, df_desp_viagem, df_desp_fixa
    )

    # ────────────────────────────────────────────
    # Métricas agrupadas por “grau de parentesco”
    # ────────────────────────────────────────────
    metricas = {

        # 1️⃣  Totais de volume e uso
        "km_total":                    km_total,
        "total_viagens":               calculos.total_viagens(df_viagens),
        "litros_combustivel_total":    calculos.litros_combustivel_total(df_viagens),

        # 2️⃣  Totais financeiros brutos
        "receita_bruta_total":         receita_bruta_tot,
        "custo_variavel_total":        custo_var_tot,
        "custo_fixo_total":            custo_fixo_tot,

        # 3️⃣  Lucros agregados
        "lucro_bruto_total":           lucro_bruto_tot,
        "lucro_liquido_total":         lucro_liq_tot,
        "lucro_liquido_mensal_df":     df_lucro_mensal,            # dataframe inteiro
        "lucro_liquido_mensal_total":  df_lucro_mensal["lucro_liquido"].sum(),

        # 4️⃣  Indicadores de margem / eficiência global
        "margem_lucro_liquido_%":      calculos.calcular_margem_lucro_liquido(
                                           lucro_liq_tot, receita_bruta_tot),
        "cpk_completo":                calculos.calcular_cpk(df_viagens, custo_fixo_tot),
        "cpk_sem_capex":               calculos.calcular_cpk_sem_capex(
                                           df_desp_viagem, df_desp_fixa, km_total),
        "rpk":                         calculos.calcular_rpk(receita_bruta_tot, km_total),
        "margem_lucro_por_km":         calculos.calcular_margem_por_km(
                                           receita_bruta_tot,
                                           custo_var_tot + custo_fixo_tot,
                                           km_total),
        "ebitda":                      calculos.calcular_ebitda(lucro_liq_tot, df_desp_fixa),

        # 5️⃣  Custos / receitas unitários
        "custo_combustivel_km":        calculos.calcular_custo_combustivel_por_km(
                                           df_desp_viagem, km_total),
        "custo_manutencao_km":         calculos.calcular_custo_manutencao_por_km(
                                           df_desp_viagem, df_desp_fixa, km_total),
        "custo_pneus_km":              calculos.calcular_custo_pneus_por_km(
                                           df_desp_viagem, km_total),

        # 6️⃣  Médias por viagem / consumo
        "consumo_medio_km_l":          calculos.calcular_consumo_km_por_litro(df_viagens),
        "receita_media_por_viagem":    calculos.calcular_receita_media_por_viagem(df_viagens),
        "despesa_media_por_viagem":    calculos.calcular_despesa_media_por_viagem(
                                           df_desp_viagem, df_viagens),
        "preco_medio_combustivel":     df_desp_viagem["preco_combustivel"].mean(),
        "media_tempo_ocioso_por_mes": calculos.calcular_idle_medio(df_viagens),

        # 7️⃣  Manutenção / CAPEX
        "capex_total":                 calculos.capex(df_desp_fixa),
        "total_manutencoes":           calculos.custo_manut(df_desp_fixa, df_desp_viagem),
        "frequencia_manutencao":       calculos.calcular_frequencia_manutencao(
                                           df_desp_viagem, df_desp_fixa),

        # 8️⃣  Gastos diretos com pessoal
        "gasto_empresa_total":         calculos.gasto_empresa_total(df_viagens),
        "gasto_motorista_total":       calculos.gasto_motorista_total(df_viagens),
        "troco_total":                 calculos.troco_total(df_viagens),
    }

    # ────────────────────────────────────────────
    # Arredondamento de valores numéricos
    # ────────────────────────────────────────────
    for k, v in metricas.items():
        if isinstance(v, (int, float)):
            metricas[k] = round(v, 2) if not pd.isna(v) else 0

    return metricas

metricas_gerais = calcular_metricas_gerais(
    dados_filtrados['viagens'], 
    dados_filtrados['despesas_viagem'], 
    dados_filtrados['despesas_fixas']
)

# ============================
# 6. Estilização para Relatório
# ============================

def bar_with_sign(df, x, y, title, labels, text_fmt="%{y:.2f}"):
    df_plot = df.copy()
    df_plot["__color"] = df_plot[y].apply(lambda v: "neg" if v < 0 else "pos")
    fig = px.bar(
        df_plot, x=x, y=y, color="__color",
        color_discrete_map={"pos": "#1f77b4", "neg": "red"},
        title=title, labels=labels, text=y
    )
    fig.update_traces(texttemplate=text_fmt, textposition="outside")
    fig.update_layout(showlegend=False)
    return fig

# ============================
# 7. Relatórios
# ============================

aba1, aba2, aba3, aba4, aba5, aba6, aba7, aba8 = st.tabs([
    "Relatório de Viagem",
    "Lucro de Viagem por Mês",
    "Análise Financeira",
    "Análise Operacional",
    "Custos Detalhados",
    "Manutenção Detalhada",
    "Combustível Detalhado",
    "Calculadora de Comissão"
])

# ============================
# 7. Relatórios
# ============================
with aba1:  # Relatório de Viagem
    st.header("Relatório Individual de Viagem")

    opcoes = dados_filtrados["viagens"][["identificador", "id"]]
    sel = st.selectbox("Selecione a Viagem", opcoes["identificador"])
    if sel:
        vid = opcoes.loc[opcoes["identificador"] == sel, "id"].iloc[0]
        df_v = dados_filtrados["viagens"].query("id == @vid")
        df_dv = dados_filtrados["despesas_viagem"].query("viagem_id == @vid")
        r = df_v.iloc[0]

        met = calcular_metricas_gerais(df_v, df_dv, dados_filtrados["despesas_fixas"])
        rep = {
            **met,
            **{k: float(r.get(k, 0) or 0) for k in [
                "frete_ida","frete_volta","frete_extra",
                "gasto_motorista","gasto_empresa","troco_da_viagem",
                "km_inicial","km_final","lts_combustivel","preco_combustivel"
            ]},
            "data_saida":   r["data_ida"].date(),
            "data_chegada": r["data_volta"].date(),
            "km_total":     float(r.get("km_total", 0) or 0),
        }

        cia, cga = st.columns([3,2], gap="small")
        pares = [
            ("Soma dos Fretes",   rep["receita_bruta_total"],        "#2E7D32", "#1B5E20"),
            ("Despesa Total",      rep["custo_variavel_total"],"#C62828", "#8E0000"),
            ("Frete Ida",         rep["frete_ida"],           "#2E7D32", "#1B5E20"),
            ("Gasto Motorista",   rep["gasto_motorista"],     "#F9A825", "#F57F17"),
            ("Frete Volta",       rep["frete_volta"],         "#2E7D32", "#1B5E20"),
            ("Gasto Empresa",     rep["gasto_empresa"],       "#F9A825", "#F57F17"),
            ("Frete Extra",       rep["frete_extra"],         "#2E7D32", "#1B5E20"),
            ("Troco da Viagem",   rep["troco_da_viagem"],     "#1565C0", "#003C8F"),
        ]

        with cia:
            st.info(
                "💡 **Como interpretar:** Estes valores pertencem *somente* à viagem "
                "selecionada. Compare a soma dos fretes com o total de despesas para "
                "ver rapidamente se a viagem foi lucrativa."
            )
            for i in range(0, len(pares), 2):
                a, b = st.columns(2)
                for w, (lbl,val, bg, bd) in zip((a,b), pares[i:i+2]):
                    w.markdown(dh.card_compacto(
                        label=lbl, valor=val, prefixo="R$ ",
                        cor_texto="#FFFFFF", cor_fundo=bg, cor_borda=bd
                    ), unsafe_allow_html=True)

        with cga:
            pmin, pmax = df_dv["preco_combustivel"].agg(["min","max"])
            pavg = df_dv["preco_combustivel"].mean()
            if pd.notna(pmin) and pd.notna(pmax) and pd.notna(pavg):
                dh.plot_gauge_indicador_base(
                    valor=pavg, titulo="Preço Médio do Combustível",
                    unidade="R$/L", faixa=[pmin, pmax]
                )
                st.info(
                    "💡 **Dica:** A régua compara o preço médio pago no abastecimento "
                    "desta viagem (ponteiro) versus o mínimo e máximo do período filtrado."
                )

        st.subheader("🛣️ Progresso da Viagem")
        km0, kmf, kmt = rep["km_inicial"], rep["km_final"], rep["km_total"]
        pct = min(max(kmt / max(kmf - km0, 1), 0), 1)
        c1, c2, c3 = st.columns(3)
        c1.metric("KM Inicial", f"{km0:,.0f}")
        c1.caption(rep["data_saida"].strftime("%d/%m/%Y"))
        c2.metric("KM Rodado", f"{kmt:,.0f}")
        c3.metric("KM Final",  f"{kmf:,.0f}")
        c3.caption(rep["data_chegada"].strftime("%d/%m/%Y"))
        st.progress(int(pct * 100))

        st.subheader("Despesas por Categoria")
        
        st.info(
            "💡 **Orientação:** Use o treemap para descobrir quais categorias pesam "
            "mais nas despesas variáveis desta viagem. Clique nos blocos para detalhar."
        )
        
        if df_dv.empty:
            st.info("Nenhuma despesa variável registrada.")
        else:
            # Agrupa despesas por categoria
            df_cat = df_dv.groupby("categoria", as_index=False)["valor"].sum()
            
            # Interface para usuário selecionar as categorias que quer ver
            categorias_disponiveis = df_cat["categoria"].unique().tolist()
            categorias_selecionadas = st.multiselect(
                "Selecione categorias para exibir:", 
                options=categorias_disponiveis,
                default=categorias_disponiveis
            )

            if not categorias_selecionadas:
                st.warning("Selecione ao menos uma categoria para visualizar o gráfico.")
            else:
                # Filtra só as categorias selecionadas
                df_filtrado = df_cat[df_cat["categoria"].isin(categorias_selecionadas)]
                
                # Cria treemap correto
                fig = px.treemap(
                    df_filtrado,
                    path=[px.Constant("Todas Despesas"), "categoria"],
                    values="valor",
                    color="categoria",
                    title="Composição de Despesas Variáveis"
                )
                fig.update_traces(root_color="lightgray")
                fig.update_layout(margin=dict(t=30, l=5, r=5, b=5))
                
                st.plotly_chart(fig, use_container_width=True)
            
with aba2: #Lucro de Viagem por mês
    st.header("Visão Geral do Mês da Frota")

    # 1. Prepara dados com mês e ano
    df_v = dados_filtrados['viagens'].copy()
    df_v['mes'] = df_v['data_ida'].dt.month
    df_v['ano'] = df_v['data_ida'].dt.year
    
    df_var = dados_filtrados['despesas_viagem'].copy()
    df_var['mes'] = df_var['data_viagem'].dt.month
    df_var['ano'] = df_var['data_viagem'].dt.year

    df_f = dados_filtrados['despesas_fixas'].copy()
    df_f['mes'] = df_f['data'].dt.month
    df_f['ano'] = df_f['data'].dt.year

    # 2. Calcula Lucro Bruto e Despesa Fixa por ano, mês e veículo
    df_rec = (
        df_v
        .groupby(['ano','mes','veiculo'])
        .apply(lambda g: calculos.calcular_receita_bruta(g))
        .reset_index(name='Receita Bruta')
    )
    
    df_var_group = (
        df_var
        .groupby(['ano','mes','veiculo'])
        .apply(lambda g: calculos.custo_variavel_total(g))
        .reset_index(name='Despesa Variável')
    )

    df_fix = (
        df_f
        .groupby(['ano','mes','veiculo'])
        .apply(lambda g: calculos.despesa_fixa_total(g))
        .reset_index(name='Despesa Fixa')
    )
    
    df_kpi = (
        df_rec
        .merge(df_var_group, on=['ano','mes','veiculo'], how='outer')
        .merge(df_fix,       on=['ano','mes','veiculo'], how='outer')
        .fillna(0)
    )

    # 3. Junta e calcula Lucro Líquido
    df_kpi['Lucro Bruto']   = df_kpi['Receita Bruta'] - df_kpi['Despesa Variável']
    df_kpi['Lucro Líquido'] = df_kpi['Lucro Bruto']    - df_kpi['Despesa Fixa']

    # 4. Cards de resumo
    total_gross = df_kpi['Lucro Bruto'].sum()
    total_fix   = df_kpi['Despesa Fixa'].sum()
    total_net   = df_kpi['Lucro Líquido'].sum()

    c1, c2, c3 = st.columns(3)
    _tooltip_lucro_bruto = "Soma de todos os fretes menos despesas de viagem (Fretes - Desp.Viagem) das viagens iniciadas no periodo"
    _tooltip_desp_fixa = "Soma de todas as Despesas Fixas no Periodo"
    _tooltip_lucro_liq = "Lucro Bruto menos Despesas Fixas (lucro_bruto - desp_fixas)"

    c1.markdown(
        f'<div title="{_tooltip_lucro_bruto}">'
        f'{dh.card_compacto("Lucro Bruto", total_gross, prefixo="R$",tipo="Flex")}'
        f'</div>',
        unsafe_allow_html=True
    )
    c2.markdown(
        f'<div title="{_tooltip_desp_fixa}">'
        f'{dh.card_compacto("Despesa Fixa Total", total_fix, prefixo="R$", tipo="Negative")}'
        f'</div>',
        unsafe_allow_html=True
    )
    c3.markdown(
        f'<div title="{_tooltip_lucro_liq}">'
        f'{dh.card_compacto("Lucro Líquido", total_net, prefixo="R$", tipo="Flex")}'
        f'</div>',
        unsafe_allow_html=True
    )

    # 5. Tabela detalhada
    st.subheader("Detalhamento Mensal por Veículo")
     # prepara a tabela
    df_table = df_kpi.rename(columns={'veiculo':'Placa'}) \
                     .loc[:, ['mes','ano','Placa','Despesa Fixa','Lucro Líquido']] \
                     .sort_values(['ano','mes','Placa'])

    # gera um mapa de cores para cada placa
    unique_plates = df_table['Placa'].unique()
    palette = px.colors.qualitative.Plotly
    plate_colors = {p: palette[i % len(palette)] for i, p in enumerate(unique_plates)}

    # funções de estilo
    def color_lucro_liquido(val):
        return 'color: red; font-weight: bold' if val < 0 else 'color: green; font-weight: bold'

    def style_placa(val):
        cor = plate_colors.get(val, '#FFFFFF')
        return f'background-color: {cor}; color: white'

    # cria o Styler
    df_styled = (
        df_table
        .style
        .format({
            'Despesa Fixa':    'R$ {:,.2f}',
            'Lucro Líquido':   'R$ {:,.2f}'
        })
        .applymap(color_lucro_liquido, subset=['Lucro Líquido'])
        .applymap(style_placa, subset=['Placa'])
    )

    col_left, col_center, col_right = st.columns([4, 2, 2])
    with col_left:
        st.dataframe(df_styled, use_container_width=True)
    
with aba3:  #Análise Financeira
    st.header("📈 Indicadores Financeiros")

    # Linha 2 de métricas
    col5, col6, col7 = st.columns(3)
    
    tooltip_ebitda  = "EBITDA = lucro operacional antes de juros, impostos, depreciação e amortização."
    tooltip_capex   = "CAPEX = investimentos em bens duráveis (Prestação, Pagamento de Financiamento) acumulados no período filtrado."
    tooltip_margem  = "Margem de Lucro Líquido = lucro líquido ÷ receita bruta. Mede quanto da receita vira lucro."

    with col5:
        st.markdown(
            f'<div title="{tooltip_ebitda}">'
            f'{dh.card_compacto("EBITDA Parcial", metricas_gerais["ebitda"], prefixo="R$")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col6:
        st.markdown(
            f'<div title="{tooltip_capex}">'
            f'{dh.card_compacto("CAPEX Total", metricas_gerais["capex_total"], prefixo="R$")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col7:
        st.markdown(
            f'<div title="{tooltip_margem}">'
            f'{dh.card_compacto("Margem de Lucro Liquido", metricas_gerais["margem_lucro_liquido_%"], unidade="%", tipo="Flex")}'
            f'</div>',
            unsafe_allow_html=True
        )
        
    # Gráficos
    st.subheader("📊 Visualizações Financeiras")
    st.info(
        "💡 **Composição de Fretes:** mostra quanto cada tipo de frete contribui "
        "para a receita total no período filtrado. Use para identificar suas rotas mais rentáveis."
    )
    
    dh.plot_bar_composicao_fretes(dados_filtrados['viagens'])
    
    st.subheader("📋 Financeiro por Veículo")

    kpis = []
    for veic, df_v in dados_filtrados['viagens'].groupby('veiculo'):
        df_df = dados_filtrados['despesas_fixas'].query("veiculo == @veic")
        df_dv = dados_filtrados['despesas_viagem'].query("veiculo == @veic")

        soma_fretes = calculos.calcular_receita_bruta(df_v)
        capex      = calculos.capex(df_df)
        lucro_liq  = calculos.calcular_lucro_liquido(df_v, df_dv, df_df)
        ebitda     = calculos.calcular_ebitda(lucro_liq, df_df)
        margem_pct = calculos.calcular_margem_lucro_liquido(lucro_liq, soma_fretes)

        kpis.append({
            "Placa": veic,
            "EBITDA": ebitda,
            "CAPEX": capex,
            "Margem (%)": margem_pct
        })

    df_fin = pd.DataFrame(kpis)

    # cores por placa
    palette = px.colors.qualitative.Plotly
    placas = df_fin["Placa"].unique()
    plate_colors = {p: palette[i % len(palette)] for i, p in enumerate(placas)}

    def style_placa(v):
        c = plate_colors.get(v, "#FFFFFF")
        return f"background-color: {c}; color: white; font-weight: bold"

    def style_margem(v):
        return "color: green; font-weight: bold" if v >= 0 else "color: red; font-weight: bold"

    styled = (
        df_fin.style
            .format({
                "EBITDA": "R$ {:,.2f}",
                "CAPEX": "R$ {:,.2f}",
                "Margem (%)": "{:.2f}%"
            })
            .applymap(style_placa, subset=["Placa"])
            .applymap(style_margem, subset=["Margem (%)"])
    )

    col_left, col_center, col_right = st.columns([4, 2, 2])
    with col_left:
        st.dataframe(styled, use_container_width=True)
        
    dh.plot_area_evolucao_financeira(
        cgd.processar_dados_historicos(
            dados_filtrados['viagens'],
            dados_filtrados['despesas_viagem'],
            dados_filtrados['despesas_fixas']
        ),
        y_cols=['soma_fretes', 'despesa_total'],
        x_col="data_ida",
        stacked=False
    )
    st.info(
        "💡 **Evolução Financeira:** acompanhe a trajetória de receita e despesa mês a mês. "
        "Passe o mouse sobre a linha para ver valores exatos."
    )

with aba4:  # Análise Operacional
    st.header("🚚 Indicadores Operacionais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    tip_km      = "Km Total = soma de todos os quilômetros percorridos no período filtrado."
    tip_viag    = "Viagens = total de viagens concluídas no período filtrado."
    tip_receita = "Receita Média por Viagem = receita bruta total ÷ número de viagens."
    tip_idle    = "Dias Ociosos = dias sem viagem ÷ meses no período filtrado."
    
    with col1:
        st.markdown(
            f'<div title="{tip_km}">'
            f'{dh.card_compacto("Km Total", metricas_gerais["km_total"], "km")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div title="{tip_viag}">'
            f'{dh.card_compacto("Viagens", metricas_gerais["total_viagens"])}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f'<div title="{tip_receita}">'
            f'{dh.card_compacto("Receita Média", metricas_gerais["receita_media_por_viagem"], prefixo="R$")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col4:
        idle_medio = metricas_gerais["media_tempo_ocioso_por_mes"]
        st.markdown(
            f'<div title="{tip_idle}">'
            f'{dh.card_compacto("Dias Ociosos (média)", idle_medio, unidade="dias")}'
            f'</div>',
            unsafe_allow_html=True
        )

        
    st.subheader("📊 Comparativo de Métricas por Veículo")
    st.info("💡 **Como usar:** compare CPK e Lucro/KM entre placas. O ideal é Lucro/KM maior que CPK.")
    
    idle_dict = calculos.idle_medio_por_veiculo(dados_filtrados["viagens"])

    # 1. Monta a lista de dicts com RPK, CPK, Lucro/KM e Custo Manutenção/KM por veículo
    metricas_por_veiculo = []
    metricas_por_veiculo = []
    for veic, df_v in dados_filtrados['viagens'].groupby('veiculo'):
        df_dv = dados_filtrados['despesas_viagem'].query("veiculo == @veic")
        df_df = dados_filtrados['despesas_fixas'].query("veiculo == @veic")
        km = calculos.km_total(df_v)
        metricas_por_veiculo.append({
            "Veículo": veic,
            "RPK": calculos.calcular_rpk(calculos.calcular_receita_bruta(df_v), km),
            "CPK": calculos.calcular_cpk(df_v, calculos.despesa_fixa_total(df_df)),
            "Lucro/KM": calculos.calcular_lucro_liquido(df_v, df_dv, df_df) / km if km else 0,
            "Custo Manutenção/KM": calculos.calcular_custo_manutencao_por_km(df_dv, df_df, km),
            "Dias Ociosos": idle_dict.get(veic, 0.0)
        })

    # 2. Transforma pra long e plota
    dfm = pd.DataFrame(metricas_por_veiculo).melt(
        id_vars="Veículo",
        value_vars=["Lucro/KM", "RPK", "CPK", "Custo Manutenção/KM"],
        var_name="Métrica",
        value_name="Valor"
    )
    
    dh.plot_bar_base(
        dfm,
        x_col="Veículo",
        y_col="Valor",
        color_col="Métrica",
        barmode="group",
        title="Comparativo de Métricas por Veículo",
        labels={"Valor": "R$/km", "Veículo": "Veículo"}
    )
    
    df_kpi = pd.DataFrame(metricas_por_veiculo)

    df_kpi = pd.DataFrame(metricas_por_veiculo).rename(columns={"Veículo": "Placa"})
    unique_plates, palette = df_kpi["Placa"].unique(), px.colors.qualitative.Plotly
    plate_colors = {p: palette[i % len(palette)] for i, p in enumerate(unique_plates)}

    def style_placa(v): return f"background-color: {plate_colors.get(v, '#FFFFFF')}; color: white; font-weight: bold"
    def color_lucro_km(v): return "color: red; font-weight: bold" if v < 0 else "color: green; font-weight: bold"
    def color_idle(v): return "color: red" if v > 5 else ""

    df_styled = (
        df_kpi.style
        .format({
            'RPK': 'R$ {:,.2f}',
            'CPK': 'R$ {:,.2f}',
            'Lucro/KM': 'R$ {:,.2f}',
            'Custo Manutenção/KM': 'R$ {:,.2f}',
            'Dias Ociosos': '{:.1f}'
        })
        .applymap(style_placa, subset=['Placa'])
        .applymap(color_lucro_km, subset=['Lucro/KM'])
        .applymap(color_idle, subset=['Dias Ociosos'])
    )
    st.subheader("📋 Tabela de Métricas por Veículo")
    
    col_left, col_center, col_right = st.columns([4, 2, 2])
    
    with col_left:
        st.dataframe(df_styled, use_container_width=True)

    dh.plot_scatter_custo_vs_lucro_veiculo(dados_filtrados['viagens'])
    st.info("💡 **Interprete o gráfico:** bolhas maiores = mais quilômetros rodados. "
            "Canto inferior direito = desempenho ideal (alto lucro, baixo custo).")
    
    st.subheader("📊 Eficiência dos Motoristas")
    
    df_eficiencia_motoristas = cgd.preparar_df_eficiencia_motoristas(dados_filtrados['viagens'], dados_filtrados['despesas_viagem'], dados_filtrados['despesas_fixas'])
    dh.plot_bar_eficiencia_motoristas(df_eficiencia_motoristas)
    st.info("💡 Eficiência é Lucro Liquido por Km Rodado. Passe o mouse sobre as barras para detalhes.")
    
with aba5:
    st.header("Detalhamento de Custo")

    # ────────────────────────────
    # 1. Despesas Fixas
    # ────────────────────────────
    st.subheader("Despesas Fixas")
    
    st.info(
        "💡Visualize quais categorias puxam mais o custo fixo mensal."
        "Mouse em cima do bloco para detalhar."
    )
    
    df_f_f = dados_filtrados["despesas_fixas"]
    df_comp_fixas = df_f_f.groupby("categoria", as_index=False)["valor"].sum()

    cats_fixas = df_comp_fixas["categoria"].unique().tolist()
    sel_fixas = st.multiselect(
        "Selecione categorias de despesas fixas para exibir:",
        options=cats_fixas,
        default=cats_fixas,
        key="multiselect_fixas",
    )

    if not sel_fixas:
        st.warning("Selecione ao menos uma categoria de despesa fixa para visualizar o gráfico.")
    else:
        df_f_f_filtrado = df_comp_fixas[df_comp_fixas["categoria"].isin(sel_fixas)]
        fig_fixas = px.treemap(
            df_f_f_filtrado,
            path=[px.Constant("Despesas Fixas"), "categoria"],
            values="valor",
            color="categoria",
            title="Composição de Despesas Fixas",
        )
        fig_fixas.update_traces(root_color="lightgrey")
        fig_fixas.update_layout(margin=dict(t=30, l=5, r=5, b=5))
        st.plotly_chart(fig_fixas, use_container_width=True)

    st.markdown("---")  # Separador

    # ────────────────────────────
    # 2. Despesas de Viagem
    # ────────────────────────────
    st.subheader("Despesas de Viagem")
    st.info(
        "💡 Mostra a distribuição das despesas variáveis associadas às viagens."
        "Ideal para encontrar gargalos de custo."
    )
    df_dv = dados_filtrados["despesas_viagem"]
    df_comp_viagem = df_dv.groupby("categoria", as_index=False)["valor"].sum()

    cats_viagem = df_comp_viagem["categoria"].unique().tolist()
    sel_viagem = st.multiselect(
        "Selecione categorias de despesas de viagem para exibir:",
        options=cats_viagem,
        default=cats_viagem,
        key="multiselect_viagem",
    )

    if not sel_viagem:
        st.warning("Selecione ao menos uma categoria de despesa de viagem para visualizar o gráfico.")
    else:
        df_dv_filtrado = df_comp_viagem[df_comp_viagem["categoria"].isin(sel_viagem)]
        fig_viagem = px.treemap(
            df_dv_filtrado,
            path=[px.Constant("Despesas de Viagem"), "categoria"],
            values="valor",
            color="categoria",
            title="Composição de Despesas de Viagem",
        )
        fig_viagem.update_traces(root_color="lightgrey")
        fig_viagem.update_layout(margin=dict(t=30, l=5, r=5, b=5))
        st.plotly_chart(fig_viagem, use_container_width=True)

    st.markdown("---")  # Separador

    # ────────────────────────────
    # 3. Despesas ao Longo do Tempo
    # ────────────────────────────
    st.subheader("Despesas ao Longo do Tempo")
    st.info(
        "💡 **Evolução Temporal:** identifique sazonalidade ou picos atípicos de gasto. "
        "Passe o mouse sobre a linha para valores exatos."
    )
    # prepara séries temporais agregadas (mês)
    df_f_f_ts = (
        df_f_f.assign(data=pd.to_datetime(df_f_f["data"]))
               .groupby(pd.Grouper(key="data", freq="M"))["valor"]
               .sum()
               .reset_index()
               .assign(tipo="Fixas")
    )

    df_dv_ts = (
        df_dv.assign(data=pd.to_datetime(df_dv["data_viagem"]))
              .groupby(pd.Grouper(key="data", freq="M"))["valor"]
              .sum()
              .reset_index()
              .assign(tipo="Viagem")
    )

    df_ts = pd.concat([df_f_f_ts, df_dv_ts]).sort_values("data")

    fig_tempo = px.line(
        df_ts,
        x="data",
        y="valor",
        color="tipo",
        markers=True,
        title="Evolução Mensal das Despesas",
        labels={"data": "Mês", "valor": "Valor (R$)", "tipo": "Tipo"},
    )
    fig_tempo.update_layout(xaxis_tickformat="%b/%Y", hovermode="x unified")
    st.plotly_chart(fig_tempo, use_container_width=True)
    
with aba6:  # Manutenção Detalhada 
    st.header("🔧 Indicadores de Manutenção")
    
    tip_ckm  = "Custo manutenção por quilômetro rodado."
    tip_freq = "Número de manutenções registradas no período."
    tip_ctot = "Soma de todas as despesas de manutenção no período selecionado."
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div title="{tip_ckm}">'
            f'{dh.card_compacto("Custo/km", metricas_gerais["custo_manutencao_km"], "R$/km")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div title="{tip_freq}">'
            f'{dh.card_compacto("Manutenções", metricas_gerais["frequencia_manutencao"])}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f'<div title="{tip_ctot}">'
            f'{dh.card_compacto("Custo Total", metricas_gerais["total_manutencoes"], prefixo="R$")}'
            f'</div>',
            unsafe_allow_html=True
        )
    st.subheader("📊 Análise de Manutenção")
    st.info("💡 **Frequência por Veículo:** alta frequência pode indicar problema.")
    
    # Gráfico de Barras (Frequência por Veículo)
    dh.plot_bar_freq_manutencao_por_veiculo(
        dados_filtrados['despesas_viagem'],  # DataFrame de despesas variáveis (viagem)
        dados_filtrados['despesas_fixas']    # DataFrame de despesas fixas
    )


with aba7:  # Combustível Detalhado
    st.header("⛽ Indicadores de Combustível")
    
    tip_cons = "Km rodados por litro — quanto maior melhor."
    tip_ckm  = "Custo de combustível por quilômetro percorrido."
    tip_pmed = "Preço médio do litro pago no período filtrado."
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div title="{tip_cons}">'
            f'{dh.card_compacto("Consumo Médio", metricas_gerais["consumo_medio_km_l"], "km/L")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div title="{tip_ckm}">'
            f'{dh.card_compacto("Custo/km", metricas_gerais["custo_combustivel_km"], "R$/km")}'
            f'</div>',
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f'<div title="{tip_pmed}">'
            f'{dh.card_compacto("Preço Médio", metricas_gerais.get("preco_medio_combustivel", 0), "R$/L")}'
            f'</div>',
            unsafe_allow_html=True
        )

    st.subheader("📊 Análise de Combustível")
    st.info("💡 **Consumo km/L:** veja quais veículos se aproximam ou superam a meta.")
    dh.plot_bar_consumo_km_por_litro(dados_filtrados['viagens'])
    
    st.info("💡 **Preço Médio do Litro:** entenda o impacto de aumentos no oleo diesel.")
    dh.plot_line_preco_medio_combustivel(dados_filtrados['despesas_viagem'])

with aba8:
    st.header("💰 Calculadora de Comissão")

    # escolha da viagem
    opcoes = dados_filtrados["viagens"][["identificador", "id"]]
    sel = st.selectbox("Selecione a Viagem", opcoes["identificador"], key="sel_viagem_comissao")

    if sel:
        vid = opcoes.loc[opcoes["identificador"] == sel, "id"].iloc[0]
        row = dados_filtrados["viagens"].loc[dados_filtrados["viagens"]["id"] == vid].iloc[0]

        # cálculo
        detalhes = calcular_comissao(row, dados_filtrados["viagens"])
        
        tip_media = "Consumo médio desta viagem comparado à média histórica do veículo."
        tip_rec   = "Receita bruta da viagem dividida pelo número de dias fora de casa."
        tip_idle  = "Dias sem viagem entre esta e a viagem anterior."


        # exibição
        c1, c2, c3 = st.columns(3)
        c1.metric("Média da Viagem (km/L)", f"{detalhes['media_trip']:.2f}", help=tip_media)
        c1.caption(f"Histórico: {detalhes['media_ref']:.2f}")

        c2.metric("Receita/dia", f"R$ {detalhes['receita_por_dia']:.2f}", help=tip_rec)
        c2.caption(f"Histórico: R$ {detalhes['receita_ref']:.2f}")

        c3.metric("Dias ociosos", detalhes["dias_ociosos"], help=tip_idle)

        st.markdown("---")
        st.subheader("Resultado")
        st.info(
            "💡 **Nota Final** combina consumo e receita/dia, há uma punição para dias ociosos."
            " é um calculo com peso maior para média."
        )
        st.metric("Nota Final", f"{detalhes['nota_final']*100:.1f} %")
        st.metric("Comissão Sugerida", f"R$ {detalhes['comissao']:.2f}", delta=None)
        st.caption(f"Parâmetros atuais: COMISSAO_MAX = R$ {config.DEFAULT_CONFIG['COMISSAO_MAXIMA']:.0f}, "
                   f"PESO_CONSUMO={config.DEFAULT_CONFIG['PESO_CONSUMO']:.0%}, PESO_RECEITA={config.DEFAULT_CONFIG['PESO_RECEITA']:.0%}, "
                   f"Ociosidade máx. {config.DEFAULT_CONFIG['PENALIDADE_OCIOSIDADE_MAX']:.0%}.")