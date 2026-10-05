"""Texto dos capitulos direto do HTML do site (sem passar pelo PDF)."""

import re
import time

import requests
from bs4 import BeautifulSoup

from .config import HEADERS, MAX_RETRIES

_RE_URL = re.compile(r"https?://(?:www\.)?centralnovel\.com\S*", re.IGNORECASE)
_RE_MARCA = re.compile(
    r"(traduzid[oa]|tradu[cç][aã]o|translated)\b.*\b"
    r"(chatgpt|gpt|deepl|gemini|claude|copilot|google|tradutor|"
    r"intelig[eê]ncia artificial|ia|usando|using|automatic\w*|machine)\b",
    re.IGNORECASE | re.DOTALL,
)
_TAMANHO_MAX_MARCA = 150  # evita casar com frases do corpo do capitulo


def url_pagina_capitulo(cap):
    """O link guardado aponta para '<capitulo>/pdf/'; o texto fica na pagina do capitulo."""
    url = cap["url"].split("#")[0].split("?")[0].rstrip("/")
    if url.endswith("/pdf"):
        url = url[: -len("/pdf")]
    return url + "/"


def obter_texto_capitulo(cap):
    """Retorna a lista de paragrafos do capitulo, sem link do site nem marca de traducao.

    Levanta RuntimeError se o texto nao puder ser obtido.
    """
    url = url_pagina_capitulo(cap)
    ultimo_erro = None
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            resposta = requests.get(url, headers=HEADERS, timeout=30)
            resposta.raise_for_status()
            resposta.encoding = "utf-8"
            paragrafos = _extrair_paragrafos(resposta.text)
            if paragrafos:
                return paragrafos
            ultimo_erro = "texto do capitulo nao encontrado na pagina"
        except requests.RequestException as exc:
            ultimo_erro = str(exc)
        if tentativa < MAX_RETRIES:
            time.sleep(2 * tentativa)
    raise RuntimeError(f"{url}: {ultimo_erro}")


def obter_info_novel(url_novel):
    """Retorna {"autor": str, "capa": str} (valores vazios se nao encontrados)."""
    info = {"autor": "", "capa": ""}
    try:
        resposta = requests.get(url_novel, headers=HEADERS, timeout=30)
        resposta.raise_for_status()
        resposta.encoding = "utf-8"
        soup = BeautifulSoup(resposta.text, "html.parser")
    except requests.RequestException as exc:
        print(f"Aviso: nao foi possivel ler a pagina da novel: {exc}")
        return info

    for span in soup.select(".spe span"):
        texto = span.get_text(" ", strip=True)
        if texto.lower().startswith("autor"):
            info["autor"] = texto.split(":", 1)[-1].strip()
            break

    imagem = soup.select_one(".thumb img, .thumbook img")
    if imagem and imagem.get("src"):
        info["capa"] = imagem["src"].split("?")[0]
    return info


def baixar_capa(url_capa, destino):
    """Baixa a capa; retorna True em caso de sucesso."""
    if not url_capa:
        return False
    try:
        resposta = requests.get(url_capa, headers=HEADERS, timeout=30)
        resposta.raise_for_status()
        with open(destino, "wb") as arquivo:
            arquivo.write(resposta.content)
        return True
    except (requests.RequestException, OSError) as exc:
        print(f"Aviso: nao foi possivel baixar a capa: {exc}")
        return False


def _extrair_paragrafos(html):
    soup = BeautifulSoup(html, "html.parser")
    conteudo = soup.select_one("div.epcontent")
    if conteudo is None:
        return []

    for quebra in conteudo.find_all("br"):
        quebra.replace_with("\n")

    paragrafos = []
    for tag in conteudo.find_all("p"):
        for linha in tag.get_text().split("\n"):
            linha = " ".join(linha.split())
            if not linha or _eh_lixo(linha):
                continue
            paragrafos.append(linha)
    return paragrafos


def _eh_lixo(texto):
    if _RE_URL.search(texto):
        return True
    return len(texto) <= _TAMANHO_MAX_MARCA and bool(_RE_MARCA.search(texto))
