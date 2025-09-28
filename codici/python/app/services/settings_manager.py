import json
from pathlib import Path
from typing import List, Dict, Optional, Any

from app.services.config_manager import ConfigManager

class SettingsManager:
    """Gestisce caricamento/salvataggio dei percorsi e metadati per materia e impostazioni globali."""
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.data_path = self.config_manager.get_data_path()
        self.filepath = self.data_path / "quiz_settings.json"
        self.settings = self._load()

    def _get_default_settings(self) -> Dict:
        """Restituisce la struttura delle impostazioni di default."""
        return {
            "global_settings": {
                "retention_period_days": 7,
                "srs_intervals": {"again": 10, "hard": 120, "good": 1440, "easy": 4320},
                "new_cards_per_day": 20
            },
            "ELETTROTECNICA": {"txt_path": "", "img_path": "", "exam_date": "17/10/2025", "status": "In Corso", "interval_modifier": 1.0},
            "FONDAMENTI DI INFORMATICA": {"txt_path": "", "img_path": "", "exam_date": "22/10/2025", "status": "In Corso", "interval_modifier": 1.0}
        }

    def _load(self) -> Dict:
        """Carica le impostazioni dal percorso dati corrente."""
        try:
            # Assicura che la cartella esista prima di tentare di leggere
            self.data_path.mkdir(parents=True, exist_ok=True)
            settings = json.loads(self.filepath.read_text(encoding='utf-8'))
            if "global_settings" not in settings:
                settings["global_settings"] = self._get_default_settings()["global_settings"]
            for subj, data in settings.items():
                if subj != "global_settings":
                    data.setdefault("interval_modifier", 1.0)
            return settings
        except (FileNotFoundError, json.JSONDecodeError):
            # Se il file non esiste nel percorso dati, ne crea uno nuovo
            default_settings = self._get_default_settings()
            self.filepath.write_text(json.dumps(default_settings, indent=2, ensure_ascii=False), encoding='utf-8')
            return default_settings

    def save(self):
        """Salva le impostazioni nel percorso dati corrente."""
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False), encoding='utf-8')

    def get_global_settings(self) -> Dict[str, Any]:
        return self.settings.get("global_settings", self._get_default_settings()["global_settings"])

    def save_global_settings(self, new_settings: Dict[str, Any]):
        self.settings["global_settings"] = new_settings
        self.save()

    def get_subjects(self, status_filter: Optional[str] = None) -> List[str]:
        subjects = [subj for subj in self.settings.keys() if subj != "global_settings"]
        if not status_filter:
            return subjects
        return [subj for subj in subjects if self.settings[subj].get("status") == status_filter]

    def get_subject_data(self, subject: str) -> Dict[str, Any]:
        return self.settings.get(subject, {})

    def set_subject_data(self, subject: str, data: Dict[str, Any]):
        if subject in self.settings and subject != "global_settings":
            self.settings[subject].update(data)

    def add_subject(self, subject: str):
        if subject and subject.strip() and subject not in self.settings:
            self.settings[subject] = {"txt_path": "", "img_path": "", "exam_date": "", "status": "In Corso", "interval_modifier": 1.0}
            self.save()

    def remove_subject(self, subject: str):
        if subject in self.settings and subject != "global_settings":
            subject_data = self.settings[subject]
            del self.settings[subject]

            # Gestione file associati con il nuovo percorso dati
            srs_file = self.data_path / f"{subject.replace(' ', '_').lower()}_srs_deck.json"
            if srs_file.exists():
                srs_file.unlink()

            # Il file di cache è relativo al file .txt, quindi questo non cambia
            txt_path_str = subject_data.get("txt_path")
            if txt_path_str:
                cache_file = Path(txt_path_str).with_suffix('.txt.cache.json')
                if cache_file.exists():
                    cache_file.unlink()
            self.save()

    def reload_settings(self):
        """Ricarica le impostazioni dal percorso dati corrente. Utile dopo aver cambiato cartella."""
        self.data_path = self.config_manager.get_data_path()
        self.filepath = self.data_path / "quiz_settings.json"
        self.settings = self._load()