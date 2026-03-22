import os
import requests
from typing import List, Dict
import json
from openai import OpenAI


class GraphRanker:

    def __init__(self, model_name: str = "qwen/qwen3-next-80b-a3b-instruct:free"):
        # OpenRouter конфигурация
        self.api_key = "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"
        self.api_url = "https://openrouter.ai/api/v1"
        self.model_name = model_name

        # Заголовки для запросов
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # Ваш сайт
            "X-Title": "News Aggregator"  # Название приложения
        }

        # Локальные эмбеддинги (бесплатно, не требует API)
        try:
            from sentence_transformers import SentenceTransformer
            self.embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("Локальная модель эмбеддингов загружена")
        except Exception as e:
            print(f"Не удалось загрузить локальную модель: {e}")
            self.embed_model = None

    def calculate_similarity(self, query: str, texts: List[str]) -> List[float]:
        """
        Вычисляет косинусное сходство между запросом и текстами
        Использует локальные эмбеддинги (бесплатно)
        """
        if self.embed_model is None:
            # Fallback: простое текстовое сходство
            return self._text_similarity(query, texts)

        # Генерируем эмбеддинги
        query_embedding = self.embed_model.encode(query)
        text_embeddings = self.embed_model.encode(texts)

        # Вычисляем косинусное сходство
        similarities = []
        for text_emb in text_embeddings:
            similarity = self._cosine_similarity(query_embedding, text_emb)
            similarities.append(float(similarity))

        return similarities

    def _text_similarity(self, query: str, texts: List[str]) -> List[float]:
        """Простое текстовое сходство (если нет эмбеддингов)"""
        query_lower = query.lower()
        similarities = []

        for text in texts:
            text_lower = text.lower()
            # Простое совпадение слов
            query_words = set(query_lower.split())
            text_words = set(text_lower.split())

            if len(query_words) == 0:
                similarities.append(0.0)
                continue

            overlap = len(query_words & text_words)
            similarity = overlap / len(query_words)
            similarities.append(similarity)

        return similarities

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Вычисляет косинусное сходство между двумя векторами"""
        import numpy as np
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def rank_nodes_by_embedding(self, query: str, nodes: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Ранжирует узлы по семантическому сходству с запросом
        """
        if not nodes:
            return []

        # Создаем текст для каждого узла
        node_texts = []
        for node in nodes:
            text = f"{node.get('name', '')} {node.get('type', '')}"
            node_texts.append(text)

        # Вычисляем сходство
        similarities = self.calculate_similarity(query, node_texts)

        # Добавляем score к узлам
        for i, node in enumerate(nodes):
            node['relevance_score'] = similarities[i]

        # Сортируем по релевантности
        ranked_nodes = sorted(nodes, key=lambda x: x.get('relevance_score', 0), reverse=True)

        # Возвращаем топ-K
        return ranked_nodes[:top_k]

    def rank_nodes_with_llm(self, query: str, nodes: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Использует LLM через OpenRouter для оценки релевантности узлов
        """
        if not nodes:
            return []

        if not self.api_key:
            print("OpenRouter API key не найден, используем embedding ранжирование")
            return self.rank_nodes_by_embedding(query, nodes, top_k)

        # Формируем текст узлов (ограничиваем для экономии токенов)
        nodes_text = "\n".join([
            f"- ID: {node.get('id')}, Name: {node.get('name')}, Type: {node.get('type')}"
            for node in nodes[:50]
        ])

        # Промпт для LLM
        prompt = f"""Ты эксперт по анализу графов знаний. Оцени релевантность узлов графа для поискового запроса.

Запрос: {query}

Узлы графа:
{nodes_text}

Оцени каждый узел по шкале от 0 до 1 (где 1 = максимально релевантен).
Верни ТОЛЬКО JSON в формате:
{{
    "ranked_nodes": [
        {{"node_id": "id узла", "score": 0.95, "reason": "почему релевантен"}},
        ...
    ]
}}

Никакого дополнительного текста, только JSON."""

        try:
            # Запрос к OpenRouter API
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "Ты помощник для анализа графов. Возвращай только JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0,
                    "max_tokens": 2000
                }
            )

            response.raise_for_status()
            result = response.json()

            # Парсим ответ LLM
            content = result['choices'][0]['message']['content']

            # Извлекаем JSON из ответа
            try:
                llm_result = json.loads(content)
            except json.JSONDecodeError:
                # Пытаемся найти JSON в тексте
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    llm_result = json.loads(json_match.group())
                else:
                    raise ValueError("Не удалось извлечь JSON из ответа LLM")

            # Добавляем scores к узлам
            scored_nodes = []
            for node in nodes:
                node_id = node.get('id')
                for ranked in llm_result.get('ranked_nodes', []):
                    if ranked.get('node_id') == node_id:
                        node['relevance_score'] = ranked.get('score', 0)
                        node['reason'] = ranked.get('reason', '')
                        scored_nodes.append(node)
                        break

            # Сортируем
            scored_nodes = sorted(scored_nodes, key=lambda x: x.get('relevance_score', 0), reverse=True)

            return scored_nodes[:top_k]

        except Exception as e:
            print(f"Ошибка LLM ранжирования через OpenRouter: {e}")
            # Fallback на embedding ранжирование
            return self.rank_nodes_by_embedding(query, nodes, top_k)

    def filter_and_rank_graph(self, query: str, graph_data: Dict, top_k: int = 10) -> Dict:
        """
        Полный пайплайн: фильтрация + ранжирование графа
        """
        nodes = graph_data.get('nodes', [])
        links = graph_data.get('links', [])

        if not nodes:
            return {"nodes": [], "links": []}

        # Ранжируем узлы
        ranked_nodes = self.rank_nodes_by_embedding(query, nodes, top_k=top_k)

        # Получаем ID релевантных узлов
        relevant_ids = {node['id'] for node in ranked_nodes}

        # Фильтруем связи (оставляем только между релевантными узлами)
        filtered_links = [
            link for link in links
            if link.get('source') in relevant_ids and link.get('target') in relevant_ids
        ]

        return {
            "nodes": ranked_nodes,
            "links": filtered_links,
            "query": query,
            "total_nodes": len(ranked_nodes),
            "total_links": len(filtered_links)
        }

    def get_available_models(self) -> List[Dict]:
        """
        Получает список доступных моделей из OpenRouter
        """
        if not self.api_key:
            return []

        try:
            response = requests.get(
                f"{self.api_url}/models",
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            return result.get('data', [])
        except Exception as e:
            print(f"⚠️ Ошибка получения списка моделей: {e}")
            return []


# Инициализация
graph_ranker = GraphRanker()