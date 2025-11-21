import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

from pathlib import Path

def _read_table(path: str) -> pd.DataFrame:
    """Erlaubt sowohl Excel als auch CSV. Verändert sonst keine Logik.
    Warum: Minimale Erweiterung für CSV-Input ohne Einfluss auf restliche Anwendung."""
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        try:
            # Versuch mit flexibler Trennzeichenerkennung
            return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], sep=None, engine="python")
        except Exception:
            # Fallback auf Standard-Komma
            return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], sep=",", engine="python")
    else:
        # Excel bleibt unverändert
        return _read_table(path, dtype=str)

from . import view as v

class Application(tk.Tk):
    """Konvertool konvertiert EXCEL-Dateien in ein entsprechendes CSV
    Format und gruppiert dabei nach einigen Regeln."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.title("Konvertool")
        self.geometry("500x800")
        self.resizable(width=True, height=True)

        """ Add views to the main window
        padx and pady in the grid methods defines the border around the widgets.
        """
        self.frame_active=0
        self.mv = v.MainView(self)
        self.mv.grid(sticky=(tk.N+tk.S+tk.E+tk.W))

        self.mv.but_load.config(command=self.load_file)
        self.mv.but_save.config(command=self.save_file)
        

    def load_file(self):
        try:
            filename = filedialog.askopenfilename()
        except:
            print("Could not open file")

        print("Öffne Datei",filename)
        
        if filename.rsplit(".",maxsplit=1)[1]=="xlsx":
            try:
                self.data = _read_table(filename)
            except:
                print("Datei kann nicht geöffnet werden!")
                self.quit()
            self.columns = list(self.data.columns)
            # The following lines will write the columns to the listboxes
            self.strvar_data_cols1 = tk.StringVar(value=self.columns)
            self.strvar_data_cols2 = tk.StringVar(value=self.columns)
            self.strvar_data_cols3 = tk.StringVar(value=self.columns)
            self.strvar_data_cols4 = tk.StringVar(value=self.columns)
            self.mv.lst_grouper.config(listvariable=self.strvar_data_cols1)
            self.mv.lst_concat.config(listvariable=self.strvar_data_cols2)
            self.mv.lst_maxmin.config(listvariable=self.strvar_data_cols3)
            self.mv.lst_semicolon.config(listvariable=self.strvar_data_cols4)
        else:
            print("Man hat mir nicht erklärt, wie man eine Datei mit der Endung",filename.rsplit(".",maxsplit=1)[1] ,"öffnet. Breche ab.")


    def save_file(self):
        idx_grouper = self.mv.lst_grouper.curselection()
        idx_concat = self.mv.lst_concat.curselection()
        idx_minmax = self.mv.lst_maxmin.curselection()
        idx_semicolon = self.mv.lst_semicolon.curselection()

        fixed_value = self.mv.lst_grouper.get(idx_grouper[0])
        target_cols = [self.mv.lst_grouper.get(i) for i in idx_concat]
        if len(idx_minmax)>0:
            minmax_cols = [self.mv.lst_maxmin.get(i) for i in idx_minmax]
        else:
            minmax_cols = []

        if len(idx_semicolon)>0:
            semicolon_cols = [self.mv.lst_semicolon.get(i) for i in idx_semicolon]
        else:
            semicolon_cols = []

        rows = []
        for item in self.data.groupby(fixed_value):
            row = []
            for col in self.columns:
                if col in semicolon_cols:
                    term = ';'
                else:
                    term = ''
                if col in target_cols:
                    # print(sorted(item[1][col].astype(str).unique()))
                    row.append(";".join(sorted(item[1][col].astype(str).unique())).replace('\n','')+term)
                elif col in minmax_cols:
                    try:
                        minmaxcol = item[1][col].astype(float)
                    except:
                        print("Kann Werte nicht in Zahlen Umwandeln!")
                        continue
                    row.append(str(minmaxcol.min()) + " - " + str(minmaxcol.max())+term)
                else:
                    row.append(str(item[1][col].iloc[0]).replace('\n','')+term)
            rows.append(row)
        results = pd.DataFrame(rows,columns=self.columns)
        try:
            filename = filedialog.asksaveasfilename()
        except:
            print("Could not get a filename to save...")

        results.to_csv(filename,index=None,sep="#")

        val = messagebox.showinfo("File saved...",f"Konvertierte Datei wurde als {filename} gespeichert.")
        print(val)
