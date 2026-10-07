import re

try:
    from num2words import num2words
except ImportError:
    num2words = None

OPCOES_PADRAO = {
    "hifen_pronome": "manter",
    "hifen_composta": "manter",
    "travessao": "manter",
    "reticencias": "virgula",
    "colchetes": "manter",
    "numeros": "extenso",
    "ponto_interno": "normal",
    "abreviacoes": "expandir",
    "interjeicoes": "manter",
}

_PRONOMES = r"(?:se|me|te|lhe|lhes|lo|la|los|las|nos|vos|o|a|os|as|no|na|nas)"
_RE_ENCLISE = re.compile(rf"(?<=[A-Za-zÀ-ÿ])-(?={_PRONOMES}\b)", re.IGNORECASE)
_RE_MESOCLISE = re.compile(rf"(?<=[A-Za-zÀ-ÿ])-({_PRONOMES})-(?=[A-Za-zÀ-ÿ])", re.IGNORECASE)
_RE_HIFEN_LETRAS = re.compile(r"(?<=[A-Za-zÀ-ÿ])-(?=[A-Za-zÀ-ÿ])")
_RE_TRAVESSAO_INICIO = re.compile(r"^\s*[—–]\s*")
_RE_TRAVESSAO_MEIO = re.compile(r"(?<=[.!?…])\s+[—–]\s+|\s+[—–]\s+")
_RE_RETICENCIAS = re.compile(r"\.{3,}|…")
_RE_COLCHETES = re.compile(r"\[([^\[\]]+)\]")
_RE_NUMERO = re.compile(r"(?<![\w.,])(\d{1,9})(?![\w.,]*\d)")
_RE_MILHAR = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+)(?![\w.,]*\d)")
_RE_BARRA_NUMEROS = re.compile(r"(?<![\w/])(\d[\d.,]*)\s*/\s*(\d[\d.,]*)(?![\w/])")
_INTERJ = (
    r"(?:ha(?:ha)*h?|h[ae]h[ae]*|hee+|rá(?:[- ]?rá)*|a{1,3}rg+h*|ugh+|gr{2,}h*|h?m{2,}|hm+|hum+|uh+m*"
    r"|tsc|pf+t*|k{3,})"
)
_RE_INTERJ = re.compile(
    rf"(^|[.!?…:]\s+|[“\"—–-]\s*)(?:(?<![A-Za-zÀ-ÿ]){_INTERJ}(?![A-Za-zÀ-ÿ])[\s,!.?…-]*)+",
    re.IGNORECASE,
)
_RE_FINAL_PONTO = re.compile(r"^(.*?[^.\s])\.([\"”’')\]]*)$", re.DOTALL)
_RE_ABREV = re.compile(r"\b(Sr|Sra|Srta|Dr|Dra|Prof|Profa|Cap)\.", re.IGNORECASE)
_EXPANSAO = {"sr": "Senhor", "sra": "Senhora", "srta": "Senhorita", "dr": "Doutor",
             "dra": "Doutora", "prof": "Professor", "profa": "Professora", "cap": "Capítulo"}


def normalizar(texto, opcoes=None):
    cfg = dict(OPCOES_PADRAO)
    cfg.update(opcoes or {})
    texto = " ".join(str(texto).split())

    if cfg["abreviacoes"] == "expandir":
        texto = _RE_ABREV.sub(lambda m: _EXPANSAO[m.group(1).lower()], texto)
    if cfg["interjeicoes"] == "remover":
        texto = _RE_INTERJ.sub(r"\1", texto)
    texto = _aplicar_travessao(texto, cfg["travessao"])
    texto = _aplicar_colchetes(texto, cfg["colchetes"])
    texto = _aplicar_reticencias(texto, cfg["reticencias"])
    texto = _aplicar_hifens(texto, cfg["hifen_pronome"], cfg["hifen_composta"])
    texto = _RE_MILHAR.sub(lambda m: m.group(1).replace(".", ""), texto)
    texto = _RE_BARRA_NUMEROS.sub(r"\1 de \2", texto)
    texto = _aplicar_numeros(texto, cfg["numeros"])
    texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)
    texto = " ".join(texto.split())
    if cfg["ponto_interno"] == "e2a":
        texto = texto.replace(".", " ;\n")
    return texto


def ajustar_final(texto, modo):
    texto = texto.rstrip()
    achado = _RE_FINAL_PONTO.match(texto)
    if modo == "ponto" or not achado:
        return texto
    corpo, fecho = achado.group(1).rstrip(), achado.group(2)
    if modo == "sem":
        return corpo + fecho
    if modo == "virgula":
        return corpo + "," + fecho
    if modo == "espaco":
        return corpo + " ." + fecho
    if modo == "e2a":
        return corpo + " ;\n" + fecho
    if modo == "ponto_nl":
        return corpo + ".\n" + fecho
    return texto


def _aplicar_travessao(texto, modo):
    if modo == "manter":
        return texto
    iniciou_dialogo = bool(_RE_TRAVESSAO_INICIO.match(texto))
    texto = _RE_TRAVESSAO_INICIO.sub("", texto)
    texto = _RE_TRAVESSAO_MEIO.sub(_trocar_travessao_meio, texto)
    if modo == "aspas" and iniciou_dialogo:
        return f"“{texto}”"
    return texto


def _trocar_travessao_meio(m):
    antes = m.string[: m.start()].rstrip()
    return " " if antes.endswith((".", "!", "?", "…")) else ", "


def _aplicar_colchetes(texto, modo):
    if modo == "manter":
        return texto
    if modo == "aspas":
        return _RE_COLCHETES.sub(r"“\1”", texto)
    return _RE_COLCHETES.sub(r"\1", texto)


def _aplicar_reticencias(texto, modo):
    if modo == "tres_pontos":
        return _RE_RETICENCIAS.sub("...", texto)
    if modo == "virgula":
        texto = _RE_RETICENCIAS.sub("...", texto)
        texto = re.sub(r"^\s*\.{3}\s*", "", texto)
        texto = re.sub(r"\s*\.{3}\s*(?=[a-zà-ÿ])", ", ", texto)
        texto = re.sub(r"\s*\.{3}\s*$", ".", texto)
        return re.sub(r"\s*\.{3}\s*(?=\S)", ". ", texto)
    return texto


def _aplicar_hifens(texto, modo_pronome, modo_composta):
    trocas = {"colar": "", "espaco": " "}
    if modo_pronome in trocas:
        molde = r"\1" if modo_pronome == "colar" else r" \1 "
        texto = _RE_MESOCLISE.sub(molde, texto)
        texto = _RE_ENCLISE.sub(trocas[modo_pronome], texto)
        texto = _RE_ENCLISE.sub(trocas[modo_pronome], texto)
    if modo_composta in trocas:
        texto = _RE_HIFEN_LETRAS.sub(trocas[modo_composta], texto)
    return texto


def _aplicar_numeros(texto, modo):
    if modo != "extenso" or num2words is None:
        return texto

    def trocar(m):
        try:
            return num2words(int(m.group(1)), lang="pt_BR")
        except Exception:
            return m.group(1)

    return _RE_NUMERO.sub(trocar, texto)
