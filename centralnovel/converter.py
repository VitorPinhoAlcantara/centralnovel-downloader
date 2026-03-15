"""PDF to CBZ conversion workflow."""

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from .config import DPI, QUALIDADE_JPG

try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError:
    print("ERRO: Bibliotecas necessarias nao encontradas!")
    print("\nInstale: pip install pymupdf Pillow")
    sys.exit(1)


def _render_page_to_image(page, dpi):
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    mode = "RGBA" if pix.alpha else "RGB"
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)


def converter_pdf_para_imagens(pdf_path, output_folder, verbose=True):
    if verbose:
        print(f"\n[+] Convertendo: {os.path.basename(pdf_path)}")
        print(f"    Renderizando (DPI: {DPI})...")
    try:
        with fitz.open(pdf_path) as doc:
            total_pages = doc.page_count
            if verbose:
                print(f"    Total: {total_pages} paginas")

            image_paths = []
            digits = len(str(total_pages))
            for index in range(total_pages):
                page = doc.load_page(index)
                image = _render_page_to_image(page, DPI)
                image_name = f"{str(index + 1).zfill(digits)}.jpg"
                image_path = os.path.join(output_folder, image_name)
                image.save(image_path, "JPEG", quality=QUALIDADE_JPG, optimize=True)
                image_paths.append(image_path)
                if verbose and (index + 1) % 5 == 0:
                    print(f"    Processando: {index + 1}/{total_pages}...")

        if verbose:
            print(f"    [OK] {len(image_paths)} imagens")
        return image_paths
    except Exception as exc:
        print(f"    [ERRO] {exc}")
        return []


def criar_cbz(image_paths, cbz_path, verbose=True):
    if verbose:
        print(f"\n[+] Criando CBZ: {os.path.basename(cbz_path)}")
    try:
        with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as cbz:
            for index, img_path in enumerate(image_paths, 1):
                cbz.write(img_path, os.path.basename(img_path))
                if verbose and index % 10 == 0:
                    print(f"    Compactando: {index}/{len(image_paths)}...")
        if verbose:
            file_size = os.path.getsize(cbz_path) / (1024 * 1024)
            print(f"    [OK] {file_size:.2f} MB")
        return True
    except Exception as exc:
        print(f"    [ERRO] {exc}")
        return False


def converter_pdf_para_cbz(pdf_path, output_folder=None, keep_images=False, verbose=True):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"[ERRO] Nao encontrado: {pdf_path}")
        return None
    if pdf_path.suffix.lower() != ".pdf":
        print(f"[ERRO] Nao e PDF: {pdf_path}")
        return None

    if output_folder is None:
        output_path = pdf_path.parent
    else:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

    cbz_path = output_path / f"{pdf_path.stem}.cbz"
    if cbz_path.exists():
        print(f"[!] Ja existe: {cbz_path.name}")
        resposta = input("    Sobrescrever? (s/n): ")
        if resposta.lower() != "s":
            print("    [CANCELADO]")
            return None

    temp_dir = tempfile.mkdtemp(prefix="pdf2cbz_")
    try:
        image_paths = converter_pdf_para_imagens(pdf_path, temp_dir, verbose=verbose)
        if not image_paths:
            print("[ERRO] Nenhuma imagem gerada")
            return None
        if criar_cbz(image_paths, str(cbz_path), verbose=verbose):
            if verbose:
                print(f"\n[SUCESSO] {cbz_path.name}")
            return str(cbz_path)
        return None
    finally:
        if not keep_images:
            try:
                shutil.rmtree(temp_dir)
            except Exception as exc:
                if verbose:
                    print(f"[AVISO] Pasta temp: {exc}")


def processar_pasta(pasta_path, output_folder=None, recursive=False, verbose=True):
    pasta_path = Path(pasta_path)
    if not pasta_path.exists() or not pasta_path.is_dir():
        print(f"[ERRO] Pasta nao encontrada: {pasta_path}")
        return 0, 0

    pdf_files = list(pasta_path.rglob("*.pdf")) if recursive else list(pasta_path.glob("*.pdf"))
    if not pdf_files:
        print(f"[AVISO] Nenhum PDF: {pasta_path}")
        return 0, 0

    print(f"\n{'=' * 60}")
    print("CONVERSAO EM LOTE")
    print(f"{'=' * 60}")
    print(f"Pasta: {pasta_path}")
    print(f"PDFs: {len(pdf_files)}")
    print(f"{'=' * 60}")

    confirmacao = input("\nContinuar? (s/n): ")
    if confirmacao.lower() != "s":
        print("[CANCELADO]")
        return 0, 0

    sucessos = 0
    falhas = 0
    for index, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'=' * 60}")
        print(f"[{index}/{len(pdf_files)}] {pdf_file.name}")
        print(f"{'=' * 60}")
        resultado = converter_pdf_para_cbz(
            pdf_file,
            output_folder=output_folder,
            keep_images=False,
            verbose=verbose,
        )
        if resultado:
            sucessos += 1
        else:
            falhas += 1
    return sucessos, falhas

