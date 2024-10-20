from api.serializers import (FavoriteSerializer, IngredientSerializer,
                             RecipeGetSerializer, RecipePostSerializer,
                             RecipeShortSerializer, ShoppingListSerializer,
                             TagSerializer, UserAvatarSerializer,
                             UserGetSerializer, UserPostSerializer,
                             UserWithRecipesSerializer)
from django.contrib.auth import update_session_auth_hash
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShopList, Tag)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from users.models import Subscription, User

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
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
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        elif self.action in ['favorite', 'shopping_cart', ]:
            return RecipeShortSerializer
        elif self.request.method in ['POST', 'PATCH']:
            return RecipePostSerializer

    def get_queryset(self):
        request: Request = self.request
        if (is_in_shopping_cart := request.query_params.get(
                "is_in_shopping_cart")) is not None:
            if is_in_shopping_cart == '1':
                return super().get_queryset().filter(
                    shopping_cart__user=request.user
                )
        return super().get_queryset()

    def add_or_remove_item(self, request, pk, model, serializer_class):
        """Метод для добавления и удаления объектов."""
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
        return self.add_or_remove_item(
            request, pk, Favorite, FavoriteSerializer
        )

    @action(["POST", "DELETE"], detail=True)
    def shopping_cart(self, request, pk=None):
        return self.add_or_remove_item(
            request, pk, ShopList, ShoppingListSerializer
        )

    @action(detail=False, permission_classes=[IsAuthenticated, ])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=user).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')).annotate(
            total_amount=Sum('amount')
        )
        data = []
        for ingredient in ingredients:
            data.append(
                f'{ingredient["name"]} - '
                f'{ingredient["total_amount"]} '
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


class UserViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet,):
    queryset = User.objects.all()
    pagination_class = CustomPagination

    def get_instance(self):
        return self.request.user

    def get_serializer_class(self):
        if self.action == 'avatar':
            return UserAvatarSerializer
        if self.action in ['subscriptions', 'subscribe']:
            return UserWithRecipesSerializer
        elif self.request.method == 'GET':
            return UserGetSerializer
        elif self.request.method == 'POST':
            return UserPostSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, ]
        return super(self.__class__, self).get_permissions()

    @action(
        detail=False,
        permission_classes=[IsAuthenticated, ]
    )
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance

        return self.retrieve(request, *args, **kwargs)

    @action(
        ["POST"],
        detail=False,
        permission_classes=[IsAuthenticated, ]
    )
    def set_password(self, request, *args, **kwargs):
        serializer = SetPasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        self.request.user.set_password(
            serializer.validated_data['new_password']
        )
        self.request.user.save()

        update_session_auth_hash(self.request, self.request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated, ]
    )
    def subscriptions(self, request):
        users = User.objects.filter(
            following__user=request.user
        ).prefetch_related('recipes')
        page = self.paginate_queryset(users)

        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True,
                context={'request': request})

            return self.get_paginated_response(serializer.data)

        serializer = UserWithRecipesSerializer(
            users, many=True, context={'request': request}
        )

        return Response(serializer.data)

    @action(
        ["POST", "DELETE"],
        detail=True,
        permission_classes=[IsAuthorOrAdminOrReadOnly, ]
    )
    def subscribe(self, request, pk):
        user = self.request.user
        author = get_object_or_404(User, id=pk)

        if request.method == 'POST':
            Subscription.objects.get_or_create(user=user, author=author)
            serializer = self.get_serializer(author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = get_object_or_404(
            Subscription, user=user, author=author
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated, ],
        methods=['PUT'],
        url_path='me/avatar'
    )
    def avatar(self, request, *args, **kwargs):
        user = self.get_instance()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
