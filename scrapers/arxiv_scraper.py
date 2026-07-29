"""
arXiv scraper — refactored so it can be driven by the GUI instead of
hardcoded constants. The scraping logic itself is unchanged from the
original script.
"""

import csv
import os
import re
import time
import random
import threading
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests
from langdetect import detect


def _filter_only_portuguese(mixed_text):
    if not mixed_text:
        return ""
    clean_text = mixed_text.replace("\n", " ").strip()
    sentences = re.split(r"\. ", clean_text)
    pt_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) < 25:
            continue
        try:
            if detect(s) == "pt":
                pt_sentences.append(s)
        except Exception:
            continue
    return ". ".join(pt_sentences) if pt_sentences else ""


def _load_existing_titles(output_path):
    titles = set()
    try:
        with open(output_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                titles.add(row["titulo"])
    except FileNotFoundError:
        pass
    return titles


def run_arxiv_scraper(
    search_query: str,
    output_path: str,
    batch_size: int = 50,
    min_pause: float = 6,
    max_start_index: int = 20000,
    portuguese_only: bool = True,
    log=print,
    stop_event: threading.Event | None = None,
):
    """
    Runs the arXiv scraper.

    search_query: raw arXiv API query string, e.g. 'cat:education*' or 'all:educação'
    output_path: path to the .csv file rows will be appended to
    batch_size: results requested per API call
    min_pause: minimum seconds to sleep between API calls (a few extra seconds are added)
    max_start_index: safety cap on how far into the result set to page
    portuguese_only: if True, keeps only sentences detected as Portuguese
    log: callable(str) used for progress/status messages
    stop_event: optional threading.Event; scraper stops cleanly when it is set
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    existing_titles = _load_existing_titles(output_path)
    log(f"Starting scan. Current base: {len(existing_titles)} articles.")

    if not existing_titles:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["data", "titulo", "autor", "abstract"])

    start = 0
    formatted_query = quote(search_query, safe="+: ")
    total_new = 0

    while start < max_start_index:
        if stop_event and stop_event.is_set():
            log("[Stopped] Stop requested by user.")
            break

        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query={formatted_query}&start={start}&max_results={batch_size}"
            "&sortBy=submittedDate&sortOrder=descending"
        )

        try:
            response = requests.get(url, timeout=60)

            if response.status_code == 429:
                log("[!] Rate limit hit. Pausing 10 min...")
                for _ in range(600):
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(1)
                continue

            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            if not entries:
                log(f"[End] No entries at index {start}. Trying a bit further...")
                start += 50
                if start > max_start_index:
                    break
                continue

            new_this_batch = 0
            for entry in entries:
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")

                if title in existing_titles:
                    continue

                summary_raw = entry.find("atom:summary", ns).text
                summary = _filter_only_portuguese(summary_raw) if portuguese_only else summary_raw.strip()

                if summary:
                    date = entry.find("atom:published", ns).text.split("T")[0]
                    author_tags = entry.findall("atom:author/atom:name", ns)
                    author = author_tags[0].text if author_tags else "N/A"

                    with open(output_path, "a", newline="", encoding="utf-8-sig") as f:
                        csv.writer(f).writerow([date, title, author, summary])

                    existing_titles.add(title)
                    new_this_batch += 1
                    total_new += 1
                    log(f"[saved #{len(existing_titles)}] {title[:50]}")

            log(f"Page done. {new_this_batch} new matching articles this batch.")

            start += batch_size
            time.sleep(random.uniform(min_pause, min_pause + 4))

        except Exception as e:
            log(f"[Error] {e}. Retrying...")
            time.sleep(20)

    log(f"[Done] arXiv scraper finished. New records saved this run: {total_new}")
    return total_new
