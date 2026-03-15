"""Scraping and novel catalog helpers."""

import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import (
    AJAX_URL,
    HEADERS,
    SERIES_POPULAR_URL,
    SERIES_SITEMAP_URL,
    SITE_URL,
)

_SITEMAP_CACHE = None


def extrair_post_id_da_url(url_pdf_page):
    try:
        response = requests.get(url_pdf_page, headers=HEADERS, timeout=30)
        response.raise_for_status()
        match = re.search(r'"post_id":\s*(\d+)', response.text)
        if match:
            return match.group(1)
        match = re.search(r'data-id["\s]*[:=]["\s]*(\d+)', response.text)
        if match:
            return match.group(1)
        return None
    except Exception as exc:
        print(f"Erro ao extrair post_id: {exc}")
        return None


def obter_token_pdf(post_id, url_pdf_page):
    try:
        if not post_id:
            print("Extraindo post_id da pagina...")
            post_id = extrair_post_id_da_url(url_pdf_page)
            if not post_id:
                print("Nao foi possivel extrair post_id")
                return None
            print(f"Post ID: {post_id}")

        headers = HEADERS.copy()
        headers["Referer"] = url_pdf_page
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = {"action": "ts_ln_dl_url", "post_id": post_id}

        response = requests.post(AJAX_URL, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("error") == 0 and result.get("url"):
            return result["url"].replace("\\/", "/")
        print(f"Resposta inesperada: {result}")
        return None
    except Exception as exc:
        print(f"Erro ao obter token: {exc}")
        return None


def extrair_links_pdf(url):
    print(f"\nAcessando: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        capitulos = soup.find_all("li", {"data-id": True})
        print(f"Encontrados {len(capitulos)} capitulos")

        dados = []
        for cap in capitulos:
            try:
                post_id = cap.get("data-id")
                if not post_id:
                    continue

                epl_num = cap.find("div", class_="epl-num")
                if not epl_num:
                    continue

                texto_num = epl_num.get_text(" ", strip=True)
                volume, capitulo = _extrair_volume_e_capitulo(texto_num)
                if not capitulo:
                    continue

                epl_title = cap.find("div", class_="epl-title")
                titulo = epl_title.get_text(strip=True) if epl_title else "Sem_Titulo"

                epl_date = cap.find("div", class_="epl-date")
                data = epl_date.get_text(strip=True) if epl_date else ""

                epl_pdf = cap.find("div", class_="epl-pdf")
                if not epl_pdf:
                    continue
                link_tag = epl_pdf.find("a", class_="dlpdf")
                if not link_tag or not link_tag.get("href"):
                    continue

                dados.append(
                    {
                        "volume": volume,
                        "capitulo": capitulo,
                        "titulo": titulo,
                        "url": link_tag["href"],
                        "data": data,
                        "post_id": post_id,
                    }
                )
            except Exception as exc:
                print(f"Erro ao processar capitulo: {exc}")
                continue

        dados.sort(key=_ordenar_capitulo)
        return dados
    except Exception as exc:
        print(f"Erro: {exc}")
        return []


def listar_top_novels(limite=10):
    try:
        response = requests.get(SERIES_POPULAR_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        print(f"Erro ao carregar top novels: {exc}")
        return []

    itens = []
    for article in soup.select("article"):
        anchor = article.select_one("a[href*='/series/']")
        if not anchor:
            continue
        url = anchor.get("href", "").strip()
        if not _eh_link_novel(url):
            continue

        titulo = anchor.get("title", "").strip()
        if not titulo:
            titulo = article.get_text(" ", strip=True)
            titulo = re.sub(r"\s+", " ", titulo)
        if not titulo:
            titulo = _titulo_from_url(url)

        itens.append({"title": titulo, "url": url})

    return _deduplicar_novels(itens)[:limite]


def buscar_novels_por_nome(texto, limite=10):
    query = _normalizar_texto(texto)
    if not query:
        return []

    novels = listar_novels_sitemap()
    scored = []
    for item in novels:
        title_norm = _normalizar_texto(item["title"])
        if not title_norm:
            continue

        score = 0.0
        if query == title_norm:
            score = 100.0
        elif query in title_norm:
            score = 90.0
        else:
            query_parts = [part for part in query.split() if len(part) > 1]
            if query_parts and all(part in title_norm for part in query_parts):
                score = 80.0
            else:
                ratio = SequenceMatcher(None, query, title_norm).ratio()
                score = ratio * 100

        if score >= 45:
            scored.append((score, item))

    scored.sort(key=lambda val: val[0], reverse=True)
    return [item for _, item in scored[:limite]]


def listar_novels_sitemap():
    global _SITEMAP_CACHE
    if _SITEMAP_CACHE is not None:
        return _SITEMAP_CACHE

    try:
        response = requests.get(SERIES_SITEMAP_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [
            item.text
            for item in root.findall(".//sm:url/sm:loc", ns)
            if item.text and _eh_link_novel(item.text)
        ]
    except Exception as exc:
        print(f"Erro ao carregar sitemap: {exc}")
        return []

    _SITEMAP_CACHE = _deduplicar_novels(
        [{"title": _titulo_from_url(url), "url": url.strip()} for url in urls]
    )
    return _SITEMAP_CACHE


def obter_titulo_novel(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        print(f"Erro ao obter titulo da novel: {exc}")
        return _titulo_from_url(url)

    for selector in ("h1.entry-title", ".entry-title", "h1[itemprop='headline']"):
        title_node = soup.select_one(selector)
        if title_node:
            title = title_node.get_text(" ", strip=True)
            if title:
                return title
    return _titulo_from_url(url)


def normalizar_url_novel(entrada):
    texto = entrada.strip().strip('"').strip("'")
    if not texto:
        return None

    if texto.startswith("http://") or texto.startswith("https://"):
        url = texto
    elif texto.startswith("/series/"):
        url = f"{SITE_URL.rstrip('/')}{texto}"
    elif "/series/" in texto:
        url = f"https://{texto}"
    else:
        return None

    parsed = urlparse(url)
    if "centralnovel.com" not in parsed.netloc:
        return None

    if not _eh_link_novel(url):
        return None

    return _normalizar_url(url)


def _extrair_volume_e_capitulo(texto_num):
    match = re.search(r"Vol\.\s*(.*?)\s*Cap\.\s*(\d+)", texto_num, flags=re.IGNORECASE)
    if match:
        volume = re.sub(r"\s+", " ", match.group(1).strip())
        return volume or "1", match.group(2)

    cap_match = re.search(r"Cap\.\s*(\d+)", texto_num, flags=re.IGNORECASE)
    if cap_match:
        return "1", cap_match.group(1)

    numeros = re.findall(r"\d+", texto_num)
    if len(numeros) >= 2:
        return numeros[0], numeros[1]
    if len(numeros) == 1:
        return "1", numeros[0]
    return None, None


def _ordenar_capitulo(item):
    vol = str(item["volume"]).strip()
    cap = int(item["capitulo"])
    if vol.isdigit():
        return (0, int(vol), cap)
    return (1, _normalizar_texto(vol), cap)


def _deduplicar_novels(novels):
    vistos = set()
    saida = []
    for item in novels:
        url = _normalizar_url(item["url"])
        if url in vistos:
            continue
        vistos.add(url)
        saida.append({"title": item["title"], "url": url})
    return saida


def _eh_link_novel(url):
    if not url:
        return False
    url = _normalizar_url(url)
    if "/series/" not in url:
        return False
    if "/series/?" in url:
        return False
    if url.rstrip("/").endswith("/series"):
        return False
    if "/series/list-mode" in url:
        return False
    return True


def _normalizar_url(url):
    return url.split("#")[0].split("?")[0].strip()


def _titulo_from_url(url):
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else ""
    slug = re.sub(r"-\d{8}$", "", slug)
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def _normalizar_texto(texto):
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()
