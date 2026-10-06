import argparse
import glob
import html
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from centralnovel.audiolivro_config import carregar_config
from centralnovel.scraper import extrair_links_pdf
from centralnovel.texto_capitulo import obter_texto_capitulo
from centralnovel.tts.dividir import dividir_paragrafos
from centralnovel.tts.normalizar import ajustar_final, normalizar
from centralnovel.tts.pool import PoolTTS
from centralnovel.tts.verificar import analisar

URL_NOVEL = "https://centralnovel.com/series/shadow-slave-20260913/"
FINAIS = ["e2a", "ponto"]


def frases_de_teste(quantidade, capitulo):
    todos = extrair_links_pdf(URL_NOVEL)
    cap = next(c for c in todos if int(c["capitulo"]) == capitulo)
    paragrafos = [normalizar(p) for p in obter_texto_capitulo(cap)]
    trechos = dividir_paragrafos([p for p in paragrafos if p])
    candidatos = [t for t in trechos if t["texto"].rstrip().endswith(".") and len(t["texto"]) >= 40]
    passo = max(1, len(candidatos) // quantidade)
    return candidatos[::passo][:quantidade]


def candidatos_do_treino(runs, base, saida, epoca_min):
    lista = [("base", base)]
    for rotulo, run in runs:
        checkpoints = sorted(
            glob.glob(os.path.join(run, "checkpoint_*.pth")),
            key=lambda c: int(os.path.basename(c)[len("checkpoint_"):-len(".pth")]),
        )
        for indice, caminho in enumerate(checkpoints, 1):
            if indice < epoca_min:
                continue
            nome = f"{rotulo}_ep{indice}"
            pasta = os.path.join(saida, "modelos", nome)
            if not os.path.exists(os.path.join(pasta, "model.pth")):
                subprocess.run(
                    [carregar_config()["tts_python"], os.path.join("scripts", "finetune", "exportar.py"),
                     "--checkpoint", caminho, "--base", base, "--saida", pasta],
                    check=True, env=dict(os.environ, PYTHONUTF8="1"), cwd=RAIZ,
                )
            lista.append((nome, pasta))
    return lista


def avaliar_modelo(config, voz_path, nome, pasta_modelo, frases, saida, workers):
    cfg = json.loads(json.dumps(config))
    cfg["xtts_model_dir"] = os.path.abspath(pasta_modelo)
    pasta_audio = os.path.join(saida, "audio", nome)
    os.makedirs(pasta_audio, exist_ok=True)
    jobs, meta = [], {}
    for t in frases:
        base = t["texto"]
        for final in FINAIS:
            id_ = f"{t['id']}_{final}"
            meta[id_] = {"texto_ref": base, "final": final}
            jobs.append({
                "id": id_, "texto": ajustar_final(base, final),
                "saida": os.path.abspath(os.path.join(pasta_audio, f"{id_}.wav")),
                "seed": 9000 + int(t["id"]), "tentativas": 1,
                "qa": {"chars_s_min": 0, "chars_s_max": 999, "silencio_max_s": 999,
                       "duracao_max_s": 999, "energia_min_db": -999, "clipping_max": 1},
            })
    with PoolTTS(cfg, [voz_path], workers=workers, log_dir=os.path.join(saida, "logs", nome)) as pool:
        resultados = pool.gerar(jobs)
        transcricoes = pool.transcrever([(j["id"], j["saida"]) for j in jobs])

    resumo = {}
    for id_, info in meta.items():
        final = info["final"]
        r = resumo.setdefault(final, {"n": 0, "ponto": 0, "pulou": 0, "mudo": 0, "cobertura": 0.0})
        m = resultados[id_]["metricas"]
        ana = analisar(info["texto_ref"], transcricoes[id_])
        r["n"] += 1
        r["ponto"] += "ponto_falado" in ana["motivos"]
        r["pulou"] += bool({"pulou_palavras", "fim_ausente"} & set(ana["motivos"]))
        r["mudo"] += bool(m) and (m["silencio_max_s"] > 1.2 or m["duracao_s"] > 27)
        r["cobertura"] += ana["cobertura"]
        info["transcricao"] = transcricoes[id_]
        info["analise"] = ana
    for r in resumo.values():
        r["cobertura"] = round(r["cobertura"] / r["n"], 3)
    return resumo, meta, [j["saida"] for j in jobs]


def similaridades(config, base, referencias, grupos, saida):
    lista = os.path.join(saida, "grupos.json")
    destino = os.path.join(saida, "similaridade.json")
    with open(lista, "w", encoding="utf-8") as arquivo:
        json.dump(grupos, arquivo)
    subprocess.run(
        [config["tts_python"], os.path.join("scripts", "finetune", "similaridade.py"),
         "--base", base, "--referencias", referencias, "--lista", lista, "--saida", destino],
        check=True, env=dict(os.environ, PYTHONUTF8="1"), cwd=RAIZ,
    )
    with open(destino, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def escrever_html(saida, nomes, frases, ids_exibir):
    linhas = ["<!doctype html><meta charset='utf-8'><title>Avaliacao do fine-tune</title>",
              "<style>body{font-family:sans-serif;max-width:1000px;margin:2em auto;padding:0 1em}"
              ".v{margin:.4em 0}code{color:#555}</style><h1>Mesmas frases, mesma seed</h1>"]
    textos = {t["id"]: t["texto"] for t in frases}
    for id_ in ids_exibir:
        linhas.append(f"<h3>{html.escape(textos[id_])}</h3>")
        for nome in nomes:
            linhas.append(
                f"<div class='v'><b>{nome}</b> <audio controls preload='none' "
                f"src='audio/{nome}/{id_}_e2a.wav'></audio></div>"
            )
    with open(os.path.join(saida, "index.html"), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="append", required=True)
    p.add_argument("--epoca-min", type=int, default=3)
    p.add_argument("--base", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--capitulo", type=int, default=349)
    p.add_argument("--frases", type=int, default=30)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--final", default=os.path.join("audiobook_work", "finetune", "modelo_final"))
    args = p.parse_args()

    os.chdir(RAIZ)
    config = carregar_config()
    voz_path = os.path.join(config["voz_dir"], config["voz_padrao"])
    os.makedirs(args.saida, exist_ok=True)
    frases = frases_de_teste(args.frases, args.capitulo)
    print(f"{len(frases)} frases de teste", flush=True)

    runs = [tuple(item.split("=", 1)) for item in args.run]
    candidatos = candidatos_do_treino(runs, args.base, args.saida, args.epoca_min)
    resumos, grupos = {}, {}
    for nome, pasta in candidatos:
        print(f"avaliando {nome}...", flush=True)
        resumo, meta, wavs = avaliar_modelo(config, voz_path, nome, pasta, frases, args.saida, args.workers)
        resumos[nome] = resumo
        grupos[nome] = [w for w in wavs if w.endswith("_e2a.wav")]
        print(json.dumps(resumo), flush=True)

    sims = similaridades(config, args.base, os.path.join(args.dataset, "wavs"), grupos, args.saida)

    tabela = []
    for nome, pasta in candidatos:
        r = resumos[nome]["e2a"]
        problemas = (r["ponto"] + r["pulou"] + r["mudo"]) / r["n"]
        ponto_com_ponto = resumos[nome]["ponto"]["ponto"] / resumos[nome]["ponto"]["n"]
        tabela.append({
            "modelo": nome, "pasta": pasta, "similaridade": sims[nome]["media"],
            "similaridade_min": sims[nome]["minimo"], "taxa_problemas": round(problemas, 3),
            "taxa_ponto_com_ponto_final": round(ponto_com_ponto, 3), "cobertura": r["cobertura"],
            "detalhe": resumos[nome],
        })
    for linha in tabela:
        linha["pontuacao"] = round(linha["similaridade"] - 0.5 * linha["taxa_problemas"], 4)
    tabela.sort(key=lambda l: -l["pontuacao"])
    with open(os.path.join(args.saida, "resultado.json"), "w", encoding="utf-8") as arquivo:
        json.dump(tabela, arquivo, ensure_ascii=False, indent=1)

    print(f"{'modelo':>10} {'simil':>7} {'min':>7} {'problemas':>10} {'ponto(.)':>9} {'cobert':>7} {'pont.':>7}")
    for l in tabela:
        print(f"{l['modelo']:>10} {l['similaridade']:>7} {l['similaridade_min']:>7} {l['taxa_problemas']:>10} "
              f"{l['taxa_ponto_com_ponto_final']:>9} {l['cobertura']:>7} {l['pontuacao']:>7}")

    melhor = next(l for l in tabela if l["modelo"] != "base")
    base_linha = next(l for l in tabela if l["modelo"] == "base")
    melhor_que_base = (
        melhor["similaridade"] >= base_linha["similaridade"] + 0.01
        and melhor["taxa_problemas"] <= base_linha["taxa_problemas"] + 0.02
    )
    destino = args.final
    if os.path.exists(destino):
        shutil.rmtree(destino)
    shutil.copytree(melhor["pasta"], destino)
    ids = [t["id"] for t in frases[:6]]
    escrever_html(args.saida, [n for n, _ in candidatos], frases, ids)
    decisao = {
        "usar": "modelo_final" if melhor_que_base else "base",
        "pasta": os.path.abspath(destino) if melhor_que_base else os.path.abspath(args.base),
        "melhor_checkpoint": melhor["modelo"],
        "melhor_que_base": melhor_que_base,
    }
    with open(os.path.join(args.saida, "decisao.json"), "w", encoding="utf-8") as arquivo:
        json.dump(decisao, arquivo, ensure_ascii=False, indent=1)
    print(f"MELHOR {melhor['modelo']} -> {os.path.abspath(destino)} | usar: {decisao['usar']}", flush=True)


if __name__ == "__main__":
    main()
