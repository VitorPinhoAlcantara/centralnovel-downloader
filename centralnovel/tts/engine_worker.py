import argparse
import hashlib
import json
import os
import sys
import time

_SAIDA = sys.stdout
sys.stdout = sys.stderr


def _emitir(obj):
    _SAIDA.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _SAIDA.flush()


def _argumentos():
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", required=True)
    p.add_argument("--voz", action="append", required=True)
    p.add_argument("--idioma", default="pt")
    p.add_argument("--dispositivo", default="cuda")
    p.add_argument("--latents-cache", default="")
    p.add_argument("--gpt-cond-len", type=int, default=30)
    p.add_argument("--gpt-cond-chunk-len", type=int, default=6)
    p.add_argument("--max-ref-length", type=int, default=30)
    p.add_argument("--params", default="{}")
    p.add_argument("--qa", default="{}")
    p.add_argument("--matmul", default="highest")
    return p.parse_args()


def _carregar_modelo(model_dir, dispositivo):
    import torch
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts

    config = XttsConfig()
    config.load_json(os.path.join(model_dir, "config.json"))
    modelo = Xtts.init_from_config(config)
    modelo.load_checkpoint(
        config,
        checkpoint_path=os.path.join(model_dir, "model.pth"),
        vocab_path=os.path.join(model_dir, "vocab.json"),
        eval=True,
    )
    modelo.to(torch.device(dispositivo))
    return modelo


def _latents(modelo, args):
    import torch

    assinatura = json.dumps(
        [[v, os.path.getsize(v), int(os.path.getmtime(v))] for v in args.voz]
        + [args.gpt_cond_len, args.gpt_cond_chunk_len, args.max_ref_length]
        + [os.path.getsize(os.path.join(args.model_dir, "model.pth")),
           int(os.path.getmtime(os.path.join(args.model_dir, "model.pth")))]
    )
    chave = hashlib.sha1(assinatura.encode("utf-8")).hexdigest()[:16]
    caminho = os.path.join(args.latents_cache, f"latents_{chave}.pt") if args.latents_cache else ""
    if caminho and os.path.exists(caminho):
        gpt, spk = torch.load(caminho, map_location=args.dispositivo)
        return gpt, spk
    gpt, spk = modelo.get_conditioning_latents(
        audio_path=list(args.voz),
        load_sr=24000,
        sound_norm_refs=True,
        gpt_cond_len=args.gpt_cond_len,
        gpt_cond_chunk_len=args.gpt_cond_chunk_len,
        max_ref_length=args.max_ref_length,
    )
    if caminho:
        os.makedirs(args.latents_cache, exist_ok=True)
        torch.save((gpt, spk), caminho)
    return gpt, spk


def _gerar_uma_vez(modelo, gpt, spk, texto, idioma, params, seed):
    import numpy as np
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    with torch.inference_mode():
        saida = modelo.inference(
            text=texto,
            language=idioma,
            gpt_cond_latent=gpt,
            speaker_embedding=spk,
            enable_text_splitting=False,
            **params,
        )
    wav = saida["wav"]
    if torch.is_tensor(wav):
        wav = wav.detach().cpu().numpy()
    return np.asarray(wav, dtype=np.float32).reshape(-1)


def _atender(modelo, gpt, spk, args, params_base, limites, job):
    import soundfile as sf

    from centralnovel.tts import qa

    texto = job["texto"]
    params = dict(params_base)
    params.update(job.get("params") or {})
    limites_job = dict(limites)
    limites_job.update(job.get("qa") or {})
    tentativas = max(1, int(job.get("tentativas", 3)))
    seed_base = int(job.get("seed", 0))

    melhor = None
    inicio = time.time()
    usadas = 0
    for n in range(tentativas):
        usadas = n + 1
        wav = _gerar_uma_vez(modelo, gpt, spk, texto, args.idioma, params, seed_base + n * 7919)
        metricas = qa.medir(wav, 24000, texto)
        aprovado, motivos = qa.avaliar(metricas, limites_job)
        ponto = qa.pontuacao(metricas, limites_job)
        if melhor is None or ponto < melhor[0]:
            melhor = (ponto, wav, metricas, motivos)
        if aprovado:
            break

    _, wav, metricas, motivos = melhor
    os.makedirs(os.path.dirname(os.path.abspath(job["saida"])), exist_ok=True)
    sf.write(job["saida"], wav, 24000, subtype="PCM_16")
    return {
        "evento": "resultado",
        "id": job["id"],
        "ok": not motivos,
        "tentativas": usadas,
        "metricas": metricas,
        "motivos": motivos,
        "tempo_s": round(time.time() - inicio, 2),
    }


def main():
    args = _argumentos()
    import torch

    from centralnovel.tts import compat

    compat.aplicar()

    try:
        torch.set_float32_matmul_precision(args.matmul)
    except Exception:
        pass

    inicio = time.time()
    modelo = _carregar_modelo(args.model_dir, args.dispositivo)
    gpt, spk = _latents(modelo, args)
    params_base = json.loads(args.params)
    limites = json.loads(args.qa)
    vram = 0
    if torch.cuda.is_available():
        vram = int(torch.cuda.memory_allocated() / 1024 / 1024)
    _emitir({"evento": "pronto", "vram_mb": vram, "carga_s": round(time.time() - inicio, 1)})

    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        job = json.loads(linha)
        if job.get("cmd") == "sair":
            break
        try:
            _emitir(_atender(modelo, gpt, spk, args, params_base, limites, job))
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            _emitir({"evento": "resultado", "id": job.get("id"), "ok": False,
                     "tentativas": 0, "metricas": {}, "motivos": [f"erro: {exc}"], "tempo_s": 0})


if __name__ == "__main__":
    main()
