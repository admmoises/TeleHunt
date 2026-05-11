import asyncio
import contextlib
import io
import queue
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

import TeleHunt as core


FILE_TYPES = [
    "",
    "Text",
    "Photo",
    "Poll",
    "Story",
    "Video",
    "Audio",
    "Voice",
    "GIF",
    "Sticker",
    "PDF",
    "SQL",
    "Python File",
    "Go File",
    "Php File",
    "DOCX",
    "ZIP",
    "RAR",
    "APK File",
    "Executable File",
    "Text File",
    "JSON File",
    "File",
]


class QueueWriter(io.TextIOBase):
    def __init__(self, event_queue):
        self.event_queue = event_queue

    def write(self, text):
        if text:
            self.event_queue.put({"type": "log", "text": text})
        return len(text)

    def flush(self):
        return None


class TeleHuntGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TeleHunt GUI")
        self.root.geometry("1200x800")
        self.event_queue = queue.Queue()
        self.current_task = None

        self._build_ui()
        self._poll_events()
        self.refresh_accounts()

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.accounts_tab = ttk.Frame(notebook)
        self.discovery_tab = ttk.Frame(notebook)
        self.search_tab = ttk.Frame(notebook)
        self.capture_tab = ttk.Frame(notebook)
        self.forward_tab = ttk.Frame(notebook)
        self.links_tab = ttk.Frame(notebook)
        self.logs_tab = ttk.Frame(notebook)

        notebook.add(self.accounts_tab, text="Contas")
        notebook.add(self.discovery_tab, text="Entidades")
        notebook.add(self.search_tab, text="Busca")
        notebook.add(self.capture_tab, text="Captura")
        notebook.add(self.forward_tab, text="Encaminhar Canal")
        notebook.add(self.links_tab, text="Link Finder")
        notebook.add(self.logs_tab, text="Logs")

        self._build_accounts_tab()
        self._build_discovery_tab()
        self._build_search_tab()
        self._build_capture_tab()
        self._build_forward_tab()
        self._build_links_tab()
        self._build_logs_tab()

    def _build_accounts_tab(self):
        form = ttk.LabelFrame(self.accounts_tab, text="Adicionar conta")
        form.pack(fill="x", padx=10, pady=10)

        self.api_hash_var = tk.StringVar()
        self.api_id_var = tk.StringVar()
        self.phone_var = tk.StringVar()

        self._labeled_entry(form, "API Hash", self.api_hash_var, 0)
        self._labeled_entry(form, "API ID", self.api_id_var, 1)
        self._labeled_entry(form, "Telefone (+5511...)", self.phone_var, 2)

        actions = ttk.Frame(form)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        ttk.Button(actions, text="Adicionar", command=self.on_add_account).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Atualizar lista", command=self.refresh_accounts).pack(side="left")

        table_frame = ttk.LabelFrame(self.accounts_tab, text="Contas cadastradas")
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("num", "nome", "username", "phone", "user_id", "session")
        self.accounts_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.accounts_tree.heading("num", text="N")
        self.accounts_tree.heading("nome", text="Nome")
        self.accounts_tree.heading("username", text="Username")
        self.accounts_tree.heading("phone", text="Telefone")
        self.accounts_tree.heading("user_id", text="User ID")
        self.accounts_tree.heading("session", text="Session")
        self.accounts_tree.column("num", width=50, anchor="center")
        self.accounts_tree.column("nome", width=220)
        self.accounts_tree.column("username", width=180)
        self.accounts_tree.column("phone", width=140)
        self.accounts_tree.column("user_id", width=120)
        self.accounts_tree.column("session", width=220)
        self.accounts_tree.pack(fill="both", expand=True)

    def _build_discovery_tab(self):
        box = ttk.LabelFrame(self.discovery_tab, text="Buscar grupos/canais/bots/DMs")
        box.pack(fill="x", padx=10, pady=10)
        self.discovery_acc_var = tk.StringVar(value="all")
        self.discovery_type_var = tk.StringVar(value="groups")

        self._labeled_entry(box, "Conta(s): 1,2 ou all", self.discovery_acc_var, 0)
        ttk.Label(box, text="Tipo").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        ttk.Combobox(
            box,
            textvariable=self.discovery_type_var,
            values=["groups", "channels", "bots", "dms"],
            state="readonly",
            width=20,
        ).grid(row=1, column=1, sticky="w", padx=8, pady=8)

        ttk.Button(box, text="Executar", command=self.on_discovery).grid(row=2, column=0, padx=8, pady=8, sticky="w")

    def _build_search_tab(self):
        box = ttk.LabelFrame(self.search_tab, text="Buscar mensagens e encaminhar")
        box.pack(fill="x", padx=10, pady=10)
        self.search_acc_var = tk.StringVar(value="all")
        self.search_text_var = tk.StringVar()
        self.search_sender_var = tk.StringVar()
        self.search_limit_var = tk.StringVar()
        self.search_forward_var = tk.StringVar()
        self.search_file_type_var = tk.StringVar(value="")

        self._labeled_entry(box, "Conta(s): 1,2 ou all", self.search_acc_var, 0)
        self._labeled_entry(box, "Texto", self.search_text_var, 1)
        self._labeled_entry(box, "Sender ID (opcional)", self.search_sender_var, 2)
        self._labeled_entry(box, "Limite (opcional)", self.search_limit_var, 3)
        self._labeled_entry(box, "Forward para @user ou ID (opcional)", self.search_forward_var, 4)
        ttk.Label(box, text="Filtro de arquivo").grid(row=5, column=0, sticky="w", padx=8, pady=8)
        ttk.Combobox(
            box, textvariable=self.search_file_type_var, values=FILE_TYPES, state="readonly", width=30
        ).grid(row=5, column=1, sticky="w", padx=8, pady=8)

        ttk.Button(box, text="Buscar", command=self.on_search).grid(row=6, column=0, padx=8, pady=8, sticky="w")

    def _build_capture_tab(self):
        box = ttk.LabelFrame(self.capture_tab, text="Capturar mensagens de alvo")
        box.pack(fill="x", padx=10, pady=10)
        self.capture_acc_var = tk.StringVar(value="all")
        self.capture_target_var = tk.StringVar()
        self.capture_forward_var = tk.StringVar()
        self.capture_limit_var = tk.StringVar()
        self.capture_file_type_var = tk.StringVar(value="")

        self._labeled_entry(box, "Conta(s): 1,2 ou all", self.capture_acc_var, 0)
        self._labeled_entry(box, "Target username sem @", self.capture_target_var, 1)
        self._labeled_entry(box, "Forward para @user ou ID (opcional)", self.capture_forward_var, 2)
        self._labeled_entry(box, "Limite (opcional)", self.capture_limit_var, 3)

        ttk.Label(box, text="Filtro de arquivo").grid(row=4, column=0, sticky="w", padx=8, pady=8)
        ttk.Combobox(
            box, textvariable=self.capture_file_type_var, values=FILE_TYPES, state="readonly", width=30
        ).grid(row=4, column=1, sticky="w", padx=8, pady=8)
        ttk.Button(box, text="Capturar", command=self.on_capture).grid(row=5, column=0, padx=8, pady=8, sticky="w")

    def _build_forward_tab(self):
        box = ttk.LabelFrame(self.forward_tab, text="Encaminhar mensagens de canal")
        box.pack(fill="x", padx=10, pady=10)
        self.forward_acc_var = tk.StringVar(value="all")
        self.forward_link_var = tk.StringVar()
        self.forward_target_var = tk.StringVar()
        self.forward_limit_var = tk.StringVar()
        self.forward_show_table_var = tk.BooleanVar(value=True)

        self._labeled_entry(box, "Conta(s): 1,2 ou all", self.forward_acc_var, 0)
        self._labeled_entry(box, "Link/@ do canal origem", self.forward_link_var, 1)
        self._labeled_entry(box, "Destino @user ou ID", self.forward_target_var, 2)
        self._labeled_entry(box, "Limite (vazio = all)", self.forward_limit_var, 3)
        ttk.Checkbutton(box, text="Mostrar tabela", variable=self.forward_show_table_var).grid(
            row=4, column=0, sticky="w", padx=8, pady=8
        )
        ttk.Button(box, text="Encaminhar", command=self.on_forward).grid(row=5, column=0, padx=8, pady=8, sticky="w")

    def _build_links_tab(self):
        box = ttk.LabelFrame(self.links_tab, text="Extrair links")
        box.pack(fill="x", padx=10, pady=10)
        self.links_acc_var = tk.StringVar(value="all")
        self._labeled_entry(box, "Conta(s): 1,2 ou all", self.links_acc_var, 0)
        ttk.Button(box, text="Buscar links", command=self.on_link_finder).grid(row=1, column=0, padx=8, pady=8, sticky="w")

    def _build_logs_tab(self):
        frame = ttk.Frame(self.logs_tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.logs_text = scrolledtext.ScrolledText(frame, wrap="word")
        self.logs_text.pack(fill="both", expand=True)
        ttk.Button(frame, text="Limpar logs", command=lambda: self.logs_text.delete("1.0", tk.END)).pack(anchor="w", pady=(8, 0))

    def _labeled_entry(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=8)
        ttk.Entry(parent, textvariable=var, width=50).grid(row=row, column=1, sticky="w", padx=8, pady=8)

    def _log(self, text):
        self.logs_text.insert(tk.END, text)
        self.logs_text.see(tk.END)

    def _poll_events(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                if event["type"] == "log":
                    self._log(event["text"])
                elif event["type"] == "prompt_text":
                    response = simpledialog.askstring(
                        "Entrada necessaria",
                        event["prompt"],
                        show="*" if event.get("secret") else None,
                        parent=self.root,
                    )
                    event["response_holder"]["value"] = response
                    event["done"].set()
                elif event["type"] == "prompt_yes_no":
                    answer = messagebox.askyesno("Confirmacao", event["prompt"], parent=self.root)
                    event["response_holder"]["value"] = answer
                    event["done"].set()
                elif event["type"] == "task_done":
                    self.current_task = None
                    self.refresh_accounts()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _request_text_from_ui(self, prompt, secret=False):
        done = threading.Event()
        holder = {"value": None}
        self.event_queue.put(
            {"type": "prompt_text", "prompt": prompt, "secret": secret, "done": done, "response_holder": holder}
        )
        done.wait()
        return holder["value"]

    def _request_yes_no_from_ui(self, prompt):
        done = threading.Event()
        holder = {"value": False}
        self.event_queue.put({"type": "prompt_yes_no", "prompt": prompt, "done": done, "response_holder": holder})
        done.wait()
        return holder["value"]

    def _parse_limit(self, raw_value):
        value = (raw_value or "").strip()
        if not value:
            return None
        return int(value)

    def _run_async_task(self, task_name, coro_factory):
        if self.current_task:
            messagebox.showwarning("Tarefa em andamento", "Aguarde a tarefa atual terminar.")
            return

        self.current_task = task_name
        self._log(f"\n=== Executando: {task_name} ===\n")

        def worker():
            writer = QueueWriter(self.event_queue)
            try:
                with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                    asyncio.run(coro_factory())
            except Exception:
                self.event_queue.put({"type": "log", "text": traceback.format_exc()})
            finally:
                self.event_queue.put({"type": "task_done"})

        threading.Thread(target=worker, daemon=True).start()

    def refresh_accounts(self):
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        accounts = core.load_accounts(core.FILES["accounts"])
        for acc in accounts:
            name = f"{acc.get('first_name', '')} {acc.get('last_name', '')}".strip()
            username = f"@{acc['username']}" if acc.get("username") else "N/A"
            self.accounts_tree.insert(
                "",
                tk.END,
                values=(
                    acc.get("account_number"),
                    name,
                    username,
                    acc.get("phone"),
                    acc.get("user_id"),
                    acc.get("session_file"),
                ),
            )

    def on_add_account(self):
        api_hash = self.api_hash_var.get().strip()
        api_id = self.api_id_var.get().strip()
        phone = self.phone_var.get().strip()
        if not api_hash or not api_id or not phone:
            messagebox.showerror("Erro", "Preencha API Hash, API ID e Telefone.")
            return

        def code_provider(prompt):
            return self._request_text_from_ui(prompt, secret=False)

        def password_provider(prompt):
            return self._request_text_from_ui(prompt, secret=True)

        self._run_async_task(
            "Adicionar conta",
            lambda: core.add_account(api_hash, api_id, phone, code_provider=code_provider, password_provider=password_provider),
        )

    def on_discovery(self):
        acc = self.discovery_acc_var.get().strip() or "all"
        entity_type = self.discovery_type_var.get().strip()
        self._run_async_task("Buscar entidades", lambda: core.fetchDGC(acc, entity_type))

    def on_search(self):
        try:
            limit = self._parse_limit(self.search_limit_var.get())
        except ValueError:
            messagebox.showerror("Erro", "Limite invalido.")
            return

        acc = self.search_acc_var.get().strip() or "all"
        search_text = self.search_text_var.get().strip() or None
        sender = self.search_sender_var.get().strip() or None
        forward = self.search_forward_var.get().strip() or None
        file_type = self.search_file_type_var.get().strip() or None

        self._run_async_task(
            "Buscar mensagens",
            lambda: core.search_messages(acc, search_text, sender, limit, forward, file_type),
        )

    def on_capture(self):
        try:
            limit = self._parse_limit(self.capture_limit_var.get())
        except ValueError:
            messagebox.showerror("Erro", "Limite invalido.")
            return

        acc = self.capture_acc_var.get().strip() or "all"
        target = self.capture_target_var.get().strip()
        if not target:
            messagebox.showerror("Erro", "Informe o target username.")
            return
        forward = self.capture_forward_var.get().strip() or None
        file_type = self.capture_file_type_var.get().strip() or None

        self._run_async_task(
            "Capturar mensagens",
            lambda: core.capture_main(acc, target, forward, limit, file_type),
        )

    def on_forward(self):
        acc = self.forward_acc_var.get().strip() or "all"
        link = self.forward_link_var.get().strip()
        target = self.forward_target_var.get().strip()
        if not link or not target:
            messagebox.showerror("Erro", "Informe origem e destino.")
            return

        limit_raw = self.forward_limit_var.get().strip()
        limit = limit_raw if limit_raw else "all"
        show_table = self.forward_show_table_var.get()

        def download_decision_provider(prompt):
            return self._request_yes_no_from_ui(prompt)

        self._run_async_task(
            "Encaminhar de canal",
            lambda: core.forward_from_channel(
                acc,
                link,
                target,
                limit=limit,
                show_table=show_table,
                download_decision_provider=download_decision_provider,
            ),
        )

    def on_link_finder(self):
        acc = self.links_acc_var.get().strip() or "all"
        self._run_async_task("Link finder", lambda: core.link_finder(acc))


def main():
    root = tk.Tk()
    TeleHuntGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
