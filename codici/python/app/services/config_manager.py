import json
from pathlib import Path
from typing import Dict, List

class ConfigManager:
    """
    Gestisce la configurazione dell'applicazione, inclusa la gestione di profili
    per diversi percorsi di dati.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    DEFAULT_JSON_DIR = BASE_DIR / "json"

    def __init__(self):
        self.config_path = self.DEFAULT_JSON_DIR / "config.json"

        # Carica la configurazione raw per verificare se è necessaria la migrazione
        raw_config = {}
        is_new_install = not self.config_path.exists()
        if not is_new_install:
            try:
                raw_config = json.loads(self.config_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, FileNotFoundError):
                pass # Tratta come se fosse una nuova installazione/file corrotto

        # Esegui il caricamento/migrazione/creazione in memoria
        self.config = self._load_or_create_config()

        # Salva se è una nuova installazione o se è avvenuta una migrazione
        if is_new_install or "data_path" in raw_config:
            self.save_config()

    def _load_or_create_config(self) -> Dict:
        """Carica la configurazione o ne crea una di default con profili."""
        config = {}
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, FileNotFoundError):
                pass  # Ignora e procedi a creare/usare il default

        # Migrazione dalla vecchia configurazione (solo data_path)
        if "data_path" in config:
            old_data_path = config["data_path"]
            return {
                "active_profile": "Default",
                "profiles": {
                    "Default": {"data_path": old_data_path}
                }
            }

        # Se il file non esiste, è corrotto o non ha profili, crea la struttura di default
        if "profiles" not in config or not config["profiles"]:
            default_path = str(self.DEFAULT_JSON_DIR)
            return {
                "active_profile": "Default",
                "profiles": {
                    "Default": {"data_path": default_path}
                }
            }

        return config

    def save_config(self):
        """Salva la configurazione corrente nel file config.json."""
        self.DEFAULT_JSON_DIR.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding='utf-8')

    def get_data_path(self) -> Path:
        """Restituisce il percorso della cartella dati per il profilo attivo."""
        active_profile_name = self.get_active_profile()
        path_str = self.config["profiles"][active_profile_name]["data_path"]
        return Path(path_str)

    def get_active_profile(self) -> str:
        """Restituisce il nome del profilo attivo."""
        return self.config.get("active_profile", "Default")

    def set_active_profile(self, profile_name: str):
        """Imposta il profilo attivo."""
        if profile_name in self.config["profiles"]:
            self.config["active_profile"] = profile_name
            self.save_config()
        else:
            raise ValueError(f"Profilo '{profile_name}' non trovato.")

    def get_profiles(self) -> List[str]:
        """Restituisce una lista dei nomi di tutti i profili."""
        return list(self.config.get("profiles", {}).keys())

    def add_profile(self, profile_name: str, data_path: str):
        """Aggiunge un nuovo profilo."""
        if profile_name in self.config["profiles"]:
            raise ValueError(f"Un profilo con nome '{profile_name}' esiste già.")
        self.config["profiles"][profile_name] = {"data_path": data_path}
        self.save_config()

    def remove_profile(self, profile_name: str):
        """Rimuove un profilo. Impedisce la rimozione dell'ultimo profilo."""
        if profile_name not in self.config["profiles"]:
            raise ValueError(f"Profilo '{profile_name}' non trovato.")
        if len(self.config["profiles"]) <= 1:
            raise ValueError("Impossibile rimuovere l'ultimo profilo.")

        del self.config["profiles"][profile_name]

        # Se il profilo rimosso era quello attivo, imposta un altro profilo come attivo
        if self.get_active_profile() == profile_name:
            self.set_active_profile(next(iter(self.config["profiles"])))

        self.save_config()

    def update_profile_path(self, profile_name: str, new_path: str):
        """Aggiorna il percorso di un profilo esistente."""
        if profile_name not in self.config["profiles"]:
            raise ValueError(f"Profilo '{profile_name}' non trovato.")
        self.config["profiles"][profile_name]["data_path"] = new_path
        self.save_config()