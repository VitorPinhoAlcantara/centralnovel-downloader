from centralnovel.tts.verificar import analisar


def test_transcricao_igual_passa():
    assert analisar("Ele ainda estava perdendo.", "ele ainda estava perdendo.")["ok"]


def test_nome_proprio_diferente_passa():
    assert analisar("Antes que Nephis pudesse alcançá-lo, Sunny a evitou.", "Antes que nefis pudesse alcançá-lo, Sunny a evitou.")["ok"]


def test_ponto_falado_no_fim_reprova():
    r = analisar("Ele ainda estava perdendo.", "ele ainda estava perdendo ponto")
    assert not r["ok"] and "ponto_falado" in r["motivos"]


def test_palavras_puladas_reprova():
    r = analisar("Agora ele finalmente era capaz de igualar Nephis e vencer a luta.", "Agora ele finalmente")
    assert not r["ok"]
    assert "pulou_palavras" in r["motivos"]


def test_numero_em_digitos_equivale_ao_extenso():
    assert analisar("Capítulo trezentos e quarenta e nove: Destino", "Capítulo 349, Destino")["ok"]


def test_frase_curta_tolera_uma_palavra():
    assert analisar("Você não pode. Acabou, Neph.", "Você não pode. Acabou, Nefi.")["ok"]


def test_linha_de_sistema_com_colchetes_e_tolerante():
    ref = "Inimigos Derrotados: [mil, duzentos e treze/seis mil]."
    assert analisar(ref, "Inimigos derrotados, 1.213 sobre 6.000")["ok"]


def test_linha_de_sistema_ainda_acusa_ponto_falado():
    ref = "Memória: [M. Su, ndo]."
    r = analisar(ref, "Memória M Su ndo ponto")
    assert "ponto_falado" in r["motivos"]


def test_frase_comum_continua_exigindo_cobertura():
    r = analisar("Agora ele finalmente era capaz de igualar Nephis e vencer a luta.", "Agora ele finalmente")
    assert not r["ok"]


def test_palavra_parecida_aceita_final_esperado():
    from centralnovel.tts.verificar import tem_palavra_parecida
    assert tem_palavra_parecida("Pedra.", "pedra")
    assert tem_palavra_parecida("Oh!", "pedra") is False
    assert tem_palavra_parecida("", "pedra") is False
