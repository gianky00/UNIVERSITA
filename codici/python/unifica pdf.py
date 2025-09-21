import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfMerger

# --- Dati per i menu a discesa ---
materie_per_anno = {
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
tipi_documento = ["Slide", "Paniere"]

def aggiorna_materie(*args):
    """
    Callback per aggiornare l'elenco delle materie quando cambia l'anno selezionato.
    """
    anno = anno_selezionato.get()
    materie = materie_per_anno[anno]
    
    # Pulisce il menu a discesa delle materie
    materia_menu['menu'].delete(0, 'end')
    
    # Aggiunge le nuove materie al menu
    for materia in materie:
        materia_menu['menu'].add_command(label=materia, command=tk._setit(materia_selezionata, materia))
        
    # Imposta la prima materia della lista come valore predefinito
    if materie:
        materia_selezionata.set(materie[0])

def crea_pdf_unito():
    """
    Funzione principale che unisce i PDF in base alle selezioni della GUI.
    """
    # Controlla che tutti i campi siano stati selezionati
    if not anno_selezionato.get() or not materia_selezionata.get() or not tipo_selezionato.get():
        messagebox.showwarning("Selezione mancante", "Per favore, seleziona Anno, Materia e Tipo di documento.")
        return

    # 1. Seleziona la cartella
    percorso_cartella = filedialog.askdirectory(title="Seleziona la cartella con i PDF da unire")
    if not percorso_cartella:
        return # L'utente ha annullato

    try:
        # 2. Trova e ordina i PDF
        file_pdf = [f for f in os.listdir(percorso_cartella) if f.endswith('.pdf')]
        if not file_pdf:
            messagebox.showinfo("Nessun PDF trovato", "Nella cartella selezionata non sono presenti file PDF.")
            return
        file_pdf.sort()

        # 3. Genera il nome del file di output
        tipo = tipo_selezionato.get()
        materia = materia_selezionata.get()
        # Sostituisce gli spazi con underscore per un nome file pulito
        materia_formattata = materia.replace(' ', '_')
        nome_file_output = f"{tipo}_Complete_{materia_formattata}.pdf"
        
        # Il percorso di salvataggio è la stessa cartella di origine
        percorso_salvataggio = os.path.join(percorso_cartella, nome_file_output)

        # 4. Unisci i PDF
        merger = PdfMerger()
        for pdf in file_pdf:
            percorso_completo = os.path.join(percorso_cartella, pdf)
            merger.append(percorso_completo)
        
        with open(percorso_salvataggio, "wb") as file_unito:
            merger.write(file_unito)
        merger.close()

        # 5. Chiedi se eliminare i file originali
        conferma = messagebox.askyesno(
            "Operazione completata con successo!",
            f"File creato: {nome_file_output}\n\nVuoi eliminare i file PDF originali?"
        )

        if conferma:
            for pdf in file_pdf:
                os.remove(os.path.join(percorso_cartella, pdf))
            messagebox.showinfo("File eliminati", "I file PDF originali sono stati eliminati.")
        else:
             messagebox.showinfo("Operazione completata", "I file originali non sono stati eliminati.")


    except Exception as e:
        messagebox.showerror("Errore", f"Si è verificato un errore: {e}")

# --- Creazione dell'interfaccia grafica (GUI) ---
root = tk.Tk()
root.title("Unificatore PDF per Materie")
root.geometry("450x300")

# Variabili per memorizzare le selezioni dell'utente
anno_selezionato = tk.StringVar(root)
materia_selezionata = tk.StringVar(root)
tipo_selezionato = tk.StringVar(root)

# Imposta il valore predefinito per l'anno e il tipo
anno_selezionato.set(list(materie_per_anno.keys())[0])
tipo_selezionato.set(tipi_documento[0])

# --- Layout della GUI ---
main_frame = tk.Frame(root, padx=20, pady=20)
main_frame.pack(expand=True, fill="both")

# Menu a discesa per l'ANNO
tk.Label(main_frame, text="1. Seleziona l'Anno:").pack(anchor="w")
anno_menu = tk.OptionMenu(main_frame, anno_selezionato, *materie_per_anno.keys())
anno_menu.pack(fill="x", pady=(0, 10))

# Menu a discesa per la MATERIA
tk.Label(main_frame, text="2. Seleziona la Materia:").pack(anchor="w")
materia_menu = tk.OptionMenu(main_frame, materia_selezionata, "") # Inizialmente vuoto
materia_menu.pack(fill="x", pady=(0, 10))

# Menu a discesa per il TIPO (Slide/Paniere)
tk.Label(main_frame, text="3. Seleziona il Tipo di Documento:").pack(anchor="w")
tipo_menu = tk.OptionMenu(main_frame, tipo_selezionato, *tipi_documento)
tipo_menu.pack(fill="x", pady=(0, 20))

# Pulsante per avviare il processo
unisci_button = tk.Button(main_frame, text="Seleziona Cartella e Crea PDF", command=crea_pdf_unito)
unisci_button.pack(pady=10, ipady=5)

# Collega la funzione di aggiornamento al cambio dell'anno
anno_selezionato.trace("w", aggiorna_materie)

# Chiamata iniziale per popolare il menu delle materie
aggiorna_materie()

# Avvia il loop principale della GUI
root.mainloop()