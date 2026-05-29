"""Pipeline de procesamiento EHUNAM WiFi CSI.

Orden:
1. mat2json.py
2. json2rdf.py
3. enrichmentLLM.py
4. validate_shacl.py

El pipeline ejecuta cada script con el mismo intérprete de Python y
se detiene si alguno falla.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_step(script_name: str, args: list[str] | None = None) -> None:
    script_path = SCRIPTS_DIR / script_name
    command = [sys.executable, str(script_path)]
    if args:
        command.extend(args)

    print(f" Ejecutando {script_name}...")
    result = subprocess.run(command, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        raise SystemExit(f"[✗] {script_name} falló con código {result.returncode}")
    print(f" {script_name} completado")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline completo de transformación y enriquecimiento")
    parser.add_argument("--skip-enrichment", action="store_true", help="No ejecutar el enriquecimiento con Ollama")
    parser.add_argument("--skip-validation", action="store_true", help="No ejecutar la validacion SHACL")
    parser.add_argument("--model", default="qwen2.5", help="Modelo de Ollama para enrichmentLLM.py")
    args = parser.parse_args()

    run_step("mat2json.py")
    run_step("json2rdf.py")

    if not args.skip_enrichment:
        run_step(
            "enrichmentLLM.py",
            [
                "--json-dir", "output/json",
                "--base-rdf-dir", "output/rdf",
                "--output-dir", "output/rdf_enriched",
                "--model", args.model,
            ],
        )

    if not args.skip_enrichment and not args.skip_validation:
        run_step("validate_shacl.py")

    print("\n Pipeline completado correctamente")


if __name__ == "__main__":
    main()
