from sqlalchemy import create_engine
from plantgraph3.db.manager import DbManager


def main():
    engine = create_engine(
        "mysql+pymysql://group_project_user:group_project_password@localhost:3306/group_project_db"
    )

    dbm = DbManager(engine)

    # print("Importing BioKB databases...")
    # dbm.import_biokb_dbs()

    # print("Creating Turtle files...")
    # dbm.create_turtle_files()

    print("Importing into Neo4j...")
    dbm.import_neo4j(
        "bolt://localhost:7687",
        "neo4j",
        "neo4j_password",
    )

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()