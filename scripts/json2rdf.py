"""
json2rdf_base.py
Ontologías utilizadas:
    sosa    → http://www.w3.org/ns/sosa/
    qudt    → http://qudt.org/schema/qudt/
    unit    → http://qudt.org/vocab/unit/
    time    → http://www.w3.org/2006/time#
    dcat    → http://www.w3.org/ns/dcat#
    dct     → http://purl.org/dc/terms/
    prov    → http://www.w3.org/ns/prov#
    spdx    → http://spdx.org/rdf/terms#
    xsd     → http://www.w3.org/2001/XMLSchema#
    // POR DEFINIR: dominio de la universidad para la ontología específica del proyecto
    // Por el momento se usara de manera local con el archivo TTL de ontology, pero la idea es publicarla en un repositorio con un IRI estable
    wifi    → https://ehu/wifi-csi/ontology# 
    meas    → https://ehu/wifi-csi/measurement/
"""

import json
import re
from urllib.parse import quote
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, XSD

# ── Namespaces ────────────────────────────────────────────────────────────────

SOSA = Namespace("http://www.w3.org/ns/sosa/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
TIME = Namespace("http://www.w3.org/2006/time#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT  = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
WIFI = Namespace("https://ehu/wifi-csi/ontology#")
MEAS = Namespace("https://ehu/wifi-csi/measurement/")
CSI_BASE = Namespace("https://ehu/wifi-csi/")
DATASET = Namespace("https://ehu/wifi-csi/dataset/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
SPDX = Namespace("http://spdx.org/rdf/terms#")

DATASET_ID = "EHUNAM-WiFi-CSI-FAIR-data"
DATASET_URI = DATASET[DATASET_ID]
DATASET_DIST_URI = DATASET[f"{DATASET_ID}-distribution"]
PROJECT_REPO = URIRef("https://github.com/mikelontxu/EHUNAM-WiFi-CSI-FAIR-data")
ORIGINAL_DATASET_URI = URIRef("https://doi.org/10.6084/m9.figshare.28541225")
LICENSE_URI = URIRef("https://creativecommons.org/licenses/by/4.0/")

# Ruta local de la ontología específica del proyecto (ttl)
ONTOLOGY_FILE = Path("ontology/wifi_activity.ttl")

# ── Mapeos deterministas ──────────────────────────────────────────────────────

ACTIVITY_MAP = {
    "W": WIFI.Walking,
    "S": WIFI.StandingStill,
    "J": WIFI.Jumping,
    "T": WIFI.SittingStill,
    "G": WIFI.SittingDownAndGettingUp,
    "F": WIFI.Falling,
    "E": WIFI.Empty,
}

APPLICATION_MAP = {
    "HAR":   WIFI.HAR,
    "PC":    WIFI.PC,
    "MR":    WIFI.MR,               # Esto en caso de que se aplique a otras campañas, no solo a MC1
    "MAR":   WIFI.MAR,              # Esto en caso de que se aplique a otras campañas, no solo a MC1
    "PCMAR": WIFI.PCMAR,            # Esto en caso de que se aplique a otras campañas, no solo a MC1
    "E":     WIFI.EmptyApplication, # Esto en caso de que se aplique a otras campañas, no solo a MC1
}

ENVIRONMENT_MAP = {
    "basement":            WIFI.BasementRoom,
    "laboratory":          WIFI.Laboratory,
    "storage":             WIFI.StorageRoom,
    "office 1":            WIFI.Office1,
    "classroom":           WIFI.Classroom,
    "office 2":            WIFI.Office2,                # Esto en caso de que se aplique a otras campañas, no solo a MC1
    "meeting room":        WIFI.MeetingRoom,            # Esto en caso de que se aplique a otras campañas, no solo a MC1
    "industrial":          WIFI.IndustrialLaboratory,   # Esto en caso de que se aplique a otras campañas, no solo a MC1
    "industrial laboratory": WIFI.IndustrialLaboratory, # Esto en caso de que se aplique a otras campañas, no solo a MC1
}

CSI_EXTRACTOR_MAP = {
    "NCE": WIFI.NexmonCSIExtractor,
    "ACT": WIFI.AtherosCsiTools,
}

STANDARD_MAP = {
    "IEEE 802.11n":  WIFI.IEEE_802_11n,
    "IEEE 802.11ac": WIFI.IEEE_802_11ac,
}

STATUS_MAP = {
    "O": WIFI.MachineOn,
    "R": WIFI.MachineRunning,
}

BAND_UNIT_MAP = {
    2.4: UNIT.GigaHertz,
    5.0: UNIT.GigaHertz,
}


# ── Construcción del IRI de medición ─────────────────────────────────────────

def build_measurement_id(meta: dict) -> str:
    """
    Construye un ID único y predecible para cada medición basado en
    los campos del nombre del archivo.
    Formato: meas:{campaign}_{set}_{receiver}_{application}_{people}_{activity}_{machine}_{status}_{number}
    Ejemplo: mc1-06-rx3-pc-abcefgh-x-01
    """
    def _safe_token(value: str, fallback: str = "x") -> str:
        token = (value or "").strip().lower()
        token = re.sub(r"[^a-z0-9]+", "x", token)
        token = token.strip("x")
        return token or fallback

    people_str = _safe_token("".join(meta.get("people") or []), fallback="x")
    number     = _safe_token(str(meta.get("number") or "00"), fallback="00")
    activity   = _safe_token(str(meta.get("activity") or "X"), fallback="x")
    machine    = _safe_token(str(meta.get("machine") or "#"), fallback="x")
    status     = _safe_token(str(meta.get("status") or "#"), fallback="x")
    campaign   = _safe_token(str(meta.get("campaign") or "mc"), fallback="mc")
    set_num    = _safe_token(str(meta.get("set", "") or "").split("_")[1] if "_" in str(meta.get("set", "")) else str(meta.get("set", "")), fallback="00")
    receiver   = _safe_token(str(meta.get("receiver") or "x"), fallback="x")
    application = _safe_token(str(meta.get("application") or "x"), fallback="x")
    return (
        f"{campaign}-"
        f"{set_num}-"   # solo la parte numérica del set
        f"{receiver}-"
        f"{application}-"
        f"{people_str}-"
        f"{activity}-"
        f"{machine}-"
        f"{status}-"
        f"{number}"
    ).lower()


def build_measurement_iri(meta: dict) -> URIRef:
    return MEAS[build_measurement_id(meta)]


def _node_uri(base: URIRef, suffix: str) -> URIRef:
    return URIRef(f"{base}/{suffix}")


# ── Función principal de mapeo ────────────────────────────────────────────────

def json_to_rdf(meta: dict, g: Graph = None) -> Graph:
    """
    Convierte un diccionario de metadatos (salida de mat2json) a un grafo RDF.
    Si se pasa un grafo existente, añade los triples a él (útil para el grafo global).
    Devuelve el grafo con los nuevos triples.
    """
    if g is None:
        g = Graph()
        _bind_namespaces(g)

    meas_uri = build_measurement_iri(meta)
    meas_id = build_measurement_id(meta)

    # ── Tipo principal ────────────────────────────────────────────────────────
    g.add((meas_uri, RDF.type, SOSA.Observation))
    g.add((meas_uri, RDF.type, WIFI.WifiMeasurement))

    # ── Campaña y set ─────────────────────────────────────────────────────────
    g.add((meas_uri, WIFI.campaign,  Literal(meta["campaign"])))
    g.add((meas_uri, WIFI.set,       Literal(meta["set"])))
    g.add((meas_uri, DCT.identifier, Literal(meas_id)))

    if meta.get("number"):
        g.add((meas_uri, WIFI.measurementNumber, Literal(meta["number"])))

    # ── Receptor ──────────────────────────────────────────────────────────────
    g.add((meas_uri, WIFI.receiver, Literal(str(meta["receiver"]))))

    # ── Aplicación ────────────────────────────────────────────────────────────
    app_raw = str(meta.get("application") or "")
    app_uri = APPLICATION_MAP.get(app_raw.upper())
    if app_uri:
        g.add((meas_uri, WIFI.application, app_uri))

    # ── Personas ──────────────────────────────────────────────────────────────
    people = meta.get("people") or []
    for person_id in people:
        g.add((meas_uri, WIFI.involvesPerson, WIFI[f"Person_{person_id}"]))
    g.add((meas_uri, WIFI.nPeople, Literal(len(people), datatype=XSD.integer)))

    # ── Actividad ─────────────────────────────────────────────────────────────
    activity_raw = str(meta.get("activity") or "")
    activity_uri = ACTIVITY_MAP.get(activity_raw.upper())
    if activity_uri:
        g.add((meas_uri, WIFI.activity, activity_uri))

    # ── Máquina y estado ─────────────────────────────────────────────────────
    if meta.get("machine"):
        g.add((meas_uri, WIFI.machine, Literal(str(meta["machine"]))))
    if meta.get("status"):
        status_uri = STATUS_MAP.get(str(meta["status"]).upper())
        if status_uri:
            g.add((meas_uri, WIFI.machineStatus, status_uri))

    # ── Parámetros WiFi (QUDT) ────────────────────────────────────────────────

    # Banda de frecuencia
    band_val = meta.get("Band")
    if band_val is not None:
        band_node = _node_uri(meas_uri, "frequency-band")
        g.add((meas_uri, WIFI.frequencyBand, band_node))
        g.add((band_node, QUDT.numericValue, Literal(float(band_val), datatype=XSD.double)))
        g.add((band_node, QUDT.unit, BAND_UNIT_MAP.get(band_val, UNIT.GigaHertz)))

    # Ancho de banda
    bw_val = meta.get("BW")
    if bw_val is None:
        bw_val = meta.get("bandwidth")
    if bw_val is not None:
        bw_node = _node_uri(meas_uri, "bandwidth")
        g.add((meas_uri, WIFI.bandwidth, bw_node))
        g.add((bw_node, QUDT.numericValue, Literal(float(bw_val), datatype=XSD.double)))
        g.add((bw_node, QUDT.unit, UNIT.MegaHertz))

    # Canal
    channel = meta.get("Channel")
    if channel is not None:
        g.add((meas_uri, WIFI.channel, Literal(int(channel), datatype=XSD.integer)))

    # Subportadoras
    subcarriers = meta.get("Subcarriers")
    if subcarriers is not None:
        g.add((meas_uri, WIFI.subcarriers, Literal(int(subcarriers), datatype=XSD.integer)))

    occupied_sc = meta.get("Occupied_SC")
    if occupied_sc is not None:
        g.add((meas_uri, WIFI.occupiedSubcarriers, Literal(int(occupied_sc), datatype=XSD.integer)))

    # Duración de la medición (segundos)
    t_meas = meta.get("T_Meas")
    if t_meas is not None:
        t_node = _node_uri(meas_uri, "duration")
        g.add((meas_uri, WIFI.measurementDuration, t_node))
        g.add((t_node, QUDT.numericValue, Literal(float(t_meas), datatype=XSD.double)))
        g.add((t_node, QUDT.unit, UNIT.Second))

    # N_Files, N_Rx, N_Machine
    for field, predicate in [
        ("N_Files",   WIFI.nFiles),
        ("N_Rx",      WIFI.nReceivers),
        ("N_Machine", WIFI.nMachines),
    ]:
        val = meta.get(field)
        if isinstance(val, list):
            val = val[0] if val else None
        if val is not None:
            g.add((meas_uri, predicate, Literal(int(val), datatype=XSD.integer)))

    # ── Entorno ───────────────────────────────────────────────────────────────
    env_raw = str(meta.get("Enviroment") or meta.get("Environment") or "").lower().strip()
    env_uri = None
    for key, uri in ENVIRONMENT_MAP.items():
        if key in env_raw:
            env_uri = uri
            break
    if env_uri:
        g.add((meas_uri, WIFI.environment, env_uri))
    elif env_raw:
        g.add((meas_uri, WIFI.environment, Literal(env_raw)))

    # ── Estándar WiFi ─────────────────────────────────────────────────────────
    std_raw = str(meta.get("Standard") or "").strip()
    std_uri = STANDARD_MAP.get(std_raw)
    if std_uri:
        g.add((meas_uri, WIFI.wifiStandard, std_uri))
    elif std_raw:
        g.add((meas_uri, WIFI.wifiStandard, Literal(std_raw)))

    # ── CSI Extractor ─────────────────────────────────────────────────────────
    csi_ext_raw = str(meta.get("CSI_Extractor") or "").strip().upper()
    csi_ext_uri = CSI_EXTRACTOR_MAP.get(csi_ext_raw)
    if csi_ext_uri:
        g.add((meas_uri, WIFI.csiExtractor, csi_ext_uri))

    # ── NIC ───────────────────────────────────────────────────────────────────
    nic_raw = str(meta.get("NIC") or "").strip()
    if nic_raw:
        g.add((meas_uri, WIFI.nic, Literal(nic_raw)))

    # ── Fecha y hora (OWL-Time) ───────────────────────────────────────────────
    datetime_iso = meta.get("datetime_iso")
    if datetime_iso:
        time_node = _node_uri(meas_uri, "time")
        g.add((meas_uri, SOSA.resultTime, time_node))
        g.add((time_node, RDF.type, TIME.Instant))
        g.add((time_node, TIME.inXSDDateTimeStamp,
               Literal(datetime_iso, datatype=XSD.dateTimeStamp)))

    # ── Referencia al archivo .mat (CSI + RSSI + Timestamp) ──────────────────
    filename = meta.get("filename") or ""
    if filename:
        result_node = _node_uri(meas_uri, "result")
        # Encode unsafe URL chars like '#' in filenames
        safe_filename = quote(filename, safe="-_.~")
        mat_url = CSI_BASE[safe_filename]
        g.add((meas_uri, SOSA.hasResult, result_node))
        g.add((result_node, RDF.type, WIFI.CSIResult))
        g.add((result_node, DCAT.downloadURL, mat_url))
        g.add((result_node, DCT["format"],
               Literal("application/x-matlab-data")))

        sha256 = meta.get("sha256")
        if sha256:
            checksum_node = _node_uri(meas_uri, "checksum")
            g.add((result_node, SPDX.checksum, checksum_node))
            g.add((checksum_node, SPDX.algorithm,
                   SPDX.checksumAlgorithm_sha256))
            g.add((checksum_node, SPDX.checksumValue,
                   Literal(sha256, datatype=XSD.hexBinary)))

    # ── Procedencia ───────────────────────────────────────────────────────────
    g.add((meas_uri, PROV.wasGeneratedBy, PROJECT_REPO))

    return g


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bind_namespaces(g: Graph):
    g.bind("sosa", SOSA)
    g.bind("qudt", QUDT)
    g.bind("unit", UNIT)
    g.bind("time", TIME)
    g.bind("dcat", DCAT)
    g.bind("dct",  DCT)
    g.bind("prov", PROV)
    g.bind("spdx", SPDX)
    g.bind("wifi", WIFI)
    g.bind("meas", MEAS)
    g.bind("qudt", QUDT)
    g.bind("spdx", SPDX)
    g.bind("dataset", DATASET)


def add_dataset_metadata(g: Graph):
    g.add((DATASET_URI, RDF.type, DCAT.Dataset))
    g.add((DATASET_URI, DCT.identifier, Literal(DATASET_ID)))
    g.add((DATASET_URI, DCT.title, Literal("EHUNAM WiFi CSI Dataset")))
    g.add((DATASET_URI, DCT.description, Literal("FAIRified version of the EHUNAM WiFi CSI dataset originally published on Figshare. The original dataset contains raw .mat files; this version provides RDF/OWL metadata following FAIR principles, with references to the original data files.", lang="en")))
    g.add((DATASET_URI, DCT.description, Literal("Versión FAIR del conjunto de datos EHUNAM WiFi CSI publicado originalmente en Figshare. El conjunto original contiene archivos .mat en bruto; esta versión proporciona metadatos RDF/OWL siguiendo los principios FAIR, con referencias a los archivos de datos originales.", lang="es")))
    g.add((DATASET_URI, DCT.issued, Literal("2025-12-22T12:25:00Z", datatype=XSD.dateTimeStamp)))
    g.add((DATASET_URI, DCT.modified, Literal("2025-12-22T12:25:00Z", datatype=XSD.dateTimeStamp)))
    g.add((DATASET_URI, DCT.version, Literal("version 1.0")))
    g.add((DATASET_URI, DCAT.keyword, Literal("WiFi CSI")))
    g.add((DATASET_URI, DCT.license, LICENSE_URI))
    g.add((DATASET_URI, PROV.wasDerivedFrom, ORIGINAL_DATASET_URI))
    g.add((DATASET_URI, DCT.source, ORIGINAL_DATASET_URI))
    g.add((DATASET_URI, DCT.publisher, Literal("EHUNAM Research Group - University of the Basque Country and the National Autonomous University of Mexico")))
    g.add((DATASET_URI, DCT.creator, Literal("EHUNAM Research Group - University of the Basque Country and the National Autonomous University of Mexico")))

    g.add((DATASET_DIST_URI, RDF.type, DCAT.Distribution))
    g.add((DATASET_URI, DCAT.distribution, DATASET_DIST_URI))
    g.add((DATASET_DIST_URI, DCT["format"], Literal("text/turtle")))
    # PROVISIONAL: enlace directo a la descarga no transformada, hasta que se suba el dataset a un repositorio/servidor con DOI y enlace de descarga estable
    g.add((DATASET_DIST_URI, DCAT.downloadURL, URIRef("https://springernature.figshare.com/ndownloader/articles/28541225/versions/1"))) 
    g.add((DATASET_DIST_URI, DCAT.accessURL, URIRef("https://doi.org/10.6084/m9.figshare.28541225")))


def process_folder(json_dir: str, output_dir: str):
    """
    Procesa todos los JSON de una carpeta y genera:
      - Un .ttl individual por medición en output_dir/rdf/
      - Un dataset.ttl unificado en output_dir/
    """
    json_path   = Path(json_dir)
    output_path = Path(output_dir)
    rdf_path    = output_path / "rdf"
    rdf_path.mkdir(parents=True, exist_ok=True)

    json_files = sorted(json_path.glob("*.json"))
    if not json_files:
        print(f"[!] No se encontraron JSON en '{json_dir}'")
        return

    print(f"[✓] Procesando {len(json_files)} archivos JSON...\n")

    global_graph = Graph()
    _bind_namespaces(global_graph)
    # Si existe la ontología local la cargar en el grafo global para que esté disponible al generar cada grafo individual y el unificado
    try:
        if ONTOLOGY_FILE.exists():
            global_graph.parse(str(ONTOLOGY_FILE), format="turtle")
    except Exception as e:
        print(f"[!] No se pudo parsear la ontología {ONTOLOGY_FILE}: {e}")
    add_dataset_metadata(global_graph)

    for jf in json_files:
        meta = json.loads(jf.read_text(encoding="utf-8"))

        # Grafo individual
        g = Graph()
        _bind_namespaces(g)
        # Cargar la ontología también en el grafo individual (si existe)
        try:
            if ONTOLOGY_FILE.exists():
                g.parse(str(ONTOLOGY_FILE), format="turtle")
        except Exception as e:
            print(f"[!] No se pudo parsear la ontología en el grafo individual: {e}")
        json_to_rdf(meta, g)

        ttl_file = rdf_path / jf.with_suffix(".ttl").name
        g.serialize(destination=str(ttl_file), format="turtle")
        print(f"  [✓] {jf.name} → {ttl_file.name}  ({len(g)} triples)")

        # Añadir al grafo global
        for triple in g:
            global_graph.add(triple)

    # Grafo unificado
    dataset_ttl = output_path / "dataset.ttl"
    global_graph.serialize(destination=str(dataset_ttl), format="turtle")
    print(f"\n[✓] Grafo completo → {dataset_ttl}  ({len(global_graph)} triples totales)")


# ── Test con samples ──────────────────────────────────────────────────────────

def test_single_json(json_path: str):
    """
    Test rápido: convierte un único JSON a Turtle y lo imprime por pantalla.
    """
    meta = json.loads(Path(json_path).read_text(encoding="utf-8"))
    g = Graph()
    _bind_namespaces(g)
    # Cargar ontología si está disponible
    try:
        if ONTOLOGY_FILE.exists():
            g.parse(str(ONTOLOGY_FILE), format="turtle")
    except Exception as e:
        print(f"[!] No se pudo parsear la ontología en el test: {e}")
    json_to_rdf(meta, g)
    print(g.serialize(format="turtle"))


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        # Test de un único JSON: python json2rdf_base.py output/json/archivo.json
        test_single_json(sys.argv[1])
    else:
        # Procesa toda la carpeta: python json2rdf_base.py
        process_folder(
            json_dir="output/json",
            output_dir="output"
        )