#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError:
    print("ERRO: Bibliotecas necessarias nao encontradas!")
    print("\nInstale: pip install pymupdf Pillow")
    sys.exit(1)

QUALIDADE_JPG = 95
DPI = 150

def _render_page_to_image(page, dpi):
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    mode = "RGBA" if pix.alpha else "RGB"
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)


def converter_pdf_para_imagens(pdf_path, output_folder, verbose=True):
    if verbose:
        print(f"\n[+] Convertendo: {os.path.basename(pdf_path)}")

    try:
        if verbose:
            print(f"    Renderizando (DPI: {DPI})...")

        with fitz.open(pdf_path) as doc:
            total_pages = doc.page_count
            if verbose:
                print(f"    Total: {total_pages} paginas")

            image_paths = []
            digits = len(str(total_pages))

            for i in range(total_pages):
                page = doc.load_page(i)
                image = _render_page_to_image(page, DPI)
                image_name = f"{str(i + 1).zfill(digits)}.jpg"
                image_path = os.path.join(output_folder, image_name)
                image.save(image_path, 'JPEG', quality=QUALIDADE_JPG, optimize=True)
                image_paths.append(image_path)

                if verbose and (i + 1) % 5 == 0:
                    print(f"    Processando: {i + 1}/{total_pages}...")

        if verbose:
            print(f"    [OK] {len(image_paths)} imagens")

        return image_paths
    except Exception as e:
        print(f"    [ERRO] {e}")
        return []


def criar_cbz(image_paths, cbz_path, verbose=True):
    if verbose:
        print(f"\n[+] Criando CBZ: {os.path.basename(cbz_path)}")

    try:
        with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as cbz:
            for i, img_path in enumerate(image_paths, 1):
                cbz.write(img_path, os.path.basename(img_path))
                if verbose and i % 10 == 0:
                    print(f"    Compactando: {i}/{len(image_paths)}...")

        if verbose:
            file_size = os.path.getsize(cbz_path) / (1024 * 1024)
            print(f"    [OK] {file_size:.2f} MB")

        return True
    except Exception as e:
        print(f"    [ERRO] {e}")
        return False


def converter_pdf_para_cbz(pdf_path, output_folder=None, keep_images=False, verbose=True):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"[ERRO] Não encontrado: {pdf_path}")
        return None

    if pdf_path.suffix.lower() != '.pdf':
        print(f"[ERRO] Não é PDF: {pdf_path}")
        return None

    if output_folder is None:
        output_folder = pdf_path.parent
    else:
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

    cbz_name = pdf_path.stem + '.cbz'
    cbz_path = output_folder / cbz_name

    if cbz_path.exists():
        print(f"[!] Já existe: {cbz_name}")
        resposta = input("    Sobrescrever? (s/n): ")
        if resposta.lower() != 's':
            print("    [CANCELADO]")
            return None

    temp_dir = tempfile.mkdtemp(prefix='pdf2cbz_')

    try:
        image_paths = converter_pdf_para_imagens(pdf_path, temp_dir, verbose)
        if not image_paths:
            print("[ERRO] Nenhuma imagem gerada")
            return None

        if criar_cbz(image_paths, str(cbz_path), verbose):
            if verbose:
                print(f"\n[SUCESSO] {cbz_name}")
            return str(cbz_path)
        else:
            return None
    finally:
        if not keep_images:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                if verbose:
                    print(f"[AVISO] Pasta temp: {e}")


def processar_pasta(pasta_path, output_folder=None, recursive=False, verbose=True):
    pasta_path = Path(pasta_path)

    if not pasta_path.exists() or not pasta_path.is_dir():
        print(f"[ERRO] Pasta não encontrada: {pasta_path}")
        return 0, 0

    if recursive:
        pdf_files = list(pasta_path.rglob('*.pdf'))
    else:
        pdf_files = list(pasta_path.glob('*.pdf'))

    if not pdf_files:
        print(f"[AVISO] Nenhum PDF: {pasta_path}")
        return 0, 0

    print(f"\n{'='*60}")
    print(f"CONVERSAO EM LOTE")
    print(f"{'='*60}")
    print(f"Pasta: {pasta_path}")
    print(f"PDFs: {len(pdf_files)}")
    print(f"{'='*60}")

    confirmacao = input("\nContinuar? (s/n): ")
    if confirmacao.lower() != 's':
        print("[CANCELADO]")
        return 0, 0

    sucessos = falhas = 0

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        print(f"{'='*60}")

        resultado = converter_pdf_para_cbz(pdf_file, output_folder=output_folder, keep_images=False, verbose=verbose)

        if resultado:
            sucessos += 1
        else:
            falhas += 1

    return sucessos, falhas


def menu_principal():
    print("="*60)
    print("PDF para CBZ - Conversor")
    print("="*60)

    while True:
        print("\nMENU")
        print("-" * 40)
        print("1. Converter arquivo PDF")
        print("2. Converter pasta")
        print("3. Converter tudo (com subpastas)")
        print("4. Configuracoes")
        print("5. Sair")
        print("-" * 40)

        escolha = input("\nOpcao: ").strip()

        if escolha == '1':
            pdf_path = input("\nPDF: ").strip().strip('"')
            if not pdf_path:
                print("[ERRO] Caminho vazio")
                continue

            output_folder = input("Saida (Enter = mesma pasta): ").strip().strip('"')
            output_folder = output_folder if output_folder else None

            resultado = converter_pdf_para_cbz(pdf_path, output_folder)
            if resultado:
                print(f"\n[SUCESSO] {resultado}")
            else:
                print("\n[ERRO] Falhou")

        elif escolha == '2':
            pasta_path = input("\nPasta: ").strip().strip('"')
            if not pasta_path:
                print("[ERRO] Caminho vazio")
                continue

            output_folder = input("Saida (Enter = mesma pasta): ").strip().strip('"')
            output_folder = output_folder if output_folder else None

            sucessos, falhas = processar_pasta(pasta_path, output_folder, recursive=False)

            print(f"\n{'='*60}")
            print(f"RESULTADO")
            print(f"{'='*60}")
            print(f"Sucessos: {sucessos}")
            print(f"Falhas: {falhas}")
            print(f"{'='*60}")

        elif escolha == '3':
            pasta_path = input("\nPasta: ").strip().strip('"')
            if not pasta_path:
                print("[ERRO] Caminho vazio")
                continue

            output_folder = input("Saida (Enter = mesma pasta): ").strip().strip('"')
            output_folder = output_folder if output_folder else None

            sucessos, falhas = processar_pasta(pasta_path, output_folder, recursive=True)

            print(f"\n{'='*60}")
            print(f"RESULTADO")
            print(f"{'='*60}")
            print(f"Sucessos: {sucessos}")
            print(f"Falhas: {falhas}")
            print(f"{'='*60}")

        elif escolha == '4':
            print("\n" + "="*60)
            print("CONFIGURACOES")
            print("="*60)
            print(f"Qualidade JPG: {QUALIDADE_JPG}")
            print(f"DPI: {DPI}")
            print("="*60)
            print("\nEdite no script:")
            print("  QUALIDADE_JPG = 95")
            print("  DPI = 150")
            input("\nEnter...")

        elif escolha == '5':
            print("\nEncerrando...")
            break

        else:
            print("[ERRO] Opcao invalida")


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\nInterrompido")
    except Exception as e:
        print(f"\n[ERRO] {e}")
