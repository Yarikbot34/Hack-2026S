from neo4j import GraphDatabase
import os

# файл переводчик для работы с neo4j

class Neo4jConnection: # подкючается к базе графов
    def __init__(self):
        self.uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.environ.get("NEO4J_USER", "neo4j")
        self.password = os.environ.get("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None): # отправляет команды на языке Cypher (аналог SQL для графов)
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def create_article_node(self, article_id, title, url):
        query = """
        MERGE (a:Article {id: $article_id, url: $url})
        SET a.title = $title, a.created_at = datetime()
        RETURN a
        """
        return self.execute_query(query, {
            'article_id': article_id,
            'title': title,
            'url': url
        })

    def create_entities(self, article_id, entities):
        """
        entities = {
            'persons': ['Илон Маск', 'Путин'],
            'locations': ['Москва', 'США'],
            'organizations': ['SpaceX', 'Кремль']
        }
        """
        queries = []

        for person in entities.get('persons', []):
            query = """
            MATCH (a:Article {id: $article_id})
            MERGE (p:Person {name: $name})
            MERGE (a)-[:MENTIONS_PERSON]->(p)
            """
            self.execute_query(query, {'article_id': article_id, 'name': person})

        for location in entities.get('locations', []):
            query = """
            MATCH (a:Article {id: $article_id})
            MERGE (l:Location {name: $name})
            MERGE (a)-[:MENTIONS_LOCATION]->(l)
            """
            self.execute_query(query, {'article_id': article_id, 'name': location})

        for org in entities.get('organizations', []):
            query = """
            MATCH (a:Article {id: $article_id})
            MERGE (o:Organization {name: $name})
            MERGE (a)-[:MENTIONS_ORG]->(o)
            """
            self.execute_query(query, {'article_id': article_id, 'name': org})

    def get_graph_data(self, limit=200):
        query = """
        MATCH (n)-[r]-(m)
        RETURN n, r, m
        LIMIT $limit
        """
        return self.execute_query(query, {'limit': limit})

    def search_person_connections(self, person_name):
        query = """
        MATCH (p:Person {name: $name})-[r]-(connected)
        RETURN p, r, connected
        """
        return self.execute_query(query, {'name': person_name})

neo4j_conn = Neo4jConnection()
