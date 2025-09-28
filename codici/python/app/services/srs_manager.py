import json
import datetime
import collections
from pathlib import Path
from typing import List, Dict, Optional, Set

from app.models.question_model import Question
from app.models.srs_model import SRSItem
from app.services.app_data_manager import AppDataManager
from app.services.settings_manager import SettingsManager
from app.services.config_manager import ConfigManager

class SRSManager:
    """Gestisce la logica del deck di studio SRS, con calibrazione dinamica e analisi di interferenza."""
    MAX_INTERVAL = 30  # Intervallo massimo di ripasso in giorni, per sicurezza
    LEECH_THRESHOLD = 6

    def __init__(self, subject: str, exam_date: Optional[datetime.date], interval_modifier: float, app_data_manager: AppDataManager, settings_manager: SettingsManager, config_manager: ConfigManager):
        self.subject = subject
        self.data_path = config_manager.get_data_path()
        self.filepath = self.data_path / f"{self.subject.replace(' ', '_').lower()}_srs_deck.json"
        self.deck: Dict[str, SRSItem] = self._load()
        self.exam_date = exam_date
        self.interval_modifier = interval_modifier
        self.similarity_map: Dict[str, Set[str]] = collections.defaultdict(set)
        self.app_data_manager = app_data_manager
        self.settings_manager = settings_manager

    def _load(self) -> Dict[str, SRSItem]:
        if not self.filepath.exists(): return {}
        try:
            data = json.loads(self.filepath.read_text(encoding='utf-8'))
            return {item_id: SRSItem.from_dict(item_data) for item_id, item_data in data.items()}
        except (json.JSONDecodeError, TypeError): return {}

    def save(self):
        data_to_save = {item_id: item.to_dict() for item_id, item in self.deck.items()}
        self.filepath.write_text(json.dumps(data_to_save, indent=2, ensure_ascii=False), encoding='utf-8')

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

        is_correct = rating != "non_la_sapevo"
        self.app_data_manager.log_review(self.subject, is_correct)

        item = self.deck[question.id]

        # Carica gli intervalli SRS dalle impostazioni globali
        global_settings = self.settings_manager.get_global_settings()
        srs_intervals = global_settings.get("srs_intervals", {"again": 10, "hard": 120, "good": 1440, "easy": 4320})

        # Mappa il rating all'intervallo corretto
        rating_map = {
            "non_la_sapevo": "again",
            "difficile": "hard",
            "medio": "good",
            "facile": "easy"
        }
        interval_key = rating_map.get(rating, "good")

        # Aggiorna la cronologia della carta
        item.history[interval_key] = item.history.get(interval_key, 0) + 1

        if not is_correct:
            item.lapses += 1

        base_interval_minutes = srs_intervals.get(interval_key, 1440)
        # Converte l'intervallo da minuti a giorni
        new_interval_days = base_interval_minutes / 1440.0 # 60 minuti * 24 ore

        # Fattore di urgenza basato sulla data dell'esame
        urgency_factor = 1.0
        if self.exam_date:
            days_to_exam = (self.exam_date - datetime.date.today()).days
            if 0 < days_to_exam <= 21:
                urgency_factor = 0.4 + 0.6 * (days_to_exam / 21)
            elif days_to_exam <= 0:
                urgency_factor = 0.1

        # Calcolo finale dell'intervallo
        final_interval_days = max(1, int(round(new_interval_days * urgency_factor * self.interval_modifier)))
        final_interval_days = min(final_interval_days, self.MAX_INTERVAL)

        item.next_review_date = datetime.date.today() + datetime.timedelta(days=final_interval_days)
        self.save()
        return item.lapses >= self.LEECH_THRESHOLD
