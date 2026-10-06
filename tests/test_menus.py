from unittest import mock

from centralnovel import menus

NOVEL = {"title": "Shadow Slave", "url": "https://exemplo/series/shadow-slave/"}
OUTRA = {"title": "Outra Novel", "url": "https://exemplo/series/outra/"}
CAP = {"volume": "1", "capitulo": "1", "titulo": "A", "url": "u"}


def _confirm(respostas):
    fila = iter(respostas)

    def fabrica(*args, **kwargs):
        return mock.Mock(execute=mock.Mock(return_value=next(fila)))

    return fabrica


def _rodar(novels, selecoes, respostas_confirm=()):
    with mock.patch.object(menus, "_clear_screen"), \
            mock.patch.object(menus, "_selecionar_novel", side_effect=novels) as novel, \
            mock.patch.object(menus, "extrair_links_pdf", return_value=[CAP]), \
            mock.patch.object(menus, "_selecionar_capitulos_ou_volumes", side_effect=selecoes) as caps, \
            mock.patch.object(menus, "_perguntar_saidas", return_value={"cbz"}) as saidas, \
            mock.patch.object(menus, "_resolver_ja_baixados", return_value=([CAP], False)), \
            mock.patch.object(menus, "download_capitulos_novel", return_value={"sucessos": 1, "falhas": []}) as baixar, \
            mock.patch.object(menus, "_tratar_falhas"), \
            mock.patch.object(menus.inquirer, "confirm", side_effect=_confirm(respostas_confirm)):
        menus.menu_download()
    return novel, caps, saidas, baixar


def test_apos_processar_volta_direto_para_selecao_de_capitulos():
    novel, caps, saidas, baixar = _rodar(
        novels=[NOVEL, None], selecoes=[[CAP], [CAP], None], respostas_confirm=[True, True]
    )
    assert novel.call_count == 2
    assert caps.call_count == 3
    assert baixar.call_count == 2
    assert saidas.call_args_list[1].args[0] == {"cbz"}


def test_voltar_na_selecao_permite_escolher_outra_novel():
    novel, caps, saidas, baixar = _rodar(novels=[NOVEL, OUTRA, None], selecoes=[None, [CAP], None],
                                         respostas_confirm=[True])
    assert novel.call_count == 3
    assert baixar.call_count == 1


def test_nenhuma_novel_volta_ao_menu_principal_sem_baixar():
    novel, caps, saidas, baixar = _rodar(novels=[None], selecoes=[])
    assert baixar.call_count == 0


def test_menu_principal_nao_tem_atalho_de_audiolivro():
    assert not hasattr(menus, "menu_audiolivro")
