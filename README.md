# KonverTool (Tkinter lokal) + Web UI (Streamlit)

- **Original** bleibt unverändert (Tkinter).
- **Web UI**: `app.py` (Streamlit) akzeptiert Excel/CSV, optional Merge, CSV-Export.

## Lokal starten
```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub & Streamlit Cloud
1. Neues Repo anlegen und diesen Ordner pushen.
2. In Streamlit Cloud: **New app** → Repo/Branch wählen → **Main file path:** `app.py` → Deploy.
