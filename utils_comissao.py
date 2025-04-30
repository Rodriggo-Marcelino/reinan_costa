import pandas as pd, numpy as np, datetime as dt

CFG = {
    "CONS_TOL":         0.92,
    "W_MEDIA":          0.70,
    "W_DIA":            0.30,
    "MAX_IDLE_PENALTY": 0.30,
    "MAX_COMISSAO":     500.0,
    "MIN_COMISSAO":     150.0,
    "WINDOW_DIAS":      90,
    "METRICA_RECEITA":  "lucro_bruto",
    "IDLE_NORMAL":      4,
    "IDLE_FULL":        10
}

def _clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))

def calcular_comissao(viagem_row: pd.Series,
                      df_viagens: pd.DataFrame,
                      cfg: dict = CFG) -> dict:

    vid, placa = viagem_row["id"], viagem_row["veiculo"]
    ida   = pd.to_datetime(viagem_row["data_ida"])
    volta = pd.to_datetime(viagem_row["data_volta"])
    dias_trip = max((volta - ida).days, 1)

    # 1. Histórico do mesmo caminhão
    hist_win_ini = ida - pd.Timedelta(days=cfg["WINDOW_DIAS"])
    hist = df_viagens.query(
        "veiculo == @placa and data_ida >= @hist_win_ini and id != @vid"
    )

    media_ref = hist["media"].mean()
    met = cfg["METRICA_RECEITA"]

    if "dias_viagem" not in hist.columns:
        hist = hist.assign(
            dias_viagem=(hist["data_volta"] - hist["data_ida"]).dt.days.clip(lower=1)
        )

    rec_dia_ref = (hist[met] / hist["dias_viagem"]).median()

    # fallback se sem histórico
    media_ref   = media_ref if not np.isnan(media_ref) else viagem_row["media"]
    rec_dia_ref = rec_dia_ref if not np.isnan(rec_dia_ref) else viagem_row[met] / dias_trip

    # 2. Pontuações
    media_trip  = viagem_row["media"]
    score_media = _clamp(
        (media_trip - media_ref * cfg["CONS_TOL"]) /
        max(media_ref - media_ref * cfg["CONS_TOL"], 1e-6)
    )

    rec_por_dia = viagem_row[met] / dias_trip
    score_dia   = _clamp(rec_por_dia / rec_dia_ref)

    # 3. Ociosidade (nova lógica)
    prev = hist[hist["data_volta"] < ida].sort_values("data_volta").tail(1)
    idle_days = (ida - prev["data_volta"].iloc[0]).days if not prev.empty else 0

    if idle_days <= cfg["IDLE_NORMAL"]:
        pen_frac = 0.0
    else:
        span = max(cfg["IDLE_FULL"] - cfg["IDLE_NORMAL"], 1)
        pen_frac = _clamp((idle_days - cfg["IDLE_NORMAL"]) / span, 0, 1)

    pen = pen_frac * cfg["MAX_IDLE_PENALTY"]   # valor entre 0 e MAX_IDLE_PENALTY

    # 4. Nota final
    nota = (cfg["W_MEDIA"] * score_media + cfg["W_DIA"] * score_dia) * (1 - pen)

    # 5. Comissão com piso e teto
    bruto = nota * cfg["MAX_COMISSAO"]
    comissao = round(
        max(cfg["MIN_COMISSAO"], min(cfg["MAX_COMISSAO"], bruto)), 2
    )

    return {
        "placa": placa,
        "media_trip":   media_trip,
        "media_ref":    media_ref,
        "score_media":  score_media,
        "rec_por_dia":  rec_por_dia,
        "rec_dia_ref":  rec_dia_ref,
        "score_dia":    score_dia,
        "idle_days":    idle_days,
        "pen":          pen,
        "nota_final":   nota,
        "comissao":     comissao,
    }
