import tkinter as tk
from tkinter import ttk

class MainView(tk.Frame):
    """Main view of the application"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.but_load = ttk.Button(text="Datei öffnen...")
        self.but_load.grid(column=1,row=0)

        lbl_sel_grp = ttk.Label(text="Gruppieren nach:")
        lbl_sel_grp.grid(column=0,row=1)

        self.lst_grouper = tk.Listbox(exportselection=False)
        self.lst_grouper.grid(column=1,row=1)

        lbl_sel_cmb = ttk.Label(text="Feld verketten:")
        lbl_sel_cmb.grid(column=0,row=2)

        self.lst_concat = tk.Listbox(selectmode="multiple",exportselection=False)
        self.lst_concat.grid(column=1,row=2)

        lbl_sel_maxmin = ttk.Label(text="Min und max anzeigen:")
        lbl_sel_maxmin.grid(column=0,row=3)

        self.lst_maxmin = tk.Listbox(selectmode="multiple",exportselection=False)
        self.lst_maxmin.grid(column=1,row=3)

        lbl_sel_semicolon = ttk.Label(text="Zelle mit Semikolon terminieren:")
        lbl_sel_semicolon.grid(column=0,row=4)

        self.lst_semicolon = tk.Listbox(selectmode="multiple",exportselection=False)
        self.lst_semicolon.grid(column=1,row=4)

        self.but_save = ttk.Button(text="Konvertierte Datei speichern unter...")
        self.but_save.grid(column=1,row=5)
        parent.update_idletasks()
        self.columnconfigure(1,weight=1)


    def get(self):
        data = {}
        for key, widget in self.inputs.items():
            if type(widget) == list:
                data[key] = []
                for cnt in range(len(widget)):
                    data[key].append(widget[cnt].get())
            else:
                data[key] = widget.get()
        return data

