from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (IngredientViewSet, RecipesViewSet, ShortLinkView,
                    TagViewSet, UserViewSet)

router_v1 = SimpleRouter()
router_v1.register('users', UserViewSet, basename='users')
router_v1.register('recipes', RecipesViewSet, basename='recipes')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('ingredients', IngredientViewSet, basename='ingridients')


urlpatterns = [

    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('s/<str:encoded_id>/', ShortLinkView.as_view(), name='shortlink'),

]
