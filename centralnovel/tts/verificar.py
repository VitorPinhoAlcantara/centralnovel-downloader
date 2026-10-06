import difflib
import re
import unicodedata

try:
    from num2words import num2words
except ImportError:
    num2words = None

LIMITES_ASR_PADRAO = {
    "cobertura_min": 0.85,
    "sobra_ponto": ("ponto", "pontos", "pont"),
    "fim_ausente_max": 2,
}


def _numeros_por_extenso(texto):
    if num2words is None:
        return texto

    def trocar(m):
        try:
            return num2words(int(m.group(0)), lang="pt_BR")
        except Exception:
            return m.group(0)

    return re.sub(r"\d{1,9}", trocar, texto)


def palavras(texto):
    texto = _numeros_por_extenso(texto)
    texto = unicodedata.normalize("NFKD", str(texto).lower().replace("-", " "))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", texto).split()


def _alinhar(ref, hip, similaridade=0.75):
    mapeada = []
    for palavra in hip:
        melhor, nota = palavra, 0.0
        for candidata in set(ref):
            razao = difflib.SequenceMatcher(a=palavra, b=candidata).ratio()
            if razao > nota:
                melhor, nota = candidata, razao
        mapeada.append(melhor if nota >= similaridade else palavra)
    return mapeada


def analisar(referencia, hipotese, limites=None):
    lim = dict(LIMITES_ASR_PADRAO)
    lim.update(limites or {})
    ref = palavras(referencia)
    hip = _alinhar(ref, palavras(hipotese))
    if not ref:
        return {"ok": True, "motivos": [], "cobertura": 1.0}

    casador = difflib.SequenceMatcher(a=ref, b=hip, autojunk=False)
    blocos = [b for b in casador.get_matching_blocks() if b.size]
    casadas = sum(b.size for b in blocos)
    cobertura = casadas / len(ref)
    fim_ref = max((b.a + b.size for b in blocos), default=0)
    fim_hip = max((b.b + b.size for b in blocos), default=0)
    sobra = hip[fim_hip:]

    motivos = []
    minimo = min(lim["cobertura_min"], (len(ref) - 1) / len(ref))
    if cobertura < minimo:
        motivos.append("pulou_palavras")
    if len(ref) - fim_ref > lim["fim_ausente_max"]:
        motivos.append("fim_ausente")
    if any(p in lim["sobra_ponto"] for p in sobra):
        motivos.append("ponto_falado")
    return {"ok": not motivos, "motivos": motivos, "cobertura": round(cobertura, 3)}
