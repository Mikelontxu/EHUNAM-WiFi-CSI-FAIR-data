import base64
import urllib.request
import urllib.parse
from pathlib import Path
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

from config import GRAPHDB_REPO


# Authorization header using .env

from dotenv import load_dotenv
import os
load_dotenv()

GRAPHDB_USER = os.environ.get("GRAPHDB_USER", "")
GRAPHDB_PASSWORD = os.environ.get("GRAPHDB_PASSWORD", "")

if not GRAPHDB_USER or not GRAPHDB_PASSWORD:
    raise EnvironmentError(
        "Faltan credenciales de GraphDB. "
        "Define GRAPHDB_USER y GRAPHDB_PASSWORD en el archivo .env o en las variables de entorno."
    )

AUTH_HEADER = "Basic " + base64.b64encode(f"{GRAPHDB_USER}:{GRAPHDB_PASSWORD}".encode()).decode()

#ENDPOINT = "http://localhost:7200/repositories/fdp"
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


# Los metadatos del dataset van al grafo por defecto
upload(METADATA)
print(f"{METADATA.name} subido al grafo por defecto")

# Cada medición → su propio Named Graph
for ttl in sorted(RDF_DIR.glob("*.ttl")):
    g = Graph()
    g.parse(str(ttl), format="turtle")
    named_graph = str(next(g.subjects(RDF.type, SOSA.Observation)))
    upload(ttl, named_graph)
    print(f"{ttl.name} subido al grafo {named_graph}")