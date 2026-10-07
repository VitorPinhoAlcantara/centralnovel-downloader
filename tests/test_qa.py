from centralnovel.tts.qa import avaliar


def m(chars, duracao, silencio=0.0, energia=-20.0):
    return {"duracao_s": duracao, "chars": chars, "chars_s": round(chars / duracao, 2),
            "silencio_max_s": silencio, "energia_db": energia, "clipping": 0.0}


def test_frases_curtas_reais_nao_sao_esticadas():
    assert avaliar(m(6, 1.109))[0]
    assert avaliar(m(4, 0.832))[0]
    assert avaliar(m(10, 1.856, 0.94))[0]
    assert avaliar(m(20, 3.435, 0.88))[0]
    assert avaliar(m(22, 3.381, 0.96))[0]


def test_frase_curta_realmente_esticada_reprova():
    ok, motivos = avaliar(m(6, 6.0))
    assert not ok and "esticado" in motivos


def test_frase_normal_lenta_demais_continua_reprovando():
    ok, motivos = avaliar(m(120, 18.0))
    assert not ok and "esticado" in motivos


def test_frase_normal_ok_passa():
    assert avaliar(m(120, 7.5))[0]


def test_silencio_longo_continua_reprovando():
    ok, motivos = avaliar(m(80, 12.0, silencio=2.0))
    assert not ok and "silencio_longo" in motivos


def test_limite_zerado_nao_quebra():
    ok, motivos = avaliar(m(6, 1.0), {"chars_s_min": 0})
    assert ok
