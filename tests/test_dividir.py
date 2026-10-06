from centralnovel.tts.dividir import TETO_XTTS, dividir_paragrafos


def textos(trechos):
    return [t["texto"] for t in trechos]


def test_ids_sequenciais_e_pausa_de_paragrafo():
    trechos = dividir_paragrafos(
        ["Primeira frase com tamanho suficiente para ficar sozinha no trecho. Segunda frase tambem longa o bastante para isso.", "Outro paragrafo curto."],
        pausa_frase_ms=250, pausa_paragrafo_ms=700,
    )
    assert [t["id"] for t in trechos] == [f"{i:04d}" for i in range(len(trechos))]
    assert trechos[0]["pausa_ms"] == 250
    assert trechos[-1]["pausa_ms"] == 700


def test_abreviacao_nao_divide_frase():
    trechos = dividir_paragrafos(["O Sr. Silva chegou cedo e foi direto para a sala de reunioes no fim do corredor."])
    assert len(trechos) == 1


def test_nenhum_trecho_passa_do_teto():
    longa = ("palavra " * 80).strip() + "."
    for trecho in dividir_paragrafos([longa]):
        assert len(trecho["texto"]) <= TETO_XTTS


def test_fragmento_curto_junta_com_vizinho():
    trechos = dividir_paragrafos(["Agora ele finalmente era capaz de igualar Nephis. Quase."])
    assert len(trechos) == 1


def test_paragrafos_vazios_sao_ignorados():
    assert dividir_paragrafos(["", "   "]) == []
