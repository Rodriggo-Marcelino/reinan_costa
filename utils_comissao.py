import pandas as pd, numpy as np, datetime as dt

CFG = {
    # ─── Parâmetros de consumo ────────────────────────────────────
    "INC_MAX": 0.40,            # +40 % de ganho na média km/L → pontuação 1
    "REC_MAX": 1.50,           # +50 % de ganho em receita/dia → pontuação 1

    # ─── Pesos das dimensões ─────────────────────────────────────
    "W_MEDIA": 0.60,           # 60 % do peso na média km/L
    "W_DIA":   0.40,           # 40 % do peso em receita/dia

    # ─── Penalidade de ociosidade ───────────────────────────────
    "IDLE_NORMAL": 4,          # até 4 dias sem punição
    "IDLE_FULL":   10,         # ≥10 dias = punição máxima
    "MAX_IDLE_PENALTY": 0.30,  # até −30 % na nota

    # ─── Comissão ───────────────────────────────────────────────
    "MAX_COMISSAO": 500.0,     # teto absoluto
    "MIN_COMISSAO": 150.0,     # piso absoluto

    # ─── Janelas e referências ──────────────────────────────────
    "WINDOW_DIAS":     90,     # janela p/ cálculo do histórico
    "METRICA_RECEITA": "lucro_bruto",  # coluna de receita usada
}

# ----------------------------------------------------------------
# helpers
# ----------------------------------------------------------------

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Limita *x* ao intervalo [lo, hi]."""
    return max(lo, min(hi, x))

# ----------------------------------------------------------------
# função principal
# ----------------------------------------------------------------

def calcular_comissao(
    viagem_row: pd.Series,
    df_viagens: pd.DataFrame,
    cfg: dict = CFG,
) -> dict:
    """Calcula comissão sugerida para *viagem_row* considerando histórico.

    A escala é calibrada para que **nota = 0,50** (isto é, comissão ≈ R$ 250)
    quando o motorista repete a própria média histórica (consumo *e* receita/dia).
    """

    vid, placa = viagem_row["id"], viagem_row["veiculo"]
    ida   = pd.to_datetime(viagem_row["data_ida"])
    volta = pd.to_datetime(viagem_row["data_volta"])
    dias_trip = max((volta - ida).days, 1)

    # ─── 1. Histórico da mesma placa ────────────────────────────
    hist_inicio = ida - pd.Timedelta(days=cfg["WINDOW_DIAS"])
    hist = df_viagens.query(
        "veiculo == @placa and data_ida >= @hist_inicio and id != @vid"
    )

    media_ref = hist["media"].mean()
    met = cfg["METRICA_RECEITA"]

    if "dias_viagem" not in hist.columns:
        hist = hist.assign(
            dias_viagem=(hist["data_volta"] - hist["data_ida"]).dt.days.clip(lower=1)
        )

    rec_dia_ref = (hist[met] / hist["dias_viagem"]).median()

    # fallback se não houver histórico suficiente
    if np.isnan(media_ref):
        media_ref = viagem_row["media"]
    if np.isnan(rec_dia_ref):
        rec_dia_ref = viagem_row[met] / dias_trip

    # ─── 2. Pontuações normalizadas (-1 … 1) ─────────────────────
    media_trip = viagem_row["media"]
    perc_inc_med = (media_trip / media_ref) - 1.0
    score_media_norm = _clamp(perc_inc_med / cfg["INC_MAX"], -1.0, 1.0)

    rec_por_dia = viagem_row[met] / dias_trip
    perc_inc_rec = (rec_por_dia / rec_dia_ref) - 1.0
    score_rec_norm = _clamp(perc_inc_rec / (cfg["REC_MAX"] - 1.0), -1.0, 1.0)

    # ─── 3. Penalidade de ociosidade ────────────────────────────
    prev = hist[hist["data_volta"] < ida].sort_values("data_volta").tail(1)
    idle_days = (ida - prev["data_volta"].iloc[0]).days if not prev.empty else 0

    if idle_days <= cfg["IDLE_NORMAL"]:
        idle_pen_frac = 0.0
    else:
        span = max(cfg["IDLE_FULL"] - cfg["IDLE_NORMAL"], 1)
        idle_pen_frac = _clamp((idle_days - cfg["IDLE_NORMAL"]) / span, 0.0, 1.0)

    pen = idle_pen_frac * cfg["MAX_IDLE_PENALTY"]  # 0 → MAX_IDLE_PENALTY

    # ─── 4. Nota final (baseline 0.50) ──────────────────────────
    nota_baseline = 0.50  # média histórica → 50 % da nota
    nota_delta = 0.50 * (
        cfg["W_MEDIA"] * score_media_norm + cfg["W_DIA"] * score_rec_norm
    )
    nota_raw = nota_baseline + nota_delta
    nota = _clamp(nota_raw, 0.0, 1.0) * (1.0 - pen)

    # ─── 5. Comissão (piso / teto) ─────────────────────────────
    com_bruto = round(nota * cfg["MAX_COMISSAO"], 2)
    comissao = max(cfg["MIN_COMISSAO"], min(cfg["MAX_COMISSAO"], com_bruto))

    # ─── 6. Retorno detalhado ──────────────────────────────────
    return {
        "placa": placa,
        "media_trip":   media_trip,
        "media_ref":    media_ref,
        "score_media_norm": score_media_norm,
        "rec_por_dia":  rec_por_dia,
        "rec_dia_ref":  rec_dia_ref,
        "score_rec_norm":  score_rec_norm,
        "idle_days":    idle_days,
        "pen":          pen,
        "nota_final":   nota,
        "comissao":     comissao,
    }