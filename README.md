# PlantGraph3

## Reproducible BioKB Integration and Knowledge Graph Construction for Plant–Chemical–Wound Data

---

## Project Overview

This project implements a **reproducible, containerized data integration pipeline** that imports multiple biological knowledge bases (BioKB modules) into a relational database, exports them to RDF/Turtle format, and constructs a **Neo4j knowledge graph** for structured cross-domain querying.

The system integrates:

* Taxonomic databases (IPNI, WFO, WCVP, TaxTree)
* Chemical ontology (ChEBI)
* Natural product database (COCONUT)
* Enzyme database (BRENDA)
* Literature-derived SQLite dataset (plant–disease associations: Ethonobot v1 and v2 databases)

The primary goal is to enable structured querying across plants, chemicals, enzymes, and wound-related entities using a unified knowledge graph representation.

---

## Project Scope

This project implements:

* Automated import of BioKB databases into MySQL
* RDF/Turtle export of integrated datasets
* Import of RDF into Neo4j
* Structured graph-based querying

This project does **not** implement:

* Machine learning prediction
* Clinical ranking models
* Experimental validation

The focus is on **data integration, ontology alignment, and reproducible knowledge graph construction**.

---

## System Architecture

The system is containerized using Podman/Docker Compose and consists of:

* **MySQL (8.4)** — relational storage for BioKB datasets
* **Neo4j (5.x)** — knowledge graph database
* **phpMyAdmin** — optional inspection interface
* **Python pipeline (main.py)** — orchestrates full workflow

### Architecture Diagram

```mermaid
fflowchart LR
  SQLITE[(SQLite .db file)]
  NEO4J[(Neo4j Container)]
  PY["Python Pipeline (main.py)"]
  TTL["Turtle Files (.ttl)"]

  PY --> SQLITE
  PY --> TTL
  TTL --> NEO4J
```

---

## Reproducibility Guarantee

The full pipeline runs with:

```bash
podman-compose up -d
python main.py
```

No OS-specific paths are used.
All services are defined in `docker-compose.yml`.

If these commands run successfully, the Neo4j knowledge graph will be populated.

You can explore the data interactively in:

[Demo Notebook](notebooks/demo.ipynb)

In the demo notebook, there's the possibility to import each database separately; the following steps will execute all the code and import all databases at once.

---

## Requirements

* Python ≥ 3.12
* Podman + podman-compose
  (Docker + docker compose also supported)
* Internet access (to install BioKB dependencies)
* prog_lab2.db file

---

## Quickstart (End-to-End Execution)

### 1. Clone the repository

```bash
git clone <REPO_URL>
cd plantgraph3
```

---

### 2. Start containers (MySQL + Neo4j)

```bash
podman-compose up -d
```

Wait 15–30 seconds for services to initialize.

Verify containers:

```bash
podman ps
```

You should see:

* mysql
* neo4j

The containers are now running.

---

### 3. Install Python dependencies

Using uv (recommended):

```bash
uv sync
```

Or using pip:

```bash
pip install -e .
```

---

### 4. Run the full pipeline

This step performs:

1. Import of BioKB datasets into MySQL
2. RDF/Turtle generation
3. Import of RDF into Neo4j


```bash
python main.py
```

Expected output:

```
Pipeline completed successfully.
```

---

### 5. Verify Neo4j Graph

Open:

```
http://localhost:7474
```

Login:

* User: `neo4j`
* Password: `neo4j_password`

Run:

```cypher
MATCH (n) RETURN COUNT(n);
```

Nodes > 0 confirms successful import.

The library is now ready to query.

---

### 6. Stop services

```bash
podman-compose down
```

To completely reset volumes:

```bash
podman-compose down -v
```

---

## Pipeline Description

### Step 1 – BioKB Import (MySQL)

`DbManager.import_biokb_dbs()` loads:

* BRENDA
* Ethnobot (v1 and v2)
* ChEBI
* COCONUT
* IPNI
* WFO
* WCVP
* TaxTree

Ethonobot v1 and v2 are imported into MySQL via SQLite 3.

The databases and their tables are accessible in this step via:
```
http://localhost:8081/
```
Login:

* User: `root`
* Password: `root_password`

---

### Step 2 – RDF/Turtle Export

`DbManager.create_turtle_files()` generates `.ttl` files representing entities and relationships using RDF namespaces defined in `src/plantgraph3/rdf/`.

---

### Step 3 – Neo4j Import

`DbManager.import_neo4j()` loads Turtle-derived data into Neo4j via Bolt protocol.

---

## Repository Structure

```
src/plantgraph3/
  db/
    manager.py
  rdf/
    namespaces.py
    helpers.py
main.py
docker-compose.yml
database/
README.md
```

* `main.py` — single entry point (required for grading)
* `manager.py` — orchestration logic
* `rdf/` — RDF namespace + helper logic
* `docker-compose.yml` — container definition

---

## Development Practices

* Modular pipeline design
* Typed method signatures
* Containerized execution
* Version-controlled via Git
* Feature branches used during development
* Issues created and closed for tracked tasks

---

## Testing & Validation

Validation steps include:

* Confirming successful MySQL import (table counts)
* Confirming successful Neo4j import (node and relationship counts)
* Verifying identifier continuity (IPNI, UniProt, ChEBI)

---

## Troubleshooting

### Neo4j not reachable

Check:

```bash
podman logs neo4j
```

Ensure port 7687 is free.

---

### MySQL connection errors

Wait until container health check passes:

```bash
podman logs mysql
```

---

### Pipeline fails

Reset environment:

```bash
podman-compose down -v
podman-compose up -d
python main.py
```
