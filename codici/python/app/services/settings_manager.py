import json
from pathlib import Path
from typing import List, Dict, Optional, Any

# Costruisce un percorso assoluto alla directory 'json'
# Questo rende l'app indipendente dalla directory di lavoro corrente
JSON_DIR = Path(__file__).resolve().parent.parent.parent.parent / "json"

class SettingsManager:
    """Gestisce caricamento/salvataggio dei percorsi e metadati per materia e impostazioni globali."""
    def __init__(self):
        self.filepath = JSON_DIR / "quiz_settings.json"
        self.settings = self._load()

    def _get_default_settings(self) -> Dict:
        """Restituisce la struttura delle impostazioni di default."""
        return {
            "global_settings": {
                "retention_period_days": 7,
                "srs_intervals": {"again": 10, "hard": 120, "good": 1440, "easy": 4320},
                "new_cards_per_day": 20,
                "active_profile": ""
            },
            "path_profiles": {
                "PC_COEMI": {},
                "PC_GIANKY": {}
            },
            "ELETTROTECNICA": {"txt_path": "", "img_path": "", "exam_date": "17/10/2025", "status": "In Corso", "interval_modifier": 1.0},
            "FONDAMENTI DI INFORMATICA": {"txt_path": "", "img_path": "", "exam_date": "22/10/2025", "status": "In Corso", "interval_modifier": 1.0}
        }

    def _load(self) -> Dict:
        try:
            settings = json.loads(self.filepath.read_text(encoding='utf-8'))
            # Migrazione per vecchi file di configurazione
            if "global_settings" not in settings:
                settings["global_settings"] = self._get_default_settings()["global_settings"]
            if "active_profile" not in settings["global_settings"]:
                settings["global_settings"]["active_profile"] = ""
            if "path_profiles" not in settings:
                settings["path_profiles"] = self._get_default_settings()["path_profiles"]

            for subj, data in settings.items():
                if subj not in ["global_settings", "path_profiles"]:
                    data.setdefault("interval_modifier", 1.0)
            return settings
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_settings()

    def save(self):
        self.filepath.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False), encoding='utf-8')

    def get_global_settings(self) -> Dict[str, Any]:
        return self.settings.get("global_settings", self._get_default_settings()["global_settings"])

    def save_global_settings(self, new_settings: Dict[str, Any]):
        self.settings["global_settings"] = new_settings
        self.save()

    def get_subjects(self, status_filter: Optional[str] = None) -> List[str]:
        subjects = [subj for subj in self.settings.keys() if subj not in ["global_settings", "path_profiles"]]
        if not status_filter:
            return subjects
        return [subj for subj in subjects if self.settings[subj].get("status") == status_filter]

    def get_path_profiles(self) -> List[str]:
        """Restituisce i nomi dei profili di percorso disponibili."""
        return list(self.settings.get("path_profiles", {}).keys())

    def get_active_profile(self) -> str:
        """Restituisce il nome del profilo attivo."""
        return self.settings.get("global_settings", {}).get("active_profile", "")

    def set_active_profile(self, profile_name: str):
        """Imposta il profilo di percorso attivo."""
        if "global_settings" in self.settings:
            self.settings["global_settings"]["active_profile"] = profile_name

    def apply_path_profile(self, profile_name: str):
        """Applica un profilo di percorso, aggiornando i percorsi per ogni materia."""
        profile_paths = self.settings.get("path_profiles", {}).get(profile_name)
        if not profile_paths:
            return

        for subject in self.get_subjects():
            if subject in profile_paths:
                self.settings[subject]["txt_path"] = profile_paths[subject].get("txt_path", "")
                self.settings[subject]["img_path"] = profile_paths[subject].get("img_path", "")

        self.set_active_profile(profile_name)
        self.save()

    def save_current_paths_as_profile(self, profile_name: str):
        """Salva i percorsi attuali delle materie come un nuovo profilo di percorso."""
        if not profile_name.strip():
            return

        current_paths = {}
        for subject in self.get_subjects():
            current_paths[subject] = {
                "txt_path": self.settings[subject].get("txt_path", ""),
                "img_path": self.settings[subject].get("img_path", "")
            }

        if "path_profiles" not in self.settings:
            self.settings["path_profiles"] = {}

        self.settings["path_profiles"][profile_name] = current_paths
        self.set_active_profile(profile_name)
        self.save()

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
        if subject in self.settings and subject not in ["global_settings", "path_profiles"]:
            subject_data = self.settings[subject]
            del self.settings[subject]
            # Gestione file associati
            srs_file = Path(f"codici/json/{subject.replace(' ', '_').lower()}_srs_deck.json")
            if srs_file.exists(): srs_file.unlink()
            txt_path_str = subject_data.get("txt_path")
            if txt_path_str:
                cache_file = Path(f"{txt_path_str}.cache.json")
                if cache_file.exists(): cache_file.unlink()
            self.save()
