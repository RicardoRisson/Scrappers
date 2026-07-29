import json
import os
from langdetect import detect, DetectorFactory

# Garante que a detecção seja consistente entre as execuções
DetectorFactory.seed = 0

# Configuração de caminhos para rodar dentro de /functions
# BASE_DIR aponta para a raiz do projeto (um nível acima de /functions)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def listar_jsonls():
    """Lista arquivos .jsonl na raiz e na pasta /data, ignorando os já filtrados"""
    arquivos_encontrados = []
    pastas_para_buscar = [BASE_DIR, DATA_DIR]
    
    for pasta in pastas_para_buscar:
        if os.path.exists(pasta):
            for f in os.listdir(pasta):
                if f.endswith(".jsonl") and "_filtrado" not in f:
                    caminho = os.path.join(pasta, f)
                    if caminho not in arquivos_encontrados:
                        arquivos_encontrados.append(caminho)
    return arquivos_encontrados

def filtrar_apenas_portugues():
    print("\n" + "="*45)
    print("   🔍 FILTRAR IDIOMA REAL (EXCLUSIVO: PT)   ")
    print("="*45)

    # 1. Menu de seleção de arquivos
    arquivos = listar_jsonls()
    
    if not arquivos:
        print(f"❌ Nenhum arquivo .jsonl encontrado em {BASE_DIR} ou {DATA_DIR}.")
        return

    print("\nArquivos disponíveis:")
    for i, caminho in enumerate(arquivos, 1):
        nome_exibicao = os.path.relpath(caminho, BASE_DIR)
        print(f"{i}. {nome_exibicao}")

    try:
        escolha = int(input("\nEscolha o número do arquivo: ")) - 1
        input_path = arquivos[escolha]
    except (ValueError, IndexError):
        print("❌ Escolha inválida!")
        return

    # 2. Caminho de saída (Pasta data na raiz)
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    nome_arquivo_base = os.path.basename(input_path).replace(".jsonl", "_filtrado_pt.jsonl")
    output_path = os.path.join(DATA_DIR, nome_arquivo_base)

    mantidos = 0
    removidos = 0

    print(f"\n⚙️  Analisando conteúdo... Somente Português será mantido.")

    try:
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    
                    # Tenta pegar o resumo de qualquer campo (abstract ou abstracts)
                    abstract_puro = data.get("abstract") 
                    abstract_dict = data.get("abstracts")
                    
                    texto_para_analisar = ""
                    
                    if isinstance(abstract_dict, dict):
                        # Pega o resumo em português se existir, ou o primeiro disponível
                        texto_para_analisar = abstract_dict.get("portuguese") or next(iter(abstract_dict.values()), "")
                    elif isinstance(abstract_puro, str):
                        texto_para_analisar = abstract_puro

                    # Validação de tamanho para evitar erros na detecção
                    if not texto_para_analisar or len(texto_para_analisar) < 30:
                        removidos += 1
                        continue

                    # 3. Detecção de Idioma (Filtro Rígido)
                    try:
                        idioma = detect(texto_para_analisar)
                        
                        # EXCLUSÃO TOTAL: Se não for 'pt', joga fora.
                        if idioma == 'pt':
                            # Padroniza a saída sempre para {"abstracts": {"portuguese": "..."}}
                            data["abstracts"] = {"portuguese": texto_para_analisar}
                            
                            # Remove o campo antigo "abstract" se ele existir
                            if "abstract" in data: del data["abstract"]
                            
                            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                            mantidos += 1
                        else:
                            removidos += 1
                    except:
                        # Em caso de falha na detecção, descarta por segurança
                        removidos += 1
                            
                except Exception:
                    continue

        print("\n" + "="*45)
        print(f"✅ PROCESSAMENTO CONCLUÍDO!")
        print(f"📊 Artigos em Português: {mantidos}")
        print(f"🗑️  Artigos descartados (outras línguas): {removidos}")
        print(f"💾 Resultado: {output_path}")
        print("="*45)

    except Exception as e:
        print(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    filtrar_apenas_portugues()