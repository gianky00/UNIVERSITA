import sys
import os
from pathlib import Path

# Add the parent directory ('codici/python') to the system path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.controllers.quiz_controller import QuizController
from app.services.settings_manager import SettingsManager
from app.services.config_manager import ConfigManager
from app.views.main_view import MainView
from app.views.path_dialog import ask_for_new_datapath

def launch_app():
    """Lancia l'applicazione principale."""
    try:
        config_manager = ConfigManager()
        settings_manager = SettingsManager(config_manager)

        main_window = MainView(
            start_callback=lambda mode: controller.start(mode),
            settings_callback=lambda: controller.open_settings(),
            analysis_callback=lambda: controller.open_analysis(),
            tools_callbacks={
                "pdf_merger": lambda: controller.launch_pdf_merger(),
                "text_formatter": lambda: controller.launch_text_formatter(),
                "image_snipper": lambda: controller.launch_image_snipper()
            }
        )

        controller = QuizController(main_window, settings_manager, config_manager)
        main_window.after(100, controller.update_dashboard_and_srs_status)
        main_window.mainloop()

    except FileNotFoundError as e:
        # Errore specifico catturato quando il data_path non è valido
        config_manager = ConfigManager()
        invalid_path = config_manager.get_data_path()

        new_path = ask_for_new_datapath(invalid_path)

        if new_path:
            # Aggiorna il profilo attivo con il nuovo percorso
            active_profile = config_manager.get_active_profile()
            config_manager.update_profile_path(active_profile, str(new_path))

            # Riavvia l'applicazione per applicare le modifiche
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            # L'utente ha annullato, l'applicazione si chiude
            sys.exit(0)

if __name__ == "__main__":
    launch_app()