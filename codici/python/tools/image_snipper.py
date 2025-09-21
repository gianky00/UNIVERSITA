import tkinter as tk
from tkinter import filedialog
from PIL import ImageGrab
import keyboard
import os
import time
import ctypes

class SnippingTool:
    """Questa classe ora gestisce una singola sessione di ritaglio."""
    def __init__(self, state):
        self.state = state  # Riferimento allo stato condiviso (cartella e contatore)
        self.root = None
        self.canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None

    def start(self):
        """Crea l'overlay e avvia il mainloop per una singola cattura."""
        self.root = tk.Tk()
        self.root.attributes("-alpha", 0.3)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="gray")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
        self.root.mainloop()

    def on_button_press(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, 
            outline='red', width=2, dash=(4, 2)
        )

    def on_mouse_drag(self, event):
        if not self.rect: return
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x_root, event.y_root)

    def on_button_release(self, event):
        end_x = event.x_root
        end_y = event.y_root

        self.root.withdraw()
        time.sleep(0.1)
        
        self.take_screenshot(end_x, end_y)
        
        self.root.destroy()
        
    def take_screenshot(self, end_x, end_y):
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        if abs(x1 - x2) < 5 or abs(y1 - y2) < 5:
            print("Selezione troppo piccola, ritaglio annullato.")
            return

        try:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)
            filepath = os.path.join(self.state['output_folder'], f"{self.state['shot_count']:03d}.png")
            img.save(filepath)
            print(f"Ritaglio salvato: {filepath}")
            self.state['shot_count'] += 1
        except Exception as e:
            print(f"Errore durante il salvataggio: {e}")

def ask_question_type():
    """
    NUOVO: Crea una finestra per chiedere all'utente il tipo di domanda.
    Ritorna 'aperte', 'chiuse', o None.
    """
    choice = None
    
    win = tk.Tk()
    win.title("Scegli Tipo")
    win.geometry("300x120")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    def set_choice(type):
        nonlocal choice
        choice = type
        win.destroy()

    tk.Label(win, text="Scegli il tipo di ritaglio:", font=("Helvetica", 12)).pack(pady=10)
    
    frame = tk.Frame(win)
    tk.Button(frame, text="Domande Aperte", command=lambda: set_choice("aperte"), width=15, height=2).pack(side='left', padx=10)
    tk.Button(frame, text="Domande Chiuse", command=lambda: set_choice("chiuse"), width=15, height=2).pack(side='left', padx=10)
    frame.pack(pady=5)

    win.mainloop()
    return choice

def main():
    """Funzione principale che gestisce lo stato e i listener."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        print("Impossibile impostare la modalità DPI-Aware.")

    # 1. Selezione cartella master
    dialog_root = tk.Tk()
    dialog_root.withdraw()
    base_directory = filedialog.askdirectory(title="Seleziona la cartella di base (es. la cartella della materia)")
    dialog_root.destroy()

    if not base_directory:
        print("Nessuna cartella selezionata. Uscita.")
        return

    # 2. NUOVO: Scelta del tipo di domanda
    question_type = ask_question_type()
    if not question_type:
        print("Nessuna scelta effettuata. Uscita.")
        return

    # 3. Preparazione dello stato in base alla scelta
    subfolder_name = f"immagini_estratte_domande_{question_type}"
    output_folder = os.path.join(base_directory, subfolder_name)
    os.makedirs(output_folder, exist_ok=True)
    
    shot_count = 1
    while os.path.exists(os.path.join(output_folder, f"{shot_count:03d}.png")):
        shot_count += 1

    app_state = {
        "output_folder": output_folder,
        "shot_count": shot_count
    }
    
    print(f"I ritagli verranno salvati in: '{app_state['output_folder']}'")
    print("\n--- Strumento di Ritaglio Pronto ---")
    print(f"Modalità: Domande {question_type.capitalize()}")
    print("Premi '1' per avviare un ritaglio.")
    print("Premi 'ESC' per uscire.")
    print("------------------------------------")

    def start_new_snip():
        print(f"Avvio ritaglio (progressivo n.{app_state['shot_count']:03d})...")
        tool = SnippingTool(app_state)
        tool.start()
        print("Pronto per il prossimo ritaglio. Premi '1' per iniziare.")

    keyboard.add_hotkey('1', start_new_snip)
    keyboard.add_hotkey('esc', lambda: os._exit(0))

    keyboard.wait()

if __name__ == '__main__':
    main()