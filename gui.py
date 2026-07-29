"""
Interface Gráfica do Coletor de Dados Acadêmicos
==================================================
Uma única janela (Tkinter) com uma aba para cada coletor:
SciELO, arXiv e OpenAlex. Basta preencher os campos e clicar em Iniciar —
sem precisar editar os scripts.

Para executar:
    python gui.py
"""

import asyncio
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from scrapers.scielo_scraper import run_scielo_scraper
from scrapers.arxiv_scraper import run_arxiv_scraper
from scrapers.openalex_scraper import run_openalex_scraper
from scrapers.format_utils import apply_format_choice


if getattr(sys, "frozen", False):
    # Rodando como .exe empacotado pelo PyInstaller: os assets ficam numa
    # pasta temporária (sys._MEIPASS), mas os dados gerados devem ficar ao
    # lado do executável, não dentro dessa pasta temporária.
    _ASSETS_BASE_DIR = sys._MEIPASS
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _ASSETS_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _APP_DIR = _ASSETS_BASE_DIR

DATA_DIR = os.path.join(_APP_DIR, "data")
ASSETS_DIR = os.path.join(_ASSETS_BASE_DIR, "assets")
LOGO_ICO = os.path.join(ASSETS_DIR, "inf_logo.ico")
LOGO_PNG_SMALL = os.path.join(ASSETS_DIR, "inf_logo_small.png")
os.makedirs(DATA_DIR, exist_ok=True)


class ScraperTab(ttk.Frame):
    """Classe base de uma aba: campos configuráveis, botões Iniciar/Parar
    e o console de log — compartilhados pelos três coletores."""

    def __init__(self, parent, note: str = ""):
        super().__init__(parent, padding=12)
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self._row = 0

        self.fields_frame = ttk.Frame(self)
        self.fields_frame.pack(fill="x", pady=(0, 8))
        self.fields_frame.columnconfigure(1, weight=1)

        if note:
            ttk.Label(self, text=note, foreground="#666666", wraplength=560, justify="left").pack(
                fill="x", pady=(0, 8)
            )

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", pady=(0, 8))
        self.start_button = ttk.Button(button_row, text="Iniciar", command=self.on_start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(button_row, text="Parar", command=self.on_stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        self.status_label = ttk.Label(button_row, text="Ocioso")
        self.status_label.pack(side="left", padx=(16, 0))

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=14, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.after(150, self._poll_log_queue)

    # --- construtores de campo (deixam as abas concisas e consistentes) --

    def add_entry(self, label: str, default: str = "", width: int = None) -> tk.StringVar:
        var = tk.StringVar(value=default)
        ttk.Label(self.fields_frame, text=label).grid(row=self._row, column=0, sticky="w", pady=4)
        ttk.Entry(self.fields_frame, textvariable=var, width=width).grid(
            row=self._row, column=1, sticky="w" if width else "ew", pady=4
        )
        self._row += 1
        return var

    def add_spinbox(self, label: str, default, from_: float, to: float, increment: float = 1) -> tk.Variable:
        var = tk.DoubleVar(value=default) if isinstance(default, float) else tk.IntVar(value=default)
        ttk.Label(self.fields_frame, text=label).grid(row=self._row, column=0, sticky="w", pady=4)
        ttk.Spinbox(self.fields_frame, from_=from_, to=to, increment=increment, textvariable=var, width=10).grid(
            row=self._row, column=1, sticky="w", pady=4
        )
        self._row += 1
        return var

    def add_checkbox(self, label: str, default: bool = False) -> tk.BooleanVar:
        var = tk.BooleanVar(value=default)
        ttk.Checkbutton(self.fields_frame, text=label, variable=var).grid(
            row=self._row, column=0, columnspan=2, sticky="w", pady=4
        )
        self._row += 1
        return var

    def add_output_path(self, label: str, filetypes, default_name: str) -> tk.StringVar:
        var = tk.StringVar(value=os.path.join(DATA_DIR, default_name))
        ttk.Label(self.fields_frame, text=label).grid(row=self._row, column=0, sticky="w", pady=4)
        out_row = ttk.Frame(self.fields_frame)
        out_row.grid(row=self._row, column=1, sticky="ew", pady=4)
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=var).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            out_row, text="Procurar...",
            command=lambda: self._browse_output_path(var, filetypes, default_name)
        ).grid(row=0, column=1, padx=(6, 0))
        self._row += 1
        return var

    def add_format_options(self, default_json: bool, default_csv: bool):
        """Caixinhas de múltipla escolha para o formato do arquivo final."""
        ttk.Label(self.fields_frame, text="Formato de saída:").grid(row=self._row, column=0, sticky="w", pady=4)
        row_frame = ttk.Frame(self.fields_frame)
        row_frame.grid(row=self._row, column=1, sticky="w", pady=4)
        json_var = tk.BooleanVar(value=default_json)
        csv_var = tk.BooleanVar(value=default_csv)
        ttk.Checkbutton(row_frame, text="JSON", variable=json_var).pack(side="left")
        ttk.Checkbutton(row_frame, text="CSV", variable=csv_var).pack(side="left", padx=(16, 0))
        self._row += 1
        self.add_hint("Marque os dois para manter ambos os arquivos; marque só um para converter e apagar o outro.")
        return json_var, csv_var

    def add_hint(self, text: str):
        ttk.Label(self.fields_frame, text=text, foreground="#666666").grid(
            row=self._row, column=0, columnspan=2, sticky="w"
        )
        self._row += 1

    # --- infraestrutura compartilhada ------------------------------------

    def log(self, message: str):
        """Thread-safe: chamado pela thread de trabalho, só enfileira o texto."""
        self.log_queue.put(str(message))

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)

    def _browse_output_path(self, var, filetypes, default_name):
        path = filedialog.asksaveasfilename(
            initialdir=DATA_DIR,
            initialfile=default_name,
            defaultextension=os.path.splitext(default_name)[1],
            filetypes=filetypes,
        )
        if path:
            var.set(path)

    def set_running_state(self, running: bool):
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.status_label.configure(text="Executando..." if running else "Ocioso")

    def on_stop(self):
        self.stop_event.set()
        self.log("[Parada solicitada] Aguardando o passo atual terminar...")

    def run_in_thread(self, target):
        self.stop_event.clear()
        self.set_running_state(True)

        def wrapper():
            try:
                target()
            except Exception as e:
                self.log(f"[Erro fatal] {e}")

        self.worker_thread = threading.Thread(target=wrapper, daemon=True)
        self.worker_thread.start()
        self._watch_done()

    def _watch_done(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.after(300, self._watch_done)
        else:
            self.set_running_state(False)

    def require(self, value, message: str) -> bool:
        if not value:
            messagebox.showerror("Informação faltando", message)
            return False
        return True

    def finalize_format(self, output_path, native_format, json_var, csv_var):
        """Chamado ao final da coleta para aplicar a escolha JSON/CSV."""
        kept = apply_format_choice(
            native_path=output_path,
            native_format=native_format,
            want_json=json_var.get(),
            want_csv=csv_var.get(),
            log=self.log,
        )
        if kept:
            self.log(f"[Formato] Arquivo(s) final(is): {', '.join(kept)}")

    def on_start(self):
        raise NotImplementedError


class SciELOTab(ScraperTab):
    NATIVE_FORMAT = "jsonl"

    def __init__(self, parent):
        super().__init__(
            parent,
            note="Uma janela do Chrome pode abrir brevemente para obter um cookie de segurança, a menos que 'headless' esteja marcado.",
        )

        self.query_var = self.add_entry("Termo de busca:", "educação")
        self.max_pages_var = self.add_spinbox("Máximo de páginas (20 resultados/página):", 10, 1, 500)
        self.headless_var = self.add_checkbox("Executar navegador em segundo plano (headless)")
        self.output_var = self.add_output_path("Arquivo de saída:", [("JSON Lines", "*.jsonl")], "scielo_dataset.jsonl")
        self.json_var, self.csv_var = self.add_format_options(default_json=True, default_csv=False)

    def on_start(self):
        query = self.query_var.get().strip()
        output_path = self.output_var.get().strip()
        if not self.require(query, "Informe um termo de busca."):
            return
        if not self.require(output_path, "Escolha um arquivo de saída."):
            return
        if not self.require(self.json_var.get() or self.csv_var.get(), "Selecione ao menos um formato de saída (JSON e/ou CSV)."):
            return

        def target():
            asyncio.run(run_scielo_scraper(
                query=query,
                max_pages=self.max_pages_var.get(),
                output_path=output_path,
                headless=self.headless_var.get(),
                log=self.log,
                stop_event=self.stop_event,
            ))
            self.finalize_format(output_path, self.NATIVE_FORMAT, self.json_var, self.csv_var)

        self.run_in_thread(target)


class ArxivTab(ScraperTab):
    NATIVE_FORMAT = "csv"

    def __init__(self, parent):
        super().__init__(parent)

        self.query_var = self.add_entry("Consulta arXiv:", "cat:educação*")
        self.add_hint("ex.: cat:educação*  ou  all:educação  (sintaxe de busca da API do arXiv)")
        self.batch_size_var = self.add_spinbox("Resultados por requisição:", 50, 1, 200)
        self.min_pause_var = self.add_spinbox("Pausa mínima entre requisições (segundos):", 6.0, 1, 60, increment=0.5)
        self.max_start_var = self.add_spinbox("Índice máximo (limite de segurança):", 20000, 100, 200000, increment=100)
        self.pt_only_var = self.add_checkbox("Manter apenas sentenças detectadas em português", default=True)
        self.output_var = self.add_output_path("Arquivo de saída:", [("CSV", "*.csv")], "arxiv_dataset.csv")
        self.json_var, self.csv_var = self.add_format_options(default_json=False, default_csv=True)

    def on_start(self):
        query = self.query_var.get().strip()
        output_path = self.output_var.get().strip()
        if not self.require(query, "Informe a consulta do arXiv."):
            return
        if not self.require(output_path, "Escolha um arquivo de saída."):
            return
        if not self.require(self.json_var.get() or self.csv_var.get(), "Selecione ao menos um formato de saída (JSON e/ou CSV)."):
            return

        def target():
            run_arxiv_scraper(
                search_query=query,
                output_path=output_path,
                batch_size=self.batch_size_var.get(),
                min_pause=self.min_pause_var.get(),
                max_start_index=self.max_start_var.get(),
                portuguese_only=self.pt_only_var.get(),
                log=self.log,
                stop_event=self.stop_event,
            )
            self.finalize_format(output_path, self.NATIVE_FORMAT, self.json_var, self.csv_var)

        self.run_in_thread(target)


class OpenAlexTab(ScraperTab):
    NATIVE_FORMAT = "jsonl"

    def __init__(self, parent):
        super().__init__(parent)

        self.query_var = self.add_entry("Termo de busca:", "educação")
        self.email_var = self.add_entry("E-mail de contato (exigido pela OpenAlex):", "")
        self.language_var = self.add_entry("Código do idioma:", "pt", width=10)
        self.output_var = self.add_output_path("Arquivo de saída:", [("JSON Lines", "*.jsonl")], "openalex_dataset.jsonl")
        self.json_var, self.csv_var = self.add_format_options(default_json=True, default_csv=False)

    def on_start(self):
        query = self.query_var.get().strip()
        email = self.email_var.get().strip()
        output_path = self.output_var.get().strip()
        if not self.require(query, "Informe um termo de busca."):
            return
        if not self.require(email, "Informe um e-mail de contato (exigido pela OpenAlex)."):
            return
        if not self.require(output_path, "Escolha um arquivo de saída."):
            return
        if not self.require(self.json_var.get() or self.csv_var.get(), "Selecione ao menos um formato de saída (JSON e/ou CSV)."):
            return

        def target():
            run_openalex_scraper(
                query_term=query,
                email_contact=email,
                output_path=output_path,
                language=self.language_var.get().strip() or "pt",
                log=self.log,
                stop_event=self.stop_event,
            )
            self.finalize_format(output_path, self.NATIVE_FORMAT, self.json_var, self.csv_var)

        self.run_in_thread(target)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coletor de Dados Acadêmicos")
        self.geometry("680x580")
        self.minsize(580, 480)
        self._set_window_icon()
        self._build_header()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        notebook.add(SciELOTab(notebook), text="SciELO")
        notebook.add(ArxivTab(notebook), text="arXiv")
        notebook.add(OpenAlexTab(notebook), text="OpenAlex")

    def _set_window_icon(self):
        # .ico funciona no título/taskbar do Windows; em outros sistemas o
        # Tk ignora silenciosamente se o formato não for suportado.
        try:
            self.iconbitmap(LOGO_ICO)
        except Exception:
            pass

    def _build_header(self):
        header = ttk.Frame(self, padding=(10, 10, 10, 0))
        header.pack(fill="x")

        ttk.Label(header, text="Coletor de Dados Acadêmicos", font=("Segoe UI", 13, "bold")).pack(side="left")

        try:
            self._logo_image = tk.PhotoImage(file=LOGO_PNG_SMALL)
            ttk.Label(header, image=self._logo_image).pack(side="right")
        except Exception:
            pass


if __name__ == "__main__":
    App().mainloop()
