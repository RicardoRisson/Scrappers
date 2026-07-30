"""
Interface Gráfica do Coletor e Manipulador de Dados Acadêmicos
==============================================================
Contém as abas para coletar dados (SciELO, arXiv, OpenAlex) e as
novas abas para Manipular Dados (Mesclar e Converter).
"""

import asyncio
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Importações dos Scrapers (certifique-se de que a pasta scrapers existe)
from scrapers.scielo_scraper import run_scielo_scraper
from scrapers.arxiv_scraper import run_arxiv_scraper
from scrapers.openalex_scraper import run_openalex_scraper
from scrapers.format_utils import apply_format_choice

# Importações das novas Funções de Manipulação (da pasta functions)
from functions.data_utils import merge_csv_files, merge_jsonl_files, convert_jsonl_to_csv


# =====================================================================
# Configuração de Diretórios
# =====================================================================
if getattr(sys, "frozen", False):
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


# =====================================================================
# Classe Base para TODAS as abas (compartilha Log e Layout padrão)
# =====================================================================
class BaseTab(ttk.Frame):
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

        log_frame = ttk.LabelFrame(self, text="Console de Ações")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=12, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.after(150, self._poll_log_queue)

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
        ttk.Label(self.fields_frame, text="Formato de saída:").grid(row=self._row, column=0, sticky="w", pady=4)
        row_frame = ttk.Frame(self.fields_frame)
        row_frame.grid(row=self._row, column=1, sticky="w", pady=4)
        json_var = tk.BooleanVar(value=default_json)
        csv_var = tk.BooleanVar(value=default_csv)
        ttk.Checkbutton(row_frame, text="JSON", variable=json_var).pack(side="left")
        ttk.Checkbutton(row_frame, text="CSV", variable=csv_var).pack(side="left", padx=(16, 0))
        self._row += 1
        return json_var, csv_var

    def add_hint(self, text: str):
        ttk.Label(self.fields_frame, text=text, foreground="#666666").grid(
            row=self._row, column=0, columnspan=2, sticky="w"
        )
        self._row += 1

    def log(self, message: str):
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
                self.log(f"[Erro] {e}")
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
        kept = apply_format_choice(
            native_path=output_path, native_format=native_format,
            want_json=json_var.get(), want_csv=csv_var.get(), log=self.log
        )
        if kept:
            self.log(f"[Formato] Arquivos finais: {', '.join(kept)}")

    def on_start(self):
        raise NotImplementedError


# =====================================================================
# Abas de Scrapers (Coleta de Dados)
# =====================================================================
class SciELOTab(BaseTab):
    NATIVE_FORMAT = "jsonl"
    def __init__(self, parent):
        super().__init__(parent, note="Pode abrir brevemente uma janela do Chrome, a menos que 'headless' esteja marcado.")
        self.query_var = self.add_entry("Termo de busca:", "educação")
        self.max_pages_var = self.add_spinbox("Máximo de páginas:", 10, 1, 500)
        self.headless_var = self.add_checkbox("Executar navegador invisível (headless)")
        self.output_var = self.add_output_path("Arquivo de saída:", [("JSON Lines", "*.jsonl")], "scielo_dataset.jsonl")
        self.json_var, self.csv_var = self.add_format_options(default_json=True, default_csv=False)

    def on_start(self):
        query = self.query_var.get().strip()
        out = self.output_var.get().strip()
        if not self.require(query, "Informe um termo de busca.") or not self.require(out, "Escolha um arquivo."): return
        def target():
            asyncio.run(run_scielo_scraper(
                query=query, max_pages=self.max_pages_var.get(), output_path=out,
                headless=self.headless_var.get(), log=self.log, stop_event=self.stop_event
            ))
            self.finalize_format(out, self.NATIVE_FORMAT, self.json_var, self.csv_var)
        self.run_in_thread(target)


class ArxivTab(BaseTab):
    NATIVE_FORMAT = "csv"
    def __init__(self, parent):
        super().__init__(parent)
        self.query_var = self.add_entry("Consulta arXiv:", "all:education")
        self.add_hint("Ex.: all:education ou ti:\"machine learning\"")
        self.batch_size_var = self.add_spinbox("Resultados por req.:", 50, 1, 200)
        self.min_pause_var = self.add_spinbox("Pausa mínima (s):", 6.0, 1, 60, 0.5)
        self.max_start_var = self.add_spinbox("Índice máx (limite):", 20000, 100, 200000, 100)
        self.pt_only_var = self.add_checkbox("Manter apenas textos detectados em português", default=False)
        self.output_var = self.add_output_path("Arquivo de saída:", [("CSV", "*.csv")], "arxiv_dataset.csv")
        self.json_var, self.csv_var = self.add_format_options(default_json=False, default_csv=True)

    def on_start(self):
        query = self.query_var.get().strip()
        out = self.output_var.get().strip()
        if not self.require(query, "Informe a consulta.") or not self.require(out, "Escolha um arquivo."): return
        def target():
            run_arxiv_scraper(
                search_query=query, output_path=out, batch_size=self.batch_size_var.get(),
                min_pause=self.min_pause_var.get(), max_start_index=self.max_start_var.get(),
                portuguese_only=self.pt_only_var.get(), log=self.log, stop_event=self.stop_event
            )
            self.finalize_format(out, self.NATIVE_FORMAT, self.json_var, self.csv_var)
        self.run_in_thread(target)


class OpenAlexTab(BaseTab):
    NATIVE_FORMAT = "jsonl"
    def __init__(self, parent):
        super().__init__(parent)
        self.query_var = self.add_entry("Termo de busca:", "educação")
        self.email_var = self.add_entry("E-mail de contato (exigido):", "")
        self.language_var = self.add_entry("Código do idioma:", "pt", width=10)
        self.output_var = self.add_output_path("Arquivo de saída:", [("JSON Lines", "*.jsonl")], "openalex_dataset.jsonl")
        self.json_var, self.csv_var = self.add_format_options(default_json=True, default_csv=False)

    def on_start(self):
        query = self.query_var.get().strip()
        email = self.email_var.get().strip()
        out = self.output_var.get().strip()
        if not self.require(query, "Informe um termo de busca.") or not self.require(email, "Informe um e-mail."): return
        def target():
            run_openalex_scraper(
                query_term=query, email_contact=email, output_path=out,
                language=self.language_var.get().strip() or "pt", log=self.log, stop_event=self.stop_event
            )
            self.finalize_format(out, self.NATIVE_FORMAT, self.json_var, self.csv_var)
        self.run_in_thread(target)


# =====================================================================
# Novas Abas: Mesclar (Juntar) e Converter Dados
# =====================================================================
class MergeTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, note="Selecione o formato e mova os arquivos para a lista da direita, definindo a ordem em que serão mesclados um abaixo do outro.")
        self.stop_button.pack_forget() # Esconde o botão Parar (não necessário aqui)
        
        # Tipo de Arquivo
        format_frame = ttk.Frame(self.fields_frame)
        format_frame.grid(row=self._row, column=0, columnspan=2, sticky="w", pady=4)
        self._row += 1
        
        ttk.Label(format_frame, text="O que deseja juntar?").pack(side="left")
        self.format_var = tk.StringVar(value=".csv")
        ttk.Radiobutton(format_frame, text="Arquivos CSV", variable=self.format_var, value=".csv", command=self.on_format_change).pack(side="left", padx=(10,5))
        ttk.Radiobutton(format_frame, text="Arquivos JSON/JSONL", variable=self.format_var, value=".jsonl", command=self.on_format_change).pack(side="left")

        # --- NOVO BOTÃO DE REFRESH AQUI ---
        ttk.Button(format_frame, text="🔄 Atualizar Lista", command=self.refresh_lists).pack(side="left", padx=(15, 0))

        # Seleção Visual com preservação de Ordem
        lists_frame = ttk.Frame(self.fields_frame)
        lists_frame.grid(row=self._row, column=0, columnspan=2, sticky="ew", pady=10)
        self._row += 1

        # Caixa: Arquivos Disponíveis
        avail_frame = ttk.LabelFrame(lists_frame, text="Arquivos na pasta 'data'")
        avail_frame.pack(side="left", fill="both", expand=True)
        self.list_avail = tk.Listbox(avail_frame, height=7, selectmode=tk.EXTENDED)
        self.list_avail.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Botões de mover
        btn_frame = ttk.Frame(lists_frame)
        btn_frame.pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Adicionar  ▶", command=self.add_files).pack(pady=(20,5))
        ttk.Button(btn_frame, text="◀  Remover", command=self.remove_files).pack(pady=5)

        # Caixa: Arquivos Selecionados (Ordem exata)
        sel_frame = ttk.LabelFrame(lists_frame, text="Arquivos Selecionados (Ordem de mesclagem)")
        sel_frame.pack(side="left", fill="both", expand=True)
        self.list_sel = tk.Listbox(sel_frame, height=7, selectmode=tk.EXTENDED)
        self.list_sel.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Saída
        self.output_var = self.add_output_path("Salvar arquivo final como:", [("Todos", "*.*")], "dados_mesclados.csv")
        
        self.refresh_lists()
        self.start_button.configure(text="Juntar Arquivos")

    def on_format_change(self):
        """Ao mudar entre CSV e JSON, limpa também os selecionados e atualiza."""
        self.list_sel.delete(0, tk.END)
        self.refresh_lists()

    def refresh_lists(self):
        """Atualiza a lista da esquerda lendo os arquivos atualizados da pasta 'data'."""
        # Mantém na memória os arquivos que você já jogou para a direita
        already_selected = set(self.list_sel.get(0, tk.END))
        
        self.list_avail.delete(0, tk.END)
        ext = self.format_var.get()
        
        if os.path.exists(DATA_DIR):
            for f in sorted(os.listdir(DATA_DIR)):
                # Ignora se o arquivo já estiver na lista da direita (selecionados)
                if f in already_selected:
                    continue
                
                if ext == ".jsonl" and (f.endswith(".json") or f.endswith(".jsonl")):
                    self.list_avail.insert(tk.END, f)
                elif ext == ".csv" and f.endswith(".csv"):
                    self.list_avail.insert(tk.END, f)
                    
        # Atualiza a extensão sugerida no caminho do arquivo de saída
        current_out = self.output_var.get()
        base_name, _ = os.path.splitext(current_out)
        self.output_var.set(base_name + ext)

    def add_files(self):
        """Move o que foi selecionado para a caixa da direita (guarda a ordem)."""
        selected_indices = self.list_avail.curselection()
        for i in selected_indices:
            self.list_sel.insert(tk.END, self.list_avail.get(i))
        # Remove de trás para frente para não bagunçar os índices
        for i in reversed(selected_indices):
            self.list_avail.delete(i)

    def remove_files(self):
        """Devolve para a caixa da esquerda."""
        selected_indices = self.list_sel.curselection()
        for i in selected_indices:
            self.list_avail.insert(tk.END, self.list_sel.get(i))
        for i in reversed(selected_indices):
            self.list_sel.delete(i)

    def on_start(self):
        files_to_merge = list(self.list_sel.get(0, tk.END))
        if len(files_to_merge) < 2:
            self.require(False, "Selecione pelo menos 2 arquivos na lista da direita para juntar.")
            return

        out_path = self.output_var.get().strip()
        if not self.require(out_path, "Escolha onde salvar o arquivo final."): return

        # Caminhos absolutos baseados na pasta DATA_DIR
        abs_files = [os.path.join(DATA_DIR, f) for f in files_to_merge]
        ext = self.format_var.get()

        def target():
            try:
                if ext == ".csv":
                    merge_csv_files(abs_files, out_path, self.log)
                else:
                    merge_jsonl_files(abs_files, out_path, self.log)
            except Exception as e:
                self.log(f"Erro ao juntar arquivos: {e}")

        self.run_in_thread(target)


class ConvertTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, note="Transforme rapidamente arquivos JSON ou JSONL brutos em planilhas CSV.")
        self.stop_button.pack_forget()

        # Selecionar Arquivo
        ttk.Label(self.fields_frame, text="Arquivo JSON/JSONL para converter:").grid(row=self._row, column=0, sticky="w", pady=4)
        
        row_frame = ttk.Frame(self.fields_frame)
        row_frame.grid(row=self._row, column=1, sticky="ew", pady=4)
        row_frame.columnconfigure(0, weight=1)

        self.file_var = tk.StringVar()
        self.combo = ttk.Combobox(row_frame, textvariable=self.file_var, state="readonly")
        self.combo.grid(row=0, column=0, sticky="ew")

        ttk.Button(row_frame, text="Atualizar Lista", command=self.refresh_combo).grid(row=0, column=1, padx=(5,0))
        ttk.Button(row_frame, text="Procurar...", command=self.browse_input).grid(row=0, column=2, padx=(5,0))
        self._row += 1

        # Saída
        self.output_var = self.add_output_path("Salvar como CSV:", [("CSV", "*.csv")], "arquivo_convertido.csv")
        
        self.refresh_combo()
        self.start_button.configure(text="Converter para CSV")

        # Atualizar nome de saída automaticamente
        self.file_var.trace_add('write', self._auto_update_output)

    def refresh_combo(self):
        if os.path.exists(DATA_DIR):
            files = [f for f in os.listdir(DATA_DIR) if f.endswith((".json", ".jsonl"))]
            self.combo['values'] = files
            if files:
                self.combo.set(files[0])

    def browse_input(self):
        path = filedialog.askopenfilename(initialdir=DATA_DIR, filetypes=[("JSON", "*.json *.jsonl"), ("Todos", "*.*")])
        if path:
            self.combo.set(path)

    def _auto_update_output(self, *args):
        in_val = self.file_var.get()
        if in_val:
            base_name = os.path.basename(in_val)
            name, _ = os.path.splitext(base_name)
            self.output_var.set(os.path.join(DATA_DIR, name + ".csv"))

    def on_start(self):
        in_file = self.file_var.get().strip()
        out_file = self.output_var.get().strip()

        if not self.require(in_file, "Selecione um arquivo de entrada para converter."): return
        if not self.require(out_file, "Defina onde salvar o CSV convertido."): return

        # Garante que seja um caminho absoluto
        if not os.path.isabs(in_file):
            in_file = os.path.join(DATA_DIR, in_file)

        def target():
            try:
                convert_jsonl_to_csv(in_file, out_file, self.log)
            except Exception as e:
                self.log(f"Erro na conversão: {e}")

        self.run_in_thread(target)


# =====================================================================
# Janela Principal do Tkinter
# =====================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coletor e Manipulador de Dados Acadêmicos")
        self.geometry("740x640")
        self.minsize(680, 580)
        self._set_window_icon()
        self._build_header()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Adiciona as abas (Coletores)
        notebook.add(SciELOTab(notebook), text="SciELO")
        notebook.add(ArxivTab(notebook), text="arXiv")
        notebook.add(OpenAlexTab(notebook), text="OpenAlex")
        
        # Adiciona as abas (Ferramentas de Dados)
        notebook.add(MergeTab(notebook), text="Mesclar Dados de CSV")
        notebook.add(ConvertTab(notebook), text="Converter para CSV")

    def _set_window_icon(self):
        try:
            self.iconbitmap(LOGO_ICO)
        except Exception:
            pass

    def _build_header(self):
        header = ttk.Frame(self, padding=(10, 10, 10, 0))
        header.pack(fill="x")
        ttk.Label(header, text="Coletor e Manipulador de Dados", font=("Segoe UI", 13, "bold")).pack(side="left")
        try:
            self._logo_image = tk.PhotoImage(file=LOGO_PNG_SMALL)
            ttk.Label(header, image=self._logo_image).pack(side="right")
        except Exception:
            pass


if __name__ == "__main__":
    App().mainloop()