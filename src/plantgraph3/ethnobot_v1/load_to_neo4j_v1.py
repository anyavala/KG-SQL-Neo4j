"""
Turtle (.ttl) -> Neo4j Loader
Auto-detects n10s plugin. Uses n10s if available, otherwise falls back
to direct loading via rdflib + Cypher (works on any Neo4j instance).
"""

import os
import time
from neo4j import GraphDatabase
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j_password"
TTL_DIR = "import"

TTL_FILES = [
    "reference_v1.ttl",
    "region_v1.ttl",
    "mode_lookups_v1.ttl",
    "traditional_usage_v1.ttl",
    "species_v1.ttl",
    "formulation_v1.ttl",
    "plant_specimen_v1.ttl",
]

BATCH_SIZE = 500


def wait_for_neo4j(driver, retries=15, delay=5):
    for i in range(retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            print("Neo4j connection successful.")
            return
        except Exception as e:
            print(f"Waiting for Neo4j... ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to Neo4j!")


def n10s_available(session):
    """Check if n10s plugin is installed."""
    try:
        result = session.run(
            "CALL dbms.procedures() YIELD name "
            "WHERE name STARTS WITH 'n10s' RETURN count(name) AS cnt"
        )
        return result.single()["cnt"] > 0
    except Exception:
        return False


# ------------------------------------------------------------------
# n10s approach (fast — requires n10s plugin)
# ------------------------------------------------------------------

def setup_n10s(session):
    print("Setting up n10s...")

    config_exists = False
    try:
        session.run("CALL n10s.graphconfig.show()").consume()
        config_exists = True
        print("  n10s config already initialized, skipping.")
    except Exception:
        pass

    if not config_exists:
        try:
            session.run("""
                CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS
                FOR (r:Resource) REQUIRE r.uri IS UNIQUE
            """).consume()
            print("  Constraint created.")
        except Exception as e:
            print(f"  Constraint already exists: {e}")

        session.run("""
            CALL n10s.graphconfig.init({
                handleVocabUris: 'IGNORE',
                handleMultival: 'OVERWRITE',
                handleRDFTypes: 'LABELS_AND_NODES',
                keepLangTag: false,
                keepCustomDataTypes: false
            })
        """).consume()
        print("  n10s GraphConfig initialized.")


def import_ttl_n10s(session, filename):
    filepath = os.path.join(TTL_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [SKIP] {filename} - file not found")
        return

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Loading: {filename} ({file_size_mb:.1f} MB)...")

    container_path = f"file:///var/lib/neo4j/import/{filename}"
    result = session.run(f"""
        CALL n10s.rdf.import.fetch('{container_path}', 'Turtle')
    """)
    summary = result.single()
    if summary:
        print(f"  [OK] triplesLoaded={summary.get('triplesLoaded', '?')}, "
              f"triplesParsed={summary.get('triplesParsed', '?')}")
    else:
        print(f"  [OK] {filename} loaded.")


# ------------------------------------------------------------------
# Direct approach (works without n10s — uses rdflib)
# ------------------------------------------------------------------

def get_local_name(uri):
    uri = str(uri)
    return uri.split("#")[-1] if "#" in uri else uri.split("/")[-1]


def literal_value(o):
    try:
        return o.toPython()
    except Exception:
        return str(o)


def import_ttl_direct(session, filename):
    filepath = os.path.join(TTL_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [SKIP] {filename} - file not found")
        return

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Parsing: {filename} ({file_size_mb:.1f} MB)...")

    g = Graph()
    g.parse(filepath, format="turtle")
    print(f"  Parsed {len(g):,} triples.")

    # Group triples by subject
    nodes = {}
    relationships = []

    for s, p, o in g:
        s_str = str(s)
        if s_str not in nodes:
            nodes[s_str] = {"uri": s_str, "label": "Resource", "props": {"uri": s_str}}

        if p == RDF.type:
            nodes[s_str]["label"] = get_local_name(o)
        elif isinstance(o, Literal):
            nodes[s_str]["props"][get_local_name(p)] = literal_value(o)
        elif isinstance(o, URIRef):
            relationships.append({
                "from": s_str,
                "to": str(o),
                "type": get_local_name(p)
            })

    # Create nodes in batches grouped by label
    node_list = list(nodes.values())
    total_nodes = len(node_list)
    print(f"  Creating {total_nodes:,} nodes...")

    by_label = {}
    for node in node_list:
        by_label.setdefault(node["label"], []).append(node["props"])

    loaded = 0
    for label, props_list in by_label.items():
        for i in range(0, len(props_list), BATCH_SIZE):
            batch = props_list[i:i + BATCH_SIZE]
            session.run(
                f"UNWIND $batch AS row MERGE (n:`{label}` {{uri: row.uri}}) SET n += row",
                batch=batch
            ).consume()
            loaded += len(batch)
            print(f"  Nodes: {loaded}/{total_nodes}", end="\r")
    print(f"  Nodes created: {total_nodes:,}")

    # Create relationships in batches grouped by type
    total_rels = len(relationships)
    print(f"  Creating {total_rels:,} relationships...")

    by_type = {}
    for rel in relationships:
        by_type.setdefault(rel["type"], []).append({"from": rel["from"], "to": rel["to"]})

    loaded_rels = 0
    for rel_type, rels in by_type.items():
        for i in range(0, len(rels), BATCH_SIZE):
            batch = rels[i:i + BATCH_SIZE]
            try:
                session.run(
                    f"UNWIND $batch AS row "
                    f"MATCH (a {{uri: row.from}}), (b {{uri: row.to}}) "
                    f"MERGE (a)-[:`{rel_type}`]->(b)",
                    batch=batch
                ).consume()
            except Exception as e:
                print(f"\n  [WARN] Relationship batch error ({rel_type}): {e}")
            loaded_rels += len(batch)
            print(f"  Relationships: {loaded_rels}/{total_rels}", end="\r")
    print(f"  Relationships created: {total_rels:,}")


# ------------------------------------------------------------------
# Verification
# ------------------------------------------------------------------

def verify(session):
    print("\n=== Verification ===")
    total = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
    print(f"Total node count: {total:,}")

    result = session.run("""
        MATCH (n)
        WITH labels(n) AS lbls, count(n) AS cnt
        RETURN lbls, cnt ORDER BY cnt DESC LIMIT 10
    """)
    print("Label distribution:")
    for row in result:
        print(f"  {row['lbls']}: {row['cnt']:,}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    print("=== Turtle -> Neo4j Loader ===\n")

    missing = [f for f in TTL_FILES if not os.path.exists(os.path.join(TTL_DIR, f))]
    if missing:
        print(f"Missing TTL files: {missing}")
        print("Please run generate_turtle.py first!")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        wait_for_neo4j(driver)

        with driver.session() as session:
            use_n10s = n10s_available(session)

            if use_n10s:
                print("n10s plugin detected — using fast n10s import.\n")
                setup_n10s(session)
                print("\nLoading TTL files...")
                for filename in TTL_FILES:
                    import_ttl_n10s(session, filename)
            else:
                print("n10s not found — using direct rdflib import.\n")
                print("Loading TTL files...")
                for filename in TTL_FILES:
                    print(f"\n[{filename}]")
                    import_ttl_direct(session, filename)

            verify(session)

    finally:
        driver.close()

    print("\n=== Neo4j loading complete! ===")
    print("Neo4j Browser: http://localhost:7474")
    print("User: neo4j / neo4j_password")


if __name__ == "__main__":
    main()
