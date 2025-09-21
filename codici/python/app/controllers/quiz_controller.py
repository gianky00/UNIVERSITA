import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import json
import time
import datetime
import random
from pathlib import Path
from typing import List, Dict, Optional, Any

from PIL import Image, ImageTk

from app.models.question_model import Question
from app.services.settings_manager import SettingsManager
from app.services.srs_manager import SRSManager
from app.services.app_data_manager import AppDataManager
from app.services.text_processing import TextFileParser, SimilarityAnalyser
from app.views.main_view import MainView
from app.views.practice_view import PracticeView
from app.views.results_view import ResultsView
from app.views.dialogs import SubjectSelectionDialog, LoadingView
from app.views.settings_view import SettingsView
from app.views.analysis_view import AnalysisView
from tools import image_snipper, text_formatter, pdf_merger


class QuizController:
    def __init__(self, root: MainView, settings_manager: SettingsManager):
        self.root = root
        self.settings_manager = settings_manager
        self.app_data_manager = AppDataManager(self.settings_manager)
        self.srs_manager: Optional[SRSManager] = None
        self.current_subject = ""
        self.all_questions: List[Question] = []
        self.active_questions: List[Question] = []
        self.image_base_path: Optional[Path] = None
        self.current_question_index = 0
        self.image_cache: Dict[Path, Image.Image] = {}
        self.timer_id: Optional[str] = None
        self.current_mode = ""
        self.practice_view: Optional[PracticeView] = None
        self.results_view: Optional[ResultsView] = None
        self.question_start_time = 0.0
        self.question_start_time = 0.0
        self.srs_session_results: List[bool] = []

    def update_dashboard_and_srs_status(self):
        """Aggiorna la dashboard con statistiche fresche e lo stato dei ripassi."""
        subjects = self.settings_manager.get_subjects(status_filter="In Corso")
        total_due = 0
        next_exam_date = None
        next_exam_subj = ""

        for subject in subjects:
            data = self.settings_manager.get_subject_data(subject)
            try:
                exam_date = datetime.datetime.strptime(data.get("exam_date", ""), '%d/%m/%Y').date()
                if not next_exam_date or exam_date < next_exam_date:
                    next_exam_date = exam_date
                    next_exam_subj = subject
            except (ValueError, TypeError):
                pass
            srs_manager = SRSManager(subject, None, 1.0, self.app_data_manager, self.settings_manager)
            total_due += len(srs_manager.get_due_questions())

        suggestion = f"Prossimo esame: {next_exam_subj}." if next_exam_subj else "Nessun esame imminente. Ottimo per un ripasso generale!"
        if total_due > 0:
            suggestion += f"\nCi sono {total_due} carte da ripassare."

        stats = {
            "review_count": total_due,
            "streak": self.app_data_manager.get_current_streak(),
            "retention_rate": self.app_data_manager.get_retention_rate(),
            "suggestion": suggestion
        }
        self.root.update_dashboard(stats)

    def open_settings(self):
        SettingsView(self.root, self.settings_manager)
        self.update_dashboard_and_srs_status()

    def open_analysis(self):
        stats = self.app_data_manager.get_overall_stats()
        AnalysisView(self.root, stats)

    # --- Tool Launchers ---
    def launch_pdf_merger(self):
        pdf_merger.main(self.root)

    def launch_text_formatter(self):
        text_formatter.main(self.root)

    def launch_image_snipper(self):
        image_snipper.main(self.root)

    def start(self, mode: str):
        self.current_mode = mode
        self._select_subject_and_begin_analysis()

    def _select_subject_and_begin_analysis(self):
        subjects = self.settings_manager.get_subjects(status_filter="In Corso")
        if not subjects:
            messagebox.showerror("Errore", "Nessuna materia 'In Corso'. Vai in Impostazioni.")
            return

        dialog = SubjectSelectionDialog(self.root, "Selezione Materia", subjects)
        subject = dialog.result
        if not subject:
            return

        self.current_subject = subject
        data = self.settings_manager.get_subject_data(subject)

        txt_path_str = data.get('txt_path')
        if not txt_path_str or not Path(txt_path_str).exists():
            messagebox.showerror("Errore Percorso", f"File Quiz non trovato per {subject}.\nControlla le Impostazioni.")
            return

        threading.Thread(target=self._background_analysis_and_setup, args=(data,), daemon=True).start()

    def _background_analysis_and_setup(self, data: Dict[str, Any]):
        loading_view = LoadingView(self.root)
        self.root.update_idletasks()

        txt_path = Path(data.get('txt_path'))
        self.all_questions = TextFileParser(txt_path).parse()

        exam_date = None
        try: exam_date = datetime.datetime.strptime(data.get("exam_date", ""), '%d/%m/%Y').date()
        except ValueError: pass
        modifier = data.get("interval_modifier", 1.0)
        self.srs_manager = SRSManager(self.current_subject, exam_date, modifier, self.app_data_manager, self.settings_manager)

        cache_path = Path(f"{data.get('txt_path')}.cache.json")

        try:
            if cache_path.exists() and cache_path.stat().st_mtime > txt_path.stat().st_mtime:
                cached_data = json.loads(cache_path.read_text(encoding='utf-8'))
                similarity_map = {k: set(v) for k, v in cached_data.items()}
            else:
                raise FileNotFoundError
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            analyser = SimilarityAnalyser(self.all_questions)
            similarity_map = analyser.compute_similarity_map()
            cache_path.write_text(json.dumps({k: list(v) for k, v in similarity_map.items()}, indent=2), encoding='utf-8')

        if self.srs_manager: self.srs_manager.similarity_map = similarity_map
        img_path_str = data.get('img_path')
        self.image_base_path = Path(img_path_str) if img_path_str and Path(img_path_str).exists() else None

        self.root.after(0, loading_view.stop)
        self.root.after(0, self._finalize_start)

    def _finalize_start(self):
        self.active_questions = []
        if self.current_mode == 'review':
            if not self.srs_manager: return
            self.srs_session_results = []
            self.active_questions = self.srs_manager.get_due_questions()
            if not self.active_questions:
                leech_questions = self.srs_manager.get_leech_questions()
                if leech_questions:
                    msg = "Nessuna domanda da ripassare oggi.\n\nTuttavia, hai difficoltà persistenti con queste domande (leeches). Considera di studiarle da una fonte diversa:\n\n"
                    for q in leech_questions[:5]: msg += f"- {q.text[:80]}...\n"
                    messagebox.showwarning("Domande Ostiche Rilevate", msg)
                else: messagebox.showinfo("Studio SRS", f"Nessuna domanda da ripassare per {self.current_subject}.\nOttimo lavoro!")
                return
            random.shuffle(self.active_questions)
        else:
            if not self.all_questions:
                messagebox.showwarning("Attenzione", "Nessuna domanda trovata. Controlla il file .txt e il segnalibro.")
                return
            if self.current_mode == 'exam':
                num, duration = self._ask_exam_settings(len(self.all_questions))
                if num == 0: return
                random.shuffle(self.all_questions); self.active_questions = self.all_questions[:num]
            else: # Practice
                self.active_questions = self.all_questions
                random.shuffle(self.active_questions)
        if self.active_questions:
            self._start_quiz_ui()

    def _ask_exam_settings(self, available_q_count: int) -> (int, int):
        if available_q_count < 24:
            messagebox.showwarning("Attenzione", f"Non ci sono abbastanza domande per un esame (minimo 24, trovate {available_q_count}).")
            return 0, 0
        num = simpledialog.askinteger("Modalità Esame", "Quante domande? (multipli di 24)", initialvalue=24, minvalue=24, maxvalue=available_q_count)
        if num is None: return 0, 0
        if num > 0 and num % 24 == 0: return num, (num // 24) * 60
        messagebox.showwarning("Input non valido", "Il numero deve essere un multiplo di 24."); return 0, 0

    def _start_quiz_ui(self, timer_duration: int = 0):
        self.root.withdraw(); self.current_question_index = 0
        self.practice_view = PracticeView(self.root, self.on_practice_close, self.current_mode, self.display_current_question)
        self.practice_view.set_callbacks(self.prev_question, self.next_question, self.submit_or_show_answer, self.rate_srs_question)
        self.practice_view.setup_for_mode()
        if self.current_mode == 'exam':
            self.practice_view.create_navigation_panel(len(self.active_questions), self.jump_to_question)
            if timer_duration > 0: self._start_timer(timer_duration)
        if self.image_base_path: threading.Thread(target=self._image_loader_worker, daemon=True).start()
        self.display_current_question()

    def _start_timer(self, duration_minutes: int):
        self.end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes); self._update_timer_display()
    def _update_timer_display(self):
        if not self.practice_view or not self.practice_view.winfo_exists(): return
        remaining = self.end_time - datetime.datetime.now()
        if remaining.total_seconds() <= 0:
            self.practice_view.update_timer("Tempo Scaduto!")
            messagebox.showinfo("Tempo Scaduto", "Il tempo è terminato. La prova sarà verificata.")
            self.submit_or_show_answer(auto_submit=True)
        else:
            self.practice_view.update_timer(f"Tempo Rimanente: {str(remaining).split('.')[0]}"); self.timer_id = self.root.after(1000, self._update_timer_display)
    def _stop_timer(self):
        if self.timer_id: self.root.after_cancel(self.timer_id); self.timer_id = None
    def _image_loader_worker(self):
        if not self.image_base_path: return
        questions_to_load = self.active_questions if self.active_questions else self.all_questions
        for q in questions_to_load:
            if q.image_path:
                full_path = self.image_base_path / q.image_path
                if full_path not in self.image_cache and full_path.exists():
                    try: img = Image.open(full_path); img.load(); self.image_cache[full_path] = img
                    except Exception as e: print(f"Errore caricamento immagine {full_path}: {e}")
    def get_resized_image(self) -> Optional[ImageTk.PhotoImage]:
        if not self.practice_view or not self.practice_view.winfo_exists() or not self.active_questions: return None
        q = self.active_questions[self.current_question_index]
        if not q.image_path or not self.image_base_path: return None
        pil_image = self.image_cache.get(self.image_base_path / q.image_path)
        if not pil_image: return None
        try:
            max_h = self.practice_view.winfo_height() * 0.4; max_w = self.practice_view.winfo_width() * 0.8
            if max_h < 100 or max_w < 100: return None
            img_copy = pil_image.copy(); w, h = img_copy.size; ratio = min(max_w / w, max_h / h)
            if ratio < 1: img_copy = img_copy.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img_copy)
        except Exception: return None

    def display_current_question(self):
        if not self.practice_view or not self.practice_view.winfo_exists() or not self.active_questions: return
        q = self.active_questions[self.current_question_index]
        status = f"Domanda {self.current_question_index + 1} di {len(self.active_questions)}"; image = self.get_resized_image()
        self.practice_view.display_question(q, status, image)
        self.practice_view.update_navigation_buttons(self.current_question_index > 0, self.current_question_index < len(self.active_questions) - 1)
        if self.current_mode == 'exam': self.practice_view.update_navigation_panel(self.active_questions, self.current_question_index)
        self.practice_view.switch_to_srs_feedback(False)
        if self.current_mode != 'review':
            for opt_radio in self.practice_view.option_widgets: opt_radio['radio'].config(command=self.on_answer_selected)
        self.question_start_time = time.monotonic()

    def on_answer_selected(self):
        q = self.active_questions[self.current_question_index]
        q.time_taken = time.monotonic() - self.question_start_time

        selected_answer = q.user_answer.get()
        if not selected_answer:
            return

        is_correct = (selected_answer == q.correct_answer)

        # Trova l'indice dell'opzione selezionata per il feedback visivo
        try:
            option_index = q.options.index(selected_answer)
            if self.practice_view:
                self.practice_view.flash_answer_feedback(option_index, is_correct)
        except (ValueError, IndexError):
            pass # L'opzione selezionata non è stata trovata, non dare feedback

    def jump_to_question(self, index: int): self.current_question_index = index; self.display_current_question()
    def next_question(self):
        if self.current_question_index < len(self.active_questions) - 1:
            self.current_question_index += 1; self.display_current_question()
        elif self.current_mode == 'review': self.on_practice_close(show_final_message=True)
    def prev_question(self):
        if self.current_question_index > 0: self.current_question_index -= 1; self.display_current_question()

    def submit_or_show_answer(self, auto_submit: bool = False):
        if self.current_mode == 'review':
            q = self.active_questions[self.current_question_index]
            self.practice_view.show_correct_answer(q.correct_answer); self.practice_view.switch_to_srs_feedback(True)
        else:
            if not auto_submit and not messagebox.askyesno("Conferma", "Sei sicuro di voler terminare?"): return
            self._stop_timer()

            incorrect_answers = [q for q in self.active_questions if q.user_answer.get() != q.correct_answer]

            newly_leeches = []
            if self.srs_manager:
                for q in incorrect_answers:
                    if self.srs_manager.add_or_update_from_exam(q): newly_leeches.append(q)

            if not incorrect_answers:
                messagebox.showinfo("Risultato", "Congratulazioni! Sessione completata senza errori.")
                return self.on_practice_close()

            title, summary = "Riepilogo Sessione", ""
            if self.current_mode == 'exam':
                total = len(self.active_questions); correct_count = total - len(incorrect_answers)
                passing_score = (total / 24) * 18
                title = "Esame Superato" if correct_count >= passing_score else "Esame NON Superato"
                summary = f"Punteggio: {correct_count}/{total} (Soglia superamento: {passing_score:.1f})"

            if newly_leeches:
                leech_text = "\n\nATTENZIONE: Le seguenti domande si sono rivelate ostiche. Studiale con più attenzione:\n"
                for q in newly_leeches: leech_text += f"- {q.text[:80]}...\n"
                summary += leech_text

            incorrect_display_data = [{"q_number": q.number, "q_text": q.text, "user_answer": q.user_answer.get() or "Nessuna risposta", "correct_answer": q.correct_answer, "options": q.options} for q in incorrect_answers]

            if self.practice_view: self.practice_view.withdraw()
            self.results_view = ResultsView(self.root, incorrect_display_data, self.on_results_close, title, summary)

    def rate_srs_question(self, rating: str):
        q = self.active_questions[self.current_question_index]
        self.srs_session_results.append(rating != "non_la_sapevo")
        if self.srs_manager:
            if self.srs_manager.update_after_review(q, rating, q.time_taken):
                messagebox.showwarning("Attenzione: Domanda Ostica!", f"Continui ad avere difficoltà con questa domanda. Prova a studiarla da una fonte diversa.\n\n- {q.text[:100]}...")
        self.next_question()

    def on_practice_close(self, show_final_message: bool = False):
        self._stop_timer()
        if self.practice_view: self.practice_view.destroy(); self.practice_view = None
        if show_final_message and self.srs_manager:
            leech_questions = self.srs_manager.get_leech_questions()
            # La logica di ritenzione è ora gestita globalmente tramite AppDataManager
            if leech_questions:
                msg = "Sessione di ripasso completata!\n\nATTENZIONE: Hai difficoltà persistenti con queste domande (leeches). Considera di studiarle da una fonte diversa:\n\n"
                for q in leech_questions[:5]: msg += f"- {q.text[:80]}...\n"
                messagebox.showwarning("Domande Ostiche Rilevate", msg)
            else: messagebox.showinfo("Fine Sessione", "Hai completato tutte le domande da ripassare per oggi!")
        self.root.deiconify(); self.update_dashboard_and_srs_status()

    def on_results_close(self):
        if self.results_view: self.results_view.destroy(); self.results_view = None
        if self.practice_view: self.practice_view.destroy(); self.practice_view = None # Clean up practice view as well
        self.root.deiconify(); self.update_dashboard_and_srs_status()
