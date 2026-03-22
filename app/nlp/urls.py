from django.urls import path, include
from . import views

urlpatterns = [
    path('api/news', views.GetArticle),
    path('api/graph', views.GetGraph),
    path('api/news/related', views.NewsRelated),
    path('api/search', views.search)
]
