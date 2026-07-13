import os
import base64
from pathlib import Path
from rdflib import Namespace, URIRef

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / "fdp" / ".env")
except ImportError:
    print("python-dotenv not installed, using default values from the system")

# Server ports, in case they don't appear in a .env file, default values will be used
SERVER_HOST  = os.environ.get("SERVER_HOST", "localhost")
GRAPHDB_PORT = os.environ.get("GRAPHDB_PORT", "7200")
NGINX_PORT   = os.environ.get("NGINX_PORT", "8090")

# GraphDB credentials (single source of truth for auth)
GRAPHDB_USER     = os.environ.get("GRAPHDB_USER", "")
GRAPHDB_PASSWORD = os.environ.get("GRAPHDB_PASSWORD", "")

def get_graphdb_auth_header() -> str:
    # Returns the Basic Auth header for GraphDB using credentials from environment variables.
    if not GRAPHDB_USER or not GRAPHDB_PASSWORD:
        raise EnvironmentError(
            "Missing GraphDB credentials. "
            "Define GRAPHDB_USER and GRAPHDB_PASSWORD in the .env file or as environment variables."
        )
    token = base64.b64encode(f"{GRAPHDB_USER}:{GRAPHDB_PASSWORD}".encode()).decode()
    return f"Basic {token}"

# The ontology and data are served by nginx at http://{SERVER_HOST}:{NGINX_PORT}/ontology/ and /data/ respectively.
WIFI     = Namespace("https://w3id.org/WiFi-CSI#")                     #  Prefix for the ontology, used in RDF generation.
MEAS = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/data/")           # /data/ folder served by nginx
DATASET  = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/wifi-csi/dataset/")

GRAPHDB_REPO  = f"http://{SERVER_HOST}:{GRAPHDB_PORT}/repositories/fdp"        # GraphDB repository URL, used for uploading RDF data. SPARQL endpoint.
ONTOLOGY_URI  = URIRef("https://w3id.org/WiFi-CSI")

# WIFI y ONTOLOGY_URI are different, WIFI is a prefix of the ontology and ONTOLOGY_URI is used to identify the ontology document.