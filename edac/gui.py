"""Fenetre principale de Expert Dev Autopilot Console (Tkinter, sans dependance)."""

from __future__ import annotations

import queue
import sys
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
import tkinter as tk

from .config import SECTIONS, SETTINGS_BY_KEY, Config, ConfigError, settings_in
from .logging_setup import list_log_files, read_tail, resolve_log_file, setup_logging
from .uninstall import collect_targets
from .runner import ACTIONS, CommandRunner, build_command, host_os

APP_TITLE = "Expert Dev Autopilot — Console"

PALETTES = {
    "clair": {
        "bg": "#f5f6f8", "fg": "#1b1c1e", "field": "#ffffff", "field_fg": "#1b1c1e",
        "accent": "#2563eb", "muted": "#6b7280", "log_bg": "#ffffff", "log_fg": "#1b1c1e",
        "tab": "#e4e6ea", "tab_active": "#ffffff",
    },
    "sombre": {
        "bg": "#1e1f22", "fg": "#e6e6e6", "field": "#2b2d31", "field_fg": "#f2f2f2",
        "accent": "#60a5fa", "muted": "#9aa0a6", "log_bg": "#141517", "log_fg": "#dcdcdc",
        "tab": "#2b2d31", "tab_active": "#3a3d43",
    },
}
LEVEL_COLORS = {
    "cmd": "#3b82f6",
    "ok": "#16a34a",
    "warn": "#d97706",
    "error": "#dc2626",
    "info": "#6b7280",
    "note": "#a855f7",
}


class ConsoleApp(ttk.Frame):
    def __init__(self, master: Tk, config: Config):
        super().__init__(master, padding=8)
        self.master_window = master
        self.config_obj = config
        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.runner = CommandRunner(config, self.queue)
        self.vars: dict[str, tk.Variable] = {}
        self.status = StringVar(value="pret")
        self.profile_var = StringVar(value=config.active_profile)

        master.title(APP_TITLE)
        master.geometry("1024x700")
        master.minsize(880, 560)
        master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.pack(fill="both", expand=True)

        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()
        self._apply_theme()
        self._bind_shortcuts()
        self.log("info", f"hote : {host_os()} · config : {self.config_obj.path}")
        self.after(80, self._drain_queue)

    # -- construction ------------------------------------------------------- #

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Projet :").pack(side="left")
        self.project_var = StringVar(value=self.config_obj.get("project.path"))
        ttk.Entry(bar, textvariable=self.project_var, width=58).pack(side="left", padx=6)
        ttk.Button(bar, text="Parcourir…", command=self.choose_project).pack(side="left")
        ttk.Label(bar, text="Profil :").pack(side="left", padx=(16, 4))
        self.profile_box = ttk.Combobox(
            bar, textvariable=self.profile_var, width=16, state="readonly",
            values=self.config_obj.profile_names(),
        )
        self.profile_box.pack(side="left")
        self.profile_box.bind("<<ComboboxSelected>>", self.on_profile_change)
        ttk.Button(bar, text="Enregistrer", command=self.save_config).pack(side="right")

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self._build_dashboard_tab()
        self._build_config_tab()
        self._build_log_tab()
        self._build_about_tab()

    def _build_dashboard_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Tableau de bord")

        actions = ttk.LabelFrame(tab, text="Actions", padding=10)
        actions.pack(fill="x")
        for index, (action, label) in enumerate(ACTIONS):
            ttk.Button(actions, text=label, width=24,
                       command=lambda a=action: self.run_action(a)).grid(
                row=index // 4, column=index % 4, padx=4, pady=4, sticky="ew")
        for column in range(4):
            actions.columnconfigure(column, weight=1)

        custom = ttk.LabelFrame(tab, text="Commande personnalisee", padding=10)
        custom.pack(fill="x", pady=8)
        self.custom_var = StringVar()
        entry = ttk.Entry(custom, textvariable=self.custom_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _event: self.run_custom())
        ttk.Button(custom, text="Executer", command=self.run_custom).pack(side="left", padx=6)
        self.stop_button = ttk.Button(custom, text="Stop", command=self.runner.stop, state="disabled")
        self.stop_button.pack(side="left")

        autopilot = ttk.LabelFrame(tab, text="Autopilot", padding=10)
        autopilot.pack(fill="x")
        self.autopilot_var = BooleanVar(value=self.config_obj.get("autopilot.enabled"))
        self.allow_all_var = BooleanVar(value=self.config_obj.get("autopilot.allow_all"))
        ttk.Checkbutton(autopilot, text="Autopilot actif", variable=self.autopilot_var,
                        command=lambda: self._quick_set("autopilot.enabled", self.autopilot_var)
                        ).pack(side="left", padx=6)
        ttk.Checkbutton(autopilot, text="Allow all (non destructif)", variable=self.allow_all_var,
                        command=lambda: self._quick_set("autopilot.allow_all", self.allow_all_var)
                        ).pack(side="left", padx=6)
        ttk.Button(autopilot, text="Chaine complete (setup → build → package)",
                   command=self.run_pipeline).pack(side="right")

    def _build_config_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="Configuration")

        sections = ttk.Notebook(tab)
        sections.pack(fill="both", expand=True)
        for section in SECTIONS:
            frame = ttk.Frame(sections, padding=12)
            sections.add(frame, text=section)
            for row, setting in enumerate(settings_in(section)):
                ttk.Label(frame, text=setting.label).grid(row=row, column=0, sticky="w", pady=3)
                value = self.config_obj.get(setting.key)
                if setting.type == "bool":
                    var: tk.Variable = BooleanVar(value=bool(value))
                    ttk.Checkbutton(frame, variable=var).grid(row=row, column=1, sticky="w")
                elif setting.type == "choice":
                    var = StringVar(value=str(value))
                    ttk.Combobox(frame, textvariable=var, values=list(setting.choices),
                                 state="readonly", width=28).grid(row=row, column=1, sticky="w")
                else:
                    text = ", ".join(map(str, value)) if setting.type == "list" else str(value)
                    var = StringVar(value=text)
                    ttk.Entry(frame, textvariable=var, width=46,
                              show="*" if setting.secret else "").grid(row=row, column=1, sticky="we")
                    if setting.type == "path":
                        ttk.Button(frame, text="…", width=3,
                                   command=lambda v=var: self.choose_path(v)).grid(row=row, column=2)
                ttk.Label(frame, text=setting.help or setting.key, style="Muted.TLabel").grid(
                    row=row, column=3, sticky="w", padx=8)
                self.vars[setting.key] = var
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(3, weight=2)

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=6)
        for text, command in (
            ("Appliquer", self.apply_config),
            ("Enregistrer", self.save_config),
            ("Recharger", self.reload_config),
            ("Valeurs par defaut", self.reset_config),
            ("Exporter…", self.export_config),
            ("Importer…", self.import_config),
            ("Nouveau profil…", self.new_profile),
            ("Supprimer le profil", self.delete_profile),
        ):
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=3)

    def _build_log_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="Journal")
        self.log_widget = tk.Text(tab, wrap="none", height=20, state="disabled",
                                  font=("Consolas" if host_os() == "windows" else "monospace", 10))
        y_scroll = ttk.Scrollbar(tab, orient="vertical", command=self.log_widget.yview)
        x_scroll = ttk.Scrollbar(tab, orient="horizontal", command=self.log_widget.xview)
        self.log_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        for level, color in LEVEL_COLORS.items():
            self.log_widget.tag_configure(level, foreground=color)
        controls = ttk.Frame(tab)
        controls.grid(row=2, column=0, sticky="w", pady=4)
        ttk.Button(controls, text="Vider", command=self.clear_log).pack(side="left")
        ttk.Button(controls, text="Enregistrer le journal…", command=self.save_log).pack(side="left", padx=4)
        ttk.Button(controls, text="Charger le fichier de log",
                   command=self.load_log_file).pack(side="left", padx=4)
        ttk.Button(controls, text="Fichiers de rotation",
                   command=self.show_log_files).pack(side="left", padx=4)

        note_bar = ttk.Frame(tab)
        note_bar.grid(row=3, column=0, sticky="ew", pady=(2, 0))
        ttk.Label(note_bar, text="Commentaire :").pack(side="left")
        self.note_var = StringVar()
        note_entry = ttk.Entry(note_bar, textvariable=self.note_var)
        note_entry.pack(side="left", fill="x", expand=True, padx=6)
        note_entry.bind("<Return>", lambda _event: self.add_note())
        ttk.Button(note_bar, text="Annoter (Ctrl+M)", command=self.add_note).pack(side="left")

    def _build_about_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="A propos")
        text = (
            f"{APP_TITLE}\n\n"
            "Console fenetree pour piloter l'agent expert-dev-autopilot :\n"
            "  · actions de build et de packaging (.exe / .apk / .dmg)\n"
            "  · configuration complete par profils (fichier, env, CLI)\n"
            "  · journal en flux avec masquage des secrets\n\n"
            f"Fichier de configuration : {self.config_obj.path}\n"
            f"Plateforme : {sys.platform} ({host_os()})\n"
            f"Python : {sys.version.split()[0]}\n\n"
            "Garde-fous : les commandes destructives listees dans\n"
            "Securite > Commandes bloquees sont refusees, quelle que soit\n"
            "la valeur de 'Allow all'."
        )
        ttk.Label(tab, text=text, justify="left").pack(anchor="w")
        buttons = ttk.Frame(tab)
        buttons.pack(anchor="w", pady=8)
        ttk.Button(buttons, text="Ouvrir le dossier de configuration",
                   command=lambda: webbrowser.open(self.config_obj.path.parent.as_uri())).pack(side="left")
        ttk.Button(buttons, text="Ouvrir le dossier des journaux",
                   command=self.open_log_dir).pack(side="left", padx=6)
        ttk.Button(buttons, text="Desinstaller…", command=self.show_uninstall).pack(side="left")

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Label(bar, textvariable=self.status).pack(side="left")
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=140)
        self.progress.pack(side="right")

    def _bind_shortcuts(self) -> None:
        self.master_window.bind("<Control-s>", lambda _e: self.save_config())
        self.master_window.bind("<Control-r>", lambda _e: self.run_action(self.config_obj.get("build.default_target") and "build"))
        self.master_window.bind("<Escape>", lambda _e: self.runner.stop())
        self.master_window.bind("<Control-l>", lambda _e: self.clear_log())
        self.master_window.bind("<Control-m>", lambda _e: self.add_note())

    # -- theme -------------------------------------------------------------- #

    def _apply_theme(self) -> None:
        theme = self.config_obj.get("ui.theme")
        if theme == "system":
            theme = "sombre" if host_os() == "linux" else "clair"
        palette = PALETTES[theme]
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        font = ("Segoe UI" if host_os() == "windows" else "DejaVu Sans",
                self.config_obj.get("ui.font_size"))
        self.master_window.configure(bg=palette["bg"])
        style.configure(".", background=palette["bg"], foreground=palette["fg"], font=font)
        style.configure("TLabelframe", background=palette["bg"], bordercolor=palette["muted"])
        style.configure("TLabelframe.Label", background=palette["bg"], foreground=palette["accent"])
        style.configure("TButton", background=palette["tab"], foreground=palette["fg"],
                        padding=(8, 4), borderwidth=1)
        style.map("TButton",
                  background=[("active", palette["tab_active"]), ("disabled", palette["bg"])],
                  foreground=[("disabled", palette["muted"])])
        for widget in ("TEntry", "TCombobox", "TSpinbox"):
            style.configure(widget, fieldbackground=palette["field"], background=palette["field"],
                            foreground=palette["field_fg"], insertcolor=palette["field_fg"],
                            arrowcolor=palette["fg"], bordercolor=palette["muted"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", palette["field"])],
                  foreground=[("readonly", palette["field_fg"])],
                  selectbackground=[("readonly", palette["field"])],
                  selectforeground=[("readonly", palette["field_fg"])])
        style.configure("TNotebook", background=palette["bg"], bordercolor=palette["muted"])
        style.configure("TNotebook.Tab", padding=(14, 7), background=palette["tab"],
                        foreground=palette["muted"])
        style.map("TNotebook.Tab",
                  background=[("selected", palette["tab_active"])],
                  foreground=[("selected", palette["fg"])],
                  expand=[("selected", (0, 0, 0, 1))])
        style.configure("TCheckbutton", background=palette["bg"], foreground=palette["fg"])
        style.map("TCheckbutton", background=[("active", palette["bg"])])
        style.configure("Muted.TLabel", background=palette["bg"], foreground=palette["muted"])
        style.configure("TProgressbar", background=palette["accent"], troughcolor=palette["field"])
        self.log_widget.configure(bg=palette["log_bg"], fg=palette["log_fg"],
                                  insertbackground=palette["log_fg"],
                                  selectbackground=palette["accent"])

    # -- journal ------------------------------------------------------------ #

    def log(self, level: str, text: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text + "\n", level if level in LEVEL_COLORS else "")
        limit = self.config_obj.get("ui.log_lines")
        lines = int(self.log_widget.index("end-1c").split(".")[0])
        if lines > limit:
            self.log_widget.delete("1.0", f"{lines - limit}.0")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", "end")
        self.log_widget.configure(state="disabled")

    def add_note(self) -> None:
        """Ecrit un commentaire horodate dans la fenetre et dans le fichier de log."""
        text = self.note_var.get().strip()
        if not text:
            return
        self.runner.note(text, author="user")
        self.note_var.set("")
        self.status.set("commentaire ajoute au journal")

    def load_log_file(self) -> None:
        path = resolve_log_file(self.config_obj)
        if not path.exists():
            messagebox.showinfo(APP_TITLE, f"aucun fichier de journal : {path}")
            return
        self.log("info", f"--- {path} (dernieres {self.config_obj.get('ui.log_lines')} lignes) ---")
        for line in read_tail(path, self.config_obj.get("ui.log_lines")).splitlines():
            self.log("note" if line.lstrip().startswith("#") else "out", line)

    def open_log_dir(self) -> None:
        directory = resolve_log_file(self.config_obj).parent
        directory.mkdir(parents=True, exist_ok=True)
        webbrowser.open(directory.as_uri())

    def show_uninstall(self) -> None:
        """Affiche le plan de desinstallation ; la suppression reste manuelle."""
        targets = [target for target in collect_targets(
            self.config_obj, keep_config=False, keep_logs=False, keep_venv=False)
            if target.path.exists()]
        if not targets:
            messagebox.showinfo(APP_TITLE, "rien a desinstaller : installation deja propre")
            return
        plan = "\n".join(f"  {target.path}  [{target.label}]" for target in targets)
        messagebox.showinfo(
            APP_TITLE,
            "Elements qui seraient supprimes :\n\n" + plan +
            "\n\nPour desinstaller, fermez la fenetre puis lancez :\n"
            "  uninstall.bat            (Windows)\n"
            "  ./uninstall.sh           (Linux/macOS)\n"
            "  python -m edac uninstall --dry-run\n\n"
            "Options : --keep-config, --keep-logs, --keep-venv, --yes."
        )

    def show_log_files(self) -> None:
        files = list_log_files(self.config_obj)
        if not files:
            messagebox.showinfo(APP_TITLE, "aucun fichier de journal")
            return
        details = "\n".join(f"{item}  ({item.stat().st_size} o)" for item in files)
        messagebox.showinfo(APP_TITLE, details)

    def save_log(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".log",
                                            filetypes=[("Journal", "*.log"), ("Tous", "*.*")])
        if path:
            Path(path).write_text(self.log_widget.get("1.0", "end"), encoding="utf-8")
            self.status.set(f"journal enregistre : {path}")

    def _drain_queue(self) -> None:
        try:
            while True:
                level, text = self.queue.get_nowait()
                self.log(level, text)
        except queue.Empty:
            pass
        running = self.runner.running
        self.stop_button.configure(state="normal" if running else "disabled")
        if running:
            self.progress.start(12)
            self.status.set("execution en cours…")
        else:
            self.progress.stop()
            if self.status.get() == "execution en cours…":
                self.status.set("pret")
        self.after(80, self._drain_queue)

    # -- actions ------------------------------------------------------------ #

    def run_action(self, action: str) -> None:
        self.apply_config(silent=True)
        try:
            command = build_command(self.config_obj, action)
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.notebook.select(2)
        self.runner.start(command)

    def run_custom(self) -> None:
        command = self.custom_var.get().strip()
        if not command:
            return
        self.apply_config(silent=True)
        self.notebook.select(2)
        self.runner.start(command)

    def run_pipeline(self) -> None:
        if not self.config_obj.get("autopilot.enabled"):
            messagebox.showinfo(APP_TITLE, "Autopilot desactive.")
            return
        target = f"package:{self.config_obj.get('build.default_target')}"
        steps = ["setup", "build", target if target != "package:web" else "build", "verify"]
        self.apply_config(silent=True)
        self.notebook.select(2)
        self._run_chain(steps)

    def _run_chain(self, steps: list[str]) -> None:
        if not steps:
            self.queue.put(("ok", "chaine terminee"))
            return
        step, rest = steps[0], steps[1:]
        try:
            command = build_command(self.config_obj, step)
        except ValueError as exc:
            self.queue.put(("error", str(exc)))
            return

        def on_done(result) -> None:
            if result.exit_code == 0:
                self.after(50, lambda: self._run_chain(rest))
            else:
                self.queue.put(("error", f"chaine interrompue a l'etape '{step}'"))

        self.runner.start(command, on_done=on_done)

    # -- configuration ------------------------------------------------------ #

    def choose_project(self) -> None:
        path = filedialog.askdirectory(title="Choisir le dossier du projet")
        if path:
            self.project_var.set(path)
            self.config_obj.set("project.path", path)
            if "project.path" in self.vars:
                self.vars["project.path"].set(path)
            self.status.set(f"projet : {path}")

    def choose_path(self, var: tk.Variable) -> None:
        path = filedialog.askdirectory(title="Choisir un dossier")
        if path:
            var.set(path)

    def _quick_set(self, key: str, var: tk.Variable) -> None:
        self.config_obj.set(key, var.get())
        if key in self.vars:
            self.vars[key].set(var.get())
        self.status.set(f"{key} = {var.get()}")

    def apply_config(self, silent: bool = False) -> bool:
        self.config_obj.set("project.path", self.project_var.get())
        errors: list[str] = []
        for key, var in self.vars.items():
            try:
                self.config_obj.set(key, var.get())
            except ConfigError as exc:
                errors.append(str(exc))
        if "project.path" in self.vars:
            self.vars["project.path"].set(self.config_obj.get("project.path"))
        if errors:
            messagebox.showerror(APP_TITLE, "\n".join(errors))
            return False
        self._apply_theme()
        if not silent:
            self.status.set("configuration appliquee (non enregistree)")
        return True

    def save_config(self) -> None:
        if not self.apply_config(silent=True):
            return
        try:
            path = self.config_obj.save()
        except (ConfigError, OSError) as exc:
            messagebox.showerror(APP_TITLE, f"enregistrement impossible : {exc}")
            return
        self.status.set(f"enregistre : {path}")
        self.log("ok", f"configuration enregistree dans {path}")

    def reload_config(self) -> None:
        self.config_obj = Config.load(self.config_obj.path, profile=self.config_obj.active_profile)
        self.runner.config = self.config_obj
        self._refresh_vars()
        self.status.set("configuration rechargee")

    def reset_config(self) -> None:
        if messagebox.askyesno(APP_TITLE, "Restaurer toutes les valeurs par defaut du profil courant ?"):
            self.config_obj.reset(scope="global")
            self.config_obj.reset(scope="profile")
            self._refresh_vars()
            self.status.set("valeurs par defaut restaurees (non enregistrees)")

    def export_config(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            self.apply_config(silent=True)
            self.config_obj.export_to(path)
            self.status.set(f"exporte : {path}")

    def import_config(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.config_obj.import_from(path)
        except (ConfigError, OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, f"import impossible : {exc}")
            return
        self._refresh_vars()
        self.status.set(f"importe : {path}")

    def new_profile(self) -> None:
        from tkinter.simpledialog import askstring

        name = askstring(APP_TITLE, "Nom du nouveau profil :", parent=self.master_window)
        if not name:
            return
        try:
            self.config_obj.create_profile(name, copy_current=True)
            self.config_obj.use_profile(name)
        except ConfigError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._refresh_profiles()
        self.status.set(f"profil actif : {name}")

    def delete_profile(self) -> None:
        name = self.config_obj.active_profile
        if not messagebox.askyesno(APP_TITLE, f"Supprimer le profil '{name}' ?"):
            return
        try:
            self.config_obj.delete_profile(name)
        except ConfigError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._refresh_profiles()
        self._refresh_vars()

    def on_profile_change(self, _event: object) -> None:
        try:
            self.config_obj.use_profile(self.profile_var.get())
        except ConfigError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._refresh_vars()
        self.status.set(f"profil actif : {self.config_obj.active_profile}")

    def _refresh_profiles(self) -> None:
        self.profile_box.configure(values=self.config_obj.profile_names())
        self.profile_var.set(self.config_obj.active_profile)

    def _refresh_vars(self) -> None:
        for key, var in self.vars.items():
            value = self.config_obj.get(key)
            setting = SETTINGS_BY_KEY[key]
            var.set(", ".join(map(str, value)) if setting.type == "list" else value)
        self.project_var.set(self.config_obj.get("project.path"))
        self.autopilot_var.set(self.config_obj.get("autopilot.enabled"))
        self.allow_all_var.set(self.config_obj.get("autopilot.allow_all"))
        self._apply_theme()

    # -- fermeture ---------------------------------------------------------- #

    def on_close(self) -> None:
        if self.runner.running:
            if not messagebox.askyesno(APP_TITLE, "Une commande est en cours. Quitter quand meme ?"):
                return
            self.runner.stop()
        elif self.config_obj.get("ui.confirm_exit"):
            if not messagebox.askyesno(APP_TITLE, "Quitter la console ?"):
                return
        self.master_window.destroy()


def launch(config: Config) -> int:
    setup_logging(config)
    root = Tk()
    try:
        icon = Path(__file__).with_name("assets") / "icon.png"
        if icon.exists():
            root.iconphoto(True, tk.PhotoImage(file=str(icon)))
    except tk.TclError:
        pass
    ConsoleApp(root, config)
    root.mainloop()
    return 0
