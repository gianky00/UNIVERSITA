import json
from pathlib import Path

class ConfigManager:
    """Gestisce la configurazione dell'applicazione, come il percorso dei dati."""

    # Il percorso della cartella 'json' di default, che contiene la configurazione dell'app.
    # Questo percorso non cambia mai.
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    DEFAULT_JSON_DIR = BASE_DIR / "json"

    def __init__(self):
        self.config_path = self.DEFAULT_JSON_DIR / "config.json"
        self.config = self._load_config()
        # Assicura che il file di configurazione esista al primo avvio
        if not self.config_path.exists():
            self.save_config()

    def _load_config(self) -> dict:
        """Carica la configurazione o ne crea una di default."""
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            pass # Ignora errori e procedi a creare/usare il default

        # Se il file non esiste o è corrotto, usa la configurazione di default
        # che punta alla cartella 'json' standard come percorso dati.
        return {"data_path": str(self.DEFAULT_JSON_DIR)}

    def save_config(self):
        """Salva la configurazione corrente nel file config.json."""
        self.DEFAULT_JSON_DIR.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding='utf-8')

    def get_data_path(self) -> Path:
        """Restituisce il percorso della cartella dati configurata dall'utente."""
        path_str = self.config.get("data_path", str(self.DEFAULT_JSON_DIR))
        return Path(path_str)

    def set_data_path(self, new_path: str):
        """Imposta un nuovo percorso per la cartella dei dati e salva la configurazione."""
        self.config["data_path"] = new_path
        self.save_config()