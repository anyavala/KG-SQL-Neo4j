---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
layout: false
mermaid: True
---
<!-- _class: lead -->
<style>
section.lead {
  text-align: center;
}
.name {
  position: absolute;
  bottom: 40px;
  right: 70px;
  font-size: 25px;
  color: #000000;
}
</style>

 
##  BioKB Integration and Knowledge Graph Construction to explore mediterranean plants usage in wound healing 
### Programming Lab 2 – Group 3
Mehak Nadeem
Özlem Kalkan
Parmida Zamani
Rojin Sadat Yasini


---
# Introduction

The goal of this project is to generate a pipeline to generate a comprehensive knowledge graph to explore potential compounds in mediterranean plants that treats wounds on skin.

---
# Databases


- Plant taxonomy → IPNI, WFO, WCVP, taxtree  
- Chemicals → ChEBI, COCONUT  
- Enzymes → BRENDA  
- Literature → Ethnobotv2 
- Literature and plant species → Ethnobotv1 
  


---

# Methodology

We implemented:

1. Automated BioKB import  
2. RDF/Turtle export of BioKB 
3. Import BioKB to Neo4j
4. Ethnobotv1, Ethnobotv2 import
5. Turtle export of Ethnobotv1, Ethnobotv2
6. Import Ethnobotv1, Ethnobotv2 to Neo4j
7. Neo4j graph construction  
8. Cross-domain Cypher queries  



---

# Automated BioKB import

- python main.py 

``` 
engine = create_engine(
    "mysql+pymysql://group_project_user:group_project_password@localhost:3306/group_project_db"
)

dbm = DbManager(engine)

dbm.import_biokb_dbs()

```
---

# Turtle export of BioKB

```
dbm.create_turtle_files()
```

example:
```
dbm.create_chebi_turtle_files()
dbm.create_brenda_turtle_files()
```

---

# Import BioKB to Neo4j

```
dbm.import_neo4j(
     neo4j_uri="bolt://localhost:7687",
     neo4j_user="neo4j",
     neo4j_password="neo4j_password",
 )
```

---

# Ethnobotv2 scripts 

```
#import generate_turtle_file and load_to_neo4jscripts first. 
from plantgraph3.ethnobot_v2 import generate_turtle_file as s2t
from plantgraph3.ethnobot_v2 import load_to_neo4j as loader
import sqlite3
```
![width:600px height:380px](images/15.png)

---
# Turtle generation of Ethnobotv2  
```
from pathlib import Path
from sqlalchemy import create_engine


conn = sqlite3.connect("prog_lab2.db")
cursor = conn.cursor()

#Create Turtle files for ethnobotanical data prog_lab2.db

s2t.export_journals(cursor)
s2t.export_articles(cursor)
s2t.export_tables(cursor)
s2t.export_disease_taxon(cursor)

conn.close()
```
---
# Turtle generation of Ethnobotv1 
```
from plantgraph3.ethnobot_v1.clean_ethnobot_db import EthnobotDBCleaner

```
* before generating turtle file, redundant tables and empty tables are removed

```
from plantgraph3.ethnobot_v1 import generate_turtle_v1 as gen
```

- Table left after removal:
conservation_status, region_type, specimen_part, usage_type, pharmacological_effect, molecule, mode_of_preparation, mode_of_administration, reference, region, species, traditional_usage, formulation, species_region_association, formulation_mode_of_administration_association, plant_specimen, plant_specimen_specimen_part_association, eb_index, ethnic_info

---
![width:700px height:500px](images/17.png)

---

# Import Ethnobotv1 to Neo4j 

```
from plantgraph3.ethnobot_v1 import load_to_neo4j_v1 as loader
```


---
# Neo4j graph construction
The knowledge graph integrates multiple biological domains:

• Plants (taxonomy databases)
• Chemical compounds (ChEBI, COCONUT)
• Enzymes (BRENDA)
• Ethnobotanical literature

Relationships connect entities across databases:

Plant → produces → Compound
Compound → interacts with → Enzyme
Article → mentions → Plant

Impact: Enables cross-database biological discovery



---
# Neo4j graph construction

![width:700px](images/01.jpeg) 
![width:700px](images/02.jpeg)
Neo4j is accessed via:
http://localhost:7474  
  


---

# Why Graph Database Instead of Relational Database?

Biological data is highly connected.

Relational database requires complex JOINs:

Plant → Compound → Enzyme → Disease

Graph database advantages:

• Direct relationship traversal
• Faster multi-step queries
• Natural representation of biological networks
• Scalable for millions of nodes


---
# Automated Data Integration Pipeline
Pipeline steps:

BioKB databases
      ↓
Turtle file generation
      ↓
Neo4j graph import
      ↓
Graph construction
      ↓
Cypher queries and analysis

Fully automated integration pipeline.

---

# Reproducibility and Deployment

Ensured through:

• Containerized environment (Docker/Podman)
• Version-controlled source code
• Automated database import pipeline

Benefits:

• Easy replication of results
• Consistent environment
• Supports collaborative research



---
# Modular System Architecture
## Library Design

Project components:

• Docker containers – isolate services
• Neo4j database – graph storage
• MySQL database – BioKB storage
• Python scripts – automation and import
• Configuration files – environment setup

---  
# Modular System Architecture

![width:600px height:500px](images/11.png)


---
# Workflow 
1. Return article with plants and diseases that plants have a role  
2. Filter by  skin wound types 
3. Search mediterranean  countries contained in articles names and filter
as a result we obtained Mediterranean plants involving in skin wound types diseases
4. We returned the compounds from Chebi database that playing a role in wound processes
---

# Cypher queries 

```
WITH 
[ {Wound Terms} ] AS woundList,

[ {Mediterranean Countries} ] AS medCountries

MATCH (a:Article)<-[:PART_OF]-(tb:Table)
      -[:MENTIONS_TAXON]->(t:Taxon)
      -[:USED_FOR]->(d:Disease)

WHERE 
  ANY(w IN woundList 
      WHERE toLower(coalesce(d.diseaseName,d.name,'')) = toLower(w))
  AND ANY(country IN medCountries
      WHERE toLower(a.title) CONTAINS country)

RETURN
  a.title AS article,
  t.taxonName AS plant,
  t.ipni AS ipni,
  coalesce(d.diseaseName, d.name) AS disease
LIMIT 200;
```
---
# Cypher queries


![width:600px height:250px](images/07.png)


---

# Cypher queries
```
query =""" MATCH (c:DbChEBI)
WHERE toLower(coalesce(c.definition,'')) CONTAINS "wound"
RETURN c.ascii_name, c.definition
LIMIT 50"""
pd.DataFrame(query_neo4j(query))
```
---
# Cypher queries
![width:7000px height:450px](images/10.png)

---
# Cypher queries

```
MATCH (t:DbNCBITaxTree:Taxon)
      <-[:SAME_AS]-(c:DbCoconut)
RETURN t.scientific_name, c.name
LIMIT 50
```


---
![width:700px height:550px](images/09.jpeg)

---
# Contribution – Issue Board

in total 30 issues

![width:8000px height:450px](images/04.jpeg)


---

# Contribution – Commits
 

![width:8000px height:450px](images/05.jpeg)

---
# Contribution – Commits
 

![width:8000px height:450px](images/06.jpeg)


---

# Thank You

Questions?

