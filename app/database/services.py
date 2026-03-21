from django.db import connection
from sentence_transformers import SentenceTransformer
import spacy

# здесь бизнес логика

model = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')
nlp = spacy.load("ru_core_news_sm")


def generate_embedding(text: str) -> list[float]: # Превращает текст статьи в набор чисел (вектор). Это делает модель ИИ
    clean_text = text.strip()
    embedding = model.encode(clean_text)
    return embedding.tolist()

def extract_entities(text: str) -> dict:
    doc = nlp(text)
    persons = set()
    locations = set()
    organizations = set()

    for ent in doc.ents:
        if ent.label_ == "PER":
            persons.add(ent.lemma_)
        elif ent.label_ == "LOC":
            locations.add(ent.lemma_)
        elif ent.label_ == "ORG":
            organizations.add(ent.text)

    return {
        'persons': list(persons),
        'locations': list(locations),
        'organizations': list(organizations)
    }

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
