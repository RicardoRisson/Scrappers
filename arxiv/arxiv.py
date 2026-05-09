import requests
import xml.etree.ElementTree as ET
import csv
import re
import time
import random
from langdetect import detect
from urllib.parse import quote  # Import necessário para tratar os acentos

# --- CONFIGURAÇÕES OTIMIZADAS ---
EMAIL_CONTATO = "email@dominio.com"
ARQUIVO_SAIDA = "dataset_computacao_pt.csv"

# Mudamos para buscar "computação" OU "computacao" para dobrar o alcance
TERMO_BUSCA = 'cat:cs.*' 

BATCH_SIZE = 50 
PAUSA_MINIMA = 6

def narrar(mensagem):
    print(f"[{time.strftime('%H:%M:%S')}] {mensagem}")

def filtrar_apenas_portugues(texto_misto):
    if not texto_misto: return ""
    texto_limpo = texto_misto.replace('\n', ' ').strip()
    sentencas = re.split(r'\. ', texto_limpo)
    frases_pt = []
    for s in sentencas:
        s = s.strip()
        if len(s) < 25: continue
        try:
            if detect(s) == 'pt': frases_pt.append(s)
        except: continue
    return ". ".join(frases_pt) if frases_pt else ""

def carregar_titulos_existentes():
    titulos = set()
    try:
        with open(ARQUIVO_SAIDA, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader: titulos.add(row['titulo'])
    except FileNotFoundError: pass
    return titulos

def minerador_v2():
    titulos_ja_salvos = carregar_titulos_existentes()
    narrar(f"🚀 Varredura iniciada. Base atual: {len(titulos_ja_salvos)} artigos.")

    if not titulos_ja_salvos:
        with open(ARQUIVO_SAIDA, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(['data', 'titulo', 'autor', 'abstract'])

    start = 0
    # Aplicamos o quote aqui para que o termo com acento seja aceito pela API do arXiv
    termo_formatado = quote(TERMO_BUSCA, safe='+: ')

    # Aumentamos o limite para garantir que ele tente buscar até o fim dos tempos
    while start < 30000: 
        # A URL agora usa o termo formatado
        url = f"http://export.arxiv.org/api/query?search_query={termo_formatado}&start={start}&max_results={BATCH_SIZE}&sortBy=submittedDate&sortOrder=descending"
        
        try:
            response = requests.get(url, timeout=60)
            
            if response.status_code == 429:
                narrar("⚠️ Rate Limit! Pausando 10 min...")
                time.sleep(600)
                continue

            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)

            if not entries:
                narrar(f"🏁 Fim da linha no índice {start}. Tentando saltar mais 50 para garantir...")
                start += 50
                # CORREÇÃO: Aumentamos este limite. Antes ele parava em 200, agora vai até o limite do while.
                if start > 20000: 
                    break
                continue

            novos_neste_lote = 0
            for entry in entries:
                titulo = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                
                # Se o título já existe, apenas pulamos para o próximo
                if titulo in titulos_ja_salvos:
                    continue

                resumo_pt = filtrar_apenas_portugues(entry.find('atom:summary', ns).text)
                if resumo_pt:
                    data = entry.find('atom:published', ns).text.split('T')[0]
                    autores_tags = entry.findall('atom:author/atom:name', ns)
                    autor = autores_tags[0].text if autores_tags else "N/A"

                    with open(ARQUIVO_SAIDA, 'a', newline='', encoding='utf-8-sig') as f:
                        csv.writer(f).writerow([data, titulo, autor, resumo_pt])
                    
                    titulos_ja_salvos.add(titulo)
                    novos_neste_lote += 1
                    narrar(f"✅ Salvo [{len(titulos_ja_salvos)}]: {titulo[:40]}...")

            narrar(f"📄 Página finalizada. {novos_neste_lote} novos artigos PT encontrados neste lote.")
            
            start += BATCH_SIZE
            time.sleep(random.uniform(PAUSA_MINIMA, PAUSA_MINIMA + 4))

        except Exception as e:
            narrar(f"💥 Erro: {e}. Retentando...")
            time.sleep(20)

if __name__ == "__main__":
    minerador_v2()
