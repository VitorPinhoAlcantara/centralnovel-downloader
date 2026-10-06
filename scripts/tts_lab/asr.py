import argparse
import json
import sys

import soundfile as sf


def carregar(modelo, dispositivo):
    import torch
    from transformers import pipeline

    return pipeline(
        "automatic-speech-recognition",
        model=modelo,
        device=dispositivo,
        torch_dtype=torch.float16 if dispositivo.startswith("cuda") else torch.float32,
    )


def transcrever(pipe, caminhos, idioma="portuguese"):
    resultados = {}
    for caminho in caminhos:
        wav, taxa = sf.read(caminho, dtype="float32")
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        saida = pipe(
            {"raw": wav, "sampling_rate": taxa},
            generate_kwargs={"language": idioma, "task": "transcribe"},
        )
        resultados[caminho] = saida["text"].strip()
    return resultados


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lista", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--modelo", default="openai/whisper-small")
    p.add_argument("--dispositivo", default="cuda")
    args = p.parse_args()

    with open(args.lista, "r", encoding="utf-8") as arquivo:
        caminhos = json.load(arquivo)
    pipe = carregar(args.modelo, args.dispositivo)
    resultados = transcrever(pipe, caminhos)
    with open(args.saida, "w", encoding="utf-8") as arquivo:
        json.dump(resultados, arquivo, ensure_ascii=False, indent=1)
    print(f"{len(resultados)} transcricoes", file=sys.stderr)


if __name__ == "__main__":
    main()
