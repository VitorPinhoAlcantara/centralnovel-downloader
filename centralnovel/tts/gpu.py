import subprocess
import time

_CONSULTA = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"]


def amostrar():
    saida = subprocess.run(_CONSULTA, capture_output=True, text=True, timeout=10).stdout
    util, usada, total = [int(x) for x in saida.strip().splitlines()[0].split(",")]
    return {"util": util, "usada_mb": usada, "total_mb": total}


def util_media(segundos=2.0, intervalo=0.5):
    amostras = []
    fim = time.time() + segundos
    while True:
        amostras.append(amostrar()["util"])
        if time.time() >= fim:
            break
        time.sleep(intervalo)
    return sum(amostras) / len(amostras)


def decidir_workers(util_externa, usada_mb, total_mb, workers_atuais, config):
    maximo = max(1, int(config["workers"]))
    if util_externa <= config["gpu_util_baixo"]:
        por_util = maximo
    elif util_externa <= config["gpu_util_moderado"]:
        por_util = min(2, maximo)
    else:
        por_util = 1

    por_worker = config["vram_por_worker_mb"]
    externa_mb = max(0, usada_mb - workers_atuais * por_worker)
    por_memoria = int((total_mb - externa_mb - config["vram_reserva_mb"]) // por_worker)
    return max(1, min(maximo, por_util, por_memoria))


def escolher_workers(config, workers_atuais=0):
    if not config.get("workers_adaptativo", True):
        return max(1, int(config["workers"])), None
    try:
        util = util_media()
        amostra = amostrar()
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return max(1, int(config["workers"])), None
    n = decidir_workers(util, amostra["usada_mb"], amostra["total_mb"], workers_atuais, config)
    return n, {"util": round(util), "usada_mb": amostra["usada_mb"], "total_mb": amostra["total_mb"]}
