import threading
import time

from centralnovel import downloader


class SessaoFalsa:
    def __init__(self, eventos, baixados, lock):
        self.eventos = eventos
        self.baixados = baixados
        self.lock = lock
        self.concluidos = 0
        self.max_a_frente = 0
        self.finalizada = False

    def pendente(self, cap, sobrescrever=False):
        return True

    def gerar_capitulo(self, cap):
        with self.lock:
            self.eventos.append(("audio_inicio", int(cap["capitulo"])))
            self.max_a_frente = max(self.max_a_frente, len(self.baixados) - self.concluidos)
        time.sleep(0.05)
        with self.lock:
            self.concluidos += 1
        return True, None

    def finalizar(self):
        self.finalizada = True


def _caps(n):
    return [{"volume": "1", "capitulo": str(i), "titulo": f"c{i}", "url": "u"} for i in range(n)]


def _rodar(n, falhar=(), monkeypatch=None):
    eventos, baixados, lock = [], [], threading.Lock()

    def baixar(cap, novel_dir, saidas, sobrescrever):
        numero = int(cap["capitulo"])
        time.sleep(0.005)
        with lock:
            eventos.append(("download", numero))
            baixados.append(numero)
        return (False, "sem token") if numero in falhar else (True, None)

    monkeypatch.setattr(downloader, "_baixar_saidas_capitulo", baixar)
    sessao = SessaoFalsa(eventos, baixados, lock)
    resultado = downloader.download_capitulos_novel(_caps(n), "Teste", saidas={"cbz", "audio"}, sessao_audio=sessao)
    return resultado, eventos, sessao


def test_audio_comeca_logo_apos_o_primeiro_download(monkeypatch):
    _, eventos, _ = _rodar(15, monkeypatch=monkeypatch)
    assert eventos.index(("audio_inicio", 0)) < eventos.index(("download", 6))


def test_nunca_baixa_mais_que_o_limite_a_frente(monkeypatch):
    resultado, eventos, sessao = _rodar(30, monkeypatch=monkeypatch)
    assert resultado["sucessos"] == 30
    assert sessao.max_a_frente <= downloader.MAX_CAPITULOS_A_FRENTE
    assert sessao.finalizada


def test_audio_respeita_a_ordem(monkeypatch):
    _, eventos, _ = _rodar(12, monkeypatch=monkeypatch)
    ordem = [n for tipo, n in eventos if tipo == "audio_inicio"]
    assert ordem == sorted(ordem)


def test_falha_no_download_nao_gera_audio_nem_trava(monkeypatch):
    resultado, eventos, _ = _rodar(10, falhar={3, 4}, monkeypatch=monkeypatch)
    assert resultado["sucessos"] == 8
    assert [f["cap"]["capitulo"] for f in resultado["falhas"]] == ["3", "4"]
    assert ("audio_inicio", 3) not in eventos and ("audio_inicio", 4) not in eventos
