from django.contrib import admin
from .models import Article, NewsSource, ProcessingLog

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'published_at', 'is_processed', 'cluster_id']
    list_filter = ['is_processed', 'source']

@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'is_active']

@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'status', 'created_at']
