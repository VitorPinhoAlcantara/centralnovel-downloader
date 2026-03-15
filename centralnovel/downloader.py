"""PDF download operations."""

import os
import re
import time

import requests

from .config import CBZ_ROOT_DIR, DELAY_ENTRE_DOWNLOADS, HEADERS, MAX_RETRIES, PDF_ROOT_DIR
from .converter import converter_pdf_para_cbz
from .csv_store import carregar_links_csv
from .download_utils import limpar_nome_arquivo
from .scraper import obter_token_pdf


def baixar_pdf(post_id, url_pdf_page, caminho_destino, tentativa=1):
    try:
        if os.path.exists(caminho_destino):
            print(f"Ja existe: {os.path.basename(caminho_destino)}")
            return True

        pdf_url_com_token = obter_token_pdf(post_id, url_pdf_page)
        if not pdf_url_com_token:
            print("Nao foi possivel obter token")
            return False

        time.sleep(0.5)
        headers = HEADERS.copy()
        headers["Referer"] = url_pdf_page
        response = requests.get(pdf_url_com_token, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)
        with open(caminho_destino, "wb") as file_obj:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_obj.write(chunk)

        if os.path.getsize(caminho_destino) < 1000:
            print("Arquivo muito pequeno, pode estar corrompido")
            os.remove(caminho_destino)
            return False

        print(
            f"Baixado: {os.path.basename(caminho_destino)} "
            f"({os.path.getsize(caminho_destino)} bytes)"
        )
        return True
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 429 and tentativa < MAX_RETRIES:
            wait_time = DELAY_ENTRE_DOWNLOADS * tentativa * 2
            print(f"Erro 429. Aguardando {wait_time}s...")
            time.sleep(wait_time)
            return baixar_pdf(post_id, url_pdf_page, caminho_destino, tentativa + 1)
        print(f"Erro HTTP: {exc}")
        return False
    except Exception as exc:
        print(f"Erro: {exc}")
        return False


def download_capitulos_novel(capitulos, novel_title, gerar_cbz=False):
    if not capitulos:
        print("Nenhum capitulo selecionado")
        return 0, 0

    sucesso = 0
    falhas = 0
    novel_dir = _limpar_nome_pasta(novel_title) or "Novel"

    print(f"\nIniciando download de {len(capitulos)} capitulos")
    if gerar_cbz:
        print("Modo: PDF + conversao automatica para CBZ")
    else:
        print("Modo: apenas PDF")

    for index, cap in enumerate(capitulos, 1):
        print(f"\n[{index}/{len(capitulos)}] Vol. {cap['volume']} Cap. {cap['capitulo']}: {cap['titulo']}")
        caminho_pdf = _montar_caminho_pdf(cap, novel_dir)

        if baixar_pdf(cap.get("post_id"), cap["url"], caminho_pdf):
            sucesso += 1
            if gerar_cbz:
                pasta_cbz = _montar_pasta_cbz(cap["volume"], novel_dir)
                resultado = converter_pdf_para_cbz(
                    caminho_pdf,
                    output_folder=pasta_cbz,
                    keep_images=False,
                    verbose=False,
                )
                if resultado:
                    print(f"CBZ gerado: {os.path.basename(resultado)}")
                else:
                    print("Falha na conversao para CBZ")
        else:
            falhas += 1

        if index < len(capitulos):
            time.sleep(DELAY_ENTRE_DOWNLOADS)

    _imprimir_resultado(sucesso, falhas)
    return sucesso, falhas


def _montar_caminho_pdf(cap, novel_dir):
    pasta = _montar_pasta_pdf(cap["volume"], novel_dir)
    titulo_limpo = limpar_nome_arquivo(cap["titulo"])
    nome_arquivo = f"Capitulo_{cap['capitulo'].zfill(3)}_{titulo_limpo}.pdf"
    return os.path.join(pasta, nome_arquivo)


def _montar_pasta_pdf(volume, novel_dir):
    pasta = os.path.join(PDF_ROOT_DIR, _formatar_nome_pasta_volume(volume, novel_dir))
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _montar_pasta_cbz(volume, novel_dir):
    pasta = os.path.join(CBZ_ROOT_DIR, _formatar_nome_pasta_volume(volume, novel_dir))
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _formatar_nome_pasta_volume(volume, novel_dir):
    volume_texto = str(volume).strip()
    return f"{novel_dir} Vol {volume_texto}"


def _limpar_nome_pasta(texto):
    texto = re.sub(r'[<>:"/\\|?*]', "", str(texto))
    return " ".join(texto.split())


def download_capitulo_especifico(numero_capitulo, dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("Execute a opcao de extrair links primeiro")
        return
    capitulo = next((item for item in dados if item["capitulo"] == str(numero_capitulo)), None)
    if not capitulo:
        print(f"Capitulo {numero_capitulo} nao encontrado")
        return
    download_capitulos_novel([capitulo], "Legacy")


def download_intervalo(inicio, fim, dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("Execute a opcao de extrair links primeiro")
        return
    capitulos_filtrados = [item for item in dados if inicio <= int(item["capitulo"]) <= fim]
    if not capitulos_filtrados:
        print(f"Nenhum capitulo no intervalo {inicio}-{fim}")
        return
    download_capitulos_novel(capitulos_filtrados, "Legacy")


def download_volume(numero_volume, dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("Execute a opcao de extrair links primeiro")
        return
    capitulos_do_volume = [item for item in dados if item["volume"] == str(numero_volume)]
    if not capitulos_do_volume:
        print(f"Volume {numero_volume} nao encontrado")
        return
    download_capitulos_novel(capitulos_do_volume, "Legacy")


def download_todos(dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("Execute a opcao de extrair links primeiro")
        return
    download_capitulos_novel(dados, "Legacy")


def _imprimir_resultado(sucesso, falhas):
    print(f"\n{'=' * 50}")
    print(f"Sucessos: {sucesso}")
    print(f"Falhas: {falhas}")
    print(f"{'=' * 50}")
