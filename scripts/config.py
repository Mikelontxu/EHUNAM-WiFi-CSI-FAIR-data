import os
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

# URLs/IRIs derived from the server host and ports, used in RDF generation and GraphDB upload.

# The ontology and data are served by nginx at http://{SERVER_HOST}:{NGINX_PORT}/ontology/ and /data/ respectively.
WIFI     = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/ontology/wifi_activity.ttl#") #  /ontology/ folder served by nginx
MEAS = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/data/")           # /data/ folder served by nginx
DATASET  = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/wifi-csi/dataset/")

GRAPHDB_REPO  = f"http://{SERVER_HOST}:{GRAPHDB_PORT}/repositories/fdp"        # GraphDB repository URL, used for uploading RDF data. SPARQL endpoint.
ONTOLOGY_URI  = URIRef(f"http://{SERVER_HOST}:{NGINX_PORT}/ontology/wifi_activity.ttl")

# WIFI y ONTOLOGY_URI are different, WIFI is a prefix of the ontology and ONTOLOGY_URI is used to identify the ontology document.