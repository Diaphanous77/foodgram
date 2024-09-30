from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers import (FavoriteSerializer, IngredientSerializer,
                             RecipeGetSerializer, RecipePostSerializer,
                             RecipeShortSerializer, ShoppingListSerializer,
                             TagSerializer)
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShopList, Tag)

from .filters import IngredientFilter, RecipeFilter
from .pagination import MyPagination
from .permissions import IsAuthorOrAdminOrReadOnly


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrAdminOrReadOnly, ]
    filter_backends = (DjangoFilterBackend,)
    filter_class = RecipeFilter
    pagination_class = MyPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        elif self.action in ['favorite', 'shopping_cart', ]:
            return RecipeShortSerializer
        if self.request.method == 'POST' or 'PATCH':
            return RecipePostSerializer

    @action(["POST", "DELETE"], detail=True)
    def favorite(self, request, pk=None):
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if self.request.method == "POST":
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = FavoriteSerializer(recipe,
                                            context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self.request.method == 'DELETE':
            favorite = get_object_or_404(
                Favorite, user=user, recipe=recipe
            )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(["POST", "DELETE"], detail=True)
    def shopping_cart(self, request, pk=None):
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if self.request.method == 'POST':
            ShopList.objects.create(user=user, recipe=recipe)
            serializer = ShoppingListSerializer(recipe,
                                                context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self.request.method == 'DELETE':
            shopping_list = get_object_or_404(ShopList, user=user,
                                              recipe=recipe)
            shopping_list.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, permission_classes=[IsAuthenticated, ])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=user).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')).annotate(
            amount=Sum('amount')
        )
        data = []
        for ingredient in ingredients:
            data.append(
                f'{ingredient["name"]} - '
                f'{ingredient["amount"]} '
                f'{ingredient["measurement_unit"]}'
            )
        content = 'Список покупок: \n\n' + '\n'.join(data)
        filename = 'purchases.txt'
        request = HttpResponse(content, content_type='text/plain')
        request['Content-Disposition'] = f'attachment; filename={filename}'
        return request

    def retrieve_by_slug(self, request, slug=None):
        print("QWEQWE:", slug)
        recipe = get_object_or_404(Recipe, slug=slug)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)
