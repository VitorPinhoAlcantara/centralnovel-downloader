import argparse
import os
import shutil

import torch


def exportar(checkpoint, base, saida):
    os.makedirs(saida, exist_ok=True)
    dados = torch.load(checkpoint, map_location="cpu", weights_only=False)
    estado = dados["model"] if "model" in dados else dados
    for chave in list(estado.keys()):
        if "dvae" in chave:
            del estado[chave]
    ruins = [c for c, v in estado.items() if torch.is_tensor(v) and v.is_floating_point() and not torch.isfinite(v).all()]
    if ruins:
        raise RuntimeError(f"checkpoint com valores nao finitos em {len(ruins)} tensores (ex.: {ruins[:3]})")
    torch.save({"model": estado}, os.path.join(saida, "model.pth"))
    for nome in ("config.json", "vocab.json"):
        shutil.copyfile(os.path.join(base, nome), os.path.join(saida, nome))
    return saida


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--saida", required=True)
    args = p.parse_args()
    print(exportar(args.checkpoint, args.base, args.saida))


if __name__ == "__main__":
    main()
