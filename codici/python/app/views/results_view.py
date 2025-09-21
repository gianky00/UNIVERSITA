import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from typing import List, Dict, Any, Callable

class ResultsView(Toplevel):
    def __init__(self, parent: tk.Tk, incorrect_answers: List[Dict[str, Any]], close_callback: Callable, title: str, summary: str):
        super().__init__(parent); self.protocol("WM_DELETE_WINDOW", close_callback)
        self.title(title); self.state('zoomed')
        style = ttk.Style(self)
        style.configure("Correct.TLabel", foreground="green", font=('Helvetica', 10, 'bold')); style.configure("Incorrect.TLabel", foreground="red", font=('Helvetica', 10, 'bold'))
        style.configure("Question.TLabel", font=('Helvetica', 10, 'bold')); style.configure("Summary.TLabel", font=('Helvetica', 12, 'bold'))
        main_frame = ttk.Frame(self, padding=10); main_frame.pack(fill="both", expand=True)
        ttk.Label(main_frame, text=summary, style="Summary.TLabel", wraplength=self.winfo_screenwidth() - 50, justify='center').pack(pady=10)
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)

        canvas = tk.Canvas(main_frame); scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")
        canvas.bind('<Configure>', lambda e: scrollable_frame.config(width=e.width))

        for item in incorrect_answers:
            frame = ttk.LabelFrame(scrollable_frame, text=f"Domanda {item['q_number']}", padding=10)

            wraplength = self.winfo_screenwidth() - 150
            ttk.Label(frame, text=item['q_text'], wraplength=wraplength, style="Question.TLabel").pack(anchor='w', pady=(5, 10), fill='x')
            ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=5)

            answer_frame_user = ttk.Frame(frame); ttk.Label(answer_frame_user, text="La tua risposta:").pack(side='left'); ttk.Label(answer_frame_user, text=item['user_answer'], wraplength=wraplength-100, style="Incorrect.TLabel").pack(side='left', padx=5); answer_frame_user.pack(anchor='w', fill='x')
            answer_frame_correct = ttk.Frame(frame); ttk.Label(answer_frame_correct, text="Risposta corretta:").pack(side='left'); ttk.Label(answer_frame_correct, text=item['correct_answer'] or "Non definita", wraplength=wraplength-100, style="Correct.TLabel").pack(side='left', padx=5); answer_frame_correct.pack(anchor='w', pady=(5,0), fill='x')

            ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=(10, 5))
            ttk.Label(frame, text="Tutte le opzioni:", font=('Helvetica', 10, 'bold')).pack(anchor='w', pady=(5, 5))
            options_container = ttk.Frame(frame); options_container.pack(fill='x', expand=True, anchor='w', padx=10)

            for option in item['options']:
                style = "TLabel"; prefix = "○ "
                if option == item['correct_answer']: style = "Correct.TLabel"; prefix = "✔ "
                elif option == item['user_answer']: style = "Incorrect.TLabel"; prefix = "✗ "
                option_label = ttk.Label(options_container, text=prefix + option, style=style, wraplength=wraplength-120); option_label.pack(anchor='w')

            copy_button = ttk.Button(frame, text="Copia testo per IA", command=lambda i=item: self._copy_for_ai(i)); copy_button.pack(pady=(10,0), anchor='e')

            frame.pack(pady=10, padx=10, fill='x', expand=True)

    def _copy_for_ai(self, item: Dict[str, Any]):
        text_to_copy = f"Domanda: {item['q_text']}\n\nOpzioni:\n"
        for option in item['options']: text_to_copy += f"- {option}\n"
        text_to_copy += f"\nRisposta corretta: {item['correct_answer'] or 'Non definita'}\n"
        text_to_copy += f"La tua risposta: {item['user_answer']}\n"
        self.clipboard_clear(); self.clipboard_append(text_to_copy)
        messagebox.showinfo("Copiato", "I dettagli della domanda sono stati copiati negli appunti.", parent=self)
