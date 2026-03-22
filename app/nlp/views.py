from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from database.serializers import ArticleSerializer, NewsSourceSerializer
from database.services import extract_keywords
from database.tasks import fetch_news_sources, process_article_nlp
from database.models import Article
from database.neo4j_client import neo4j_conn
from .AI import graph_ranker

# Create your views here.


@api_view(['GET'])
def GetArticle(request):
    articles = Article.objects.filter().order_by('-published_at')[:50]
    articles = articles[:3]
    for i in articles:
        process_article_nlp(i.id)
    serializer_data = ArticleSerializer(articles, many=True).data
    transformed_data = []
    for article in serializer_data:
        transformed_data.append({
            **article,
            'text': article.get('content', ''),
            'publication_date': article.get('published_at', '')
        })

    return Response(transformed_data)


@api_view(['GET'])
def GetGraph(request):

    records = neo4j_conn.get_first_keyword_with_neighbors()
    graph_data = neo4j_conn.format_graph_data(records)
    print(graph_data)
    return Response(graph_data)


@api_view(['GET'])
def NewsRelated(request):
    entity = request.query_params.get('entity')
    limit = int(request.query_params.get('limit', 10))

    if not entity:
        return Response({
            "error": "Parameter 'entity' is required",
            "news": []
        }, status=400)

    entity = entity.strip()

    # Ищем статьи по ключевому слову в поле keywords
    articles = Article.objects.filter(
        keywords__icontains=entity
    ).order_by('-published_at')[:limit]

    # Сериализуем статьи
    serializer = ArticleSerializer(articles, many=True)

    news_data = []
    for article in serializer.data:
        news_data.append({
            **article,
            'text': article.get('content', ''),  # ✅ Добавляем text
            'publication_date': article.get('published_at', '')  # ✅ Добавляем publication_date
        })

    return Response({
        "answer": f"Найдено {len(news_data)} статей по запросу '{entity}'",
        "keyword": entity,
        "count": len(news_data),
        "news": news_data  # ✅ Возвращаем массив
    })

@api_view(['GET', 'POST'])
def search(request):
    if request.method == 'POST':
        query = request.data.get('query')
        if not query:
            return Response({
                "answer": "Пустой запрос.'",
                "graph": {"nodes": [], "links": []}
            }, status=400)
        keywords = extract_keywords(query, 3)
        if not keywords:
            return Response({
                "answer": f"Не удалось извлечь ключевые слова из запроса: {query}",
                "graph": {"nodes": [], "links": []}
            })
        try:
            graph_data = neo4j_conn.get_graph_by_keywords(keywords)
        except Exception as e:
            print(f"⚠️ Ошибка при получении графа: {e}")
            import traceback
            traceback.print_exc()
            graph_data = {"nodes": [], "links": []}

        ranked_nodes = graph_ranker.rank_nodes_with_llm(query, graph_data['nodes'], 5)
        relevant_ids = {node['id'] for node in ranked_nodes}
        filtered_links = [
            link for link in graph_data['links']
            if link.get('source') in relevant_ids and link.get('target') in relevant_ids
        ]

        return Response({
            "query": query,
            "answer": f"Найдено {len(ranked_nodes)} релевантных узлов",
            "graph": {
                "nodes": ranked_nodes,
                "links": filtered_links
            }
        })
