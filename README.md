# Centralnovel Downloader

Projeto em Python para:
- baixar capitulos de qualquer novel da Centralnovel
- selecionar capitulos especificos ou volumes completos
- converter PDF para CBZ no mesmo fluxo de download

## Execucao principal

Use o arquivo unico `main.py`:

```powershell
python main.py
```

A navegacao agora e interativa no terminal (setas/espaco/enter), com limpeza de tela ao trocar de menu.

Menu principal:
1. Download de novel
2. Conversao PDF -> CBZ
3. Sair

## Fluxo de download

No menu de download:
1. lista top 10 novels do site
2. voce escolhe por numero, nome da novel ou link da novel
3. escolhe baixar capitulos especificos ou volumes completos (aceita varios: `1,2,10-15`)
4. escolhe formato:
   - apenas PDF
   - PDF + conversao automatica para CBZ

## Recursos do download

- **Ja baixados**: antes de baixar, o programa verifica cada capitulo (PDF, e CBZ se escolhido). Se algum ja existir, voce escolhe: baixar so os faltantes, reescrever os existentes, ambos ou cancelar.
- **Falhas**: ao final, os capitulos com erro sao listados e voce pode tentar novamente (repetivel). O log com capitulo, motivo e URL fica em `logs/falhas_<novel>_<data>.log` (removido se tudo for recuperado).
- **Limpeza do PDF**: o link do site e a marca "Traduzido usando o ChatGPT" (ou similar) sao removidos da primeira pagina automaticamente. Ajuste em `centralnovel/config.py` (`REMOVER_LINK_PDF`, `REMOVER_MARCA_TRADUCAO`). Para PDFs ja baixados: Conversao PDF -> CBZ > "Limpar PDFs".

## Pastas de saida (padrao)

Todos os arquivos ficam separados por novel e volume:

```text
PDF/<Novel>/Vol_XX/*.pdf
CBZ/<Novel>/Vol_XX/*.cbz
```

## Instalar dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Estrutura nova

```text
centralnovel-downloader/
├── main.py
├── centralnovel/
│   ├── __init__.py
│   ├── config.py
│   ├── csv_store.py
│   ├── download_utils.py
│   ├── downloader.py
│   ├── scraper.py
│   ├── converter.py
│   └── menus.py
├── requirements.txt
│   └── selection.py
├── Backup/
│   ├── download_pdfs.py
│   └── pdf_to_cbz.py
├── PDF/
├── CBZ/
└── links_capitulos.csv
```

## Ajustes de configuracao

Edite `centralnovel/config.py`:
- `DELAY_ENTRE_DOWNLOADS`
- `MAX_RETRIES`
- `QUALIDADE_JPG`
- `DPI`
- `PDF_ROOT_DIR`
- `CBZ_ROOT_DIR`

## Audiolivro (ebook2audiobook + Audiobookshelf)

Menu principal > **Gerar audiolivro (Audiobookshelf)**. Fluxo:

1. escolhe a novel e os capitulos/volumes (mesmo seletor do download)
2. o texto de cada capitulo e lido direto do HTML do site (sem passar pelo PDF), sem o link e a marca de traducao
3. cada capitulo vira um EPUB temporario (titulo, autor e serie nos metadados)
4. o `ebook2audiobook` converte os EPUBs em lote (modo `--headless`, XTTS, voz de referencia `.wav`)
5. o audio e regravado, sem recodificar, com as tags corretas, enviado ao servidor do Audiobookshelf (SSH) e um scan da biblioteca e solicitado

Estrutura gravada (o Audiobookshelf junta os arquivos da pasta em um unico livro e reconhece a serie pelo caminho):

```
<abs_dir>/<Autor>/<Novel>/Vol. 2 - <Novel> Volume 2/0096 - Capitulo 96 - Exilio.m4b
```

Capitulos que ja existem na pasta do Audiobookshelf sao ignorados, entao interromper e rodar de novo retoma de onde parou.

### Configuracao

Na primeira execucao e criado `audiobook_config.json` (fora do git). Ajuste:

- `e2a_dir`, `e2a_python`, `e2a_launcher`: onde esta o ebook2audiobook
- `voz_dir`, `voz_padrao`: pasta dos `.wav` de referencia e a voz padrao
- `xtts`: temperatura, repetition penalty, top-k, top-p e speed
- `abs_ssh`, `abs_remote_dir`: servidor do Audiobookshelf acessado por SSH (ex.: `topiinho@server`) e a pasta de livros nele; os audios sao enviados por SSH (com conferencia de tamanho) e a copia local e apagada. Deixe `abs_ssh` vazio para gravar numa pasta local (`abs_dir`)
- `abs_url`, `abs_token` (ou variavel de ambiente `ABS_TOKEN`), `abs_biblioteca`: usados para pedir o scan
- `lote_capitulos`: quantos capitulos por execucao do ebook2audiobook (o modelo e carregado uma vez por lote)
