from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Article, NewsSource
from .serializers import ArticleSerializer, NewsSourceSerializer
from .services import search_similar_articles, generate_embedding

# Принимает запросы от сайта и отдает ответы.
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer

    @action(detail=False, methods=['get'])
    def semantic_search(self, request):
        query = request.query_params.get('q')
        if not query:
            return Response({"error": "No query provided"}, status=400)
        query_vec = generate_embedding(query)
        results = search_similar_articles(query_vec)
        return Response({'results': results})

class NewsSourceViewSet(viewsets.ModelViewSet):
    queryset = NewsSource.objects.all()
    serializer_class = NewsSourceSerializer
