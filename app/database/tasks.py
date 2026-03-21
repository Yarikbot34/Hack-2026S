from celery import shared_task
from .models import Article, NewsSource, ProcessingLog
from .services import generate_embedding, extract_entities
from .neo4j_client import neo4j_conn
import feedparser
import requests
from bs4 import BeautifulSoup
from django.utils import timezone

@shared_task
def fetch_news_sources(): # Запускается по расписанию. Залезает на RSS-ленты, забирает заголовки, создает записи в Article
    sources = NewsSource.objects.filter(is_active=True)
    for source in sources:
        try:
            if source.source_type == 'rss':
                feed = feedparser.parse(source.url)
                for entry in feed.entries:
                    if source.last_article_url == entry.link:
                        break

                    article = Article.objects.create(
                        source=source,
                        title=entry.title,
                        content=entry.summary if hasattr(entry, 'summary') else '',
                        url=entry.link,
                        published_at=timezone.now()
                    )

                    source.last_article_url = entry.link
                    source.last_checked_at = timezone.now()
                    source.save()

                    process_article_nlp.delay(article.id)

            ProcessingLog.objects.create(
                task_name='fetch_news_sources',
                status='SUCCESS',
                message=f'Processed {source.name}'
            )

        except Exception as e:
            ProcessingLog.objects.create(
                task_name='fetch_news_sources',
                status='FAILED',
                message=str(e)
            )

@shared_task
def process_article_nlp(article_id): #  Запускается для каждой новой статьи (Считает вектор (для поиска), Ищет сущности (кто упомянут?), Пишет в Neo4j (строит граф))
    try:
        article = Article.objects.get(id=article_id)

        text = f"{article.title} {article.content}"
        article.embedding = generate_embedding(text)

        entities = extract_entities(text)

        article.is_processed = True
        article.save()

        neo4j_conn.create_article_node(article.id, article.title, article.url)
        neo4j_conn.create_entities(article.id, entities)

        ProcessingLog.objects.create(
            task_name='process_article_nlp',
            status='SUCCESS',
            message=f'Article {article.id} processed'
        )

    except Exception as e:
        ProcessingLog.objects.create(
            task_name='process_article_nlp',
            status='FAILED',
            message=str(e)
        )

def update_neo4j_graph(article_id, title):
    query = """
    MERGE (a:Article {id: $article_id, title: $title})
    """
    neo4j_conn.execute_query(query, {'article_id': article_id, 'title': title})
