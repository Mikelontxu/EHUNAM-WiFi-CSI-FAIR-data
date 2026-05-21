import scipy.io
import hashlib
import json
import os
from pathlib import Path


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


def extract_metadata(filepath):
    """
    Extrae los metadatos de un archivo .mat, excluyendo las matrices grandes.
    Combina los metadatos del contenido con los del nombre del archivo.
    Devuelve un diccionario con todos los campos relevantes + checksum SHA-256.
    """
    filepath = Path(filepath)
    mat = scipy.io.loadmat(str(filepath))

    # Campos a excluir: matrices grandes + claves internas de scipy
    skip = {"CSI", "RSSI", "TimeStamp", "__header__", "__version__", "__globals__"}

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

    # Checksum SHA-256 del archivo completo
    sha256 = hashlib.sha256(filepath.read_bytes()).hexdigest()

    # Metadatos del nombre del archivo
    filename_meta = parse_filename(filepath.name)

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "sha256":   sha256,
        **filename_meta,
        **metadata,
    }


def test_samples(samples_dir="data/samples", output_dir="output/json"):
    """
    Prueba el pipeline con todos los .mat en data/samples.
    Guarda el JSON resultante de cada archivo en output/json.
    """
    samples_path = Path(samples_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    mat_files = list(samples_path.glob("*.mat"))

    if not mat_files:
        print(f"[!] No se encontraron archivos .mat en '{samples_dir}'")
        return

    print(f"[✓] Encontrados {len(mat_files)} archivos .mat en '{samples_dir}'\n")

    for mat_file in sorted(mat_files):
        print(f"{'='*60}")
        print(f"Procesando: {mat_file.name}")
        print(f"{'='*60}")
        try:
            result = extract_metadata(mat_file)
            output_file = output_path / f"{mat_file.stem}.json"
            output_file.write_text(
                json.dumps(result, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(f"Guardado: {output_file}")
        except Exception as e:
            print(f"[ERROR] {mat_file.name}: {e}")
        print()


if __name__ == "__main__":
    test_samples("data/samples")