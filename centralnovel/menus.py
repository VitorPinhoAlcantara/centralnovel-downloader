"""CLI menus for downloader and converter."""

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


def menu_download():
    print("=" * 60)
    print("DOWNLOAD DE NOVEL")
    print("=" * 60)

    while True:
        novel = _selecionar_novel()
        if not novel:
            return

        capitulos = extrair_links_pdf(novel["url"])
        if not capitulos:
            print("Nenhum capitulo encontrado para esta novel.")
            continue

        selecionados = _selecionar_capitulos_ou_volumes(capitulos)
        if not selecionados:
            print("Nenhum capitulo selecionado.")
            continue

        gerar_cbz = _perguntar_formato_saida()
        print(
            f"\nNovel: {novel['title']}\n"
            f"Capitulos selecionados: {len(selecionados)}\n"
            f"Volumes: {', '.join(_listar_volumes(selecionados))}"
        )

        confirmacao = input("\nContinuar com o download? (s/n): ").strip().lower()
        if confirmacao != "s":
            print("Cancelado.")
            continue

        download_capitulos_novel(selecionados, novel["title"], gerar_cbz=gerar_cbz)

        repetir = input("\nDeseja baixar outra novel? (s/n): ").strip().lower()
        if repetir != "s":
            break


def menu_conversao():
    print("=" * 60)
    print("PDF para CBZ - Conversor")
    print("=" * 60)

    while True:
        print("\nMENU CONVERSAO")
        print("-" * 40)
        print("1. Converter arquivo PDF")
        print("2. Converter pasta")
        print("3. Converter tudo (com subpastas)")
        print("4. Configuracoes")
        print("5. Voltar")
        print("-" * 40)
        escolha = input("\nOpcao: ").strip()

        if escolha == "1":
            pdf_path = input("\nPDF: ").strip().strip('"')
            if not pdf_path:
                print("[ERRO] Caminho vazio")
                continue
            output_folder = input("Saida (Enter = mesma pasta): ").strip().strip('"')
            output_folder = output_folder if output_folder else None
            resultado = converter_pdf_para_cbz(pdf_path, output_folder)
            print(f"\n[SUCESSO] {resultado}" if resultado else "\n[ERRO] Falhou")
        elif escolha == "2":
            pasta_path = input("\nPasta: ").strip().strip('"')
            if not pasta_path:
                print("[ERRO] Caminho vazio")
                continue
            output_folder = input("Saida (Enter = mesma pasta): ").strip().strip('"')
            output_folder = output_folder if output_folder else None
            sucessos, falhas = processar_pasta(pasta_path, output_folder, recursive=False)
            _imprimir_resultado_conversao(sucessos, falhas)
        elif escolha == "3":
            pasta_path = input("\nPasta: ").strip().strip('"')
            if not pasta_path:
                print("[ERRO] Caminho vazio")
                continue
            output_folder = input("Saida (Enter = mesma pasta): ").strip().strip('"')
            output_folder = output_folder if output_folder else None
            sucessos, falhas = processar_pasta(pasta_path, output_folder, recursive=True)
            _imprimir_resultado_conversao(sucessos, falhas)
        elif escolha == "4":
            print("\n" + "=" * 60)
            print("CONFIGURACOES")
            print("=" * 60)
            print(f"Qualidade JPG: {QUALIDADE_JPG}")
            print(f"DPI: {DPI}")
            print("=" * 60)
            input("\nEnter...")
        elif escolha == "5":
            break
        else:
            print("[ERRO] Opcao invalida")


def menu_principal():
    while True:
        print("\n" + "=" * 60)
        print("CENTRALNOVEL - MAIN")
        print("=" * 60)
        print("1. Download de novel")
        print("2. Conversao PDF -> CBZ")
        print("3. Sair")
        print("-" * 40)
        escolha = input("\nOpcao: ").strip()

        if escolha == "1":
            menu_download()
        elif escolha == "2":
            menu_conversao()
        elif escolha == "3":
            print("\nEncerrando...")
            break
        else:
            print("Opcao invalida")


def _selecionar_novel():
    top_novels = listar_top_novels(limite=10)
    if top_novels:
        print("\nTop 10 novels:")
        for index, novel in enumerate(top_novels, 1):
            print(f"{index}. {novel['title']}")
    else:
        print("\nNao foi possivel carregar o top 10 agora.")

    print("\nDigite o numero da lista, nome da novel, link da novel, ou 'v' para voltar.")
    entrada = input("Escolha: ").strip()
    if entrada.lower() == "v":
        return None

    if entrada.isdigit() and top_novels:
        idx = int(entrada)
        if 1 <= idx <= len(top_novels):
            return top_novels[idx - 1]
        print("Indice invalido.")
        return None

    url = normalizar_url_novel(entrada)
    if url:
        return {"title": obter_titulo_novel(url), "url": url}

    resultados = buscar_novels_por_nome(entrada, limite=10)
    if not resultados:
        print("Nenhuma novel encontrada para esse nome.")
        return None

    print("\nResultados:")
    for index, item in enumerate(resultados, 1):
        print(f"{index}. {item['title']}")
    escolha = input("Selecione o numero do resultado (ou Enter para cancelar): ").strip()
    if not escolha:
        return None
    if not escolha.isdigit():
        print("Entrada invalida.")
        return None
    idx = int(escolha)
    if not (1 <= idx <= len(resultados)):
        print("Indice invalido.")
        return None
    return resultados[idx - 1]


def _selecionar_capitulos_ou_volumes(capitulos):
    volumes_disponiveis = _listar_volumes(capitulos)
    cap_nums = sorted({int(item["capitulo"]) for item in capitulos})
    print("\nSelecao de download:")
    print("1. Capitulos especificos (ex: 1,2,10-15)")
    print("2. Volumes completos (ex: 1,2,5-7)")
    escolha = input("Opcao: ").strip()

    if escolha == "1":
        print(f"Capitulos disponiveis: {cap_nums[0]} ate {cap_nums[-1]}")
        entrada = input("Digite os capitulos: ").strip()
        try:
            selecionados = set(parse_numero_lista_ou_intervalo(entrada))
        except ValueError:
            print("Formato invalido.")
            return []
        return [item for item in capitulos if int(item["capitulo"]) in selecionados]

    if escolha == "2":
        print("Volumes disponiveis:")
        for index, volume in enumerate(volumes_disponiveis, 1):
            print(f"{index}. {volume}")
        print("Digite indices (ex: 1,3-5) ou nomes (ex: Extra, Side Story 1)")
        entrada = input("Digite os volumes: ").strip()
        return _filtrar_por_volumes(capitulos, volumes_disponiveis, entrada)

    print("Opcao invalida.")
    return []


def _perguntar_formato_saida():
    print("\nFormato de saida:")
    print("1. Baixar apenas PDF")
    print("2. Baixar PDF e converter para CBZ")
    escolha = input("Opcao: ").strip()
    return escolha == "2"


def _listar_volumes(capitulos):
    return sorted({item["volume"] for item in capitulos}, key=_ordenar_volume)


def _filtrar_por_volumes(capitulos, volumes_disponiveis, entrada):
    if not entrada:
        return []

    try:
        indices = parse_numero_lista_ou_intervalo(entrada)
        validos = [idx for idx in indices if 1 <= idx <= len(volumes_disponiveis)]
        volumes_escolhidos = {volumes_disponiveis[idx - 1] for idx in validos}
        return [item for item in capitulos if item["volume"] in volumes_escolhidos]
    except ValueError:
        nomes = {_normalizar_volume(parte) for parte in entrada.split(",") if parte.strip()}
        return [item for item in capitulos if _normalizar_volume(item["volume"]) in nomes]


def _ordenar_volume(value):
    texto = str(value).strip()
    if texto.isdigit():
        return (0, int(texto))
    return (1, _normalizar_volume(texto))


def _normalizar_volume(value):
    return " ".join(str(value).strip().lower().split())


def _imprimir_resultado_conversao(sucessos, falhas):
    print(f"\n{'=' * 60}")
    print("RESULTADO")
    print(f"{'=' * 60}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {falhas}")
    print(f"{'=' * 60}")
