"""Configuracao do fluxo de audiolivro (XTTS + Audiobookshelf).

Os valores ficam em `audiobook_config.json` (criado na primeira execucao, fora do git,
porque guarda o token do Audiobookshelf). O token tambem pode vir da variavel ABS_TOKEN.
"""

import json
import os

ARQUIVO_CONFIG = "audiobook_config.json"
PASTA_TRABALHO = "audiobook_work"
PASTA_ESPERA = f"{PASTA_TRABALHO}/espera_envio"  # audios prontos aguardando envio ao servidor

PADRAO = {
    "voz_dir": r"C:\Users\vitor\Downloads\AuidoBook\vozes",
    "voz_padrao": "voz_shadow_slave_ref.wav",
    "idioma": "por",
    "dispositivo": "cuda",
    "formato": "m4b",
    "xtts": {
        "temperature": 0.55,
        "repetition_penalty": 2.0,
        "top_k": 30,
        "top_p": 0.7,
        "speed": 1.1,
    },
    "xtts_ref": {
        "gpt_cond_len": 30,
        "gpt_cond_chunk_len": 6,
        "max_ref_length": 30,
    },
    "tts_python": r"C:\Users\vitor\Downloads\AuidoBook\ebook2audiobook\python_env\Scripts\python.exe",
    "xtts_model_dir": (
        r"C:\Users\vitor\Downloads\AuidoBook\ebook2audiobook\models\tts"
        r"\models--coqui--XTTS-v2\snapshots\6c2b0d75eae4b7047358e3b6bd9325f857d43f77"
    ),
    "idioma_xtts": "pt",
    "workers": 3,
    "workers_adaptativo": True,
    "gpu_util_baixo": 35,
    "gpu_util_moderado": 70,
    "vram_por_worker_mb": 3500,
    "vram_reserva_mb": 2000,
    "vram_critica_mb": 1000,
    "vram_folga_mb": 2500,
    "matmul": "highest",
    "qa": {},
    "qa_tentativas": 3,
    "final_trecho": "e2a",
    "asr": True,
    "asr_modelo": "openai/whisper-small",
    "asr_rodadas": 2,
    "asr_variacao_params": {"2": {"temperature": 0.7, "top_p": 0.85}},
    "normalizacao": {},
    "bitrate": "96k",
    "pausas_ms": {"frase": 250, "paragrafo": 700},
    "latents_cache": f"{PASTA_TRABALHO}/latents",
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
