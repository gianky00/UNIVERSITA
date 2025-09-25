import tkinter as tk
from tkinter import ttk, Toplevel
from typing import List, Dict, Optional, Any, Callable
from PIL import Image, ImageTk

from app.models.question_model import Question

class PracticeView(Toplevel):
    MAX_OPTIONS = 10
    def __init__(self, parent: tk.Tk, close_callback: Callable[[], None], mode: str, image_update_callback: Callable[[], None]):
        super().__init__(parent)
        self.parent = parent; self.mode = mode; self.is_exam_mode = (mode == 'exam'); self.close_controller_callback = close_callback
        self.image_update_callback = image_update_callback
        self.protocol("WM_DELETE_WINDOW", self.on_close); self.title(f"Modalità: {mode.capitalize()}"); self.state('zoomed')
        self.img_ref, self._after_id = None, None; self.nav_buttons: List[ttk.Button] = []
        self._setup_styles(); self._setup_ui()
        self.bind("<Configure>", self._on_resize)
        self.bind("<KeyPress-Left>", self._handle_key_press); self.bind("<KeyPress-Right>", self._handle_key_press)
        if self.mode != 'review':
            self.bind("<KeyPress-1>", lambda e: self.select_option_by_key('1')); self.bind("<KeyPress-2>", lambda e: self.select_option_by_key('2'))
            self.bind("<KeyPress-3>", lambda e: self.select_option_by_key('3'))
        self.focus_set()

    def on_close(self):
        # Unbind events only from this window instance upon closing.
        self.unbind("<KeyPress-Left>")
        self.unbind("<KeyPress-Right>")
        if self.mode != 'review':
            self.unbind("<KeyPress-1>")
            self.unbind("<KeyPress-2>")
            self.unbind("<KeyPress-3>")
        self.close_controller_callback()

    def _setup_styles(self):
        style = ttk.Style(self)
        # Stili per i pulsanti di navigazione dell'esame
        style.configure("Answered.TButton", foreground="green", font=('Helvetica', 9, 'bold'))
        style.configure("Current.TButton", relief="sunken", foreground="blue", font=('Helvetica', 9, 'bold'))
        # Stile per la risposta corretta in modalità ripasso
        style.configure("CorrectAnswer.TLabel", foreground="blue", font=('Helvetica', 11, 'bold'))
        # Stili per il feedback immediato
        correct_bg = "#d4edda"; correct_fg = "#155724" # Verde
        incorrect_bg = "#f8d7da"; incorrect_fg = "#721c24" # Rosso
        style.configure("Correct.TFrame", background=correct_bg)
        style.configure("Correct.TLabel", background=correct_bg, foreground=correct_fg)
        style.configure("Correct.TRadiobutton", background=correct_bg)
        style.configure("Incorrect.TFrame", background=incorrect_bg)
        style.configure("Incorrect.TLabel", background=incorrect_bg, foreground=incorrect_fg)
        style.configure("Incorrect.TRadiobutton", background=incorrect_bg)
        # Stile per i pulsanti di valutazione SRS
        style.configure("Rate.TButton", font=('Helvetica', 10, 'bold'))

    def _setup_ui(self):
        root_frame = ttk.Frame(self, padding=10); root_frame.pack(expand=True, fill='both')
        self.timer_label = ttk.Label(root_frame, text="", font=("Helvetica", 14, "bold"), foreground="navy")
        if self.is_exam_mode: self.timer_label.pack(pady=(0, 10))
        content_frame = ttk.Frame(root_frame); content_frame.pack(expand=True, fill='both')
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        question_area = ttk.Frame(content_frame); question_area.grid(row=0, column=0, sticky="nsew")
        question_area.rowconfigure(1, weight=1)
        question_area.columnconfigure(0, weight=1)

        if self.is_exam_mode:
            content_frame.columnconfigure(1, weight=0) # Nav panel non si espande
            nav_container = ttk.Frame(content_frame); nav_container.grid(row=0, column=1, sticky="ns", padx=(10, 0))
            nav_canvas = tk.Canvas(nav_container, width=120); nav_scrollbar = ttk.Scrollbar(nav_container, orient="vertical", command=nav_canvas.yview)
            self.nav_panel = ttk.Frame(nav_canvas); self.nav_panel.bind("<Configure>", lambda e: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
            nav_canvas.create_window((0, 0), window=self.nav_panel, anchor="nw"); nav_canvas.configure(yscrollcommand=nav_scrollbar.set)
            nav_canvas.pack(side="left", fill="both", expand=True); nav_scrollbar.pack(side="right", fill="y")

        self.status_label = ttk.Label(question_area, text="", font=("Helvetica", 12)); self.status_label.pack(pady=(0, 10), fill='x')

        container = ttk.Frame(question_area); container.pack(expand=True, fill='both', pady=10)
        container.grid_rowconfigure(1, weight=1); container.grid_columnconfigure(0, weight=1)

        self.image_label = ttk.Label(container); self.image_label.grid(row=0, column=0, pady=10)

        frame_content = ttk.LabelFrame(container, text="Domanda", padding=20); frame_content.grid(row=1, column=0, sticky='nsew')
        frame_content.columnconfigure(0, weight=1)

        self.question_text_label = ttk.Label(frame_content, wraplength=100, font=('Helvetica', 12, 'bold'), justify='left'); self.question_text_label.pack(anchor='w', pady=(10, 20), fill='x')

        self.option_widgets: List[Dict[str, Any]] = []
        options_frame = ttk.Frame(frame_content); options_frame.pack(expand=True, fill='both', anchor='n')
        for _ in range(self.MAX_OPTIONS):
            option_frame = ttk.Frame(options_frame)
            radio = ttk.Radiobutton(option_frame); label = ttk.Label(option_frame, wraplength=100, font=('Helvetica', 11), justify='left')
            radio.pack(side='left', anchor='n', pady=2); label.pack(side='left', expand=True, fill='x', padx=5)
            self.option_widgets.append({'frame': option_frame, 'radio': radio, 'label': label})
        self.nav_frame = ttk.Frame(question_area); self.nav_frame.pack(side='bottom', fill='x', pady=(10, 0))
        self.nav_frame.columnconfigure((0, 1, 2), weight=1)
        self.prev_button = ttk.Button(self.nav_frame, text="<< Precedente"); self.prev_button.grid(row=0, column=0, sticky='ew', padx=5, ipady=5)
        self.submit_button = ttk.Button(self.nav_frame, text="Verifica", style="Accent.TButton"); self.submit_button.grid(row=0, column=1, sticky='ew', padx=5, ipady=5)
        self.next_button = ttk.Button(self.nav_frame, text="Successiva >>"); self.next_button.grid(row=0, column=2, sticky='ew', padx=5, ipady=5)
        self.feedback_frame = ttk.Frame(question_area); self.feedback_frame.columnconfigure((0,1,2,3), weight=1)
        self.srs_rate_buttons = {
            "non_la_sapevo": ttk.Button(self.feedback_frame, text="Non la sapevo (1)"), "difficile": ttk.Button(self.feedback_frame, text="Difficile (2)"),
            "medio": ttk.Button(self.feedback_frame, text="Medio (3)"), "facile": ttk.Button(self.feedback_frame, text="Facile (4)"),
        }
        for i, (rating, button) in enumerate(self.srs_rate_buttons.items()):
            button.grid(row=0, column=i, sticky='ew', padx=5, ipady=8); self.bind(f"<KeyPress-{i+1}>", lambda e, r=rating: self._rate_by_key(r))

    def _rate_by_key(self, rating: str):
        if self.feedback_frame.winfo_ismapped(): self.srs_rate_buttons[rating].invoke()
    def set_callbacks(self, prev_cb, next_cb, submit_cb, rate_cb):
        print("DEBUG: View.set_callbacks called")
        self.prev_button.config(command=prev_cb); self.next_button.config(command=next_cb); self.submit_button.config(command=submit_cb)
        for rating, button in self.srs_rate_buttons.items():
            print(f"DEBUG: View - Setting callback for rating button: {rating}")
            button.config(command=lambda r=rating: rate_cb(r))
        print("DEBUG: View.set_callbacks finished")

    def switch_to_srs_feedback(self, show: bool):
        print(f"DEBUG: View.switch_to_srs_feedback called with show={show}")
        if show:
            print("DEBUG: View - Hiding nav_frame, showing feedback_frame")
            self.nav_frame.pack_forget()
            self.feedback_frame.pack(side='bottom', fill='x', pady=(10, 0))
        else:
            print("DEBUG: View - Hiding feedback_frame, showing nav_frame")
            self.feedback_frame.pack_forget()
            self.nav_frame.pack(side='bottom', fill='x', pady=(10, 0))
        print("DEBUG: View.switch_to_srs_feedback finished")
    def setup_for_mode(self):
        if self.mode == 'review':
            self.submit_button.config(text="Mostra Risposta"); self.prev_button.grid_remove(); self.next_button.grid_remove()
            self.submit_button.grid(row=0, column=0, columnspan=3, sticky='ew')
            for widget in self.option_widgets: widget['radio'].config(state='disabled')
        else:
            self.submit_button.config(text="Verifica"); self.prev_button.grid(); self.next_button.grid(); self.submit_button.grid(row=0, column=1, columnspan=1)
            for widget in self.option_widgets:
                widget['radio'].config(state='normal')
                widget['label'].bind("<Button-1>", lambda e, r=widget['radio']: r.invoke()); widget['frame'].bind("<Button-1>", lambda e, r=widget['radio']: r.invoke())
    def create_navigation_panel(self, count: int, jump_callback: Callable[[int], None]):
        for widget in self.nav_panel.winfo_children(): widget.destroy(); self.nav_buttons.clear()
        for i in range(count):
            btn = ttk.Button(self.nav_panel, text=f"{i + 1}", command=lambda idx=i: jump_callback(idx)); btn.pack(fill='x', pady=2, padx=2); self.nav_buttons.append(btn)
    def update_navigation_panel(self, questions: List[Question], current_index: int):
        if not self.is_exam_mode: return
        for i, btn in enumerate(self.nav_buttons):
            q = questions[i]; style_name = "TButton"
            if q.user_answer.get(): style_name = "Answered.TButton"
            if i == current_index: style_name = "Current.TButton"
            btn.configure(style=style_name)
    def _on_resize(self, event: tk.Event):
        if not self.winfo_exists() or (self.winfo_width() < 100 or self.winfo_height() < 100): return
        if self._after_id: self.after_cancel(self._after_id)
        self._after_id = self.after(200, self.update_wraplength_and_image)

    def update_wraplength_and_image(self):
        if not self.winfo_exists(): return
        width = self.winfo_width(); nav_width = 150 if self.is_exam_mode else 0
        wraplength_value = max(300, width - nav_width - 100)
        self.question_text_label.config(wraplength=wraplength_value)
        for widget in self.option_widgets: widget['label'].config(wraplength=wraplength_value - 50)
        if self.image_update_callback:
            self.image_update_callback()

    def flash_answer_feedback(self, option_index: int, is_correct: bool):
        """Evidenzia brevemente la risposta selezionata cambiando lo stile dei widget."""
        if not (0 <= option_index < len(self.option_widgets)):
            return

        widgets = self.option_widgets[option_index]
        target_frame = widgets['frame']
        radio_button = widgets['radio']
        label_widget = widgets['label']

        feedback_style_prefix = "Correct" if is_correct else "Incorrect"

        # Applica i nuovi stili
        target_frame.configure(style=f"{feedback_style_prefix}.TFrame")
        radio_button.configure(style=f"{feedback_style_prefix}.TRadiobutton")
        label_widget.configure(style=f"{feedback_style_prefix}.TLabel")

        def clear_feedback():
            if target_frame.winfo_exists():
                # Ripristina gli stili predefiniti
                target_frame.configure(style="TFrame")
                radio_button.configure(style="TRadiobutton")
                label_widget.configure(style="TLabel")

        self.after(750, clear_feedback)

    def display_question(self, q: Question, status_text: str, image: Optional[ImageTk.PhotoImage]):
        self.status_label.config(text=status_text); self.question_text_label.config(text=q.text)
        self.image_label.config(image=image or ''); self.img_ref = image
        for i in range(self.MAX_OPTIONS):
            widget = self.option_widgets[i]
            if i < len(q.options):
                option_text = q.options[i]; widget['frame'].pack(anchor='w', fill='x', pady=4)
                widget['radio'].config(variable=q.user_answer, value=option_text); widget['label'].config(text=option_text, style="TLabel")
            else: widget['frame'].pack_forget()

    def show_correct_answer(self, correct_answer: str):
        print("DEBUG: View.show_correct_answer called")
        for widget in self.option_widgets:
            if widget['radio']['value'] == correct_answer:
                print(f"DEBUG: View - Highlighting correct answer: {correct_answer}")
                widget['label'].config(style="CorrectAnswer.TLabel")
        print("DEBUG: View.show_correct_answer finished")
    def update_navigation_buttons(self, prev_enabled: bool, next_enabled: bool):
        self.prev_button.config(state='normal' if prev_enabled else 'disabled'); self.next_button.config(state='normal' if next_enabled else 'disabled')
    def select_option_by_key(self, key: str):
        if not self.winfo_viewable(): return
        try:
            index = int(key) - 1
            if self.focus_get() and isinstance(self.focus_get(), (ttk.Entry, tk.Text)): return
            if 0 <= index < len(self.option_widgets):
                radio = self.option_widgets[index]['radio']
                if radio.winfo_ismapped(): radio.invoke()
        except (ValueError, IndexError): pass
    def _handle_key_press(self, event: tk.Event):
        # This method is bound to the Toplevel, so it only fires when it has focus.
        if self.nav_frame.winfo_ismapped():
            if event.keysym == "Left" and self.prev_button['state'] == 'normal': self.prev_button.invoke()
            elif event.keysym == "Right" and self.next_button['state'] == 'normal': self.next_button.invoke()
    def update_timer(self, time_str: str): self.timer_label.config(text=time_str)
