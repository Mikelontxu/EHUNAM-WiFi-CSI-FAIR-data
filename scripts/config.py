import os
from pathlib import Path
from rdflib import Namespace, URIRef

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / "fdp" / ".env")
except ImportError:
    print("python-dotenv no instalado, usando valores por defecto del sistema")

# Servidor puertos, en caso que no aparezcan en un .env se pondra las variables por defecto
SERVER_HOST  = os.environ.get("SERVER_HOST", "localhost")
GRAPHDB_PORT = os.environ.get("GRAPHDB_PORT", "7200")
NGINX_PORT   = os.environ.get("NGINX_PORT", "8090")

# URLs/IRIs derivadas

# La ontología y los .mat los sirve nginx (servicio "ontology" del compose)
# en http://{SERVER_HOST}:{NGINX_PORT}/ontology/ y /data/ respectivamente.
WIFI     = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/ontology/wifi_activity.ttl#") # carpeta /ontology/ servida por nginx
MEAS     = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/wifi-csi/measurement/")
CSI_BASE = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/data/")              # carpeta /data/ servida por nginx
DATASET  = Namespace(f"http://{SERVER_HOST}:{NGINX_PORT}/wifi-csi/dataset/")

GRAPHDB_REPO  = f"http://{SERVER_HOST}:{GRAPHDB_PORT}/repositories/fdp"        # base del repo en GraphDB
ONTOLOGY_URI  = URIRef(f"http://{SERVER_HOST}:{NGINX_PORT}/ontology/wifi_activity.ttl")

# WIFI y ONTOLOGY_URI son diferentes, WIFI es un prefijo de la ontologia y ONTOLOGY_URI es para identificar el documento de la ontologia.