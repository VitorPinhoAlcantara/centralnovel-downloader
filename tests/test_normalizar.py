from centralnovel.tts.normalizar import ajustar_final, normalizar


def test_hifen_de_enclise_mantido_por_padrao():
    assert normalizar("Ele tentou iluminá-la agora.") == "Ele tentou iluminá-la agora."
    assert normalizar("Ela far-se-á ouvir.") == "Ela far-se-á ouvir."


def test_enclise_colada_opcional():
    assert normalizar("Quis dá-lo e disse-lhe.", {"hifen_pronome": "colar"}) == "Quis dálo e disselhe."
    assert normalizar("Ela far-se-á ouvir.", {"hifen_pronome": "colar"}) == "Ela farseá ouvir."


def test_enclise_com_espaco_opcional():
    assert normalizar("iluminá-la", {"hifen_pronome": "espaco"}) == "iluminá la"


def test_composta_mantida_por_padrao():
    assert normalizar("O guarda-chuva e o arco-íris.") == "O guarda-chuva e o arco-íris."


def test_travessao_mantido_por_padrao():
    assert normalizar("— Você não pode — disse Nephis.") == "— Você não pode — disse Nephis."


def test_travessao_removido_opcional():
    entrada = "— Você não pode — disse Nephis. — Não agora."
    assert normalizar(entrada, {"travessao": "remover"}) == "Você não pode, disse Nephis. Não agora."


def test_travessao_aspas_opcional():
    assert normalizar("— Sim.", {"travessao": "aspas"}) == "“Sim.”"


def test_colchetes_mantidos_por_padrao():
    assert normalizar("o encantamento [Intacto] entrou") == "o encantamento [Intacto] entrou"


def test_numeros_por_extenso():
    assert normalizar("Eram 349 dias.") == "Eram trezentos e quarenta e nove dias."


def test_abreviacoes_expandidas():
    assert normalizar("O Sr. Silva e a Dra. Costa.") == "O Senhor Silva e a Doutora Costa."


def test_reticencias_viram_virgula_antes_de_minuscula():
    assert normalizar("Hesitou… talvez.") == "Hesitou, talvez."


def test_reticencias_antes_de_maiuscula_viram_ponto():
    assert normalizar("Hesitou... Talvez.") == "Hesitou. Talvez."


def test_reticencias_no_inicio_sao_removidas():
    assert normalizar("… Claro, tudo bem.") == "Claro, tudo bem."


def test_ajustar_final_modos():
    assert ajustar_final("Frase.", "ponto") == "Frase."
    assert ajustar_final("Frase.", "sem") == "Frase"
    assert ajustar_final("Frase.", "virgula") == "Frase,"
    assert ajustar_final("Frase.", "espaco") == "Frase ."
    assert ajustar_final("Frase!", "sem") == "Frase!"


def test_interjeicao_no_inicio_e_removida():
    assert normalizar("Ha! Ele riu alto.", {"interjeicoes": "remover"}) == "Ele riu alto."
    assert normalizar("Argh! Ele rosnou.", {"interjeicoes": "remover"}) == "Ele rosnou."
    assert normalizar("Ha, ha, ha, ele riu.", {"interjeicoes": "remover"}) == "ele riu."


def test_interjeicao_sozinha_vira_vazio():
    assert normalizar("Ha!", {"interjeicoes": "remover"}) == ""


def test_interjeicao_no_meio_apos_dois_pontos():
    assert normalizar("Ele disse: Ha! Não.", {"interjeicoes": "remover"}) == "Ele disse: Não."


def test_interjeicao_mantida_por_padrao():
    assert normalizar("Ha! Ele riu.") == "Ha! Ele riu."
    assert normalizar("Argh! Ele rosnou.") == "Argh! Ele rosnou."


def test_palavras_normais_nao_sao_removidas():
    assert normalizar("Há muito tempo, o argumento era claro.") == "Há muito tempo, o argumento era claro."
