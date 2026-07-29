"""
OpenAlex scraper — refactored so it can be driven by the GUI instead of
hardcoded constants. The scraping logic itself is unchanged from the
original script.
"""

import json
import os
import time
import threading

import requests


def _reconstruct_abstract(inverted_index):
    """Reconstructs the abstract from the OpenAlex inverted index format."""
    if not inverted_index:
        return None

    word_index = {}
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            word_index[pos] = word

    sorted_positions = sorted(word_index.keys())
    return " ".join(word_index[i] for i in sorted_positions)


def run_openalex_scraper(
    query_term: str,
    email_contact: str,
    output_path: str,
    language: str = "pt",
    log=print,
    stop_event: threading.Event | None = None,
):
    """
    Runs the OpenAlex scraper.

    query_term: search text, e.g. "educação"
    email_contact: contact email sent to OpenAlex's API (required by their usage policy)
    output_path: path to the .jsonl file records will be appended to
    language: language filter code, e.g. "pt"
    log: callable(str) used for progress/status messages
    stop_event: optional threading.Event; scraper stops cleanly when it is set
    """
    endpoint = "https://api.openalex.org/works"
    cursor = "*"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    total_records = 0

    log(f"Target file: {output_path}")

    with open(output_path, "a", encoding="utf-8") as f:
        while True:
            if stop_event and stop_event.is_set():
                log("[Stopped] Stop requested by user.")
                break

            params = {
                "filter": f"default.search:{query_term},language:{language}",
                "per_page": 200,
                "cursor": cursor,
                "mailto": email_contact,
            }

            try:
                response = requests.get(endpoint, params=params)

                if response.status_code != 200:
                    log(f"[Error {response.status_code}] Data collection interrupted.")
                    break

                data = response.json()
                results = data.get("results", [])

                if not results:
                    break

                for work in results:
                    record = {
                        "title": work.get("display_name"),
                        "authors": [
                            auth.get("author", {}).get("display_name")
                            for auth in work.get("authorships", [])
                        ],
                        "publication_year": work.get("publication_year"),
                        "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
                        "doi": work.get("doi"),
                        "openalex_id": work.get("id"),
                    }

                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_records += 1

                log(f"Records collected so far: {total_records}")

                next_cursor = data.get("meta", {}).get("next_cursor")
                if not next_cursor or next_cursor == cursor:
                    break

                cursor = next_cursor
                time.sleep(0.05)

            except Exception as e:
                log(f"[Critical error] {e}")
                break

    log(f"[Done] OpenAlex scraper finished. Total records saved: {total_records}")
    return total_records
