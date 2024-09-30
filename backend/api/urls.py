from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import (IngredientViewSet, TagViewSet, RecipeViewSet)
from users.views import (UserViewSet)


app_name = 'api'

router = DefaultRouter()

router.register('users', UserViewSet, basename='users')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path('recipe/<slug:slug>/',
         RecipeViewSet.as_view({'get': 'retrieve_by_slug'}),
         name='recipe-detail-by-slug'),
]
