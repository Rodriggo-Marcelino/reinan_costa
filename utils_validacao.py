import pandas as pd, numpy as np, datetime as dt

LIM_CONSUMO = (1.0, 3.5)      # km / L
LIM_DIESEL  = (3.0, 8.0)      # R$/L

# ────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────
def _sample_rows(df, cols, n=5):
    """Retorna uma lista curta de tuplas-string para exibir no alerta."""
    if df.empty:
        return []
    return [
        " | ".join(str(df.iloc[i][c]) for c in cols)
        for i in range(min(n, len(df)))
    ]

def checar_anomalias(data, max_rows=5):
    """
    Recebe o dict {'viagens', 'despesas_viagem', 'despesas_fixas'}
    devolve lista de avisos:
      {msg, qtd, nivel, detalhes, sugestao}
    """
    v  = data["viagens"].copy()
    dv = data["despesas_viagem"].copy()
    df = data["despesas_fixas"].copy()
    avisos = []

    # 1. km_total ≤ 0
    mask = v["km_total"] <= 0
    if mask.any():
        avisos.append({
            "msg":    "Viagens com km_total ≤ 0",
            "qtd":    int(mask.sum()),
            "nivel":  "error",
            "detalhes": _sample_rows(
                v.loc[mask, ["identificador", "km_inicial", "km_final", "km_total"]],
                ["identificador", "km_inicial", "km_final", "km_total"],
                max_rows
            ),
            "sugestao": "Conferir leitura do hodômetro ou digitação do campo km_total."
        })

    # 2. Volta antes da ida
    mask = v["data_volta"] < v["data_ida"]
    if mask.any():
        avisos.append({
            "msg":   "data_volta anterior à data_ida",
            "qtd":   int(mask.sum()),
            "nivel": "error",
            "detalhes": _sample_rows(
                v.loc[mask, ["identificador", "data_ida", "data_volta"]],
                ["identificador", "data_ida", "data_volta"],
                max_rows
            ),
            "sugestao": "Verificar data de lançamento; corrigir inversão de dia/mês."
        })

    # 3. Consumo fora da faixa
    mask_hi = v["media"] > LIM_CONSUMO[1]
    mask_lo = v["media"] < LIM_CONSUMO[0]
    if mask_hi.any():
        avisos.append({
            "msg":  f"Média > {LIM_CONSUMO[1]} km/L",
            "qtd":  int(mask_hi.sum()),
            "nivel": "warning",
            "detalhes": _sample_rows(
                v.loc[mask_hi, ["identificador", "media"]],
                ["identificador", "media"],
                max_rows
            ),
            "sugestao": "Rever litros abastecidos ou km_total; valores altos indicam erro."
        })
    if mask_lo.any():
        avisos.append({
            "msg":  f"Média < {LIM_CONSUMO[0]} km/L",
            "qtd":  int(mask_lo.sum()),
            "nivel": "warning",
            "detalhes": _sample_rows(
                v.loc[mask_lo, ["identificador", "media"]],
                ["identificador", "media"],
                max_rows
            ),
            "sugestao": "Checar possível erro de abastecimento parcial ou falha de leitura."
        })

    # 4. Km>0 sem litros
    mask = (v["km_total"] > 0) & (v["lts_combustivel"].fillna(0) == 0)
    if mask.any():
        avisos.append({
            "msg":  "Km rodado sem litros registrados",
            "qtd":  int(mask.sum()),
            "nivel": "warning",
            "detalhes": _sample_rows(
                v.loc[mask, ["identificador", "km_total", "lts_combustivel"]],
                ["identificador", "km_total", "lts_combustivel"],
                max_rows
            ),
            "sugestao": "Registrar abastecimentos correspondentes."
        })

    # 5. Diesel fora da faixa
    mask_low  = dv["preco_combustivel"].between(0, LIM_DIESEL[0], inclusive="left")
    mask_high = dv["preco_combustivel"] > LIM_DIESEL[1]
    if mask_low.any():
        avisos.append({
            "msg":  f"Diesel < R${LIM_DIESEL[0]:.0f}",
            "qtd":  int(mask_low.sum()),
            "nivel": "info",
            "detalhes": _sample_rows(
                dv.loc[mask_low, ["descricao", "data", "preco_combustivel","id"]],
                ["descricao", "data", "preco_combustivel","id"],
                max_rows
            ),
            "sugestao": "Confirmar se o valor inclui desconto ou se foi lançado em outra moeda."
        })
    if mask_high.any():
        avisos.append({
            "msg":  f"Diesel > R${LIM_DIESEL[1]:.0f}",
            "qtd":  int(mask_high.sum()),
            "nivel": "info",
            "detalhes": _sample_rows(
                dv.loc[mask_high, ["descricao", "data", "preco_combustivel", "id"]],
                ["descricao", "data", "preco_combustivel", "id"],
                max_rows
            ),
            "sugestao": "Verificar se o lançamento é ARLA ou outro produto, não diesel."
        })

    # 6. Valores ≤ 0
    for nome, df_ in [("despesas_viagem", dv), ("despesas_fixas", df)]:
        mask = df_["valor"] <= 0
        if mask.any():
            avisos.append({
                "msg":      f"Valores ≤ 0 em {nome}",
                "qtd":      int(mask.sum()),
                "nivel":    "warning",
                "detalhes": _sample_rows(
                    df_.loc[mask, ["descricao","data", "valor", "id"]],
                    ["descricao","data", "valor", "id"],
                    max_rows
                ),
                "sugestao": "Corrigir sinal (→ positivo) ou remover teste/digitação duplicada."
            })

    return avisos