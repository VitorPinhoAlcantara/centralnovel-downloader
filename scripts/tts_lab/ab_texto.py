import argparse
import html
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from centralnovel.audiolivro_config import carregar_config
from centralnovel.tts.normalizar import ajustar_final, normalizar
from centralnovel.tts.pool import PoolTTS

CASOS = [
    {
        "nome": "enclise_1",
        "titulo": "Hifen de enclise (iluminá-la)",
        "texto": "Ele tentou iluminá-la com a tocha, mas a escuridão parecia engolir tudo ao redor.",
        "variantes": {
            "hifen_mantido": {"hifen_pronome": "manter"},
            "hifen_colado": {"hifen_pronome": "colar"},
            "hifen_espaco": {"hifen_pronome": "espaco"},
        },
    },
    {
        "nome": "enclise_2",
        "titulo": "Hifen de enclise (dá-lo, disse-lhe)",
        "texto": "Sunny quis dá-lo a ela, mas hesitou, e Nephis disse-lhe que não era preciso.",
        "variantes": {
            "hifen_mantido": {"hifen_pronome": "manter"},
            "hifen_colado": {"hifen_pronome": "colar"},
            "hifen_espaco": {"hifen_pronome": "espaco"},
        },
    },
    {
        "nome": "mesoclise",
        "titulo": "Mesoclise (far-se-á)",
        "texto": "Ela far-se-á ouvir antes do amanhecer, e todos curvar-se-ão diante dela.",
        "variantes": {
            "hifen_mantido": {"hifen_pronome": "manter"},
            "hifen_colado": {"hifen_pronome": "colar"},
            "hifen_espaco": {"hifen_pronome": "espaco"},
        },
    },
    {
        "nome": "composta",
        "titulo": "Palavra composta (guarda-chuva, arco-íris)",
        "texto": "O guarda-chuva e o arco-íris pareciam muito distantes do guarda-roupa abandonado.",
        "variantes": {
            "hifen_mantido": {"hifen_composta": "manter"},
            "hifen_colado": {"hifen_composta": "colar"},
            "hifen_espaco": {"hifen_composta": "espaco"},
        },
    },
    {
        "nome": "dialogo",
        "titulo": "Travessao de dialogo",
        "texto": "— Você não pode fazer isso — disse Nephis, olhando para ele. — Não agora.",
        "variantes": {
            "travessao_mantido": {"travessao": "manter"},
            "travessao_removido": {"travessao": "remover"},
            "travessao_aspas": {"travessao": "aspas"},
        },
    },
    {
        "nome": "onomatopeia",
        "titulo": "Interjecao curta (Ha!)",
        "variantes_texto": {
            "isolada": "Ha!",
            "fundida": "Ha! Ele riu alto, sacudindo a cabeça.",
            "extenso": "Ha ha ha! Ele riu alto, sacudindo a cabeça.",
        },
    },
    {
        "nome": "fragmento",
        "titulo": "Fragmento curto ao fim do paragrafo (Quase.)",
        "variantes_texto": {
            "isolado": "Quase.",
            "fundido": "Agora, ele finalmente era capaz de igualar Nephis... Quase.",
        },
    },
    {
        "nome": "reticencias",
        "titulo": "Reticencias",
        "texto": "Ele hesitou... talvez fosse melhor esperar... mas não havia mais tempo.",
        "variantes": {
            "tres_pontos": {"reticencias": "tres_pontos"},
            "virgula": {"reticencias": "virgula"},
            "manter": {"reticencias": "manter"},
        },
    },
    {
        "nome": "ponto_interno",
        "titulo": "Ponto interno (abreviacao) como no E2A vs normal",
        "texto": "O Sr. Silva e a Dra. Costa chegaram juntos, mas o Prof. Lima já tinha partido.",
        "variantes": {
            "expandido": {"abreviacoes": "expandir"},
            "ponto_mantido": {"abreviacoes": "manter", "ponto_interno": "normal"},
            "e2a": {"abreviacoes": "manter", "ponto_interno": "e2a"},
        },
    },
    {
        "nome": "colchetes",
        "titulo": "Colchetes ([Intacto])",
        "texto": "O encantamento oculto do Fragmento da Meia-Noite, [Intacto], entrou em vigor.",
        "variantes": {
            "colchetes_removidos": {"colchetes": "remover"},
            "colchetes_mantidos": {"colchetes": "manter"},
            "colchetes_aspas": {"colchetes": "aspas"},
        },
    },
    {
        "nome": "numero",
        "titulo": "Numeros",
        "texto": "Eram 349 dias e 12 mortos, e ainda restavam 3 sobreviventes.",
        "variantes": {
            "extenso": {"numeros": "extenso"},
            "digitos": {"numeros": "manter"},
        },
    },
    {
        "nome": "longa",
        "titulo": "Frase longa (~190 caracteres)",
        "texto": "Quando algo no peito de Sunny se quebrou, o encantamento oculto do Fragmento da Meia-Noite entrou em vigor e abriu as comportas de poder para apoiá-lo na última resistência.",
        "variantes": {
            "inteira": {},
        },
    },
    {
        "nome": "referencia",
        "titulo": "Tamanho da referencia de voz (gpt_cond_len 6 vs 30)",
        "texto": "Pela primeira vez desde o início da luta brutal, Sunny não cambaleou por causa do violento choque que reverberava em seus ossos.",
        "variantes": {
            "ref_6s": {"__ref": {"gpt_cond_len": 6}},
            "ref_30s": {"__ref": {"gpt_cond_len": 30}},
        },
    },
]

FINAIS = {
    "ponto": {"__final": "ponto"},
    "sem_ponto": {"__final": "sem"},
    "virgula": {"__final": "virgula"},
    "espaco_ponto": {"__final": "espaco"},
    "e2a_ponto_virgula": {"__final": "e2a"},
    "ponto_quebra": {"__final": "ponto_nl"},
}

CASOS_RODADA2 = [
    {
        "nome": "final_curta",
        "titulo": "Final de frase curta",
        "texto": "Ele ainda estava perdendo.",
        "variantes": FINAIS,
    },
    {
        "nome": "final_media",
        "titulo": "Final de frase media",
        "texto": "Agora, ele havia atingido o absoluto auge de seu potencial de poder.",
        "variantes": FINAIS,
    },
    {
        "nome": "final_longa",
        "titulo": "Final de frase longa",
        "texto": "Pela primeira vez desde o início da luta brutal, Sunny não cambaleou por causa do violento choque que reverberava em seus ossos.",
        "variantes": FINAIS,
    },
    {
        "nome": "final_fragmento",
        "titulo": "Fragmento curto ao fim (Quase.)",
        "texto": "Agora, ele finalmente era capaz de igualar Nephis... Quase.",
        "variantes": FINAIS,
    },
    {
        "nome": "ha_interjeicao",
        "titulo": "Interjeicao (Ha!)",
        "variantes_texto": {
            "ha_exclamacao": "Ha! Ele riu alto, sacudindo a cabeça.",
            "ra_exclamacao": "Rá! Ele riu alto, sacudindo a cabeça.",
            "ha_virgula": "Ha, ele riu alto, sacudindo a cabeça.",
            "ha_ha_virgula": "Ha, ha, ha, ele riu alto, sacudindo a cabeça.",
            "ele_riu_direto": "Ele riu alto, sacudindo a cabeça.",
            "gargalhou": "Ele gargalhou alto, sacudindo a cabeça.",
        },
    },
    {
        "nome": "argh_interjeicao",
        "titulo": "Interjeicao (Argh!)",
        "variantes_texto": {
            "argh_exclamacao": "Argh! Ele rosnou, apertando os dentes.",
            "arg_exclamacao": "Arg! Ele rosnou, apertando os dentes.",
            "argh_virgula": "Argh, ele rosnou, apertando os dentes.",
            "ele_rosnou_direto": "Ele rosnou, apertando os dentes.",
        },
    },
]


def montar_itens(casos):
    itens = []
    for indice, caso in enumerate(casos):
        seed = 5000 + indice * 100
        if "variantes_texto" in caso:
            for nome, texto in caso["variantes_texto"].items():
                itens.append({"caso": caso["nome"], "variante": nome, "bruto": texto,
                              "texto": normalizar(texto), "seed": seed, "ref": None})
            continue
        for nome, opcoes in caso["variantes"].items():
            opcoes = dict(opcoes)
            ref = opcoes.pop("__ref", None)
            final = opcoes.pop("__final", "ponto")
            itens.append({"caso": caso["nome"], "variante": nome, "bruto": caso["texto"],
                          "texto": ajustar_final(normalizar(caso["texto"], opcoes), final),
                          "seed": seed, "ref": ref})
    return itens


def gerar(config, voz_path, itens, pasta, workers=1):
    grupos = {}
    for item in itens:
        chave = json.dumps(item["ref"], sort_keys=True)
        grupos.setdefault(chave, []).append(item)

    for chave, grupo in grupos.items():
        cfg = json.loads(json.dumps(config))
        if grupo[0]["ref"]:
            cfg["xtts_ref"].update(grupo[0]["ref"])
        jobs = []
        for item in grupo:
            nome = f"{item['caso']}__{item['variante']}.wav"
            item["arquivo"] = nome
            jobs.append({"id": nome, "texto": item["texto"],
                         "saida": os.path.abspath(os.path.join(pasta, nome)),
                         "seed": item["seed"], "tentativas": 1,
                         "qa": {"chars_s_min": 0, "chars_s_max": 999, "silencio_max_s": 999,
                                "duracao_max_s": 999, "energia_min_db": -999, "clipping_max": 1}})
        with PoolTTS(cfg, [voz_path], workers=workers, log_dir=os.path.join(pasta, "logs")) as pool:
            resultados = pool.gerar(jobs)
        for item in grupo:
            item["metricas"] = resultados[item["arquivo"]]["metricas"]


def escrever_html(casos, itens, pasta):
    por_caso = {}
    for item in itens:
        por_caso.setdefault(item["caso"], []).append(item)
    linhas = ["<!doctype html><meta charset='utf-8'><title>A/B de texto</title>",
              "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto;padding:0 1em}"
              "h2{margin-top:2em}.v{margin:.8em 0;padding:.6em;border:1px solid #ccc;border-radius:6px}"
              "code{display:block;white-space:pre-wrap;color:#555}</style>",
              "<h1>A/B de texto (mesma seed, so o texto muda)</h1>"]
    for caso in casos:
        linhas.append(f"<h2>{html.escape(caso['titulo'])}</h2>")
        for item in por_caso.get(caso["nome"], []):
            m = item.get("metricas", {})
            linhas.append(
                f"<div class='v'><b>{html.escape(item['variante'])}</b> "
                f"<small>({m.get('duracao_s', 0)}s, {m.get('chars_s', 0)} chars/s, "
                f"silencio max {m.get('silencio_max_s', 0)}s)</small>"
                f"<code>{html.escape(item['texto'])}</code>"
                f"<audio controls preload='none' src='{html.escape(item['arquivo'])}'></audio></div>"
            )
    caminho = os.path.join(pasta, "index.html")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))
    return caminho


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--voz", default=None)
    p.add_argument("--saida", default=None)
    p.add_argument("--rodada", type=int, default=1)
    args = p.parse_args()
    casos = CASOS_RODADA2 if args.rodada == 2 else CASOS
    args.saida = args.saida or os.path.join("scripts", "tts_lab", "ab" if args.rodada == 1 else "ab2")

    os.chdir(RAIZ)
    config = carregar_config()
    voz_path = os.path.join(config["voz_dir"], args.voz or config["voz_padrao"])
    os.makedirs(args.saida, exist_ok=True)

    itens = montar_itens(casos)
    print(f"{len(itens)} variantes em {len(casos)} casos")
    inicio = time.time()
    gerar(config, voz_path, itens, args.saida)
    caminho = escrever_html(casos, itens, args.saida)
    with open(os.path.join(args.saida, "itens.json"), "w", encoding="utf-8") as arquivo:
        json.dump(itens, arquivo, ensure_ascii=False, indent=1)
    print(f"pronto em {time.time() - inicio:.0f}s: {os.path.abspath(caminho)}")


if __name__ == "__main__":
    main()
