from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from recipes.models import (Tag, Recipe, Favorite,
                            ShopList, IngredientInRecipe,
                            Ingredient)
from api.serializers import (IngredientSerializer, TagSerializer,
                             RecipeGetSerializer, FavoriteSerializer,
                             RecipePostSerializer, ShoppingListSerializer,
                             )
from users.serializers import RecipeShortSerializer
from .permissions import IsAuthorOrAdminOrReadOnly
from .pagination import CustomPagination
from .filters import IngredientFilter, RecipeFilter


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
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        elif self.action in ['favorite', 'shopping_cart', ]:
            return RecipeShortSerializer
        elif self.request.method in ['POST', 'PATCH']:
            return RecipePostSerializer

    def add_or_remove_item(self, request, pk, model, serializer_class):
        """метод для добавления и удаления объектов."""
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if self.request.method == "POST":
            model.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        item = get_object_or_404(model, user=user, recipe=recipe)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["POST", "DELETE"], detail=True)
    def favorite(self, request, pk=None):
        return self.add_or_remove_item(request, pk, Favorite, FavoriteSerializer)

    @action(["POST", "DELETE"], detail=True)
    def shopping_cart(self, request, pk=None):
        return self.add_or_remove_item(request, pk, ShopList, ShoppingListSerializer)

    @action(detail=False, permission_classes=[IsAuthenticated, ])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=user).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')).annotate(
            amount_total=Sum('amount')
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
        recipe = get_object_or_404(Recipe, slug=slug)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)
