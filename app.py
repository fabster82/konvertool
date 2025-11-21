# app.py (Streamlit-Frontend für bestehendes Tkinter-Programm)
# Hinweis: Originalprogramm bleibt unverändert. Diese Datei ist nur eine Web-Oberfläche.
from __future__ import annotations

import io
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="KonverTool (Web)", layout="wide")
st.title("KonverTool – Web UI")
st.caption("Excel **und** CSV als Eingabe, CSV-Export. Original-Logik bleibt unberührt.")

uploaded = st.file_uploader("Datei hochladen (Excel/CSV)", type=["xlsx","xls","csv"])
join_file = st.file_uploader("Optionale Referenzdatei (Excel/CSV) zum Mergen", type=["xlsx","xls","csv"])

col1, col2 = st.columns(2)
with col1:
    sep = st.selectbox("Export Separator", options=[",",";","\t","#"], index=3)
with col2:
    encoding = st.selectbox("Export Encoding", options=["utf-8","utf-8-sig","latin-1"], index=1)

def read_any(file) -> pd.DataFrame:
    name = (file.name or "").lower()
    if name.endswith(".csv"):
        data = file.read()
        return pd.read_csv(io.BytesIO(data), sep=None, engine="python", dtype=str, keep_default_na=False, na_values=[""])
    else:
        return pd.read_excel(file, dtype=str)

left_keys = right_keys = []
ref_df = None

if uploaded:
    df = read_any(uploaded)
    st.subheader("Vorschau")
    st.dataframe(df.head(20), use_container_width=True, height=260)

    if join_file:
        ref_df = read_any(join_file)
        st.subheader("Merge-Einstellungen")
        left_keys = st.multiselect("Join-Keys (Hauptdatei)", options=list(df.columns))
        right_keys = st.multiselect("Join-Keys (Referenz)", options=list(ref_df.columns))

    if st.button("Verarbeiten & CSV herunterladen", type="primary"):
        try:
            out = df
            if ref_df is not None and left_keys and right_keys and len(left_keys)==len(right_keys):
                out = out.merge(ref_df, how="left", left_on=left_keys, right_on=right_keys)
            # Export
            buf = io.StringIO()
            out.to_csv(buf, index=False, sep=sep)
            st.download_button("CSV herunterladen", data=buf.getvalue().encode(encoding, errors="replace"), file_name="ergebnis.csv", mime="text/csv")
            st.success(f"Fertig: {len(out):,} Zeilen.")
        except Exception as e:
            st.error(f"Fehler: {e}")
else:
    st.info("Bitte eine Datei hochladen (Excel oder CSV).")
