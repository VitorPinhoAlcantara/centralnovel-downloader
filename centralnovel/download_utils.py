"""Utilities for download workflow."""

import os
import re


def limpar_nome_arquivo(texto):
    texto = re.sub(r'[<>:"/\\|?*]', "", texto)
    texto = " ".join(texto.split())
    return texto.replace(" ", "_")


def criar_pasta_volume(volume):
    pasta = f"Lord Of The Mysteries Vol {volume.zfill(2)}"
    if not os.path.exists(pasta):
        os.makedirs(pasta)
        print(f"Pasta criada: {pasta}")
    return pasta

