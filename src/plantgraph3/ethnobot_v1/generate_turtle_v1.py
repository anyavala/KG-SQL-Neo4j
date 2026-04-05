"""
SQLite -> Turtle (.ttl) Generator
Exports ethnobotany data from a SQLite database into RDF/Turtle format files.
Namespace: http://ethnobot.org/
"""

import os
from sqlalchemy import create_engine, text
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

SQLITE_URL = "sqlite:///ethnobot_v1.db"
OUTPUT_DIR = "import"

# Define Namespaces
ETHNOBOT = Namespace("http://ethnobot.org/")
EB_CLASS = Namespace("http://ethnobot.org/class/")
EB_PROP = Namespace("http://ethnobot.org/property/")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def new_graph():
    g = Graph()
    g.bind("ethnobot", ETHNOBOT)
    g.bind("eb", EB_CLASS)
    g.bind("ebp", EB_PROP)
    g.bind("xsd", XSD)
    g.bind("rdfs", RDFS)
    return g


def safe_literal(value, datatype=None):
    if value is None:
        return None
    if datatype:
        return Literal(value, datatype=datatype)
    return Literal(str(value))


def save_graph(g, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    g.serialize(destination=path, format="turtle")
    print(f"  Saved: {path} ({len(g)} triple)")


def generate_species(conn):
    print("species.ttl is being generated...")
    g = new_graph()
    rows = conn.execute(text("""
        SELECT s.id, s.scientific_name, s.english_name, s.species, s.family,
               s.genus, s.ontology_id, cs.status_type, cs.status_year, cs.status_source
        FROM species s
        LEFT JOIN conservation_status cs ON s.conservation_status_id = cs.id
    """))
    for row in rows:
        subj = ETHNOBOT[f"species_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.Species))
        if row.scientific_name:
            g.add((subj, EB_PROP.scientificName, safe_literal(row.scientific_name)))
        if row.english_name:
            g.add((subj, EB_PROP.englishName, safe_literal(row.english_name)))
        if row.species:
            g.add((subj, EB_PROP.species, safe_literal(row.species)))
        if row.family:
            g.add((subj, EB_PROP.family, safe_literal(row.family)))
        if row.genus:
            g.add((subj, EB_PROP.genus, safe_literal(row.genus)))
        if row.ontology_id:
            g.add((subj, EB_PROP.ontologyId, safe_literal(row.ontology_id)))
        if row.status_type:
            g.add((subj, EB_PROP.conservationStatus, safe_literal(row.status_type)))
        if row.status_year:
            g.add((subj, EB_PROP.conservationStatusYear, safe_literal(str(row.status_year))))
        if row.status_source:
            g.add((subj, EB_PROP.conservationStatusSource, safe_literal(row.status_source)))
    save_graph(g, "species.ttl")


def generate_region(conn):
    print("region.ttl is being generated...")
    g = new_graph()
    rows = conn.execute(text("""
        SELECT r.id, r.region, r.location, r.province, r.country, r.biome,
               r.latitude, r.longitude, r.elevation, r.ontology_id,
               rt.formulation_usage_region, rt.species_distribution_region,
               rt.specimen_collection_region
        FROM region r
        LEFT JOIN region_type rt ON r.region_type_id = rt.id
    """))
    for row in rows:
        subj = ETHNOBOT[f"region_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.Region))
        if row.region:
            g.add((subj, EB_PROP.regionName, safe_literal(row.region)))
        if row.location:
            g.add((subj, EB_PROP.location, safe_literal(row.location)))
        if row.province:
            g.add((subj, EB_PROP.province, safe_literal(row.province)))
        if row.country:
            g.add((subj, EB_PROP.country, safe_literal(row.country)))
        if row.biome:
            g.add((subj, EB_PROP.biome, safe_literal(row.biome)))
        if row.latitude is not None:
            g.add((subj, EB_PROP.latitude, Literal(float(row.latitude), datatype=XSD.double)))
        if row.longitude is not None:
            g.add((subj, EB_PROP.longitude, Literal(float(row.longitude), datatype=XSD.double)))
        if row.elevation is not None:
            g.add((subj, EB_PROP.elevation, Literal(float(row.elevation), datatype=XSD.double)))
        if row.ontology_id:
            g.add((subj, EB_PROP.ontologyId, safe_literal(row.ontology_id)))
    save_graph(g, "region.ttl")


def generate_reference(conn):
    print("reference.ttl is being generated...")
    g = new_graph()
    rows = conn.execute(text("""
        SELECT id, reference_text, title, doi, url, journal,
               authors, volume, issue, page, year
        FROM reference
    """))
    for row in rows:
        subj = ETHNOBOT[f"reference_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.Reference))
        if row.title:
            g.add((subj, EB_PROP.title, safe_literal(row.title)))
        if row.reference_text:
            g.add((subj, EB_PROP.referenceText, safe_literal(row.reference_text)))
        if row.doi:
            g.add((subj, EB_PROP.doi, safe_literal(row.doi)))
        if row.url:
            g.add((subj, EB_PROP.url, safe_literal(row.url)))
        if row.journal:
            g.add((subj, EB_PROP.journal, safe_literal(row.journal)))
        if row.authors:
            g.add((subj, EB_PROP.authors, safe_literal(row.authors)))
        if row.volume:
            g.add((subj, EB_PROP.volume, safe_literal(str(row.volume))))
        if row.issue:
            g.add((subj, EB_PROP.issue, safe_literal(str(row.issue))))
        if row.page:
            g.add((subj, EB_PROP.page, safe_literal(str(row.page))))
        if row.year:
            g.add((subj, EB_PROP.year, Literal(int(row.year), datatype=XSD.integer)))
    save_graph(g, "reference.ttl")


def generate_traditional_usage(conn):
    print("traditional_usage.ttl is being generated...")
    g = new_graph()
    rows = conn.execute(text("""
        SELECT tu.id, tu.usage_term, tu.usage_category, tu.usage_subcategory,
               tu.ontology_id, ut.usage_type
        FROM traditional_usage tu
        LEFT JOIN usage_type ut ON tu.usage_type_id = ut.id
    """))
    for row in rows:
        subj = ETHNOBOT[f"traditional_usage_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.TraditionalUsage))
        if row.usage_term:
            g.add((subj, EB_PROP.usageTerm, safe_literal(row.usage_term)))
        if row.usage_category:
            g.add((subj, EB_PROP.usageCategory, safe_literal(row.usage_category)))
        if row.usage_subcategory:
            g.add((subj, EB_PROP.usageSubcategory, safe_literal(row.usage_subcategory)))
        if row.ontology_id:
            g.add((subj, EB_PROP.ontologyId, safe_literal(row.ontology_id)))
        if row.usage_type:
            g.add((subj, EB_PROP.usageType, safe_literal(row.usage_type)))
    save_graph(g, "traditional_usage.ttl")


def generate_mode_lookups(conn):
    print("mode_lookups.ttl is being generated...")
    g = new_graph()

    rows = conn.execute(text("SELECT id, method FROM mode_of_preparation"))
    for row in rows:
        subj = ETHNOBOT[f"mode_of_preparation_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.ModeOfPreparation))
        if row.method:
            g.add((subj, EB_PROP.method, safe_literal(row.method)))

    rows = conn.execute(text("SELECT id, mode FROM mode_of_administration"))
    for row in rows:
        subj = ETHNOBOT[f"mode_of_administration_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.ModeOfAdministration))
        if row.mode:
            g.add((subj, EB_PROP.mode, safe_literal(row.mode)))

    rows = conn.execute(text("SELECT id, specimen_part FROM specimen_part"))
    for row in rows:
        subj = ETHNOBOT[f"specimen_part_{row.id}"]
        g.add((subj, RDF.type, EB_CLASS.SpecimenPart))
        if row.specimen_part:
            g.add((subj, EB_PROP.specimenPart, safe_literal(row.specimen_part)))

    save_graph(g, "mode_lookups.ttl")


def generate_formulation(conn):
    print("formulation.ttl is being generated...")
    g = new_graph()
    BATCH = 10000
    offset = 0
    total = conn.execute(text("SELECT COUNT(*) FROM formulation")).scalar()

    while offset < total:
        rows = conn.execute(text(f"""
            SELECT f.id, f.formulation_description, f.recipe_description,
                   f.dosage_description, f.usage_description,
                   f.adverse_effect_description,
                   mop.method AS prep_method,
                   r.title AS ref_title, f.reference_id, f.mode_of_preparation_id
            FROM formulation f
            LEFT JOIN mode_of_preparation mop ON f.mode_of_preparation_id = mop.id
            LEFT JOIN reference r ON f.reference_id = r.id
            LIMIT {BATCH} OFFSET {offset}
        """))
        batch_rows = rows.fetchall()
        if not batch_rows:
            break
        for row in batch_rows:
            subj = ETHNOBOT[f"formulation_{row.id}"]
            g.add((subj, RDF.type, EB_CLASS.Formulation))
            if row.formulation_description:
                g.add((subj, EB_PROP.formulationDescription, safe_literal(row.formulation_description)))
            if row.recipe_description:
                g.add((subj, EB_PROP.recipeDescription, safe_literal(row.recipe_description)))
            if row.dosage_description:
                g.add((subj, EB_PROP.dosageDescription, safe_literal(row.dosage_description)))
            if row.usage_description:
                g.add((subj, EB_PROP.usageDescription, safe_literal(row.usage_description)))
            if row.adverse_effect_description:
                g.add((subj, EB_PROP.adverseEffectDescription, safe_literal(row.adverse_effect_description)))
            if row.prep_method:
                g.add((subj, EB_PROP.preparationMethod, safe_literal(row.prep_method)))
            if row.reference_id:
                g.add((subj, EB_PROP.hasReference, ETHNOBOT[f"reference_{row.reference_id}"]))

            # Mode of administration ilişkileri
            moa_rows = conn.execute(text(f"""
                SELECT moa.mode FROM formulation_mode_of_administration_association fma
                JOIN mode_of_administration moa ON fma.mode_of_administration_id = moa.id
                WHERE fma.formulation_id = {row.id}
            """))
            for moa in moa_rows:
                if moa.mode:
                    g.add((subj, EB_PROP.administrationMode, safe_literal(moa.mode)))

        offset += BATCH
        print(f"  formulation: {min(offset, total)}/{total}", end="\r")

    print()
    save_graph(g, "formulation.ttl")


def generate_plant_specimen(conn):
    print("plant_specimen.ttl is being generated...")
    g = new_graph()
    BATCH = 10000
    offset = 0
    total = conn.execute(text("SELECT COUNT(*) FROM plant_specimen")).scalar()

    while offset < total:
        rows = conn.execute(text(f"""
            SELECT ps.id, ps.voucher_codes, ps.herbarium_codes,
                   ps.species_id, ps.formulation_id, ps.region_id,
                   ei.local_species_name, ei.local_language, ei.ethnic_group,
                   ebi.use_reports, ebi.use_value, ebi.fidelity_level
            FROM plant_specimen ps
            LEFT JOIN ethnic_info ei ON ei.plant_specimen_id = ps.id
            LEFT JOIN eb_index ebi ON ebi.plant_specimen_id = ps.id
            LIMIT {BATCH} OFFSET {offset}
        """))
        batch_rows = rows.fetchall()
        if not batch_rows:
            break
        for row in batch_rows:
            subj = ETHNOBOT[f"plant_specimen_{row.id}"]
            g.add((subj, RDF.type, EB_CLASS.PlantSpecimen))
            if row.voucher_codes:
                g.add((subj, EB_PROP.voucherCodes, safe_literal(row.voucher_codes)))
            if row.herbarium_codes:
                g.add((subj, EB_PROP.herbariumCodes, safe_literal(row.herbarium_codes)))
            if row.species_id:
                g.add((subj, EB_PROP.hasSpecies, ETHNOBOT[f"species_{row.species_id}"]))
            if row.formulation_id:
                g.add((subj, EB_PROP.hasFormulation, ETHNOBOT[f"formulation_{row.formulation_id}"]))
            if row.region_id:
                g.add((subj, EB_PROP.hasRegion, ETHNOBOT[f"region_{row.region_id}"]))
            if row.local_species_name:
                g.add((subj, EB_PROP.localSpeciesName, safe_literal(row.local_species_name)))
            if row.local_language:
                g.add((subj, EB_PROP.localLanguage, safe_literal(row.local_language)))
            if row.ethnic_group:
                g.add((subj, EB_PROP.ethnicGroup, safe_literal(row.ethnic_group)))
            if row.use_reports is not None:
                g.add((subj, EB_PROP.useReports, Literal(float(row.use_reports), datatype=XSD.double)))
            if row.use_value is not None:
                g.add((subj, EB_PROP.useValue, Literal(float(row.use_value), datatype=XSD.double)))
            if row.fidelity_level is not None:
                g.add((subj, EB_PROP.fidelityLevel, Literal(float(row.fidelity_level), datatype=XSD.double)))

            # Kullanılan bitki parçaları
            part_rows = conn.execute(text(f"""
                SELECT sp.specimen_part FROM plant_specimen_specimen_part_association psa
                JOIN specimen_part sp ON psa.specimen_part_id = sp.id
                WHERE psa.plant_specimen_id = {row.id}
            """))
            for part in part_rows:
                if part.specimen_part:
                    g.add((subj, EB_PROP.specimenPart, safe_literal(part.specimen_part)))

        offset += BATCH
        print(f"  plant_specimen: {min(offset, total)}/{total}", end="\r")

    print()
    save_graph(g, "plant_specimen.ttl")


def main():
    print("=== SQLite -> Turtle Generator ===")
    print(f"Output directory: {OUTPUT_DIR}/\n")

    engine = create_engine(SQLITE_URL)

    with engine.connect() as conn:
        generate_species(conn)
        generate_region(conn)
        generate_reference(conn)
        generate_traditional_usage(conn)
        generate_mode_lookups(conn)
        generate_formulation(conn)
        generate_plant_specimen(conn)

    print("\n=== All TTL files have been generated! ===")
    print(f"Files are in the {OUTPUT_DIR}/ directory")


if __name__ == "__main__":
    main()
