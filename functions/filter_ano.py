import pandas as pd
import os

def filtrar_por_ano():
    # 1. Pede o nome do arquivo ao usuário
    nome_arquivo = input("Digite o nome do arquivo CSV (ex: data/scielo_data.csv): ").strip()

    # Verifica se o arquivo existe para não dar erro
    if not os.path.exists(nome_arquivo):
        print(f"❌ Erro: O arquivo '{nome_arquivo}' não foi encontrado.")
        return

    try:
        print(f"⏳ Carregando {nome_arquivo}...")
        # Lendo o CSV (ajuste o 'sep' se o seu arquivo usar ';' em vez de ',')
        df = pd.read_csv(nome_arquivo)

        # Identificando a coluna de ano (geralmente 'year' ou 'publication_year')
        coluna_ano = None
        for col in ['year', 'publication_year', 'data', 'ano']:
            if col in df.columns:
                coluna_ano = col
                break
        
        if not coluna_ano:
            print("❌ Erro: Não encontrei uma coluna de ano no CSV. Colunas disponíveis:", list(df.columns))
            return

        # Converter para numérico para garantir o filtro
        df[coluna_ano] = pd.to_numeric(df[coluna_ano], errors='coerce')

        # 2. Aplicando o Filtro: Mantém de 2018 para cima (2018, 2019, 2020...)
        # Remove os abaixo de 2018
        total_antes = len(df)
        df_filtrado = df[df[coluna_ano] >= 2018].copy()
        
        total_depois = len(df_filtrado)
        removidos = total_antes - total_depois

        # 3. Salva o novo arquivo
        nome_saida = nome_arquivo.replace(".csv", "_filtrado.csv")
        df_filtrado.to_csv(nome_saida, index=False, encoding='utf-8-sig')

        print("-" * 30)
        print(f"✅ Filtro concluído!")
        print(f"🗑️ Registros removidos (anteriores a 2018): {removidos}")
        print(f"📦 Registros mantidos (2018-2026): {total_depois}")
        print(f"💾 Arquivo salvo como: {nome_saida}")
        print("-" * 30)

    except Exception as e:
        print(f"💥 Ocorreu um erro ao processar: {e}")

if __name__ == "__main__":
    filtrar_por_ano()