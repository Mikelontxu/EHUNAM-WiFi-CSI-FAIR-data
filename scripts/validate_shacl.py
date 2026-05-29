from pyshacl import validate
from pathlib import Path

def validate_dataset(data_path: str, shapes_path: str = "shapes/dcat-ap.shacl.ttl"):
    conforms, report_graph, report_text = validate(
        data_graph=data_path,
        shacl_graph=shapes_path,
        inference="rdfs",
        report_all=True,
    )
    print(f"Conforms: {conforms}")
    print(report_text)
    return conforms

if __name__ == "__main__":
    validate_dataset("output/dataset_enriched.ttl")
