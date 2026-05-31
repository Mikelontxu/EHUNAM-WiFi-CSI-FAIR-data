from pyshacl import validate
from pathlib import Path


def validate_dataset(data_path: str, shapes_path: str) -> bool:
    conforms, report_graph, report_text = validate(
        data_graph=data_path,
        shacl_graph=shapes_path,
        inference="rdfs",
        report_all=True,
    )
    print(f"Conforms: {conforms} ({shapes_path})")
    print(report_text)
    return conforms


def main() -> int:
    data_path = "output/dataset_enriched.ttl"
    shapes_files = [
        "shapes/dcat-ap.shacl.ttl",
        "shapes/shapes.ttl",
    ]

    all_ok = True
    for shapes_path in shapes_files:
        if not Path(shapes_path).exists():
            print(f"[!] SHACL file not found: {shapes_path}")
            all_ok = False
            continue
        if not validate_dataset(data_path, shapes_path):
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
