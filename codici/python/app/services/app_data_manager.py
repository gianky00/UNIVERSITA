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

    def _get_default_data(self) -> Dict[str, Any]:
        """Restituisce la struttura dati di default."""
        return {
            "user_stats": {"current_streak": 0, "last_study_date": None, "longest_streak": 0},
            "review_log": [],
            "retention_trend": []
        }

    def _load_data(self) -> Dict[str, Any]:
        """Carica i dati dal percorso dati corrente o crea un file di default."""
        try:
            self.data_path.mkdir(parents=True, exist_ok=True)
            if self.filepath.exists():
                loaded_data = json.loads(self.filepath.read_text(encoding='utf-8'))
                # Assicura che le nuove chiavi esistano per retrocompatibilità
                loaded_data.setdefault("retention_trend", [])
                loaded_data.setdefault("user_stats", {}).setdefault("longest_streak", 0)
                return loaded_data
            else:
                default_data = self._get_default_data()
                self.filepath.write_text(json.dumps(default_data, indent=2, ensure_ascii=False), encoding='utf-8')
                return default_data
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_data()

    def _save_data(self):
        """Salva i dati correnti nel percorso dati corrente."""
        self.data_path.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def log_review(self, subject: str, is_correct: bool):
        """Registra un nuovo evento di ripasso, aggiorna lo streak e l'andamento della ritenzione."""
        self.data.setdefault("review_log", []).append({
            "timestamp": datetime.datetime.now().isoformat(),
            "subject": subject,
            "is_correct": is_correct
        })
        self._update_study_streak()
        self._recalibrate_interval_modifier(subject)
        self._update_retention_trend()
        self._save_data()

    def _update_retention_trend(self):
        """Salva o aggiorna l'istantanea del tasso di ritenzione per il giorno corrente."""
        today_str = datetime.date.today().isoformat()
        current_retention = self.get_retention_rate()
        trend_list = self.data.setdefault("retention_trend", [])

        today_entry = next((item for item in trend_list if item["date"] == today_str), None)
        if today_entry:
            today_entry["retention"] = current_retention
        else:
            trend_list.append({"date": today_str, "retention": current_retention})

    def _update_study_streak(self):
        """Aggiorna la serie di studio (streak) e la serie più lunga."""
        stats = self.data.setdefault("user_stats", self._get_default_data()["user_stats"])
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
                current_streak = 1
        else:
            current_streak = 1
        stats["current_streak"] = current_streak
        stats["longest_streak"] = max(current_streak, longest_streak)
        stats["last_study_date"] = today.isoformat()

    def _recalibrate_interval_modifier(self, subject: str):
        review_log = self.data.get("review_log", [])
        subject_reviews = [r for r in review_log if r["subject"] == subject]
        recent_reviews = subject_reviews[-50:]
        if len(recent_reviews) < 20: return
        correct_count = sum(1 for r in recent_reviews if r["is_correct"])
        retention_rate = correct_count / len(recent_reviews)
        subject_data = self.settings_manager.get_subject_data(subject)
        if not subject_data: return
        modifier = subject_data.get("interval_modifier", 1.0)
        if retention_rate > 0.9: modifier *= 1.05
        elif retention_rate < 0.8: modifier *= 0.95
        subject_data["interval_modifier"] = max(0.7, min(1.5, modifier))
        self.settings_manager.set_subject_data(subject, subject_data)
        self.settings_manager.save()

    def get_overall_stats(self) -> Dict[str, Any]:
        review_log = self.get_review_log()
        user_stats = self.get_user_stats()
        total_reviews = len(review_log)
        if total_reviews == 0:
            return {"total_reviews": 0, "overall_retention": 0.0, "longest_streak": user_stats.get("longest_streak", 0), "most_studied": "N/D", "retention_trend": []}

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
            recent_subject_reviews = [r for r in review_log if r["subject"] == subject and datetime.datetime.fromisoformat(r["timestamp"]) >= cutoff_date]
            retention_rate = None
            if recent_subject_reviews:
                correct_count = sum(1 for r in recent_subject_reviews if r["is_correct"])
                retention_rate = (correct_count / len(recent_subject_reviews)) * 100
            subject_details[subject] = {"status": subject_data.get("status", "N/D"),"retention_rate": retention_rate}

        return {
            "total_reviews": total_reviews,
            "overall_retention": self.get_retention_rate(),
            "longest_streak": user_stats.get("longest_streak", 0),
            "most_studied": most_studied,
            "retention_trend": self.data.get("retention_trend", []),
            "subject_details": subject_details
        }

    def get_review_log(self) -> List[Dict[str, Any]]:
        return self.data.get("review_log", [])

    def get_user_stats(self) -> Dict[str, Any]:
        return self.data.get("user_stats", {})

    def get_current_streak(self) -> int:
        return self.get_user_stats().get("current_streak", 0)

    def get_retention_rate(self) -> float:
        global_settings = self.settings_manager.get_global_settings()
        retention_days = global_settings.get("retention_period_days", 7)
        review_log = self.get_review_log()
        if not review_log: return 0.0
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        relevant_reviews = [r for r in review_log if datetime.datetime.fromisoformat(r["timestamp"]) >= cutoff_date]
        if not relevant_reviews: return 0.0
        correct_reviews = sum(1 for review in relevant_reviews if review["is_correct"])
        return (correct_reviews / len(relevant_reviews)) * 100

    def reload_data(self):
        self.data_path = self.config_manager.get_data_path()
        self.filepath = self.data_path / "app_data.json"
        self.data = self._load_data()