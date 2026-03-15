"""CSV persistence for chapter links."""

import csv
import os

from .config import LINKS_CSV


def salvar_links_csv(dados, arquivo=LINKS_CSV):
    if not dados:
        print("Nenhum dado para salvar")
        return False
    try:
        with open(arquivo, "w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(
                file_obj,
                fieldnames=["volume", "capitulo", "titulo", "url", "data", "post_id"],
            )
            writer.writeheader()
            writer.writerows(dados)
        print(f"Links salvos: {arquivo}")
        print(f"Total: {len(dados)} capitulos")
        return True
    except Exception as exc:
        print(f"Erro ao salvar CSV: {exc}")
        return False


def carregar_links_csv(arquivo=LINKS_CSV):
    if not os.path.exists(arquivo):
        print(f"Arquivo {arquivo} nao encontrado")
        return []
    try:
        with open(arquivo, "r", encoding="utf-8") as file_obj:
            dados = list(csv.DictReader(file_obj))
        print(f"Carregados {len(dados)} capitulos")
        return dados
    except Exception as exc:
        print(f"Erro ao carregar CSV: {exc}")
        return []

