"""
Turtle (RDF) files → Neo4j loader
----------------------------------
Workflow:
  - Parses each .ttl file using rdflib
  - Uses Neo4j Python driver with MERGE to write nodes and relationships
  - Neosemantics (n10s) plugin is NOT required; uses standard Cypher

Usage:
  1. Update the NEO4J_* variables below according to your Neo4j settings
  2. python load_to_neo4j.py

Requirements:
  pip install rdflib neo4j
"""

import os
import glob
import time
from rdflib import Graph, Namespace, RDF, URIRef, Literal, XSD
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# ── Neo4j connection settings (read from environment variables or use defaults) ─
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ── File paths ──────────────────────────────────────────────────────────────
TTL_DIR = os.getenv("TTL_DIR", "turtle_files")

# ── Namespaces ──────────────────────────────────────────────────────────────
EX   = Namespace("http://example.org/ethnomed/")
PROP = Namespace("http://example.org/ethnomed/prop/")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Extract type and ID from URI
# ─────────────────────────────────────────────────────────────────────────────
def parse_uri(uri: URIRef):
    s = str(uri)
    base = "http://example.org/ethnomed/"
    if s.startswith(base):
        rest = s[len(base):]
        parts = rest.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]   # (type, id_string)
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Batch writer for efficient inserts
# ─────────────────────────────────────────────────────────────────────────────
class BatchWriter:
    def __init__(self, driver, database, batch_size=500):
        self.driver     = driver
        self.database   = database
        self.batch_size = batch_size
        self.nodes      = []   # {label, props}
        self.rels       = []   # {src_type, src_uri, rel_type, tgt_type, tgt_uri}

    def flush_nodes(self, session):
        if not self.nodes:
            return
        by_label = {}
        for n in self.nodes:
            by_label.setdefault(n["label"], []).append(n["props"])
        for label, props_list in by_label.items():
            q = (
                f"UNWIND $rows AS row "
                f"MERGE (n:{label} {{uri: row.uri}}) "
                f"SET n += row"
            )
            session.run(q, rows=props_list)
        self.nodes.clear()

    def flush_rels(self, session):
        if not self.rels:
            return
        by_key = {}
        for r in self.rels:
            key = (r["src_type"], r["rel_type"], r["tgt_type"])
            by_key.setdefault(key, []).append(r)
        for (st, rt, tt), items in by_key.items():
            q = (
                f"UNWIND $rows AS row "
                f"MATCH (a:{st} {{uri: row.src_uri}}) "
                f"MATCH (b:{tt} {{uri: row.tgt_uri}}) "
                f"MERGE (a)-[:{rt}]->(b)"
            )
            session.run(q, rows=[{"src_uri": i["src_uri"], "tgt_uri": i["tgt_uri"]} for i in items])
        self.rels.clear()

    def flush(self, session):
        self.flush_nodes(session)
        self.flush_rels(session)

    def add_node(self, session, label: str, props: dict):
        self.nodes.append({"label": label, "props": props})
        if len(self.nodes) >= self.batch_size:
            self.flush_nodes(session)

    def add_rel(self, session, src_type, src_uri, rel_type, tgt_type, tgt_uri):
        self.rels.append({
            "src_type": src_type, "src_uri": src_uri,
            "rel_type": rel_type,
            "tgt_type": tgt_type, "tgt_uri": tgt_uri,
        })
        if len(self.rels) >= self.batch_size:
            self.flush_rels(session)


# ─────────────────────────────────────────────────────────────────────────────
# Process a single TTL file
# ─────────────────────────────────────────────────────────────────────────────
def process_file(ttl_path: str, session, writer: BatchWriter):
    g = Graph()
    g.parse(ttl_path, format="turtle")

    # RDF type → Neo4j label mapping
    type_label = {
        str(EX.Journal): "Journal",
        str(EX.Article): "Article",
        str(EX.Table):   "Table",
        str(EX.Taxon):   "Taxon",
        str(EX.Disease): "Disease",
    }

    # RDF predicate → Neo4j relationship type mapping
    rel_map = {
        str(PROP.publishedIn):     "PUBLISHED_IN",
        str(PROP.partOf):          "PART_OF",
        str(PROP.mentionsTaxon):   "MENTIONS_TAXON",
        str(PROP.mentionsDisease): "MENTIONS_DISEASE",
        str(PROP.usedFor):         "USED_FOR",
    }

    # RDF predicate → Neo4j property key mapping
    prop_map = {
        str(PROP.journalId):             "journalId",
        str(PROP.nlmTa):                 "nlmTa",
        str(PROP.isoAbbrev):             "isoAbbrev",
        str(PROP.publisherIdentifier):   "publisherIdentifier",
        str(PROP.pmcid):                 "pmcid",
        str(PROP.pmid):                  "pmid",
        str(PROP.doi):                   "doi",
        str(PROP.title):                 "title",
        str(PROP.abstract):              "abstract",
        str(PROP.tableId):               "tableId",
        str(PROP.taxonName):             "taxonName",
        str(PROP.ipni):                  "ipni",
        str(PROP.diseaseName):           "diseaseName",
    }

    # --- Collect nodes ---
    subjects = set(g.subjects(RDF.type, None))
    for subj in subjects:
        if not isinstance(subj, URIRef):
            continue
        rdf_type = g.value(subj, RDF.type)
        if rdf_type is None:
            continue
        label = type_label.get(str(rdf_type))
        if not label:
            continue

        props = {"uri": str(subj)}
        for pred, obj in g.predicate_objects(subj):
            if str(pred) == str(RDF.type):
                continue
            pk = prop_map.get(str(pred))
            if pk and isinstance(obj, Literal):
                val = obj.toPython()
                # Truncate very long strings (e.g., long abstracts)
                if isinstance(val, str) and len(val) > 32000:
                    val = val[:32000]
                props[pk] = val

        writer.add_node(session, label, props)

    # --- Collect relationships ---
    for subj, pred, obj in g:
        if not isinstance(subj, URIRef) or not isinstance(obj, URIRef):
            continue
        rel_type = rel_map.get(str(pred))
        if not rel_type:
            continue

        src_type_uri = g.value(subj, RDF.type)
        tgt_type_uri = g.value(obj,  RDF.type)

        src_label = type_label.get(str(src_type_uri)) if src_type_uri else None
        tgt_label = type_label.get(str(tgt_type_uri)) if tgt_type_uri else None

        # If type triple is missing, infer label from URI
        if not src_label:
            t, _ = parse_uri(subj)
            label_map2 = {"journal":"Journal","article":"Article","table":"Table",
                          "taxon":"Taxon","disease":"Disease"}
            src_label = label_map2.get(t)
        if not tgt_label:
            t, _ = parse_uri(obj)
            label_map2 = {"journal":"Journal","article":"Article","table":"Table",
                          "taxon":"Taxon","disease":"Disease"}
            tgt_label = label_map2.get(t)

        if src_label and tgt_label:
            writer.add_rel(session, src_label, str(subj), rel_type, tgt_label, str(obj))

    writer.flush(session)


# ─────────────────────────────────────────────────────────────────────────────
# Create indexes (for performance)
# ─────────────────────────────────────────────────────────────────────────────
def create_indexes(session):
    indexes = [
        ("Journal", "uri"),
        ("Article", "uri"),
        ("Table",   "uri"),
        ("Taxon",   "uri"),
        ("Disease", "uri"),
    ]
    for label, prop in indexes:
        try:
            session.run(
                f"CREATE INDEX {label.lower()}_{prop} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.{prop})"
            )
        except Exception as e:
            print(f"  Index warning ({label}.{prop}): {e}")
    print("  Indexes ready.")


# ─────────────────────────────────────────────────────────────────────────────
# Main workflow
# ─────────────────────────────────────────────────────────────────────────────
def wait_for_neo4j(uri, user, password, retries=20, delay=5):
    """Wait until Neo4j is ready (extra safety for Docker healthcheck)."""
    print(f"Waiting for Neo4j: {uri}")
    for attempt in range(1, retries + 1):
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as s:
                s.run("RETURN 1")
            driver.close()
            print("  Neo4j is ready!")
            return
        except Exception as e:
            print(f"  Attempt {attempt}/{retries}: {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to Neo4j (timeout).")


def main():
    ttl_files = sorted(glob.glob(os.path.join(TTL_DIR, "*.ttl")))
    if not ttl_files:
        print(f"ERROR: No .ttl files found in {TTL_DIR}/")
        return

    wait_for_neo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    print(f"Connecting to Neo4j: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            print("Creating indexes...")
            create_indexes(session)

            writer = BatchWriter(driver, NEO4J_DATABASE, batch_size=500)

            for i, ttl_path in enumerate(ttl_files, 1):
                fname = os.path.basename(ttl_path)
                print(f"\n[{i}/{len(ttl_files)}] Processing {fname}...")
                t0 = time.time()
                process_file(ttl_path, session, writer)
                print(f"  Completed ({time.time()-t0:.1f}s)")

        print("\nNeo4j loading completed successfully!")

    except Exception as e:
        print(f"\nERROR: {e}")
        raise
    finally:
        driver.close()


if __name__ == "__main__":
    main()