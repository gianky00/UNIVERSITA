import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfMerger
from pathlib import Path

class PdfMergerApp(tk.Toplevel):
    def __init__(self, parent, data_path: Path):
        super().__init__(parent)
        self.data_path = data_path
        self.title("Unificatore PDF per Materie")
        self.geometry("450x300")
        self.transient(parent)
        self.grab_set()

        # --- Dati per i menu a discesa ---
        self.materie_per_anno = {
            "1° Anno": [
                "FISICA", "FONDAMENTI DI INFORMATICA", "COMPLEMENTI DI MATEMATICA",
                "ANALISI MATEMATICA", "ANALISI NUMERICA", "ELETTROTECNICA", "LINGUA INGLESE A"
            ],
            "2° Anno": [
                "LINGUA INGLESE B", "MODELLISTICA E SIMULAZIONE", "FONDAMENTI DI AUTOMATICA",
                "CALCOLATORI ELETTRONICI E SISTEMI OPERATIVI", "SEGNALI E SISTEMI",
                "ALGORITMI E STRUTTURE DATI", "BASI DI DATI", "ELETTRONICA DEI SISTEMI DIGITALI"
            ],
            "3° Anno": [
                "AUTOMAZIONE INDUSTRIALE", "RETI DI TELECOMUNICAZIONI", "RICERCA OPERATIVA",
                "INGEGNERIA DEL SOFTWARE", "MISURE MECCANICHE E TERMICHE",
                "SISTEMI PER LA GESTIONE DEI DATI", "LINUX E RETI", "SISTEMI ELETTRONICI E MISURE"
            ]
        }
        self.tipi_documento = ["Slide", "Paniere"]

        # Variabili per memorizzare le selezioni dell'utente
        self.anno_selezionato = tk.StringVar(self)
        self.materia_selezionata = tk.StringVar(self)
        self.tipo_selezionato = tk.StringVar(self)

        self._create_widgets()

        # Imposta il valore predefinito per l'anno e il tipo
        self.anno_selezionato.set(list(self.materie_per_anno.keys())[0])
        self.tipo_selezionato.set(self.tipi_documento[0])

        # Collega la funzione di aggiornamento al cambio dell'anno
        self.anno_selezionato.trace("w", self.aggiorna_materie)

        # Chiamata iniziale per popolare il menu delle materie
        self.aggiorna_materie()

    def _create_widgets(self):
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        # Menu a discesa per l'ANNO
        tk.Label(main_frame, text="1. Seleziona l'Anno:").pack(anchor="w")
        anno_menu = tk.OptionMenu(main_frame, self.anno_selezionato, *self.materie_per_anno.keys())
        anno_menu.pack(fill="x", pady=(0, 10))

        # Menu a discesa per la MATERIA
        tk.Label(main_frame, text="2. Seleziona la Materia:").pack(anchor="w")
        self.materia_menu = tk.OptionMenu(main_frame, self.materia_selezionata, "") # Inizialmente vuoto
        self.materia_menu.pack(fill="x", pady=(0, 10))

        # Menu a discesa per il TIPO (Slide/Paniere)
        tk.Label(main_frame, text="3. Seleziona il Tipo di Documento:").pack(anchor="w")
        tipo_menu = tk.OptionMenu(main_frame, self.tipo_selezionato, *self.tipi_documento)
        tipo_menu.pack(fill="x", pady=(0, 20))

        # Pulsante per avviare il processo
        unisci_button = tk.Button(main_frame, text="Unisci PDF", command=self.crea_pdf_unito)
        unisci_button.pack(pady=10, ipady=5)

    def aggiorna_materie(self, *args):
        anno = self.anno_selezionato.get()
        materie = self.materie_per_anno[anno]

        self.materia_menu['menu'].delete(0, 'end')

        for materia in materie:
            self.materia_menu['menu'].add_command(label=materia, command=tk._setit(self.materia_selezionata, materia))

        if materie:
            self.materia_selezionata.set(materie[0])

    def crea_pdf_unito(self):
        anno = self.anno_selezionato.get()
        materia = self.materia_selezionata.get()
        tipo = self.tipo_selezionato.get()

        if not all([anno, materia, tipo]):
            messagebox.showwarning("Selezione mancante", "Per favore, seleziona Anno, Materia e Tipo di documento.", parent=self)
            return

        materia_formattata = materia.replace(' ', '_').replace('/', '-')

        # Costruisce il percorso basandosi sulla cartella dati configurata
        percorso_cartella = self.data_path / "pdf" / anno / materia_formattata / tipo
        percorso_cartella.mkdir(parents=True, exist_ok=True)

        try:
            # Cerca solo i file che non sono già un file unito
            file_pdf = [f for f in os.listdir(percorso_cartella) if f.endswith('.pdf') and not f.startswith(f"{tipo}_Complete_")]
            if not file_pdf:
                messagebox.showinfo("Nessun PDF trovato", f"Nessun file PDF da unire trovato in:\n\n{percorso_cartella}\n\nAssicurati di aver inserito i file in questa cartella.", parent=self)
                return
            file_pdf.sort()

            nome_file_output = f"{tipo}_Complete_{materia_formattata}.pdf"
            percorso_salvataggio = percorso_cartella / nome_file_output

            merger = PdfMerger()
            for pdf in file_pdf:
                percorso_completo = percorso_cartella / pdf
                merger.append(str(percorso_completo))

            with open(percorso_salvataggio, "wb") as file_unito:
                merger.write(file_unito)
            merger.close()

            conferma = messagebox.askyesno(
                "Operazione completata con successo!",
                f"File creato: {nome_file_output}\n\nVuoi eliminare i file PDF originali?",
                parent=self
            )

            if conferma:
                for pdf in file_pdf:
                    os.remove(percorso_cartella / pdf)
                messagebox.showinfo("File eliminati", "I file PDF originali sono stati eliminati.", parent=self)
            else:
                 messagebox.showinfo("Operazione completata", "I file originali non sono stati eliminati.", parent=self)

        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {e}", parent=self)

def main(parent, data_path: Path):
    """Initializes the PDF Merger application window as a Toplevel window."""
    app = PdfMergerApp(parent, data_path)
    app.focus_set()

if __name__ == "__main__":
    # This block allows the script to be run standalone for testing.
    root = tk.Tk()
    root.title("Main App")

    def launch_tool():
        # For standalone execution, use a default path
        default_data_path = Path(__file__).resolve().parent.parent.parent / "json"
        main(root, default_data_path)

    tk.Button(root, text="Launch PDF Merger", command=launch_tool).pack(padx=50, pady=50)
    root.mainloop()