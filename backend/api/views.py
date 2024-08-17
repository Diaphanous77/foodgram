from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from djoser import views
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

from .filters import RecipeFilter
from .pagination import CustomPagination
from .permissions import AccessDenied, IsAuthorOrReadOnly
from .serializers import (CreateRecipesSerializer, FollowSerializer,
                          IngredientSerializer, RecipesSerializer,
                          ShortRecipeDescriptionSerializer, TagSerializer,
                          UserSerializer, UserSetImageSerializer)

User = get_user_model()


class UserViewSet(views.UserViewSet):
    queryset = User.objects.all().order_by('id')
    pagination_class = CustomPagination
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'create', 'retrieve']:
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @action(detail=False, methods=['get'],)
    def me(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], )
    def subscriptions(self, request):
        queryset = self.get_queryset()
        queryset = queryset.filter(following__follower=request.user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(pages, many=True,
                                      context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],)
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            if user == author:
                return Response('Невозможно подписаться на самого себя',
                                status=status.HTTP_400_BAD_REQUEST)
            if Follow.objects.filter(follower=user, author=author).exists():
                return Response('Вы уже подписаны на этого автора',
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = FollowSerializer(
                author,
                context={"request": request, }
            )
            Follow.objects.create(
                follower=user,
                author=author
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if not Follow.objects.filter(follower=user, author=author).exists():
            return Response(
                'Такой подписки нет',
                status=status.HTTP_400_BAD_REQUEST
            )
        subscribe = get_object_or_404(Follow, follower=user, author=author)
        subscribe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',)
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            if request.data.get('avatar') is None:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            serializer = UserSetImageSerializer(
                user,
                data=request.data,
                partial=True
            )
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_200_OK)
            if request.body is None:
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    search_fields = ('name',)
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('name',)


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-pub_date')
    pagination_class = CustomPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update']:
            return CreateRecipesSerializer
        return RecipesSerializer

    def perform_create(self, serializer, *args, **kwargs):
        user = self.request.user
        if user.is_anonymous:
            raise AccessDenied()
        serializer.save(author=self.request.user)

    def add_or_delete(self, model, pk, message, request):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        related_recipe = model.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if related_recipe.exists():
                return Response(
                    message,
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(
                user=user,
                recipe=recipe
            )
            serializer = ShortRecipeDescriptionSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if related_recipe.exists():
            related_recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk):
        return self.add_or_delete(
            Favorite,
            pk,
            'Рецепт уже добавлен в избранное.',
            request
        )

    @action(
        detail=True,
        methods=['post', 'delete']
    )
    def shopping_cart(self, request, pk):
        return self.add_or_delete(
            ShoppingCart,
            pk,
            'Ингредиенты из рецепта уже добавлены в список покупок',
            request
        )

    @action(
        detail=False,
        methods=['get'],
    )
    def download_shopping_cart(self, request):
        user = request.user
        recipes = ShoppingCart.objects.filter(user=user).values_list('recipe')
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in=recipes
            ).values(
                'ingredient'
            ).annotate(
                quantity=Sum('amount')
            ).values_list(
                'ingredient__name',
                'quantity',
                'ingredient__measurement_unit',
            )
        )
        shopping_list = []
        for ingredient in ingredients:
            name, value, unit = ingredient
            shopping_list.append(
                f'{name}, {value} {unit}'
            )
        shopping_list = '\n'.join(shopping_list)

        filename = 'Shopping_list.csv'
        response = HttpResponse(shopping_list, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    @action(
        methods=['get'],
        detail=True,
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request):
        recipe = self.get_object()
        encode_id = baseconv.base64.encode(recipe.id)
        short_link = request.build_absolute_uri(
            reverse('shortlink', kwargs={'encoded_id': encode_id})
        )
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class ShortLinkView(APIView):
    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Недопустимые символы в короткой ссылке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe_id = baseconv.base64.decode(encoded_id)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        return HttpResponseRedirect(
            request.build_absolute_uri(
                f'/api/recipes/{recipe.id}/'
            )
        )
