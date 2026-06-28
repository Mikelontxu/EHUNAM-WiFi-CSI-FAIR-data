"""Pipeline de procesamiento EHUNAM WiFi CSI.

Orden:
1. mat2rdf.py
2. validate_shacl.py
3. rdf2graphdb.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path 


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"


def run_step(script_name: str, args: list[str] | None = None) -> None:
    script_path = SCRIPTS_DIR / script_name
    command     = [sys.executable, str(script_path)]
    if args:
        command.extend(args)

    print(f"  Ejecutando {script_name}...")
    result = subprocess.run(command, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        raise SystemExit(f"[✗] {script_name} falló con código {result.returncode}")
    print(f" {script_name} completado\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline completo de transformación y enriquecimiento")
    parser.add_argument("--skip-validation",  action="store_true", help="No ejecutar la validación SHACL")
    parser.add_argument("--skip-upload",      action="store_true", help="No subir a GraphDB")
    args = parser.parse_args()

    run_step("mat2rdf.py")

    if not args.skip_validation:
        run_step("validate_shacl.py")

    if not args.skip_upload:
        run_step("rdf2graphdb.py")

    print("\n Pipeline completado correctamente")


if __name__ == "__main__":
    main()