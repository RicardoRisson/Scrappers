import requests
import json
import time
import os

def reconstruct_abstract(inverted_index):
    """
    Reconstructs the abstract from the OpenAlex inverted index format.
    """
    if not inverted_index:
        return None
    
    word_index = {}
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            word_index[pos] = word
            
    sorted_positions = sorted(word_index.keys())
    return " ".join([word_index[i] for i in sorted_positions])

def fetch_openalex_data(query_term, email_contact):
    """
    Fetches records from OpenAlex and saves them into the ../data directory.
    """
    endpoint = "https://api.openalex.org/works"
    cursor = "*"
    
    # Define path to 'data' folder at the same level as 'scholar'
    # os.path.join(os.getcwd(), "..", "data") handles the navigation correctly
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "data"))
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_filename = os.path.join(output_dir, "data_export_education.jsonl")
    total_records = 0

    print(f"Directory: {output_dir}")
    print(f"Target file: {output_filename}")

    with open(output_filename, "a", encoding="utf-8") as f:
        while True:
            params = {
                'filter': f'default.search:{query_term},language:pt',
                'per_page': 200,
                'cursor': cursor,
                'mailto': email_contact
            }

            try:
                response = requests.get(endpoint, params=params)
                
                if response.status_code != 200:
                    print(f"\nError {response.status_code}: Data collection interrupted.")
                    break
                
                data = response.json()
                results = data.get('results', [])
                
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
                        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
                        "doi": work.get("doi"),
                        "openalex_id": work.get("id")
                    }
                    
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_records += 1

                print(f"Records collected: {total_records}", end="\r")

                next_cursor = data.get('meta', {}).get('next_cursor')
                if not next_cursor or next_cursor == cursor:
                    break
                
                cursor = next_cursor
                time.sleep(0.05)

            except Exception as e:
                print(f"\nCritical error: {e}")
                break

    print(f"\nProcess finished. Total records saved: {total_records}")

if __name__ == "__main__":
    SEARCH_TERM = "educação"
    CONTACT_EMAIL = "email@dominio.com"
    
    fetch_openalex_data(SEARCH_TERM, CONTACT_EMAIL)