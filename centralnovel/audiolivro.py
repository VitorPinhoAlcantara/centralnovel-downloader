import json
import os
import re
import shutil
import threading
import zlib

import requests

from .audiolivro_config import PASTA_ESPERA, PASTA_TRABALHO, carregar_config
from .epub_writer import criar_epub_volume
from .servidor_abs import (
    enviar_espera,
    listar_existentes,
    modo_remoto,
    raiz_publicacao,
    verificar_destino,
)
from .texto_capitulo import baixar_capa, obter_info_novel, obter_texto_capitulo
from .tts.dividir import dividir_paragrafos
from .tts.gpu import escolher_workers
from .tts.montar import codificar_m4b, montar_capitulo
from .tts.normalizar import ajustar_final, normalizar
from .tts.pool import PoolTTS
from .tts.verificar import analisar


def separar_pendentes(capitulos, novel_title, info, config):
    autor = info.get("autor") or config["autor_padrao"]
    existentes = _listar_existentes(config, autor, novel_title)
    prontos, pendentes = [], []
    for cap in capitulos:
        pronto = caminho_relativo(config, autor, novel_title, cap) in existentes
        (prontos if pronto else pendentes).append(cap)
    return prontos, pendentes


def caminho_relativo(config, autor, novel_title, cap):
    volume = str(cap["volume"]).strip()
    titulo_vol = config["titulo_volume"].format(novel=novel_title, volume=volume)
    pasta_livro = f"Vol. {volume} - {titulo_vol}" if volume.isdigit() else titulo_vol
    numero = int(cap["capitulo"])
    nome = f"{numero:04d} - Capitulo {numero} - {cap['titulo']}.{config['formato']}"
    return (
        _nome_seguro(autor), _nome_seguro(novel_title), _nome_seguro(pasta_livro), _nome_seguro(nome),
    )


def caminho_epub_volume(config, autor, novel_title, volume):
    cap_exemplo = {"volume": volume, "capitulo": "1", "titulo": "x"}
    base = caminho_relativo(config, autor, novel_title, cap_exemplo)[:-1]
    titulo_vol = config["titulo_volume"].format(novel=novel_title, volume=volume)
    return base + (_nome_seguro(f"{titulo_vol}.epub"),)


def caminho_destino(config, autor, novel_title, cap):
    raiz = raiz_publicacao(config, PASTA_ESPERA)
    return os.path.join(raiz, *caminho_relativo(config, autor, novel_title, cap))


def escanear_biblioteca(config):
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


class SessaoAudiolivro:
    def __init__(self, novel_title, url_novel, voz, config=None, info=None):
        self.novel_title = novel_title
        self.url_novel = url_novel
        self.voz = voz
        self.config = config or carregar_config()
        self.info = info
        self.autor = None
        self.existentes = set()
        self.pool = None
        self.publicados = []
        self.volumes_com_capa = set()
        self._preparada = False
        self._erro_preparo = None

    def pendente(self, cap, sobrescrever=False):
        self._preparar()
        if self._erro_preparo:
            return True
        if sobrescrever:
            return True
        return caminho_relativo(self.config, self.autor, self.novel_title, cap) not in self.existentes

    def gerar_capitulo(self, cap):
        self._preparar()
        if self._erro_preparo:
            return False, self._erro_preparo
        try:
            paragrafos = obter_texto_capitulo(cap)
        except RuntimeError as exc:
            return False, f"texto indisponivel: {exc}"

        numero = int(cap["capitulo"])
        volume = str(cap["volume"]).strip()
        titulo_cap = f"Capítulo {numero}: {cap['titulo']}"
        self._garantir_capa(volume)
        self._guardar_texto(volume, numero, titulo_cap, paragrafos)

        opcoes = self.config.get("normalizacao", {})
        textos = [normalizar(p, opcoes) for p in [titulo_cap] + list(paragrafos)]
        pausas = self.config["pausas_ms"]
        trechos = dividir_paragrafos(
            [t for t in textos if t],
            pausa_frase_ms=pausas["frase"],
            pausa_paragrafo_ms=pausas["paragrafo"],
        )
        if not trechos:
            return False, "capitulo sem texto apos a normalizacao"

        pasta = os.path.join(PASTA_TRABALHO, _nome_seguro(self.novel_title), f"cap_{volume}_{numero:04d}")
        try:
            resultados = self._sintetizar(trechos, pasta, volume, numero)
        except RuntimeError as exc:
            return False, str(exc)

        ausentes = [t["id"] for t in trechos if not os.path.exists(os.path.join(pasta, f"{t['id']}.wav"))]
        if ausentes:
            return False, f"{len(ausentes)} trecho(s) sem audio (ex.: {', '.join(ausentes[:5])})"

        self._gravar_relatorio_qa(volume, numero, trechos, resultados)
        wav = os.path.join(pasta, "capitulo.wav")
        destino = caminho_destino(self.config, self.autor, self.novel_title, cap)
        try:
            duracao = montar_capitulo(trechos, pasta, wav)
            codificar_m4b(wav, destino, self._metadados(cap, titulo_cap, volume, numero),
                          bitrate=self.config["bitrate"])
        except (OSError, RuntimeError) as exc:
            return False, f"falha ao montar o audio: {exc}"

        reprovados = [i for i, r in resultados.items() if not r.get("ok") or r.get("asr_motivos")]
        print(f"Audio pronto: {duracao / 60:.1f} min, {len(trechos)} trechos, "
              f"{len(reprovados)} com alerta de QA")
        shutil.rmtree(pasta, ignore_errors=True)
        self.publicados.append(cap)
        self.existentes.add(caminho_relativo(self.config, self.autor, self.novel_title, cap))
        if len(self.publicados) >= max(1, int(self.config["lote_capitulos"])):
            self._publicar_lote()
        return True, None

    def finalizar(self):
        try:
            self._publicar_lote()
        finally:
            if self.pool is not None:
                self.pool.encerrar()
                self.pool = None

    def _preparar(self):
        if self._preparada:
            return
        self._preparada = True
        erro = self._validar_ambiente()
        if erro:
            self._erro_preparo = erro
            print(f"[ERRO] {erro}")
            return
        try:
            if self.info is None:
                self.info = obter_info_novel(self.url_novel)
            self.autor = self.info.get("autor") or self.config["autor_padrao"]
            print(f"Autor: {self.autor}")
            reenviados = enviar_espera(self.config, PASTA_ESPERA)
            if reenviados:
                print(f"{reenviados} arquivo(s) que aguardavam envio foram enviados ao servidor")
            self.existentes = _listar_existentes(self.config, self.autor, self.novel_title)
        except RuntimeError as exc:
            self._erro_preparo = f"servidor do Audiobookshelf indisponivel: {exc}"
            print(f"[ERRO] {self._erro_preparo}")

    def _validar_ambiente(self):
        cfg = self.config
        if not os.path.isfile(cfg["tts_python"]):
            return f"Python do TTS nao encontrado: {cfg['tts_python']}"
        if not os.path.isfile(os.path.join(cfg["xtts_model_dir"], "model.pth")):
            return f"Modelo XTTS nao encontrado em: {cfg['xtts_model_dir']}"
        if not os.path.isfile(os.path.join(cfg["voz_dir"], self.voz)):
            return f"Voz nao encontrada: {os.path.join(cfg['voz_dir'], self.voz)}"
        if shutil.which("ffmpeg") is None:
            return "ffmpeg nao encontrado no PATH"
        return verificar_destino(cfg)

    def _iniciar_pool(self):
        if self.pool is not None:
            self._ajustar_pool()
            return
        n, leitura = escolher_workers(self.config, 0)
        self._anunciar_workers(n, leitura)
        voz_path = os.path.join(self.config["voz_dir"], self.voz)
        pool = PoolTTS(self.config, [voz_path], workers=n, log_dir=os.path.join(PASTA_TRABALHO, "logs_tts"))
        print(f"Carregando o XTTS ({pool.n_workers} worker(s))...")
        try:
            pool.iniciar()
        except Exception as exc:
            raise RuntimeError(f"falha ao iniciar o XTTS: {exc}") from exc
        self.pool = pool

    def _ajustar_pool(self):
        n, leitura = escolher_workers(self.config, len(self.pool.workers))
        if n == len(self.pool.workers):
            return
        self._anunciar_workers(n, leitura)
        self.pool.redimensionar(n)

    def _anunciar_workers(self, n, leitura):
        if leitura:
            print(f"GPU: uso {leitura['util']}%, VRAM {leitura['usada_mb']}/{leitura['total_mb']} MB -> {n} worker(s)")

    def _sintetizar(self, trechos, pasta, volume, numero):
        os.makedirs(pasta, exist_ok=True)
        caminho_estado = os.path.join(pasta, "estado.json")
        estado = {}
        if os.path.exists(caminho_estado):
            try:
                with open(caminho_estado, "r", encoding="utf-8") as arquivo:
                    estado = json.load(arquivo)
            except (OSError, ValueError):
                estado = {}

        usa_asr = bool(self.config["asr"])
        resultados = {}
        jobs = []
        sementes = {}
        for trecho in trechos:
            anterior = estado.get(trecho["id"])
            wav = os.path.join(pasta, f"{trecho['id']}.wav")
            sementes[trecho["id"]] = zlib.crc32(
                f"{self.novel_title}:{volume}:{numero}:{trecho['id']}".encode("utf-8")
            ) % 1000000
            if (anterior and anterior.get("texto") == trecho["texto"]
                    and anterior["res"].get("ok") and os.path.exists(wav)
                    and (not usa_asr or anterior.get("verificado"))):
                resultados[trecho["id"]] = anterior["res"]
                continue
            jobs.append(self._job(trecho, wav, sementes[trecho["id"]], 0))

        if resultados:
            print(f"Retomando: {len(resultados)} trecho(s) ja gerados")
        if not jobs:
            return resultados

        self._iniciar_pool()
        textos = {t["id"]: t["texto"] for t in trechos}
        trava = threading.Lock()

        def gravar_estado():
            with open(caminho_estado, "w", encoding="utf-8") as arquivo:
                json.dump(estado, arquivo, ensure_ascii=False)

        def ao_concluir(resposta, feitos, total):
            with trava:
                estado[resposta["id"]] = {"texto": textos[resposta["id"]], "res": resposta}
                gravar_estado()
            if feitos % 10 == 0 or feitos == total:
                print(f"  trechos {feitos}/{total}")

        novos = self.pool.gerar(jobs, ao_concluir=ao_concluir)
        resultados.update(novos)
        if usa_asr:
            self._verificar_asr(
                [j["id"] for j in jobs], textos, pasta, sementes, resultados, estado, gravar_estado
            )
        return resultados

    def _job(self, trecho, wav, semente, rodada):
        finais = [self.config["final_trecho"], "sem", self.config["final_trecho"]]
        job = {
            "id": trecho["id"],
            "texto": ajustar_final(trecho["texto"], finais[rodada % len(finais)]),
            "saida": os.path.abspath(wav),
            "seed": semente + rodada * 104729,
            "tentativas": int(self.config["qa_tentativas"]),
        }
        variacao = self.config["asr_variacao_params"].get(str(rodada))
        if variacao:
            job["params"] = variacao
        return job

    def _verificar_asr(self, ids, textos, pasta, sementes, resultados, estado, gravar_estado):
        pendentes = list(ids)
        rodadas = int(self.config["asr_rodadas"])
        por_id = {}
        print(f"Verificando {len(pendentes)} trecho(s) com o Whisper...")
        for rodada in range(rodadas + 1):
            transcricoes = self.pool.transcrever(
                [(i, os.path.join(pasta, f"{i}.wav")) for i in pendentes]
            )
            ruins = []
            for i in pendentes:
                analise = analisar(textos[i], transcricoes[i], self.config.get("asr_limites"))
                por_id[i] = analise
                resultados[i]["asr_motivos"] = analise["motivos"]
                estado[i]["res"] = resultados[i]
                estado[i]["verificado"] = True
                if not analise["ok"]:
                    ruins.append(i)
            gravar_estado()
            if not ruins or rodada == rodadas:
                break
            print(f"  rodada {rodada + 1}: regenerando {len(ruins)} trecho(s) com problema")
            trechos_por_id = {i: {"id": i, "texto": textos[i]} for i in ruins}
            jobs = [
                self._job(trechos_por_id[i], os.path.join(pasta, f"{i}.wav"), sementes[i], rodada + 1)
                for i in ruins
            ]
            novos = self.pool.gerar(jobs)
            for i, res in novos.items():
                resultados[i] = res
                estado[i]["res"] = res
                estado[i]["verificado"] = False
            pendentes = ruins
        restantes = [i for i, a in por_id.items() if not a["ok"]]
        if restantes:
            print(f"  {len(restantes)} trecho(s) ainda com alerta apos {rodadas} rodada(s) (veja o relatorio de QA)")

    def _gravar_relatorio_qa(self, volume, numero, trechos, resultados):
        pasta = os.path.join(PASTA_TRABALHO, "qa", _nome_seguro(self.novel_title))
        os.makedirs(pasta, exist_ok=True)
        textos = {t["id"]: t["texto"] for t in trechos}
        alertas = [
            {"id": i, "texto": textos.get(i, ""), "motivos": r.get("motivos"),
             "asr_motivos": r.get("asr_motivos"),
             "tentativas": r.get("tentativas"), "metricas": r.get("metricas")}
            for i, r in sorted(resultados.items()) if not r.get("ok") or r.get("asr_motivos")
        ]
        with open(os.path.join(pasta, f"vol{volume}_cap{numero:04d}.json"), "w", encoding="utf-8") as arquivo:
            json.dump({"trechos": len(trechos), "alertas": alertas}, arquivo, ensure_ascii=False, indent=1)

    def _metadados(self, cap, titulo_cap, volume, numero):
        album = self.config["titulo_volume"].format(novel=self.novel_title, volume=volume)
        meta = {
            "title": titulo_cap,
            "artist": self.autor,
            "album_artist": self.autor,
            "album": album,
            "track": str(numero),
            "genre": "Audiobook",
            "series": self.novel_title,
            "language": self.config["idioma"],
        }
        if volume.isdigit():
            meta["series-part"] = volume
        return meta

    def _garantir_capa(self, volume):
        if volume in self.volumes_com_capa:
            return
        self.volumes_com_capa.add(volume)
        cap_exemplo = {"volume": volume, "capitulo": "1", "titulo": "x"}
        partes_capa = caminho_relativo(self.config, self.autor, self.novel_title, cap_exemplo)[:-1] + ("cover.jpg",)
        url_capa = (self.info or {}).get("capa", "")
        if not url_capa or partes_capa in self.existentes:
            return
        capa = os.path.join(raiz_publicacao(self.config, PASTA_ESPERA), *partes_capa)
        os.makedirs(os.path.dirname(capa), exist_ok=True)
        baixar_capa(url_capa, capa)

    def _publicar_lote(self):
        if not self.publicados:
            return
        publicados, self.publicados = self.publicados, []
        for volume in sorted({str(cap["volume"]).strip() for cap in publicados}):
            self._gerar_epub_volume(volume)
        if modo_remoto(self.config):
            try:
                enviados = enviar_espera(self.config, PASTA_ESPERA)
                print(f"Enviados ao servidor {self.config['abs_ssh']}: {enviados} arquivo(s)")
            except RuntimeError as exc:
                print(f"Aviso: falha ao enviar ao servidor ({exc}); os audios ficam na pasta de espera "
                      "e serao reenviados na proxima execucao")
                return
        for cap in publicados:
            print("Publicado: " + "/".join(caminho_relativo(self.config, self.autor, self.novel_title, cap)))
        escanear_biblioteca(self.config)


    def _pasta_textos(self, volume):
        return os.path.join(PASTA_TRABALHO, "textos", _nome_seguro(self.novel_title), f"vol_{volume}")

    def _guardar_texto(self, volume, numero, titulo_cap, paragrafos):
        pasta = self._pasta_textos(volume)
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, f"{numero:04d}.json"), "w", encoding="utf-8") as arquivo:
            json.dump({"titulo": titulo_cap, "paragrafos": list(paragrafos)}, arquivo, ensure_ascii=False)

    def _gerar_epub_volume(self, volume):
        pasta = self._pasta_textos(volume)
        if not os.path.isdir(pasta):
            return
        capitulos = []
        for nome in sorted(os.listdir(pasta)):
            with open(os.path.join(pasta, nome), "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            capitulos.append((dados["titulo"], dados["paragrafos"]))
        if not capitulos:
            return
        partes = caminho_epub_volume(self.config, self.autor, self.novel_title, volume)
        destino = os.path.join(raiz_publicacao(self.config, PASTA_ESPERA), *partes)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        titulo_vol = self.config["titulo_volume"].format(novel=self.novel_title, volume=volume)
        criar_epub_volume(
            destino, titulo_vol, capitulos, autor=self.autor, serie=self.novel_title,
            indice_serie=volume if volume.isdigit() else None, idioma="pt",
        )


def _listar_existentes(config, autor, novel_title):
    partes_base = (_nome_seguro(autor), _nome_seguro(novel_title))
    return listar_existentes(config, partes_base, PASTA_ESPERA)


def _nome_seguro(texto):
    texto = re.sub(r'[<>:"/\\|?*]', "", str(texto))
    return " ".join(texto.split()).rstrip(". ")


__all__ = ["SessaoAudiolivro", "separar_pendentes", "escanear_biblioteca"]
