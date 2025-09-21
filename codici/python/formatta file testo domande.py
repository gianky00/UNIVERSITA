import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def find_subject_folder(base_path, subject_name):
    """Cerca o crea la cartella della materia e ritorna il percorso."""
    # Pulisce il nome della materia da caratteri non validi per i nomi di cartella
    safe_subject_name = re.sub(r'[\\/*?:"<>|]', "", subject_name)
    
    # Cerca una cartella esistente con lo stesso nome (ignorando maiuscole/minuscole)
    for item in os.listdir(base_path):
        if os.path.isdir(os.path.join(base_path, item)) and item.lower() == safe_subject_name.lower():
            return os.path.join(base_path, item)
            
    # Se non la trova, la crea
    new_folder_path = os.path.join(base_path, safe_subject_name)
    os.makedirs(new_folder_path, exist_ok=True)
    return new_folder_path

def format_quiz_file(input_path, output_base_path):
    """Primo passaggio: elabora il paniere e crea i file con segnaposto XXX."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile leggere il file di input:\n{e}")
        return

    subject_name = "Sconosciuta"
    match = re.search(r"Set Domande\n([^\n]+)", content)
    if match:
        subject_name = match.group(1).strip()
    
    # Pulisce il nome della materia per usarlo nei nomi dei file
    safe_subject_name_for_file = re.sub(r'[\\/*?:"<>|]', "", subject_name)

    lines = content.split('\n')
    cleaned_lines = []
    ignore_patterns = [
        "Set Domande", "INGEGNERIA INDUSTRIALE", "Docente:", "© 2016 - 2024",
        "Lezione ", "N° Domande", "Indice", "Powered by TCPDF"
    ]
    for line in lines:
        if not line.strip() or any(pattern in line for pattern in ignore_patterns):
            continue
        cleaned_lines.append(line)

    full_text = "\n".join(cleaned_lines)
    # Lo split ora cerca un numero di due cifre, un punto e uno spazio all'inizio di una riga
    question_blocks = re.split(r'\n(?=\d{2}\.\s)', full_text)

    open_questions, closed_questions_formatted = [], []
    for block in question_blocks:
        if not block.strip(): continue
        lines = [line for line in block.strip().split('\n') if line.strip()]
        question_lines, option_lines = [], []
        
        # Identifica le opzioni in base al fatto che inizino con uno spazio
        is_question_part = True
        for line in lines:
            if line.startswith(" ") and len(question_lines) > 0:
                is_question_part = False
            
            if is_question_part:
                 question_lines.append(line.strip())
            else:
                 option_lines.append(line.strip())

        full_question_text = " ".join(question_lines)
        if option_lines:
            formatted_block = [f"# {full_question_text}"]
            if 'in figura' in full_question_text.lower():
                formatted_block.append("[image: XXX.png]")
            formatted_block.extend(option_lines)
            closed_questions_formatted.append("\n".join(formatted_block))
        else:
            open_questions.append(full_question_text)

    output_folder = find_subject_folder(output_base_path, subject_name)
    
    output_closed_path = os.path.join(output_folder, f"domande chiuse {safe_subject_name_for_file}.txt")
    with open(output_closed_path, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(closed_questions_formatted))

    if open_questions:
        output_open_path = os.path.join(output_folder, f"domande aperte {safe_subject_name_for_file}.txt")
        with open(output_open_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(open_questions))
    
    messagebox.showinfo("Successo", f"Elaborazione completata!\nFile salvati nella cartella '{os.path.basename(output_folder)}'.")

def renumber_images_in_file(file_path):
    """Secondo passaggio: numera progressivamente i segnaposto [image: XXX.png]."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        counter = 1
        def replacer(match):
            nonlocal counter
            new_number = f"{counter:03d}"
            counter += 1
            return f"[image: {new_number}.png]"

        new_content = re.sub(r"\[image: XXX\.png\]", replacer, content, flags=re.IGNORECASE)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        messagebox.showinfo("Successo", f"Numerazione completata!\nSostituiti {counter - 1} segnaposto nel file:\n{os.path.basename(file_path)}")

    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile numerare le immagini:\n{e}")

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tool Paniere")
        self.geometry("400x250")
        
        # Memorizza l'ultimo percorso di output usato
        self.output_path = ""

        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(expand=True, fill='both')

        tk.Label(main_frame, text="Tool di Elaborazione Paniere", font=("Helvetica", 14, "bold")).pack(pady=(0, 20))
        
        tk.Button(main_frame, text="1. Elabora File Paniere", command=self.process_paniere, height=2, bg="#cce5ff", fg="black").pack(fill='x', pady=5)
        tk.Button(main_frame, text="2. Numera Immagini nel File", command=self.renumber_images, height=2, bg="#d4edda", fg="black").pack(fill='x', pady=5)

    def process_paniere(self):
        input_file = filedialog.askopenfilename(title="Seleziona il file .txt del paniere sorgente")
        if not input_file:
            return
            
        # Chiede all'utente di selezionare la cartella di destinazione
        output_folder = filedialog.askdirectory(title="Seleziona la cartella di destinazione per i file elaborati")
        if not output_folder:
            return
        
        # Salva il percorso per usi futuri (es. per il secondo bottone)
        self.output_path = output_folder
            
        format_quiz_file(input_file, self.output_path)

    def renumber_images(self):
        choice = self.ask_type_choice()
        if not choice:
            return
        
        # Usa il percorso salvato come directory iniziale, se esiste
        initial_dir = self.output_path if self.output_path and os.path.isdir(self.output_path) else "/"

        file_to_renumber = filedialog.askopenfilename(
            title=f"Seleziona il file 'domande {choice}...'",
            initialdir=initial_dir
        )
        if not file_to_renumber:
            return
        
        renumber_images_in_file(file_to_renumber)

    def ask_type_choice(self):
        choice = tk.StringVar()
        
        win = tk.Toplevel(self)
        win.title("Scegli Tipo")
        win.geometry("300x120")
        win.resizable(False, False)
        win.transient(self) 
        win.grab_set() 

        def set_choice(type):
            choice.set(type)
            win.destroy()

        tk.Label(win, text="Su quale file vuoi numerare le immagini?", font=("Helvetica", 10)).pack(pady=10)
        
        frame = tk.Frame(win)
        tk.Button(frame, text="Domande Aperte", command=lambda: set_choice("aperte"), width=15, height=2).pack(side='left', padx=10)
        tk.Button(frame, text="Domande Chiuse", command=lambda: set_choice("chiuse"), width=15, height=2).pack(side='left', padx=10)
        frame.pack(pady=5)
        
        self.wait_window(win)
        return choice.get()

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()