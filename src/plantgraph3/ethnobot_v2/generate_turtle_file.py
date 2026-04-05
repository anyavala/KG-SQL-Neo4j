"""
SQLite → Turtle (RDF) Converter
Database: prog_lab2 (1).db

Ontology:
  - ex:Journal   → nlmTa, isoAbbrev, publisherIdentifier
  - ex:Article   → pmcid, pmid, doi, title, abstract  --publishedIn--> Journal
  - ex:Table     → tableId  --partOf--> Article
  - ex:Taxon     → taxonName, ipni
  - ex:Disease   → diseaseName
  - ex:Table     --mentionsTaxon--> Taxon
  - ex:Table     --mentionsDisease--> Disease
  - ex:Taxon     --usedFor--> Disease  (pairs from table_disease_taxon)
"""

import os
import re
from rdflib import Graph, Namespace, URIRef, Literal, RDF, XSD
import sqlite3

# Namespace definitions 
EX   = Namespace("http://example.org/ethnomed/")
PROP = Namespace("http://example.org/ethnomed/prop/")

DB_PATH  = "prog_lab2.db"
OUT_DIR  = "turtle_files"
CHUNK    = 5000          # all tables are small except table_disease_taxon, so we chunk it to avoid memory issues

os.makedirs(OUT_DIR, exist_ok=True)


#Helper functions
def uri_safe(text: str) -> str:
    """Metni URI parçasına uygun hale getirir."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", str(text)).strip("_")


def new_graph() -> Graph:
    g = Graph()
    g.bind("ex",   EX)
    g.bind("prop", PROP)
    return g


def save(g: Graph, filename: str):
    path = os.path.join(OUT_DIR, filename)
    g.serialize(destination=path, format="turtle")
    print(f"  OK {filename}  ({len(g)} triple)")


# ── 1. Journal ─────────────────────────────────────────────────────────────────
def export_journals(cursor):
    print("\n[1/4] Journal table ...")
    g = new_graph()

    cursor.execute("SELECT id, nlm_ta, iso_abbrev, publisher_identifier FROM journal")
    for row in cursor.fetchall():
        jid, nlm_ta, iso_abbrev, pub_id = row
        uri = EX[f"journal/{jid}"]
        g.add((uri, RDF.type,       EX.Journal))
        g.add((uri, PROP.journalId, Literal(jid, datatype=XSD.integer)))
        if nlm_ta:
            g.add((uri, PROP.nlmTa,               Literal(nlm_ta)))
        if iso_abbrev:
            g.add((uri, PROP.isoAbbrev,           Literal(iso_abbrev)))
        if pub_id:
            g.add((uri, PROP.publisherIdentifier, Literal(pub_id)))

    save(g, "01_journals.ttl")


# ── 2. Article ─────────────────────────────────────────────────────────────────
def export_articles(cursor):
    print("\n[2/4] Article table is being processed...")
    g = new_graph()

    cursor.execute(
        "SELECT pmcid, pmid, doi, title, abstract, journal_id FROM article"
    )
    for row in cursor.fetchall():
        pmcid, pmid, doi, title, abstract, jid = row
        uri = EX[f"article/{pmcid}"]
        g.add((uri, RDF.type,       EX.Article))
        g.add((uri, PROP.pmcid,     Literal(pmcid,  datatype=XSD.integer)))
        if pmid:
            g.add((uri, PROP.pmid,  Literal(pmid,   datatype=XSD.integer)))
        if doi:
            g.add((uri, PROP.doi,   Literal(doi)))
        if title:
            g.add((uri, PROP.title, Literal(title)))
        if abstract:
            g.add((uri, PROP.abstract, Literal(abstract)))
        # Journal ilişkisi
        g.add((uri, PROP.publishedIn, EX[f"journal/{jid}"]))

    save(g, "02_articles.ttl")


# ── 3. TableInArticle ──────────────────────────────────────────────────────────
def export_tables(cursor):
    print("\n[3/4] table_in_article table is being processed (chunk={})...".format(CHUNK))
    cursor.execute("SELECT COUNT(*) FROM table_in_article")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT id, article_id FROM table_in_article")
    rows = cursor.fetchall()

    for chunk_idx, start in enumerate(range(0, total, CHUNK)):
        g = new_graph()
        chunk = rows[start : start + CHUNK]
        for tid, art_id in chunk:
            uri = EX[f"table/{tid}"]
            g.add((uri, RDF.type,        EX.Table))
            g.add((uri, PROP.tableId,    Literal(tid,     datatype=XSD.integer)))
            g.add((uri, PROP.partOf,     EX[f"article/{art_id}"]))
        save(g, f"03_tables_{chunk_idx+1:02d}.ttl")


# ── 4. Taxon, Disease and relationships ─────────────────────────────────────────────
def export_disease_taxon(cursor):
    print("\n[4/4] table_disease_taxon table is being processed (chunk={})...".format(CHUNK))
    cursor.execute("SELECT COUNT(*) FROM table_disease_taxon")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT \"index\", taxon, disease, table_id, ipni FROM table_disease_taxon"
    )
    rows = cursor.fetchall()

    for chunk_idx, start in enumerate(range(0, total, CHUNK)):
        g = new_graph()
        chunk = rows[start : start + CHUNK]

        for idx, taxon, disease, table_id, ipni in chunk:
            # Taxon node
            taxon_safe = uri_safe(taxon) if taxon else f"unknown_{idx}"
            taxon_uri  = EX[f"taxon/{taxon_safe}"]
            g.add((taxon_uri, RDF.type,         EX.Taxon))
            if taxon:
                g.add((taxon_uri, PROP.taxonName, Literal(taxon)))
            if ipni:
                g.add((taxon_uri, PROP.ipni,      Literal(ipni)))

            # Disease node
            dis_safe  = uri_safe(disease) if disease else f"unknown_{idx}"
            dis_uri   = EX[f"disease/{dis_safe}"]
            g.add((dis_uri, RDF.type,            EX.Disease))
            if disease:
                g.add((dis_uri, PROP.diseaseName, Literal(disease)))

            # Table → Taxon relationships
            if table_id is not None:
                table_uri = EX[f"table/{int(table_id)}"]
                g.add((table_uri, PROP.mentionsTaxon,   taxon_uri))
                g.add((table_uri, PROP.mentionsDisease, dis_uri))

            # Taxon → Disease (usedFor)
            g.add((taxon_uri, PROP.usedFor, dis_uri))

        save(g, f"04_disease_taxon_{chunk_idx+1:02d}.ttl")



def main():
    print(f"Veritabani: {DB_PATH}")
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    export_journals(cursor)
    export_articles(cursor)
    export_tables(cursor)
    export_disease_taxon(cursor)

    conn.close()
    print("\nTum Turtle files are being generated in:", os.path.abspath(OUT_DIR))


if __name__ == "__main__":
    main()
