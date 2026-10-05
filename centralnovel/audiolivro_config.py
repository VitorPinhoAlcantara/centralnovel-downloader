"""Configuracao do fluxo de audiolivro (ebook2audiobook + Audiobookshelf).

Os valores ficam em `audiobook_config.json` (criado na primeira execucao, fora do git,
porque guarda o token do Audiobookshelf). O token tambem pode vir da variavel ABS_TOKEN.
"""

import json
import os

ARQUIVO_CONFIG = "audiobook_config.json"
PASTA_TRABALHO = "audiobook_work"
PASTA_ESPERA = f"{PASTA_TRABALHO}/espera_envio"  # audios prontos aguardando envio ao servidor

PADRAO = {
    # ebook2audiobook
    "e2a_dir": r"C:\Users\vitor\Downloads\AuidoBook",
    "e2a_app_dir": "ebook2audiobook",
    "e2a_python": r"ebook2audiobook\python_env\Scripts\python.exe",
    "e2a_launcher": "start-ebook2audiobook.py",
    "voz_dir": r"C:\Users\vitor\Downloads\AuidoBook\vozes",
    "voz_padrao": "voz_shadow_slave_ref.wav",
    "idioma": "por",
    "motor": "xtts",
    "dispositivo": "cuda",
    "formato": "m4b",
    "xtts": {
        "temperature": 0.55,
        "repetition_penalty": 2.0,
        "top_k": 30,
        "top_p": 0.7,
        "speed": 1.1,
    },
    "lote_capitulos": 10,
    # Audiobookshelf
    # servidor remoto via SSH (deixe abs_ssh vazio para usar a pasta local abs_dir)
    "abs_ssh": "topiinho@server",
    "abs_remote_dir": "/home/topiinho/Code/production/audiobookshelf/audiobooks",
    "abs_dir": "",
    "abs_url": "http://192.168.15.3:13378",
    "abs_token": "",
    "abs_biblioteca": "",
    "titulo_volume": "{novel} Volume {volume}",
    "autor_padrao": "Central Novel",
}


def carregar_config():
    config = json.loads(json.dumps(PADRAO))  # copia profunda
    if os.path.exists(ARQUIVO_CONFIG):
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as arquivo:
            _mesclar(config, json.load(arquivo))
    else:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as arquivo:
            json.dump(PADRAO, arquivo, indent=2, ensure_ascii=False)
        print(f"Configuracao criada: {ARQUIVO_CONFIG} (ajuste caminhos, voz e token se precisar)")

    token_env = os.environ.get("ABS_TOKEN", "").strip()
    if token_env:
        config["abs_token"] = token_env
    return config


def _mesclar(base, novo):
    for chave, valor in novo.items():
        if isinstance(valor, dict) and isinstance(base.get(chave), dict):
            _mesclar(base[chave], valor)
        else:
            base[chave] = valor
