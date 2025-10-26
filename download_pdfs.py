#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import csv
import os
import re
import time
import json

BASE_URL = "https://centralnovel.com/series/lord-of-mysteries-20240505/"
AJAX_URL = "https://centralnovel.com/wp-admin/admin-ajax.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://centralnovel.com/'
}
DELAY_ENTRE_DOWNLOADS = 3
MAX_RETRIES = 3


def limpar_nome_arquivo(texto):
    texto = re.sub(r'[<>:"/\\|?*]', '', texto)
    texto = ' '.join(texto.split())
    return texto.replace(' ', '_')


def extrair_post_id_da_url(url_pdf_page):
    try:
        response = requests.get(url_pdf_page, headers=HEADERS, timeout=30)
        response.raise_for_status()
        match = re.search(r'"post_id":\s*(\d+)', response.text)
        if match:
            return match.group(1)
        match = re.search(r'data-id["\s]*[:=]["\s]*(\d+)', response.text)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"⚠️  Erro ao extrair post_id: {e}")
        return None


def obter_token_pdf(post_id, url_pdf_page):
    try:
        if not post_id or post_id == '':
            print(f"⚠️  Extraindo post_id da página...")
            post_id = extrair_post_id_da_url(url_pdf_page)
            if not post_id:
                print(f"❌ Não foi possível extrair post_id")
                return None
            print(f"✅ Post ID: {post_id}")

        headers = HEADERS.copy()
        headers['Referer'] = url_pdf_page
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        data = {'action': 'ts_ln_dl_url', 'post_id': post_id}
        response = requests.post(AJAX_URL, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get('error') == 0 and result.get('url'):
            return result['url'].replace('\\/', '/')
        else:
            print(f"⚠️  Resposta inesperada: {result}")
            return None
    except Exception as e:
        print(f"❌ Erro ao obter token: {e}")
        return None


def extrair_links_pdf(url):
    print(f"\n📥 Acessando: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        capitulos = soup.find_all('li', {'data-id': True})
        print(f"✅ Encontrados {len(capitulos)} capítulos")

        dados = []
        for cap in capitulos:
            try:
                post_id = cap.get('data-id')
                if not post_id:
                    continue

                epl_num = cap.find('div', class_='epl-num')
                if not epl_num:
                    continue

                match = re.search(r'Vol\.\s*(\d+)\s*Cap\.\s*(\d+)', epl_num.get_text(strip=True))
                if not match:
                    continue

                volume = match.group(1)
                capitulo = match.group(2)

                epl_title = cap.find('div', class_='epl-title')
                titulo = epl_title.get_text(strip=True) if epl_title else "Sem_Titulo"

                epl_date = cap.find('div', class_='epl-date')
                data = epl_date.get_text(strip=True) if epl_date else ""

                epl_pdf = cap.find('div', class_='epl-pdf')
                if epl_pdf:
                    link_tag = epl_pdf.find('a', class_='dlpdf')
                    if link_tag and link_tag.get('href'):
                        dados.append({
                            'volume': volume,
                            'capitulo': capitulo,
                            'titulo': titulo,
                            'url': link_tag['href'],
                            'data': data,
                            'post_id': post_id
                        })
            except Exception as e:
                print(f"⚠️  Erro ao processar capítulo: {e}")
                continue

        dados.sort(key=lambda x: (int(x['volume']), int(x['capitulo'])))
        return dados
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []


def salvar_links_csv(dados, arquivo='links_capitulos.csv'):
    if not dados:
        print("⚠️  Nenhum dado para salvar")
        return False
    try:
        with open(arquivo, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['volume', 'capitulo', 'titulo', 'url', 'data', 'post_id'])
            writer.writeheader()
            writer.writerows(dados)
        print(f"✅ Links salvos: {arquivo}")
        print(f"📊 Total: {len(dados)} capítulos")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar CSV: {e}")
        return False


def carregar_links_csv(arquivo='links_capitulos.csv'):
    if not os.path.exists(arquivo):
        print(f"⚠️  Arquivo {arquivo} não encontrado")
        return []
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados = list(csv.DictReader(f))
        print(f"✅ Carregados {len(dados)} capítulos")
        return dados
    except Exception as e:
        print(f"❌ Erro ao carregar CSV: {e}")
        return []


def criar_pasta_volume(volume):
    pasta = f"lord-of-mysteries-{volume.zfill(2)}"
    if not os.path.exists(pasta):
        os.makedirs(pasta)
        print(f"📁 Pasta criada: {pasta}")
    return pasta


def baixar_pdf(post_id, url_pdf_page, caminho_destino, tentativa=1):
    try:
        if os.path.exists(caminho_destino):
            print(f"⏭️  Já existe: {os.path.basename(caminho_destino)}")
            return True

        pdf_url_com_token = obter_token_pdf(post_id, url_pdf_page)
        if not pdf_url_com_token:
            print(f"❌ Não foi possível obter token")
            return False

        time.sleep(0.5)

        headers = HEADERS.copy()
        headers['Referer'] = url_pdf_page
        response = requests.get(pdf_url_com_token, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        with open(caminho_destino, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if os.path.getsize(caminho_destino) < 1000:
            print(f"⚠️  Arquivo muito pequeno, pode estar corrompido")
            os.remove(caminho_destino)
            return False

        print(f"✅ Baixado: {os.path.basename(caminho_destino)} ({os.path.getsize(caminho_destino)} bytes)")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429 and tentativa < MAX_RETRIES:
            wait_time = DELAY_ENTRE_DOWNLOADS * tentativa * 2
            print(f"⚠️  Erro 429. Aguardando {wait_time}s...")
            time.sleep(wait_time)
            return baixar_pdf(post_id, url_pdf_page, caminho_destino, tentativa + 1)
        else:
            print(f"❌ Erro HTTP: {e}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def download_capitulo_especifico(numero_capitulo, dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("❌ Execute a opção 1 primeiro")
        return

    capitulo = next((item for item in dados if item['capitulo'] == str(numero_capitulo)), None)
    if not capitulo:
        print(f"❌ Capítulo {numero_capitulo} não encontrado")
        return

    print(f"\n📥 Baixando capítulo {numero_capitulo}...")
    pasta = criar_pasta_volume(capitulo['volume'])
    titulo_limpo = limpar_nome_arquivo(capitulo['titulo'])
    nome_arquivo = f"Capitulo_{capitulo['capitulo'].zfill(3)}_{titulo_limpo}.pdf"
    caminho_completo = os.path.join(pasta, nome_arquivo)

    if baixar_pdf(capitulo.get('post_id'), capitulo['url'], caminho_completo):
        print(f"\n✅ Capítulo {numero_capitulo} baixado!")


def download_intervalo(inicio, fim, dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("❌ Execute a opção 1 primeiro")
        return

    capitulos_filtrados = [item for item in dados if inicio <= int(item['capitulo']) <= fim]
    if not capitulos_filtrados:
        print(f"❌ Nenhum capítulo no intervalo {inicio}-{fim}")
        return

    print(f"\n📥 Baixando {len(capitulos_filtrados)} capítulos ({inicio}-{fim})...")

    sucesso = falhas = 0
    for i, cap in enumerate(capitulos_filtrados, 1):
        print(f"\n[{i}/{len(capitulos_filtrados)}] Cap. {cap['capitulo']}: {cap['titulo']}")
        pasta = criar_pasta_volume(cap['volume'])
        titulo_limpo = limpar_nome_arquivo(cap['titulo'])
        nome_arquivo = f"Capitulo_{cap['capitulo'].zfill(3)}_{titulo_limpo}.pdf"
        caminho_completo = os.path.join(pasta, nome_arquivo)

        if baixar_pdf(cap.get('post_id'), cap['url'], caminho_completo):
            sucesso += 1
        else:
            falhas += 1

        if i < len(capitulos_filtrados):
            time.sleep(DELAY_ENTRE_DOWNLOADS)

    print(f"\n{'='*50}")
    print(f"✅ Sucessos: {sucesso}")
    print(f"❌ Falhas: {falhas}")
    print(f"{'='*50}")


def download_todos(dados=None):
    if dados is None:
        dados = carregar_links_csv()
    if not dados:
        print("❌ Execute a opção 1 primeiro")
        return

    print(f"\n📥 Baixando TODOS os {len(dados)} capítulos...")
    print(f"⏱️  Tempo estimado: ~{len(dados) * DELAY_ENTRE_DOWNLOADS / 60:.1f} min")

    confirmacao = input("\n⚠️  Continuar? (s/n): ")
    if confirmacao.lower() != 's':
        print("❌ Cancelado")
        return

    sucesso = falhas = 0
    for i, cap in enumerate(dados, 1):
        print(f"\n[{i}/{len(dados)}] Vol. {cap['volume']} Cap. {cap['capitulo']}: {cap['titulo']}")
        pasta = criar_pasta_volume(cap['volume'])
        titulo_limpo = limpar_nome_arquivo(cap['titulo'])
        nome_arquivo = f"Capitulo_{cap['capitulo'].zfill(3)}_{titulo_limpo}.pdf"
        caminho_completo = os.path.join(pasta, nome_arquivo)

        if baixar_pdf(cap.get('post_id'), cap['url'], caminho_completo):
            sucesso += 1
        else:
            falhas += 1

        if i < len(dados):
            time.sleep(DELAY_ENTRE_DOWNLOADS)

    print(f"\n{'='*50}")
    print(f"✅ Sucessos: {sucesso}")
    print(f"❌ Falhas: {falhas}")
    print(f"{'='*50}")


def menu_principal():
    print("="*60)
    print("LORD OF MYSTERIES - DOWNLOADER DE PDFs")
    print("="*60)

    while True:
        print("\nMENU")
        print("-" * 40)
        print("1. Extrair links")
        print("2. Baixar todos")
        print("3. Baixar capítulo específico")
        print("4. Baixar intervalo")
        print("5. Sair")
        print("-" * 40)

        escolha = input("\nOpção: ").strip()

        if escolha == '1':
            dados = extrair_links_pdf(BASE_URL)
            if dados:
                salvar_links_csv(dados)
                volumes = set(item['volume'] for item in dados)
                print(f"\n📊 Capítulos: {len(dados)}")
                print(f"   Volumes: {', '.join(sorted(volumes))}")

        elif escolha == '2':
            download_todos()

        elif escolha == '3':
            try:
                numero = int(input("\nCapítulo: ").strip())
                download_capitulo_especifico(numero)
            except ValueError:
                print("❌ Número inválido")

        elif escolha == '4':
            try:
                intervalo = input("\nIntervalo (ex: 10-200): ").strip()
                inicio, fim = map(int, intervalo.split('-'))
                if inicio > fim:
                    print("❌ Início deve ser menor que fim")
                else:
                    download_intervalo(inicio, fim)
            except ValueError:
                print("❌ Formato inválido")

        elif escolha == '5':
            print("\n👋 Encerrando...")
            break

        else:
            print("❌ Opção inválida")


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
