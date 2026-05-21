"""
json2rdf_base.py
Paso 2 del pipeline: JSON de metadatos → RDF Turtle (mapeo determinista)

Ontologías utilizadas:
    sosa    → http://www.w3.org/ns/sosa/
    ssn     → http://www.w3.org/ns/ssn/
    qudt    → http://qudt.org/schema/qudt/
    unit    → http://qudt.org/vocab/unit/
    time    → http://www.w3.org/2006/time#
    dcat    → http://www.w3.org/ns/dcat#
    dct     → http://purl.org/dc/terms/
    prov    → http://www.w3.org/ns/prov#
    spdx    → http://spdx.org/rdf/terms#
    xsd     → http://www.w3.org/2001/XMLSchema#
    // POR DEFINIR: dominio de la universidad para la ontología específica del proyecto
    wifi    → https://ehu/wifi-activity/ontology# 
    meas    → https://ehu/wifi-activity/measurement/
"""

import json
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL

# ── Namespaces ────────────────────────────────────────────────────────────────

SOSA = Namespace("http://www.w3.org/ns/sosa/")
SSN  = Namespace("http://www.w3.org/ns/ssn/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
TIME = Namespace("http://www.w3.org/2006/time#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT  = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
WIFI = Namespace("https://ehu/wifi-activity/ontology#")
MEAS = Namespace("https://ehu/wifi-activity/measurement/")
CSI_BASE = Namespace("https://ehu/wifi-csi/")

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
    "MR":    WIFI.MR,
    "MAR":   WIFI.MAR,
    "PCMAR": WIFI.PCMAR,
    "E":     WIFI.EmptyApplication,
}

ENVIRONMENT_MAP = {
    "basement":            WIFI.BasementRoom,
    "laboratory":          WIFI.Laboratory,
    "storage":             WIFI.StorageRoom,
    "office1":             WIFI.Office1,
    "office 1":            WIFI.Office1,
    "classroom":           WIFI.Classroom,
    "office2":             WIFI.Office2,
    "office 2":            WIFI.Office2,
    "meeting":             WIFI.MeetingRoom,
    "meeting room":        WIFI.MeetingRoom,
    "industrial":          WIFI.IndustrialLaboratory,
    "industrial laboratory": WIFI.IndustrialLaboratory,
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
    2:   UNIT.GigaHertz,
    5:   UNIT.GigaHertz,
}
