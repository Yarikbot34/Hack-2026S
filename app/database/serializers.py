from rest_framework import serializers
from .models import Article, NewsSource

# База данных хранит объекты Python, а браузер понимает только JSON (текст).
# Превращает объект в JSON и обратно.

class NewsSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsSource
        fields = '__all__'

class ArticleSerializer(serializers.ModelSerializer): # Решает, какие поля статьи показать пользователю
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'url', 'published_at', 'source_name', 'cluster_id', 'is_processed']
