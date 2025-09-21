import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

class AnalysisView(tk.Toplevel):
    """Una finestra per visualizzare le statistiche di performance complessive."""
    def __init__(self, parent: tk.Tk, stats: Dict[str, Any]):
        super().__init__(parent)
        self.title("Analisi Performance")
        self.geometry("450x350")
        self.transient(parent)
        self.grab_set()

        self._configure_styles()
        self._create_widgets(stats)

    def _configure_styles(self):
        self.configure(background="#ECECEC")
        style = ttk.Style(self)
        style.configure("Analysis.TLabelFrame", padding=15, background="#ECECEC")
        style.configure("Analysis.TLabelFrame.Label", font=("Helvetica", 12, "bold"))
        style.configure("Stat.TLabel", font=("Helvetica", 10), background="#ECECEC")
        style.configure("StatValue.TLabel", font=("Helvetica", 10, "bold"), foreground="#333333", background="#ECECEC")

    def _create_widgets(self, stats: Dict[str, Any]):
        main_frame = ttk.Frame(self, padding=20, style="Analysis.TLabelFrame")
        main_frame.pack(expand=True, fill="both")

        main_frame.columnconfigure(1, weight=1)

        stat_labels = {
            "Serie di studio più lunga:": f"{stats.get('longest_streak', 0)} giorni",
            "Totale ripassi effettuati:": f"{stats.get('total_reviews', 0)}",
            "Tasso di ritenzione generale:": f"{stats.get('overall_retention', 0.0):.1f}%",
            "Materia più studiata:": f"{stats.get('most_studied', 'N/D')}"
        }

        row = 0
        for label, value in stat_labels.items():
            ttk.Label(main_frame, text=label, style="Stat.TLabel").grid(row=row, column=0, sticky="w", pady=5)
            ttk.Label(main_frame, text=value, style="StatValue.TLabel").grid(row=row, column=1, sticky="e", pady=5, padx=10)
            row += 1

        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=15)
        row += 1

        close_button = ttk.Button(main_frame, text="Chiudi", command=self.destroy, style="Accent.TButton")
        close_button.grid(row=row, column=0, columnspan=2, sticky="ew", ipady=5)
