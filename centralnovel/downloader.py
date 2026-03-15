"""PDF download operations."""

import os
import time

import requests

from .config import DELAY_ENTRE_DOWNLOADS, HEADERS, MAX_RETRIES
from .csv_store import carregar_links_csv
from .download_utils import criar_pasta_volume, limpar_nome_arquivo
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


def _montar_caminho_saida(cap):
    pasta = criar_pasta_volume(cap["volume"])
    titulo_limpo = limpar_nome_arquivo(cap["titulo"])
    nome_arquivo = f"Capitulo_{cap['capitulo'].zfill(3)}_{titulo_limpo}.pdf"
    return os.path.join(pasta, nome_arquivo)


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

    print(f"\nBaixando capitulo {numero_capitulo}...")
    caminho_completo = _montar_caminho_saida(capitulo)
    if baixar_pdf(capitulo.get("post_id"), capitulo["url"], caminho_completo):
        print(f"\nCapitulo {numero_capitulo} baixado")


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

    print(f"\nBaixando {len(capitulos_filtrados)} capitulos ({inicio}-{fim})...")
    sucesso, falhas = _executar_download_em_lote(capitulos_filtrados)
    _imprimir_resultado(sucesso, falhas)


def download_volume(numero_volume, dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("Execute a opcao de extrair links primeiro")
        return

    capitulos_do_volume = [item for item in dados if item["volume"] == str(numero_volume)]
    if not capitulos_do_volume:
        print(f"Volume {numero_volume} nao encontrado")
        volumes_disponiveis = sorted(set(item["volume"] for item in dados))
        print(f"Volumes disponiveis: {', '.join(volumes_disponiveis)}")
        return

    print(f"\nBaixando Volume {numero_volume}...")
    print(f"Total de capitulos: {len(capitulos_do_volume)}")
    print(
        f"Capitulos: {capitulos_do_volume[0]['capitulo']} "
        f"ate {capitulos_do_volume[-1]['capitulo']}"
    )
    print(f"Tempo estimado: ~{len(capitulos_do_volume) * DELAY_ENTRE_DOWNLOADS / 60:.1f} min")

    confirmacao = input("\nContinuar? (s/n): ")
    if confirmacao.lower() != "s":
        print("Cancelado")
        return

    sucesso, falhas = _executar_download_em_lote(capitulos_do_volume)
    _imprimir_resultado(sucesso, falhas)


def download_todos(dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("Execute a opcao de extrair links primeiro")
        return

    print(f"\nBaixando TODOS os {len(dados)} capitulos...")
    print(f"Tempo estimado: ~{len(dados) * DELAY_ENTRE_DOWNLOADS / 60:.1f} min")

    confirmacao = input("\nContinuar? (s/n): ")
    if confirmacao.lower() != "s":
        print("Cancelado")
        return

    sucesso, falhas = _executar_download_em_lote(dados)
    _imprimir_resultado(sucesso, falhas)


def _executar_download_em_lote(capitulos):
    sucesso = 0
    falhas = 0
    for index, cap in enumerate(capitulos, 1):
        print(f"\n[{index}/{len(capitulos)}] Vol. {cap['volume']} Cap. {cap['capitulo']}: {cap['titulo']}")
        caminho_completo = _montar_caminho_saida(cap)
        if baixar_pdf(cap.get("post_id"), cap["url"], caminho_completo):
            sucesso += 1
        else:
            falhas += 1
        if index < len(capitulos):
            time.sleep(DELAY_ENTRE_DOWNLOADS)
    return sucesso, falhas


def _imprimir_resultado(sucesso, falhas):
    print(f"\n{'=' * 50}")
    print(f"Sucessos: {sucesso}")
    print(f"Falhas: {falhas}")
    print(f"{'=' * 50}")

