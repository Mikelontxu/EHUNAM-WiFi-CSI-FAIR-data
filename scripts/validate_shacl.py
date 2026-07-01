from pyshacl import validate
from pathlib import Path


def validate_dataset(data_path: str, shapes_path: str, label: str = "") -> bool:
    conforms, report_graph, report_text = validate(
        data_graph=data_path,
        shacl_graph=shapes_path,
        inference="rdfs",
        report_all=True,
    )
    tag = f"[{label}] " if label else ""
    print(f"{tag}Conforms: {conforms} ({shapes_path})")
    print(report_text)
    return conforms


def main() -> int:
    rdf_dir = Path("output/rdf")
    metadata_path = Path("output/dataset_metadata.ttl")

    shapes_metadata = [
        "shapes/dcat-ap.shacl.ttl",
        "shapes/shapes_dataset.ttl",
    ]
    shapes_rdf = [
        "shapes/shapes.ttl",
    ]

    all_ok = True

    # dcat-ap.shacl.ttl + shapes_dataset.ttl against dataset_metadata.ttl
    print("\n=== DCAT-AP validation (dataset_metadata.ttl) ===")
    for shapes_path in shapes_metadata:
        if not Path(shapes_path).exists():
            print(f"Not found: {shapes_path}")
            all_ok = False
            continue
        if not validate_dataset(str(metadata_path), shapes_path):
            all_ok = False

    # shapes.ttl → against each individual RDF file
    print("\n=== Domain validation (output/rdf/*.ttl) ===")
    rdf_files = sorted(rdf_dir.glob("*.ttl"))
    if not rdf_files:
        print(f"Not found: {rdf_dir}")
        all_ok = False
    for shapes_path in shapes_rdf:
        if not Path(shapes_path).exists():
            print(f"Not found: {shapes_path}")
            all_ok = False
            continue
        for rdf_file in rdf_files:
            print(f"\n{rdf_file.name}")
            if not validate_dataset(str(rdf_file), shapes_path):
                all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())