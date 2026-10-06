import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from centralnovel.audiolivro_config import carregar_config
from centralnovel.tts.dividir import dividir_paragrafos
from centralnovel.tts.pool import PoolTTS


def ler_paragrafos(caminho):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        blocos = arquivo.read().split("\n\n")
    return [" ".join(b.split()) for b in blocos if b.strip()]


class AmostradorGPU(threading.Thread):
    def __init__(self, caminho_csv, intervalo=1.0):
        super().__init__(daemon=True)
        self.caminho_csv = caminho_csv
        self.intervalo = intervalo
        self.parar = threading.Event()
        self.amostras = []

    def run(self):
        inicio = time.time()
        while not self.parar.is_set():
            try:
                saida = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
                util, mem = [int(x) for x in saida.split(",")]
                self.amostras.append((round(time.time() - inicio, 1), util, mem))
            except Exception:
                pass
            self.parar.wait(self.intervalo)

    def finalizar(self):
        self.parar.set()
        self.join(timeout=5)
        with open(self.caminho_csv, "w", newline="") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(["t_s", "gpu_util", "mem_mb"])
            escritor.writerows(self.amostras)
        if not self.amostras:
            return 0, 0
        util_media = sum(a[1] for a in self.amostras) / len(self.amostras)
        return round(util_media, 1), max(a[2] for a in self.amostras)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--texto", default=os.path.join("audiobook_work", "teste", "cap349.txt"))
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--saida", default=None)
    p.add_argument("--limite", type=int, default=0)
    p.add_argument("--voz", default=None)
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--tentativas", type=int, default=3)
    args = p.parse_args()

    os.chdir(RAIZ)
    config = carregar_config()
    voz = args.voz or config["voz_padrao"]
    voz_path = os.path.join(config["voz_dir"], voz)
    saida = args.saida or os.path.join("audiobook_work", "lab", f"paralelo_k{args.workers}")
    os.makedirs(saida, exist_ok=True)

    trechos = dividir_paragrafos(
        ler_paragrafos(args.texto),
        pausa_frase_ms=config["pausas_ms"]["frase"],
        pausa_paragrafo_ms=config["pausas_ms"]["paragrafo"],
    )
    if args.limite:
        trechos = trechos[: args.limite]
    jobs = [
        {"id": t["id"], "texto": t["texto"], "saida": os.path.abspath(os.path.join(saida, f"{t['id']}.wav")),
         "seed": args.seed + int(t["id"]), "tentativas": args.tentativas}
        for t in trechos
    ]
    print(f"{len(jobs)} trechos | {args.workers} worker(s) | voz {voz}")

    amostrador = AmostradorGPU(os.path.join(saida, "gpu.csv"))
    pool = PoolTTS(config, [voz_path], workers=args.workers, log_dir=os.path.join(saida, "logs"))

    inicio_carga = time.time()
    prontos = pool.iniciar()
    carga_s = round(time.time() - inicio_carga, 1)
    print(f"workers prontos em {carga_s}s | vram do modelo: {[p_['vram_mb'] for p_ in prontos]} MB")

    amostrador.start()
    inicio = time.time()

    def progresso(res, feitos, total):
        if feitos % 10 == 0 or feitos == total:
            print(f"  {feitos}/{total} ({time.time() - inicio:.0f}s)")

    try:
        resultados = pool.gerar(jobs, ao_concluir=progresso)
    finally:
        pool.encerrar()
        parede = time.time() - inicio
        util_media, mem_max = amostrador.finalizar()

    audio_s = sum(r["metricas"].get("duracao_s", 0) for r in resultados.values())
    reprovados = [r for r in resultados.values() if not r["ok"]]
    tentativas = [r["tentativas"] for r in resultados.values() if r["tentativas"]]
    resumo = {
        "workers": args.workers,
        "trechos": len(jobs),
        "tempo_parede_s": round(parede, 1),
        "audio_s": round(audio_s, 1),
        "audio_por_segundo": round(audio_s / parede, 3) if parede else 0,
        "rtf": round(parede / audio_s, 3) if audio_s else 0,
        "reprovados": len(reprovados),
        "tentativas_media": round(sum(tentativas) / len(tentativas), 2) if tentativas else 0,
        "gpu_util_media": util_media,
        "vram_max_mb": mem_max,
        "carga_s": carga_s,
    }
    with open(os.path.join(saida, "resultados.json"), "w", encoding="utf-8") as arquivo:
        json.dump({"resumo": resumo, "trechos": resultados}, arquivo, ensure_ascii=False, indent=1)
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    for r in reprovados[:15]:
        print(f"  reprovado {r['id']}: {r['motivos']} {r['metricas']}")


if __name__ == "__main__":
    main()
