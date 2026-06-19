"""
Ontologías utilizadas:
    sosa    → http://www.w3.org/ns/sosa/
    qudt    → http://qudt.org/schema/qudt/
    unit    → http://qudt.org/vocab/unit/
    time    → http://www.w3.org/2006/time#
    dcat    → http://www.w3.org/ns/dcat#
    dct     → http://purl.org/dc/terms/
    prov    → http://www.w3.org/ns/prov#
    spdx    → http://spdx.org/rdf/terms#
    wifi    → https://{SERVER_HOST}:{NGINX_PORT}/wifi_activity.ttl#
"""

import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import quote

from matio import load_from_mat
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, RDF, RDFS, SKOS, XSD

from config import SERVER_HOST, NGINX_PORT, WIFI, MEAS, CSI_BASE, DATASET, GRAPHDB_REPO, ONTOLOGY_URI
# ── Namespaces ────────────────────────────────────────────────────────────────

SOSA     = Namespace("http://www.w3.org/ns/sosa/")
QUDT     = Namespace("http://qudt.org/schema/qudt/")
UNIT     = Namespace("http://qudt.org/vocab/unit/")
TIME     = Namespace("http://www.w3.org/2006/time#")
DCAT     = Namespace("http://www.w3.org/ns/dcat#")
DCT      = Namespace("http://purl.org/dc/terms/")
PROV     = Namespace("http://www.w3.org/ns/prov#")
SPDX     = Namespace("http://spdx.org/rdf/terms#")
#WIFI     = Namespace("https://ehu/wifi-csi/ontology#")      # temporal, ontologia en el servidor
#MEAS     = Namespace("https://ehu/wifi-csi/measurement/")   # temporal, ubicación de las instancias
#CSI_BASE = Namespace("https://ehu/wifi-csi/")               # temporal, esto es para redirigir a los archivos CSI, RSSI y timestamp.
#DATASET  = Namespace("https://ehu/wifi-csi/dataset/")       # temporal, IRI del dataset 

DATASET_ID           = "EHUNAM-WiFi-CSI-FAIR-data"
DATASET_URI          = DATASET[DATASET_ID]
DATASET_DIST_URI     = DATASET[f"{DATASET_ID}-distribution"]
PROJECT_REPO         = URIRef("https://github.com/mikelontxu/EHUNAM-WiFi-CSI-FAIR-data")
ORIGINAL_DATASET_URI = URIRef("https://doi.org/10.6084/m9.figshare.28541225")
LICENSE_URI          = URIRef("https://creativecommons.org/licenses/by/4.0/")
ONTOLOGY_FILE        = Path("ontology/wifi_activity.ttl")   # ontologia del github local
#GRAPHDB_REPO         = "http://localhost:7200/repositories/fdp"  # temporal, base del repo en GraphDB
TURTLE_MEDIATYPE_URI = URIRef("https://www.iana.org/assignments/media-types/text/turtle")

# Campos que no se trasladan a RDF: matrices de datos grandes (y relacionados), artefactos internos
SKIP_FIELDS = {
    "CSI", "RSSI", "TimeStamp", "Date", "Time", "Original_File",
    "__header__", "__version__", "__globals__", "__function_workspace__",
    "None",
}


# ── Extracción de metadatos del .mat ─────────────────────────────────────────

def serialize(value):
    #Convierte los arrays de matio a versión de python, aplanando arrays de un elemento.
    if not hasattr(value, "tolist"):
        return value
    val = value.tolist()
    if isinstance(val, list) and len(val) == 1:
        inner = val[0]
        if isinstance(inner, list) and len(inner) == 1:
            return inner[0]
        return inner
    return val

def extract_mat_metadata(filepath: Path) -> dict:
    """
    Información extraída de las issues de scipy que documenta el problema de lectura de la clase datetime:
    https://github.com/scipy/scipy/issues/22736
    https://github.com/scipy/scipy/issues/15984

    El campo Date de cada archivo .mat, al no utilizar MatLab, se vuelve un puntero que señala un trozo de la memoria del propio archivo.
    Esto es, al leerlo con scipy o Octave, se obtiene un array de bytes que no se interpreta automáticamente como fecha. 
    Para extraer la fecha, hay que leer el bloque de memoria apuntado por __function_workspace__ (el trozo de memoria) y utilizar los bytes para reconstruir la fecha.

    Cada archivo individual .mat tiene un bloque de memoria llamado __function_workspace__ que contiene varias variables internas de MATLAB, incluyendo la fecha.
    Utilizando este bloque se puede obtener la fecha original del archivo, de esta manera obteniendo la variable Date.
        
    Este es el array que se obtiene de la clase Date al leer cualquier archivo .mat con Octave:
    [3707764736,  2,  1,  1,  1,  1] 
    Este es el resultado que se obtiene al leer la clase Date con scipy:
    MatlabOpaque([
    (b'Date', b'MCOS', b'datetime', array([
        [3707764736],
        [         2],
        [         1],
        [         1],
        [         1],
        [         1]], dtype=uint32))
    ], dtype=[('s0', 'O'), ('s1', 'O'), ('s2', 'O'), ('arr', 'O')])

    Con esto se puede deducir que MCOS es el formato de objeto de MATLAB que se utiliza para serializar objetos complejos como datetime.
    Para resolver esto he encontrado un github que se encarga de leer clases datetime de archivos .mat:
    https://github.com/foreverallama/matio
        
    El archivo original con los datos del CSI quedan en el triple sosa:hasResult del grafo RDF.
    El datetime se construye combinando Date (datetime64 de matio) y Time (string).
    """
    filepath = Path(filepath)
    mat = load_from_mat(str(filepath))

    metadata = {
        key: serialize(value)
        for key, value in mat.items()
        if key not in SKIP_FIELDS
    }

    # matio deserializa Date de manera legible
    # el str() que devuelve tiene formato '2024-01-16T00:00:00.000000000' — se parte por T para obtener la fecha.
    # Time viene directamente como string 'HH:MM:SS'.
    date_raw     = mat.get("Date")
    time_raw     = mat.get("Time")
    date_str     = str(date_raw[0][0]).split("T")[0] if date_raw is not None else None
    time_str     = serialize(time_raw) if time_raw is not None else None
    datetime_iso = f"{date_str}T{time_str}Z" if date_str and time_str else (
                   f"{date_str}T00:00:00Z"   if date_str else None)

    return {
        "filepath":     str(filepath),                                     
        "filename":     filepath.name,                                     #nombre del archivo para construir la URL de descarga en el RDF
        "sha256":       hashlib.sha256(filepath.read_bytes()).hexdigest(), #sha256 del archivo para verificación de integridad
        "datetime_iso": datetime_iso,                                       #fecha y hora en formato ISO 8601, combinando Date y Time
        **metadata,                                                         #el resto de campos del .mat, como Set, Rx, Application, People, Activity, Machine, Status, Band, BW, Channel, Subcarriers, T_Meas… 
    }


# ── Lookups desde la ontología ────────────────────────────────────────────────

def build_ontology_indexes(g: Graph) -> dict:
    """
    Construye índices de lookup leyendo la ontología ya cargada en el grafo g.
    - by_notation: skos:notation.upper() -> URIRef  (Activity, Application, CSIExtractor, MachineStatus)
    - by_label:    rdfs:label.lower()    -> URIRef  (Environment, WifiStandard)
    Estos índices permiten mapear los valores de los campos del .mat a las instancias de la ontología, buscando coincidencias por notación o etiqueta.
    """
    def by_notation(cls):
        return {
            str(n).upper(): i
            for i, n in g.subject_objects(SKOS.notation)
            if (i, RDF.type, cls) in g
        }

    def by_label(cls):
        return {
            str(l).lower(): i
            for i, l in g.subject_objects(RDFS.label)
            if (i, RDF.type, cls) in g and l.language == "en"
        }

    return {
        "activity":       by_notation(WIFI.Activity),
        "application":    by_notation(WIFI.Application),
        "csi_extractor":  by_notation(WIFI.CSIExtractor),
        "machine_status": by_notation(WIFI.MachineStatus),
        "environment":    by_label(WIFI.Environment),
        "wifi_standard":  by_label(WIFI.WifiStandard),
    }


# ── Normalización de valores del JSON ─────────────────────────────────────────

def empty_lists_to_none(value) -> str | None:
    #Desempaqueta listas vacías y devuelve un string limpio o None para evitar valores vacíos.
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value).strip() or None if value is not None else None

def define_int(value) -> int | None:
    #Convierte a int pasando por float para manejar valores como 40.0 a 40
    s = empty_lists_to_none(value)
    if s is None:
        return None
    return int(float(s))

def secure_IRI_token(value, fallback="x") -> str:
    #Convierte un valor a token seguro para componer IRIs.
    lag = empty_lists_to_none(value)
    if lag is None:
        return fallback
    token = str(lag).strip().lower()
    token = re.sub(r"[^a-z0-9]+", "x", token).strip("x")
    return token or fallback


# ── IRI de medición ───────────────────────────────────────────────────────────

def build_measurement_id(meta: dict) -> str:
    """
    Construye un ID único y predecible para cada medición.
    Formato: meas:{campaign}-{set}-{receiver}-{application}-{people}-{activity}-{machine}-{status}-{number}
    Ejemplo: mc1-05-rx1-pc-abcdfgh-x-x-x-01
    """
    raw_set     = str(meta.get("Set") or "")
    parts       = re.split(r"[-_]", raw_set, maxsplit=1)
    campaign    = secure_IRI_token(parts[0], fallback="mc")
    set_num     = parts[1] if len(parts) > 1 else raw_set
    set_token   = set_num.lower() if not set_num.isdigit() else f"{int(set_num):02d}"

    receiver    = str(define_int(meta.get("Rx")) or "x")
    application = secure_IRI_token(empty_lists_to_none(meta.get("Application")))
    people      = "".join(list(str(empty_lists_to_none(meta.get("People")) or ""))) or "x"
    activity    = secure_IRI_token(empty_lists_to_none(meta.get("Activity")))
    machine     = secure_IRI_token(empty_lists_to_none(meta.get("Machine")))
    status      = secure_IRI_token(empty_lists_to_none(meta.get("Status")))
    num_raw     = define_int(meta.get("Number"))
    number      = f"{num_raw:02d}" if num_raw is not None else "x"

    return "-".join([
        campaign, set_token,
        f"rx{receiver}",
        application, people, activity, machine, status, number,
    ])

def _node_uri(base: URIRef, suffix: str) -> URIRef:
    #IRI de un nodo auxiliar de una medición (tiempo, banda, checksum…).
    return URIRef(f"{base}/{suffix}")


# ── Conversión metadatos → RDF ────────────────────────────────────────────────

def mat_to_rdf(meta: dict, g: Graph, idx: dict) -> None:
    #Añade los triples de una medición al grafo g usando los índices de la ontología.
    meas_id  = build_measurement_id(meta)
    meas_uri = MEAS[meas_id]
    raw_set  = str(meta.get("Set") or "")
    campaign = re.split(r"[-_]", raw_set, maxsplit=1)[0]
    people   = list(str(empty_lists_to_none(meta.get("People")) or ""))

    # ── Tipo principal ────────────────────────────────────────────────────────
    g.add((meas_uri, RDF.type, SOSA.Observation))
    g.add((meas_uri, RDF.type, WIFI.WifiMeasurement))

    # ── Campaña y set ─────────────────────────────────────────────────────────
    g.add((meas_uri, WIFI.campaign,  Literal(campaign)))
    g.add((meas_uri, WIFI.set,       Literal(raw_set)))
    g.add((meas_uri, DCT.identifier, Literal(meas_id)))

    if (number := define_int(meta.get("Number"))) is not None:
        g.add((meas_uri, WIFI.sequentialNumber, Literal(number, datatype=XSD.integer)))

    # ── Receptor ──────────────────────────────────────────────────────────────
    if (rx := define_int(meta.get("Rx"))) is not None:
        g.add((meas_uri, WIFI.receiver, Literal(rx, datatype=XSD.integer)))

    # ── Aplicación ────────────────────────────────────────────────────────────
    app_raw = (empty_lists_to_none(meta.get("Application")) or "").upper()
    if app_uri := idx["application"].get(app_raw):
        g.add((meas_uri, WIFI.application, app_uri))

    # ── Personas ──────────────────────────────────────────────────────────────
    for person_id in people:
        g.add((meas_uri, WIFI.involvesPerson, WIFI[f"Person_{person_id}"]))
        g.add((WIFI[f"Person_{person_id}"], RDF.type, WIFI.Person))
    n_people = define_int(meta.get("N_People")) or len(people)
    g.add((meas_uri, WIFI.nPeople, Literal(n_people, datatype=XSD.integer)))

    # ── Actividad ─────────────────────────────────────────────────────────────
    activity_raw = (empty_lists_to_none(meta.get("Activity")) or "").upper()
    if activity_uri := idx["activity"].get(activity_raw):
        g.add((meas_uri, WIFI.activity, activity_uri))

    # ── Máquina y estado ─────────────────────────────────────────────────────
    if machine := empty_lists_to_none(meta.get("Machine")):
        g.add((meas_uri, WIFI.machine, Literal(machine, datatype=XSD.integer)))
    status_raw = (empty_lists_to_none(meta.get("Status")) or "").upper()
    if status_uri := idx["machine_status"].get(status_raw):
        g.add((meas_uri, WIFI.machineStatus, status_uri))

    # ── Parámetros WiFi (QUDT) ────────────────────────────────────────────────

    # Banda de frecuencia
    band_val = meta.get("Band")
    if band_val is not None:
        band_node = _node_uri(meas_uri, "frequency-band")
        g.add((meas_uri, WIFI.frequencyBand, band_node))
        g.add((band_node, RDF.type, WIFI.FrequencyBand)) 
        g.add((band_node, QUDT.numericValue, Literal(float(band_val), datatype=XSD.double)))
        g.add((band_node, QUDT.unit, UNIT.GigaHertz))

    # Ancho de banda
    bw_val = meta.get("BW") if meta.get("BW") is not None else meta.get("bandwidth")
    if bw_val is not None:
        bw_node = _node_uri(meas_uri, "bandwidth")
        g.add((meas_uri, WIFI.bandwidth, bw_node))
        g.add((bw_node, RDF.type, WIFI.Bandwidth))
        g.add((bw_node, QUDT.numericValue, Literal(float(bw_val), datatype=XSD.double)))
        g.add((bw_node, QUDT.unit, UNIT.MegaHertz))

    # Canal
    if (channel := meta.get("Channel")) is not None:
        g.add((meas_uri, WIFI.channel, Literal(int(channel), datatype=XSD.integer)))

    # Subportadoras
    if (subcarriers := meta.get("Subcarriers")) is not None:
        g.add((meas_uri, WIFI.subcarriers, Literal(int(subcarriers), datatype=XSD.integer)))

    if (occupied_sc := meta.get("Occupied_SC")) is not None:
        g.add((meas_uri, WIFI.occupiedSubcarriers, Literal(int(occupied_sc), datatype=XSD.integer)))

    # Duración de la medición (segundos)
    if (t_meas := meta.get("T_Meas")) is not None:
        t_node = _node_uri(meas_uri, "duration")
        g.add((meas_uri, WIFI.measurementDuration, t_node))
        g.add((t_node, RDF.type, WIFI.Duration))
        g.add((t_node, QUDT.numericValue, Literal(float(t_meas), datatype=XSD.double)))
        g.add((t_node, QUDT.unit, UNIT.Second))

    # N_Files, N_Rx, N_Machine
    for field, predicate in [("N_Files",   WIFI.nFiles), ("N_Rx", WIFI.nReceivers), ("N_Machine", WIFI.nMachine)]:
        val = meta.get(field)
        if isinstance(val, list):
            val = val[0] if val else None
        if val is not None:
            g.add((meas_uri, predicate, Literal(int(val), datatype=XSD.integer)))

    # ── Entorno ───────────────────────────────────────────────────────────────
    env_raw = str(meta.get("Enviroment") or meta.get("Environment") or "").lower().strip()
    env_uri = next(
        (uri for label, uri in idx["environment"].items() if label in env_raw or env_raw in label),
        None
    )
    if env_uri:
        g.add((meas_uri, WIFI.environment, env_uri))
    elif env_raw:
        g.add((meas_uri, WIFI.environment, Literal(env_raw)))

    # ── Estándar WiFi ─────────────────────────────────────────────────────────
    std_raw = str(meta.get("Standard") or "").strip()
    if std_uri := idx["wifi_standard"].get(std_raw.lower()):
        g.add((meas_uri, WIFI.wifiStandard, std_uri))
    elif std_raw:
        g.add((meas_uri, WIFI.wifiStandard, Literal(std_raw)))

    # ── CSI Extractor ─────────────────────────────────────────────────────────
    csi_ext_raw = str(meta.get("CSI_Extractor") or "").strip().upper()
    if csi_ext_uri := idx["csi_extractor"].get(csi_ext_raw):
        g.add((meas_uri, WIFI.csiExtractor, csi_ext_uri))

    # ── NIC ───────────────────────────────────────────────────────────────────
    if nic_raw := str(meta.get("NIC") or "").strip():
        g.add((meas_uri, WIFI.nic, Literal(nic_raw)))

    # ── Traffic ───────────────────────────────────────────────────────────────
    if traffic_raw := str(meta.get("Traffic") or "").strip():
        g.add((meas_uri, WIFI.traffic, Literal(traffic_raw)))

    # ── Fecha y hora (OWL-Time) ───────────────────────────────────────────────
    if datetime_iso := meta.get("datetime_iso"):
        time_node = _node_uri(meas_uri, "time")
        g.add((meas_uri, SOSA.resultTime, time_node))
        g.add((time_node, RDF.type, TIME.Instant))
        g.add((time_node, TIME.inXSDDateTimeStamp,
               Literal(datetime_iso, datatype=XSD.dateTimeStamp)))

    # ── Referencia al archivo .mat (CSI + RSSI + Timestamp) ──────────────────
    if filename := meta.get("filename"):
        result_node   = _node_uri(meas_uri, "result")
        safe_filename = quote(filename, safe="-_.~")
        mat_url       = CSI_BASE[safe_filename]
        g.add((meas_uri, SOSA.hasResult, result_node))
        g.add((result_node, RDF.type, WIFI.CSIResult))
        g.add((result_node, DCAT.downloadURL, mat_url))
        g.add((result_node, DCT["format"], Literal("application/x-matlab-data")))
        if sha256 := meta.get("sha256"):
            checksum_node = _node_uri(meas_uri, "checksum")
            g.add((result_node, SPDX.checksum, checksum_node))
            g.add((checksum_node, SPDX.algorithm, SPDX.checksumAlgorithm_sha256))
            g.add((checksum_node, SPDX.checksumValue,
                   Literal(sha256, datatype=XSD.hexBinary)))

    # ── Procedencia ───────────────────────────────────────────────────────────
    g.add((meas_uri, PROV.wasGeneratedBy, PROJECT_REPO))


# ── Metadatos del dataset DCAT ────────────────────────────────────────────────

def add_measurement_distributions(g: Graph, measurement_ids: list[str]):
    #Por cada medición se crea su dcat:Distribution apuntando a cada named graph en GraphDB
    
    for meas_id in measurement_ids:
        meas_uri  = MEAS[meas_id]
        dist_uri  = MEAS[f"{meas_id}-distribution"]
        named_graph_iri = str(MEAS[meas_id])
        graph_url = URIRef(f"{GRAPHDB_REPO}/statements?context=%3C{quote(named_graph_iri, safe='')}%3E")
        
        g.add((dist_uri, RDF.type, DCAT.Distribution))
        g.add((dist_uri, DCT["format"], TURTLE_MEDIATYPE_URI))
        g.add((dist_uri, DCAT.downloadURL, graph_url))
        g.add((dist_uri, DCAT.accessURL, graph_url))

        g.add((DATASET_URI, DCAT.distribution, dist_uri))
        g.add((DATASET_URI, DCT.hasPart, meas_uri))

def add_dataset_metadata(g: Graph):
    g.add((DATASET_URI, RDF.type,        DCAT.Dataset))
    g.add((DATASET_URI, DCT.identifier,  Literal(DATASET_ID)))
    g.add((DATASET_URI, DCT.title,       Literal("EHUNAM WiFi CSI Dataset")))
    g.add((DATASET_URI, DCT.description, Literal("FAIRified version of the EHUNAM WiFi CSI dataset originally published on Figshare. The original dataset contains raw .mat files; this version provides RDF/OWL metadata following FAIR principles, with references to the original data files.", lang="en")))
    g.add((DATASET_URI, DCT.description, Literal("Versión FAIR del conjunto de datos EHUNAM WiFi CSI publicado originalmente en Figshare. El conjunto original contiene archivos .mat en bruto; esta versión proporciona metadatos RDF/OWL siguiendo los principios FAIR, con referencias a los archivos de datos originales.", lang="es")))
    g.add((DATASET_URI, DCT.issued,      Literal("2025-12-22T12:25:00Z", datatype=XSD.dateTimeStamp)))
    g.add((DATASET_URI, DCT.modified,    Literal("2025-12-22T12:25:00Z", datatype=XSD.dateTimeStamp)))
    g.add((DATASET_URI, DCT.version,     Literal("1.0")))
    g.add((DATASET_URI, DCAT.keyword,    Literal("CSI, human Activity Recognition, WiFi, people counting", lang="en")))
    g.add((DATASET_URI, DCAT.THEME,      Literal("http://publications.europa.eu/resource/authority/data-theme/TECH")))
    g.add((DATASET_URI, DCT.license,     LICENSE_URI))
    g.add((DATASET_URI, PROV.wasDerivedFrom, ORIGINAL_DATASET_URI))
    # needs to be a dct:Dataset
    g.add((ORIGINAL_DATASET_URI, RDF.type,            DCAT.Dataset))
    g.add((ORIGINAL_DATASET_URI, DCT.title,           Literal("EHUNAM WiFi CSI Dataset (Figshare)", lang="en")))
    g.add((ORIGINAL_DATASET_URI, DCT.description,     Literal("Original EHUNAM WiFi CSI dataset published on Figshare, containing raw .mat files.", lang="en")))
    g.add((ORIGINAL_DATASET_URI, DCT.license,         LICENSE_URI))
    g.add((ORIGINAL_DATASET_URI, DCT.source,          ORIGINAL_DATASET_URI))
    g.add((ORIGINAL_DATASET_URI, PROV.wasDerivedFrom, ORIGINAL_DATASET_URI))
    g.add((DATASET_URI,          DCT.source,          ORIGINAL_DATASET_URI))
    # needs to be a foaf:Agent
    PUBLISHER_URI = URIRef("https://research.science.eus/documentos/695028cd9244cb45822e855e?lang=gl")
    CREATOR_URI   = URIRef("https://github.com/Mikelontxu")
    g.add((PUBLISHER_URI, RDF.type,  FOAF.Agent))
    g.add((PUBLISHER_URI, FOAF.name, Literal("EHUNAM Research Group - University of the Basque Country and the National Autonomous University of Mexico")))
    g.add((DATASET_URI, DCT.publisher, PUBLISHER_URI))
    g.add((CREATOR_URI, RDF.type,  FOAF.Agent))
    g.add((CREATOR_URI, FOAF.name, Literal("Mikelontxu")))
    g.add((DATASET_URI, DCT.creator,   CREATOR_URI)) 

    g.add((DATASET_DIST_URI, RDF.type, DCAT.Distribution))
    g.add((DATASET_URI, DCAT.distribution, DATASET_DIST_URI))
    g.add((TURTLE_MEDIATYPE_URI, RDF.type, DCT.MediaTypeOrExtent))
    g.add((DATASET_DIST_URI, DCT["format"],    TURTLE_MEDIATYPE_URI))
    g.add((DATASET_DIST_URI, DCAT.downloadURL, URIRef("https://springernature.figshare.com/ndownloader/articles/28541225/versions/1")))
    g.add((DATASET_DIST_URI, DCAT.accessURL,   URIRef("https://doi.org/10.6084/m9.figshare.28541225")))
    # SPARQL endpoint to follow FAIR best practices for accessibility
    SPARQL_ENDPOINT = URIRef(GRAPHDB_REPO)
    g.add((SPARQL_ENDPOINT, RDF.type,           DCAT.DataService))
    SPARQL_DOCS_URI = URIRef("https://graphdb.ontotext.com/documentation/11.3/sparql.html")
    g.add((SPARQL_ENDPOINT, DCAT.endpointDescription, SPARQL_DOCS_URI))    
    g.add((SPARQL_ENDPOINT, DCT.title,          Literal("SPARQL endpoint – EHUNAM WiFi CSI", lang="en")))
    g.add((SPARQL_ENDPOINT, DCAT.endpointURL,   SPARQL_ENDPOINT))
    g.add((SPARQL_ENDPOINT, DCAT.servesDataset, DATASET_URI))
    # In DCAT-AP, a DataService isn't directly a Distribution. We wrap it in a proper Distribution:
    SPARQL_DIST_URI = DATASET[f"{DATASET_ID}-sparql-distribution"]
    g.add((SPARQL_DIST_URI, RDF.type,           DCAT.Distribution))
    g.add((DATASET_URI,     DCAT.distribution,  SPARQL_DIST_URI))
    g.add((SPARQL_DIST_URI, DCAT.accessService, SPARQL_ENDPOINT))
    g.add((SPARQL_DIST_URI, DCAT.accessURL,     SPARQL_ENDPOINT))

    #ONTOLOGY_URI = URIRef("https://localhost:7200/repositories/fdp/ontology/wifi_activity.ttl")
    g.add((ONTOLOGY_URI, RDF.type, DCT.Standard))
    g.add((DATASET_URI, DCT.conformsTo, ONTOLOGY_URI))
# ── Funciones principales ──────────────────────────────────────────────────────────────────

def _bind_namespaces(g: Graph):
    g.bind("sosa",    SOSA)
    g.bind("qudt",    QUDT)
    g.bind("unit",    UNIT)
    g.bind("time",    TIME)
    g.bind("dcat",    DCAT)
    g.bind("dct",     DCT)
    g.bind("prov",    PROV)
    g.bind("spdx",    SPDX)
    g.bind("wifi",    WIFI)
    g.bind("meas",    MEAS)
    g.bind("dataset", DATASET)


def process_folder(mat_dir: str = "data/samples", output_dir: str = "output"):

    # Procesa todos los .mat de mat_dir y genera:
    #  - Un .ttl individual por medición en output_dir/rdf/
    #  - Un dataset_metadata.ttl con los metadatos DCAT en output_dir/
    # Cada .ttl individual se va a subir al GraphDB en un graph unico
    # De esta manera se puede consultar individualmente y realizar actualizaciones especifcas.

    mat_path    = Path(mat_dir)
    output_path = Path(output_dir)
    rdf_path    = output_path / "rdf"
    rdf_path.mkdir(parents=True, exist_ok=True)

    mat_files = sorted(mat_path.glob("*.mat"))
    if not mat_files:
        print(f"No se encontraron archivos .mat en '{mat_dir}'")
        return

    # Cargar ontología una sola vez y construir índices de lookup
    ontology_graph = Graph()
    _bind_namespaces(ontology_graph)
    try:
        if ONTOLOGY_FILE.exists():
            ontology_graph.parse(str(ONTOLOGY_FILE), format="turtle")
    except Exception as e:
        print(f"No se pudo parsear la ontología {ONTOLOGY_FILE}: {e}")
    idx = build_ontology_indexes(ontology_graph)

    print(f"Procesando {len(mat_files)} archivos .mat\n")

    measurement_id = []

    for mat_file in mat_files:
        print(f"{'='*60}\nProcesando: {mat_file.name}")
        try:
            meta = extract_mat_metadata(mat_file)
            g = Graph()
            _bind_namespaces(g)
            #try:
                #if ONTOLOGY_FILE.exists():
                    #g.parse(str(ONTOLOGY_FILE), format="turtle")
            #except Exception as e:
                #print(f"No se pudo parsear la ontología en el grafo individual: {e}")
            mat_to_rdf(meta, g, idx)
            ttl_file = rdf_path / f"{mat_file.stem}.ttl"
            g.serialize(destination=str(ttl_file), format="turtle")
            print(f"{ttl_file.name}  ({len(g)} triples)")
            measurement_id.append(build_measurement_id(meta))
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()

    # Metadatos DCAT, fichero separado para subir al grafo por defecto de GraphDB
    meta_graph = Graph()
    _bind_namespaces(meta_graph)
    add_dataset_metadata(meta_graph)
    add_measurement_distributions(meta_graph, measurement_id)
    meta_ttl = output_path / "dataset_metadata.ttl"
    meta_graph.serialize(destination=str(meta_ttl), format="turtle")
    print(f"dataset_metadata.ttl → {meta_ttl}  ({len(meta_graph)} triples)")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        # Test rápido con un único .mat para tests
        mat_file = Path(sys.argv[1])
        meta     = extract_mat_metadata(mat_file)
        g        = Graph()
        _bind_namespaces(g)
        try:
            if ONTOLOGY_FILE.exists():
                g.parse(str(ONTOLOGY_FILE), format="turtle")
        except Exception as e:
            print(f"No se pudo parsear la ontología en el test: {e}")
        mat_to_rdf(meta, g, build_ontology_indexes(g))
        print(g.serialize(format="turtle"))
    else:
        # Procesamiento completo de la carpeta de datos
        process_folder()