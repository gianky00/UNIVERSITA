import tkinter as tk
from tkinter import filedialog, Toplevel, messagebox
from PIL import ImageGrab
import os
import time
import ctypes

class SnippingTool(Toplevel):
    def __init__(self, parent, state):
        super().__init__(parent)
        self.state = state
        self.withdraw() # Hide window until we are ready

        # Make this a transient window that stays on top
        self.transient(parent)
        self.attributes("-alpha", 0.3)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)

        self.canvas = tk.Canvas(self, cursor="cross", bg="gray")
        self.canvas.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.deiconify() # Show window
        self.grab_set() # Grab all events
        self.focus_set()

    def on_button_press(self, event):
        self.start_x = self.winfo_pointerx()
        self.start_y = self.winfo_pointery()
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, dash=(4, 2))

    def on_mouse_drag(self, event):
        if not self.rect: return
        cur_x, cur_y = (self.winfo_pointerx(), self.winfo_pointery())
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.winfo_pointerx()
        end_y = self.winfo_pointery()
        self.take_screenshot(end_x, end_y)
        self.destroy()

    def take_screenshot(self, end_x, end_y):
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        if abs(x1 - x2) < 5 or abs(y1 - y2) < 5:
            messagebox.showwarning("Selezione troppo piccola", "Selezione troppo piccola, ritaglio annullato.", parent=self)
            return

        try:
            # Short delay to ensure the snipping overlay is gone
            self.withdraw()
            time.sleep(0.1)
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)

            filepath = os.path.join(self.state['output_folder'], f"{self.state['shot_count']:03d}.png")
            img.save(filepath)
            print(f"Ritaglio salvato: {filepath}")
            self.state['shot_count'] += 1
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il salvataggio: {e}", parent=self)
        finally:
            self.destroy()

from pathlib import Path

def main(parent, data_path: Path):
    """Launches the image snipping tool."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        print("Impossibile impostare la modalità DPI-Aware.")

    # Use the configured data path directly
    output_folder = data_path / "immagini_ritagliate"
    output_folder.mkdir(parents=True, exist_ok=True)

    shot_count = 1
    while os.path.exists(os.path.join(output_folder, f"{shot_count:03d}.png")):
        shot_count += 1

    app_state = {
        "output_folder": output_folder,
        "shot_count": shot_count
    }

    messagebox.showinfo("Avvio Strumento Ritaglio", f"I ritagli verranno salvati in:\n'{app_state['output_folder']}'\n\nTrascina per selezionare l'area.", parent=parent)

    # The snipping tool is now a Toplevel window
    SnippingTool(parent, app_state)

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App")

    # Hide the root window, as the tool is the main interaction
    root.withdraw()

    # For standalone execution, use a default path relative to this script
    # This assumes a certain project structure for testing purposes
    default_data_path = Path(__file__).resolve().parent.parent.parent / "json"
    main(root, default_data_path)

    # We can destroy the root window after the tool is used
    root.destroy()