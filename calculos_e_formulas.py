import pandas as pd
import config

# ============================
# 4. Fórmulas e Indicadores
# ============================

# Verifiquei usando os dados de 2024 inteiro, que são os mais confiaveis no sentido do
# que tenho no Power BI no momento
# obs: "indicador novo" significa que eu não usei ele no Power BI antes, e só tenho como verificar
# manualmente com dados de exemplo ou pelo notion (o que eu não fiz)

#Varificado
def calcular_cpk(df_viagens, despesa_fixa_total):
    custo_variavel = df_viagens["total_despesas_viagem"].sum()
    km_total       = df_viagens["km_total"].sum()
    return (custo_variavel + despesa_fixa_total) / km_total if km_total else 0

# Importante para calcular a eficiencia real da frota, uma vez que o capex é investimento em
# bens de capital, logo não é um custo relacionado diretamente ao funcionamento dela
# não foi verificado, mas também não tem motivo pra dizer que o calculo tá errado
def calcular_cpk_sem_capex(desp_viagem, desp_fixa, km_total):
    try:
        custo_variavel = desp_viagem["valor"].sum()
        custo_fixo = desp_fixa.query("categoria != 'PRESTACAO'")["valor"].sum()  # Exclui CAPEX
        return (custo_variavel + custo_fixo) / km_total
    except ZeroDivisionError:
        return pd.NA

#verificado
def calcular_rpk(receita_total, km_total):
    return receita_total / km_total if km_total else 0

#verificado
def calcular_margem_lucro_liquido(lucro_liquido: float, receita_total: float) -> float:
    """
    Calcula a margem de lucro líquido em porcentagem.
    
    Args:
        lucro_liquido (float): Lucro líquido total.
        receita_total (float): Receita total.
    
    Returns:
        float: Margem de lucro líquido (em %).
    """
    return 0 if receita_total==0 else (lucro_liquido / receita_total) * 100

#verificado
def calcular_margem_por_km(receita_total, custo_total, km_total):
    lucro = receita_total - custo_total
    return lucro / km_total if km_total else 0

# indicador novo 
def calcular_despesa_media_por_viagem(desp_viagem, viagem_completa):
    total_viagens = viagem_completa["id"].nunique()
    return desp_viagem["valor"].sum() / total_viagens if total_viagens else 0

# indicador novo
def calcular_receita_media_por_viagem(viagem_completa):
    total_viagens = viagem_completa["id"].nunique()
    soma_fretes_total = (
        viagem_completa[["frete_ida", "frete_volta", "frete_extra"]]
        .fillna(0).sum(axis=1).sum()
    )
    return soma_fretes_total / total_viagens if total_viagens else 0

# indicador novo
def calcular_custo_combustivel_por_km(desp_viagem, km_total):
    combustivel = desp_viagem[desp_viagem["categoria"].str.contains("COMBUSTIVEL", case=False, na=False)]
    return combustivel["valor"].sum() / km_total if km_total else 0

# Em relação ao dado de média no Power bi, deu 0.02 pontos abaixo, o que está dentro da margem de erro
# inclusive acredito que esse esteja mais preciso que o do Power Bi
# verificado
def calcular_consumo_km_por_litro(df_viagens):
    """
    Calcula a média de consumo (Km/L) para todas as viagens válidas.
    - Viagens válidas: km_total > 0 e lts_combustivel > 0
    """
    df_filtrado = df_viagens[
        (df_viagens["km_total"] > 0) & 
        (df_viagens["lts_combustivel"] > 0)
    ]
    
    df_filtrado = df_filtrado.copy()
    
    df_filtrado["km_por_litro"] = (
        df_filtrado["km_total"] 
        / df_filtrado["lts_combustivel"]
    )
    
    return df_filtrado["km_por_litro"].mean(skipna=True)

#indicador novo
def calcular_custo_pneus_por_km(desp_viagem, km_total):
    pneus = desp_viagem[desp_viagem["categoria"].str.contains("PNEU", case=False, na=False)]
    return pneus["valor"].sum() / km_total if km_total else 0

# Verificado
# Bateu exatamento com o que tenho no outro relatorio
def calcular_custo_manutencao_por_km(desp_viagem, desp_fixa, km_total):
    categorias_viagem = config.CATEGORIAS_MANUTENCAO_VIAGEM_UPPER
    categorias_fixa = config.CATEGORIAS_MANUTENCAO_FIXAS_UPPER
    df_manut_viagem = desp_viagem[desp_viagem["categoria"].str.upper().isin(categorias_viagem)]
    df_manut_fixa = desp_fixa[desp_fixa["categoria"].str.upper().isin(categorias_fixa)]
    total = df_manut_viagem["valor"].sum() + df_manut_fixa["valor"].sum()
    return total / km_total if km_total else 0

# indicador novo
def calcular_frequencia_manutencao(desp_viagem, desp_fixas):
    """
    Calcula a quantidade total de manutenções considerando:
    - Despesas de viagem (MANUTENCAO, BORRACHARIA, PLANO MANUTENCAO)
    - Despesas fixas (MANUTENCAO, BORRACHARIA, PLANO MANUTENCAO, PNEU, LAVAGEM, MECANICO)
    """
    # Categorias de manutenção (case insensitive)
    categorias_viagem = config.CATEGORIAS_MANUTENCAO_VIAGEM
    categorias_fixas = config.CATEGORIAS_MANUTENCAO_FIXAS

    # Filtra despesas de viagem
    manut_viagem = desp_viagem[
        desp_viagem["categoria"].str.lower().isin(categorias_viagem)
    ].shape[0]

    # Filtra despesas fixas
    manut_fixas = desp_fixas[
        desp_fixas["categoria"].str.lower().isin(categorias_fixas)
    ].shape[0]

    return manut_viagem + manut_fixas

# verificado
def calcular_receita_bruta(df):
    return (df["frete_ida"].fillna(0) + df["frete_volta"].fillna(0) + df["frete_extra"].fillna(0)).sum()

def calcular_lucro_bruto(df_viagens, df_desp_viagem):
    """
    Lucro Bruto = Receita Bruta (soma de fretes)
               - Despesas Variáveis (todas as despesas de viagem)
    """
    receita = calcular_receita_bruta(df_viagens)
    custo_var = custo_variavel_total(df_desp_viagem)
    return receita - custo_var

#verificado
def despesa_fixa_total(df):
    return df["valor"].fillna(0).sum()

#verificado
def despesa_livre_impostos(df):
    m = ~df["categoria"].str.upper().isin(["IMPOSTO", "DETRAN"])
    return df.loc[m, "valor"].fillna(0).sum()

# verificado, porém incompleto, o CAPEX inclui outros dados não calculados aqui, mas que
# a base de dados também não disponibiliza, então nos contentaremos com isso por
# agora 
def capex(df):
    return df[df["categoria"].str.upper() == "PRESTACAO"]["valor"].fillna(0).sum()

# fui verificar no notion pois achei importante, essa aqui está on point
# verificada
def custo_manut(df_fixas, df_viagem_desp):
    fixas  = config.CATEGORIAS_MANUTENCAO_FIXAS_UPPER
    viagem = config.CATEGORIAS_MANUTENCAO_VIAGEM_UPPER
    return (
        df_fixas[df_fixas["categoria"].str.upper().isin(fixas)]["valor"].fillna(0).sum()
        + df_viagem_desp[df_viagem_desp["categoria"].str.upper().isin(viagem)]["valor"].fillna(0).sum()
    )
    
# verificado, porem incompleto, Ebitda inclui outros dados não calculados aqui, mas que
# a base de dados não disponibiliza, então nos contetaremos
def calcular_ebitda(lucro_liquido, df_desp_fixa):
    impostos = despesa_fixa_total(df_desp_fixa) - despesa_livre_impostos(df_desp_fixa)
    
    # Juros, Depreciação e Amortização (usando mesma lógica de filtro de categorias)
    # juros = df_desp_fixa[df_desp_fixa["categoria"].str.upper() == "JUROS"]["valor"].sum()
    # depreciacao_amortizacao = capex(df_desp_fixa)  # Assumindo que CAPEX inclui depreciação/amortização
    
    return lucro_liquido + impostos

def calcular_faturamento_por_mes(df_viagens, df_desp_viagem, df_desp_fixa):
    # cópias seguras
    df_v  = df_viagens.copy()
    df_dv = df_desp_viagem.copy()
    df_df = df_desp_fixa.copy()

    df_v["data_ida"] = pd.to_datetime(df_v["data_ida"], errors="coerce")
    df_dv["data"]    = pd.to_datetime(df_dv["data"], errors="coerce")
    df_df["data"]    = pd.to_datetime(df_df["data"], errors="coerce")

    # RECEITA BRUTA por mês
    receita_bruta = (
        df_v.groupby(pd.Grouper(key="data_ida", freq="M"))
            .apply(lambda g: calcular_receita_bruta(g))
            .rename("receita_bruta")
            .reset_index()
            .rename(columns={"data_ida": "data"})   # ← padroniza
    )

    # DESPESA VARIÁVEL por mês
    despesa_var = calcular_custo_variavel_por_mes(df_dv)      # já vem com col. 'data'

    # DESPESA FIXA por mês
    despesa_fixa = (
        df_df.groupby(pd.Grouper(key="data", freq="M"))["valor"]
             .sum()
             .rename("despesa_fixa")
             .reset_index()                                  # col. 'data'
    )

    # MERGE final
    df_merge = (
        receita_bruta
        .merge(despesa_var,  on="data", how="outer")
        .merge(despesa_fixa, on="data", how="outer")
        .fillna(0)
        .sort_values("data")
        .reset_index(drop=True)
    )

    df_merge["lucro_bruto"]   = df_merge["receita_bruta"] - df_merge["despesa_var"]
    df_merge["lucro_liquido"] = df_merge["lucro_bruto"]  - df_merge["despesa_fixa"]

    return df_merge

def calcular_custo_variavel_por_mes(df_desp_viagem: pd.DataFrame) -> pd.DataFrame:
    """
    Soma das despesas variáveis (despesas de viagem) **por mês**.

    Retorna DataFrame com:
    ┌───────────────┬─────────────────────┐
    │ data (month)  │ despesa_variavel    │
    └───────────────┴─────────────────────┘
    """
    if df_desp_viagem.empty:
        return pd.DataFrame(columns=["data", "despesa_var"])

    df = df_desp_viagem.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    return (
        df.groupby(pd.Grouper(key="data", freq="M"))["valor"]
          .sum()
          .rename("despesa_var")          #  <<< nome já padronizado
          .reset_index()
    )

# verificado -> método bem direto
def custo_variavel_total(df_desp_viagem):
    """Soma total das despesas variáveis"""
    return df_desp_viagem['valor'].sum()

#verificado
def gasto_empresa_total(df_viagens):
    """Soma total da coluna gasto_empresa"""
    return df_viagens['gasto_empresa'].sum()

#verificado
def gasto_motorista_total(df_viagens):
    """Soma total da coluna gasto_motorista"""
    return df_viagens['gasto_motorista'].sum()

#verificado
def litros_combustivel_total(df_viagens):
    """Soma total da coluna lts_combustivel"""
    return df_viagens['lts_combustivel'].sum()

#verificado
def troco_total(df_viagens):
    """Soma total da coluna troco_da_viagem"""
    return df_viagens['troco_da_viagem'].sum()

#verificado
def total_viagens(df_viagens):
    """Contagem de viagens únicas"""
    return df_viagens['id'].nunique()

#verificado
def calcular_lucro_liquido(df_viagens, df_desp_viagem, df_desp_fixa):
    """Lucro líquido total usando métodos existentes"""
    return (calcular_receita_bruta(df_viagens) - 
            (custo_variavel_total(df_desp_viagem) + despesa_fixa_total(df_desp_fixa)))
    
# verificado
def km_total(df_viagens):
    """Total de quilômetros rodados (para padronização)"""
    return df_viagens['km_total'].sum()

def calcular_idle_medio(df_viagens: pd.DataFrame) -> float:
    """
    Retorna a média de dias ociosos entre viagens
    (diferença entre volta da viagem N-1 e ida da viagem N)
    para o conjunto filtrado.
    """
    if df_viagens.empty:
        return 0.0

    # ordena por veículo e data de ida
    v = df_viagens.sort_values(["veiculo", "data_ida"]).copy()

    # diferença entre ida atual e volta anterior no mesmo caminhão
    v["idle"] = (
        v["data_ida"] -
        v.groupby("veiculo")["data_volta"].shift()
    ).dt.days.clip(lower=0)           # dias negativos viram 0

    return round(v["idle"].mean(), 1)

def idle_medio_por_veiculo(df_viagens: pd.DataFrame) -> dict:
    """
    Retorna dict {placa: dias_ociosos_médios} para o conjunto filtrado.
    """
    idle_dict = {}
    for placa, grp in (
        df_viagens.sort_values(["veiculo", "data_ida"])
                  .groupby("veiculo")
    ):
        diff = (
            grp["data_ida"] - grp["data_volta"].shift()
        ).dt.days.clip(lower=0)
        idle_dict[placa] = round(diff.mean(), 1) if not diff.empty else 0.0
    return idle_dict