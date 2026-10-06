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
3. Gerar audiolivro (Audiobookshelf)
4. Sair

## Fluxo de download

No menu de download:
1. lista top 10 novels do site
2. voce escolhe por numero, nome da novel ou link da novel
3. escolhe baixar capitulos especificos ou volumes completos (aceita varios: `1,2,10-15`)
4. marca o que gerar: PDF, CBZ e/ou Audiolivro

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

## Saidas do download

No menu de download voce marca o que gerar (espaco marca, enter confirma), em qualquer combinacao:

- **PDF**
- **CBZ** (se o PDF nao foi marcado, o PDF baixado so como etapa intermediaria e apagado depois do CBZ; um PDF que ja existia e preservado)
- **Audiolivro (Audiobookshelf)**

Com **Audiolivro** marcado, os capitulos sao processados um por vez (PDF, CBZ e audio de cada capitulo em sequencia), o que tambem reduz o risco de bloqueio do site. Sem audiolivro, os downloads continuam em paralelo. O item "Gerar audiolivro" do menu principal e um atalho com o audiolivro ja marcado.

## Audiolivro (XTTS + Audiobookshelf)

O motor e proprio (pacote `centralnovel/tts/`), sem ebook2audiobook. Fluxo por capitulo:

1. o texto e lido direto do HTML do site (sem PDF), sem o link e a marca de traducao
2. normalizacao PT-BR (abreviacoes, numeros por extenso, reticencias, interjeicoes removidas) e divisao em trechos de 60-180 caracteres
3. `workers` processos XTTS geram os trechos em paralelo na GPU (modelo carregado uma vez); o ponto final do trecho vira ` ;` para o XTTS nao falar "ponto"
4. QA numerico (duracao, silencio, energia) e verificacao por transcricao com Whisper: trechos com palavras puladas ou "ponto" falado sao regenerados com outra seed
5. os trechos sao montados com pausas, normalizados (loudnorm) e gravados em m4b com as tags corretas
6. a cada `lote_capitulos` os audios sao enviados ao servidor do Audiobookshelf (SSH, com conferencia de tamanho) junto com um EPUB do volume (texto dos capitulos) e e pedido um scan da biblioteca

Estrutura gravada (o Audiobookshelf junta os arquivos da pasta em um unico livro e reconhece a serie pelo caminho):

```
<abs_dir>/<Autor>/<Novel>/Vol. 2 - <Novel> Volume 2/0096 - Capitulo 96 - Exilio.m4b
<abs_dir>/<Autor>/<Novel>/Vol. 2 - <Novel> Volume 2/<Novel> Volume 2.epub
```

Capitulos que ja existem no servidor sao ignorados, e um capitulo interrompido retoma dos trechos ja gerados.

### Ambiente do TTS

O worker roda no Python que tem torch/coqui-tts (`tts_python`). Hoje e o do ebook2audiobook. Para um ambiente proprio, use `requirements-tts.txt` (torch cu130, para GPUs Blackwell):

```powershell
python -m venv tts_env
.\tts_env\Scripts\python.exe -m pip install -r requirements-tts.txt
```

e aponte `tts_python` para `tts_env\Scripts\python.exe` no `audiobook_config.json`. O modelo XTTS-v2 e baixado do Hugging Face; `xtts_model_dir` aponta a pasta com `config.json`, `model.pth` e `vocab.json`. O Whisper (`asr_modelo`) tambem e baixado na primeira verificacao.

### Configuracao

Na primeira execucao e criado `audiobook_config.json` (fora do git). Ajuste:

- `tts_python`, `xtts_model_dir`, `workers` (maximo; 3 e ~2,5x mais rapido que 1 e usa ~12 GB de VRAM), `workers_adaptativo` (liga o ajuste ao vivo: antes de cada capitulo mede o uso da GPU sem os workers e usa 3 com uso baixo, 2 com moderado e 1 com alto, limitado pela VRAM livre; durante o capitulo pausa workers se a VRAM livre ficar critica), `gpu_util_baixo`, `gpu_util_moderado`, `vram_por_worker_mb`, `vram_reserva_mb`, `vram_critica_mb`, `vram_folga_mb`, `matmul`
- `voz_dir`, `voz_padrao`: pasta dos `.wav` de referencia e a voz padrao
- `xtts`: temperatura, repetition penalty, top-k, top-p e speed; `xtts_ref`: tamanho da referencia de voz (`gpt_cond_len` 30 s soa mais expressivo que o padrao de 6 s)
- `qa`, `qa_tentativas`, `asr`, `asr_modelo`, `asr_rodadas`, `final_trecho`, `normalizacao`, `pausas_ms`, `bitrate`
- `abs_ssh`, `abs_remote_dir`: servidor do Audiobookshelf acessado por SSH (ex.: `topiinho@server`) e a pasta de livros nele; deixe `abs_ssh` vazio para gravar numa pasta local (`abs_dir`)
- `abs_url`, `abs_token` (ou variavel de ambiente `ABS_TOKEN`), `abs_biblioteca`: usados para pedir o scan
- `lote_capitulos`: a cada quantos capitulos enviar ao servidor e escanear

Relatorios de QA por capitulo ficam em `audiobook_work/qa/`. Experimentos de qualidade (A/B de texto, paralelismo) estao em `scripts/tts_lab/`.
