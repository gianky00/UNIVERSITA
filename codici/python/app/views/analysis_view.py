import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
from app.views.dialogs import Tooltip

class AnalysisView(tk.Toplevel):
    """Una finestra per visualizzare le statistiche di performance complessive."""
    def __init__(self, parent: tk.Tk, stats: Dict[str, Any]):
        super().__init__(parent)
        self.title("Analisi Performance")
        self.geometry("800x700") # Increased size for leeches
        self.transient(parent)
        self.grab_set()

        self._configure_styles()
        self._create_widgets(stats)

    def _configure_styles(self):
        BG_COLOR = "#ECECEC"
        self.configure(background=BG_COLOR)
        style = ttk.Style(self)
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR)
        style.configure("TLabelFrame", padding=15, background=BG_COLOR)
        style.configure("TLabelFrame.Label", font=("Helvetica", 12, "bold"), background=BG_COLOR)
        style.configure("Stat.TLabel", font=("Helvetica", 10), background=BG_COLOR)
        style.configure("StatValue.TLabel", font=("Helvetica", 10, "bold"), foreground="#333333", background=BG_COLOR)

    def _create_widgets(self, stats: Dict[str, Any]):
        # --- Main container ---
        container = ttk.Frame(self, padding=10, style="TFrame")
        container.pack(expand=True, fill="both")

        # --- General Stats Frame ---
        main_frame = ttk.LabelFrame(container, text="Statistiche Complessive")
        main_frame.pack(fill="x", padx=10, pady=(5, 10))
        main_frame.columnconfigure(1, weight=1)

        # General Stats content
        ttk.Label(main_frame, text="Serie di studio più lunga:", style="Stat.TLabel").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(main_frame, text=f"{stats.get('longest_streak', 0)} giorni", style="StatValue.TLabel").grid(row=0, column=1, sticky="e", pady=2, padx=10)

        ttk.Label(main_frame, text="Totale ripassi effettuati:", style="Stat.TLabel").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Label(main_frame, text=f"{stats.get('total_reviews', 0)}", style="StatValue.TLabel").grid(row=1, column=1, sticky="e", pady=2, padx=10)

        retention_frame = ttk.Frame(main_frame, style="TFrame")
        retention_frame.grid(row=2, column=0, sticky="w", padx=5)
        ttk.Label(retention_frame, text="Tasso di ritenzione generale:", style="Stat.TLabel").pack(side='left')
        help_icon = ttk.Label(retention_frame, text="?", font=('Helvetica', 9, 'bold'), cursor="question_arrow", style="Stat.TLabel")
        help_icon.pack(side='left', padx=5)
        Tooltip(help_icon, "Indica la percentuale di risposte 'Buono' o 'Facile' per le carte ripassate negli ultimi X giorni, come impostato nelle Impostazioni Generali.")
        ttk.Label(main_frame, text=f"{stats.get('overall_retention', 0.0):.1f}%", style="StatValue.TLabel").grid(row=2, column=1, sticky="e", pady=2, padx=10)

        ttk.Label(main_frame, text="Materia più studiata:", style="Stat.TLabel").grid(row=3, column=0, sticky="w", pady=(2,5), padx=5)
        ttk.Label(main_frame, text=f"{stats.get('most_studied', 'N/D')}", style="StatValue.TLabel").grid(row=3, column=1, sticky="e", pady=(2,5), padx=10)

        # --- Subject Details Frame ---
        details_frame = ttk.LabelFrame(container, text="Dettaglio per Materia")
        details_frame.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        columns = ("subject", "cards", "retention", "status")
        tree = ttk.Treeview(details_frame, columns=columns, show="headings")
        tree.heading("subject", text="Materia")
        tree.heading("cards", text="Nr. Carte")
        tree.heading("retention", text="Tasso Ritenzione")
        tree.heading("status", text="Stato")

        tree.column("subject", width=250, anchor='w')
        tree.column("cards", width=80, anchor='center')
        tree.column("retention", width=110, anchor='center')
        tree.column("status", width=100, anchor='center')

        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        subject_details = stats.get('subject_details', {})
        for subject, data in sorted(subject_details.items()):
            retention_str = f"{data.get('retention_rate', 0.0):.1f}%" if data.get('retention_rate') is not None else "N/D"
            tree.insert("", "end", values=(subject, data.get('card_count', 0), retention_str, data.get('status', 'In Corso')))

        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", expand=True, fill="both")

        # --- Leech Questions Frame ---
        leech_frame = ttk.LabelFrame(container, text="Domande Ostiche (Leeches)")
        leech_frame.pack(expand=True, fill='both', padx=10)

        leech_columns = ("subject", "question")
        leech_tree = ttk.Treeview(leech_frame, columns=leech_columns, show="headings")
        leech_tree.heading("subject", text="Materia")
        leech_tree.heading("question", text="Testo Domanda")
        leech_tree.column("subject", width=200, anchor='w')
        leech_tree.column("question", width=550, anchor='w')

        leech_scrollbar = ttk.Scrollbar(leech_frame, orient="vertical", command=leech_tree.yview)
        leech_tree.configure(yscrollcommand=leech_scrollbar.set)

        leech_questions = stats.get('leech_questions', [])
        for leech in sorted(leech_questions, key=lambda x: x['subject']):
            leech_tree.insert("", "end", values=(leech['subject'], leech['question_text']))

        leech_scrollbar.pack(side="right", fill="y")
        leech_tree.pack(side="left", expand=True, fill="both")

        # --- Close Button ---
        close_button = ttk.Button(container, text="Chiudi", command=self.destroy, style="Accent.TButton")
        close_button.pack(side='bottom', fill='x', padx=10, pady=(10,0), ipady=5)
