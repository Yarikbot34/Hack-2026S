from .models import Article, NewsSource, ProcessingLog
from .services import generate_embedding
import feedparser
from django.utils import timezone

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
                    article.save()

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

def process_article_nlp(article_id):
    try:
        article = Article.objects.get(id=article_id)
        text = f"{article.title} {article.content}"
        article.embedding = generate_embedding(text)
        article.is_processed = True
        article.save()
    except Exception as e:
        ProcessingLog.objects.create(task_name='process_article_nlp', status='FAILED', message=str(e))



