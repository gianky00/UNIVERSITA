import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, simpledialog
import datetime
from typing import Dict
from pathlib import Path

from app.services.settings_manager import SettingsManager
from app.services.config_manager import ConfigManager
from app.services.text_processing import TextFileParser
from app.views.dialogs import Tooltip

class SettingsView(Toplevel):
    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager, config_manager: ConfigManager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.config_manager = config_manager
        self.title("Impostazioni")
        self.geometry("800x520")
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill="both")

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both", pady=5)

        self.materie_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.materie_tab, text="Gestione Materie")
        self.create_materie_tab()

        self.generali_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.generali_tab, text="Impostazioni Generali")
        self.create_generali_tab()

        ttk.Button(main_frame, text="Salva e Chiudi", command=self.save_and_close, style="Accent.TButton").pack(side='bottom', fill='x', ipady=5, pady=(10,0))

        self._refresh_combobox()
        self._load_global_settings()

    def create_materie_tab(self):
        self.subject_vars = {"txt_path": tk.StringVar(), "img_path": tk.StringVar(), "exam_date": tk.StringVar(), "status": tk.StringVar()}

        subject_frame = ttk.LabelFrame(self.materie_tab, text="Selezione Materia", padding=10)
        subject_frame.pack(fill='x', expand=True)
        subject_frame.columnconfigure(1, weight=1)
        ttk.Label(subject_frame, text="Materia:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.subject_combo = ttk.Combobox(subject_frame, values=self.settings_manager.get_subjects(), state="readonly")
        self.subject_combo.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        self.subject_combo.bind("<<ComboboxSelected>>", self.update_display_for_subject)
        btn_frame = ttk.Frame(subject_frame)
        btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Aggiungi...", command=self._add_subject).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Rimuovi", command=self._remove_subject).pack(side='left', padx=2)

        details_frame = ttk.LabelFrame(self.materie_tab, text="Dettagli Materia Selezionata", padding=10)
        details_frame.pack(fill='x', expand=True, pady=(10,0))
        details_frame.columnconfigure(1, weight=1)
        ttk.Label(details_frame, text="File Quiz (.txt):").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(details_frame, textvariable=self.subject_vars["txt_path"], state="readonly").grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(details_frame, text="Cambia...", command=lambda: self.select_path("txt_path")).grid(row=0, column=2, sticky='ew', pady=5, padx=5)
        ttk.Label(details_frame, text="Cartella Immagini:").grid(row=1, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(details_frame, textvariable=self.subject_vars["img_path"], state="readonly").grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(details_frame, text="Cambia...", command=lambda: self.select_path("img_path")).grid(row=1, column=2, sticky='ew', pady=5, padx=5)
        ttk.Label(details_frame, text="Data Esame (GG/MM/AAAA):").grid(row=2, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(details_frame, textvariable=self.subject_vars["exam_date"]).grid(row=2, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        ttk.Label(details_frame, text="Stato:").grid(row=3, column=0, sticky='w', pady=5, padx=5)
        ttk.Combobox(details_frame, textvariable=self.subject_vars["status"], values=["In Corso", "Passato"], state="readonly").grid(row=3, column=1, columnspan=2, sticky='ew', pady=5, padx=5)

    def create_generali_tab(self):
        self.global_vars = {
            "retention_period_days": tk.IntVar(value=7), "new_cards_per_day": tk.IntVar(value=20),
            "srs_again": tk.IntVar(value=10), "srs_hard": tk.IntVar(value=120),
            "srs_good": tk.IntVar(value=1440), "srs_easy": tk.IntVar(value=4320)
        }

        srs_frame = ttk.LabelFrame(self.generali_tab, text="Intervalli di Ripetizione (in minuti)", padding=10)
        srs_frame.pack(fill='x', expand=True)
        srs_labels = {"srs_again": "Di Nuovo:", "srs_hard": "Difficile:", "srs_good": "Buono:", "srs_easy": "Facile:"}
        for i, (key, label) in enumerate(srs_labels.items()):
            ttk.Label(srs_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            ttk.Entry(srs_frame, textvariable=self.global_vars[key], width=10).grid(row=i, column=1, padx=5, pady=5, sticky='w')

        other_frame = ttk.LabelFrame(self.generali_tab, text="Altre Impostazioni", padding=10)
        other_frame.pack(fill='x', expand=True, pady=(10,0))
        ttk.Label(other_frame, text="Periodo Ritenzione (giorni):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(other_frame, textvariable=self.global_vars["retention_period_days"], width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(other_frame, text="Nuove Carte per Sessione:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(other_frame, textvariable=self.global_vars["new_cards_per_day"], width=10).grid(row=1, column=1, padx=5, pady=5, sticky='w')

        sync_frame = ttk.LabelFrame(self.generali_tab, text="Sincronizzazione Dati (Google Drive, etc.)", padding=10)
        sync_frame.pack(fill='x', expand=True, pady=(10,0))
        sync_frame.columnconfigure(0, weight=1)
        self.data_path_var = tk.StringVar()
        path_entry = ttk.Entry(sync_frame, textvariable=self.data_path_var, state="readonly")
        path_entry.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        path_button = ttk.Button(sync_frame, text="Cambia Cartella Dati...", command=self._select_data_directory)
        path_button.grid(row=0, column=1, padx=5, pady=5)
        path_help = ttk.Label(sync_frame, text="?", font=('Helvetica', 9, 'bold'), cursor="question_arrow")
        path_help.grid(row=0, column=2, padx=(5,0), sticky='w')
        Tooltip(path_help, "Seleziona la cartella dove salvare i dati. Per la sincronizzazione, scegli la tua cartella Google Drive/Dropbox. ATTENZIONE: Dovrai spostare manualmente i file esistenti e riavviare l'app.")

    def _load_global_settings(self):
        settings = self.settings_manager.get_global_settings()
        self.global_vars["retention_period_days"].set(settings.get("retention_period_days", 7))
        self.global_vars["new_cards_per_day"].set(settings.get("new_cards_per_day", 20))
        srs_intervals = settings.get("srs_intervals", {})
        self.global_vars["srs_again"].set(srs_intervals.get("again", 10))
        self.global_vars["srs_hard"].set(srs_intervals.get("hard", 120))
        self.global_vars["srs_good"].set(srs_intervals.get("good", 1440))
        self.global_vars["srs_easy"].set(srs_intervals.get("easy", 4320))
        self.data_path_var.set(str(self.config_manager.get_data_path()))

    def _select_data_directory(self):
        new_path_str = filedialog.askdirectory(title="Seleziona la nuova cartella per i dati", mustexist=True, parent=self)
        if not new_path_str:
            return

        new_path = Path(new_path_str)
        if new_path == self.config_manager.get_data_path():
            return

        self.config_manager.set_data_path(new_path_str)
        self.data_path_var.set(new_path_str)
        messagebox.showinfo("Riavvio Richiesto", f"Il percorso dei dati è stato impostato su:\n{new_path_str}\n\nPer favore, sposta manualmente i tuoi file .json in questa nuova cartella e riavvia l'applicazione per rendere effettive le modifiche.", parent=self)
        self.destroy()

    def _save_global_settings(self):
        new_settings = {
            "retention_period_days": self.global_vars["retention_period_days"].get(),
            "new_cards_per_day": self.global_vars["new_cards_per_day"].get(),
            "srs_intervals": {
                "again": self.global_vars["srs_again"].get(),
                "hard": self.global_vars["srs_hard"].get(),
                "good": self.global_vars["srs_good"].get(),
                "easy": self.global_vars["srs_easy"].get()
            }
        }
        self.settings_manager.save_global_settings(new_settings)

    def _refresh_combobox(self):
        self.subject_combo['values'] = self.settings_manager.get_subjects()
        if self.settings_manager.get_subjects():
            self.subject_combo.current(0)
        else:
            self.subject_combo.set('')
        self.update_display_for_subject()

    def _add_subject(self):
        new_subject = simpledialog.askstring("Aggiungi Materia", "Nome nuova materia:", parent=self)
        if new_subject and new_subject.strip():
            self.settings_manager.add_subject(new_subject.strip().upper())
            self._refresh_combobox()
            self.subject_combo.set(new_subject.strip().upper())

    def _remove_subject(self):
        subject = self.subject_combo.get()
        if not subject:
            return messagebox.showwarning("Attenzione", "Nessuna materia selezionata.", parent=self)
        if messagebox.askyesno("Conferma", f"Vuoi rimuovere '{subject}' e tutti i suoi dati di studio?", parent=self):
            self.settings_manager.remove_subject(subject)
            self._refresh_combobox()

    def update_display_for_subject(self, event=None):
        subject = self.subject_combo.get()
        data = self.settings_manager.get_subject_data(subject) if subject else {}
        for key, var in self.subject_vars.items():
            var.set(data.get(key, ''))

    def select_path(self, path_type: str):
        if not self.subject_combo.get():
            return messagebox.showwarning("Attenzione", "Seleziona prima una materia.", parent=self)

        initial_dir = self.config_manager.get_data_path()

        if path_type == "txt_path":
            path = filedialog.askopenfilename(
                title="Seleziona file .txt",
                filetypes=[("Text Files", "*.txt")],
                initialdir=initial_dir
            )
        else:
            path = filedialog.askdirectory(
                title="Seleziona cartella immagini",
                initialdir=initial_dir
            )

        if path:
            # Mostra sempre il percorso assoluto nell'interfaccia utente.
            # La conversione in relativo avviene solo al salvataggio.
            self.subject_vars[path_type].set(path)

    def save_and_close(self):
        subject = self.subject_combo.get()
        if subject:
            data_to_save = {key: var.get() for key, var in self.subject_vars.items()}

            # Assicura che i percorsi siano relativi se possibile
            data_path = self.config_manager.get_data_path()
            for key in ["txt_path", "img_path"]:
                path_str = data_to_save.get(key)
                if path_str:
                    try:
                        path_obj = Path(path_str)
                        if path_obj.is_absolute():
                            relative_path = path_obj.relative_to(data_path)
                            data_to_save[key] = str(relative_path)
                    except ValueError:
                        # Se non è possibile creare un percorso relativo, lo si lascia assoluto
                        pass

            try:
                if data_to_save["exam_date"]:
                    datetime.datetime.strptime(data_to_save["exam_date"], '%d/%m/%Y')
            except ValueError:
                return messagebox.showerror("Errore Formato", "Formato data non valido. Usare GG/MM/AAAA.", parent=self)

            self.settings_manager.set_subject_data(subject, data_to_save)

        try:
            self._save_global_settings()
        except tk.TclError as e:
            return messagebox.showerror("Errore Input", f"Valore non valido nelle impostazioni generali. Assicurati che tutti i campi siano numeri interi.\n\nDettaglio: {e}", parent=self)

        self.settings_manager.save()
        self.destroy()