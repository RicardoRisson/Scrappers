import os
import json
import asyncio
import hashlib
import time
import random
import urllib.parse
import re
import aiohttp
import aiofiles
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES DE CAMINHOS ---
DATA_DIR = "data"
RAW_FILE = os.path.join(DATA_DIR, "dataset_raw.jsonl")
LOG_FILE = "logs/pipeline_log.jsonl"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# --- UTILITÁRIOS ---
async def log_event(event: dict):
    async with aiofiles.open(LOG_FILE, "a") as f:
        await f.write(json.dumps(event) + "\n")

def extract_pid(url: str) -> str:
    match = re.search(r"pid=S([\d\-X]+)", url)
    return match.group(1) if match else hashlib.md5(url.encode()).hexdigest()

# --- GESTÃO DE COOKIES (BUNNY SHIELD) ---
async def refresh_scielo_cookie():
    """Gera o cookie necessário para ultrapassar o firewall da SciELO."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("[Cookie] Acessando SciELO para validar Shield...")
        await page.goto("https://search.scielo.org/", wait_until="networkidle")
        
        # Espera o cookie de segurança ser injetado
        await asyncio.sleep(2) 
        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        await browser.close()
        os.environ["SCIELO_COOKIE"] = cookie_str
        return cookie_str

# --- ENGINE DE EXTRAÇÃO ---
async def fetch_content(session, url, params=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Cookie": os.environ.get("SCIELO_COOKIE", "")
    }
    try:
        async with session.get(url, params=params, headers=headers, timeout=20) as resp:
            if resp.status == 200:
                return await resp.text()
            if resp.status == 403:
                print("[!] Bloqueado (403). Atualizando Cookie...")
                await refresh_scielo_cookie()
    except Exception as e:
        await log_event({"event": "fetch_error", "url": url, "error": str(e)})
    return None

async def process_scielo_search(query: str, max_pages: int = 5):
    async with aiohttp.ClientSession() as session:
        # Garante que temos um cookie inicial
        if not os.environ.get("SCIELO_COOKIE"):
            await refresh_scielo_cookie()

        for page_num in range(max_pages):
            from_record = page_num * 20
            params = {
                "q": query,
                "lang": "pt",
                "count": 20,
                "from": from_record,
                "format": "abstract"
            }
            
            print(f"[*] Buscando SciELO - Página {page_num + 1}...")
            html = await fetch_content(session, "https://search.scielo.org/", params=params)
            
            if not html: break
            
            soup = BeautifulSoup(html, "lxml")
            articles = soup.select("div.results div.item")
            
            if not articles:
                print("[!] Sem mais resultados.")
                break

            async with aiofiles.open(RAW_FILE, "a", encoding="utf-8") as f:
                for art in articles:
                    try:
                        # Extração de Metadados
                        link_tag = art.find("a", title=True)
                        if not link_tag: continue
                        
                        url = link_tag.get("href", "")
                        title = link_tag.get_text(strip=True)
                        
                        authors_div = art.select_one("div.authors")
                        authors = [a.strip() for a in authors_div.text.split(";")] if authors_div else []
                        
                        source_div = art.select_one("div.source")
                        year_match = re.search(r"(19|20)\d{2}", source_div.text) if source_div else None
                        year = int(year_match.group(0)) if year_match else None
                        
                        # Abstract (SciELO costuma colocar inline no modo 'abstract')
                        abstract_div = art.select_one("div.abstract")
                        abstract_text = abstract_div.get_text(strip=True) if abstract_div else ""

                        # Montagem do Objeto igual ao OpenAlex/Outros
                        record = {
                            "title": title,
                            "authors": authors,
                            "publication_year": year,
                            "abstract": abstract_text,
                            "doi": extract_pid(url), # SciELO usa PID no lugar do DOI muitas vezes
                            "url": url,
                            "source": "scielo"
                        }

                        await f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        await log_event({"event": "record_saved", "source": "scielo", "title": title[:50]})
                    
                    except Exception as e:
                        continue
            
            # Delay humano para evitar ban
            await asyncio.sleep(random.uniform(2, 5))

# --- EXECUÇÃO ---
if __name__ == "__main__":
    SEARCH_TERM = "educação"
    asyncio.run(process_scielo_search(SEARCH_TERM, max_pages=10))