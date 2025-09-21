import tkinter as tk
from tkinter import ttk
from typing import Callable
from ttkthemes import ThemedTk

class MainView(ThemedTk):
    """Finestra principale di avvio con le modalità."""
    def __init__(self, start_callback: Callable[[str], None], settings_callback: Callable[[], None], tools_callbacks: dict):
        super().__init__(theme="arc")
        self.title("Quiz Loader"); self.geometry("550x300")

        # --- Creazione Menu Bar ---
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # --- Menu Strumenti ---
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Strumenti", menu=tools_menu)
        tools_menu.add_command(label="Unisci PDF...", command=tools_callbacks['pdf_merger'])
        tools_menu.add_command(label="Formatta Testo Paniere...", command=tools_callbacks['text_formatter'])
        tools_menu.add_separator()
        tools_menu.add_command(label="Crea Ritagli Immagine...", command=tools_callbacks['image_snipper'])

        style = ttk.Style(self); style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        main_frame = ttk.Frame(self, padding=20); main_frame.pack(expand=True, fill='both')
        ttk.Label(main_frame, text="Quiz Loader", font=("Helvetica", 16, "bold")).pack(pady=10)
        self.info_label = ttk.Label(main_frame, text="Seleziona una modalità per iniziare:", font=("Helvetica", 11)); self.info_label.pack(pady=(10, 15))
        button_frame = ttk.Frame(main_frame); button_frame.pack(expand=True, fill='x', pady=5)
        ttk.Button(button_frame, text="Esercitazione", command=lambda: start_callback('practice')).pack(side='left', expand=True, fill='x', padx=5, ipady=10)
        self.exam_button = ttk.Button(button_frame, text="Esame", command=lambda: start_callback('exam')); self.exam_button.pack(side='left', expand=True, fill='x', padx=5, ipady=10)
        self.review_button = ttk.Button(button_frame, text="Studio SRS", command=lambda: start_callback('review'), state='disabled'); self.review_button.pack(side='left', expand=True, fill='x', padx=5, ipady=10)
        ttk.Button(main_frame, text="Impostazioni", command=settings_callback).pack(side='bottom', fill='x', pady=(10,0), ipady=5)

    def update_review_button(self, count: int, next_exam_info: str):
        if count > 0: self.review_button.config(text=f"Studio SRS ({count})", state='normal')
        else: self.review_button.config(text="Studio SRS", state='disabled')
        self.info_label.config(text=next_exam_info)
