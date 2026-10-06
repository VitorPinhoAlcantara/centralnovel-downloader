import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from centralnovel.audiolivro import SessaoAudiolivro
from centralnovel.audiolivro_config import carregar_config
from centralnovel.downloader import download_capitulos_novel
from centralnovel.scraper import extrair_links_pdf
from centralnovel.texto_capitulo import obter_info_novel

URL_NOVEL = "https://centralnovel.com/series/shadow-slave-20260913/"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--volume", default="1")
    p.add_argument("--de", type=int, default=4)
    p.add_argument("--ate", type=int, default=23)
    args = p.parse_args()

    os.chdir(RAIZ)
    config = carregar_config()
    todos = extrair_links_pdf(URL_NOVEL)
    caps = [c for c in todos if str(c["volume"]).strip() == args.volume and args.de <= int(c["capitulo"]) <= args.ate]
    caps.sort(key=lambda c: int(c["capitulo"]))
    print(f"{len(caps)} capitulos: {caps[0]['capitulo']} a {caps[-1]['capitulo']}", flush=True)

    info = obter_info_novel(URL_NOVEL)
    sessao = SessaoAudiolivro("Shadow Slave", URL_NOVEL, config["voz_padrao"], config, info)
    resultado = download_capitulos_novel(caps, "Shadow Slave", saidas={"cbz", "audio"}, sessao_audio=sessao)
    print("LOTE_CONCLUIDO", json.dumps({"sucessos": resultado["sucessos"],
                                        "falhas": [f["cap"]["capitulo"] for f in resultado["falhas"]]}), flush=True)


if __name__ == "__main__":
    main()
