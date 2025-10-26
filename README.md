# Centralnovel Downloader - Lord of Mysteries

Automação em Python para baixar capítulos da novel **Lord of Mysteries** do site [Centralnovel](https://centralnovel.com/) e converter PDFs em formato CBZ.

**Novel**: [Lord of Mysteries - Centralnovel](https://centralnovel.com/manga/lord-of-the-mysteries/)

> Este projeto foi criado especificamente para baixar esta novel do Centralnovel. Os scripts podem não funcionar com outros sites ou novels.

---

## 📥 Script 1: Download de PDFs (download_pdfs.py)

### Como usar:
```bash
python download_pdfs.py
```

### Opções do menu:
1. **Extrair links** - Busca todos os capítulos disponíveis no site
2. **Baixar todos** - Baixa todos os capítulos
3. **Baixar específico** - Baixa um capítulo (ex: 213)
4. **Baixar intervalo** - Baixa vários capítulos (ex: 1-50)

### Primeira vez:
```bash
# 1. Instale as dependências
pip install -r requirements.txt

# 2. Execute o script
python download_pdfs.py

# 3. Escolha opção 1 para extrair os links
# 4. Depois escolha opção 2, 3 ou 4 para baixar
```

### Configurações:
No arquivo `download_pdfs.py`, linha 24-25:
```python
DELAY_ENTRE_DOWNLOADS = 3  # segundos entre downloads
MAX_RETRIES = 3            # tentativas por download
```

### Saída:
```
Novel Download/
├── links_capitulos.csv (lista de todos os capítulos)
├── lord-of-mysteries-01/
│   ├── Capitulo_001_Titulo.pdf
│   ├── Capitulo_002_Titulo.pdf
│   └── ...
├── lord-of-mysteries-02/
│   └── ...
```

---

## 📚 Script 2: PDF para CBZ (pdf_to_cbz.py)

Converte PDFs em formato CBZ (Comic Book Archive) para leitura em apps de quadrinhos.

### Como usar:
```bash
python pdf_to_cbz.py
```

### Opções do menu:
1. **Converter arquivo** - Converte um PDF específico
2. **Converter pasta** - Converte todos os PDFs de uma pasta
3. **Converter tudo** - Converte todos os PDFs (incluindo subpastas)

### Primeira vez:
```bash
# 1. Instale as dependências
pip install -r requirements_pdf_to_cbz.txt

# 2. O Poppler já deve estar instalado (C:\poppler)
# 3. Execute o script
python pdf_to_cbz.py
```

### Configurações:
No arquivo `pdf_to_cbz.py`, linha 32-33:
```python
QUALIDADE_JPG = 95  # 0-100 (qualidade da imagem)
DPI = 150           # resolução (150 = ótimo para tablets)
```

#### Recomendações por dispositivo:
| Dispositivo | DPI | Qualidade | Tamanho por cap* |
|-------------|-----|-----------|------------------|
| Celular | 150 | 80 | ~2-3 MB |
| Tablet | 150 | 85 | ~3-4 MB |
| PC/Monitor | 200 | 90 | ~5-6 MB |
| 4K | 250 | 95 | ~8-10 MB |

*Baseado em capítulo de 7 páginas

### Saída:
```
Capitulo_001_Carmesim.pdf → Capitulo_001_Carmesim.cbz
```

Cada CBZ contém imagens numeradas:
```
Capitulo_001_Carmesim.cbz (ZIP)
├── 001.jpg (página 1)
├── 002.jpg (página 2)
├── 003.jpg (página 3)
└── ...
```

### Leitores compatíveis:
- **Windows**: CDisplayEx, Sumatra PDF, YACReader
- **Android**: Tachiyomi, PerfectViewer
- **iOS**: Panels, Chunky
- **Linux/Mac**: YACReader

---

## 📦 Dependências

### Para download_pdfs.py:
```bash
pip install requests beautifulsoup4 lxml
```

### Para pdf_to_cbz.py:
```bash
pip install pdf2image Pillow
```

**Importante**: O Poppler deve estar instalado em `C:\poppler\poppler-24.08.0\Library\bin`

---

## 🔧 Solução de Problemas

### Erro ao baixar PDFs:
- **429 Too Many Requests**: O script já tem retry automático, aguarde
- **post_id não encontrado**: Execute a opção 1 primeiro para atualizar o CSV

### Erro ao converter PDFs:
- **Poppler not found**: Verifique se está instalado em `C:\poppler`
- **Qualidade ruim**: Aumente `DPI` ou `QUALIDADE_JPG`
- **Arquivos grandes**: Diminua `DPI` para 120 e `QUALIDADE_JPG` para 80

---

## 📂 Estrutura de Arquivos

```
Novel Download/
├── download_pdfs.py              # Script de download
├── pdf_to_cbz.py                 # Conversor PDF→CBZ
├── requirements.txt              # Dependências do downloader
├── requirements_pdf_to_cbz.txt   # Dependências do conversor
├── LEIA-ME.md                    # Este arquivo
├── links_capitulos.csv           # Lista de capítulos (gerado)
└── lord-of-mysteries-XX/         # Pastas com PDFs (geradas)
```

---

## 💡 Dicas

### Download:
- Execute a opção 1 uma vez para extrair todos os links
- Use opção 4 para baixar em lotes (ex: 1-50, 51-100)
- O script pula arquivos já baixados automaticamente

### Conversão:
- Teste com 1 capítulo primeiro para ajustar DPI/qualidade
- Use opção 2 para converter pastas inteiras de uma vez
- CBZ = ZIP, pode renomear e extrair manualmente se precisar

### Organização:
- Mantenha PDFs e CBZs em pastas separadas
- Use nomes descritivos nas pastas (ex: `CBZ - Tablet`, `CBZ - PC`)

---

## 📊 Exemplo Completo

```bash
# 1. Baixar todos os capítulos do volume 1
python download_pdfs.py
# Escolha: 1 (extrair links)
# Escolha: 4 (intervalo: 1-213)

# 2. Converter todos para CBZ
python pdf_to_cbz.py
# Escolha: 2
# Pasta: C:\Users\alcan\Downloads\Novel Donwload\lord-of-mysteries-01

# 3. Resultado:
# - lord-of-mysteries-01/Capitulo_XXX.pdf (originais)
# - lord-of-mysteries-01/Capitulo_XXX.cbz (convertidos)
```

---

## ⚙️ Configurações Avançadas

### Economizar espaço (centenas de capítulos):
```python
# pdf_to_cbz.py
QUALIDADE_JPG = 75
DPI = 120
# Resultado: ~1.5 MB por capítulo (vs ~4 MB)
```

### Máxima qualidade (monitor 4K):
```python
# pdf_to_cbz.py
QUALIDADE_JPG = 95
DPI = 250
# Resultado: ~10 MB por capítulo
```

### Download mais rápido:
```python
# download_pdfs.py
DELAY_ENTRE_DOWNLOADS = 2  # cuidado com erro 429
```

---

**Criado com Claude Code** 🤖
