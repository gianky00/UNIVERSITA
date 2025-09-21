import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, simpledialog
from ttkthemes import ThemedTk
from PIL import Image, ImageTk
import json
import re
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Set
import random
import datetime
import collections
import math

# --- MODELLO DATI (Data Models) ---

class Question:
    """Rappresenta una singola domanda del quiz."""
    def __init__(self, number: str, text: str, options: List[str], correct_answer: Optional[str], image_path: Optional[Path] = None):
        self.id = text.strip()
        self.number = number
        self.text = text
        self.options = options
        self.correct_answer = correct_answer
        self.image_path = image_path
        self.user_answer = tk.StringVar(value="")
        self.time_taken = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number, "text": self.text, "options": self.options,
            "image_path": str(self.image_path) if self.image_path else None,
            "correct_answer": self.correct_answer
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        image_path = Path(data["image_path"]) if data["image_path"] and data["image_path"] != "None" else None
        return cls(data["number"], data["text"], data["options"], data["correct_answer"], image_path)

# --- SISTEMA DI RIPETIZIONE DILAZIONATA (SRS) ---

class SRSItem:
    """Rappresenta una domanda nel sistema SRS, con i suoi metadati di studio."""
    def __init__(self, question: Question, srs_level: int = 0, next_review_date: Optional[datetime.date] = None, lapses: int = 0):
        self.question = question
        self.srs_level = srs_level
        self.next_review_date = next_review_date or (datetime.date.today() + datetime.timedelta(days=1))
        self.lapses = lapses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question.to_dict(), "srs_level": self.srs_level,
            "next_review_date": self.next_review_date.isoformat(), "lapses": self.lapses
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SRSItem':
        question = Question.from_dict(data["question"])
        return cls(question, data["srs_level"], datetime.date.fromisoformat(data["next_review_date"]), data.get("lapses", 0))

class SRSManager:
    """Gestisce la logica del deck di studio SRS, con calibrazione dinamica e analisi di interferenza."""
    SHORT_INTERVALS = [1, 2, 4, 7, 12, 20, 30]
    MAX_INTERVAL = 30
    LEECH_THRESHOLD = 6

    def __init__(self, subject: str, exam_date: Optional[datetime.date], interval_modifier: float):
        self.subject = subject
        self.filepath = Path(f"{self.subject.replace(' ', '_').lower()}_srs_deck.json")
        self.deck: Dict[str, SRSItem] = self._load()
        self.exam_date = exam_date
        self.interval_modifier = interval_modifier
        self.similarity_map: Dict[str, Set[str]] = collections.defaultdict(set)

    def _load(self) -> Dict[str, SRSItem]:
        if not self.filepath.exists(): return {}
        try:
            data = json.loads(self.filepath.read_text(encoding='utf-8'))
            return {item_id: SRSItem.from_dict(item_data) for item_id, item_data in data.items()}
        except (json.JSONDecodeError, TypeError): return {}

    def save(self):
        data_to_save = {item_id: item.to_dict() for item_id, item in self.deck.items()}
        self.filepath.write_text(json.dumps(data_to_save, indent=2), encoding='utf-8')
    
    def get_due_questions(self) -> List[Question]:
        today = datetime.date.today()
        due_items = [item for item in self.deck.values() if item.next_review_date <= today and item.lapses < self.LEECH_THRESHOLD]
        final_due_questions = []
        processed_ids = set()
        for item in sorted(due_items, key=lambda x: x.next_review_date):
            if item.question.id not in processed_ids:
                final_due_questions.append(item.question)
                processed_ids.add(item.question.id)
                related_ids = self.similarity_map.get(item.question.id, set())
                for related_id in related_ids:
                    if related_id in self.deck and related_id not in processed_ids and self.deck[related_id].next_review_date <= today + datetime.timedelta(days=2):
                        final_due_questions.append(self.deck[related_id].question)
                        processed_ids.add(related_id)
        return final_due_questions

    def get_leech_questions(self) -> List[Question]:
         return [item.question for item in self.deck.values() if item.lapses >= self.LEECH_THRESHOLD]

    def add_or_update_from_exam(self, question: Question) -> bool:
        item = self.deck.get(question.id)
        if item:
            item.srs_level = 0; item.lapses += 1
            item.next_review_date = datetime.date.today() + datetime.timedelta(days=1)
        else:
            item = SRSItem(question)
            self.deck[question.id] = item
        self.save()
        return item.lapses >= self.LEECH_THRESHOLD

    def update_after_review(self, question: Question, rating: str, time_taken: float) -> bool:
        if question.id not in self.deck: return False
        item = self.deck[question.id]
        if rating == "non_la_sapevo":
            item.lapses += 1; item.srs_level = 0
            new_interval_days = self.SHORT_INTERVALS[0]
        else:
            ease_factors = {"difficile": 0.9, "medio": 1.0, "facile": 1.25}
            time_factors = {"veloce": 1.15, "fluida": 1.0, "lenta": 0.85}
            if time_taken < 7.0: time_cat = "veloce"
            elif time_taken < 18.0: time_cat = "fluida"
            else: time_cat = "lenta"
            ease_factor = ease_factors[rating]; time_factor = time_factors[time_cat]
            if item.srs_level < len(self.SHORT_INTERVALS) - 1: item.srs_level += 1
            new_interval_days = self.SHORT_INTERVALS[item.srs_level] * ease_factor * time_factor
        urgency_factor = 1.0
        if self.exam_date:
            days_to_exam = (self.exam_date - datetime.date.today()).days
            if 0 < days_to_exam <= 21: urgency_factor = 0.4 + 0.6 * (days_to_exam / 21)
            elif days_to_exam <= 0: urgency_factor = 0.1
        final_interval_days = max(1, int(round(new_interval_days * urgency_factor * self.interval_modifier)))
        final_interval_days = min(final_interval_days, self.MAX_INTERVAL)
        item.next_review_date = datetime.date.today() + datetime.timedelta(days=final_interval_days)
        self.save()
        return item.lapses >= self.LEECH_THRESHOLD

# --- ANALISI NLP E SIMILARITA' ---

class SimilarityAnalyser:
    ITALIAN_STOP_WORDS = set(['a', 'adesso', 'ai', 'al', 'alla', 'allo', 'allora', 'altre', 'altri', 'altro', 'anche', 'ancora', 'avere', 'aveva', 'avevano', 'c', 'che', 'chi', 'ci', 'come', 'con', 'contro', 'cui', 'da', 'dagli', 'dai', 'dal', 'dall', 'dalla', 'dalle', 'dallo', 'de', 'degli', 'dei', 'del', 'dell', 'della', 'delle', 'dello', 'dentro', 'di', 'dov', 'dove', 'e', 'ed', 'era', 'erano', 'essere', 'fa', 'fino', 'fra', 'fu', 'furono', 'gli', 'ha', 'hanno', 'hai', 'ho', 'i', 'il', 'in', 'io', 'la', 'le', 'lei', 'li', 'lo', 'loro', 'lui', 'ma', 'me', 'mi', 'mia', 'mie', 'miei', 'mio', 'ne', 'negli', 'nei', 'nel', 'nell', 'nella', 'nelle', 'nello', 'noi', 'non', 'nostra', 'nostre', 'nostri', 'nostro', 'o', 'ogni', 'per', 'perche', 'perché', 'piu', 'più', 'quale', 'quando', 'quanta', 'quante', 'quanti', 'quanto', 'quella', 'quelle', 'quelli', 'quello', 'questa', 'queste', 'questi', 'questo', 're', 'se', 'sei', 'senza', 'si', 'sia', 'siamo', 'siete', 'sono', 'sta', 'stata', 'state', 'stati', 'stato', 'su', 'sua', 'sue', 'sui', 'suo', 'tra', 'tu', 'tua', 'tue', 'tui', 'tuo', 'un', 'una', 'uno', 'vi', 'voi', 'vostra', 'vostre', 'vostri', 'vostro'])
    SIMILARITY_THRESHOLD = 0.35

    def __init__(self, questions: List[Question]):
        self.questions = questions
        self.question_map = {q.id: q for q in questions}

    def _preprocess(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        return [word for word in words if word not in self.ITALIAN_STOP_WORDS]

    def _calculate_cosine_similarity(self, vec1: Dict, vec2: Dict) -> float:
        intersection = set(vec1.keys()) & set(vec2.keys())
        dot_product = sum(vec1[x] * vec2[x] for x in intersection)
        sum_sq_vec1 = sum(val**2 for val in vec1.values())
        sum_sq_vec2 = sum(val**2 for val in vec2.values())
        magnitude = math.sqrt(sum_sq_vec1) * math.sqrt(sum_sq_vec2)
        return dot_product / magnitude if magnitude != 0 else 0

    def compute_similarity_map(self) -> Dict[str, List[str]]:
        docs = {q.id: self._preprocess(q.text + " " + " ".join(q.options)) for q in self.questions}
        vocab = set(word for words in docs.values() for word in words)
        if not vocab: return {}
        num_docs = len(docs)
        idf = {word: math.log(num_docs / (1 + sum(1 for doc_words in docs.values() if word in doc_words))) for word in vocab}
        
        tfidf_vectors = {}
        for doc_id, words in docs.items():
            term_counts = collections.Counter(words)
            total_terms = len(words)
            if total_terms == 0: continue
            vector = {word: (count / total_terms) * idf[word] for word, count in term_counts.items()}
            tfidf_vectors[doc_id] = vector

        similarity_map = collections.defaultdict(list)
        question_ids = list(self.question_map.keys())
        for i in range(len(question_ids)):
            for j in range(i + 1, len(question_ids)):
                id1, id2 = question_ids[i], question_ids[j]
                if id1 in tfidf_vectors and id2 in tfidf_vectors:
                    sim = self._calculate_cosine_similarity(tfidf_vectors[id1], tfidf_vectors[id2])
                    if sim > self.SIMILARITY_THRESHOLD:
                        similarity_map[id1].append(id2)
                        similarity_map[id2].append(id1)
        return {k: v for k, v in similarity_map.items()} # Convert back to dict for JSON

# --- PARSER ---

class TextFileParser:
    BOOKMARK = "---SEGNALIBRO_STUDIO---"
    def __init__(self, file_path: Path): self.file_path = file_path
    def parse(self) -> List[Question]:
        questions: List[Question] = []
        try: content = self.file_path.read_text(encoding='utf-8')
        except Exception: return []
        if self.BOOKMARK in content: content, _ = content.split(self.BOOKMARK, 1)
        blocks = re.split(r'^\s*#\s*', content, flags=re.MULTILINE)
        for block in filter(None, (b.strip() for b in blocks)):
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines: continue
            q_text_full = lines.pop(0)
            q_number_match = re.match(r"(\d+)\.", q_text_full)
            q_number = q_number_match.group(1) if q_number_match else 'N/A'
            options, correct_answer, image_path = [], None, None
            for line in lines:
                if line.startswith('[image:'): image_path = Path(line.replace('[image:', '').replace(']', '').strip())
                elif line.startswith('*'):
                    option_text = line[1:].strip(); options.append(option_text); correct_answer = option_text
                else: options.append(line)
            if options: questions.append(Question(q_number, q_text_full, options, correct_answer, image_path))
        return questions

# --- GESTIONE IMPOSTAZIONI ---

class SettingsManager:
    """Gestisce caricamento/salvataggio dei percorsi e metadati per materia."""
    def __init__(self, filename="quiz_settings.json"):
        self.filepath = Path(filename)
        self.settings = self._load()

    def _load(self) -> Dict:
        try:
            settings = json.loads(self.filepath.read_text(encoding='utf-8'))
            for subj, data in settings.items():
                data.setdefault("retention_history", []); data.setdefault("interval_modifier", 1.0)
            return settings
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "ELETTROTECNICA": {"txt_path": "", "img_path": "", "exam_date": "17/10/2025", "status": "In Corso", "retention_history": [], "interval_modifier": 1.0},
                "FONDAMENTI DI INFORMATICA": {"txt_path": "", "img_path": "", "exam_date": "22/10/2025", "status": "In Corso", "retention_history": [], "interval_modifier": 1.0}
            }

    def save(self): self.filepath.write_text(json.dumps(self.settings, indent=2), encoding='utf-8')
    def get_subjects(self, status_filter: Optional[str] = None) -> List[str]:
        if not status_filter: return list(self.settings.keys())
        return [subj for subj, data in self.settings.items() if data.get("status") == status_filter]
    def get_subject_data(self, subject: str) -> Dict[str, Any]: return self.settings.get(subject, {})
    def set_subject_data(self, subject: str, data: Dict[str, Any]):
        if subject in self.settings: self.settings[subject].update(data)
    def add_subject(self, subject: str):
        if subject and subject.strip() and subject not in self.settings:
            self.settings[subject] = {"txt_path": "", "img_path": "", "exam_date": "", "status": "In Corso", "retention_history": [], "interval_modifier": 1.0}
            self.save()
    def remove_subject(self, subject: str):
        if subject in self.settings:
            subject_data = self.settings[subject]
            del self.settings[subject]
            srs_file = Path(f"{subject.replace(' ', '_').lower()}_srs_deck.json")
            if srs_file.exists(): srs_file.unlink()
            txt_path_str = subject_data.get("txt_path")
            if txt_path_str:
                cache_file = Path(f"{txt_path_str}.cache.json")
                if cache_file.exists(): cache_file.unlink()
            self.save()
    def update_retention_stats(self, subject: str, session_results: List[bool]):
        if subject not in self.settings: return
        data = self.settings[subject]
        history = data.get("retention_history", [])
        history.extend([1 if r else 0 for r in session_results])
        data["retention_history"] = history[-50:]
        if len(history) < 20: return
        retention_rate = sum(history) / len(history)
        modifier = data.get("interval_modifier", 1.0)
        if retention_rate > 0.9: modifier *= 1.05
        elif retention_rate < 0.8: modifier *= 0.95
        data["interval_modifier"] = max(0.7, min(1.5, modifier))
        self.save()

# --- VIEW (Viste / Finestre UI) ---

class MainView(ThemedTk):
    """Finestra principale di avvio con le modalità."""
    def __init__(self, start_callback: Callable[[str], None], settings_callback: Callable[[], None]):
        super().__init__(theme="arc")
        self.title("Quiz Loader"); self.geometry("550x300")
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

class SubjectSelectionDialog(simpledialog.Dialog):
    def __init__(self, parent, title, subjects):
        self.subjects = subjects; self.result = None; super().__init__(parent, title)
    def body(self, master):
        ttk.Label(master, text="Seleziona una materia:").pack(pady=10)
        self.combo = ttk.Combobox(master, values=self.subjects, state="readonly", width=30); self.combo.pack(padx=10)
        if self.subjects: self.combo.current(0)
        return self.combo
    def apply(self): self.result = self.combo.get()

class PracticeView(Toplevel):
    MAX_OPTIONS = 10
    def __init__(self, parent: tk.Tk, close_callback: Callable[[], None], mode: str):
        super().__init__(parent)
        self.parent = parent; self.mode = mode; self.is_exam_mode = (mode == 'exam'); self.close_controller_callback = close_callback
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
        style.configure("Answered.TButton", foreground="green", font=('Helvetica', 9, 'bold')); style.configure("Current.TButton", relief="sunken", foreground="blue", font=('Helvetica', 9, 'bold'))
        style.configure("CorrectAnswer.TLabel", foreground="blue", font=('Helvetica', 11, 'bold')); style.configure("Rate.TButton", font=('Helvetica', 10, 'bold'))
    def _setup_ui(self):
        root_frame = ttk.Frame(self, padding=10); root_frame.pack(expand=True, fill='both')
        self.timer_label = ttk.Label(root_frame, text="", font=("Helvetica", 14, "bold"), foreground="navy")
        if self.is_exam_mode: self.timer_label.pack(pady=(0, 10))
        content_frame = ttk.Frame(root_frame); content_frame.pack(expand=True, fill='both')
        question_area = ttk.Frame(content_frame); question_area.pack(side='left', expand=True, fill='both')
        if self.is_exam_mode:
            nav_container = ttk.Frame(content_frame); nav_container.pack(side='right', fill='y', padx=(10, 0))
            nav_canvas = tk.Canvas(nav_container, width=120); nav_scrollbar = ttk.Scrollbar(nav_container, orient="vertical", command=nav_canvas.yview)
            self.nav_panel = ttk.Frame(nav_canvas); self.nav_panel.bind("<Configure>", lambda e: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
            nav_canvas.create_window((0, 0), window=self.nav_panel, anchor="nw"); nav_canvas.configure(yscrollcommand=nav_scrollbar.set)
            nav_canvas.pack(side="left", fill="both", expand=True); nav_scrollbar.pack(side="right", fill="y")
        self.status_label = ttk.Label(question_area, text="", font=("Helvetica", 12)); self.status_label.pack(pady=(0, 10))
        container = ttk.Frame(question_area); container.pack(expand=True, fill='both', pady=10)
        container.grid_rowconfigure(1, weight=1); container.grid_columnconfigure(0, weight=1)
        self.image_label = ttk.Label(container); self.image_label.grid(row=0, column=0, pady=10)
        frame_content = ttk.LabelFrame(container, text="Domanda", padding=20); frame_content.grid(row=1, column=0, sticky='nsew')
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
        self.prev_button.config(command=prev_cb); self.next_button.config(command=next_cb); self.submit_button.config(command=submit_cb)
        for rating, button in self.srs_rate_buttons.items(): button.config(command=lambda r=rating: rate_cb(r))
    def switch_to_srs_feedback(self, show: bool):
        if show: self.nav_frame.pack_forget(); self.feedback_frame.pack(side='bottom', fill='x', pady=(10, 0))
        else: self.feedback_frame.pack_forget(); self.nav_frame.pack(side='bottom', fill='x', pady=(10, 0))
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
    def update_wraplength_and_image(self, image_update_callback: Optional[Callable] = None):
        if not self.winfo_exists(): return
        width = self.winfo_width(); nav_width = 150 if self.is_exam_mode else 0
        wraplength_value = max(300, width - nav_width - 100)
        self.question_text_label.config(wraplength=wraplength_value)
        for widget in self.option_widgets: widget['label'].config(wraplength=wraplength_value - 50)
        if image_update_callback: image_update_callback()
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
        for widget in self.option_widgets:
            if widget['radio']['value'] == correct_answer: widget['label'].config(style="CorrectAnswer.TLabel")
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

# --- CONTROLLER (Il "Cervello" dell'Applicazione) ---

class QuizController:
    def __init__(self, root: MainView, settings_manager: SettingsManager):
        self.root = root; self.settings_manager = settings_manager; self.srs_manager: Optional[SRSManager] = None
        self.current_subject = ""; self.all_questions: List[Question] = []; self.active_questions: List[Question] = []
        self.image_base_path: Optional[Path] = None; self.current_question_index = 0
        self.image_cache: Dict[Path, Image.Image] = {}; self.timer_id: Optional[str] = None; self.current_mode = ""
        self.practice_view: Optional[PracticeView] = None; self.results_view: Optional[ResultsView] = None
        self.question_start_time = 0.0; self.srs_session_results: List[bool] = []

    def check_srs_availability(self):
        subjects = self.settings_manager.get_subjects(status_filter="In Corso"); total_due = 0; next_exam_date = None; next_exam_subj = ""
        for subject in subjects:
            data = self.settings_manager.get_subject_data(subject)
            try:
                exam_date = datetime.datetime.strptime(data.get("exam_date", ""), '%d/%m/%Y').date()
                if not next_exam_date or exam_date < next_exam_date: next_exam_date = exam_date; next_exam_subj = subject
            except ValueError: pass
            srs_manager = SRSManager(subject, None, 1.0); total_due += len(srs_manager.get_due_questions())
        info = "Seleziona una modalità per iniziare:"
        if next_exam_date:
            days_left = (next_exam_date - datetime.date.today()).days
            info = f"Prossimo esame: {next_exam_subj} in {days_left} giorni." if days_left >= 0 else f"Esame di {next_exam_subj} era {abs(days_left)} giorni fa."
        self.root.update_review_button(total_due, info)

    def open_settings(self): SettingsView(self.root, self.settings_manager); self.check_srs_availability()

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
        self.srs_manager = SRSManager(self.current_subject, exam_date, modifier)

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
        self.practice_view = PracticeView(self.root, self.on_practice_close, self.current_mode)
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

    def on_answer_selected(self): self.active_questions[self.current_question_index].time_taken = time.monotonic() - self.question_start_time
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
            if self.srs_session_results: self.settings_manager.update_retention_stats(self.current_subject, self.srs_session_results)
            if leech_questions:
                msg = "Sessione di ripasso completata!\n\nATTENZIONE: Hai difficoltà persistenti con queste domande (leeches). Considera di studiarle da una fonte diversa:\n\n"
                for q in leech_questions[:5]: msg += f"- {q.text[:80]}...\n"
                messagebox.showwarning("Domande Ostiche Rilevate", msg)
            else: messagebox.showinfo("Fine Sessione", "Hai completato tutte le domande da ripassare per oggi!")
        self.root.deiconify(); self.check_srs_availability()
    
    def on_results_close(self):
        if self.results_view: self.results_view.destroy(); self.results_view = None
        if self.practice_view: self.practice_view.destroy(); self.practice_view = None # Clean up practice view as well
        self.root.deiconify(); self.check_srs_availability()

if __name__ == "__main__":
    class App:
        def __init__(self):
            self.settings_manager = SettingsManager()
            self.main_window = MainView(self.start_quiz_mode, self.open_settings)
            self.controller = QuizController(self.main_window, self.settings_manager)
            self.main_window.after(100, self.controller.check_srs_availability)
            self.main_window.mainloop()
        def start_quiz_mode(self, mode: str): self.controller.start(mode)
        def open_settings(self): self.controller.open_settings()
    app = App()

