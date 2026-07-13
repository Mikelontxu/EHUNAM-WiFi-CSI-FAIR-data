import urllib.request
import urllib.parse
from pathlib import Path
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

from config import GRAPHDB_REPO, get_graphdb_auth_header

AUTH_HEADER = get_graphdb_auth_header()

ENDPOINT = GRAPHDB_REPO
RDF_DIR  = Path("output/rdf")
METADATA = Path("output/dataset_metadata.ttl")
SOSA     = Namespace("http://www.w3.org/ns/sosa/")


def upload(path: Path, named_graph: str | None = None) -> None:
    if named_graph:
        url    = f"{ENDPOINT}/rdf-graphs/service?graph={urllib.parse.quote(named_graph, safe='')}"
        method = "PUT"
    else:
        url    = f"{ENDPOINT}/statements"
        method = "POST"
    req = urllib.request.Request(
        url, 
        data=path.read_bytes(),
        headers={
            "Content-Type": "text/turtle",
            "Authorization": AUTH_HEADER,
        }, 
        method=method
    )
    with urllib.request.urlopen(req) as r:
        return r.status

def main() -> None:
    # The default graph is used for the general dataset metadata.
    upload(METADATA)
    print(f"{METADATA.name} uploaded to the default graph")

    # Each measurement RDFq file is uploaded to its own named graph.
    for ttl in sorted(RDF_DIR.glob("*.ttl")):
        g = Graph()
        g.parse(str(ttl), format="turtle")
        named_graph = str(next(g.subjects(RDF.type, SOSA.Observation)))
        upload(ttl, named_graph)
        print(f"{ttl.name} uploaded to named graph {named_graph}")

if __name__ == "__main__":
    main()