"""Interactive TUI menus for downloader and converter."""

import os

from InquirerPy import inquirer

from .config import DPI, QUALIDADE_JPG
from .converter import converter_pdf_para_cbz, processar_pasta
from .downloader import download_capitulos_novel
from .scraper import (
    buscar_novels_por_nome,
    extrair_links_pdf,
    listar_top_novels,
    normalizar_url_novel,
    obter_titulo_novel,
)
from .selection import parse_numero_lista_ou_intervalo


def menu_principal():
    while True:
        _clear_screen()
        escolha = inquirer.select(
            message="CENTRALNOVEL - MAIN",
            choices=[
                {"name": "Download de novel", "value": "download"},
                {"name": "Conversao PDF -> CBZ", "value": "conversao"},
                {"name": "Sair", "value": "sair"},
            ],
            cycle=True,
        ).execute()

        if escolha == "download":
            menu_download()
        elif escolha == "conversao":
            menu_conversao()
        else:
            _clear_screen()
            print("Encerrando...")
            return


def menu_download():
    while True:
        _clear_screen()
        novel = _selecionar_novel()
        if not novel:
            return

        _clear_screen()
        print(f"Carregando capitulos de: {novel['title']}")
        capitulos = extrair_links_pdf(novel["url"])
        if not capitulos:
            inquirer.confirm(message="Nenhum capitulo encontrado. Voltar?", default=True).execute()
            continue

        selecionados = _selecionar_capitulos_ou_volumes(capitulos)
        if not selecionados:
            if not inquirer.confirm(
                message="Nenhum capitulo selecionado. Tentar novamente?",
                default=True,
            ).execute():
                return
            continue

        gerar_cbz = _perguntar_formato_saida()
        volumes = ", ".join(_listar_volumes(selecionados))
        _clear_screen()
        print(f"Novel: {novel['title']}")
        print(f"Capitulos selecionados: {len(selecionados)}")
        print(f"Volumes: {volumes}")
        if not inquirer.confirm(message="Continuar com o download?", default=True).execute():
            if not inquirer.confirm(message="Selecionar outra novel?", default=True).execute():
                return
            continue

        download_capitulos_novel(selecionados, novel["title"], gerar_cbz=gerar_cbz)
        if not inquirer.confirm(message="Deseja baixar outra novel?", default=False).execute():
            return


def menu_conversao():
    while True:
        _clear_screen()
        escolha = inquirer.select(
            message="MENU CONVERSAO",
            choices=[
                {"name": "Converter arquivo PDF", "value": "arquivo"},
                {"name": "Converter pasta", "value": "pasta"},
                {"name": "Converter tudo (com subpastas)", "value": "pasta_rec"},
                {"name": "Configuracoes", "value": "config"},
                {"name": "Voltar", "value": "voltar"},
            ],
            cycle=True,
        ).execute()

        if escolha == "voltar":
            return

        if escolha == "config":
            _clear_screen()
            print("CONFIGURACOES")
            print("=" * 40)
            print(f"Qualidade JPG: {QUALIDADE_JPG}")
            print(f"DPI: {DPI}")
            inquirer.confirm(message="Voltar", default=True).execute()
            continue

        if escolha == "arquivo":
            _converter_arquivo()
            continue

        if escolha == "pasta":
            _converter_pasta(recursive=False)
            continue

        if escolha == "pasta_rec":
            _converter_pasta(recursive=True)


def _selecionar_novel():
    top_novels = listar_top_novels(limite=10)
    choices = [{"name": f"{index}. {item['title']}", "value": item} for index, item in enumerate(top_novels, 1)]
    choices.extend(
        [
            {"name": "Buscar por nome", "value": "buscar"},
            {"name": "Informar link da novel", "value": "link"},
            {"name": "Voltar", "value": None},
        ]
    )

    escolha = inquirer.select(
        message="Escolha uma novel",
        choices=choices,
        cycle=True,
        height=min(20, len(choices) + 2),
    ).execute()

    if escolha is None:
        return None
    if isinstance(escolha, dict):
        return escolha
    if escolha == "link":
        return _selecionar_novel_por_link()
    return _selecionar_novel_por_busca()


def _selecionar_novel_por_link():
    while True:
        entrada = inquirer.text(message="Cole o link da novel (ou vazio para voltar):").execute().strip()
        if not entrada:
            return None
        url = normalizar_url_novel(entrada)
        if not url:
            if not inquirer.confirm(message="Link invalido. Tentar novamente?", default=True).execute():
                return None
            continue
        return {"title": obter_titulo_novel(url), "url": url}


def _selecionar_novel_por_busca():
    termo = inquirer.text(message="Digite o nome da novel (ou vazio para voltar):").execute().strip()
    if not termo:
        return None

    resultados = buscar_novels_por_nome(termo, limite=20)
    if not resultados:
        inquirer.confirm(message="Nenhuma novel encontrada. Voltar?", default=True).execute()
        return None

    escolha = inquirer.select(
        message="Resultados da busca",
        choices=[{"name": item["title"], "value": item} for item in resultados]
        + [{"name": "Voltar", "value": None}],
        cycle=True,
        height=min(20, len(resultados) + 3),
    ).execute()
    return escolha


def _selecionar_capitulos_ou_volumes(capitulos):
    modo = inquirer.select(
        message="Selecione o tipo de download",
        choices=[
            {"name": "Capitulos especificos", "value": "caps"},
            {"name": "Volumes completos", "value": "vols"},
            {"name": "Cancelar", "value": "cancel"},
        ],
        cycle=True,
    ).execute()

    if modo == "cancel":
        return []
    if modo == "caps":
        return _selecionar_capitulos(capitulos)
    return _selecionar_volumes(capitulos)


def _selecionar_capitulos(capitulos):
    cap_nums = sorted({int(item["capitulo"]) for item in capitulos})
    entrada = inquirer.text(
        message=(
            f"Digite os capitulos ({cap_nums[0]} a {cap_nums[-1]}), "
            "ex: 1,2,10-15. Vazio cancela:"
        )
    ).execute().strip()
    if not entrada:
        return []

    try:
        selecionados = set(parse_numero_lista_ou_intervalo(entrada))
    except ValueError:
        inquirer.confirm(message="Formato invalido. Voltar?", default=True).execute()
        return []
    return [item for item in capitulos if int(item["capitulo"]) in selecionados]


def _selecionar_volumes(capitulos):
    volumes_disponiveis = _listar_volumes(capitulos)
    selecionados = inquirer.checkbox(
        message="Selecione um ou mais volumes (espaco marca, enter confirma)",
        choices=[{"name": volume, "value": volume} for volume in volumes_disponiveis],
        cycle=True,
        height=min(20, len(volumes_disponiveis) + 2),
    ).execute()
    if not selecionados:
        return []
    volumes_set = set(selecionados)
    return [item for item in capitulos if item["volume"] in volumes_set]


def _perguntar_formato_saida():
    escolha = inquirer.select(
        message="Formato de saida",
        choices=[
            {"name": "Baixar apenas PDF", "value": "pdf"},
            {"name": "Baixar PDF e converter para CBZ", "value": "cbz"},
        ],
        cycle=True,
    ).execute()
    return escolha == "cbz"


def _converter_arquivo():
    _clear_screen()
    pdf_path = inquirer.text(message="Caminho do PDF (vazio cancela):").execute().strip().strip('"')
    if not pdf_path:
        return
    output_folder = inquirer.text(message="Pasta de saida (vazio = mesma pasta):").execute().strip().strip('"')
    output_folder = output_folder if output_folder else None
    resultado = converter_pdf_para_cbz(pdf_path, output_folder)
    _clear_screen()
    print(f"[SUCESSO] {resultado}" if resultado else "[ERRO] Falhou")
    inquirer.confirm(message="Voltar", default=True).execute()


def _converter_pasta(recursive):
    _clear_screen()
    pasta_path = inquirer.text(message="Caminho da pasta (vazio cancela):").execute().strip().strip('"')
    if not pasta_path:
        return
    output_folder = inquirer.text(message="Pasta de saida (vazio = mesma pasta):").execute().strip().strip('"')
    output_folder = output_folder if output_folder else None
    sucessos, falhas = processar_pasta(pasta_path, output_folder, recursive=recursive)
    _clear_screen()
    _imprimir_resultado_conversao(sucessos, falhas)
    inquirer.confirm(message="Voltar", default=True).execute()


def _listar_volumes(capitulos):
    return sorted({item["volume"] for item in capitulos}, key=_ordenar_volume)


def _ordenar_volume(value):
    texto = str(value).strip()
    if texto.isdigit():
        return (0, int(texto))
    return (1, _normalizar_volume(texto))


def _normalizar_volume(value):
    return " ".join(str(value).strip().lower().split())


def _clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _imprimir_resultado_conversao(sucessos, falhas):
    print(f"\n{'=' * 60}")
    print("RESULTADO")
    print(f"{'=' * 60}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {falhas}")
    print(f"{'=' * 60}")

