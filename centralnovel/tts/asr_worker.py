import argparse
import json
import sys
import time

_SAIDA = sys.stdout
sys.stdout = sys.stderr


def _emitir(obj):
    _SAIDA.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _SAIDA.flush()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modelo", default="openai/whisper-small")
    p.add_argument("--dispositivo", default="cuda")
    p.add_argument("--idioma", default="portuguese")
    args = p.parse_args()

    import soundfile as sf
    import torch
    from transformers import pipeline

    inicio = time.time()
    pipe = pipeline(
        "automatic-speech-recognition",
        model=args.modelo,
        device=args.dispositivo,
        dtype=torch.float16 if args.dispositivo.startswith("cuda") else torch.float32,
    )
    _emitir({"evento": "pronto", "carga_s": round(time.time() - inicio, 1)})

    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        job = json.loads(linha)
        if job.get("cmd") == "sair":
            break
        try:
            wav, taxa = sf.read(job["wav"], dtype="float32")
            if wav.ndim > 1:
                wav = wav.mean(axis=1)
            saida = pipe(
                {"raw": wav, "sampling_rate": taxa},
                generate_kwargs={"language": args.idioma, "task": "transcribe"},
            )
            _emitir({"evento": "transcricao", "id": job["id"], "texto": saida["text"].strip()})
        except Exception as exc:
            _emitir({"evento": "transcricao", "id": job.get("id"), "texto": "", "erro": str(exc)})


if __name__ == "__main__":
    main()
