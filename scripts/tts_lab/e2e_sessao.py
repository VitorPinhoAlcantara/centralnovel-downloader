import argparse
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from centralnovel.audiolivro import SessaoAudiolivro
from centralnovel.audiolivro_config import carregar_config
from centralnovel.scraper import extrair_links_pdf
from centralnovel.texto_capitulo import obter_info_novel

URL_NOVEL = "https://centralnovel.com/series/shadow-slave-20260913/"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--capitulos", nargs="+", type=int, default=[349])
    p.add_argument("--destino", default=os.path.join("audiobook_work", "teste", "fake_abs2"))
    args = p.parse_args()

    os.chdir(RAIZ)
    config = carregar_config()
    config.update({"abs_ssh": "", "abs_dir": os.path.abspath(args.destino), "abs_token": "",
                   "lote_capitulos": 1})
    os.makedirs(config["abs_dir"], exist_ok=True)

    todos = extrair_links_pdf(URL_NOVEL)
    escolhidos = [c for c in todos if int(c["capitulo"]) in set(args.capitulos)]
    print(f"{len(escolhidos)} capitulo(s) encontrados")
    info = obter_info_novel(URL_NOVEL)
    sessao = SessaoAudiolivro("Shadow Slave", URL_NOVEL, config["voz_padrao"], config, info)
    try:
        for cap in escolhidos:
            inicio = time.time()
            print(f"pendente: {sessao.pendente(cap, True)}")
            ok, motivo = sessao.gerar_capitulo(cap)
            print(f"cap {cap['capitulo']}: ok={ok} motivo={motivo} em {time.time() - inicio:.0f}s")
    finally:
        sessao.finalizar()


if __name__ == "__main__":
    main()
