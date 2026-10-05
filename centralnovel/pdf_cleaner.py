"""Remove o link do site e a marca de traducao automatica do PDF baixado."""

import os
import re
from pathlib import Path
from threading import Lock

import fitz  # PyMuPDF

from .config import REMOVER_LINK_PDF, REMOVER_MARCA_TRADUCAO

_LOCK = Lock()  # PyMuPDF nao e thread-safe

_RE_URL = re.compile(r"https?://(?:www\.)?centralnovel\.com\S*", re.IGNORECASE)
_RE_MARCA = re.compile(
    r"(traduzid[oa]|tradu[cç][aã]o|translated)\b.*\b"
    r"(chatgpt|gpt|deepl|gemini|claude|copilot|google|tradutor|"
    r"intelig[eê]ncia artificial|ia|usando|using|automatic\w*|machine)\b",
    re.IGNORECASE | re.DOTALL,
)
_TAMANHO_MAX_MARCA = 150  # evita casar com frases do corpo do capitulo


def limpar_pdf(caminho):
    """Retorna True se o PDF foi alterado."""
    if not (REMOVER_LINK_PDF or REMOVER_MARCA_TRADUCAO):
        return False

    tmp = f"{caminho}.clean"
    with _LOCK:
        try:
            with fitz.open(caminho) as doc:
                if doc.page_count == 0 or not _limpar_pagina(doc[0]):
                    return False
                doc.save(tmp, garbage=3, deflate=True)
            os.replace(tmp, caminho)
            return True
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def limpar_pasta(pasta, recursive=True):
    """Retorna (alterados, falhas, total)."""
    padrao = "**/*.pdf" if recursive else "*.pdf"
    pdfs = sorted(Path(pasta).glob(padrao))
    alterados = falhas = 0
    for pdf in pdfs:
        try:
            alterados += limpar_pdf(str(pdf))
        except Exception as exc:
            falhas += 1
            print(f"[ERRO] {pdf.name}: {exc}")
    return alterados, falhas, len(pdfs)


def _limpar_pagina(page):
    areas = []
    if REMOVER_LINK_PDF:
        areas.extend(_areas_link(page))
    if REMOVER_MARCA_TRADUCAO:
        areas.extend(_areas_marca(page))
    if not areas:
        return False

    for area in areas:
        page.add_redact_annot(area, fill=(1, 1, 1))
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
    )
    return True


def _areas_link(page):
    areas = []
    for bloco in page.get_text("dict")["blocks"]:
        for linha in bloco.get("lines", []):
            for span in linha["spans"]:
                if _RE_URL.search(span["text"]):
                    areas.append(fitz.Rect(span["bbox"]))
    return areas


def _areas_marca(page):
    blocos = [b for b in page.get_text("blocks") if b[6] == 0]
    marcas = [b for b in blocos if _eh_marca(b[4])]
    areas = []
    for marca in marcas:
        # cobre tambem as linhas horizontais entre a marca e o proximo texto
        abaixo = [
            b[1] for b in blocos
            if b not in marcas and b[1] >= marca[3] - 0.5
        ]
        limite = min(abaixo, default=marca[3]) - 2
        areas.append(
            fitz.Rect(0, marca[1] - 1, page.rect.width, max(marca[3], limite))
        )
    return areas


def _eh_marca(texto):
    texto = " ".join(texto.split())
    return len(texto) <= _TAMANHO_MAX_MARCA and bool(_RE_MARCA.search(texto))
