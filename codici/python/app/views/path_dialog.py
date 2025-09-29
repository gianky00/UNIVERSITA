import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

def ask_for_new_datapath(invalid_path: Path) -> Path | None:
    """
    Mostra un dialogo di errore e chiede all'utente di selezionare una nuova cartella dati.

    Args:
        invalid_path: Il percorso non valido che ha causato l'errore.

    Returns:
        Un nuovo percorso Path valido se selezionato, altrimenti None.
    """
    # Nasconde la finestra root principale di Tkinter
    root = tk.Tk()
    root.withdraw()

    # Messaggio di errore
    error_message = (
        f"Il percorso dati configurato non è stato trovato o non è accessibile:\n\n"
        f"{invalid_path}\n\n"
        "Potrebbe essere necessario collegare un'unità esterna o selezionare una nuova cartella."
    )

    # Mostra un avviso e chiede se l'utente vuole scegliere una nuova cartella
    response = messagebox.askokcancel(
        "Percorso Dati Non Valido",
        f"{error_message}\n\nVuoi scegliere una nuova cartella dati?"
    )

    if not response:
        # L'utente ha premuto "Annulla"
        messagebox.showinfo("Uscita", "L'applicazione verrà chiusa.")
        return None

    # Apre il selettore di cartelle
    new_path_str = filedialog.askdirectory(
        title="Seleziona la Nuova Cartella Dati",
        initialdir=Path.home()  # Parte dalla home dell'utente per comodità
    )

    if not new_path_str:
        # L'utente ha chiuso il selettore di cartelle
        messagebox.showinfo("Uscita", "Nessuna cartella selezionata. L'applicazione verrà chiusa.")
        return None

    return Path(new_path_str)