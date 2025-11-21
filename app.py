# app.py
# Streamlit-App: CSV/Excel Upload, große CSVs chunkweise verarbeiten, Merge, CSV-Export
from __future__ import annotations

import io
import csv
from dataclasses import dataclass
from typing import Generator, Optional
import pandas as pd
import streamlit as st

DEFAULT_CHUNKSIZE = 200_000
SNIFF_BYTES = 100_000

@dataclass
class CSVFormat:
    encoding: str
    delimiter: str
    quotechar: str | None

def detect_csv_format(file_bytes: bytes) -> CSVFormat:
    encoding = "utf-8"
    try:
        file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            file_bytes.decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            encoding = "latin-1"
    sample = file_bytes[:SNIFF_BYTES].decode(encoding, errors="replace")
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample)
        delimiter = dialect.delimiter
        quotechar = getattr(dialect, "quotechar", None)
    except Exception:
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
        quotechar = '"'
    return CSVFormat(encoding=encoding, delimiter=delimiter, quotechar=quotechar)

def read_csv_in_chunks(uploaded: io.BytesIO, fmt: CSVFormat, chunksize: int):
    uploaded.seek(0)
    for chunk in pd.read_csv(
        uploaded,
        encoding=fmt.encoding,
        sep=fmt.delimiter,
        quotechar=fmt.quotechar or '"',
        chunksize=chunksize,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        engine="python",
        header=0,
    ):
        yield chunk

def read_csv_all(uploaded: io.BytesIO, fmt: CSVFormat) -> pd.DataFrame:
    uploaded.seek(0)
    return pd.read_csv(
        uploaded,
        encoding=fmt.encoding,
        sep=fmt.delimiter,
        quotechar=fmt.quotechar or '"',
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        engine="python",
        header=0,
    )

def read_excel(uploaded: io.BytesIO, sheet_name: str | int | None) -> pd.DataFrame:
    uploaded.seek(0)
    if sheet_name is None:
        xls = pd.ExcelFile(uploaded)
        sheet_name = xls.sheet_names[0]
        uploaded.seek(0)
    uploaded.seek(0)
    return pd.read_excel(uploaded, sheet_name=sheet_name, dtype=str)

def merge_chunk_with_ref(left_chunk, right_ref, keys_left, keys_right, how: str):
    return left_chunk.merge(right_ref, how=how, left_on=keys_left, right_on=keys_right)

st.set_page_config(page_title="KonverTool – CSV/Excel Merge", layout="wide")
st.title("KonverTool – CSV/Excel Analyse & Merge")
st.caption("Große CSVs chunkweise verarbeiten, Excel & CSV als Eingabe, Export als CSV.")

with st.sidebar:
    st.header("Eingabedateien")
    main_file = st.file_uploader("Hauptdatei (CSV/Excel)", type=["csv","xlsx","xls"])
    ref_file = st.file_uploader("Referenzdatei (optional, CSV/Excel)", type=["csv","xlsx","xls"])
    chunksize = st.number_input("Chunksize für große CSVs", min_value=10_000, max_value=2_000_000, step=50_000, value=DEFAULT_CHUNKSIZE)
    join_type = st.selectbox("Join-Typ", options=["inner","left","right","outer"], index=1)
    st.subheader("Export")
    out_delim = st.selectbox("CSV-Trennzeichen", [",",";","\t"], index=1)
    out_encoding = st.selectbox("Encoding", ["utf-8","utf-8-sig","latin-1"], index=1)

if not main_file:
    st.info("Bitte Hauptdatei hochladen (CSV/Excel).")
    st.stop()

def infer_kind(uploaded) -> str:
    name = (uploaded.name or "").lower()
    if name.endswith(".csv"): return "csv"
    if name.endswith(".xlsx") or name.endswith(".xls"): return "excel"
    mime = uploaded.type or ""
    if "csv" in mime: return "csv"
    if "excel" in mime or "spreadsheet" in mime: return "excel"
    return "csv"

main_kind = infer_kind(main_file)
ref_kind = infer_kind(ref_file) if ref_file else None

main_sheet = None
ref_sheet = None
if main_kind == "excel":
    with st.expander("Hauptdatei – Excel-Optionen", expanded=True):
        ef = pd.ExcelFile(main_file)
        main_sheet = st.selectbox("Excel-Sheet (Hauptdatei)", ef.sheet_names)
if ref_file and ref_kind == "excel":
    with st.expander("Referenz – Excel-Optionen", expanded=False):
        ef2 = pd.ExcelFile(ref_file)
        ref_sheet = st.selectbox("Excel-Sheet (Referenz)", ef2.sheet_names)

main_preview = None
if main_kind == "csv":
    b = main_file.getvalue()
    fmt = detect_csv_format(b)
    st.write(f"**Erkannt (Hauptdatei):** Encoding=`{fmt.encoding}`, Delimiter=`{fmt.delimiter}`")
    preview_df = read_csv_all(io.BytesIO(b[:100_000]), fmt)
    main_preview = preview_df.head(20)
    main_cols = list(main_preview.columns)
else:
    df = read_excel(main_file, main_sheet)
    main_preview = df.head(20)
    main_cols = list(df.columns)

st.subheader("Vorschau Hauptdatei")
st.dataframe(main_preview, use_container_width=True, height=240)

ref_df = None
if ref_file:
    if ref_kind == "csv":
        ref_bytes = ref_file.getvalue()
        ref_fmt = detect_csv_format(ref_bytes)
        st.write(f"**Erkannt (Referenz):** Encoding=`{ref_fmt.encoding}`, Delimiter=`{ref_fmt.delimiter}`")
        ref_df = read_csv_all(io.BytesIO(ref_bytes), ref_fmt)
    else:
        ref_df = read_excel(ref_file, ref_sheet)
    for c in ref_df.columns:
        ref_df[c] = ref_df[c].astype(str)

if ref_df is not None:
    st.subheader("Merge-Einstellungen")
    left_keys = st.multiselect("Join-Keys (Hauptdatei)", options=main_cols)
    right_keys = st.multiselect("Join-Keys (Referenz)", options=list(ref_df.columns))
    if left_keys and right_keys and len(left_keys) != len(right_keys):
        st.warning("Die Anzahl der Keys muss übereinstimmen.")
        st.stop()
else:
    left_keys, right_keys = [], []

st.divider()
col_a, col_b = st.columns([1,2])
with col_a:
    start_btn = st.button("Verarbeiten & Ergebnis erzeugen", type="primary")
with col_b:
    status = st.empty()
progress = st.progress(0)

output_buffer = io.StringIO()
wrote_header = False
rows_out = 0

if start_btn:
    try:
        if main_kind == "excel":
            main_df = read_excel(main_file, main_sheet)
            for c in main_df.columns:
                main_df[c] = main_df[c].astype(str)
            if ref_df is not None and left_keys:
                main_df = merge_chunk_with_ref(main_df, ref_df, left_keys, right_keys, how=join_type)
            main_df.to_csv(output_buffer, index=False, sep=out_delim, encoding=out_encoding)
            rows_out = len(main_df)
            progress.progress(100)
            status.success(f"Fertig. Zeilen im Ergebnis: {rows_out:,}")
        else:
            main_bytes = main_file.getvalue()
            fmt = detect_csv_format(main_bytes)
            total_size = len(main_bytes) or 1
            processed_size = 0
            for i, chunk in enumerate(read_csv_in_chunks(io.BytesIO(main_bytes), fmt, chunksize=chunksize)):
                for c in chunk.columns:
                    chunk[c] = chunk[c].astype(str)
                if ref_df is not None and left_keys:
                    chunk = merge_chunk_with_ref(chunk, ref_df, left_keys, right_keys, how=join_type)
                chunk.to_csv(output_buffer, index=False, sep=out_delim, header=not wrote_header, encoding=out_encoding, mode="a")
                wrote_header = True
                rows_out += len(chunk)
                processed_size = min(total_size, processed_size + chunksize * 100)
                pct = int(100 * processed_size / total_size)
                progress.progress(min(100, max(1, pct)))
                status.info(f"Verarbeite… Chunks: {i+1}, Zeilen bisher: {rows_out:,}")
            status.success(f"Fertig. Zeilen im Ergebnis: {rows_out:,}")
            progress.progress(100)
    except Exception as exc:
        st.error(f"Fehler: {exc}")
        st.stop()

    st.subheader("Ergebnis herunterladen")
    result_bytes = output_buffer.getvalue().encode(out_encoding, errors="replace")
    st.download_button(label=f"CSV herunterladen ({rows_out:,} Zeilen)", data=result_bytes, file_name="ergebnis.csv", mime="text/csv")

with st.expander("Tipps & Hinweise"):
    st.markdown(
        """
        - Für sehr große Merges sollte die **Referenztabelle kleiner** sein (liegt komplett im RAM).
        - Wenn **beide** Dateien groß sind: Wir können eine Sort-Merge-Strategie oder eine DB (DuckDB) ergänzen.
        - Umlaute/ß-Probleme? Stelle das **Encoding** im Export auf `utf-8-sig` oder `latin-1`.
        - Separator falsch erkannt? Die Erkennung ist robust, ggf. Datei mit korrektem Separator neu exportieren.
        """
    )
