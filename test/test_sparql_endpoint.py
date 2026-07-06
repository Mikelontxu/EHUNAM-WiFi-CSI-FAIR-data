import argparse
import sys
from pathlib import Path
 
import requests
 
#Test 1: Extrae las medidas tomadas a 80 MHz en la campaña MC1 con el receptor 2 en el sótano (basement room) para las actividades E, W, S y J.
#Test 2: Extrae las medidas tomadas a 80 MHz en la campaña MC1 con los receptores 1 y 3 en el storage room para contar 4 personas.
#Test 3: Extrae las medidas de la persona b en el laboratorio (Laboratory) para el gesto de saltar J para todos los receptores.
#Test 4: Extrae las medidas para conteo de personas entre 0 y 4 en el receptor 1 a 20 MHz.
#Test 5: Extrae las medidas multilabel de los gestos caminar (W) y estar sentado (T) realizadas por dos personas para el receptor 4.

SPARQL_ENDPOINT = "http://34.51.146.173:7200/repositories/fdp"
 
QUERIES = {
    1: """
        PREFIX wifi: <http://34.51.146.173:8090/ontology/wifi_activity.ttl#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX qudt: <http://qudt.org/schema/qudt/>
        SELECT DISTINCT ?measurement ?downloadURL
        WHERE {
        ?measurement a wifi:WifiMeasurement ;
            wifi:campaign    "MC1" ;
            wifi:receiver    2 ;
            wifi:environment wifi:BasementRoom ;
            wifi:bandwidth   ?bwNode ;
            wifi:application wifi:HAR ;
            wifi:activity    ?activity ;
            sosa:hasResult   ?result .
        ?bwNode  qudt:numericValue ?bwValue .
        ?result  dcat:downloadURL  ?downloadURL .
        FILTER(?bwValue = 80.0)
        FILTER(?activity IN (wifi:Walking, wifi:StandingStill, wifi:Jumping, wifi:Empty))
        }
        ORDER BY ?downloadURL
    """,
    2: """
        PREFIX wifi: <http://34.51.146.173:8090/ontology/wifi_activity.ttl#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX qudt: <http://qudt.org/schema/qudt/>
        SELECT ?measurement ?receiver ?downloadURL
        WHERE {
          ?measurement a wifi:WifiMeasurement ;
              wifi:campaign    "MC1" ;
              wifi:receiver    ?receiver ;
              wifi:environment wifi:StorageRoom ;
              wifi:application wifi:PC ;
              wifi:nPeople     4 ;
              wifi:bandwidth   ?bwNode ;
              sosa:hasResult   ?result .
          ?bwNode  qudt:numericValue ?bwValue .
          ?result  dcat:downloadURL  ?downloadURL .
          FILTER(?bwValue = 80.0)
          FILTER(?receiver IN (1, 3))
        }
        ORDER BY ?downloadURL
    """,
    3: """
        PREFIX wifi: <http://34.51.146.173:8090/ontology/wifi_activity.ttl#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        SELECT ?measurement ?receiver ?downloadURL
        WHERE {
          ?measurement a wifi:WifiMeasurement ;
              wifi:environment    wifi:Laboratory ;
              wifi:involvesPerson wifi:Person_b ;
              wifi:activity       wifi:Jumping ;
              wifi:receiver       ?receiver ;
              sosa:hasResult      ?result .
          ?result dcat:downloadURL ?downloadURL .
        }
        ORDER BY ?receiver
    """,
    4: """
        PREFIX wifi: <http://34.51.146.173:8090/ontology/wifi_activity.ttl#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX qudt: <http://qudt.org/schema/qudt/>
        SELECT ?measurement ?nPeople ?downloadURL
        WHERE {
          ?measurement a wifi:WifiMeasurement ;
              wifi:campaign    "MC1" ;
              wifi:receiver    1 ;
              wifi:application ?app ;
              wifi:nPeople     ?nPeople ;
              wifi:bandwidth   ?bwNode ;
              sosa:hasResult   ?result .
          ?bwNode  qudt:numericValue ?bwValue .
          ?result  dcat:downloadURL  ?downloadURL .
          FILTER(?bwValue = 20.0)
          FILTER(?app IN (wifi:PC))
          FILTER(?nPeople >= 0 && ?nPeople <= 4)
        }
        ORDER BY ?nPeople
    """,
    5: """
        PREFIX wifi: <http://34.51.146.173:8090/ontology/wifi_activity.ttl#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        SELECT ?measurement ?downloadURL
        WHERE {
          ?measurement a wifi:WifiMeasurement ;
              wifi:receiver 4 ;
              wifi:nPeople  2 ;
              wifi:activity wifi:Walking ;
              wifi:activity wifi:SittingStill ;
              sosa:hasResult ?result .
          ?result dcat:downloadURL ?downloadURL .
        }
        ORDER BY ?downloadURL
    """,
}

def run_query(query: str) -> list[str]:
    # Execute an SPARQL query and get the download URLs in JSON format
    response = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    response.raise_for_status()
    bindings = response.json()["results"]["bindings"]
    urls = [row["downloadURL"]["value"] for row in bindings if "downloadURL" in row]
    return list(dict.fromkeys(urls))

def download_file(url: str, dest_dir: Path) -> None:
    filename = url.rstrip("/").split("/")[-1]
    dest_path = dest_dir / filename
  
    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
        print(f"    downloaded: {filename}")
    except requests.RequestException as exc:
        print(f"    ERROR downloading {url}: {exc}", file=sys.stderr)

def main() -> None:
    parser = argparse.ArgumentParser(description="Download .mat files from the SPARQL endpoint using test queries")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("test_folder"),
        help="Default output directory for downloaded .mat files",
    )
    args = parser.parse_args()
 
    for test_id in sorted(QUERIES.keys()):
        print(f"\n== Test {test_id} ==")
        query = QUERIES[test_id]
 
        try:
            urls = run_query(query)
        except requests.RequestException as exc:
            print(f" ERROR executing SPARQL query: {exc}", file=sys.stderr)
            continue
 
        if not urls:
            print(" No files found.")
            continue
 
        print(f"  {len(urls)} file(s) found")
 
        dest_dir = args.out / f"test{test_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
 
        for url in urls:
            download_file(url, dest_dir)
 
if __name__ == "__main__":
    main()
 