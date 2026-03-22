from neo4j import GraphDatabase
import os


class Neo4jConnection: # подкючается к базе графов
    def __init__(self):
        self.uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.environ.get("NEO4J_USER", "neo4j")
        self.password = os.environ.get("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None): # отправляет команды на языке Cypher
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def get_graph_by_keywords(self, keywords, limit_nodes=100, limit_links=200):
        """
        Получает узлы по ключевым словам и ВСЕ их соседние связи
        """
        if not keywords:
            return {"nodes": [], "links": []}

        all_nodes = []
        all_links = []
        seen_nodes = set()

        # Выполняем запрос для каждого ключевого слова
        for keyword in keywords:
            try:
                # Запрос находит узлы, содержащие ключевое слово
                query = """
                MATCH (n)
                WHERE 
                    n.name CONTAINS $keyword OR 
                    n.title CONTAINS $keyword OR
                    toString(n.id) CONTAINS $keyword
                WITH n
                OPTIONAL MATCH (n)-[r]-(neighbor)
                RETURN n, r, neighbor
                LIMIT $limit
                """

                results = self.execute_query(query, {'keyword': keyword, 'limit': limit_nodes})

                # Проверяем что results - это список
                if not isinstance(results, list):
                    print(f"⚠️ Warning: results is {type(results)}, expected list")
                    continue

                for record in results:
                    # Проверяем что record - это словарь
                    if not isinstance(record, dict):
                        print(f"⚠️ Warning: record is {type(record)}, expected dict")
                        continue

                    source = record.get('n', {})
                    target = record.get('neighbor', {})
                    rel = record.get('r', {})

                    # Добавляем исходный узел
                    if source and isinstance(source, dict):
                        node_id = self._get_node_id(source)
                        if node_id and node_id not in seen_nodes:
                            all_nodes.append({
                                "id": node_id,
                                "name": source.get('name') or source.get('title') or node_id,
                                "type": self._get_node_type(source)
                            })
                            seen_nodes.add(node_id)

                    # Добавляем целевой узел
                    if target and isinstance(target, dict):
                        node_id = self._get_node_id(target)
                        if node_id and node_id not in seen_nodes:
                            all_nodes.append({
                                "id": node_id,
                                "name": target.get('name') or target.get('title') or node_id,
                                "type": self._get_node_type(target)
                            })
                            seen_nodes.add(node_id)

                    # Добавляем связь
                    if source and target and rel:
                        source_id = self._get_node_id(source) if isinstance(source, dict) else None
                        target_id = self._get_node_id(target) if isinstance(target, dict) else None

                        if source_id and target_id:
                            all_links.append({
                                "source": source_id,
                                "target": target_id,
                                "relation": self._get_rel_type(rel) if isinstance(rel, dict) else "related",
                                "weight": rel.get('weight', 1) if isinstance(rel, dict) and rel else 1
                            })

            except Exception as e:
                print(f"⚠️ Ошибка при поиске графа для '{keyword}': {e}")
                import traceback
                traceback.print_exc()
                continue

        # Ограничиваем количество результатов
        return {
            "nodes": all_nodes[:limit_nodes],
            "links": all_links[:limit_links]
        }

    def _get_node_id(self, node):
        """Извлекает ID узла"""
        if not node or not isinstance(node, dict):
            return None

        # Пробуем разные возможные поля для ID
        node_id = node.get('id') or node.get('name') or node.get('url')
        if node_id is not None:
            return str(node_id)
        return None

    def _get_node_type(self, node):
        """Определяет тип узла"""
        if not node or not isinstance(node, dict):
            return "unknown"

        # Проверяем метки узла
        labels = node.get('_labels', [])
        if labels:
            if isinstance(labels, list):
                return labels[0] if labels else "node"
            return str(labels)

        # Определяем тип по наличию полей
        if 'title' in node and 'url' in node:
            return "article"
        elif 'name' in node:
            return "entity"

        return "node"

    def _get_rel_type(self, rel):
        """Получает тип связи"""
        if not rel or not isinstance(rel, dict):
            return "related"

        rel_type = rel.get('_type') or rel.get('type') or rel.get('relation')
        return str(rel_type) if rel_type else "related"

    def get_articles_for_keywords(self, keywords, limit=10):
        """
        Возвращает статьи и их полный текст для ключевых слов
        """
        query = """
        MATCH (k:Keyword)
        WHERE k.name IN $keywords
        WITH collect(DISTINCT k) as keyword_nodes

        MATCH (a:Article)-[:HAS_KEYWORD]->(k:Keyword)
        WHERE k IN keyword_nodes
        RETURN 
            a.id as id,
            a.title as title,
            a.content as content,
            a.url as url,
            a.published_at as published_at
        ORDER BY a.published_at DESC
        LIMIT $limit
        """

        return self.execute_query(query, {
            'keywords': keywords,
            'limit': limit
        })


    def search_by_keyword(self, keyword, limit=20):
        """
        Упрощенный поиск по одному ключевому слову
        """
        query = """
        MATCH (k:Keyword {name: $keyword})<-[:HAS_KEYWORD]-(a:Article)
        OPTIONAL MATCH (a)-[:MENTIONS_PERSON]->(p:Person)
        OPTIONAL MATCH (a)-[:MENTIONS_ORG]->(o:Organization)
        RETURN 
            a.id as article_id,
            a.title as title,
            collect(DISTINCT p.name) as persons,
            collect(DISTINCT o.name) as organizations
        LIMIT $limit
        """
        return self.execute_query(query, {'keyword': keyword, 'limit': limit})

    def create_entities(self, article_id, entities):
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

    def format_graph_data(self, records):
        nodes = []
        links = []
        node_ids = set()

        for record in records:
            k = record.get('k', {})
            neighbor = record.get('neighbor', {})
            r = record.get('r', {})

            # Извлекаем тип связи правильно
            relation_type = 'RELATED_TO'
            if r:
                if isinstance(r, dict):
                    relation_type = r.get('_type', 'RELATED_TO')
                elif hasattr(r, 'type'):
                    relation_type = r.type()

            # Добавляем центральный узел
            if k and 'name' in k:
                node_id = f"keyword_{k['name']}"
                if node_id not in node_ids:
                    nodes.append({
                        'id': node_id,
                        'name': k['name'],
                        'type': 'Keyword',
                        'usage_count': k.get('usage_count', 1),
                        'is_center': True
                    })
                    node_ids.add(node_id)

            # Добавляем соседний узел
            if neighbor and 'name' in neighbor:
                node_id = f"keyword_{neighbor['name']}"
                if node_id not in node_ids:
                    # Определяем тип узла
                    node_type = 'Keyword'
                    if isinstance(neighbor, dict):
                        labels = neighbor.get('_labels', neighbor.get('_label', []))
                        if isinstance(labels, list):
                            node_type = labels[0] if labels else 'Keyword'
                        else:
                            node_type = labels if labels else 'Keyword'

                    nodes.append({
                        'id': node_id,
                        'name': neighbor['name'],
                        'type': node_type,
                        'usage_count': neighbor.get('usage_count', 1),
                        'is_center': False
                    })
                    node_ids.add(node_id)

                # Добавляем связь
                if k and 'name' in k and neighbor and 'name' in neighbor:
                    # Извлекаем вес связи
                    weight = 1
                    if isinstance(r, dict):
                        weight = r.get('weight', 1)

                    links.append({
                        'source': f"keyword_{k['name']}",
                        'target': f"keyword_{neighbor['name']}",
                        'relation': relation_type,
                        'weight': weight
                    })

        return {'nodes': nodes, 'links': links}

    def search_person_connections(self, person_name):
        query = """
        MATCH (p:Person {name: $name})-[r]-(connected)
        RETURN p, r, connected
        """
        return self.execute_query(query, {'name': person_name})

    def create_keywords_for_article(self, article_id: int, text: str, max_keywords: int = 6):
        from database.services import extract_keywords
        keywords = extract_keywords(text, max_keywords)

        if not keywords:
            return []

        # 2. Создаем узлы ключевых слов в БД
        for keyword in keywords:
            query = """
            MERGE (k:Keyword {name: $name})
            SET k.usage_count = coalesce(k.usage_count, 0) + 1
            RETURN k
            """
            self.execute_query(query, {'name': keyword})

        # 3. Связываем статью с ключевыми словами
        for keyword in keywords:
            query = """
            MATCH (a:Article {id: $article_id})
            MATCH (k:Keyword {name: $keyword})
            MERGE (a)-[:HAS_KEYWORD]->(k)
            """
            self.execute_query(query, {'article_id': article_id, 'keyword': keyword})

        # 4. Создаем связи между ВСЕМИ ключевыми словами статьи (полный граф)
        for i in range(len(keywords)):
            for j in range(i + 1, len(keywords)):
                query = """
                MATCH (k1:Keyword {name: $word1})
                MATCH (k2:Keyword {name: $word2})
                MERGE (k1)-[r:RELATED_TO]-(k2)
                SET r.weight = coalesce(r.weight, 0) + 1
                """
                self.execute_query(query, {'word1': keywords[i], 'word2': keywords[j]})

        return keywords

neo4j_conn = Neo4jConnection()
