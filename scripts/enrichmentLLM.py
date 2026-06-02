import json
import re
import time
from pathlib import Path

try:
    import ollama
except ImportError:  # depende del entorno local
    ollama = None
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDFS, OWL

# ── Namespaces (mismos que json2rdf_base) ────────────────────────────────────

SOSA    = Namespace("http://www.w3.org/ns/sosa/")
DCAT    = Namespace("http://www.w3.org/ns/dcat#")
DCT     = Namespace("http://purl.org/dc/terms/")
SKOS    = Namespace("http://www.w3.org/2004/02/skos/core#")
WIFI    = Namespace("https://ehu/wifi-csi/ontology#")
MEAS    = Namespace("https://ehu/wifi-csi/measurement/")
DATASET = Namespace("https://ehu/wifi-csi/dataset/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
QUDT    = Namespace("http://qudt.org/schema/qudt/")
UNIT    = Namespace("http://qudt.org/vocab/unit/")
TIME    = Namespace("http://www.w3.org/2006/time#")
SPDX    = Namespace("http://spdx.org/rdf/terms#")

# ── Mapeos legibles para el prompt ───────────────────────────────────────────

ACTIVITY_LABELS = {
    "W": "walking",
    "S": "standing still",
    "J": "jumping",
    "T": "sitting still",
    "G": "sitting down and getting up",
    "F": "falling",
    "E": "empty (no activity)",
}

APPLICATION_LABELS = {
    "HAR":   "Human Activity Recognition",
    "PC":    "People Counting",
    "MR":    "Machine Recognition",
    "MAR":   "Machine Activity Recognition",
    "PCMAR": "People Counting and Machine Activity Recognition",
    "E":     "Empty",
}

# DBpedia links deterministas para conceptos clave del dominio
DBPEDIA_SUBJECTS = [
    DBPEDIA["Channel_state_information"],
    DBPEDIA["Wi-Fi"],
    DBPEDIA["Activity_recognition"],
    DBPEDIA["Orthogonal_frequency-division_multiplexing"],
]

# ── System prompt para el LLM ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a semantic web expert specializing in FAIR data principles and RDF ontologies.
You will receive a JSON summary of a WiFi CSI measurement and must return ONLY a valid JSON object.
No explanations, no markdown, no code blocks. Only the raw JSON object.

Your output must follow this exact structure:
{
  "label_en": "short label in English (max 15 words)",
  "label_es": "short label in Spanish (max 15 words)",
  "description_en": "human-readable description in English (2-3 sentences)",
  "description_es": "human-readable description in Spanish (2-3 sentences)",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}

Rules:
- keywords must be lowercase, relevant to WiFi sensing, CSI, and the specific activity/application
- descriptions must be informative for a researcher who wants to reuse this data
- do not include IRIs, technical field names, or JSON keys in the output values
- use only facts explicitly present in the summary; do not invent people, environments, hardware, or standards
- do not mention frequency band or bandwidth unless they appear in the summary
- keywords must be exactly 5 items
- avoid filenames, file extensions, or special symbols like '#'
- always return valid JSON, nothing else"""


def build_prompt(meta: dict) -> str:
    activity    = ACTIVITY_LABELS.get(str(meta.get("activity") or ""), meta.get("activity", "unknown"))
    application = APPLICATION_LABELS.get(str(meta.get("application") or ""), meta.get("application", "unknown"))
    people      = meta.get("people") or []
    environment = meta.get("Enviroment") or meta.get("Environment") or "unknown"
    standard    = meta.get("Standard") or "unknown"
    band        = meta.get("Band") or "unknown"
    bw          = meta.get("BW") or meta.get("bandwidth") or "unknown"
    channel     = meta.get("Channel") or "unknown"
    t_meas      = meta.get("T_Meas") or "unknown"
    extractor   = meta.get("CSI_Extractor") or "unknown"
    n_rx        = meta.get("N_Rx") or "unknown"
    datetime_iso = meta.get("datetime_iso") or "unknown"

    return f"""WiFi CSI measurement summary:
- Campaign: {meta.get('campaign', 'MC1')}
- Set: {meta.get('set', 'unknown')}
- Environment: {environment}
- Activity performed: {activity}
- Application: {application}
- Number of people: {len(people)} ({', '.join(people) if people else 'none'})
- WiFi standard: {standard}
- Frequency band: {band} GHz
- Bandwidth: {bw} MHz
- Channel: {channel}
- Duration: {t_meas} seconds
- CSI extractor software: {extractor}
- Number of receivers: {n_rx}
- Recorded at: {datetime_iso}

Generate the JSON enrichment for this measurement."""


def build_measurement_id(meta: dict) -> str:
    """
    Reconstruye el mismo identificador determinista que json2rdf.py,
    para enriquecer exactamente el mismo recurso RDF.
    """
    def _safe_token(value: str, fallback: str = "x") -> str:
        token = (value or "").strip().lower()
        token = re.sub(r"[^a-z0-9]+", "x", token)
        token = token.strip("x")
        return token or fallback

    people_str = _safe_token("".join(meta.get("people") or []), fallback="x")
    number = _safe_token(str(meta.get("number") or "00"), fallback="00")
    activity = _safe_token(str(meta.get("activity") or "X"), fallback="x")
    machine = _safe_token(str(meta.get("machine") or "#"), fallback="x")
    status = _safe_token(str(meta.get("status") or "#"), fallback="x")
    campaign = _safe_token(str(meta.get("campaign") or "mc"), fallback="mc")
    set_num = _safe_token(str(meta.get("set", "") or "").split("_")[1] if "_" in str(meta.get("set", "")) else str(meta.get("set", "")), fallback="00")
    receiver = _safe_token(str(meta.get("receiver") or "x"), fallback="x")
    application = _safe_token(str(meta.get("application") or "x"), fallback="x")
    return (
        f"{campaign}-"
        f"{set_num}-"
        f"{receiver}-"
        f"{application}-"
        f"{people_str}-"
        f"{activity}-"
        f"{machine}-"
        f"{status}-"
        f"{number}"
    ).lower()

def call_ollama(prompt: str, model: str = "qwen2.5", retries: int = 3) -> dict | None:
    """
    Llama a Ollama y parsea la respuesta JSON.
    Reintenta hasta `retries` veces si la respuesta no es JSON válido.
    """
    if ollama is None:
        print("   El paquete 'ollama' no está instalado en este entorno")
        return None

    for attempt in range(1, retries + 1):
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                options={"temperature": 0.2},  # baja temperatura = más consistente
            )
            raw = response["message"]["content"].strip()

            # Limpiar posibles bloques markdown que el LLM añada igualmente
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            return json.loads(raw)

        except json.JSONDecodeError:
            print(f"    Intento {attempt}/{retries}: respuesta no es JSON válido, reintentando...")
            time.sleep(1)
        except Exception as e:
            print(f"    Error Ollama (intento {attempt}/{retries}): {e}")
            time.sleep(2)

    print("    No se pudo obtener respuesta válida del LLM tras todos los intentos")
    return None


def _detect_band_token(text: str) -> str | None:
    text = text.lower()
    if "2.4ghz" in text or "2.4 ghz" in text:
        return "2.4"
    if "5ghz" in text or "5 ghz" in text:
        return "5"
    return None


def _detect_bw_token(text: str) -> str | None:
    text = text.lower()
    if "20mhz" in text or "20 mhz" in text:
        return "20"
    if "80mhz" in text or "80 mhz" in text:
        return "80"
    return None


def _validate_enrichment(meta: dict, enriched: dict) -> tuple[dict, list[str]]:
    """
    Validacion simple para evitar contradicciones.
    Si hay conflicto, limpia descripciones y keywords.
    """
    warnings: list[str] = []
    band_val = meta.get("Band")
    bw_val = meta.get("BW") or meta.get("bandwidth")

    text_fields = [
        enriched.get("label_en", ""),
        enriched.get("label_es", ""),
        enriched.get("description_en", ""),
        enriched.get("description_es", ""),
        " ".join(enriched.get("keywords", []) or []),
    ]
    joined = " ".join(text_fields)

    band_token = _detect_band_token(joined)
    if band_token and band_val is not None:
        band_str = str(float(band_val)).rstrip("0").rstrip(".")
        if band_token != band_str:
            warnings.append("band_mismatch")

    bw_token = _detect_bw_token(joined)
    if bw_token and bw_val is not None:
        bw_str = str(float(bw_val)).rstrip("0").rstrip(".")
        if bw_token != bw_str:
            warnings.append("bandwidth_mismatch")

    if warnings:
        enriched = {
            "label_en": enriched.get("label_en", ""),
            "label_es": enriched.get("label_es", ""),
            "description_en": "",
            "description_es": "",
            "keywords": [],
        }

    return enriched, warnings


def enrich_graph(base_ttl: Path, meta: dict, model: str = "qwen2.5") -> Graph:
    """
    Carga el Turtle base, llama al LLM para enriquecerlo y devuelve
    el grafo enriquecido con los nuevos triples.
    """
    # Cargar el grafo base
    g = Graph()
    g.parse(str(base_ttl), format="turtle")

    # Reconstruir el IRI de la medición (mismo método que json2rdf_base)
    meas_uri = MEAS[build_measurement_id(meta)]

    # Llamar al LLM
    prompt   = build_prompt(meta)
    enriched = call_ollama(prompt, model=model)
    if enriched:
        enriched, warnings = _validate_enrichment(meta, enriched)
        if warnings:
            print(f"    [!] Enrichment ajustado por: {', '.join(warnings)}")

    if enriched:
        # Labels en inglés y español
        label_en = enriched.get("label_en", "").strip()
        label_es = enriched.get("label_es", "").strip()
        if label_en:
            g.add((meas_uri, RDFS.label, Literal(label_en, lang="en")))
        if label_es:
            g.add((meas_uri, RDFS.label, Literal(label_es, lang="es")))

        # Descriptions
        desc_en = enriched.get("description_en", "").strip()
        desc_es = enriched.get("description_es", "").strip()
        if desc_en:
            g.add((meas_uri, DCT.description, Literal(desc_en, lang="en")))
        if desc_es:
            g.add((meas_uri, DCT.description, Literal(desc_es, lang="es")))

        # Keywords (dcat:keyword)
        for kw in enriched.get("keywords", []):
            kw = kw.strip().lower()
            if kw:
                g.add((meas_uri, DCAT.keyword, Literal(kw, lang="en")))

    # DBpedia subjects deterministas (siempre, independientemente del LLM)
    for subject_uri in DBPEDIA_SUBJECTS:
        g.add((meas_uri, DCT.subject, subject_uri))

    # FAIR: enlace al dataset padre
    dataset_uri = DATASET["EHUNAM-WiFi-CSI-FAIR-data"]
    g.add((dataset_uri, DCAT.dataset, meas_uri))

    return g


def _bind_namespaces(g: Graph):
    g.bind("sosa",    SOSA)
    g.bind("dcat",    DCAT)
    g.bind("dct",     DCT)
    g.bind("skos",    SKOS)
    g.bind("wifi",    WIFI)
    g.bind("meas",    MEAS)
    g.bind("dataset", DATASET)
    g.bind("dbpedia", DBPEDIA)
    g.bind("qudt",    QUDT)
    g.bind("unit",    UNIT)
    g.bind("time",    TIME)
    g.bind("spdx",    SPDX)
    g.bind("rdfs",    RDFS)
    g.bind("owl",     OWL)


# ── Procesado de carpeta completa ─────────────────────────────────────────────

def process_folder(
    json_dir:    str = "output/json",
    base_rdf_dir: str = "output/rdf",
    output_dir:  str = "output/rdf_enriched",
    model:       str = "qwen2.5",
):
    """
    Para cada JSON en json_dir:
      1. Carga el .ttl base correspondiente de base_rdf_dir
      2. Llama al LLM para enriquecerlo
      3. Guarda el .ttl enriquecido en output_dir
    Al final genera un dataset_enriched.ttl unificado.
    """
    json_path     = Path(json_dir)
    base_rdf_path = Path(base_rdf_dir)
    output_path   = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_files = sorted(json_path.glob("*.json"))
    if not json_files:
        print(f"[!] No se encontraron JSON en '{json_dir}'")
        return

    print(f"[✓] Enriqueciendo {len(json_files)} mediciones con Ollama ({model})...\n")

    global_graph = Graph()
    _bind_namespaces(global_graph)

    # secured that dcat:Dataset is always present in the global graph
    dataset_base = Path("output/dataset.ttl")
    if dataset_base.exists():
        global_graph.parse(str(dataset_base), format="turtle")
        print(f"Metadatos del Dataset cargados desde {dataset_base}\n")
    else:
        print(f"No se encontró {dataset_base} — el nodo dcat:Dataset no estará en el output\n")

    for jf in json_files:
        base_ttl = base_rdf_path / jf.with_suffix(".ttl").name
        if not base_ttl.exists():
            print(f"  [!] No se encontró el Turtle base para {jf.name}, saltando...")
            continue

        meta = json.loads(jf.read_text(encoding="utf-8"))
        print(f"  Enriqueciendo: {jf.name}")

        g = enrich_graph(base_ttl, meta, model=model)
        _bind_namespaces(g)

        out_ttl = output_path / base_ttl.name
        g.serialize(destination=str(out_ttl), format="turtle")
        print(f"  [✓] → {out_ttl.name}  ({len(g)} triples)")

        for triple in g:
            global_graph.add(triple)

    # Grafo enriquecido unificado
    enriched_dataset = Path("output") / "dataset_enriched.ttl"
    _bind_namespaces(global_graph)
    global_graph.serialize(destination=str(enriched_dataset), format="turtle")
    print(f"\n[✓] Grafo enriquecido completo → {enriched_dataset}  ({len(global_graph)} triples totales)")
# ── Test con un único archivo ─────────────────────────────────────────────────

def test_single(json_path: str, base_rdf_dir: str = "output/rdf", model: str = "qwen2.5"):
    """
    Test rápido con un único JSON + su Turtle base.
    Imprime el Turtle enriquecido por pantalla.
    python json2rdf_enrich.py output/json/MC1_03_2_HAR_e_S_01.json
    """
    jf       = Path(json_path)
    base_ttl = Path(base_rdf_dir) / jf.with_suffix(".ttl").name
    meta     = json.loads(jf.read_text(encoding="utf-8"))

    print(f"[→] Enriqueciendo: {jf.name}")
    print(f"[→] Turtle base:   {base_ttl}\n")

    g = enrich_graph(base_ttl, meta, model=model)
    _bind_namespaces(g)
    print(g.serialize(format="turtle"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enriquece los RDF con Ollama")
    parser.add_argument("json_path", nargs="?", help="JSON a enriquecer en modo test")
    parser.add_argument("--json-dir", default="output/json", help="Carpeta de JSON de entrada")
    parser.add_argument("--base-rdf-dir", default="output/rdf", help="Carpeta con los RDF base")
    parser.add_argument("--output-dir", default="output/rdf_enriched", help="Carpeta de salida para RDF enriquecidos")
    parser.add_argument("--model", default="qwen2.5", help="Modelo de Ollama a usar")
    args = parser.parse_args()

    if args.json_path:
        test_single(args.json_path, base_rdf_dir=args.base_rdf_dir, model=args.model)
    else:
        process_folder(
            json_dir=args.json_dir,
            base_rdf_dir=args.base_rdf_dir,
            output_dir=args.output_dir,
            model=args.model,
        )