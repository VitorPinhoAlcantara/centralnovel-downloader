"""Scraping and token retrieval."""

import re

import requests
from bs4 import BeautifulSoup

from .config import AJAX_URL, HEADERS


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

                match = re.search(r"Vol\.\s*(\d+)\s*Cap\.\s*(\d+)", epl_num.get_text(strip=True))
                if not match:
                    continue

                volume = match.group(1)
                capitulo = match.group(2)

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

        dados.sort(key=lambda item: (int(item["volume"]), int(item["capitulo"])))
        return dados
    except Exception as exc:
        print(f"Erro: {exc}")
        return []

