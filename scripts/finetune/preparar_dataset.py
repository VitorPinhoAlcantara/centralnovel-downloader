import argparse
import glob
import json
import os
import random
import shutil
import re
import sys
import time

import numpy as np
import soundfile as sf

TAXA = 24000
JANELA_S = 0.02
PAUSA_MIN_S = 0.25
CLIPE_MIN_S = 3.8
CLIPE_ALVO_S = 10.0
CLIPE_MAX_S = 11.0
PULAR_INICIO_S = 6.0
PULAR_FIM_S = 12.0
PALAVRAS_PROIBIDAS = (
    "inscrev", "canal", "youtube", "like", "curt", "patreon", "apoia", "link na descri", "descrição",
    "obrigado por assistir", "sino", "notifica", "comentário", "comente", "compartilh", "legenda",
)


FORTES = re.compile(
    r"(?<![A-Za-zÀ-ÿ])(ha(?:ha)*h?|h[ae]h[ae]*|hee+|rá(?:[- ]?rá)*|a{1,3}rg+h*|ugh+|gr{2,}h*|h?m{2,}|hm+|hum+"
    r"|uh+m*|tsc|pf+t*|shh+|k{3,})(?![A-Za-zÀ-ÿ])[!?.,…]",
    re.IGNORECASE,
)
FRACAS = re.compile(
    r"(?<![A-Za-zÀ-ÿ])(ah+|oh+|ei|eh+|opa|ops|ufa)(?![A-Za-zÀ-ÿ])[!?.,…]", re.IGNORECASE
)


def db(x):
    return 20.0 * np.log10(np.maximum(x, 1e-6))


def quadros_db(wav):
    n = int(TAXA * JANELA_S)
    q = len(wav) // n
    rms = np.sqrt(np.mean(wav[: q * n].reshape(q, n) ** 2, axis=1))
    return db(rms)


def segmentar(wav):
    nivel = quadros_db(wav)
    piso = float(np.percentile(nivel, 5))
    limiar = max(piso + 10.0, -52.0)
    fala = nivel > limiar
    pausa_q = int(PAUSA_MIN_S / JANELA_S)

    segmentos = []
    i, n = 0, len(fala)
    inicio = None
    silencio = 0
    for k in range(n):
        if fala[k]:
            if inicio is None:
                inicio = k
            silencio = 0
        elif inicio is not None:
            silencio += 1
            if silencio >= pausa_q:
                segmentos.append((inicio, k - silencio + 1))
                inicio, silencio = None, 0
    if inicio is not None:
        segmentos.append((inicio, n))
    return segmentos, nivel, piso


def dividir_longo(inicio, fim, nivel):
    pedacos = []
    while (fim - inicio) * JANELA_S > CLIPE_MAX_S - 0.8:
        a = inicio + int(4.0 / JANELA_S)
        b = inicio + int((CLIPE_ALVO_S - 0.5) / JANELA_S)
        corte = a + int(np.argmin(nivel[a:b]))
        pedacos.append((inicio, corte))
        inicio = corte
    pedacos.append((inicio, fim))
    return pedacos


def montar_clipes(wav):
    segmentos, nivel, piso = segmentar(wav)
    expandidos = []
    for ini, fim in segmentos:
        if (fim - ini) * JANELA_S > CLIPE_MAX_S - 0.8:
            expandidos.extend(dividir_longo(ini, fim, nivel))
        else:
            expandidos.append((ini, fim))

    clipes = []
    atual = None
    for ini, fim in expandidos:
        if atual is None:
            atual = [ini, fim]
        elif (fim - atual[0]) * JANELA_S <= CLIPE_ALVO_S:
            atual[1] = fim
        else:
            clipes.append(tuple(atual))
            atual = [ini, fim]
    if atual is not None:
        clipes.append(tuple(atual))

    resultado = []
    limite = len(wav)
    for idx, (ini, fim) in enumerate(clipes):
        ant = clipes[idx - 1][1] if idx > 0 else 0
        prox = clipes[idx + 1][0] if idx + 1 < len(clipes) else int(limite / (TAXA * JANELA_S))
        folga_ini = min(int(0.15 / JANELA_S), max(0, (ini - ant) // 2))
        folga_fim = min(int(0.20 / JANELA_S), max(0, (prox - fim) // 2))
        a = int((ini - folga_ini) * JANELA_S * TAXA)
        b = int((fim + folga_fim) * JANELA_S * TAXA)
        a, b = max(0, a), min(limite, b)
        dur = (b - a) / TAXA
        if CLIPE_MIN_S <= dur <= CLIPE_MAX_S:
            resultado.append((a, b))
    return resultado, piso


def carregar_whisper(modelo, dispositivo):
    import torch
    from transformers import pipeline

    return pipeline(
        "automatic-speech-recognition",
        model=modelo,
        device=dispositivo,
        dtype=torch.float16,
    )


def transcrever(pipe, clipes, batch):
    entradas = [{"raw": c, "sampling_rate": TAXA} for c in clipes]
    saidas = pipe(
        entradas,
        batch_size=batch,
        generate_kwargs={"language": "portuguese", "task": "transcribe", "num_beams": 1},
    )
    return [s["text"].strip() for s in saidas]


def texto_valido(texto):
    if not texto or len(texto) > 200:
        return False
    baixo = texto.lower()
    if any(p in baixo for p in PALAVRAS_PROIBIDAS):
        return False
    palavras = re.findall(r"\w+", baixo)
    if len(palavras) < 4:
        return False
    for n in (2, 3):
        gramas = [" ".join(palavras[i:i + n]) for i in range(len(palavras) - n + 1)]
        if gramas and max(gramas.count(g) for g in set(gramas)) >= 4:
            return False
    return True


def processar_videos(args):
    os.makedirs(args.saida, exist_ok=True)
    pasta_clipes = os.path.join(args.saida, "clipes")
    os.makedirs(pasta_clipes, exist_ok=True)
    jsonl = os.path.join(args.saida, "clipes.jsonl")
    feitos = set()
    if os.path.exists(jsonl):
        with open(jsonl, "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                feitos.add(json.loads(linha)["video"])

    videos = sorted(
        v for v in glob.glob(os.path.join(args.raw, "*.wav")) if time.time() - os.path.getmtime(v) > 90
    )
    pendentes = [v for v in videos if os.path.basename(v) not in feitos]
    print(f"{len(videos)} videos, {len(pendentes)} a processar", flush=True)
    if not pendentes:
        return jsonl

    pipe = carregar_whisper(args.modelo, args.dispositivo)
    for caminho in pendentes:
        nome = os.path.basename(caminho)
        inicio = time.time()
        wav, taxa = sf.read(caminho, dtype="float32")
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        if taxa != TAXA:
            raise RuntimeError(f"taxa inesperada em {caminho}: {taxa}")
        a0 = int(PULAR_INICIO_S * TAXA)
        b0 = len(wav) - int(PULAR_FIM_S * TAXA)
        if b0 <= a0:
            continue
        miolo = wav[a0:b0]
        faixas, piso = montar_clipes(miolo)
        pedacos = [miolo[a:b] for a, b in faixas]
        textos = transcrever(pipe, pedacos, args.batch) if pedacos else []
        base = os.path.splitext(nome)[0]
        with open(jsonl, "a", encoding="utf-8") as arquivo:
            if not pedacos:
                arquivo.write(json.dumps({"video": nome, "vazio": True, "piso_db": round(piso, 1)}) + "\n")
            for k, ((a, b), clipe, texto) in enumerate(zip(faixas, pedacos, textos)):
                arq = os.path.join(pasta_clipes, f"{base}_{k:04d}.wav")
                sf.write(arq, clipe, TAXA, subtype="PCM_16")
                dur = len(clipe) / TAXA
                arquivo.write(json.dumps({
                    "video": nome, "arquivo": os.path.relpath(arq, args.saida).replace(os.sep, "/"),
                    "dur": round(dur, 3), "texto": texto, "cps": round(len(texto) / dur, 2),
                    "piso_db": round(piso, 1),
                    "pico": round(float(np.max(np.abs(clipe))), 3),
                }, ensure_ascii=False) + "\n")
        print(f"{nome}: {len(pedacos)} clipes, piso {piso:.1f} dB, {time.time() - inicio:.0f}s", flush=True)
    return jsonl


def selecionar(args, jsonl):
    registros = []
    with open(jsonl, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            r = json.loads(linha)
            if "arquivo" in r:
                registros.append(r)
    total_h = sum(r["dur"] for r in registros) / 3600
    validos = [r for r in registros if texto_valido(r["texto"]) and r["pico"] < 0.999]
    mediana = float(np.median([r["cps"] for r in validos]))
    validos = [r for r in validos if 0.7 * mediana <= r["cps"] <= 1.35 * mediana]

    forcados = []
    restantes = []
    for r in validos:
        if args.forcar_interjeicoes and FORTES.search(r["texto"]):
            forcados.append((r, args.repeticoes))
        elif args.forcar_interjeicoes and FRACAS.search(r["texto"]):
            forcados.append((r, 1))
        else:
            restantes.append(r)
    dur_forcada = sum(r["dur"] * rep for r, rep in forcados)

    por_video = {}
    for r in restantes:
        por_video.setdefault(r["video"], []).append(r)
    orcamento = max(0.0, args.horas * 3600 - dur_forcada) / max(1, len(por_video))
    rnd = random.Random(7)
    escolhidos = list(forcados)
    for video, lista in por_video.items():
        rnd.shuffle(lista)
        soma = 0.0
        for r in lista:
            if soma + r["dur"] > orcamento:
                continue
            escolhidos.append((r, 1))
            soma += r["dur"]
    escolhidos.sort(key=lambda par: par[0]["arquivo"])

    pasta = os.path.join(args.saida, args.nome_dataset)
    if os.path.exists(pasta):
        shutil.rmtree(pasta)
    os.makedirs(os.path.join(pasta, "wavs"), exist_ok=True)
    linhas = ["audio_file|text|speaker_name"]
    for r, rep in escolhidos:
        origem = os.path.join(args.saida, r["arquivo"])
        base_nome = os.path.splitext(os.path.basename(r["arquivo"]))[0]
        for k in range(rep):
            nome = f"{base_nome}.wav" if k == 0 else f"{base_nome}_rep{k}.wav"
            destino = os.path.join("wavs", nome)
            with open(origem, "rb") as e, open(os.path.join(pasta, destino), "wb") as sai:
                sai.write(e.read())
            linhas.append(f"{destino.replace(os.sep, '/')}|{r['texto'].replace('|', ' ')}|narrador")
    with open(os.path.join(pasta, "metadata.csv"), "w", encoding="utf-8", newline="") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")

    pisos = sorted(r["piso_db"] for r in registros)
    resumo = {
        "videos": len({r["video"] for r in registros}),
        "clipes_totais": len(registros),
        "horas_totais": round(total_h, 2),
        "clipes_validos": len(validos),
        "horas_validas": round(sum(r["dur"] for r in validos) / 3600, 2),
        "clipes_escolhidos": sum(rep for _, rep in escolhidos),
        "clipes_unicos_escolhidos": len(escolhidos),
        "clipes_interjeicao": len(forcados),
        "horas_escolhidas": round(sum(r["dur"] * rep for r, rep in escolhidos) / 3600, 2),
        "cps_mediana": round(mediana, 2),
        "piso_ruido_db_mediana": pisos[len(pisos) // 2] if pisos else None,
        "piso_ruido_db_max": pisos[-1] if pisos else None,
    }
    with open(os.path.join(args.saida, "resumo.json"), "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=1)
    print(json.dumps(resumo, ensure_ascii=False, indent=1), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--modelo", required=True)
    p.add_argument("--dispositivo", default="cuda")
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--horas", type=float, default=4.0)
    p.add_argument("--so-selecionar", action="store_true")
    p.add_argument("--nome-dataset", default="dataset")
    p.add_argument("--forcar-interjeicoes", action="store_true")
    p.add_argument("--repeticoes", type=int, default=4)
    args = p.parse_args()
    jsonl = os.path.join(args.saida, "clipes.jsonl") if args.so_selecionar else processar_videos(args)
    selecionar(args, jsonl)


if __name__ == "__main__":
    main()
