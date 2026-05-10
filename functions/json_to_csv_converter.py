import json
import csv
import os

# Configuração de caminhos para funcionar dentro de /functions
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def flatten_record(record):
    """
    Transforma o dicionário 'abstracts' em colunas separadas para o CSV.
    Ex: {'abstracts': {'portuguese': 'oi'}} vira {'abstract_portuguese': 'oi'}
    """
    new_record = {}
    for key, value in record.items():
        if key == 'abstracts' and isinstance(value, dict):
            for lang, text in value.items():
                new_record[f'abstract_{lang}'] = text
        else:
            new_record[key] = value
    return new_record

def convert_all_data_to_csv():
    print("\n" + "="*40)
    print("   📑 CONVERSOR JSONL -> CSV (DATA)   ")
    print("="*40)

    if not os.path.exists(DATA_DIR):
        print(f"❌ Pasta 'data' não encontrada em: {DATA_DIR}")
        return

    # Lista arquivos .jsonl
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.jsonl')]
    
    if not files:
        print(f"ℹ️ Nenhum arquivo .jsonl encontrado em: {DATA_DIR}")
        return

    print(f"📂 Arquivos encontrados: {len(files)}")

    for filename in files:
        input_path = os.path.join(DATA_DIR, filename)
        output_filename = filename.replace('.jsonl', '.csv')
        output_path = os.path.join(DATA_DIR, output_filename)
        
        print(f"\n🔄 Convertendo: {filename}...")
        
        count = 0
        try:
            # Primeiro passamos para coletar todos os cabeçalhos possíveis (headers)
            # Isso é importante porque um artigo pode ter abstract em ES e outro não
            fieldnames = set()
            records_to_save = []
            
            with open(input_path, 'r', encoding='utf-8') as infile:
                for line in infile:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        flat = flatten_record(record)
                        fieldnames.update(flat.keys())
                        records_to_save.append(flat)
                    except:
                        continue

            if not records_to_save:
                print(f"⚠️ Arquivo {filename} está vazio ou corrompido.")
                continue

            # Agora salvamos no CSV com a lista completa de cabeçalhos
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as outfile:
                # Ordenar fieldnames para manter padrão (opcional)
                sorted_fields = sorted(list(fieldnames))
                writer = csv.DictWriter(outfile, fieldnames=sorted_fields)
                writer.writeheader()
                
                for rec in records_to_save:
                    writer.writerow(rec)
                    count += 1
                    if count % 1000 == 0:
                        print(f"   > {count} registros processados...", end='\r')

            print(f"✅ Finalizado: {count} registros salvos em CSV.")
            
        except Exception as e:
            print(f"\n❌ Erro ao processar {filename}: {e}")

    print("\n" + "="*40)
    print("✨ TODOS OS ARQUIVOS FORAM CONVERTIDOS!")
    print("="*40)

if __name__ == '__main__':
    convert_all_data_to_csv()