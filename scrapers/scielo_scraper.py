"""
SciELO scraper — refactored so it can be driven by the GUI instead of
hardcoded constants. The scraping logic itself is unchanged from the
original script.
"""

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


def extract_pid(url: str) -> str:
    match = re.search(r"pid=S([\d\-X]+)", url)
    return match.group(1) if match else hashlib.md5(url.encode()).hexdigest()


async def _refresh_scielo_cookie(headless: bool, log):
    """Generates the cookie needed to get past SciELO's bot-protection shield."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        log("[Cookie] Accessing SciELO to validate the Shield...")
        await page.goto("https://search.scielo.org/", wait_until="networkidle")

        # Wait for the security cookie to be injected
        await asyncio.sleep(2)
        cookies = await context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()
        os.environ["SCIELO_COOKIE"] = cookie_str
        return cookie_str


async def _fetch_content(session, url, headless, log, params=None):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ),
        "Cookie": os.environ.get("SCIELO_COOKIE", ""),
    }
    try:
        async with session.get(url, params=params, headers=headers, timeout=20) as resp:
            if resp.status == 200:
                return await resp.text()
            if resp.status == 403:
                log("[!] Blocked (403). Refreshing cookie...")
                await _refresh_scielo_cookie(headless, log)
    except Exception as e:
        log(f"[fetch_error] {url} -> {e}")
    return None


async def run_scielo_scraper(
    query: str,
    max_pages: int,
    output_path: str,
    headless: bool = False,
    log=print,
    stop_event: threading.Event | None = None,
):
    """
    Runs the SciELO search scraper.

    query: search term (e.g. "educação")
    max_pages: number of result pages to fetch (20 records per page)
    output_path: path to the .jsonl file records will be appended to
    headless: whether the cookie-refresh browser window is visible
    log: callable(str) used for progress/status messages
    stop_event: optional asyncio.Event; scraper stops cleanly when it is set
    """
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
                log("[!] No response, stopping.")
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

                        url = link_tag.get("href", "")
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
                            "doi": extract_pid(url),
                            "url": url,
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
