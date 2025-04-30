"""
Módulo de validação de anomalias em dados de viagens e despesas.
Fornece verificações específicas para km, datas, consumo, preço de combustível e valores.
Interface pública principal: `checar_anomalias` (não alterada).
"""

import pandas as pd
from typing import Dict, List, Any

# =============================================
# Constantes de limites de consumo e preço
# =============================================
CONSUMO_MINIMO_KM_L = 1.0  # km/L mínimo esperado
CONSUMO_MAXIMO_KM_L = 3.5  # km/L máximo esperado
PRECO_DIESEL_MINIMO_R_L = 3.0  # R$/L mínimo aceitável
PRECO_DIESEL_MAXIMO_R_L = 8.0  # R$/L máximo aceitável


def gerar_preview_linhas(df: pd.DataFrame, colunas: List[str], max_linhas: int) -> List[str]:
    """
    Gera até `max_linhas` de visualização de `df`, formatando apenas as colunas indicadas.
    Útil para incluir detalhes nos relatórios de anomalias.
    """
    if df.empty:
        return []
    previews: List[str] = []
    for idx in range(min(len(df), max_linhas)):
        linha = df.iloc[idx]
        previews.append(" | ".join(str(linha[col]) for col in colunas))
    return previews


def validar_km_zero(viagens: pd.DataFrame, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Identifica viagens com `km_total` menor ou igual a zero.
    Retorna erro se existir registro inválido.
    """
    mask = viagens["km_total"] <= 0
    if not mask.any():
        return []
    return [{
        "msg": "Viagens com km_total ≤ 0",
        "qtd": int(mask.sum()),
        "nivel": "error",
        "detalhes": gerar_preview_linhas(
            viagens.loc[mask, ["identificador", "km_inicial", "km_final", "km_total"]],
            ["identificador", "km_inicial", "km_final", "km_total"],
            max_linhas
        ),
        "sugestao": "Verificar hodômetro ou digitação de km_total."
    }]


def validar_data_retorno_antes_partida(viagens: pd.DataFrame, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Detecta registros onde `data_volta` é anterior a `data_ida`.
    Indica provável inversão de dia/mês ou erro de lançamento.
    """
    mask = viagens["data_volta"] < viagens["data_ida"]
    if not mask.any():
        return []
    return [{
        "msg": "data_volta anterior a data_ida",
        "qtd": int(mask.sum()),
        "nivel": "error",
        "detalhes": gerar_preview_linhas(
            viagens.loc[mask, ["identificador", "data_ida", "data_volta"]],
            ["identificador", "data_ida", "data_volta"],
            max_linhas
        ),
        "sugestao": "Corrigir data de partida/retorno."
    }]


def validar_consumo_fora_limites(viagens: pd.DataFrame, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Verifica se média km/L está fora dos limites realistas.
    Emite warning para consumo muito baixo ou muito alto.
    """
    avisos: List[Dict[str, Any]] = []
    excesso = viagens["media"] > CONSUMO_MAXIMO_KM_L
    defasagem = viagens["media"] < CONSUMO_MINIMO_KM_L

    if excesso.any():
        avisos.append({
            "msg": f"Média > {CONSUMO_MAXIMO_KM_L} km/L",
            "qtd": int(excesso.sum()),
            "nivel": "warning",
            "detalhes": gerar_preview_linhas(
                viagens.loc[excesso, ["identificador", "media"]],
                ["identificador", "media"],
                max_linhas
            ),
            "sugestao": "Revisar litros abastecidos ou km_total."
        })
    if defasagem.any():
        avisos.append({
            "msg": f"Média < {CONSUMO_MINIMO_KM_L} km/L",
            "qtd": int(defasagem.sum()),
            "nivel": "warning",
            "detalhes": gerar_preview_linhas(
                viagens.loc[defasagem, ["identificador", "media"]],
                ["identificador", "media"],
                max_linhas
            ),
            "sugestao": "Verificar possível erro de abastecimento ou leitura."
        })
    return avisos


def validar_km_sem_combustivel(viagens: pd.DataFrame, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Detecta viagens com km_total positivo mas sem litros de combustível registrados.
    """
    mask = (viagens["km_total"] > 0) & (viagens["lts_combustivel"].fillna(0) == 0)
    if not mask.any():
        return []
    return [{
        "msg": "Km rodado sem litros registrados",
        "qtd": int(mask.sum()),
        "nivel": "warning",
        "detalhes": gerar_preview_linhas(
            viagens.loc[mask, ["identificador", "km_total", "lts_combustivel"]],
            ["identificador", "km_total", "lts_combustivel"],
            max_linhas
        ),
        "sugestao": "Registrar abastecimentos correspondentes."
    }]


def validar_preco_diesel_fora_limites(despesas_viagem: pd.DataFrame, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Avalia se `preco_combustivel` está abaixo ou acima dos limites aceitáveis.
    Gera alertas de info para possíveis valores incorretos.
    """
    avisos: List[Dict[str, Any]] = []
    baixo = despesas_viagem["preco_combustivel"] < PRECO_DIESEL_MINIMO_R_L
    alto = despesas_viagem["preco_combustivel"] > PRECO_DIESEL_MAXIMO_R_L

    if baixo.any():
        avisos.append({
            "msg": f"Diesel < R${PRECO_DIESEL_MINIMO_R_L:.2f}",
            "qtd": int(baixo.sum()),
            "nivel": "info",
            "detalhes": gerar_preview_linhas(
                despesas_viagem.loc[baixo, ["descricao", "data", "preco_combustivel", "id"]],
                ["descricao", "data", "preco_combustivel", "id"],
                max_linhas
            ),
            "sugestao": "Confirmar se é ARLA ou outro produto."
        })
    if alto.any():
        avisos.append({
            "msg": f"Diesel > R${PRECO_DIESEL_MAXIMO_R_L:.2f}",
            "qtd": int(alto.sum()),
            "nivel": "info",
            "detalhes": gerar_preview_linhas(
                despesas_viagem.loc[alto, ["descricao", "data", "preco_combustivel", "id"]],
                ["descricao", "data", "preco_combustivel", "id"],
                max_linhas
            ),
            "sugestao": "Verificar lançamento incorreto."
        })
    return avisos


def validar_valores_nao_positivos(df: pd.DataFrame, nome: str, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Verifica registros em que o campo `valor` é menor ou igual a zero.
    """
    mask = df["valor"] <= 0
    if not mask.any():
        return []
    cols = [c for c in ["descricao", "data", "valor", "id"] if c in df.columns]
    return [{
        "msg": f"Valores ≤ 0 em {nome}",
        "qtd": int(mask.sum()),
        "nivel": "warning",
        "detalhes": gerar_preview_linhas(df.loc[mask, cols], cols, max_linhas),
        "sugestao": "Corrigir sinal ou remover duplicatas."
    }]


def validar_datas_faltantes(df: pd.DataFrame, nome: str, max_linhas: int) -> List[Dict[str, Any]]:
    """
    Detecta registros sem data válida (`NaN`) e que serão ignorados na análise histórica.
    """
    mask = pd.to_datetime(df["data"], errors="coerce").isna()
    if not mask.any():
        return []
    cols = [c for c in ["descricao", "categoria", "valor", "id"] if c in df.columns]
    return [{
        "msg": f"Registros sem data em {nome}",
        "qtd": int(mask.sum()),
        "nivel": "warning",
        "detalhes": gerar_preview_linhas(df.loc[mask, cols], cols, max_linhas),
        "sugestao": "Informar data válida para inclusão em gráficos."
    }]


def checar_anomalias(data: Dict[str, pd.DataFrame], max_linhas: int = 5) -> List[Dict[str, Any]]:
    """
    Interface pública – NÃO MODIFICAR.
    Recebe:
      {
        'viagens': pd.DataFrame,
        'despesas_viagem': pd.DataFrame,
        'despesas_fixas': pd.DataFrame
      }
    Retorna lista de dicionários com mensagens, nível e sugestões.
    """
    viagens_df = data["viagens"].copy()
    despesas_viagem_df = data["despesas_viagem"].copy()
    despesas_fixas_df = data["despesas_fixas"].copy()

    avisos: List[Dict[str, Any]] = []
    avisos.extend(validar_km_zero(viagens_df, max_linhas))
    avisos.extend(validar_data_retorno_antes_partida(viagens_df, max_linhas))
    avisos.extend(validar_consumo_fora_limites(viagens_df, max_linhas))
    avisos.extend(validar_km_sem_combustivel(viagens_df, max_linhas))
    avisos.extend(validar_preco_diesel_fora_limites(despesas_viagem_df, max_linhas))
    avisos.extend(validar_valores_nao_positivos(despesas_viagem_df, "despesas_viagem", max_linhas))
    avisos.extend(validar_valores_nao_positivos(despesas_fixas_df, "despesas_fixas", max_linhas))
    avisos.extend(validar_datas_faltantes(despesas_viagem_df, "despesas_viagem", max_linhas))
    avisos.extend(validar_datas_faltantes(despesas_fixas_df, "despesas_fixas", max_linhas))

    return avisos
