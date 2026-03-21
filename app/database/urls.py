from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, NewsSourceViewSet

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'sources', NewsSourceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
