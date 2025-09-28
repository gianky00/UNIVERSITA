import json
import datetime
from typing import Dict, Any, List
from pathlib import Path

from app.services.settings_manager import SettingsManager
from app.services.config_manager import ConfigManager

class AppDataManager:
    def __init__(self, settings_manager: SettingsManager, config_manager: ConfigManager):
        self.settings_manager = settings_manager
        self.config_manager = config_manager
        self.data_path = self.config_manager.get_data_path()
        self.filepath = self.data_path / "app_data.json"
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Carica i dati dal file JSON."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"user_stats": {"current_streak": 0, "last_study_date": None}, "review_log": []}

    def _save_data(self):
        """Salva i dati correnti nel file JSON."""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def log_review(self, subject: str, is_correct: bool):
        """Registra un nuovo evento di ripasso, aggiorna lo streak e ricalibra il modificatore di intervallo."""
        review_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "subject": subject,
            "is_correct": is_correct
        }
        self.data["review_log"].append(review_entry)
        self._update_study_streak()
        self._recalibrate_interval_modifier(subject)
        self._save_data()

    def _update_study_streak(self):
        """Aggiorna la serie di studio (streak) e la serie più lunga."""
        stats = self.data["user_stats"]
        today = datetime.date.today()
        last_study_str = stats.get("last_study_date")
        current_streak = stats.get("current_streak", 0)
        longest_streak = stats.get("longest_streak", 0)

        if last_study_str:
            last_study_date = datetime.date.fromisoformat(last_study_str)
            delta = today - last_study_date
            if delta.days == 1:
                current_streak += 1
            elif delta.days > 1:
                current_streak = 1  # Reset to 1 for today's study
        else:
            current_streak = 1  # Primo studio in assoluto

        stats["current_streak"] = current_streak
        stats["longest_streak"] = max(current_streak, longest_streak)
        stats["last_study_date"] = today.isoformat()

    def _recalibrate_interval_modifier(self, subject: str):
        """Ricalibra il modificatore dell'intervallo per una materia in base alla performance recente."""
        subject_reviews = [r for r in self.data.get("review_log", []) if r["subject"] == subject]

        # Considera solo le ultime 50 recensioni per la ricalibrazione
        recent_reviews = subject_reviews[-50:]

        # Richiede un numero minimo di recensioni per evitare aggiustamenti prematuri
        if len(recent_reviews) < 20:
            return

        correct_count = sum(1 for r in recent_reviews if r["is_correct"])
        retention_rate = correct_count / len(recent_reviews)

        subject_data = self.settings_manager.get_subject_data(subject)
        if not subject_data:
            return

        modifier = subject_data.get("interval_modifier", 1.0)

        if retention_rate > 0.9: # Performance alta, aumenta l'intervallo
            modifier *= 1.05
        elif retention_rate < 0.8: # Performance bassa, riduci l'intervallo
            modifier *= 0.95

        # Limita il modificatore tra 0.7 e 1.5 per evitare valori estremi
        subject_data["interval_modifier"] = max(0.7, min(1.5, modifier))

        self.settings_manager.set_subject_data(subject, subject_data)
        self.settings_manager.save() # Salva immediatamente la modifica

    def get_overall_stats(self) -> Dict[str, Any]:
        """Calcola e restituisce un dizionario di statistiche complessive, inclusi i dettagli per materia."""
        review_log = self.get_review_log()
        user_stats = self.get_user_stats()

        total_reviews = len(review_log)

        subject_counts = {}
        for r in review_log:
            subject_counts[r["subject"]] = subject_counts.get(r["subject"], 0) + 1
        most_studied = max(subject_counts, key=subject_counts.get) if subject_counts else "N/D"

        # --- Dettagli per Materia ---
        subject_details = {}
        all_subjects = self.settings_manager.get_subjects()
        global_settings = self.settings_manager.get_global_settings()
        retention_days = global_settings.get("retention_period_days", 7)
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)

        for subject in all_subjects:
            subject_data = self.settings_manager.get_subject_data(subject)

            # Calcolo ritenzione per la materia (basato sul periodo di ritenzione)
            recent_subject_reviews = [
                r for r in review_log
                if r["subject"] == subject and datetime.datetime.fromisoformat(r["timestamp"]) >= cutoff_date
            ]

            retention_rate = None
            if recent_subject_reviews:
                correct_count = sum(1 for r in recent_subject_reviews if r["is_correct"])
                retention_rate = (correct_count / len(recent_subject_reviews)) * 100

            subject_details[subject] = {
                "status": subject_data.get("status", "N/D"),
                "retention_rate": retention_rate,
                "txt_path": subject_data.get("txt_path", ""), # Passa il percorso al controller
            }

        return {
            "total_reviews": total_reviews,
            "overall_retention": self.get_retention_rate(), # Usa il metodo corretto
            "longest_streak": user_stats.get("longest_streak", 0),
            "most_studied": most_studied,
            "subject_details": subject_details
        }

    def get_review_log(self) -> List[Dict[str, Any]]:
        """Restituisce il log completo dei ripassi."""
        return self.data.get("review_log", [])

    def get_user_stats(self) -> Dict[str, Any]:
        """Restituisce le statistiche dell'utente (streak, ecc.)."""
        return self.data.get("user_stats", {})

    def get_current_streak(self) -> int:
        """Restituisce la serie di studio (streak) corrente."""
        stats = self.get_user_stats()
        return stats.get("current_streak", 0)

    def get_retention_rate(self) -> float:
        """
        Calcola il tasso di ritenzione globale basandosi sul periodo configurato.
        Restituisce il tasso come percentuale (es. 85.0) o 0.0 se non ci sono dati.
        """
        global_settings = self.settings_manager.get_global_settings()
        retention_days = global_settings.get("retention_period_days", 7)

        review_log = self.get_review_log()
        if not review_log:
            return 0.0

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)

        relevant_reviews = [
            review for review in review_log
            if datetime.datetime.fromisoformat(review["timestamp"]) >= cutoff_date
        ]

        if not relevant_reviews:
            return 0.0

        correct_reviews = sum(1 for review in relevant_reviews if review["is_correct"])
        return (correct_reviews / len(relevant_reviews)) * 100
