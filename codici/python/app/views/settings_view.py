import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, simpledialog
import datetime
from typing import Dict

from app.services.settings_manager import SettingsManager
from app.services.text_processing import TextFileParser

class SettingsView(Toplevel):
    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.title("Impostazioni")
        self.geometry("800x520")
        self.transient(parent)
        self.grab_set()

        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill="both")

        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both", pady=5)

        # --- Tab 1: Materie ---
        self.materie_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.materie_tab, text="Gestione Materie")
        self.create_materie_tab()

        # --- Tab 2: Impostazioni Generali ---
        self.generali_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.generali_tab, text="Impostazioni Generali")
        self.create_generali_tab()

        # --- Save Button ---
        ttk.Button(main_frame, text="Salva e Chiudi", command=self.save_and_close, style="Accent.TButton").pack(side='bottom', fill='x', ipady=5, pady=(10,0))

        self._refresh_combobox()
        self._load_global_settings()

    def create_materie_tab(self):
        self.subject_vars = {"txt_path": tk.StringVar(), "img_path": tk.StringVar(), "exam_date": tk.StringVar(), "status": tk.StringVar()}

        # Path profiles
        profile_frame = ttk.LabelFrame(self.materie_tab, text="Percorsi Predefiniti", padding=10)
        profile_frame.pack(fill='x', expand=True, pady=(0, 10))
        profile_frame.columnconfigure(1, weight=1)
        ttk.Label(profile_frame, text="Profilo:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.profile_combo = ttk.Combobox(profile_frame, state="readonly")
        self.profile_combo.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._apply_profile_on_select)

        profile_btn_frame = ttk.Frame(profile_frame)
        profile_btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(profile_btn_frame, text="Crea/Aggiorna", command=self._save_profile).pack(side='left', padx=2)
        ttk.Button(profile_btn_frame, text="Rimuovi", command=self._remove_profile).pack(side='left', padx=2)

        # Subject selection
        subject_frame = ttk.LabelFrame(self.materie_tab, text="Gestione Materia", padding=10)
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

        # Subject details
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
            "retention_period_days": tk.IntVar(value=7),
            "new_cards_per_day": tk.IntVar(value=20),
            "srs_again": tk.IntVar(value=10), "srs_hard": tk.IntVar(value=120),
            "srs_good": tk.IntVar(value=1440), "srs_easy": tk.IntVar(value=4320)
        }

        # SRS intervals
        srs_frame = ttk.LabelFrame(self.generali_tab, text="Intervalli di Ripetizione (in minuti)", padding=10)
        srs_frame.pack(fill='x', expand=True)
        srs_labels = {"srs_again": "Di Nuovo:", "srs_hard": "Difficile:", "srs_good": "Buono:", "srs_easy": "Facile:"}
        for i, (key, label) in enumerate(srs_labels.items()):
            ttk.Label(srs_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            ttk.Entry(srs_frame, textvariable=self.global_vars[key], width=10).grid(row=i, column=1, padx=5, pady=5, sticky='w')

        # Other settings
        other_frame = ttk.LabelFrame(self.generali_tab, text="Altre Impostazioni", padding=10)
        other_frame.pack(fill='x', expand=True, pady=(10,0))
        ttk.Label(other_frame, text="Periodo Ritenzione (giorni):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(other_frame, textvariable=self.global_vars["retention_period_days"], width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(other_frame, text="Nuove Carte per Sessione:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(other_frame, textvariable=self.global_vars["new_cards_per_day"], width=10).grid(row=1, column=1, padx=5, pady=5, sticky='w')

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

    def _refresh_combobox(self):
        subjects = self.settings_manager.get_subjects()
        self.subject_combo['values'] = subjects
        if subjects:
            self.subject_combo.current(0)
        else:
            self.subject_combo.set('')

        profiles = self.settings_manager.get_path_profiles()
        self.profile_combo['values'] = profiles
        active_profile = self.settings_manager.get_active_profile()
        if active_profile in profiles:
            self.profile_combo.set(active_profile)
        else:
            self.profile_combo.set('')

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
        if path_type == "txt_path":
            path = filedialog.askopenfilename(title="Seleziona file .txt", filetypes=[("Text Files", "*.txt")])
        else:
            path = filedialog.askdirectory(title="Seleziona cartella immagini")
        if path:
            self.subject_vars[path_type].set(path)

    def _apply_profile_on_select(self, event=None):
        profile_name = self.profile_combo.get()
        if not profile_name:
            return

        if messagebox.askyesno("Conferma", f"Vuoi applicare il profilo '{profile_name}'?\nQuesto sovrascriverà i percorsi per tutte le materie.", parent=self):
            self.settings_manager.apply_path_profile(profile_name)
            self.update_display_for_subject()
            messagebox.showinfo("Successo", f"Profilo '{profile_name}' applicato.", parent=self)
        else:
            self.profile_combo.set(self.settings_manager.get_active_profile())

    def _save_profile(self):
        if not self._save_current_subject_data():
            return

        profile_name_to_save = simpledialog.askstring("Salva Profilo", "Salva i percorsi correnti come:", initialvalue=self.profile_combo.get(), parent=self)

        if profile_name_to_save and profile_name_to_save.strip():
            self.settings_manager.save_current_paths_as_profile(profile_name_to_save.strip())
            self._refresh_combobox()
            self.profile_combo.set(profile_name_to_save.strip())
            messagebox.showinfo("Successo", f"Profilo '{profile_name_to_save.strip()}' salvato.", parent=self)

    def _remove_profile(self):
        profile_name = self.profile_combo.get()
        if not profile_name:
            messagebox.showwarning("Attenzione", "Nessun profilo selezionato.", parent=self)
            return
        if messagebox.askyesno("Conferma", f"Vuoi davvero rimuovere il profilo '{profile_name}'?", parent=self):
            self.settings_manager.remove_path_profile(profile_name)
            self._refresh_combobox()
            messagebox.showinfo("Successo", f"Profilo '{profile_name}' rimosso.", parent=self)

    def _save_current_subject_data(self) -> bool:
        subject = self.subject_combo.get()
        if not subject:
            return True

        data_to_save = {key: var.get() for key, var in self.subject_vars.items()}
        try:
            if data_to_save["exam_date"]:
                datetime.datetime.strptime(data_to_save["exam_date"], '%d/%m/%Y')
        except ValueError:
            messagebox.showerror("Errore Formato", f"Formato data non valido per la materia '{subject}'. Usare GG/MM/AAAA.", parent=self)
            return False

        self.settings_manager.set_subject_data(subject, data_to_save)
        return True

    def save_and_close(self):
        if not self._save_current_subject_data():
            return

        # Aggiorna il profilo attivo con i percorsi correnti
        active_profile = self.settings_manager.get_active_profile()
        if active_profile:
            self.settings_manager.update_profile_with_current_paths(active_profile)

        try:
            self._save_global_settings()
        except tk.TclError as e:
            messagebox.showerror("Errore Input", f"Valore non valido nelle impostazioni generali. Assicurati che tutti i campi siano numeri interi.\n\n Dettaglio: {e}", parent=self)
            return

        self.settings_manager.save()
        self.destroy()
