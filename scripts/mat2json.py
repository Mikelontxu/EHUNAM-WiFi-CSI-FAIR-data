import scipy.io
import hashlib
import json
import pandas as pd
from pathlib import Path

def load_summary(summary_path: str = "data/Summary.xlsx") -> dict:
    """
    Carga el Excel summary y construye un índice {filename: {Date, Time}}
    para cruzar con cada .mat durante la extracción.
    """
    df = pd.read_excel(summary_path, sheet_name="Sheet1")
 
    index = {}
    for _, row in df.iterrows():
        filename = str(row["File"]).strip()
 
        # Date: puede venir como datetime o string
        date_val = row.get("Date")
        if pd.notna(date_val):
            if hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val).strip().split(" ")[0]  # quitar hora si viene junto
        else:
            date_str = None
 
        # Time: viene como string "HH:MM:SS"
        time_val = row.get("Time")
        if pd.notna(time_val):
            time_str = str(time_val).strip()
            # pandas puede leerlo como datetime.time → convertir a string
            if hasattr(time_val, "strftime"):
                time_str = time_val.strftime("%H:%M:%S")
        else:
            time_str = None
 
        index[filename] = { #buildea el índice con filename como clave
            "date_str": date_str,  
            "time_str": time_str,   
        }
 
    return index
 
 
def build_datetime(date_str: str, time_str: str) -> str | None:
    """
    Combina date_str ('2024-10-21') y time_str ('14:48:49')
    en un ISO 8601 datetime string: '2024-10-21T14:48:49'
    """
    if not date_str:
        return None
    if time_str:
        return f"{date_str}T{time_str}"
    return f"{date_str}T00:00:00"

# ── Parser del nombre del archivo ─────────────────────────────────────────────

def parse_filename(filename):
    """
    Parsea el nombre del archivo .mat y extrae los campos definidos a JSON.
    Formato: MC1_01A_2_PC_eabc_W_#_#_01.mat
    Fields:
        0 → campaign
        1 → set number + optional BW letter (A=20MHz, B=80MHz, none=80MHz)
        2 → receiver
        3 → application
        4 → people (one char per person)
        5 → activity
        6 → machine (# = not applicable)
        7 → status  (# = not applicable)
        8 → number (made to evade filename collisions)
    """
    base = filename.replace(".mat", "")
    parts = base.split("_")

    # Campo 1: set — extraer letra de BW si existe (A o B al final)
    set_field = parts[1]
    if set_field[-1] in ("A", "B"):
        bw_letter = set_field[-1]
        bandwidth = 20.0 if bw_letter == "A" else 80.0
    else:
        bw_letter = None
        bandwidth = 80.0  # sin letra = 80 MHz por defecto

    # Campo 6 y 7: machine y status pueden ser '#' (no aplica)
    machine_raw = parts[6] if len(parts) > 6 else "#"
    status_raw  = parts[7] if len(parts) > 7 else "#"

    # Campo 8: number (made to evade filename collisions)
    number_raw = parts[8] if len(parts) > 8 else None

    return {
        "campaign":   parts[0],
        "set":        f"{parts[0]}_{parts[1]}",
        "bw_letter":  bw_letter,
        "bandwidth":  bandwidth,
        "receiver":   parts[2],
        "application": parts[3],
        "people":     list(parts[4]),        # lista de chars, ej. ['e'] o ['a','b','c']
        "n_people_filename": len(parts[4]),  # número de personas según filename
        "activity":   parts[5],
        "machine":    None if machine_raw == "#" else machine_raw,
        "status":     None if status_raw  == "#" else status_raw,
        "number":     number_raw,
    }


def extract_metadata(filepath, summary_index: dict = None):
    """
    Extrae los metadatos de un archivo .mat, excluyendo las matrices grandes.
    Combina los metadatos del contenido con los del nombre del archivo.
    Devuelve un diccionario con todos los campos relevantes + checksum SHA-256.
    """
    filepath = Path(filepath)
    mat = scipy.io.loadmat(str(filepath))

    # Campos a excluir: matrices grandes + claves internas de scipy
    skip = {
    # Matrices grandes que se incluiran como archivos separados, no como metadatos en JSON
    "CSI", "RSSI", "TimeStamp",
    # Fecha/hora del .mat (objeto MCOS no parseable — se usa el summary)
    "Date", "Time",
    # Artefactos internos de scipy/MATLAB
    "__header__", "__version__", "__globals__",
    "__function_workspace__",
    # Objeto MCOS mal deserializado (aparece como clave "None")
    "None", None,
    }
    
    def serialize(v):
        """Convierte valores numpy a tipos Python nativos."""
        if hasattr(v, "tolist"):
            val = v.tolist()
            # Aplanar listas de un solo elemento
            if isinstance(val, list) and len(val) == 1:
                if isinstance(val[0], list) and len(val[0]) == 1:
                    return val[0][0]
                return val[0]
            return val
        return v

    metadata = {k: serialize(v) for k, v in mat.items() if k not in skip}

    # Fecha y hora desde el summary para evitar fallos de timestamp con uint32
    datetime_iso = None
    if summary_index:
        entry = summary_index.get(filepath.name)
        if entry:
            datetime_iso = build_datetime(entry["date_str"], entry["time_str"])
        else:
            print(f"  [!] '{filepath.name}' no encontrado en el summary")
 
    sha256 = hashlib.sha256(filepath.read_bytes()).hexdigest()     # Checksum SHA-256 del archivo completo
    filename_meta = parse_filename(filepath.name)               # Metadatos extraídos del nombre del archivo  

    return {
        "filepath":     str(filepath),
        "filename":     filepath.name,
        "sha256":       sha256,
        "datetime_iso": datetime_iso,   # "2024-10-21T14:48:49" — campo unificado para RDF
        **filename_meta,
        **metadata,
    }

def process_samples(
    samples_dir:  str = "data/samples",
    output_dir:   str = "output/json",
    summary_path: str = "data/Summary.xlsx",
):
    samples_path = Path(samples_dir)
    output_path  = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
 
    mat_files = sorted(samples_path.glob("*.mat"))
    if not mat_files:
        print(f"[!] No se encontraron archivos .mat en '{samples_dir}'")
        return
 
    # Cargar summary una sola vez
    summary_index = load_summary(summary_path)
    print(f"[✓] Summary cargado: {len(summary_index)} entradas")
    print(f"[✓] Encontrados {len(mat_files)} archivos .mat en '{samples_dir}'\n")
 
    for mat_file in mat_files:
        print(f"{'='*60}")
        print(f"Procesando: {mat_file.name}")
        try:
            result = extract_metadata(mat_file, summary_index)
            output_file = output_path / f"{mat_file.stem}.json"
            output_file.write_text(
                json.dumps(result, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(f"  datetime_iso: {result.get('datetime_iso')}")
            print(f"  Guardado: {output_file}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
 
 
if __name__ == "__main__":
    process_samples()