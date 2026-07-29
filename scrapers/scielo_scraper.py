import os
import json
import asyncio
import hashlib
import re
import random
import threading

import aiohttp
import aiofiles
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Define o User-Agent global para garantir que o Playwright e o aiohttp usem a mesma assinatura
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

def extract_pid(url: str) -> str:
    match = re.search(r"pid=S([\d\-X]+)", url)
    return match.group(1) if match else hashlib.md5(url.encode()).hexdigest()

async def _launch_browser_with_fallback(p, headless: bool, log):
    """
    Tenta abrir o navegador do Playwright. Se estiver rodando via .exe
    e faltar o binário, tenta usar o Chrome do Windows e depois o MS Edge.
    """
    try:
        return await p.chromium.launch(headless=headless)
    except Exception:
        log("[Navegador] Chromium interno não encontrado. Tentando Google Chrome...")

    try:
        return await p.chromium.launch(headless=headless, channel="chrome")
    except Exception:
        log("[Navegador] Google Chrome não encontrado. Tentando Microsoft Edge...")

    try:
        return await p.chromium.launch(headless=headless, channel="msedge")
    except Exception as e:
        log("[Erro Fatal] Nenhum navegador (Chrome/Edge) foi detectado no sistema.")
        raise e

async def _refresh_scielo_cookie(headless: bool, log):
    """Generates the cookie needed to get past SciELO's bot-protection shield."""
    async with async_playwright() as p:
        browser = await _launch_browser_with_fallback(p, headless, log)
        
        context = await browser.new_context(
            user_agent=USER_AGENT, # Usa a constante global
            viewport={"width": 1280, "height": 720},
        )
        
        page = await context.new_page()
        
        # Oculta a propriedade 'navigator.webdriver' que os bloqueadores detectam
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        log("[Cookie] Acessando SciELO para validar a proteção (Shield)...")
        try:
            await page.goto("https://search.scielo.org/", wait_until="domcontentloaded", timeout=30000)
            
            # Dá tempo para o Cloudflare validar e injetar os cookies
            log("[Cookie] Aguardando validação de segurança (6 segundos)...")
            await asyncio.sleep(6)
            
            cookies = await context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('value'))
            
            os.environ["SCIELO_COOKIE"] = cookie_str
            log(f"[Cookie] Capturado com sucesso! (Tamanho: {len(cookie_str)})")
            return cookie_str
        except Exception as e:
            log(f"[Cookie] Erro ao obter cookie: {e}")
            return ""
        finally:
            await browser.close()

async def _fetch_content(session, url, headless, log, params=None):
    """Faz a requisição com sistema de retentativa em caso de erro 403."""
    max_retries = 2 # Tenta até 2 vezes caso seja bloqueado
    
    for attempt in range(max_retries):
        headers = {
            "User-Agent": USER_AGENT, # Mesmo do Playwright
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": os.environ.get("SCIELO_COOKIE", ""),
        }
        
        try:
            async with session.get(url, params=params, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    return await resp.text()
                if resp.status == 403:
                    log(f"[!] Blocked (403) na tentativa {attempt+1}/{max_retries}. Atualizando cookie...")
                    await _refresh_scielo_cookie(headless, log)
                    continue # Volta para o início do loop e tenta de novo com o novo cookie
        except Exception as e:
            log(f"[fetch_error] {url} -> {e}")
            
    return None # Retorna None apenas se falhar todas as tentativas

async def run_scielo_scraper(
    query: str,
    max_pages: int,
    output_path: str,
    headless: bool = False,
    log=print,
    stop_event: threading.Event | None = None,
):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    total_saved = 0

    async with aiohttp.ClientSession() as session:
        if not os.environ.get("SCIELO_COOKIE"):
            await _refresh_scielo_cookie(headless, log)

        for page_num in range(max_pages):
            if stop_event and stop_event.is_set():
                log("[Stopped] Stop requested by user.")
                break

            from_record = page_num * 20
            params = {
                "q": query,
                "lang": "pt",
                "count": 20,
                "from": from_record,
                "format": "abstract",
            }

            log(f"[*] Fetching SciELO - page {page_num + 1}/{max_pages}...")
            html = await _fetch_content(session, "https://search.scielo.org/", headless, log, params=params)

            if not html:
                log("[!] No response or max retries reached, stopping.")
                break

            soup = BeautifulSoup(html, "lxml")
            articles = soup.select("div.results div.item")

            if not articles:
                log("[!] No more results.")
                break

            async with aiofiles.open(output_path, "a", encoding="utf-8") as f:
                for art in articles:
                    try:
                        link_tag = art.find("a", title=True)
                        if not link_tag:
                            continue

                        url_art = link_tag.get("href", "")
                        title = link_tag.get_text(strip=True)

                        authors_div = art.select_one("div.authors")
                        authors = [a.strip() for a in authors_div.text.split(";")] if authors_div else []

                        source_div = art.select_one("div.source")
                        year_match = re.search(r"(19|20)\d{2}", source_div.text) if source_div else None
                        year = int(year_match.group(0)) if year_match else None

                        abstract_div = art.select_one("div.abstract")
                        abstract_text = abstract_div.get_text(strip=True) if abstract_div else ""

                        record = {
                            "title": title,
                            "authors": authors,
                            "publication_year": year,
                            "abstract": abstract_text,
                            "doi": extract_pid(url_art),
                            "url": url_art,
                            "source": "scielo",
                        }

                        await f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        total_saved += 1
                        log(f"[saved #{total_saved}] {title[:60]}")

                    except Exception:
                        continue

            await asyncio.sleep(random.uniform(2, 5))

    log(f"[Done] SciELO scraper finished. Records saved this run: {total_saved}")
    return total_saved
