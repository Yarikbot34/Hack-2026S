from collections import Counter
from django.db import connection
from sentence_transformers import SentenceTransformer
import spacy
import os

# здесь бизнес логика

model = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')
nlp = spacy.load("ru_core_news_sm")
API = os.environ.get('OPEN_ROUTER_KEY')


def generate_embedding(text: str) -> list[float]: # Превращает текст статьи в набор чисел (вектор). Это делает модель ИИ
    clean_text = text.strip()
    embedding = model.encode(clean_text)
    return embedding.tolist()



def extract_keywords(text: str, max_keywords: int = 6):
    doc = nlp(text)
    keywords = []
    for token in doc.ents:
        if  token.label_ in ['PER', 'ORG', 'LOC']:
            keywords.append(token.lemma_)

    keyword_counts = Counter(keywords)
    result = [word for word, count in keyword_counts.most_common(max_keywords)]
    return result


def search_similar_articles(query_embedding, limit=5): # Ищет в базе статьи, похожие на запрос
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, title, url, (embedding <=> %s) as similarity
            FROM database_article
            WHERE embedding IS NOT NULL
            ORDER BY similarity
            LIMIT %s
        """, [query_embedding, limit])
        return cursor.fetchall()



print(API)