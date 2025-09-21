import json
from pathlib import Path
from typing import List, Dict, Optional, Any

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
