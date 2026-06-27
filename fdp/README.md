This folder called fdp (FAIR Data Point) its used to import the docker that contains the local build of FDP. This FAIR Data Point is configurated to maintain persistance even if docker compose down is executed.

It brings up these services:
- fdp: FAIR Data Point backend
- fdp-client: FDP UI
- graphdb: RDF triple store that FDP uses
- mongo: FDP persistence
- ontology: static host for the ontology TTL + own page and formats
- fuji: FAIR metrics evaluator

Prerequisites
- Docker Desktop (or Docker Engine + Compose)

Start the stack
1) From the repository:
    root:
	    docker compose -f .\fdp\compose.yml up -d
    fdp carpet:
        docker compose up -d

2) Check status:
    root:
	    docker compose -f .\fdp\compose.yml ps
    fdp carpet:
        docker compose ps

Service URLs (host)
- FDP UI: http://34.51.146.173/
- GraphDB: http://34.51.146.173:7200/
- Ontology: http://34.51.146.173:8090/ontology/docs/index-en.html#toc
            http://34.51.146.173:8090/ontology/docs/index-es.html#toc
- Fuji UI: http://34.51.146.173:1071/fuji/api/v1/ui/

Stop the stack
    root:
        docker compose -f .\fdp\compose.yml down
    fdp carpet:
        docker compose down

fuji-request.json: used to call fuji validator from console with a curl. To make a test, its neccesary to put which is the ID of the dataset from FDP.