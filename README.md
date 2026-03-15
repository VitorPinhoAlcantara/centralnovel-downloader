# Centralnovel Downloader - Lord of Mysteries

Projeto em Python para:
- baixar capitulos em PDF da Centralnovel
- converter PDF em CBZ

## Execucao principal

Use o arquivo unico `main.py`:

```powershell
python main.py
```

Menu principal:
1. Download de PDFs
2. Conversao PDF -> CBZ
3. Sair

## Entradas legadas (compatibilidade)

Ainda funcionam:

```powershell
python download_pdfs.py
python pdf_to_cbz.py
```

Esses arquivos agora sao wrappers que chamam os menus modulares.

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
├── download_pdfs.py
├── pdf_to_cbz.py
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
└── links_capitulos.csv
```

## Ajustes de configuracao

Edite `centralnovel/config.py`:
- `DELAY_ENTRE_DOWNLOADS`
- `MAX_RETRIES`
- `QUALIDADE_JPG`
- `DPI`

