import logging
from venv import logger

from biokb_brenda.db.manager import DbManager as BrendaDbManager
from biokb_brenda.rdf.neo4j_importer import Neo4jImporter as BrendaNeo4jImporter
from biokb_brenda.rdf.turtle import TurtleCreator as BrendaTurtleCreator
from biokb_chebi.db.manager import DbManager as ChebiDbManager
from biokb_chebi.rdf.neo4j_importer import Neo4jImporter as ChebiNeo4jImporter
from biokb_chebi.rdf.turtle import TurtleCreator as ChebiTurtleCreator
from biokb_coconut.db.manager import DbManager as CoconutDbManager
from biokb_coconut.rdf.neo4j_importer import Neo4jImporter as CoconutNeo4jImporter
from biokb_coconut.rdf.turtle import TurtleCreator as CoconutTurtleCreator
from biokb_ipni.db.manager import DbManager as IpniDbManager
from biokb_ipni.rdf.neo4j_importer import Neo4jImporter as IpniNeo4jImporter
from biokb_ipni.rdf.turtle import TurtleCreator as IpniTurtleCreator
from biokb_taxtree.db.manager import DbManager as TaxtreeDbManager
from biokb_taxtree.rdf.neo4j_importer import Neo4jImporter as TaxtreeNeo4jImporter
from biokb_taxtree.rdf.turtle import TurtleCreator as TaxtreeTurtleCreator
from biokb_wfo.db.manager import DbManager as WfoDbManager
from biokb_wfo.rdf.neo4j_importer import Neo4jImporter as WfoNeo4jImporter
from biokb_wfo.rdf.turtle import TurtleCreator as WfoTurtleCreator
from biokb_wcvp.db.manager import DbManager as wcvpDbManager
from biokb_wcvp.rdf.neo4j_importer import Neo4jImporter as wcvpNeo4jImporter
from biokb_wcvp.rdf.turtle import TurtleCreator as wcvpTurtleCreator
from sqlalchemy import Engine

logger = logging.getLogger(__name__)


class DbManager:
    def __init__(self, engine: Engine):
        self.engine = engine

    def import_biokb_dbs(self):
        logger.info("Importing BioKB databases...")
        self.import_brenda_db()
        self.import_chebi_db()
        self.import_coconut_db()
        self.import_ipni_db()
        self.import_taxtree_db()
        self.import_wfo_db()
        self.import_wcvp_db()
        logger.info("BioKB database import completed.")

    def import_brenda_db(self):
        BrendaDbManager(self.engine).import_data()

    def import_chebi_db(self):
        ChebiDbManager(self.engine).import_data()

    def import_coconut_db(self):
        CoconutDbManager(self.engine).import_data()

    def import_ipni_db(self):
        IpniDbManager(self.engine).import_data()

    def import_taxtree_db(self):
        TaxtreeDbManager(self.engine).import_data()

    def import_wfo_db(self):
        WfoDbManager(self.engine).import_data()

    def import_wcvp_db(self):
        wcvpDbManager(self.engine).import_data()

    def create_turtle_files(self):
        logger.info("Creating Turtle files...")
        self.create_brenda_turtle_files()
        self.create_chebi_turtle_files()
        self.create_coconut_turtle_files()
        self.create_ipni_turtle_files()
        self.create_taxtree_turtle_files()
        self.create_wfo_turtle_files()
        self.create_wcvp_turtle_files()
        logger.info("Turtle file creation completed.")

    def create_brenda_turtle_files(self):
        BrendaTurtleCreator(self.engine).create_ttls()

    def create_chebi_turtle_files(self):
        ChebiTurtleCreator(self.engine).create_ttls()

    def create_coconut_turtle_files(self):
        CoconutTurtleCreator(self.engine).create_ttls()

    def create_ipni_turtle_files(self):
        IpniTurtleCreator(self.engine).create_ttls()

    def create_taxtree_turtle_files(self):
        TaxtreeTurtleCreator(self.engine).create_ttls()

    def create_wfo_turtle_files(self):
        WfoTurtleCreator(self.engine).create_ttls()

    def create_wcvp_turtle_files(self):
        wcvpTurtleCreator(self.engine).create_ttls()

    def import_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        logger.info("Importing data into Neo4j...")
        self.import_brenda_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        self.import_chebi_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        self.import_coconut_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        self.import_ipni_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        self.import_taxtree_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        self.import_wfo_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        self.import_wcvp_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        logger.info("Neo4j import completed.")

    def import_brenda_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        BrendaNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()

    def import_chebi_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        ChebiNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()

    def import_coconut_neo4j(
        self, neo4j_uri: str, neo4j_user: str, neo4j_password: str
    ):
        CoconutNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()

    def import_ipni_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        IpniNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()

    def import_taxtree_neo4j(
        self, neo4j_uri: str, neo4j_user: str, neo4j_password: str
    ):
        TaxtreeNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()

    def import_wfo_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        WfoNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()
    
    def import_wcvp_neo4j(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        wcvpNeo4jImporter(neo4j_uri, neo4j_user, neo4j_password).import_ttls()
