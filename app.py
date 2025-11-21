# app.py  (vollständig, drop-in)
from __future__ import annotations

import io
import csv
from typing import Optional, Tuple
import pandas as pd
import streamlit as st

# ---------------- UI ----------------
st.set_page_config(page_title="KonverTool – Web UI", layout="wide")
st.title("KonverTool – Web UI")
st.caption("Excel **und** CSV als Eingabe, optionales Merge, CSV-Export – Original-Logik bleibt unberührt.")

uploaded = st.file_uploader("Hauptdatei (Excel/CSV)", type=["xlsx", "xls", "csv"])
join_file = st.file_uploader("Referenzdatei (optional, Excel/CSV)", type=["xlsx", "xls", "csv"])

with st.expander("Import-Optionen (nur für CSV)", expanded=False):
    user_sep = st.selectbox(
        "CSV-Trennzeichen (optional, leer = automatische Erkennung)",
        options=["(auto)", ";", ",", "\\t", "|"],
        index=0,
        help="Bei Parser-Fehlern hier explizit wählen.",
    )
    user_sep = None if user_sep == "(auto)" else ("\t" if user_sep == "\\t" else user_sep)
    on_bad_lines = st.selectbox(
        "Ungültige Zeilen",
        options=["skip", "error"],
        index=0,
        help="Bei krummen Zeilen 'skip' wählen, um Fehler zu vermeiden.",
    )

col1, col2 = st.columns(2)
with col1:
    out_sep = st.selectbox("Export: Trennzeichen", options=[",", ";", "\\t", "|"], index=1)
    out_sep = "\t" if out_sep == "\\t" else out_sep
with col2:
    out_enc = st.selectbox("Export: Encoding", options=["utf-8", "utf-8-sig", "latin-1"], index=1)

# -------------- CSV/Excel robust lesen --------------
def _detect_encoding(b: bytes) -> list[str]:
    """Kleine, harte Fallback-Kette – ohne Zusatz-Abhängigkeiten."""
    # Reihenfolge nach Praxis-Häufigkeit
    return ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

def _sniff_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        # Heuristik: nehme das Zeichen mit den meisten Treffer
        counts = {d: sample_text.count(d) for d in [",", ";", "\t", "|"]}
        return max(counts, key=counts.get) or ","

def _read_csv_robust(b: bytes, user_sep: Optional[str], on_bad_lines: str) -> pd.DataFrame:
    encodings = _detect_encoding(b)
    sample = None
    # 1) Wenn Benutzer-Trennzeichen gesetzt → direkt probieren (C-Engine schnell)
    if user_sep:
        for enc in encodings:
            try:
                return pd.read_csv(
                    io.BytesIO(b),
                    encoding=enc,
                    sep=user_sep,
                    dtype=str,
                    keep_default_na=False,
                    na_values=[""],
                    engine="c",
                    on_bad_lines=on_bad_lines,
                )
            except Exception:
                continue  # Fallback auf nächste Kodierung

    # 2) Auto: Sniffer + Python-Engine (kann gemischte CSVs besser)
    for enc in encodings:
        try:
            sample = b[:200_000].decode(enc, errors="replace")
            sep = _sniff_delimiter(sample)
            df = pd.read_csv(
                io.BytesIO(b),
                encoding=enc,
                sep=sep,
                dtype=str,
                keep_default_na=False,
                na_values=[""],
                engine="python",
                on_bad_lines=on_bad_lines,
            )
            # Wenn nur 1 Spalte rauskam, war Sep evtl. falsch → Fallbacks
            if df.shape[1] >= 2:
                return df
        except Exception:
            pass

    # 3) Harte Fallback-Schleife über Delimiter (C-Engine)
    for enc in encodings:
        for sep in [";", ",", "\t", "|"]:
            try:
                df = pd.read_csv(
                    io.BytesIO(b),
                    encoding=enc,
                    sep=sep,
                    dtype=str,
                    keep_default_na=False,
                    na_values=[""],
                    engine="c",
                    on_bad_lines=on_bad_lines,
                )
                if df.shape[1] >= 1:
                    return df
            except Exception:
                continue

    # 4) Letzter Versuch: QUOTE_NONE + Escape (für „schmutzige“ CSVs)
    for enc in encodings:
        try:
            return pd.read_csv(
                io.BytesIO(b),
                encoding=enc,
                sep=user_sep or ",",
                dtype=str,
                keep_default_na=False,
                na_values=[""],
                engine="python",
                on_bad_lines=on_bad_lines,
                quoting=csv.QUOTE_NONE,
                escapechar="\\",
            )
        except Exception:
            continue

    raise ValueError("CSV konnte nicht robust geparst werden (bitte Separator im Import-Abschnitt setzen).")

def _read_any(uploaded_file) -> pd.DataFrame:
    name = (uploaded_file.name or "").lower()
    if name.endswith(".csv"):
        data = uploaded_file.getvalue()  # wichtig: nicht .read(), sonst ist der Stream leer beim 2. Zugriff
        return _read_csv_robust(data, user_sep=user_sep, on_bad_lines=on_bad_lines)
    # Excel unverändert
    return pd.read_excel(uploaded_file, dtype=str)

# -------------- App-Logik (unverändert außer Nutzung _read_any) --------------
left_keys = []
right_keys = []
ref_df = None

if uploaded:
    df = _read_any(uploaded)
    st.subheader("Vorschau Hauptdatei")
    st.dataframe(df.head(20), use_container_width=True, height=260)

    if join_file:
        ref_df = _read_any(join_file)
        st.subheader("Merge-Einstellungen")
        left_keys = st.multiselect("Join-Keys (Hauptdatei)", options=list(df.columns))
        right_keys = st.multiselect("Join-Keys (Referenz)", options=list(ref_df.columns))

    if st.button("Verarbeiten & CSV herunterladen", type="primary"):
        try:
            out = df
            if ref_df is not None and left_keys and right_keys and len(left_keys) == len(right_keys):
                out = out.merge(ref_df, how="left", left_on=left_keys, right_on=right_keys)
            buf = io.StringIO()
            out.to_csv(buf, index=False, sep=out_sep)
            st.download_button(
                "CSV herunterladen",
                data=buf.getvalue().encode(out_enc, errors="replace"),
                file_name="ergebnis.csv",
                mime="text/csv",
            )
            st.success(f"Fertig: {len(out):,} Zeilen.")
        except Exception as e:
            st.error(f"Fehler: {e}")
else:
    st.info("Bitte eine Datei hochladen (Excel oder CSV).")


# ---------------- (Empfohlen) requirements.txt ----------------
# streamlit>=1.36
# pandas>=2.2
# openpyxl>=3.1

# ---------------- (Empfohlen) runtime.txt ----------------
# python-3.11
