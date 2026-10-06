import argparse
import html
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from centralnovel.audiolivro_config import carregar_config
from centralnovel.tts.dividir import dividir_paragrafos
from centralnovel.tts.montar import montar_capitulo
from centralnovel.tts.normalizar import ajustar_final, normalizar
from centralnovel.tts.pool import PoolTTS

SITUACOES = [
    ("Narração calma", {}, [
        "A sala estava em silêncio. Sunny respirou fundo e olhou para a janela, onde a luz pálida da manhã começava a tocar as paredes de pedra. Havia algo de estranho naquele lugar, como se o próprio ar guardasse segredos antigos.",
    ]),
    ("Ação intensa", {}, [
        "A espada da Estrela da Mudança assobiou pelo ar. Sunny girou, desviou por um fio e contra-atacou. O aço colidiu com o aço, e o choque reverberou em seus ossos. Ele não recuou.",
    ]),
    ("Diálogo com travessão", {}, [
        "— Você não pode fazer isso — disse Nephis, olhando para ele.",
        "— Não agora. Acabou, Neph. Tudo o que queríamos já está feito.",
        "— Então por que ainda está de pé?",
    ]),
    ("Diálogo com aspas, pergunta e exclamação", {}, [
        "“Como você pôde fazer isso com ela?”, gritou o velho policial.",
        "“Cuidado!”, ela berrou. “Atrás de você!”",
    ]),
    ("Interjeições (removidas, como hoje)", {"interjeicoes": "remover"}, [
        "Ha! Ele riu alto, sacudindo a cabeça.",
        "Argh! Ele rosnou, apertando os dentes.",
        "Pft. Sou da periferia, disse o homem.",
        "Shhh! Fale mais baixo, idiota!",
    ]),
    ("Interjeições (mantidas, para o modelo pronunciar)", {"interjeicoes": "manter"}, [
        "Ha! Ele riu alto, sacudindo a cabeça.",
        "Argh! Ele rosnou, apertando os dentes.",
        "Pft. Sou da periferia, disse o homem.",
        "Shhh! Fale mais baixo, idiota!",
        "Ah, tão amargo! Ele fez uma careta.",
        "Hum, constrangedor. Ele queria explicar, mas hesitou.",
    ]),
    ("Nomes próprios e termos", {}, [
        "Sunny e Nephis atravessaram o Pináculo Carmesim, enquanto Cassia e o Fragmento da Meia-Noite, [Intacto], pulsavam com o poder do Feitiço do Pesadelo.",
    ]),
    ("Números e abreviações", {}, [
        "Eram 349 dias e 12 mortos, e ainda restavam 3 sobreviventes. O Sr. Silva e a Dra. Costa chegaram às 7 horas.",
    ]),
    ("Frase longa", {}, [
        "Quando algo no peito de Sunny se quebrou, o encantamento oculto do Fragmento da Meia-Noite entrou em vigor e abriu as comportas de poder para apoiá-lo na última resistência.",
    ]),
    ("Frase curta isolada", {}, [
        "Quase.",
        "Ele ainda estava perdendo.",
    ]),
    ("Ênclise e hífens", {}, [
        "Ele tentou iluminá-la com a tocha, mas a escuridão parecia engolir tudo. Quis dá-lo a ela e disse-lhe que o guarda-chuva era do arco-íris.",
    ]),
]


def montar_job_lista(situacao_idx, nome, opcoes, paragrafos, pausas):
    textos = [normalizar(p, opcoes) for p in paragrafos]
    trechos = dividir_paragrafos([t for t in textos if t],
                                 pausa_frase_ms=pausas["frase"], pausa_paragrafo_ms=pausas["paragrafo"])
    return trechos


def gerar_modelo(config, voz_path, rotulo, pasta_modelo, saida, workers):
    cfg = json.loads(json.dumps(config))
    cfg["xtts_model_dir"] = os.path.abspath(pasta_modelo)
    pausas = cfg["pausas_ms"]
    resultados = {}
    with PoolTTS(cfg, [voz_path], workers=workers, log_dir=os.path.join(saida, "logs", rotulo)) as pool:
        for idx, (nome, opcoes, paragrafos) in enumerate(SITUACOES):
            trechos = montar_job_lista(idx, nome, opcoes, paragrafos, pausas)
            pasta = os.path.join(saida, "trechos", rotulo, f"s{idx:02d}")
            os.makedirs(pasta, exist_ok=True)
            jobs = [
                {"id": t["id"], "texto": ajustar_final(t["texto"], cfg["final_trecho"]),
                 "saida": os.path.abspath(os.path.join(pasta, f"{t['id']}.wav")),
                 "seed": 4000 + idx * 50 + int(t["id"]), "tentativas": 3}
                for t in trechos
            ]
            pool.gerar(jobs)
            wav = os.path.join(saida, "audio", rotulo, f"s{idx:02d}.wav")
            montar_capitulo(trechos, pasta, wav, pausa_inicial_ms=300, pausa_final_ms=400)
            resultados[idx] = {"wav": f"audio/{rotulo}/s{idx:02d}.wav", "trechos": [t["texto"] for t in trechos]}
    return resultados


def escrever_html(saida, rotulos, resultados):
    linhas = ["<!doctype html><meta charset='utf-8'><title>Amostras do modelo</title>",
              "<style>body{font-family:sans-serif;max-width:1000px;margin:2em auto;padding:0 1em}"
              ".v{margin:.5em 0}.t{color:#555;font-size:.9em}h2{margin-top:1.6em}</style>",
              "<h1>Mesmas frases e seeds em cada modelo</h1>"]
    for idx, (nome, opcoes, paragrafos) in enumerate(SITUACOES):
        linhas.append(f"<h2>{idx + 1}. {html.escape(nome)}</h2>")
        for p in paragrafos:
            linhas.append(f"<div class='t'>{html.escape(p)}</div>")
        for rotulo in rotulos:
            wav = resultados[rotulo][idx]["wav"]
            linhas.append(f"<div class='v'><b>{html.escape(rotulo)}</b> "
                          f"<audio controls preload='none' src='{html.escape(wav)}'></audio></div>")
    with open(os.path.join(saida, "index.html"), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modelo", action="append", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--workers", type=int, default=3)
    args = p.parse_args()

    os.chdir(RAIZ)
    config = carregar_config()
    voz_path = os.path.join(config["voz_dir"], config["voz_padrao"])
    os.makedirs(args.saida, exist_ok=True)

    modelos = [tuple(m.split("=", 1)) for m in args.modelo]
    resultados = {}
    for rotulo, pasta in modelos:
        print(f"gerando amostras: {rotulo}", flush=True)
        resultados[rotulo] = gerar_modelo(config, voz_path, rotulo, pasta, args.saida, args.workers)
    escrever_html(args.saida, [r for r, _ in modelos], resultados)
    print("AMOSTRAS_PRONTAS", os.path.abspath(os.path.join(args.saida, "index.html")), flush=True)


if __name__ == "__main__":
    main()
