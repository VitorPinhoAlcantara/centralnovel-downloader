import os
import subprocess

import numpy as np
import soundfile as sf

TAXA = 24000
_LIMIAR_BORDA_DB = -48.0
_MARGEM_BORDA_S = 0.04
_JANELA_S = 0.01


def aparar_bordas(wav, taxa=TAXA):
    janela = max(1, int(taxa * _JANELA_S))
    quadros = len(wav) // janela
    if quadros == 0:
        return wav
    rms = np.sqrt(np.mean(wav[: quadros * janela].reshape(quadros, janela) ** 2, axis=1))
    ativos = np.flatnonzero(20.0 * np.log10(np.maximum(rms, 1e-6)) > _LIMIAR_BORDA_DB)
    if len(ativos) == 0:
        return wav
    margem = int(taxa * _MARGEM_BORDA_S)
    inicio = max(0, ativos[0] * janela - margem)
    fim = min(len(wav), (ativos[-1] + 1) * janela + margem)
    return wav[inicio:fim]


def montar_capitulo(trechos, pasta_wavs, saida_wav, pausa_inicial_ms=600, pausa_final_ms=1200):
    partes = [np.zeros(int(TAXA * pausa_inicial_ms / 1000), dtype=np.float32)]
    for trecho in trechos:
        caminho = os.path.join(pasta_wavs, f"{trecho['id']}.wav")
        wav, taxa = sf.read(caminho, dtype="float32")
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        if taxa != TAXA:
            raise RuntimeError(f"taxa inesperada em {caminho}: {taxa}")
        partes.append(aparar_bordas(wav))
        partes.append(np.zeros(int(TAXA * trecho["pausa_ms"] / 1000), dtype=np.float32))
    partes.append(np.zeros(int(TAXA * pausa_final_ms / 1000), dtype=np.float32))
    audio = np.concatenate(partes)
    os.makedirs(os.path.dirname(os.path.abspath(saida_wav)), exist_ok=True)
    sf.write(saida_wav, audio, TAXA, subtype="PCM_16")
    return len(audio) / TAXA


def codificar_m4b(wav, destino, metadados, bitrate="96k", loudnorm=True):
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", wav, "-vn"]
    if loudnorm:
        cmd += ["-af", "loudnorm=I=-18:TP=-1.5:LRA=11"]
    cmd += ["-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", bitrate]
    for chave, valor in metadados.items():
        cmd += ["-metadata", f"{chave}={valor}"]
    cmd += ["-movflags", "+faststart+use_metadata_tags", destino]
    resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg: {resultado.stderr.strip()[:300]}")
    return destino
