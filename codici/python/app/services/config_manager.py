import json
from pathlib import Path

class ConfigManager:
    """Gestisce la configurazione dell'applicazione, come il percorso dei dati."""

    # Percorso di base dell'applicazione
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    DEFAULT_JSON_DIR = BASE_DIR / "json"

    def __init__(self):
        self.config_path = self.DEFAULT_JSON_DIR / "config.json"
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Carica la configurazione o ne crea una di default."""
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            pass # Ignora errori e procedi a creare il default

        # Se il file non esiste o è corrotto, crea la configurazione di default
        return {"data_path": str(self.DEFAULT_JSON_DIR)}

    def save_config(self):
        """Salva la configurazione corrente."""
        # Assicura che la directory esista
        self.DEFAULT_JSON_DIR.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding='utf-8')

    def get_data_path(self) -> Path:
        """Restituisce il percorso della cartella dei dati (es. 'json')."""
        path_str = self.config.get("data_path", str(self.DEFAULT_JSON_DIR))
        return Path(path_str)

    def set_data_path(self, new_path: str):
        """Imposta un nuovo percorso per la cartella dei dati."""
        self.config["data_path"] = new_path
        self.save_config()