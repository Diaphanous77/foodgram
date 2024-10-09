from django.contrib import admin
from django.contrib.auth.models import Group
from .models import Ingredient, Tag, Recipe, IngredientInRecipe, Favorite, ShopList


class IngredientsInLine(admin.TabularInline):
    model = Recipe.ingredients.through


class IngredientAdmin(admin.ModelAdmin):
    """Ингредиенты"""
    list_display = ('pk', 'name', 'measurement_unit')


class IngredienInRecipeAdmin(admin.ModelAdmin):
    """Ингредиенты в рецептах"""
    list_display = ('recipe', 'ingredient', 'amount')


class FavoriteAdmin(admin.ModelAdmin):
    """Избранные пельмени"""
    list_display = ('user', 'recipe')


class TagAdmin(admin.ModelAdmin):
    """ Настройка отображения тэгов в админке"""
    list_display = ('pk', 'name', 'slug')


class RecipeAdmin(admin.ModelAdmin):
    """Рецепты"""
    list_display = (
        'name', 'author', 'pub_date',
    )
    list_filter = ('name', 'author',)
    search_fields = ('name',)
    inlines = (IngredientsInLine,)


class ShopListAdmin(admin.ModelAdmin):
    """Покупки"""
    list_display = ('user', 'recipe')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(IngredientInRecipe, IngredienInRecipeAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShopList, ShopListAdmin)
admin.site.unregister(Group)
