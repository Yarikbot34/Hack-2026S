import threading
from django.apps import AppConfig
import time



class DatabaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'database'

    def ready(self):
        # Запускаем фоновый поток
        thread = threading.Thread(target=self._run_periodic_task, daemon=True)
        thread.start()

    def _run_periodic_task(self):
        from database.tasks import fetch_news_sources
        while True:
            try:
                print("Запуск задачи парсинга...")
                fetch_news_sources()
                print("Задача завершена")
            except Exception as e:
                print(f"Ошибка: {e}")

            from .models import Article
            articles = Article.objects.filter(is_processed=True)

            for article in articles:
                try:
                    from database.neo4j_client import neo4j_conn
                    text = f"{article.title} {article.content}"

                    # Создаем ключевые слова в Neo4j
                    keywords = neo4j_conn.create_keywords_for_article(
                        article_id=article.id,
                        text=text,
                        max_keywords=5
                    )

                    # Сохраняем в статью
                    if keywords:
                        article.keywords = ', '.join(keywords)
                        article.is_processed = False
                        article.save(update_fields=['keywords'])

                except Exception as e:
                    print(f"Ошибка статьи {article.id}: {e}")
                    continue

            time.sleep(60)


