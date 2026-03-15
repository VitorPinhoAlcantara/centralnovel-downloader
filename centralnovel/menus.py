"""CLI menus for downloader and converter."""

from .config import BASE_URL, DPI, QUALIDADE_JPG
from .converter import converter_pdf_para_cbz, processar_pasta
from .csv_store import salvar_links_csv
from .downloader import (
    download_capitulo_especifico,
    download_intervalo,
    download_todos,
    download_volume,
)
from .scraper import extrair_links_pdf


def menu_download():
    print("=" * 60)
    print("LORD OF MYSTERIES - DOWNLOADER DE PDFs")
    print("=" * 60)

    while True:
        print("\nMENU DOWNLOAD")
        print("-" * 40)
        print("1. Extrair links")
        print("2. Baixar todos")
        print("3. Baixar capitulo especifico")
        print("4. Baixar intervalo")
        print("5. Baixar volume")
        print("6. Voltar")
        print("-" * 40)
        escolha = input("\nOpcao: ").strip()

        if escolha == "1":
            dados = extrair_links_pdf(BASE_URL)
            if dados:
                salvar_links_csv(dados)
                volumes = set(item["volume"] for item in dados)
                print(f"\nCapitulos: {len(dados)}")
                print(f"Volumes: {', '.join(sorted(volumes))}")
        elif escolha == "2":
            download_todos()
        elif escolha == "3":
            try:
                numero = int(input("\nCapitulo: ").strip())
                download_capitulo_especifico(numero)
            except ValueError:
                print("Numero invalido")
        elif escolha == "4":
            try:
                intervalo = input("\nIntervalo (ex: 10-200): ").strip()
                inicio, fim = map(int, intervalo.split("-"))
                if inicio > fim:
                    print("Inicio deve ser menor que fim")
                else:
                    download_intervalo(inicio, fim)
            except ValueError:
                print("Formato invalido")
        elif escolha == "5":
            try:
                numero_volume = int(input("\nVolume: ").strip())
                download_volume(numero_volume)
            except ValueError:
                print("Numero invalido")
        elif escolha == "6":
            break
        else:
            print("Opcao invalida")


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
        print("1. Download de PDFs")
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


def _imprimir_resultado_conversao(sucessos, falhas):
    print(f"\n{'=' * 60}")
    print("RESULTADO")
    print(f"{'=' * 60}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {falhas}")
    print(f"{'=' * 60}")

