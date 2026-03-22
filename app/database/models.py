from django.db import models
from pgvector.django import VectorField

# Здесь ты описываешь, какие данные будут храниться в PostgreSQL. Django сам создаст таблицы на основе этого кода.
class NewsSource(models.Model): # откуда берёт новости
    TYPE_CHOICES = [
        ('rss', 'RSS Feed'),
        ('api', 'News API')
    ]
    name = models.CharField(max_length=255)
    url = models.URLField()
    source_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_article_url = models.URLField(null=True, blank=True, max_length=2000)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.name

class Article(models.Model): # сама новость
    id = models.BigAutoField(primary_key=True)
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE, related_name='articles')
    title = models.CharField(max_length=1000)
    content = models.TextField()
    url = models.URLField(unique=True)
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    embedding = VectorField(dimensions=384, null=True, blank=True)  # это вектор (набор чисел), который описывает смысл статьи. Оно нужно для поиска "по смыслу".
    cluster_id = models.IntegerField(null=True, blank=True, db_index=True) # Номер группы, к которой относится статья
    is_processed = models.BooleanField(default=True)
    keywords = models.CharField(max_length = 250) #Ключевые слова для выбора ИИ

    class Meta:
        indexes = [models.Index(fields=['published_at'])]

    def __str__(self):
        return self.title[:50]

class ProcessingLog(models.Model): # журнал ошибок и успехов
    task_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    message = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
