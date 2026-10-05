"""Gera audiolivros dos capitulos: texto do site -> EPUB -> ebook2audiobook -> Audiobookshelf.

Estrutura gravada no Audiobookshelf (Autor/Serie/Livro), com um arquivo por capitulo:

    <pasta de livros>/<Autor>/<Novel>/Vol. 2 - <Novel> Volume 2/0096 - Capitulo 96 - Exilio.m4b

A pasta de livros e local (`abs_dir`) ou, com `abs_ssh`, a de um servidor remoto (`abs_remote_dir`).

O Audiobookshelf junta os arquivos de uma mesma pasta em um unico livro (capitulos como
faixas) e reconhece a serie e o numero do volume pelos nomes das pastas.
"""

import os
import re
import shutil
import subprocess
import time

import requests

from .audiolivro_config import PASTA_ESPERA, PASTA_TRABALHO, carregar_config
from .epub_writer import criar_epub
from .servidor_abs import (
    enviar_espera,
    listar_existentes,
    modo_remoto,
    raiz_publicacao,
    verificar_destino,
)
from .texto_capitulo import baixar_capa, obter_info_novel, obter_texto_capitulo


def listar_vozes(config):
    pasta = config["voz_dir"]
    if not os.path.isdir(pasta):
        return []
    # ignora arquivos grandes (ex.: o audio original completo do video)
    return sorted(
        nome for nome in os.listdir(pasta)
        if nome.lower().endswith(".wav")
        and os.path.getsize(os.path.join(pasta, nome)) < 10 * 1024 * 1024
    )


def separar_pendentes(capitulos, novel_title, info, config):
    """Retorna (ja_prontos, pendentes) conforme os arquivos ja existentes no Audiobookshelf."""
    autor = info.get("autor") or config["autor_padrao"]
    existentes = _listar_existentes(config, autor, novel_title)
    prontos, pendentes = [], []
    for cap in capitulos:
        pronto = caminho_relativo(config, autor, novel_title, cap) in existentes
        (prontos if pronto else pendentes).append(cap)
    return prontos, pendentes


def gerar_audiolivro(capitulos, novel_title, url_novel, voz, config=None, info=None):
    """Converte os capitulos em audio e os publica na pasta do Audiobookshelf.

    Retorna {"sucessos": int, "falhas": [{"cap": cap, "motivo": str}]}.
    """
    config = config or carregar_config()
    erro = _validar_ambiente(config, voz)
    if erro:
        print(f"[ERRO] {erro}")
        return {"sucessos": 0, "falhas": [{"cap": cap, "motivo": erro} for cap in capitulos]}

    info = info or obter_info_novel(url_novel)
    autor = info["autor"] or config["autor_padrao"]
    print(f"Autor: {autor}")

    try:
        reenviados = enviar_espera(config, PASTA_ESPERA)
        if reenviados:
            print(f"{reenviados} arquivo(s) que aguardavam envio foram enviados ao servidor")
        existentes = _listar_existentes(config, autor, novel_title)
    except RuntimeError as exc:
        erro = f"servidor do Audiobookshelf indisponivel: {exc}"
        print(f"[ERRO] {erro}")
        return {"sucessos": 0, "falhas": [{"cap": cap, "motivo": erro} for cap in capitulos]}

    prontos = [c for c in capitulos if caminho_relativo(config, autor, novel_title, c) in existentes]
    pendentes = [c for c in capitulos if c not in prontos]
    if prontos:
        print(f"{len(prontos)} capitulo(s) ja existem no Audiobookshelf e serao ignorados")
    if not pendentes:
        print("Nada a gerar")
        return {"sucessos": 0, "falhas": []}

    sucessos, falhas = 0, []
    por_volume = {}
    for cap in pendentes:
        por_volume.setdefault(str(cap["volume"]), []).append(cap)

    tamanho_lote = max(1, int(config["lote_capitulos"]))
    for volume, caps in por_volume.items():
        _garantir_capa(config, autor, novel_title, volume, info.get("capa", ""), existentes)
        for inicio in range(0, len(caps), tamanho_lote):
            lote = caps[inicio:inicio + tamanho_lote]
            print(f"\n=== Vol. {volume}: capitulos {_resumo(lote)} ===")
            ok, falhas_lote = _processar_lote(lote, novel_title, autor, voz, config)
            sucessos += ok
            falhas.extend(falhas_lote)
            if ok:
                escanear_biblioteca(config)

    print(f"\nAudiolivro: {sucessos} gerado(s), {len(falhas)} falha(s)")
    return {"sucessos": sucessos, "falhas": falhas}


def caminho_relativo(config, autor, novel_title, cap):
    """(Autor, Novel, pasta do livro, arquivo) dentro da pasta de livros do Audiobookshelf."""
    volume = str(cap["volume"]).strip()
    titulo_vol = config["titulo_volume"].format(novel=novel_title, volume=volume)
    pasta_livro = f"Vol. {volume} - {titulo_vol}" if volume.isdigit() else titulo_vol
    numero = int(cap["capitulo"])
    nome = f"{numero:04d} - Capitulo {numero} - {cap['titulo']}.{config['formato']}"
    return (
        _nome_seguro(autor), _nome_seguro(novel_title), _nome_seguro(pasta_livro), _nome_seguro(nome),
    )


def caminho_destino(config, autor, novel_title, cap):
    """Caminho local onde o audio e gravado (pasta de espera se o destino for remoto)."""
    raiz = raiz_publicacao(config, PASTA_ESPERA)
    return os.path.join(raiz, *caminho_relativo(config, autor, novel_title, cap))


def _listar_existentes(config, autor, novel_title):
    partes_base = (_nome_seguro(autor), _nome_seguro(novel_title))
    return listar_existentes(config, partes_base, PASTA_ESPERA)


def escanear_biblioteca(config):
    """Pede ao Audiobookshelf um scan da biblioteca. Retorna True se solicitado."""
    token = config.get("abs_token", "")
    if not token:
        print("Aviso: sem token do Audiobookshelf (abs_token ou ABS_TOKEN); faca o scan manualmente.")
        return False
    base = config["abs_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resposta = requests.get(f"{base}/api/libraries", headers=headers, timeout=15)
        resposta.raise_for_status()
        bibliotecas = resposta.json().get("libraries", [])
        nome = config.get("abs_biblioteca", "")
        escolhida = next((b for b in bibliotecas if b.get("name") == nome), None) if nome else None
        if escolhida is None and len(bibliotecas) == 1:
            escolhida = bibliotecas[0]
        if escolhida is None:
            print("Aviso: defina 'abs_biblioteca' no audiobook_config.json "
                  f"(disponiveis: {', '.join(b.get('name', '?') for b in bibliotecas)})")
            return False
        scan = requests.post(f"{base}/api/libraries/{escolhida['id']}/scan",
                             headers=headers, timeout=30)
        scan.raise_for_status()
        print(f"Scan solicitado ao Audiobookshelf (biblioteca: {escolhida.get('name')})")
        return True
    except requests.RequestException as exc:
        print(f"Aviso: nao foi possivel acionar o scan do Audiobookshelf: {exc}")
        return False


def _processar_lote(lote, novel_title, autor, voz, config):
    pasta_lote = os.path.join(
        PASTA_TRABALHO, _nome_seguro(novel_title), f"lote_{int(time.time())}"
    )
    pasta_in = os.path.join(pasta_lote, "in")
    pasta_out = os.path.join(pasta_lote, "out")
    os.makedirs(pasta_in, exist_ok=True)
    os.makedirs(pasta_out, exist_ok=True)

    falhas, validos = [], []
    for cap in lote:
        try:
            paragrafos = obter_texto_capitulo(cap)
        except RuntimeError as exc:
            falhas.append({"cap": cap, "motivo": f"texto indisponivel: {exc}"})
            continue
        numero = int(cap["capitulo"])
        volume = str(cap["volume"]).strip()
        titulo_cap = f"Capítulo {numero}: {cap['titulo']}"
        # titulo unico por EPUB: evita colisao de nomes na saida do ebook2audiobook
        criar_epub(
            os.path.join(pasta_in, f"{numero:04d}.epub"),
            titulo_livro=f"{novel_title} {numero:04d} {cap['titulo']}",
            titulo_capitulo=titulo_cap,
            paragrafos=paragrafos,
            autor=autor,
            serie=novel_title,
            indice_serie=volume if volume.isdigit() else None,
            idioma="pt",
        )
        validos.append(cap)

    if not validos:
        shutil.rmtree(pasta_lote, ignore_errors=True)
        return 0, falhas

    codigo = _rodar_ebook2audiobook(pasta_in, pasta_out, voz, config)
    if codigo != 0:
        print(f"Aviso: ebook2audiobook terminou com codigo {codigo}; aproveitando o que foi gerado")

    publicados = []
    for cap in validos:
        numero = int(cap["capitulo"])
        origem = _achar_saida(pasta_out, numero, config["formato"])
        if not origem:
            falhas.append({"cap": cap, "motivo": "audio nao foi gerado pelo ebook2audiobook"})
            continue
        destino = caminho_destino(config, autor, novel_title, cap)
        try:
            _publicar(origem, destino, cap, novel_title, autor, config)
            publicados.append(cap)
        except (OSError, RuntimeError) as exc:
            falhas.append({"cap": cap, "motivo": f"falha ao publicar: {exc}"})

    sucessos = len(publicados)
    if publicados and modo_remoto(config):
        try:
            enviados = enviar_espera(config, PASTA_ESPERA)
            print(f"Enviados ao servidor {config['abs_ssh']}: {enviados} arquivo(s)")
        except RuntimeError as exc:
            # os audios ficam na pasta de espera e sao reenviados na proxima execucao
            falhas.extend(
                {"cap": cap, "motivo": f"falha ao enviar ao servidor: {exc}"} for cap in publicados
            )
            sucessos = 0
    if sucessos:
        for cap in publicados:
            print("Publicado: " + "/".join(caminho_relativo(config, autor, novel_title, cap)))

    if not falhas:
        shutil.rmtree(pasta_lote, ignore_errors=True)
    else:
        print(f"Arquivos do lote mantidos em: {pasta_lote}")
    return sucessos, falhas


def _rodar_ebook2audiobook(pasta_in, pasta_out, voz, config):
    e2a_dir = config["e2a_dir"]
    xtts = config["xtts"]
    cmd = [
        os.path.join(e2a_dir, config["e2a_python"]), "-u",
        os.path.join(e2a_dir, config["e2a_launcher"]),
        "--headless",
        "--ebooks_dir", os.path.abspath(pasta_in),
        "--output_dir", os.path.abspath(pasta_out),
        "--language", config["idioma"],
        "--voice", _voz_para_e2a(voz, config),
        "--tts_engine", config["motor"],
        "--device", config["dispositivo"],
        "--output_format", config["formato"],
        "--temperature", str(xtts["temperature"]),
        "--repetition_penalty", str(xtts["repetition_penalty"]),
        "--top_k", str(xtts["top_k"]),
        "--top_p", str(xtts["top_p"]),
        "--speed", str(xtts["speed"]),
    ]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.call(cmd, env=env)


def _voz_para_e2a(voz, config):
    """Copia a voz para `<e2a>/ebook2audiobook/voices/<idioma>/` e devolve esse caminho.

    O ebook2audiobook so usa a voz diretamente quando o caminho contem o codigo do idioma;
    com a voz em outra pasta, do segundo capitulo do lote em diante ele tenta reconverter a
    voz, falha e aborta o lote.
    """
    origem = os.path.join(config["voz_dir"], voz)
    pasta = os.path.join(config["e2a_dir"], config["e2a_app_dir"], "voices", config["idioma"])
    destino = os.path.join(pasta, voz)
    os.makedirs(pasta, exist_ok=True)
    if not os.path.exists(destino) or os.path.getsize(destino) != os.path.getsize(origem):
        shutil.copyfile(origem, destino)
    return destino


def _achar_saida(pasta_out, numero, formato):
    """Localiza o audio de um capitulo (o EPUB se chama NNNN.epub; o titulo comeca por NNNN)."""
    prefixo = f"{numero:04d}"
    candidatos = []
    for raiz, _, arquivos in os.walk(pasta_out):
        for nome in arquivos:
            if nome.lower().endswith(f".{formato}") and (
                nome.startswith(prefixo) or f" {prefixo} " in f" {nome} "
            ):
                candidatos.append(os.path.join(raiz, nome))
    return max(candidatos, key=os.path.getmtime) if candidatos else None


def _publicar(origem, destino, cap, novel_title, autor, config):
    """Copia o audio para o Audiobookshelf regravando as tags (sem recodificar)."""
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    volume = str(cap["volume"]).strip()
    numero = int(cap["capitulo"])
    album = config["titulo_volume"].format(novel=novel_title, volume=volume)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", origem,
        "-map", "0:a", "-map_chapters", "-1", "-c", "copy",
        "-metadata", f"title=Capítulo {numero}: {cap['titulo']}",
        "-metadata", f"artist={autor}",
        "-metadata", f"album_artist={autor}",
        "-metadata", f"album={album}",
        "-metadata", f"track={numero}",
        "-metadata", "genre=Audiobook",
        "-metadata", f"series={novel_title}",
        "-metadata", f"language={config['idioma']}",
    ]
    if volume.isdigit():
        cmd += ["-metadata", f"series-part={volume}"]
    cmd += ["-movflags", "+faststart+use_metadata_tags", destino]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg: {resultado.stderr.strip()[:200]}")


def _garantir_capa(config, autor, novel_title, volume, url_capa, existentes):
    cap_exemplo = {"volume": volume, "capitulo": "1", "titulo": "x"}
    partes_capa = caminho_relativo(config, autor, novel_title, cap_exemplo)[:-1] + ("cover.jpg",)
    if not url_capa or partes_capa in existentes:
        return
    capa = os.path.join(raiz_publicacao(config, PASTA_ESPERA), *partes_capa)
    os.makedirs(os.path.dirname(capa), exist_ok=True)
    baixar_capa(url_capa, capa)


def _validar_ambiente(config, voz):
    e2a_dir = config["e2a_dir"]
    python_e2a = os.path.join(e2a_dir, config["e2a_python"])
    if not os.path.isfile(python_e2a):
        return f"Python do ebook2audiobook nao encontrado: {python_e2a}"
    if not os.path.isfile(os.path.join(e2a_dir, config["e2a_launcher"])):
        return f"Launcher nao encontrado: {os.path.join(e2a_dir, config['e2a_launcher'])}"
    if not os.path.isfile(os.path.join(config["voz_dir"], voz)):
        return f"Voz nao encontrada: {os.path.join(config['voz_dir'], voz)}"
    if shutil.which("ffmpeg") is None:
        return "ffmpeg nao encontrado no PATH"
    return verificar_destino(config)


def _resumo(caps):
    numeros = sorted(int(c["capitulo"]) for c in caps)
    return f"{numeros[0]}-{numeros[-1]}" if len(numeros) > 1 else str(numeros[0])


def _nome_seguro(texto):
    texto = re.sub(r'[<>:"/\\|?*]', "", str(texto))
    return " ".join(texto.split()).rstrip(". ")


__all__ = ["gerar_audiolivro", "listar_vozes", "separar_pendentes", "escanear_biblioteca"]
