## 1. Introduction

### 1.1 Scientific Context and Motivation
#### Problem Definition

The integration of heterogeneous biological databases remains a central challenge in bioinformatics. Plant-related knowledge relevant to wound healing is distributed across taxonomic databases, chemical ontologies, enzyme repositories, pathway resources, and scientific publications. These datasets differ in structure, identifiers, and data models, making cross-domain querying difficult.

The aim of this project was to design and implement a reproducible computational pipeline that integrates multiple BioKB databases and literature-derived evidence into a unified knowledge graph, enabling structured querying of plant, metabolite, enzyme, and wound-related entities.

#### Scientific Background

Wound healing is a complex biological process involving inflammation, angiogenesis, extracellular matrix remodeling, and cellular proliferation. Molecular components of these processes are represented in pathway databases such as Reactome, while pharmacological modulators are cataloged in resources such as DrugCentral. At the same time, natural product databases (e.g., COCONUT) and chemical ontologies (e.g., ChEBI) describe plant-derived metabolites, and taxonomic backbones (e.g., WFO, WCVP, IPNI) provide standardized plant identifiers.

Knowledge graphs and RDF representations enable integration of such heterogeneous datasets by expressing biological entities and their relationships in a unified semantic framework. Neo4j provides a property-graph implementation suitable for multi-hop querying across these linked domains.

#### Motivation and Objectives

Although curated biological databases are individually well structured, they are rarely integrated in a reproducible, containerized workflow that supports end-to-end execution. This project addresses this gap by:
1. Importing multiple BioKB datasets into a relational database.
2. Exporting them into RDF/Turtle format.
3. Importing the RDF into Neo4j as a knowledge graph.
4. Enabling structured queries linking plants, metabolites, enzymes, pathways, and wound-related drug targets.
5. Providing a fully containerized environment for reproducibility.

The focus is therefore not on predictive modeling, but on data integration, interoperability, and knowledge graph construction.

## 2. Methods
### 2.1 Software Design and Implementation

#### System Architecture

The software is implemented as a reproducible, containerized ETL + knowledge-graph pipeline. The execution entry point is `main.py`, which orchestrates the full workflow: importing multiple BioKB datasets into a relational database, generating RDF/Turtle exports, and importing these RDF datasets into Neo4j.

The runtime environment is defined by `docker-compose.yml`, which deploys three services:
- A local SQLite database file (`.db`) serves as the integrated relational store for all imported BioKB tables.

- Neo4j (neo4j:5.26.14) as the knowledge graph store for querying cross-dataset biological relations.

- phpMyAdmin as an optional UI for inspecting MySQL tables during development.

A high-level overview is shown below:

flowchart LR
  subgraph Podman/Compose
    MYSQL[(MySQL)]
    NEO4J[(Neo4j)]
    PMA[phpMyAdmin]
    MYSQL --- PMA
  end

  PY[Python pipeline\n(main.py + DbManager)] --> MYSQL
  PY --> TTL[Turtle files (.ttl)]
  TTL --> NEO4J
  NEO4J --> Q[Cypher queries\n(analysis)]

#### Implementation Details (modules and data flow)

The orchestration logic is implemented in `src/plantgraph3/db/manager.py` via the class `DbManager(engine: Engine)`. The key design choice is delegation to BioKB submodules, each of which provides a consistent interface for:
1. Relational import: `DbManager(...).import_db()`

2. RDF export: `TurtleCreator(engine).create_ttls()`

3. Neo4j ingestion: `Neo4jImporter(...).import_ttls()`


The pipeline imports the following BioKB datasets:
- BRENDA (enzyme/metabolism information)
- ChEBI (chemical ontology / identifiers)
- COCONUT (natural products collection)
- IPNI (plant nomenclature identifiers)
- WFO (World Flora Online taxonomic backbone)
- WCVP (World Checklist of Vascular Plants)
- TaxTree (taxonomic structure for linking/normalization)

The complete pipeline is executed sequentially in `main.py`:
1. Create MySQL engine
2. `DbManager.import_biokb_dbs()` to load all BioKB sources into MySQL
3. `DbManager.create_turtle_files()` to export RDF/Turtle
4. `DbManager.import_neo4j(uri, user, password)` to load RDF into Neo4j
This structure ensures that the workflow can be rerun end-to-end with a single command while keeping the internal steps modular and testable.

#### Reproducibility

RReproducibility is achieved through:

- A local SQLite database file used as the relational data store.
- Containerized deployment of Neo4j via `docker-compose.yml`.
- A single-command Python pipeline (`main.py`) that executes the full workflow.

The Neo4j service is started using:

- `podman-compose up -d`

The full pipeline is then executed using:

- `python main.py`

Neo4j is accessed via the Bolt endpoint at `bolt://localhost:7687`, as defined in the compose configuration.

#### Code Quality and Version Control

- The pipeline follows a modular design, separating orchestration (`DbManager`) from dataset-specific logic (delegated to BioKB submodules).
- The project uses typed function signatures for core orchestration calls (e.g., `import_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str)`).
- Development notebooks are used for exploration and debugging, while the “official” pipeline remains the single Python entry point (`main.py`) to meet course requirements.

### 2.2 Data and Analysis

#### Input Data

The project integrates multiple heterogeneous biological and chemical datasets into a unified knowledge graph. The primary data sources include:

- **Ethnobotanical dataset (Ethnobot v2):** Contains structured information about traditional medicinal plant usage, including articles, tables, taxa, and associated diseases.

- **COCONUT database:** A curated repository of natural products, including physicochemical properties and drug-likeness metrics.

- **NCBI Taxonomy (DbNCBITaxTree):** Provides standardized taxonomic identifiers and hierarchical classification of organisms.

- **ChEBI and BRENDA (via BioKB):** Provide chemical ontology annotations and enzyme-related biochemical information.


The ethnobotanical dataset serves as the entry point for identifying Mediterranean plant species associated with wound-healing related terms. The BioKB databases provide chemical and biochemical annotations that allow linking plants to known natural products.

All datasets were converted into RDF Turtle files and imported into Neo4j, where they were represented as labeled nodes and typed relationships.


---

#### Analysis Workflow

The analytical workflow follows a structured multi-step graph traversal strategy:

1. Identification of wound-healing plants
Articles were filtered using a predefined list of wound-related disease terms. Mediterranean context was approximated using country mentions within article titles.
Query pattern:

```
Article → Table → Taxon → Disease
```

2. Taxonomic normalization
Ethnobotanical taxa were mapped to standardized NCBI Taxonomy nodes using string-based matching on scientific names:

```
(:Taxon) → (:Taxon:DbNCBITaxTree)
```

3. Compound association via COCONUT
Natural products were retrieved through the ontology bridge:

```
(:DbCoconut) -[:SAME_AS]- (:Taxon:DbNCBITaxTree)
```

4. Compound property extraction
For each compound, relevant chemical descriptors were extracted:
  - Molecular weight
  - Lipinski rule-of-five violations
  - QED drug-likeliness score
  - NP-likeness score

This workflow enables tracing biologically motivated hypotheses from traditional medicinal use to molecular-level compound information within a unified graph representation.


---

#### Output and Validation

The final output consists of a list of Mediterranean taxa associated with wound-healing terms.

Validation was performed through:
- Manual inspection of intermediate query results.
- Verification of taxonomic name matching.
- Schema inspection using Neo4j PROFILE to ensure query correctness.

While exact mechanistic validation (e.g., protein-level evidence) was not fully resolved due to schema integration complexity, the pipeline successfully demonstrates multi-database graph integration and compound retrieval.

---

## 3. Results

#### Identification of Mediterranean Wound-Healing Taxa

Using the predefined wound-related term list and Mediterranean country filter, the knowledge graph query pipeline identified:

- 200 distinct plant taxa

- Associated with wound-healing or burn-related indications

- Extracted from ethnobotanical articles


The query structure followed:

```
Article → Table → Taxon → Disease
```

Disease filtering was performed using an exact match strategy against curated wound-related expressions (e.g., “Wound”, “Burns”, “Skin lesions”, “wound healing”).

This resulted in a filtered subgraph of Mediterranean medicinal plants traditionally used for wound treatment.


---

#### Taxonomic Normalization

To enable integration with biochemical databases, ethnobotanical taxa were mapped to standardized NCBI Taxonomy nodes using scientific name matching.

This step was necessary because different datasets used heterogeneous taxonomic identifiers.

While string-based exact matching successfully identified corresponding NCBI Taxonomy nodes for a subset of taxa, inconsistencies in naming conventions (author abbreviations, formatting differences, capitalization) limited full automation.


---

#### Compound Integration Attempt (COCONUT)

The next analytical step aimed to associate identified plant taxa with known natural products from the COCONUT database.

COCONUT compounds were connected to NCBI taxonomy nodes via SAME_AS relationships:

```
DbCoconut → SAME_AS → Taxon:DbNCBITaxTree
```

However, integration between ethnobotanical taxa and COCONUT compounds required precise taxonomic normalization. Due to identifier heterogeneity and schema differences, a complete automated compound mapping was not achieved within the project timeframe.

Nevertheless, the graph structure and query framework for compound retrieval were successfully implemented and validated.


---

#### Quantitative Summary

Component Result

Mediterranean wound-healing taxa 200
Articles contributing evidence Multiple (filtered via country context)
Successfully imported Neo4j nodes ~10 million
Successfully imported relationships ~22 million
Cross-database compound integration Partially implemented


The system demonstrates scalable graph-based integration of large biological datasets and enables structured hypothesis-driven exploration.


---

## 4. Discussion

### Strengths

This project demonstrates:

- Successful integration of multiple heterogeneous biological databases into a unified Neo4j knowledge graph.

- Implementation of a reproducible containerized workflow using Podman and Docker Compose.

- Scalable graph traversal across ~10 million nodes and ~22 million relationships.

- Structured filtering of ethnobotanical data based on disease terms and geographical context.

- Ontology-aware integration using SAME_AS relations for cross-database mapping.


The modular architecture allows future expansion without redesigning the core system.


---

### Limitations

Several limitations were encountered:

1. Taxonomic Identifier Heterogeneity
Ethnobotanical data and COCONUT relied on different taxonomic reference systems, requiring string-based matching. Minor inconsistencies prevented fully automated mapping.


2. Performance Constraints
Queries involving large taxonomic joins required careful optimization to avoid full graph scans.


3. Geographical Approximation
Mediterranean filtering relied on country mentions in article titles, which may not fully capture ecological origin.

4. Incomplete Mechanistic Validation
While compound retrieval infrastructure was implemented, protein-level wound-healing mechanism validation remains future work.



These limitations reflect real-world challenges in biological knowledge graph integration.


---

### Future Work

Future improvements include:

- Implementation of persistent cross-database mapping edges (e.g., precomputed SAME_AS_NCBI links).

- Use of taxonomic identifiers (NCBI TaxID) instead of string matching.

- Integration of Gene Ontology (GO) annotations for wound-related biological processes.

- Quantitative ranking of compounds using drug-likeness and Lipinski metrics.

- Inclusion of curated Mediterranean biodiversity datasets instead of title-based filtering.


---

## 5. Conclusion

This project presents a graph-based computational framework for identifying Mediterranean medicinal plants associated with wound healing and exploring their potential natural products.

A large-scale Neo4j knowledge graph integrating ethnobotanical, taxonomic, and chemical databases was successfully constructed and queried. The pipeline identified 200 Mediterranean wound-healing plant taxa and established a structured foundation for compound-level investigation.

Although full automated mapping to COCONUT compounds was limited by taxonomic heterogeneity, the implemented ontology-bridging strategy demonstrates a scalable approach for cross-database integration.

The developed system provides a reproducible and extensible platform for future exploration of plant-derived bioactive compounds.


---

## 6. Documentation and User Guidance

Documentation was done during the project in various ways, such as documenting the code, creating issues and issue comments. 

The README file of this project could be viewed as summarized report and user guide, but also for more explanation of the workflow and code, the demo notebook is available.

[README](README.md)

[Demo Notebook](notebooks/demo.ipynb)

---

#### Reproducibility

- All databases are imported via scripted workflows.

- Turtle files are generated programmatically.

- Container configuration ensures consistent runtime environment.

- All parameters and method signatures are typed.

- Version control tracked via GitLab issue board and commits.


