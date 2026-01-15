# Centralnovel Downloader - Lord of Mysteries

Projeto em Python para baixar capitulos da novel **Lord of Mysteries** no site Centralnovel e converter PDFs em CBZ.

Site oficial: https://centralnovel.com/

AVISO LEGAL
- Este projeto nao tem consentimento do site oficial.
- O conteudo baixado pertence ao site Centralnovel.
- Ao usar este projeto, voce deve respeitar todos os direitos do Centralnovel sobre os volumes baixados.

---

## Passo a passo: criar e usar venv

No diretório do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependencias:

```powershell
pip install -r requirements.txt
```

Para sair do venv:

```powershell
deactivate
```

Se der erro de permissao de script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## Script 1: download_pdfs.py

### Como executar
```powershell
python download_pdfs.py
```

### Funcoes do menu
1. Extrair links - busca todos os capitulos disponiveis e gera `links_capitulos.csv`
2. Baixar todos - baixa todos os capitulos
3. Baixar especifico - baixa um capitulo (ex: 213)
4. Baixar intervalo - baixa um intervalo (ex: 1-50)

### Fluxo recomendado (primeira vez)
1. Execute o script
2. Escolha a opcao 1 para extrair os links
3. Depois use a opcao 2, 3 ou 4 para baixar

### Configuracoes (no arquivo)
Em `download_pdfs.py`:
- `DELAY_ENTRE_DOWNLOADS`: tempo entre downloads
- `MAX_RETRIES`: tentativas por capitulo

### Saida esperada
```
Novel Download/
├── links_capitulos.csv
├── lord-of-mysteries-01/
│   ├── Capitulo_001_Titulo.pdf
│   └── ...
└── lord-of-mysteries-02/
    └── ...
```

---

## Script 2: pdf_to_cbz.py

### Como executar
```powershell
python pdf_to_cbz.py
```

### Funcoes do menu
1. Converter arquivo - converte um PDF especifico
2. Converter pasta - converte todos os PDFs de uma pasta
3. Converter tudo - converte todos os PDFs (inclui subpastas)

### Configuracoes (no arquivo)
Em `pdf_to_cbz.py`:
- `QUALIDADE_JPG`: qualidade das imagens (0-100)
- `DPI`: resolucao da conversao

### Saida esperada
```
Capitulo_001_Carmesim.pdf -> Capitulo_001_Carmesim.cbz
```

---

## Estrutura do projeto
```
centralnovel-downloader/
├── download_pdfs.py
├── pdf_to_cbz.py
├── README.md
└── requirements.txt
```

---

## Dicas
- O script de download pula arquivos ja baixados.
- Para evitar erro 429, nao reduza muito o `DELAY_ENTRE_DOWNLOADS`.
- Teste a conversao em 1 capitulo antes de converter tudo.
