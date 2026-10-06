import re

TAMANHO_MIN = 60
TAMANHO_MAX = 180
TETO_XTTS = 203

_ABREVIACOES = (
    "Sr", "Sra", "Srta", "Dr", "Dra", "Prof", "Profa", "Ex", "Exa", "Ilmo", "Gen", "Cap",
    "Cel", "Maj", "Sgt", "Tte", "Av", "etc", "vs", "p", "pág", "nº", "No",
)
_RE_ABREVIACAO = re.compile(r"\b(" + "|".join(re.escape(a) for a in _ABREVIACOES) + r")\.", re.IGNORECASE)
_MARCA = "\u0001"
_RE_FIM_FRASE = re.compile(
    r"(?<=[.!?…])([\"”’')\]]*)\s+(?=[\"“‘'(\[—–-]?\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9\[])"
)
_RE_VIRGULA = re.compile(r"(?<=[,;:])\s+")


def dividir_paragrafos(paragrafos, tamanho_min=TAMANHO_MIN, tamanho_max=TAMANHO_MAX,
                       pausa_frase_ms=250, pausa_paragrafo_ms=700):
    trechos = []
    for paragrafo in paragrafos:
        texto = " ".join(str(paragrafo).split())
        if not texto:
            continue
        pedacos = _dividir_paragrafo(texto, tamanho_min, tamanho_max)
        for i, pedaco in enumerate(pedacos):
            ultimo = i == len(pedacos) - 1
            trechos.append({
                "texto": pedaco,
                "pausa_ms": pausa_paragrafo_ms if ultimo else pausa_frase_ms,
            })
    for indice, trecho in enumerate(trechos):
        trecho["id"] = f"{indice:04d}"
    return trechos


def _dividir_paragrafo(texto, tamanho_min, tamanho_max):
    protegido = _RE_ABREVIACAO.sub(lambda m: m.group(1) + _MARCA, texto)
    frases = [f.replace(_MARCA, ".").strip() for f in _RE_FIM_FRASE.split(protegido) if f is not None]
    frases = _recolar_fechamentos(frases)

    limitadas = []
    for frase in frases:
        limitadas.extend(_quebrar_longa(frase, tamanho_max))

    juntas = []
    atual = ""
    for frase in limitadas:
        if atual and len(atual) < tamanho_min and len(atual) + 1 + len(frase) <= tamanho_max:
            atual = f"{atual} {frase}"
            continue
        if atual:
            juntas.append(atual)
        atual = frase
    if atual:
        if juntas and len(atual) < tamanho_min // 2 and len(juntas[-1]) + 1 + len(atual) <= tamanho_max:
            juntas[-1] = f"{juntas[-1]} {atual}"
        else:
            juntas.append(atual)
    return juntas


def _recolar_fechamentos(partes):
    resultado = []
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        if resultado and re.fullmatch(r"[\"”’')\]]+", parte):
            resultado[-1] += parte
        else:
            resultado.append(parte)
    return resultado


def _quebrar_longa(frase, tamanho_max):
    if len(frase) <= tamanho_max:
        return [frase]
    partes = [p for p in _RE_VIRGULA.split(frase) if p]
    saida = []
    atual = ""
    for parte in partes:
        if atual and len(atual) + 1 + len(parte) > tamanho_max:
            saida.append(atual)
            atual = parte
        else:
            atual = f"{atual} {parte}".strip()
    if atual:
        saida.append(atual)

    final = []
    for pedaco in saida:
        while len(pedaco) > TETO_XTTS:
            corte = pedaco.rfind(" ", 0, tamanho_max)
            if corte <= 0:
                corte = tamanho_max
            final.append(pedaco[:corte].strip())
            pedaco = pedaco[corte:].strip()
        if pedaco:
            final.append(pedaco)
    return final
