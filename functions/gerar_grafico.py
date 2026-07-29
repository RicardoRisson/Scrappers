import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def plotar_distribuicao():
    # 1. Pede o arquivo ao usuário
    arquivo = input("Digite o nome do arquivo CSV final (ex: data/dataset_final.csv): ").strip()
    
    if not os.path.exists(arquivo):
        print(f"❌ Erro: Arquivo '{arquivo}' não encontrado.")
        return

    try:
        # Lendo o CSV podado
        print(f"⏳ Processando dados de {arquivo}...")
        df = pd.read_csv(arquivo, low_memory=False)
        
        # Coluna padrão após a poda
        coluna_ano = 'ano'
        
        if coluna_ano not in df.columns:
            print(f"❌ Erro: Coluna '{coluna_ano}' não encontrada. Certifique-se de rodar o script de poda antes.")
            return

        # Limpeza rápida: garante que ano seja número e remove vazios
        df[coluna_ano] = pd.to_numeric(df[coluna_ano], errors='coerce')
        df = df.dropna(subset=[coluna_ano])
        df[coluna_ano] = df[coluna_ano].astype(int)

        # 2. Configuração Visual do Seaborn
        plt.figure(figsize=(12, 7))
        sns.set_context("talk") # Melhora a leitura dos eixos
        sns.set_style("whitegrid")

        # 3. Criação do gráfico
        # Ordenamos os anos para garantir a linha do tempo correta
        anos_ordenados = sorted(df[coluna_ano].unique())
        
        ax = sns.countplot(
            data=df, 
            x=coluna_ano, 
            order=anos_ordenados,
            palette="viridis" 
        )

        # Adiciona os totais exatos no topo das barras
        for p in ax.patches:
            ax.annotate(f'{int(p.get_height())}', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        xytext=(0, 10), 
                        textcoords='offset points',
                        fontsize=11, 
                        fontweight='bold')

        # 4. Títulos e Finalização
        plt.title('Distribuição de Produção Científica por Ano', fontsize=18, pad=20)
        plt.xlabel('Ano de Publicação', fontsize=14)
        plt.ylabel('Total de Artigos', fontsize=14)
        
        plt.tight_layout()

        # Salva a imagem
        nome_img = arquivo.replace(".csv", "_grafico.png")
        plt.savefig(nome_img, dpi=300)
        print(f"✅ Sucesso! Gráfico salvo em: {nome_img}")
        
        # Abre a janela para visualização
        plt.show()

    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    plotar_distribuicao()