import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, simpledialog
import datetime

from app.services.settings_manager import SettingsManager
from app.services.text_processing import TextFileParser

class SettingsView(Toplevel):
    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager):
        super().__init__(parent); self.settings_manager = settings_manager
        self.title("Impostazioni Materie e Percorsi"); self.geometry("800x480")
        self.transient(parent); self.grab_set()
        self.vars = {"txt_path": tk.StringVar(), "img_path": tk.StringVar(), "exam_date": tk.StringVar(), "status": tk.StringVar()}
        frame = ttk.Frame(self, padding=20); frame.pack(expand=True, fill="both")
        subject_frame = ttk.LabelFrame(frame, text="Gestione Materie", padding=10); subject_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 20))
        subject_frame.columnconfigure(1, weight=1)
        ttk.Label(subject_frame, text="Materia:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.subject_combo = ttk.Combobox(subject_frame, values=self.settings_manager.get_subjects(), state="readonly"); self.subject_combo.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        self.subject_combo.bind("<<ComboboxSelected>>", self.update_display_for_subject)
        btn_frame = ttk.Frame(subject_frame); btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Aggiungi...", command=self._add_subject).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Rimuovi", command=self._remove_subject).pack(side='left', padx=2)
        details_frame = ttk.LabelFrame(frame, text="Dettagli Materia Selezionata", padding=10); details_frame.grid(row=1, column=0, columnspan=3, sticky='ew')
        details_frame.columnconfigure(1, weight=1)
        ttk.Label(details_frame, text="File Quiz (.txt):").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(details_frame, textvariable=self.vars["txt_path"], state="readonly").grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(details_frame, text="Cambia...", command=lambda: self.select_path("txt_path")).grid(row=0, column=2, sticky='ew', pady=5, padx=5)
        bookmark_frame = ttk.Frame(details_frame); bookmark_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5, pady=(0,10))
        bookmark_frame.columnconfigure(1, weight=1)
        ttk.Label(bookmark_frame, text="Segnalibro di Studio:", font=('Helvetica', 9, 'italic')).grid(row=0, column=0, sticky='w')
        self.bookmark_var = tk.StringVar(value=TextFileParser.BOOKMARK); ttk.Entry(bookmark_frame, textvariable=self.bookmark_var, state="readonly", justify='center').grid(row=0, column=1, sticky='ew', padx=10)
        ttk.Button(bookmark_frame, text="Copia", command=self._copy_bookmark).grid(row=0, column=2)
        ttk.Label(details_frame, text="Cartella Immagini:").grid(row=2, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(details_frame, textvariable=self.vars["img_path"], state="readonly").grid(row=2, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(details_frame, text="Cambia...", command=lambda: self.select_path("img_path")).grid(row=2, column=2, sticky='ew', pady=5, padx=5)
        ttk.Label(details_frame, text="Data Esame (GG/MM/AAAA):").grid(row=3, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(details_frame, textvariable=self.vars["exam_date"]).grid(row=3, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        ttk.Label(details_frame, text="Stato:").grid(row=4, column=0, sticky='w', pady=5, padx=5)
        ttk.Combobox(details_frame, textvariable=self.vars["status"], values=["In Corso", "Passato"], state="readonly").grid(row=4, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        ttk.Button(frame, text="Salva e Chiudi", command=self.save_and_close, style="Accent.TButton").grid(row=2, column=0, columnspan=3, sticky='ew', pady=(20,0), ipady=5)
        self._refresh_combobox()

    def _copy_bookmark(self):
        self.clipboard_clear(); self.clipboard_append(self.bookmark_var.get()); messagebox.showinfo("Copiato", "La frase segnalibro è stata copiata negli appunti.", parent=self)
    def _refresh_combobox(self):
        subjects = self.settings_manager.get_subjects(); self.subject_combo['values'] = subjects
        if subjects: self.subject_combo.current(0)
        else: self.subject_combo.set('')
        self.update_display_for_subject()
    def _add_subject(self):
        new_subject = simpledialog.askstring("Aggiungi Materia", "Nome nuova materia:", parent=self)
        if new_subject and new_subject.strip():
            self.settings_manager.add_subject(new_subject.strip().upper()); self._refresh_combobox(); self.subject_combo.set(new_subject.strip().upper())
    def _remove_subject(self):
        subject = self.subject_combo.get()
        if not subject: return messagebox.showwarning("Attenzione", "Nessuna materia selezionata.", parent=self)
        if messagebox.askyesno("Conferma", f"Vuoi rimuovere '{subject}' e tutti i suoi dati di studio?", parent=self):
            self.settings_manager.remove_subject(subject); self._refresh_combobox()
    def update_display_for_subject(self, event=None):
        subject = self.subject_combo.get()
        data = self.settings_manager.get_subject_data(subject) if subject else {}
        for key, var in self.vars.items(): var.set(data.get(key, ''))
    def select_path(self, path_type: str):
        if not self.subject_combo.get(): return messagebox.showwarning("Attenzione", "Seleziona prima una materia.", parent=self)
        if path_type == "txt_path": path = filedialog.askopenfilename(title="Seleziona file .txt", filetypes=[("Text Files", "*.txt")])
        else: path = filedialog.askdirectory(title="Seleziona cartella immagini")
        if path: self.vars[path_type].set(path)
    def save_and_close(self):
        subject = self.subject_combo.get()
        if subject:
            data_to_save = {key: var.get() for key, var in self.vars.items()}
            try:
                if data_to_save["exam_date"]: datetime.datetime.strptime(data_to_save["exam_date"], '%d/%m/%Y')
            except ValueError: return messagebox.showerror("Errore Formato", "Formato data non valido. Usare GG/MM/AAAA.", parent=self)
            self.settings_manager.set_subject_data(subject, data_to_save)
        self.settings_manager.save(); self.destroy()
