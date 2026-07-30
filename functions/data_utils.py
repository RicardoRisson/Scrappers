import csv
import json
import os

def merge_csv_files(file_paths, output_path, log_func=print):
    """Mescla múltiplos arquivos CSV alinhando colunas equivalentes."""
    if not file_paths:
        raise ValueError("Nenhum arquivo CSV selecionado.")

    ALIAS_MAP = {
        'titulo': 'title', 'Title': 'title',
        'autores': 'authors', 'author': 'authors', 'Authors': 'authors', 'Author': 'authors',
        'resumo': 'abstract', 'summary': 'abstract', 'Abstract': 'abstract',
        'ano': 'date', 'year': 'date', 'published': 'date', 'Year': 'date', 'Date': 'date',
        'doi': 'doi', 'DOI': 'doi',
        'url': 'url', 'link': 'url', 'URL': 'url', 'Link': 'url'
    }

    def normalize_header(name):
        if not name:
            return ""
        cleaned = name.strip()
        return ALIAS_MAP.get(cleaned.lower(), ALIAS_MAP.get(cleaned, cleaned))

    all_fieldnames = []

    # 1. Mapeia todas as colunas existentes entre todos os arquivos
    for fp in file_paths:
        with open(fp, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                for field in reader.fieldnames:
                    norm = normalize_header(field)
                    if norm and norm not in all_fieldnames:
                        all_fieldnames.append(norm)

    # 2. Escreve a mesclagem garantindo alinhamento
    with open(output_path, 'w', encoding='utf-8', newline='') as out_f:
        writer = csv.DictWriter(out_f, fieldnames=all_fieldnames)
        writer.writeheader()

        for fp in file_paths:
            log_func(f"Adicionando: {os.path.basename(fp)}")
            with open(fp, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    normalized_row = {}
                    for k, v in row.items():
                        if k is not None:
                            norm_k = normalize_header(k)
                            normalized_row[norm_k] = v
                    writer.writerow(normalized_row)

    log_func(f"Concluído! Salvo em: {output_path}")


def merge_jsonl_files(file_paths, output_path, log_func=print):
    """Mescla múltiplos arquivos JSON/JSONL em um único arquivo."""
    if not file_paths:
        raise ValueError("Nenhum arquivo JSONL selecionado.")

    total_lines = 0
    with open(output_path, 'w', encoding='utf-8') as out_f:
        for fp in file_paths:
            log_func(f"Adicionando: {os.path.basename(fp)}")
            with open(fp, 'r', encoding='utf-8') as in_f:
                for line in in_f:
                    if line.strip():
                        out_f.write(line.strip() + '\n')
                        total_lines += 1

    log_func(f"Concluído! {total_lines} registros mesclados em: {output_path}")


def convert_jsonl_to_csv(input_path, output_path, log_func=print):
    """Converte um arquivo JSON/JSONL para formato CSV."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    records = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))

    if not records:
        log_func("O arquivo JSON/JSONL está vazio.")
        return

    # Mapeia todas as chaves presentes nos objetos
    fieldnames = []
    for r in records:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    log_func(f"Conversão concluída! {len(records)} registros salvos em: {output_path}")