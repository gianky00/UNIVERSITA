import tkinter as tk
from tkinter import ttk, simpledialog, Toplevel

class SubjectSelectionDialog(simpledialog.Dialog):
    def __init__(self, parent, title, subjects):
        self.subjects = subjects; self.result = None; super().__init__(parent, title)
    def body(self, master):
        ttk.Label(master, text="Seleziona una materia:").pack(pady=10)
        self.combo = ttk.Combobox(master, values=self.subjects, state="readonly", width=30); self.combo.pack(padx=10)
        if self.subjects: self.combo.current(0)
        return self.combo
    def apply(self): self.result = self.combo.get()

class LoadingView(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Analisi in corso...")
        self.geometry("300x100")
        self.transient(parent); self.grab_set(); self.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(self, text="Analisi delle domande in corso...", font=('Helvetica', 11)).pack(pady=10, expand=True)
        ttk.Progressbar(self, mode='indeterminate').pack(fill='x', padx=20, pady=10)
        self.start_animation()
    def start_animation(self): self.children['!progressbar'].start(10)
    def stop(self): self.destroy()
