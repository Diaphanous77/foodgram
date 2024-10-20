from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter

from recipes.models import Recipe, Tag


class IngredientFilter(SearchFilter):
    """Фильтра для ингредиентов."""
    search_param = 'name'


class RecipeFilter(filters.FilterSet):
    """Фильтр для рецептов по избранному, списку покупок, автору и тэгам."""
    author = filters.CharFilter(method='filter_by_author')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        queryset=Tag.objects.all(),
        label='Tags',
        to_field_name='slug'
    )
    is_favorited = filters.BooleanFilter(method='get_favorite')
    is_in_shopping_cart = filters.BooleanFilter(method='get_is_in_shopping_cart')

    def get_favorite(self, queryset, name, value):
        if value:
            return queryset.filter(Favorite__user=self.request.user)
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        if value:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset

    def filter_by_author(self, queryset, name, value):
        try:
            author_id = int(value)
            return queryset.filter(author=author_id)
        except ValueError:
            return queryset

    class Meta:
        model = Recipe
        fields = ['tags', 'author', 'is_favorited', 'is_in_shopping_cart']