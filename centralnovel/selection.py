"""Selection parsing helpers."""


def parse_numero_lista_ou_intervalo(texto):
    valores = set()
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            inicio_str, fim_str = parte.split("-", 1)
            inicio = int(inicio_str.strip())
            fim = int(fim_str.strip())
            if inicio > fim:
                inicio, fim = fim, inicio
            for numero in range(inicio, fim + 1):
                valores.add(numero)
        else:
            valores.add(int(parte))
    return sorted(valores)

