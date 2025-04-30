import pandas as pd
from datetime import datetime

# ============================
# 1. Carregamento de Dados Brutos
# ============================
def carregar_dados_brutos():
    """Carrega todos os DataFrames brutos sem modificações."""
    df_desp_viagem = pd.read_csv(
        "reinan_costa_despesas_de_viagem_db.csv", 
        parse_dates=["data"]
    )
    df_desp_fixa = pd.read_csv(
        "reinan_costa_despesas_fixas_db.csv", 
        parse_dates=["data"]
    )
    df_motorista = pd.read_csv("reinan_costa_motorista_db.csv")
    df_veiculo = pd.read_csv("reinan_costa_veiculo_db.csv")
    df_viagem = pd.read_csv(
        "reinan_costa_viagem_completa.csv", 
        parse_dates=["data_ida", "data_volta"]
    )
    return df_desp_viagem, df_desp_fixa, df_motorista, df_veiculo, df_viagem

# ============================
# 2. Enriquecimento de Dados
# ============================
def enriquecer_dados(df_desp_viagem, df_desp_fixa, df_motorista, df_veiculo, df_viagem):
    """
    Aplica filtros estáticos e enriquece dados com relacionamentos:
    1. Filtra viagens não iniciadas
    2. Adiciona motorista/veículo às viagens
    3. Adiciona metadados às despesas
    """
    # Filtros iniciais
    df_viagem_filtrado = df_viagem[
        ~df_viagem["status"].isin(["NAO INICIADA", "EM VIAGEM"])]
    
    df_desp_viagem_filtrado = df_desp_viagem[
        df_desp_viagem["viagem_id"].isin(df_viagem_filtrado["id"])]

    # 3. Enriquecimento de viagens
    df_viagem_enriquecido = (
        df_viagem_filtrado
        .merge(
            df_motorista[["id", "nome"]], 
            left_on="motorista_id", 
            right_on="id", 
            how="left",
            suffixes=("", "_motorista")  # Sufixo explícito
        )
        .rename(columns={"nome": "motorista"})
        .merge(
            df_veiculo[["id", "placa"]], 
            left_on="veiculo_id", 
            right_on="id", 
            how="left",
            suffixes=("", "_veiculo")  # Sufixo explícito
        )
        .rename(columns={"placa": "veiculo"})
        .drop(columns=["id_motorista", "id_veiculo"])  # Colunas geradas pelos sufixos
    )

    # 4. Enriquecimento de despesas de viagem
    df_desp_viagem_enriquecido = (
        df_desp_viagem_filtrado
        .merge(
            df_viagem_enriquecido[["id", "motorista", "veiculo", "data_ida"]],
            left_on="viagem_id",
            right_on="id",
            how="left",
            suffixes=("", "_viagem")  # Sufixo para evitar duplicatas
        )
        .rename(columns={"data_ida": "data_viagem"})
        .drop(columns=["id_viagem"])  # Dropa a coluna gerada pelo merge
    )

    # 5. Enriquecimento de despesas fixas
    df_desp_fixa_enriquecido = (
        df_desp_fixa
        .merge(
            df_veiculo[["id", "placa"]],
            left_on="veiculo_id",
            right_on="id",
            how="left",
            suffixes=("", "_veiculo")  # Sufixo para evitar duplicatas
        )
        .rename(columns={"placa": "veiculo"})
        .drop(columns=["id_veiculo"])  # Dropa a coluna gerada pelo merge
    )

    return {
        "viagens": df_viagem_enriquecido,
        "despesas_viagem": df_desp_viagem_enriquecido,
        "despesas_fixas": df_desp_fixa_enriquecido
    }
# ============================
# 3. Cruzamento de Dados e Geração dos DataFrames Necessários
# ============================

def processar_dados_historicos(df_viagem,
                               df_desp_viagem,
                               df_desp_fixas):
    """Consolida KPIs mensais (robusto a datas vazias)."""

    # ───── 1. Sanitiza colunas de data ────────────────────────────
    for _df, col in [(df_desp_viagem, "data"), (df_desp_fixas, "data")]:
        _df[col] = pd.to_datetime(_df[col], errors="coerce")
        _df.dropna(subset=[col], inplace=True)

    # ───── 2. KPIs de viagens (já estavam OK) ─────────────────────
    df = df_viagem.copy()
    df["soma_frete_row"] = (
        df["frete_ida"].fillna(0)
        + df["frete_volta"].fillna(0)
        + df["frete_extra"].fillna(0)
    )
    historico_mensal = (
        df.groupby(pd.Grouper(key="data_ida", freq="M"))
          .agg(soma_fretes=("soma_frete_row", "sum"),
               lucro_bruto=("lucro_bruto", "sum"),
               km_total   =("km_total",    "sum"))
          .reset_index()
    )

    # ───── 3. Despesas viagem/fixas via RESAMPLE ─────────────────
    despesas_viagem_mensal = (
        df_desp_viagem
            .resample("M", on="data")["valor"]
            .sum()
            .reset_index(name="despesa_total_viagem")
    )

    def _is_imposto(cat: pd.Series) -> pd.Series:
        return cat.str.upper().isin(["IMPOSTO", "DETRAN"])

    despesas_fixas_mensal = (
        df_desp_fixas
            .resample("M", on="data")
            .agg(despesa_fixa_total=("valor", "sum"),
                 despesa_livre_impostos=("valor",
                     lambda x: x[~_is_imposto(df_desp_fixas.loc[x.index, "categoria"])].sum()),
                 capex=("valor",
                     lambda x: x[df_desp_fixas.loc[x.index, "categoria"]
                                   .str.upper().eq("PRESTACAO")].sum()))
            .reset_index()
    )

    # ───── 4. Merge & métricas derivadas (inalterado) ────────────
    hist = (
        historico_mensal
          .merge(despesas_viagem_mensal, left_on="data_ida",
                 right_on="data", how="left").drop(columns="data")
          .merge(despesas_fixas_mensal, left_on="data_ida",
                 right_on="data", how="left").drop(columns="data")
    )

    hist["despesa_total"]          = hist["despesa_total_viagem"].fillna(0) + hist["despesa_fixa_total"].fillna(0)
    hist["faturamento_viagem_mes"] = hist["lucro_bruto"] - hist["despesa_fixa_total"]
    hist["lucro_liquido"]          = hist["lucro_bruto"] - hist["despesa_fixa_total"]
    hist["ebitda_parcial"]         = hist["lucro_bruto"] - hist["despesa_livre_impostos"]
    hist["margem_lucro_liquido"]   = hist["lucro_liquido"] / hist["soma_fretes"].replace(0, pd.NA)
    hist["rpk"]                    = hist["soma_fretes"] / hist["km_total"].replace(0, pd.NA)
    hist["lucro_liquido_por_km"]   = hist["faturamento_viagem_mes"] / hist["km_total"].replace(0, pd.NA)
    hist["cpk"]                    = hist["despesa_total"] / hist["km_total"].replace(0, pd.NA)

    return hist.fillna(0)

def preparar_df_manutencao_por_veiculo(df_viagem, df_fixas):
    """
    Retorna a quantidade de manutenções por veículo E CATEGORIA.
    """
    # Categorias de manutenção (case insensitive)
    categorias_viagem = ["manutencao", "borracharia", "lavagem"]
    categorias_fixas = ["manutencao", "borracharia", "plano manutencao", "pneu", "lavagem", "mecanico", "filtros", "pneu coberto"]

    # Processa despesas de viagem
    manut_viagem = (
        df_viagem[df_viagem["categoria"].str.lower().isin(categorias_viagem)]
        .groupby(["veiculo", "categoria"])
        .agg(qtd_manutencoes=("categoria", "count"))
        .reset_index()
    )

    # Processa despesas fixas
    manut_fixas = (
        df_fixas[df_fixas["categoria"].str.lower().isin(categorias_fixas)]
        .groupby(["veiculo", "categoria"])
        .agg(qtd_manutencoes=("categoria", "count"))
        .reset_index()
    )

    # Combina os resultados
    return pd.concat([manut_viagem, manut_fixas], ignore_index=True)

def preparar_df_manutencao_ao_longo_do_tempo(df_viagem, df_fixas):
    """
    Retorna a quantidade de manutenções por data, considerando:
    - Despesas de viagem (categorias: MANUTENCAO, BORRACHARIA, LAVAGEM)
    - Despesas fixas (categorias: MANUTENCAO, BORRACHARIA, PLANO MANUTENCAO, PNEU, LAVAGEM, MECANICO)
    """
    # Categorias de manutenção
    categorias_viagem = ["manutencao", "borracharia", "lavagem"]
    categorias_fixas = ["manutencao", "borracharia", "plano manutencao", "pneu", "lavagem", "mecanico", "filtros", "pneu coberto"]

    # Processa despesas de viagem
    manut_viagem = (
        df_viagem[df_viagem["categoria"].str.lower().isin(categorias_viagem)]
        .assign(data=lambda x: pd.to_datetime(x["data"], errors="coerce"))
        .dropna(subset=["data"])
        .groupby(pd.Grouper(key="data", freq="D"))
        .agg(qtd_manut_viagem=("categoria", "count"))
    )

    # Processa despesas fixas
    manut_fixas = (
        df_fixas[df_fixas["categoria"].str.lower().isin(categorias_fixas)]
        .assign(data=lambda x: pd.to_datetime(x["data"], errors="coerce"))
        .dropna(subset=["data"])
        .groupby(pd.Grouper(key="data", freq="D"))
        .agg(qtd_manut_fixas=("categoria", "count"))
    )

    # Combina os resultados
    df_final = (
        pd.concat([manut_viagem, manut_fixas], axis=1)
        .fillna(0)
        .assign(qtd_total=lambda x: x["qtd_manut_viagem"] + x["qtd_manut_fixas"])
        .reset_index()
    )

    return df_final[["data", "qtd_total"]].rename(columns={"qtd_total": "qtd_manutencoes"})

def preparar_df_manutencao_vs_km(df):
    return df.groupby("veiculo").agg(
        valor=("valor", "sum"),
        km_total=("km_total", "sum"),
        qtd_manutencoes=("categoria", "count")
    ).reset_index()

def preparar_df_consumo_km_por_litro(df_viagens):
    """
    Retorna o consumo médio (Km/L) por veículo, baseado nas viagens válidas.
    """
    df_filtrado = df_viagens[
        (df_viagens["km_total"] > 0) & 
        (df_viagens["lts_combustivel"] > 0)
    ].copy()
    
    df_filtrado["km_por_litro"] = (
        df_filtrado["km_total"] 
        / df_filtrado["lts_combustivel"]
    )
    
    return (
        df_filtrado.groupby("veiculo")
        .agg(km_por_litro=("km_por_litro", "mean"))
        .reset_index()
    )

def preparar_df_preco_medio_combustivel(df):
    df_comb = df[df["categoria"].str.contains("COMBUSTIVEL", case=False, na=False)].copy()
    df_comb["data"] = pd.to_datetime(df_comb["data"], errors="coerce")
    df_comb["mes"] = df_comb["data"].dt.to_period("M").dt.to_timestamp()
    df_comb["preco_medio_combustivel"] = df_comb["valor"] / df_comb["lts_combustivel"].replace(0, pd.NA)
    return df_comb.groupby("mes").agg(preco_medio_combustivel=("preco_medio_combustivel", "mean")).reset_index().rename(columns={"mes": "data"})

def preparar_df_custo_combustivel_por_km(df):
    df_comb = df[df["categoria"].str.contains("COMBUSTIVEL", case=False, na=False)].copy()
    return df_comb.groupby("veiculo").agg(
        custo_comb_km=(lambda d: d["valor"].sum() / d["km_abastecimento"].replace(0, pd.NA).sum())
    ).reset_index()
    
def preparar_df_eficiencia_motoristas(df_viagens, df_desp_viagem, df_desp_fixas):
    """
    Cria DataFrame com eficiência operacional (Lucro Líquido/Km) por motorista
    com alocação proporcional de custos fixos por uso do veículo.
    
    Args:
        df_viagens (pd.DataFrame): DataFrame de viagens enriquecido
        df_desp_viagem (pd.DataFrame): Despesas variáveis por viagem
        df_desp_fixas (pd.DataFrame): Despesas fixas por veículo
    
    Returns:
        pd.DataFrame: DataFrame com eficiência operacional por motorista
    """
    
    # Validação das colunas necessárias
    required = ['motorista', 'veiculo', 'frete_ida', 'frete_volta', 'frete_extra', 'km_total']
    if not all(col in df_viagens.columns for col in required):
        missing = [col for col in required if col not in df_viagens.columns]
        raise ValueError(f"Colunas obrigatórias faltando: {missing}")

    # 1. Calcular receita bruta real por motorista
    receita_motorista = (
        df_viagens
        .assign(receita_bruta=lambda x: x['frete_ida'] + x['frete_volta'].fillna(0) + x['frete_extra'].fillna(0))
        .groupby('motorista', as_index=False)
        .agg(receita_bruta=('receita_bruta', 'sum'),
             km_total=('km_total', 'sum'))
    )

    # 2. Calcular custos variáveis por motorista
    custos_variaveis = (
        df_desp_viagem
        .groupby('motorista', as_index=False)
        .agg(custo_variavel=('valor', 'sum'))
    )

    # 3. Calcular custos fixos proporcionais por motorista
    uso_veiculos = (
        df_viagens
        .groupby(['veiculo', 'motorista'])
        .size()
        .reset_index(name='viagens_por_veiculo')
    )

    custos_fixos_proporcionais = (
        df_desp_fixas
        .groupby('veiculo', as_index=False)
        .agg(custo_fixo_total=('valor', 'sum'))
        .merge(uso_veiculos, on='veiculo')
        .assign(custo_fixo_proporcional=lambda x: 
            x['custo_fixo_total'] * x['viagens_por_veiculo'] / x.groupby('veiculo')['viagens_por_veiculo'].transform('sum'))
        .groupby('motorista', as_index=False)
        .agg(custo_fixo=('custo_fixo_proporcional', 'sum'))
    )

    # 4. Consolidar dados
    df_eficiencia = (
        receita_motorista
        .merge(custos_variaveis, on='motorista', how='left')
        .merge(custos_fixos_proporcionais, on='motorista', how='left')
        .fillna({'custo_variavel': 0, 'custo_fixo': 0})
        .assign(
            lucro_liquido=lambda x: x['receita_bruta'] - (x['custo_variavel'] + x['custo_fixo']),
            eficiencia=lambda x: x['lucro_liquido'] / x['km_total'].replace(0, pd.NA)
        )
        .dropna(subset=['eficiencia'])
        .sort_values('eficiencia', ascending=False)
        .round({'eficiencia': 2, 'lucro_liquido': 2})
    )

    return df_eficiencia[['motorista', 'receita_bruta', 'custo_variavel', 'custo_fixo', 'lucro_liquido', 'km_total', 'eficiencia']]
