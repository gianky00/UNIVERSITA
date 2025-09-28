import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, simpledialog
import datetime
from typing import Dict
from pathlib import Path

from app.services.settings_manager import SettingsManager
from app.services.config_manager import ConfigManager
from app.views.dialogs import Tooltip

class SettingsView(Toplevel):
    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager, config_manager: ConfigManager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.config_manager = config_manager
        self.title("Impostazioni")
        self.geometry("800x600")  # Aumentata l'altezza per i nuovi widget
        self.transient(parent)
        self.grab_set()

        # Memorizza il profilo attivo all'apertura per rilevare cambiamenti
        self.initial_active_profile = self.config_manager.get_active_profile()

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

        self._refresh_subject_combobox()
        self._load_global_settings()
        self._refresh_profile_combobox()

    def create_materie_tab(self):
        self.subject_vars = {"txt_path": tk.StringVar(), "img_path": tk.StringVar(), "exam_date": tk.StringVar(), "status": tk.StringVar()}

        subject_frame = ttk.LabelFrame(self.materie_tab, text="Selezione Materia", padding=10)
        subject_frame.pack(fill='x', expand=True)
        subject_frame.columnconfigure(1, weight=1)
        ttk.Label(subject_frame, text="Materia:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.subject_combo = ttk.Combobox(subject_frame, state="readonly")
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

        # --- Profile Management Frame ---
        profile_frame = ttk.LabelFrame(self.generali_tab, text="Gestione Profili di Sincronizzazione", padding=10)
        profile_frame.pack(fill='x', expand=True, pady=(0, 10))
        profile_frame.columnconfigure(1, weight=1)

        ttk.Label(profile_frame, text="Profilo Attivo:").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.profile_combo = ttk.Combobox(profile_frame, state="readonly", exportselection=False)
        self.profile_combo.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected_in_combo)

        profile_btn_frame = ttk.Frame(profile_frame)
        profile_btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(profile_btn_frame, text="Aggiungi", command=self._add_profile).pack(side='left', padx=2)
        ttk.Button(profile_btn_frame, text="Rimuovi", command=self._remove_profile).pack(side='left', padx=2)

        ttk.Label(profile_frame, text="Percorso Dati:").grid(row=1, column=0, sticky='w', pady=5, padx=5)
        self.data_path_var = tk.StringVar()
        path_entry = ttk.Entry(profile_frame, textvariable=self.data_path_var, state="readonly")
        path_entry.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(profile_frame, text="Cambia Percorso", command=self._edit_profile_path).grid(row=1, column=2, sticky='ew', pady=5, padx=5)

        # --- SRS Frame ---
        srs_frame = ttk.LabelFrame(self.generali_tab, text="Intervalli di Ripetizione (in minuti)", padding=10)
        srs_frame.pack(fill='x', expand=True)
        srs_labels = {"srs_again": "Di Nuovo:", "srs_hard": "Difficile:", "srs_good": "Buono:", "srs_easy": "Facile:"}
        for i, (key, label) in enumerate(srs_labels.items()):
            ttk.Label(srs_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            ttk.Entry(srs_frame, textvariable=self.global_vars[key], width=10).grid(row=i, column=1, padx=5, pady=5, sticky='w')

        # --- Other Settings Frame ---
        other_frame = ttk.LabelFrame(self.generali_tab, text="Altre Impostazioni", padding=10)
        other_frame.pack(fill='x', expand=True, pady=10)
        ttk.Label(other_frame, text="Periodo Ritenzione (giorni):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(other_frame, textvariable=self.global_vars["retention_period_days"], width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(other_frame, text="Nuove Carte per Sessione:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(other_frame, textvariable=self.global_vars["new_cards_per_day"], width=10).grid(row=1, column=1, padx=5, pady=5, sticky='w')

    # --- Profile Methods ---
    def _refresh_profile_combobox(self):
        profiles = self.config_manager.get_profiles()
        self.profile_combo['values'] = profiles
        active_profile = self.config_manager.get_active_profile()
        if active_profile in profiles:
            self.profile_combo.set(active_profile)
        elif profiles:
            self.profile_combo.set(profiles[0])
        self._update_path_display()

    def _update_path_display(self):
        selected_profile = self.profile_combo.get()
        if selected_profile:
            path = self.config_manager.config["profiles"][selected_profile]["data_path"]
            self.data_path_var.set(path)
        else:
            self.data_path_var.set("")

    def _on_profile_selected_in_combo(self, event=None):
        self._update_path_display()

    def _add_profile(self):
        new_name = simpledialog.askstring("Nuovo Profilo", "Inserisci il nome per il nuovo profilo:", parent=self)
        if not new_name or not new_name.strip():
            return

        new_path = filedialog.askdirectory(title=f"Seleziona la cartella dati per '{new_name}'", mustexist=True, parent=self)
        if not new_path:
            return

        try:
            self.config_manager.add_profile(new_name.strip(), new_path)
            self._refresh_profile_combobox()
            self.profile_combo.set(new_name.strip())
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)

    def _remove_profile(self):
        profile_to_remove = self.profile_combo.get()
        if not profile_to_remove:
            return messagebox.showwarning("Attenzione", "Nessun profilo selezionato.", parent=self)

        if not messagebox.askyesno("Conferma", f"Sei sicuro di voler rimuovere il profilo '{profile_to_remove}'?\nQuesta azione non cancella i dati, solo il riferimento al profilo.", parent=self):
            return

        try:
            self.config_manager.remove_profile(profile_to_remove)
            self._refresh_profile_combobox()
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)

    def _edit_profile_path(self):
        selected_profile = self.profile_combo.get()
        if not selected_profile:
            return messagebox.showwarning("Attenzione", "Nessun profilo selezionato.", parent=self)

        new_path = filedialog.askdirectory(title=f"Seleziona la nuova cartella dati per '{selected_profile}'", mustexist=True, parent=self)
        if not new_path:
            return

        self.config_manager.update_profile_path(selected_profile, new_path)
        self._update_path_display()

    def _load_global_settings(self):
        settings = self.settings_manager.get_global_settings()
        self.global_vars["retention_period_days"].set(settings.get("retention_period_days", 7))
        self.global_vars["new_cards_per_day"].set(settings.get("new_cards_per_day", 20))
        srs_intervals = settings.get("srs_intervals", {})
        self.global_vars["srs_again"].set(srs_intervals.get("again", 10))
        self.global_vars["srs_hard"].set(srs_intervals.get("hard", 120))
        self.global_vars["srs_good"].set(srs_intervals.get("good", 1440))
        self.global_vars["srs_easy"].set(srs_intervals.get("easy", 4320))

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

    def _refresh_subject_combobox(self):
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
            self._refresh_subject_combobox()
            self.subject_combo.set(new_subject.strip().upper())

    def _remove_subject(self):
        subject = self.subject_combo.get()
        if not subject:
            return messagebox.showwarning("Attenzione", "Nessuna materia selezionata.", parent=self)
        if messagebox.askyesno("Conferma", f"Vuoi rimuovere '{subject}' e tutti i suoi dati di studio?", parent=self):
            self.settings_manager.remove_subject(subject)
            self._refresh_subject_combobox()

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
            path = filedialog.askopenfilename(title="Seleziona file .txt", filetypes=[("Text Files", "*.txt")], initialdir=initial_dir)
        else:
            path = filedialog.askdirectory(title="Seleziona cartella immagini", initialdir=initial_dir)

        if path:
            self.subject_vars[path_type].set(path)

    def save_and_close(self):
        # Salva le modifiche al profilo attivo
        new_active_profile = self.profile_combo.get()
        if new_active_profile and new_active_profile != self.initial_active_profile:
            self.config_manager.set_active_profile(new_active_profile)

        # Salva le impostazioni della materia
        subject = self.subject_combo.get()
        if subject:
            data_to_save = {key: var.get() for key, var in self.subject_vars.items()}
            # Usa il percorso del profilo *appena impostato* per rendere relativi i path
            data_path = self.config_manager.get_data_path()
            for key in ["txt_path", "img_path"]:
                path_str = data_to_save.get(key)
                if path_str:
                    try:
                        path_obj = Path(path_str)
                        if path_obj.is_absolute():
                            data_to_save[key] = str(path_obj.relative_to(data_path))
                    except ValueError:
                        pass  # Lascia il percorso assoluto se non è relativo al data_path
            try:
                if data_to_save["exam_date"]:
                    datetime.datetime.strptime(data_to_save["exam_date"], '%d/%m/%Y')
            except ValueError:
                return messagebox.showerror("Errore Formato", "Formato data non valido. Usare GG/MM/AAAA.", parent=self)
            self.settings_manager.set_subject_data(subject, data_to_save)

        # Salva le impostazioni globali
        try:
            self._save_global_settings()
        except tk.TclError as e:
            return messagebox.showerror("Errore Input", f"Valore non valido nelle impostazioni generali. Assicurati che tutti i campi siano numeri interi.\n\nDettaglio: {e}", parent=self)

        self.settings_manager.save()
        self.destroy()