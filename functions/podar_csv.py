import pandas as pd
import os

def podar_csv():
    # 1. Pede o nome do arquivo
    nome_arquivo = input("Digite o nome do arquivo CSV para podar (ex: data/dataset_filtrado.csv): ").strip()

    if not os.path.exists(nome_arquivo):
        print(f"❌ Erro: Arquivo '{nome_arquivo}' não encontrado.")
        return

    try:
        print(f"⏳ Lendo e podando colunas de {nome_arquivo}...")
        
        # Lendo com low_memory=False para evitar warnings
        df = pd.read_csv(nome_arquivo, low_memory=False)

        # 2. Mapeamento de colunas
        # Como seu CSV tem nomes variados (titulo/title, etc), vamos normalizar
        colunas_desejadas = {
            'titulo': 'titulo',
            'abstract_portuguese': 'abstract', # ou 'abstract' se já estiver assim
            'autores': 'autor',
            'ano': 'ano'
        }

        # Verificando quais colunas existem e renomeando para o padrão
        # Se 'abstract_portuguese' não existir, tenta 'abstract'
        if 'abstract_portuguese' not in df.columns and 'abstract' in df.columns:
            colunas_desejadas['abstract'] = 'abstract'
        else:
            colunas_desejadas['abstract_portuguese'] = 'abstract'

        # Filtrando apenas as que existem no seu arquivo atual
        existentes = [col for col in colunas_desejadas.keys() if col in df.columns]
        
        # Criando o novo DataFrame apenas com o que interessa
        df_podado = df[existentes].copy()
        
        # Renomeando para ficar bonitinho
        df_podado = df_podado.rename(columns=colunas_desejadas)

        # 3. Salvando o resultado
        nome_saida = nome_arquivo.replace(".csv", "_final.csv")
        df_podado.to_csv(nome_saida, index=False, encoding='utf-8-sig')

        print("-" * 30)
        print(f"✅ Poda concluída!")
        print(f"Columns mantidas: {list(df_podado.columns)}")
        print(f"Total de registros: {len(df_podado)}")
        print(f"💾 Arquivo limpo salvo em: {nome_saida}")
        print("-" * 30)

    except Exception as e:
        print(f"❌ Erro ao podar: {e}")

if __name__ == "__main__":
    podar_csv()