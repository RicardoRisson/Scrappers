# Academic Data Scraper

Este repositório contém ferramentas de automação para coleta de dados acadêmicos das plataformas **OpenAlex** e **arXiv**. O objetivo é extrair metadados e resumos (abstracts) de publicações científicas para análises bibliométricas e processamento de linguagem natural (NLP).

## 📂 Estrutura do Projeto

O projeto segue uma organização modular para garantir a integridade dos dados e a persistência de logs:

```text
.
├── data/           # Datasets gerados em formato .jsonl
├── log/            # Arquivos de log e monitoramento
├── scielo/         # Scripts de extração (ponto de execução)
│   ├── openalex_scraper.py
│   └── arxiv_scraper.py
└── requirements.txt