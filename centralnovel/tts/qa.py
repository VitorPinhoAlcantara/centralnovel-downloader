import numpy as np

LIMITES_PADRAO = {
    "chars_s_min": 8.0,
    "chars_s_max": 28.0,
    "silencio_max_s": 1.2,
    "duracao_max_s": 27.0,
    "energia_min_db": -45.0,
    "clipping_max": 0.002,
    "chars_curtas_max": 40,
    "curta_base_s": 1.5,
}

_JANELA_S = 0.02
_LIMIAR_SILENCIO_DB = -50.0


def medir(wav, sr, texto):
    wav = np.asarray(wav, dtype=np.float32).reshape(-1)
    duracao = len(wav) / sr if sr else 0.0
    chars = len(texto.strip())
    metricas = {
        "duracao_s": round(duracao, 3),
        "chars": chars,
        "chars_s": round(chars / duracao, 2) if duracao > 0 else 0.0,
        "silencio_max_s": 0.0,
        "energia_db": -120.0,
        "clipping": 0.0,
    }
    if len(wav) == 0:
        return metricas

    metricas["clipping"] = round(float(np.mean(np.abs(wav) >= 0.999)), 5)
    metricas["energia_db"] = round(_db(float(np.sqrt(np.mean(wav ** 2)))), 1)

    janela = max(1, int(sr * _JANELA_S))
    quadros = len(wav) // janela
    if quadros == 0:
        return metricas
    rms = np.sqrt(np.mean(wav[: quadros * janela].reshape(quadros, janela) ** 2, axis=1))
    silencio = _db_array(rms) < _LIMIAR_SILENCIO_DB
    metricas["silencio_max_s"] = round(_maior_silencio_interno(silencio) * _JANELA_S, 2)
    return metricas


def avaliar(metricas, limites=None):
    lim = dict(LIMITES_PADRAO)
    lim.update(limites or {})
    motivos = []
    if metricas["duracao_s"] <= 0.05:
        return False, ["vazio"]
    if metricas["energia_db"] < lim["energia_min_db"]:
        motivos.append("mudo")
    if metricas["duracao_s"] > lim["duracao_max_s"]:
        motivos.append("nao_parou")
    if _esticado(metricas, lim):
        motivos.append("esticado")
    if metricas["chars_s"] > lim["chars_s_max"]:
        motivos.append("cortado")
    if metricas["silencio_max_s"] > lim["silencio_max_s"]:
        motivos.append("silencio_longo")
    if metricas["clipping"] > lim["clipping_max"]:
        motivos.append("clipping")
    return not motivos, motivos


def _esticado(metricas, lim):
    if metricas["chars"] < lim["chars_curtas_max"]:
        return metricas["duracao_s"] > lim["curta_base_s"] + metricas["chars"] / max(lim["chars_s_min"], 1e-6)
    return metricas["chars_s"] < lim["chars_s_min"]


def pontuacao(metricas, limites=None):
    lim = dict(LIMITES_PADRAO)
    lim.update(limites or {})
    _, motivos = avaliar(metricas, lim)
    ponto = float(len(motivos))
    ponto += max(0.0, metricas["silencio_max_s"] - lim["silencio_max_s"]) / 5.0
    centro = (lim["chars_s_min"] + lim["chars_s_max"]) / 2
    ponto += abs(metricas["chars_s"] - centro) / 100.0
    return ponto


def _maior_silencio_interno(silencio):
    indices = np.flatnonzero(~silencio)
    if len(indices) == 0:
        return 0
    miolo = silencio[indices[0]: indices[-1] + 1]
    maior = atual = 0
    for quadro in miolo:
        atual = atual + 1 if quadro else 0
        maior = max(maior, atual)
    return maior


def _db(valor):
    return 20.0 * float(np.log10(max(valor, 1e-6)))


def _db_array(valores):
    return 20.0 * np.log10(np.maximum(valores, 1e-6))
