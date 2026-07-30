<h1 align="center">
 <img height="100px" src="assets/inf_logo.png" />
 <br />
 Scraper Acadêmico
</h1>
<div align="center">
 <img src="https://img.shields.io/github/license/RicardoRisson/Scrappers" />
 <img src="https://img.shields.io/github/repo-size/RicardoRisson/Scrappers" />
 <img src="https://img.shields.io/github/last-commit/RicardoRisson/Scrappers" />
 <img src="https://img.shields.io/github/stars/RicardoRisson/Scrappers" />
</div>

<div align="center">
 Interface gráfica para coletar metadados e resumos acadêmicos do <b>SciELO</b>, <b>arXiv</b> e <b>OpenAlex</b> — sem precisar mexer em código.
</div>

# Índice

* [⚠️ Antes de baixar o .exe](#️-antes-de-baixar-o-exe)
* [Download](#download)
* [Funcionalidades](#funcionalidades)
  * [Abas](#abas)
  * [Formato de saída (JSON e/ou CSV)](#formato-de-saída-json-eou-csv)
* [Suporte por plataforma](#suporte-por-plataforma)
* [Rodando a partir do código-fonte](#rodando-a-partir-do-código-fonte)
  * [Pré-requisitos](#pré-requisitos)
  * [Passos](#passos)
* [Gerando o .exe você mesmo](#gerando-o-exe-você-mesmo)
* [Solução de problemas](#solução-de-problemas)
* [Estrutura do projeto](#estrutura-do-projeto)
* [Screenshots](#screenshots)
* [Licença](#licença)

# ⚠️ Antes de baixar o .exe

> [!WARNING]
> ## 🚨 O .exe **NÃO FUNCIONA SOZINHO** — leia isto primeiro 🚨
>
> A aba **SciELO** usa um navegador de verdade (Chromium, via Playwright) para conseguir passar pela proteção anti-bot do site. O `.exe` **não** vem com esse navegador embutido.
>
> ### Rode isto no PowerShell ANTES de abrir o `.exe` (uma única vez, python deve estar instalado para usar "pip"):
>
> ```powershell
> pip install playwright
> playwright install
> ```
>
> **Se já rodou antes e o erro continuar aparecendo** (tipo `Executable doesn't exist at ...\_MEI...\playwright\...\chrome.exe`), rode de novo o comando acima — às vezes é preciso reinstalar depois de atualizar o `.exe`:
>
> ```powershell
> playwright install
> ```
>
> Sem isso, a aba SciELO trava/erra ao tentar iniciar. As abas **arXiv** e **OpenAlex** funcionam no `.exe` sem precisar de nada disso.
>
> Precisa de Python instalado só para rodar esses dois comandos (não precisa do resto do projeto). Baixe em [python.org](https://www.python.org/downloads/) se ainda não tiver.

# Download

<table align="center">
  <tr>
    <th>
      Windows (.exe)
    </th>
    <th>
      Linux / macOS
    </th>
  </tr>
  <tr>
    <td align="center">
      <a href="https://github.com/RicardoRisson/Scrappers/releases/latest">Última Release</a>
      <br />
      <sub>não esqueça o aviso do Chromium acima ⚠️</sub>
    </td>
    <td align="center">
      Sem build pronto ainda — rode a partir do <a href="#rodando-a-partir-do-código-fonte">código-fonte</a>
    </td>
  </tr>
</table>

> [!NOTE]
> O link acima aponta para a página de Releases do repositório. Se ainda não houver nenhuma publicada, veja [Gerando o .exe você mesmo](#gerando-o-exe-você-mesmo) para compilar a sua.

# Funcionalidades

* Uma única interface gráfica (Tkinter) reunindo três coletores diferentes
* Cada aba tem seus próprios campos, log e botões de Iniciar/Parar — nada de editar código
* Escolha de formato de saída em JSON, CSV, ou os dois ao mesmo tempo
* Botão para parar a coleta a qualquer momento, sem travar a interface
* Feito para lidar com datasets de médio/grande porte (+120k registros) com baixo consumo de RAM
* Mesclar Dados: Junte múltiplos arquivos CSV ou JSON/JSONL em um único arquivo, alinhando colunas automaticamente independentemente da ordem original.
* Conversor Direto: Converta arquivos JSON/JSONL brutos em planilhas CSV com interface dedicada.

## Abas

| Aba | Fonte | O que faz |
|---|---|---|
| **SciELO** | search.scielo.org | Busca por termo, pagina os resultados, resolve o cookie anti-bot automaticamente |
| **arXiv** | export.arxiv.org | Busca com a sintaxe da API do arXiv, filtra por português, evita duplicados |
| **OpenAlex** | api.openalex.org | Busca por termo e idioma, reconstrói o abstract a partir do índice invertido da API |

## Formato de saída (JSON e/ou CSV)

Cada aba tem duas caixinhas, **JSON** e **CSV**, marcáveis juntas:

- **Só JSON** → fica como o coletor gera nativamente, nada é convertido.
- **Só CSV** → converte para `.csv` e apaga o arquivo original.
- **Os dois marcados** → converte e mantém **ambos** os arquivos no PC.

# Suporte por plataforma

| | Windows | Linux | macOS |
|---|:---:|:---:|:---:|
| `.exe` pronto | ✓ | ✗ | ✗ |
| Rodar via código-fonte (`python gui.py`) | ✓ | ✓[^1] | ✓ |
| Aba SciELO (precisa do Chromium) | ✓ | ✓ | ✓ |

[^1]: No Linux, o Tkinter às vezes não vem junto com o Python — veja [Solução de problemas](#solução-de-problemas).

# Rodando a partir do código-fonte

## Pré-requisitos

* [Python 3.10+](https://www.python.org/downloads/)
* Google Chrome ou qualquer navegador Chromium instalado não é necessário — o Playwright baixa o próprio Chromium isolado

## Passos

```bash
git clone https://github.com/RicardoRisson/Scrappers.git
cd Scrappers
pip install -r requirements.txt
playwright install chromium
python gui.py
```

# Gerando o .exe você mesmo

Rode os passos abaixo **no Windows** (o PyInstaller empacota para o sistema em que está rodando):

```bash
pip install -r requirements.txt
pip install -r requirements-build.txt
playwright install chromium
pyinstaller gui.spec
```

O executável aparece em `dist/ColetorDeDadosAcademicos.exe`, já com o ícone do INF/UFRGS embutido. Depois é só criar uma [Release no GitHub](https://github.com/RicardoRisson/Scrappers/releases/new) e anexar esse arquivo — o link da seção [Download](#download) já aponta pra lá.

> [!WARNING]
> Lembre-se: o `.exe` gerado **ainda depende do Chromium do Playwright** instalado na máquina de quem for usar. O PyInstaller empacota o código Python, não o navegador. Repasse o aviso do topo deste README junto com o `.exe`.

# Solução de problemas

### A aba SciELO trava, dá erro, ou não abre nenhum navegador
* Você (ou quem for rodar o `.exe`) esqueceu de instalar o Chromium do Playwright — veja o [aviso no topo](#️-antes-de-baixar-o-exe).

### `python gui.py` reclama que não encontra o módulo `tkinter`
* No Linux, instale com o gerenciador de pacotes da sua distro, ex.: `sudo apt install python3-tk` no Debian/Ubuntu. No Windows e macOS o Tkinter já vem com o Python.

### A busca do SciELO retorna vazio ou dá erro 403 direto
* O site pode ter mudado a proteção anti-bot; tente novamente com "headless" desmarcado pra ver visualmente o que está acontecendo.

# Estrutura do projeto

```
Scrappers/
├── gui.py                  ← interface gráfica (execute este arquivo)
├── gui.spec                ← usado pelo PyInstaller para gerar o .exe
├── requirements.txt        ← dependências para rodar o app
├── requirements-build.txt  ← dependência extra só para gerar o .exe
├── assets/
│   ├── inf_logo.png
│   ├── inf_logo_small.png
│   └── inf_logo.ico
├── docs/
│   └── screenshots/
└── scrapers/
    ├── scielo_scraper.py
    ├── arxiv_scraper.py
    ├── openalex_scraper.py
    └── format_utils.py     ← conversão entre JSON e CSV
```

# Screenshots

<p align="center">
  <img width="90%" src="docs/screenshots/a1.png" />
  <br /><sub>Aba SciELO</sub>
</p>
<p align="center">
  <img width="90%" src="docs/screenshots/a2.png" />
  <br /><sub>Aba arXiv</sub>
</p>
<p align="center">
  <img width="90%" src="docs/screenshots/a3.png" />
  <br /><sub>Aba OpenAlex</sub>
</p>
<p align="center">
  <img width="90%" src="docs/screenshots/a4.png" />
  <br /><sub>Mesclar Dados</sub>
</p>
<p align="center">
  <img width="90%" src="docs/screenshots/a5.png" />
  <br /><sub>Aba Converter para CSV</sub>
</p>
# Licença

Este projeto é distribuído sob a licença **GPL-3.0**. Veja o arquivo `LICENSE` no repositório para o texto completo
