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

_CSS = "body{font-family:serif;line-height:1.5}h1{font-size:1.4em;margin:1em 0}p{margin:0 0 .8em}"


def criar_epub_volume(caminho, titulo_livro, capitulos, autor="", serie="", indice_serie=None,
                      idioma="pt"):
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

    itens = "".join(
        f'    <item id="cap{i}" href="cap_{i:04d}.xhtml" media-type="application/xhtml+xml"/>\n'
        for i in range(len(capitulos))
    )
    spine = "".join(f'    <itemref idref="cap{i}"/>\n' for i in range(len(capitulos)))
    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{identificador}</dc:identifier>
    <dc:title>{escape(titulo_livro)}</dc:title>
{autor_xml}    <dc:language>{escape(idioma)}</dc:language>
{meta_serie}  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="css" href="estilo.css" media-type="text/css"/>
{itens}  </manifest>
  <spine>
{spine}  </spine>
</package>
"""
    entradas_nav = "".join(
        f'      <li><a href="cap_{i:04d}.xhtml">{escape(titulo)}</a></li>\n'
        for i, (titulo, _) in enumerate(capitulos)
    )
    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{escape(idioma)}">
<head><title>{escape(titulo_livro)}</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <ol>
{entradas_nav}    </ol>
  </nav>
</body>
</html>
"""
    with zipfile.ZipFile(caminho, "w") as epub:
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        epub.writestr("META-INF/container.xml", _CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        epub.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        epub.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        epub.writestr("OEBPS/estilo.css", _CSS, compress_type=zipfile.ZIP_DEFLATED)
        for i, (titulo, paragrafos) in enumerate(capitulos):
            corpo = "\n".join(f"  <p>{escape(p)}</p>" for p in paragrafos)
            pagina = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{escape(idioma)}">
<head><title>{escape(titulo)}</title><link rel="stylesheet" type="text/css" href="estilo.css"/></head>
<body>
  <h1>{escape(titulo)}</h1>
{corpo}
</body>
</html>
"""
            epub.writestr(f"OEBPS/cap_{i:04d}.xhtml", pagina, compress_type=zipfile.ZIP_DEFLATED)
    return caminho
