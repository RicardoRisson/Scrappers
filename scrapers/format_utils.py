"""
Utilitário de formato de saída.

Cada coletor grava nativamente em um formato (SciELO e OpenAlex em .jsonl,
arXiv em .csv). Este módulo converte para o outro formato quando solicitado
e remove o arquivo original quando ele não foi marcado para ser mantido.
"""

import csv
import json
import os


def jsonl_to_csv(jsonl_path: str, csv_path: str):
    records = []
    keys = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            records.append(record)
            for k in record.keys():
                if k not in keys:
                    keys.append(k)

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for record in records:
            row = {}
            for k in keys:
                value = record.get(k)
                if isinstance(value, list):
                    value = "; ".join(str(v) for v in value)
                row[k] = value
            writer.writerow(row)


def csv_to_jsonl(csv_path: str, jsonl_path: str):
    with open(csv_path, "r", encoding="utf-8-sig") as f_in, open(jsonl_path, "w", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in)
        for row in reader:
            f_out.write(json.dumps(row, ensure_ascii=False) + "\n")


def apply_format_choice(
    native_path: str,
    native_format: str,
    want_json: bool,
    want_csv: bool,
    log=print,
) -> list:
    """
    native_path: caminho do arquivo que o coletor realmente gravou (formato nativo)
    native_format: 'jsonl' ou 'csv'
    want_json / want_csv: valores das caixinhas de seleção
    Retorna a lista de arquivos finais mantidos no disco.
    """
    if native_format not in ("jsonl", "csv"):
        raise ValueError("native_format precisa ser 'jsonl' ou 'csv'")

    base, _ = os.path.splitext(native_path)
    jsonl_path = base + ".jsonl"
    csv_path = base + ".csv"

    if not os.path.exists(native_path):
        log(f"[Formato] Arquivo nativo não encontrado, nada para converter: {native_path}")
        return []

    if native_format == "jsonl":
        if want_csv and not os.path.exists(csv_path):
            log(f"[Formato] Convertendo para CSV: {csv_path}")
            jsonl_to_csv(native_path, csv_path)
        if not want_json:
            os.remove(native_path)
            log("[Formato] Removido o .jsonl (apenas CSV foi solicitado).")
    else:  # native_format == "csv"
        if want_json and not os.path.exists(jsonl_path):
            log(f"[Formato] Convertendo para JSON: {jsonl_path}")
            csv_to_jsonl(native_path, jsonl_path)
        if not want_csv:
            os.remove(native_path)
            log("[Formato] Removido o .csv (apenas JSON foi solicitado).")

    kept = []
    if want_json and os.path.exists(jsonl_path):
        kept.append(jsonl_path)
    if want_csv and os.path.exists(csv_path):
        kept.append(csv_path)
    return kept
