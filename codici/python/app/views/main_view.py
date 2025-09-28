import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict
from ttkthemes import ThemedTk

class MainView(ThemedTk):
    """Dashboard principale dell'applicazione."""
    def __init__(self, start_callback: Callable[[str], None], settings_callback: Callable[[], None], analysis_callback: Callable[[], None], tools_callbacks: dict):
        super().__init__(theme="arc")
        self.title("Flashcard SRS Dashboard")
        self.geometry("650x450")

        self.start_callback = start_callback
        self.settings_callback = settings_callback
        self.analysis_callback = analysis_callback

        self._configure_styles()
        self._create_menubar(tools_callbacks)
        self._create_widgets()

    def _configure_styles(self):
        style = ttk.Style(self)
        BG_COLOR = "#ECECEC"
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR)
        style.configure("Accent.TButton", font=("Helvetica", 11, "bold"))
        style.configure("TLabelFrame", padding=15, background=BG_COLOR)
        style.configure("TLabelFrame.Label", font=("Helvetica", 12, "bold"), background=BG_COLOR)
        style.configure("StatValue.TLabel", font=("Helvetica", 18, "bold"), foreground="#007BFF", background=BG_COLOR)
        style.configure("Suggestion.TLabel", font=("Helvetica", 10, "italic"), background=BG_COLOR)

    def _create_menubar(self, tools_callbacks: dict):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Strumenti", menu=tools_menu)
        tools_menu.add_command(label="Unisci PDF...", command=tools_callbacks['pdf_merger'])
        tools_menu.add_command(label="Formatta Testo Paniere...", command=tools_callbacks['text_formatter'])
        tools_menu.add_separator()
        tools_menu.add_command(label="Crea Ritagli Immagine...", command=tools_callbacks['image_snipper'])

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(expand=True, fill='both')
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # --- Titolo ---
        ttk.Label(main_frame, text="Dashboard di Studio", font=("Helvetica", 18, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # --- Pannello Sinistro: Statistiche e Suggerimenti ---
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=1, column=0, sticky="nswe", padx=(0, 10))
        left_panel.rowconfigure(1, weight=1)

        # Statistiche
        stats_frame = ttk.LabelFrame(left_panel, text="Le tue Statistiche")
        stats_frame.pack(fill="x", expand=True)
        self.streak_var = tk.StringVar(value="0 giorni")
        self.retention_var = tk.StringVar(value="N/D")
        ttk.Label(stats_frame, text="🔥 Serie di Studio:", font=("Helvetica", 11)).pack(anchor="w", padx=5)
        ttk.Label(stats_frame, textvariable=self.streak_var, style="StatValue.TLabel").pack(anchor="w", padx=5, pady=(0,10))
        ttk.Label(stats_frame, text="🎯 Tasso di Ritenzione:", font=("Helvetica", 11)).pack(anchor="w", padx=5)
        ttk.Label(stats_frame, textvariable=self.retention_var, style="StatValue.TLabel").pack(anchor="w", padx=5)

        # Suggerimenti
        suggestion_frame = ttk.LabelFrame(left_panel, text="Suggerimenti")
        suggestion_frame.pack(fill="x", expand=True, pady=(20, 0))
        self.suggestion_var = tk.StringVar(value="Inizia una sessione di ripasso per vedere i suggerimenti.")
        ttk.Label(suggestion_frame, textvariable=self.suggestion_var, wraplength=250, justify="left", style="Suggestion.TLabel").pack(padx=5, pady=5)

        # --- Pannello Destro: Azioni ---
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky="nswe", padx=(10, 0))
        right_panel.rowconfigure(3, weight=1)

        actions_frame = ttk.LabelFrame(right_panel, text="Sessioni di Studio")
        actions_frame.pack(fill="both", expand=True)

        help_button = ttk.Button(actions_frame, text="?", command=self._show_study_modes_help, width=2)
        help_button.place(relx=1.0, x=-5, y=-8) # Posiziona nell'angolo in alto a destra

        self.review_button = ttk.Button(actions_frame, text="Studio SRS", command=lambda: self.start_callback('review'), style="Accent.TButton", state='disabled')
        self.review_button.pack(expand=True, fill="both", ipady=15, padx=10, pady=(20, 10)) # Aggiunto pady top per fare spazio

        self.exam_button = ttk.Button(actions_frame, text="Modalità Esame", command=lambda: self.start_callback('exam'))
        self.exam_button.pack(expand=True, fill="both", ipady=15, padx=10, pady=5)

        self.practice_button = ttk.Button(actions_frame, text="Esercitazione Libera", command=lambda: self.start_callback('practice'))
        self.practice_button.pack(expand=True, fill="both", ipady=15, padx=10, pady=10)

        # --- Pulsanti in basso ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(20,0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)

        ttk.Button(bottom_frame, text="Analisi Performance", command=self.analysis_callback).pack(side='left', expand=True, fill='x', ipady=8, padx=(0,5))
        ttk.Button(bottom_frame, text="Impostazioni", command=self.settings_callback).pack(side='left', expand=True, fill='x', ipady=8, padx=(5,0))

    def _show_study_modes_help(self):
        """Mostra una finestra di dialogo con la spiegazione delle modalità di studio."""
        help_text = (
            "Ecco una spiegazione delle diverse modalità di studio:\n\n"
            "• Studio SRS (Spaced Repetition System):\n"
            "Questa è la modalità di studio principale. Il sistema ti presenta le domande a intervalli di tempo crescenti per massimizzare la memorizzazione a lungo termine. Si concentra sulle domande che hai trovato difficili e introduce nuove domande gradualmente.\n\n"
            "• Modalità Esame:\n"
            "Simula una sessione d'esame. Ti verranno presentate tutte le domande della materia selezionata in ordine casuale, senza feedback immediato. Alla fine, otterrai un punteggio complessivo.\n\n"
            "• Esercitazione Libera:\n"
            "Ti permette di ripassare tutte le domande di una materia in modo sequenziale, senza l'algoritmo SRS. Utile per una revisione rapida o per familiarizzare con il materiale."
        )
        messagebox.showinfo("Guida Modalità di Studio", help_text, parent=self)

    def update_dashboard(self, stats: Dict[str, any]):
        """Aggiorna i widget della dashboard con le nuove statistiche."""
        # Aggiorna il pulsante di ripasso
        review_count = stats.get("review_count", 0)
        if review_count > 0:
            self.review_button.config(text=f"Studio SRS ({review_count})", state='normal')
        else:
            self.review_button.config(text="Studio SRS", state='disabled')

        # Aggiorna le statistiche
        streak = stats.get("streak", 0)
        self.streak_var.set(f"{streak} giorni")

        retention = stats.get("retention_rate", 0.0)
        self.retention_var.set(f"{retention:.1f}%" if retention is not None else "N/D")

        # Aggiorna i suggerimenti
        suggestion = stats.get("suggestion", "Nessun suggerimento per ora.")
        self.suggestion_var.set(suggestion)
