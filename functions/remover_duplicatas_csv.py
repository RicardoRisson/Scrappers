import pandas as pd
import os

# Configuração para funcionar dentro de /functions
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def listar_csvs():
    """Busca arquivos .csv na raiz e na pasta /data"""
    extensoes = ('.csv')
    arquivos_encontrados = []
    pastas_para_buscar = [BASE_DIR, DATA_DIR]
    
    for pasta in pastas_para_buscar:
        if os.path.exists(pasta):
            for f in os.listdir(pasta):
                if f.endswith(extensoes) and "_limpo" not in f:
                    caminho = os.path.join(pasta, f)
                    if caminho not in arquivos_encontrados:
                        arquivos_encontrados.append(caminho)
    return arquivos_encontrados

def remover_duplicados():
    print("\n" + "="*40)
    print("      ✨ REMOVER DUPLICADOS (CSV)      ")
    print("="*40)

    # 1. Listar e selecionar o arquivo
    csvs = listar_csvs()
    if not csvs:
        print(f"❌ Nenhum arquivo CSV encontrado em {BASE_DIR} ou {DATA_DIR}.")
        return

    print("\nArquivos disponíveis:")
    for i, caminho in enumerate(csvs, 1):
        nome_exibicao = os.path.relpath(caminho, BASE_DIR)
        print(f"{i}. {nome_exibicao}")

    try:
        escolha = int(input("\nDigite o número do arquivo que deseja limpar: ")) - 1
        caminho_input = csvs[escolha]
    except (ValueError, IndexError):
        print("❌ Escolha inválida.")
        return

    # 2. Carregar o arquivo
    try:
        print(f"⏳ Carregando {os.path.basename(caminho_input)}...")
        df = pd.read_csv(caminho_input, low_memory=False)
        total_antes = len(df)

        # 3. Opção de filtro
        print("\nComo deseja remover as duplicatas?")
        print("1. Linha inteira exatamente igual (mais seguro)")
        print("2. Baseado apenas na coluna 'id'")
        print("3. Baseado apenas na coluna 'url'")
        
        opcao = input("Escolha (padrão 1): ").strip()

        if opcao == '2' and 'id' in df.columns:
            df_limpo = df.drop_duplicates(subset=['id'], keep='first')
        elif opcao == '3' and 'url' in df.columns:
            df_limpo = df.drop_duplicates(subset=['url'], keep='first')
        else:
            if opcao in ['2', '3']:
                print("⚠️ Coluna não encontrada. Usando modo 'Linha Inteira'.")
            df_limpo = df.drop_duplicates(keep='first')

        total_depois = len(df_limpo)
        duplicados_removidos = total_antes - total_depois

        # 4. Salvar resultado na pasta /data
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        nome_base = os.path.basename(caminho_input).replace(".csv", "")
        caminho_saida = os.path.join(DATA_DIR, f"{nome_base}_limpo.csv")

        df_limpo.to_csv(caminho_saida, index=False, encoding='utf-8-sig')

        print("\n" + "="*40)
        print(f"✅ LIMPEZA CONCLUÍDA!")
        print(f"📊 Linhas originais: {total_antes}")
        print(f"🗑️  Duplicados removidos: {duplicados_removidos}")
        print(f"💎 Linhas únicas restantes: {total_depois}")
        print(f"💾 Salvo em: {caminho_saida}")
        print("="*40)

    except Exception as e:
        print(f"❌ Erro ao processar: {e}")

if __name__ == "__main__":
    remover_duplicados()