import numpy as np

from centralnovel.tts.montar import TAXA, cortar_em, detectar_rajada_final, recortar


def tom(segundos, amplitude=0.3, freq=220):
    t = np.arange(int(segundos * TAXA)) / TAXA
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silencio(segundos):
    return np.zeros(int(segundos * TAXA), dtype=np.float32)


def test_detecta_rajada_curta_depois_de_silencio_longo():
    wav = np.concatenate([tom(1.0), silencio(1.1), tom(0.1, 0.1), silencio(0.2)])
    r = detectar_rajada_final(wav)
    assert r is not None
    assert abs(r["ini"] - 2.1) < 0.03 and abs(r["fim"] - 2.2) < 0.03
    assert abs(r["corte"] - 1.25) < 0.03


def test_cortar_preserva_a_fala_e_termina_em_fade():
    wav = np.concatenate([tom(1.0), silencio(1.1), tom(0.1, 0.1)])
    r = detectar_rajada_final(wav)
    novo = cortar_em(wav, r["corte"])
    assert abs(len(novo) / TAXA - 1.25) < 0.03
    assert np.array_equal(novo[: int(1.1 * TAXA)], wav[: int(1.1 * TAXA)])
    assert abs(float(novo[-1])) < 1e-3


def test_rajada_proxima_da_fala_nao_e_detectada():
    wav = np.concatenate([tom(1.0), silencio(0.3), tom(0.1, 0.1)])
    assert detectar_rajada_final(wav) is None


def test_trecho_longo_depois_do_silencio_nao_e_rajada():
    wav = np.concatenate([tom(1.0), silencio(1.1), tom(1.5)])
    assert detectar_rajada_final(wav) is None


def test_sem_rajada_ou_audio_vazio():
    assert detectar_rajada_final(np.concatenate([tom(1.0), silencio(0.4)])) is None
    assert detectar_rajada_final(np.zeros(100, dtype=np.float32)) is None
    assert detectar_rajada_final(silencio(2.0)) is None


def test_recortar_inclui_margem():
    wav = np.concatenate([tom(1.0), silencio(1.1), tom(0.1, 0.1)])
    r = detectar_rajada_final(wav)
    clipe = recortar(wav, r["ini"], r["fim"])
    assert 0.2 < len(clipe) / TAXA < 0.5
