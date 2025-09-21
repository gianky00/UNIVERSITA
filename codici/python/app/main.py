import sys
from pathlib import Path

# Add the parent directory ('codici/python') to the system path
# This allows us to import from both 'app' and 'tools' packages
sys.path.append(str(Path(__file__).parent.parent))

from app.controllers.quiz_controller import QuizController
from app.services.settings_manager import SettingsManager
from app.views.main_view import MainView

class App:
    def __init__(self):
        # 1. Initialize core logic components
        settings_manager = SettingsManager()

        # 2. Create the main window (View)
        # The view is created first, but it's just a UI shell at this point.
        main_window = MainView(
            start_callback=lambda mode: controller.start(mode),
            settings_callback=lambda: controller.open_settings(),
            tools_callbacks={
                "pdf_merger": lambda: controller.launch_pdf_merger(),
                "text_formatter": lambda: controller.launch_text_formatter(),
                "image_snipper": lambda: controller.launch_image_snipper()
            }
        )

        # 3. Create the Controller, linking the View and logic together
        controller = QuizController(main_window, settings_manager)

        # 4. Perform initial checks and start the main loop
        main_window.after(100, controller.check_srs_availability)
        main_window.mainloop()

if __name__ == "__main__":
    app = App()
