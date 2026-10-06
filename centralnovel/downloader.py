"""PDF download operations."""

import os
import queue
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import requests

from .config import (
    CBZ_ROOT_DIR,
    DELAY_ENTRE_DOWNLOADS,
    HEADERS,
    MAX_CAPITULOS_A_FRENTE,
    MAX_DOWNLOADS_PARALELOS,
    MAX_RETRIES,
    PDF_ROOT_DIR,
)
from .converter import converter_pdf_para_cbz
from .csv_store import carregar_links_csv
from .download_utils import limpar_nome_arquivo
from .pdf_cleaner import limpar_pdf
from .scraper import obter_token_pdf


def baixar_pdf(post_id, url_pdf_page, caminho_destino, tentativa=1, sobrescrever=False):
    """Retorna (sucesso, motivo_do_erro)."""
    caminho_tmp = f"{caminho_destino}.part"
    try:
        if os.path.exists(caminho_destino) and not sobrescrever:
            print(f"Ja existe: {os.path.basename(caminho_destino)}")
            return True, None

        pdf_url_com_token = obter_token_pdf(post_id, url_pdf_page)
        if not pdf_url_com_token:
            print("Nao foi possivel obter token")
            return False, "Nao foi possivel obter token"

        time.sleep(0.5)
        headers = HEADERS.copy()
        headers["Referer"] = url_pdf_page
        response = requests.get(pdf_url_com_token, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)
        with open(caminho_tmp, "wb") as file_obj:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_obj.write(chunk)

        if os.path.getsize(caminho_tmp) < 1000:
            print("Arquivo muito pequeno, pode estar corrompido")
            return False, "Arquivo baixado muito pequeno (possivelmente corrompido)"

        try:
            limpar_pdf(caminho_tmp)
        except Exception as exc:
            print(f"Aviso: nao foi possivel limpar o PDF: {exc}")

        # o arquivo antigo so e trocado depois que o novo foi baixado por completo
        os.replace(caminho_tmp, caminho_destino)
        print(
            f"Baixado: {os.path.basename(caminho_destino)} "
            f"({os.path.getsize(caminho_destino)} bytes)"
        )
        return True, None
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 429 and tentativa < MAX_RETRIES:
            wait_time = DELAY_ENTRE_DOWNLOADS * tentativa * 2
            print(f"Erro 429. Aguardando {wait_time}s...")
            time.sleep(wait_time)
            return baixar_pdf(post_id, url_pdf_page, caminho_destino, tentativa + 1, sobrescrever)
        print(f"Erro HTTP: {exc}")
        return False, f"Erro HTTP: {exc}"
    except Exception as exc:
        print(f"Erro: {exc}")
        return False, f"Erro: {exc}"
    finally:
        if os.path.exists(caminho_tmp):
            os.remove(caminho_tmp)


def separar_baixados(capitulos, novel_title, saidas=None, audio_prontos=None):
    saidas = _normalizar_saidas(saidas)
    novel_dir = _nome_pasta_novel(novel_title)
    existentes, faltantes = [], []
    for cap in capitulos:
        baixado = True
        if "pdf" in saidas:
            baixado = baixado and os.path.exists(_montar_caminho_pdf(cap, novel_dir))
        if "cbz" in saidas:
            baixado = baixado and os.path.exists(_montar_caminho_cbz(cap, novel_dir))
        if "audio" in saidas:
            baixado = baixado and chave_capitulo(cap) in (audio_prontos or set())
        (existentes if baixado else faltantes).append(cap)
    return existentes, faltantes


def chave_capitulo(cap):
    return (str(cap["volume"]).strip(), str(cap["capitulo"]).strip())


def descrever_saidas(saidas):
    nomes = {"pdf": "PDF", "cbz": "CBZ", "audio": "Audiolivro"}
    return " + ".join(nomes[s] for s in ("pdf", "cbz", "audio") if s in saidas)


def _normalizar_saidas(saidas):
    return set(saidas) if saidas else {"pdf"}


def download_capitulos_novel(capitulos, novel_title, saidas=None, sobrescrever=False,
                             sessao_audio=None):
    if not capitulos:
        print("Nenhum capitulo selecionado")
        return {"sucessos": 0, "falhas": []}

    saidas = _normalizar_saidas(saidas)
    if "audio" in saidas and sessao_audio is None:
        raise ValueError("saida 'audio' exige uma sessao de audiolivro")

    novel_dir = _nome_pasta_novel(novel_title)
    total = len(capitulos)
    com_audio = "audio" in saidas
    paralelos = 1 if com_audio else MAX_DOWNLOADS_PARALELOS

    if com_audio:
        print(f"\nIniciando {total} capitulos (downloads um por vez, ate {MAX_CAPITULOS_A_FRENTE} a frente do audio)")
    else:
        print(f"\nIniciando {total} capitulos ({paralelos} em paralelo)")
    print(f"Saidas: {descrever_saidas(saidas)}")
    if sobrescrever:
        print("Arquivos ja existentes serao sobrescritos")

    resultado_lock = Lock()
    contadores = {"sucesso": 0, "concluidos": 0}
    falhas = []

    def _registrar(indice, cap, sucesso, motivo):
        with resultado_lock:
            contadores["concluidos"] += 1
            if sucesso:
                contadores["sucesso"] += 1
            else:
                falhas.append({"indice": indice, "cap": cap, "motivo": motivo})
            print(
                f"\n[{contadores['concluidos']}/{total}] "
                f"Vol. {cap['volume']} Cap. {cap['capitulo']}: {cap['titulo']}"
            )
            if not sucesso:
                print(f"ERRO: {motivo}")

    def _processar_capitulo(indice, cap):
        try:
            sucesso, motivo = _baixar_saidas_capitulo(cap, novel_dir, saidas, sobrescrever)
        except Exception as exc:
            sucesso, motivo = False, f"Erro inesperado: {exc}"
        _registrar(indice, cap, sucesso, motivo)

    try:
        if com_audio:
            _executar_com_audio(
                capitulos, novel_dir, saidas, sobrescrever, sessao_audio, _registrar
            )
        else:
            with ThreadPoolExecutor(max_workers=paralelos) as executor:
                futures = []
                for indice, cap in enumerate(capitulos):
                    futures.append(executor.submit(_processar_capitulo, indice, cap))
                    time.sleep(0.3)
                for future in as_completed(futures):
                    future.result()
    finally:
        if sessao_audio is not None:
            sessao_audio.finalizar()

    falhas.sort(key=lambda item: item["indice"])
    falhas = [{"cap": item["cap"], "motivo": item["motivo"]} for item in falhas]
    _imprimir_resultado(contadores["sucesso"], len(falhas))
    return {"sucessos": contadores["sucesso"], "falhas": falhas}


def _executar_com_audio(capitulos, novel_dir, saidas, sobrescrever, sessao_audio, registrar):
    fila = queue.Queue()
    vagas = threading.Semaphore(MAX_CAPITULOS_A_FRENTE)
    parar = threading.Event()

    def produtor():
        for indice, cap in enumerate(capitulos):
            vagas.acquire()
            if parar.is_set():
                break
            try:
                sucesso, motivo = _baixar_saidas_capitulo(cap, novel_dir, saidas, sobrescrever)
            except Exception as exc:
                sucesso, motivo = False, f"Erro inesperado: {exc}"
            fila.put((indice, cap, sucesso, motivo))
            time.sleep(0.3)
        fila.put(None)

    thread = threading.Thread(target=produtor, daemon=True)
    thread.start()
    try:
        while True:
            item = fila.get()
            if item is None:
                break
            indice, cap, sucesso, motivo = item
            try:
                if sucesso and sessao_audio.pendente(cap, sobrescrever):
                    sucesso, motivo = sessao_audio.gerar_capitulo(cap)
            except Exception as exc:
                sucesso, motivo = False, f"Erro inesperado: {exc}"
            vagas.release()
            registrar(indice, cap, sucesso, motivo)
    finally:
        parar.set()
        vagas.release()


def _baixar_saidas_capitulo(cap, novel_dir, saidas, sobrescrever):
    caminho_pdf = _montar_caminho_pdf(cap, novel_dir)
    caminho_cbz = _montar_caminho_cbz(cap, novel_dir)

    quer_pdf = "pdf" in saidas and (sobrescrever or not os.path.exists(caminho_pdf))
    quer_cbz = "cbz" in saidas and (sobrescrever or not os.path.exists(caminho_cbz))

    if quer_pdf or quer_cbz:
        pdf_existia = os.path.exists(caminho_pdf)
        sucesso, motivo = baixar_pdf(
            cap.get("post_id"), cap["url"], caminho_pdf, sobrescrever=sobrescrever
        )
        if not sucesso:
            return False, motivo
        if quer_cbz:
            cbz_gerado = converter_pdf_para_cbz(
                caminho_pdf,
                output_folder=_montar_pasta_cbz(cap["volume"], novel_dir),
                keep_images=False,
                verbose=False,
                sobrescrever=True,
            )
            if not cbz_gerado:
                return False, "Falha na conversao para CBZ"
            print(f"CBZ gerado: {os.path.basename(cbz_gerado)}")
            if "pdf" not in saidas and not pdf_existia:
                os.remove(caminho_pdf)
    return True, None


def _montar_caminho_pdf(cap, novel_dir):
    pasta = _montar_pasta_pdf(cap["volume"], novel_dir)
    titulo_limpo = limpar_nome_arquivo(cap["titulo"])
    nome_arquivo = f"Capitulo_{cap['capitulo'].zfill(3)}_{titulo_limpo}.pdf"
    return os.path.join(pasta, nome_arquivo)


def _montar_pasta_pdf(volume, novel_dir):
    return os.path.join(PDF_ROOT_DIR, _formatar_nome_pasta_volume(volume, novel_dir))


def _montar_pasta_cbz(volume, novel_dir):
    return os.path.join(CBZ_ROOT_DIR, _formatar_nome_pasta_volume(volume, novel_dir))


def _montar_caminho_cbz(cap, novel_dir):
    pasta = _montar_pasta_cbz(cap["volume"], novel_dir)
    nome_pdf = os.path.basename(_montar_caminho_pdf(cap, novel_dir))
    return os.path.join(pasta, f"{os.path.splitext(nome_pdf)[0]}.cbz")


def _formatar_nome_pasta_volume(volume, novel_dir):
    volume_texto = str(volume).strip()
    return f"{novel_dir} Vol {volume_texto}"


def _nome_pasta_novel(novel_title):
    return _limpar_nome_pasta(novel_title) or "Novel"


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
