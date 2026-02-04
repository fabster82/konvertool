# app.py — KonverTool Web (UI wie Desktop)
from __future__ import annotations
import io, csv
from typing import Optional, Iterable
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Konvertool – Web", layout="wide")
st.title("Konvertool")
st.caption("UI analog Desktop: Datei öffnen → Gruppieren → Feld verketten → Min/Max → Zellen terminieren → Speichern")

# -------------------- Upload --------------------
uploaded = st.file_uploader("Datei öffnen...", type=["xlsx","xls","csv"])

@st.cache_data(show_spinner=False)
def read_any(b: bytes, name: str) -> pd.DataFrame:
    name = (name or "").lower()
    if name.endswith(".csv"):
        # Robust CSV-Reader (Delimeter/Encoding heuristics)
        encodings = ["utf-8","utf-8-sig","cp1252","latin-1"]
        for enc in encodings:
            try:
                # Sniff delimiter
                sample = b[:200_000].decode(enc, errors="replace")
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=[",",";","\t","|"])
                    sep = dialect.delimiter
                except Exception:
                    sep = max([",",";","\t","|"], key=sample.count)
                df = pd.read_csv(io.BytesIO(b), encoding=enc, sep=sep, dtype=str, keep_default_na=False, na_values=[""], engine="python", on_bad_lines="skip")
                if df.shape[1] >= 1:
                    return df
            except Exception:
                continue
        # Fallback
        return pd.read_csv(io.BytesIO(b), encoding="latin-1", sep=";", dtype=str, keep_default_na=False, na_values=[""], engine="python", on_bad_lines="skip")
    else:
        return pd.read_excel(io.BytesIO(b), dtype=str)

if not uploaded:
    st.info("Bitte eine Datei (Excel/CSV) hochladen.")
    st.stop()

df = read_any(uploaded.getvalue(), uploaded.name)
st.subheader("Vorschau")
st.dataframe(df.head(20), use_container_width=True, height=260)

# -------------------- UI: Einstellungen --------------------
st.markdown("### Gruppieren nach:")
cols = list(df.columns)
group_cols = st.multiselect("Gruppieren nach:", options=cols, default=[])

st.markdown("### Feld verketten:")
concat_cols = st.multiselect("Feld verketten:", options=[c for c in cols if c not in group_cols], default=[],
                             help="Für diese Spalten werden Werte innerhalb jeder Gruppe zu einem einzigen Feld zusammengeführt (Duplikate entfernt).")

st.markdown("### Min und max anzeigen:")
minmax_cols = st.multiselect("Min und max anzeigen:", options=[c for c in cols if c not in group_cols], default=[],
                             help="Für diese Spalten wird je Gruppe 'min - max' berechnet (numerische Konvertierung).")

st.markdown("### Zelle mit Semikolon terminieren:")
term_all = st.checkbox("Alle Spalten terminieren", value=False)
term_cols = []
if not term_all:
    term_cols = st.multiselect("Semikolon für folgende Spalten anhängen:", options=cols, default=[])

st.markdown("### Sonstige Einstellungen")
out_sep = st.selectbox("Export-Trennzeichen", options=["#", ";", ",", "\t", "|"], index=0)
out_sep = "\t" if out_sep == "\t" else out_sep
out_order = st.multiselect("Ausgabe-Spalten (Reihenfolge)", options=cols, default=group_cols + [c for c in cols if c not in group_cols])

# -------------------- Verarbeitung --------------------
def aggregate_group(g: pd.DataFrame) -> dict:
    row = {}
    for col in out_order:
        val = None
        if col in concat_cols:
            s = g[col].astype(str)
            # warum: Whitespace normalisieren, Duplikate stabil entfernen, dann mit | verketten
            vals = [x.replace("\n"," ").strip() for x in s if x is not None and str(x) != ""]
            seen = set()
            uniq = []
            for x in vals:
                if x not in seen:
                    seen.add(x); uniq.append(x)
            val = "|".join(uniq)  # <- geändert: Pipe statt Leerzeichen
        elif col in minmax_cols:
            s = pd.to_numeric(g[col].str.replace(",",".", regex=False), errors="coerce").dropna()
            if len(s) == 0:
                val = ""
            else:
                val = f"{s.min()} - {s.max()}"
        else:
            # erstes nicht-leeres Element
            s = g[col].astype(str)
            v = next((x for x in s if x is not None and str(x) != ""), "")
            val = str(v).replace("\n","")
        if term_all or (col in term_cols):
            val = f"{val};" if val != "" else ";"
        row[col] = val
    return row

st.divider()
if st.button("Konvertierte Datei speichern…", type="primary"):
    if not group_cols:
        st.error("Bitte zuerst 'Gruppieren nach' auswählen.")
    else:
        grouped = df.groupby(group_cols, dropna=False, sort=False)
        out_rows = []
        for _, g in grouped:
            out_rows.append(aggregate_group(g))
        out_df = pd.DataFrame(out_rows, columns=out_order)
        buf = io.StringIO()
        out_df.to_csv(buf, index=False, sep=out_sep)
        st.success(f"Fertig. Zeilen: {len(out_df):,}")
        st.download_button("CSV herunterladen", data=buf.getvalue().encode("utf-8-sig"), file_name="konvertiert.csv", mime="text/csv")
