import pandas as pd
import os

# Configuração para funcionar corretamente dentro de /functions
# Sobe um nível para encontrar a raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def listar_csvs():
    """Busca arquivos .csv na raiz e na pasta /data"""
    extensoes = ('.csv')
    arquivos_encontrados = []

    # Busca na pasta raiz do projeto e na subpasta /data
    pastas_para_buscar = [BASE_DIR, DATA_DIR]
    
    for pasta in pastas_para_buscar:
        if os.path.exists(pasta):
            for f in os.listdir(pasta):
                if f.endswith(extensoes):
                    caminho_completo = os.path.join(pasta, f)
                    # Evita duplicados e não lista o arquivo se ele já for um resultado final anterior
                    if caminho_completo not in arquivos_encontrados:
                        arquivos_encontrados.append(caminho_completo)
    
    return arquivos_encontrados

def merge_csvs_melhorado():
    print("\n" + "="*40)
    print("      📊 UNIFICADOR DE CSVs (MENU)      ")
    print("="*40)

    # 1. Listar arquivos
    csvs = listar_csvs()
    
    if not csvs:
        print(f"❌ Nenhum arquivo CSV encontrado em {BASE_DIR} ou {DATA_DIR}.")
        return

    print("\nArquivos disponíveis para unificar:")
    for i, caminho in enumerate(csvs, 1):
        # Mostra o caminho relativo à raiz para ficar mais fácil de ler
        nome_exibicao = os.path.relpath(caminho, BASE_DIR)
        print(f"{i}. {nome_exibicao}")

    # 2. Seleção de arquivos
    try:
        selecao = input("\nDigite os números dos arquivos (ex: 1 2 5): ")
        indices = [int(n.strip()) - 1 for n in selecao.replace(',', ' ').split()]
        
        arquivos_selecionados = [csvs[idx] for idx in indices]
    except (ValueError, IndexError):
        print("❌ Seleção inválida. Use os números da lista.")
        return

    # 3. Nome do arquivo final
    nome_final = input("💾 Nome do arquivo de saída (sem .csv): ").strip()
    if not nome_final.endswith('.csv'):
        nome_final += '.csv'
    
    # Garante que a pasta data existe na raiz
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    caminho_saida = os.path.join(DATA_DIR, nome_final)

    # 4. Processamento com Pandas
    try:
        lista_dfs = []
        print(f"\n⏳ Lendo {len(arquivos_selecionados)} arquivos...")
        
        for caminho in arquivos_selecionados:
            # low_memory=False ajuda se os CSVs forem muito grandes e variados
            df = pd.read_csv(caminho, low_memory=False)
            lista_dfs.append(df)
            print(f"✔️  Lido: {os.path.basename(caminho)} ({len(df)} linhas)")

        print("🔗 Unificando tabelas e alinhando colunas...")
        # O concat do pandas cuida de alinhar colunas com nomes iguais automaticamente
        df_final = pd.concat(lista_dfs, ignore_index=True)

        # Salva o resultado com encoding seguro para Excel
        df_final.to_csv(caminho_saida, index=False, encoding='utf-8-sig')

        print("\n" + "="*40)
        print(f"✅ SUCESSO!")
        print(f"📊 Total de registros unificados: {len(df_final)}")
        print(f"💾 Arquivo salvo em: {caminho_saida}")
        print("="*40)

    except Exception as e:
        print(f"\n❌ Erro crítico no processamento: {e}")

if __name__ == "__main__":
    merge_csvs_melhorado()