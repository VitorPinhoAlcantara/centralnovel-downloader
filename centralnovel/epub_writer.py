"""Gera EPUBs minimos (um capitulo por arquivo) sem dependencias externas."""

import uuid
import zipfile
from html import escape

_CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def criar_epub(caminho, titulo_livro, titulo_capitulo, paragrafos, autor="", serie="",
               indice_serie=None, idioma="pt"):
    """Grava um EPUB3 com um unico capitulo.

    `titulo_capitulo` vira o <h1> e e a primeira coisa que o narrador le.
    """
    identificador = f"urn:uuid:{uuid.uuid4()}"
    meta_serie = ""
    if serie:
        meta_serie += (
            f'    <meta property="belongs-to-collection" id="serie">{escape(serie)}</meta>\n'
            '    <meta refines="#serie" property="collection-type">series</meta>\n'
        )
        if indice_serie is not None:
            meta_serie += (
                f'    <meta refines="#serie" property="group-position">{escape(str(indice_serie))}</meta>\n'
                f'    <meta name="calibre:series" content="{escape(serie)}"/>\n'
                f'    <meta name="calibre:series_index" content="{escape(str(indice_serie))}"/>\n'
            )
    autor_xml = f"    <dc:creator>{escape(autor)}</dc:creator>\n" if autor else ""

    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{identificador}</dc:identifier>
    <dc:title>{escape(titulo_livro)}</dc:title>
{autor_xml}    <dc:language>{escape(idioma)}</dc:language>
{meta_serie}  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="cap" href="capitulo.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="cap"/>
  </spine>
</package>
"""
    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{escape(idioma)}">
<head><title>{escape(titulo_livro)}</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <ol><li><a href="capitulo.xhtml">{escape(titulo_capitulo)}</a></li></ol>
  </nav>
</body>
</html>
"""
    corpo = "\n".join(f"  <p>{escape(p)}</p>" for p in paragrafos)
    capitulo = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{escape(idioma)}">
<head><title>{escape(titulo_capitulo)}</title></head>
<body>
  <h1>{escape(titulo_capitulo)}</h1>
{corpo}
</body>
</html>
"""
    with zipfile.ZipFile(caminho, "w") as epub:
        # o 'mimetype' precisa ser o primeiro item e sem compressao
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        epub.writestr("META-INF/container.xml", _CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        epub.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        epub.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        epub.writestr("OEBPS/capitulo.xhtml", capitulo, compress_type=zipfile.ZIP_DEFLATED)
    return caminho
