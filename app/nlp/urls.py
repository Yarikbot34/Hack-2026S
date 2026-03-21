from django.urls import path, include
from . import views

urlpatterns = [
    path('api/news', views.GetArticle),
    path('api/graph', views.GetArticle),
]
