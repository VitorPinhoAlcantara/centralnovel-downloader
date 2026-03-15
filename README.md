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
