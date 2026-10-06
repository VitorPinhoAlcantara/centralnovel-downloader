from centralnovel.tts.gpu import decidir_workers

CONFIG = {
    "workers": 3,
    "gpu_util_baixo": 35,
    "gpu_util_moderado": 70,
    "vram_por_worker_mb": 3500,
    "vram_reserva_mb": 2000,
}
TOTAL = 16311


def test_uso_baixo_e_memoria_livre_usa_tres():
    assert decidir_workers(5, 3000, TOTAL, 0, CONFIG) == 3


def test_uso_moderado_usa_dois():
    assert decidir_workers(50, 3000, TOTAL, 0, CONFIG) == 2


def test_uso_alto_usa_um():
    assert decidir_workers(90, 3000, TOTAL, 0, CONFIG) == 1


def test_pouca_memoria_limita_workers():
    assert decidir_workers(5, 8000, TOTAL, 0, CONFIG) == 1
    assert decidir_workers(5, 6000, TOTAL, 0, CONFIG) == 2


def test_memoria_dos_proprios_workers_nao_conta_como_externa():
    assert decidir_workers(5, 3000 + 3 * 3500, TOTAL, 3, CONFIG) == 3


def test_nunca_menos_que_um():
    assert decidir_workers(100, 16000, TOTAL, 0, CONFIG) == 1
