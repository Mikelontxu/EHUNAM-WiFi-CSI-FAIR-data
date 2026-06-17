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
- FDP UI: http://localhost/
- GraphDB: http://localhost:7200/
- Ontology: http://localhost:8090/
- Fuji UI: http://localhost:1071/fuji/api/v1/ui/

Notes
- If you are calling FDP from inside a container, use http://fdp-client/... instead of localhost.
- Fuji API uses Basic Auth. If you see 401, check the Fuji credentials in the container config. You can us the default credentials of Fuji.

Stop the stack
    root:
        docker compose -f .\fdp\compose.yml down
    fdp carpet:
        docker compose down

fuji-request.json: used to call fuji validator from console with a curl. To make a test, its neccesary to put which is the ID of the dataset from FDP.