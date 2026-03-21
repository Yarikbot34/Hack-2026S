from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from database.serializers import ArticleSerializer, NewsSourceSerializer
from database.tasks import fetch_news_sources
from database.models import Article

# Create your views here.


@api_view(['GET'])
def GetArticle(request):
    fetch_news_sources()
    articles = Article.objects.filter().order_by('-published_at')[:50]
    articles = articles[:3]
    return Response(ArticleSerializer(articles, many=True).data)


