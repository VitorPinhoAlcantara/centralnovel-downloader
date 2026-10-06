import argparse
import glob
import json
import os
import random

import torch
import torchaudio
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts


def carregar_modelo(base, dispositivo):
    config = XttsConfig()
    config.load_json(os.path.join(base, "config.json"))
    modelo = Xtts.init_from_config(config)
    modelo.load_checkpoint(
        config,
        checkpoint_path=os.path.join(base, "model.pth"),
        vocab_path=os.path.join(base, "vocab.json"),
        eval=True,
    )
    return modelo.to(dispositivo)


def embedding(modelo, caminho, dispositivo):
    wav, taxa = torchaudio.load(caminho)
    wav = wav.mean(dim=0, keepdim=True)
    wav = torchaudio.functional.resample(wav, taxa, 16000).to(dispositivo)
    with torch.inference_mode():
        vetor = modelo.hifigan_decoder.speaker_encoder.forward(wav, l2_norm=True)
    return torch.nn.functional.normalize(vetor.reshape(-1), dim=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--referencias", required=True)
    p.add_argument("--lista", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--n-referencias", type=int, default=60)
    p.add_argument("--dispositivo", default="cuda")
    args = p.parse_args()

    modelo = carregar_modelo(args.base, args.dispositivo)
    refs = sorted(glob.glob(os.path.join(args.referencias, "*.wav")))
    random.Random(3).shuffle(refs)
    vetores = torch.stack([embedding(modelo, r, args.dispositivo) for r in refs[: args.n_referencias]])
    centro = torch.nn.functional.normalize(vetores.mean(dim=0), dim=0)

    with open(args.lista, "r", encoding="utf-8") as arquivo:
        grupos = json.load(arquivo)
    saida = {}
    for nome, caminhos in grupos.items():
        notas = []
        for caminho in caminhos:
            notas.append(float(torch.dot(embedding(modelo, caminho, args.dispositivo), centro)))
        notas.sort()
        saida[nome] = {
            "media": round(sum(notas) / len(notas), 4),
            "minimo": round(notas[0], 4),
            "n": len(notas),
        }
    with open(args.saida, "w", encoding="utf-8") as arquivo:
        json.dump(saida, arquivo, indent=1)


if __name__ == "__main__":
    main()
