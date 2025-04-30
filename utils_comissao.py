"""
Módulo de cálculo de comissão de motoristas baseado em desempenho, receita e ociosidade.
Interface pública principal: `calcular_comissao` (não deve ser alterada).
"""
import pandas as pd
import numpy as np
from typing import Any, Tuple, Dict

# =============================================
# Configurações padrão de comissão
# =============================================
DEFAULT_CONFIG = {
    "INCREMENTO_CONSUMO_MAXIMO": 0.30,   # +40% → score_consumo = 1
    "INCREMENTO_RECEITA_MAXIMO": 1.30,   # +50% → score_receita = 1

    "PESO_CONSUMO": 0.70,                # peso do consumo no cálculo final
    "PESO_RECEITA": 0.30,                # peso da receita no cálculo final

    "DIAS_OCIOSIDADE_NORMAL": 4,         # dias sem penalidade
    "DIAS_OCIOSIDADE_PLENO": 10,         # dias para penalidade máxima
    "PENALIDADE_OCIOSIDADE_MAX": 0.30,   # até -30% na nota final

    "COMISSAO_MAXIMA": 500.00,
    "COMISSAO_MINIMA": 150.00,

    "JANELA_HISTORICO_DIAS": 90,
    "COLUNA_RECEITA": "lucro_bruto",
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Limita `value` ao intervalo [minimum, maximum]."""
    return max(minimum, min(value, maximum))


def _extrair_historico(
    df_viagens: pd.DataFrame,
    placa: str,
    inicio: pd.Timestamp,
    janela_dias: int,
    id_atual: Any,
) -> pd.DataFrame:
    """Retorna histórico de viagens da mesma `placa` na janela antes de `inicio`, excluindo `id_atual`."""
    data_inicio = inicio - pd.Timedelta(days=janela_dias)
    return df_viagens.query(
        "veiculo == @placa and data_ida >= @data_inicio and id != @id_atual"
    ).copy()


def _calcular_referencias(
    hist_df: pd.DataFrame,
    row: pd.Series,
    cfg: dict,
) -> Tuple[float, float]:
    """Retorna média histórica de consumo e mediana de receita diária como referência."""
    media_consumo_ref = hist_df["media"].mean()
    # calcula dias de viagem histórico
    if "dias_viagem" not in hist_df.columns:
        hist_df = hist_df.assign(
            dias_viagem=(
                pd.to_datetime(hist_df["data_volta"]) - pd.to_datetime(hist_df["data_ida"])
            ).dt.days.clip(lower=1)
        )
    # mediana da receita por dia
    receita_col = cfg["COLUNA_RECEITA"]
    receita_diaria_ref = (hist_df[receita_col] / hist_df["dias_viagem"]).median()

    # fallback sem histórico
    if np.isnan(media_consumo_ref):
        media_consumo_ref = row["media"]
    dias = max((pd.to_datetime(row["data_volta"]) - pd.to_datetime(row["data_ida"])).days, 1)
    if np.isnan(receita_diaria_ref):
        receita_diaria_ref = row[receita_col] / dias

    return media_consumo_ref, receita_diaria_ref


def _pontuar_consumo(
    media_trip: float,
    media_ref: float,
    incremento_max: float,
) -> float:
    """Normaliza variação de consumo em [-1,1]."""
    variacao = media_trip / media_ref - 1.0
    return _clamp(variacao / incremento_max, -1.0, 1.0)


def _pontuar_receita(
    receita_trip: float,
    receita_ref: float,
    incremento_max: float,
) -> float:
    """Normaliza variação de receita diária em [-1,1]."""
    variacao = receita_trip / receita_ref - 1.0
    return _clamp(variacao / (incremento_max - 1.0), -1.0, 1.0)


def _obter_dias_ociosos(
    hist_df: pd.DataFrame,
    data_ida: pd.Timestamp,
) -> int:
    """Retorna número de dias desde último `data_volta` antes de `data_ida`."""
    antes = hist_df[hist_df["data_volta"] < data_ida]
    if antes.empty:
        return 0
    ultimo = antes.sort_values("data_volta").iloc[-1]["data_volta"]
    return (data_ida - pd.to_datetime(ultimo)).days


def _calcular_penalidade_ociosidade(
    dias_ociosos: int,
    normal: int,
    pleno: int,
    penalidade_max: float,
) -> float:
    """Calcula penalidade baseada em `dias_ociosos` comparado a limites."""
    if dias_ociosos <= normal:
        return 0.0
    span = max(pleno - normal, 1)
    frac = (dias_ociosos - normal) / span
    return _clamp(frac, 0.0, 1.0) * penalidade_max


def calcular_comissao(
    viagem_row: pd.Series,
    df_viagens: pd.DataFrame,
    cfg: dict = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """
    Interface pública – NÃO MODIFICAR.
    Calcula comissão para `viagem_row` com base em consumo, receita e ociosidade.
    """
    placa = viagem_row["veiculo"]
    id_atual = viagem_row["id"]
    data_ida = pd.to_datetime(viagem_row["data_ida"])
    data_volta = pd.to_datetime(viagem_row["data_volta"])
    dias_atual = max((data_volta - data_ida).days, 1)

    # histórico e referências
    historico = _extrair_historico(
        df_viagens, placa, data_ida, cfg["JANELA_HISTORICO_DIAS"], id_atual
    )
    media_ref, receita_ref = _calcular_referencias(historico, viagem_row, cfg)

    # desempenho atual
    media_trip = viagem_row["media"]
    receita_por_dia = viagem_row[cfg["COLUNA_RECEITA"]] / dias_atual
    score_consumo = _pontuar_consumo(media_trip, media_ref, cfg["INCREMENTO_CONSUMO_MAXIMO"])
    score_receita = _pontuar_receita(receita_por_dia, receita_ref, cfg["INCREMENTO_RECEITA_MAXIMO"])

    # ociosidade
    dias_ociosos = _obter_dias_ociosos(historico, data_ida)
    penalidade = _calcular_penalidade_ociosidade(
        dias_ociosos,
        cfg["DIAS_OCIOSIDADE_NORMAL"],
        cfg["DIAS_OCIOSIDADE_PLENO"],
        cfg["PENALIDADE_OCIOSIDADE_MAX"],
    )

    # nota final e comissão
    baseline = 0.50
    delta = 0.50 * (cfg["PESO_CONSUMO"] * score_consumo + cfg["PESO_RECEITA"] * score_receita)
    nota_bruta = baseline + delta
    nota_final = _clamp(nota_bruta, 0.0, 1.0) * (1.0 - penalidade)

    valor_bruto = round(nota_final * cfg["COMISSAO_MAXIMA"], 2)
    comissao = _clamp(valor_bruto, cfg["COMISSAO_MINIMA"], cfg["COMISSAO_MAXIMA"])

    return {
        "placa": placa,
        "media_trip": media_trip,
        "media_ref": media_ref,
        "score_consumo": score_consumo,
        "receita_por_dia": receita_por_dia,
        "receita_ref": receita_ref,
        "score_receita": score_receita,
        "dias_ociosos": dias_ociosos,
        "penalidade_ociosidade": penalidade,
        "nota_final": nota_final,
        "comissao": comissao,
    }
