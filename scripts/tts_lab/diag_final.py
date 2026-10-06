import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "scripts", "tts_lab"))

from ab_texto import gerar
from centralnovel.audiolivro_config import carregar_config
from centralnovel.tts.dividir import dividir_paragrafos
from centralnovel.tts.normalizar import ajustar_final, normalizar
from gerar_trechos import ler_paragrafos

FINAIS = ["ponto", "e2a", "sem"]
REFS = [6, 30]


def palavras(texto):
    texto = unicodedata.normalize("NFKD", texto.lower().replace("-", " "))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", texto).split()


def analisar(referencia, hipotese):
    ref, hip = palavras(referencia), palavras(hipotese)
    casador = difflib.SequenceMatcher(a=ref, b=hip, autojunk=False)
    casadas = sum(b.size for b in casador.get_matching_blocks())
    cobertura = casadas / len(ref) if ref else 1.0
    ultimo = max((b.b + b.size for b in casador.get_matching_blocks() if b.size), default=0)
    sobra = hip[ultimo:]
    return {
        "cobertura": round(cobertura, 3),
        "sobra_final": sobra,
        "ponto": any(w in ("ponto", "pontos", "pont") for w in sobra),
        "pulou": cobertura < 0.85,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--texto", default=os.path.join("audiobook_work", "teste", "cap349.txt"))
    p.add_argument("--amostras", type=int, default=36)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--saida", default=os.path.join("audiobook_work", "lab", "diag_final"))
    p.add_argument("--voz", default=None)
    args = p.parse_args()

    os.chdir(RAIZ)
    config = carregar_config()
    voz_path = os.path.join(config["voz_dir"], args.voz or config["voz_padrao"])
    os.makedirs(args.saida, exist_ok=True)

    trechos = dividir_paragrafos(ler_paragrafos(args.texto))
    candidatos = [t for t in trechos if t["texto"].rstrip().endswith(".") and len(t["texto"]) >= 40]
    passo = max(1, len(candidatos) // args.amostras)
    escolhidos = candidatos[::passo][: args.amostras]

    itens = []
    for t in escolhidos:
        base = normalizar(t["texto"])
        for ref in REFS:
            for final in FINAIS:
                itens.append({
                    "caso": f"c{t['id']}", "variante": f"ref{ref}_{final}", "bruto": base,
                    "texto": ajustar_final(base, final), "seed": 7000 + int(t["id"]),
                    "ref": {"gpt_cond_len": ref}, "final": final, "refn": ref,
                })
    print(f"{len(escolhidos)} trechos x {len(REFS) * len(FINAIS)} combinacoes = {len(itens)} geracoes")
    gerar(config, voz_path, itens, args.saida, workers=args.workers)

    lista = os.path.join(args.saida, "lista.json")
    with open(lista, "w", encoding="utf-8") as arquivo:
        json.dump([os.path.join(args.saida, i["arquivo"]) for i in itens], arquivo)
    transcr = os.path.join(args.saida, "transcricoes.json")
    env = dict(os.environ, PYTHONUTF8="1")
    subprocess.run([config["tts_python"], os.path.join("scripts", "tts_lab", "asr.py"),
                    "--lista", lista, "--saida", transcr], check=True, env=env)
    with open(transcr, "r", encoding="utf-8") as arquivo:
        texto_asr = json.load(arquivo)

    resumo = {}
    for item in itens:
        ana = analisar(item["bruto"], texto_asr[os.path.join(args.saida, item["arquivo"])])
        item["asr"] = texto_asr[os.path.join(args.saida, item["arquivo"])]
        item["analise"] = ana
        m = item["metricas"]
        mudo = m["silencio_max_s"] > 1.2 or m["duracao_s"] > 27
        chave = (item["refn"], item["final"])
        r = resumo.setdefault(chave, {"n": 0, "ponto": 0, "pulou": 0, "mudo": 0, "cobertura": 0.0})
        r["n"] += 1
        r["ponto"] += ana["ponto"]
        r["pulou"] += ana["pulou"]
        r["mudo"] += mudo
        r["cobertura"] += ana["cobertura"]

    with open(os.path.join(args.saida, "itens.json"), "w", encoding="utf-8") as arquivo:
        json.dump(itens, arquivo, ensure_ascii=False, indent=1)

    print(f"{'ref':>4} {'final':>6} {'n':>4} {'ponto':>6} {'pulou':>6} {'mudo':>5} {'cobertura':>10}")
    for (ref, final), r in sorted(resumo.items()):
        print(f"{ref:>4} {final:>6} {r['n']:>4} {r['ponto']:>6} {r['pulou']:>6} {r['mudo']:>5} "
              f"{r['cobertura'] / r['n']:>10.3f}")


if __name__ == "__main__":
    main()
