from django.contrib import admin
from django.contrib.auth.models import Group

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShopList, Tag)


class IngredientsInLine(admin.TabularInline):
    model = Recipe.ingredients.through


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'measurement_unit')


class IngredienInRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


class TagAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'slug')


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'author', 'pub_date',
    )
    list_filter = ('name', 'author',)
    search_fields = ('name',)
    inlines = (IngredientsInLine,)


class ShopListAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(IngredientInRecipe, IngredienInRecipeAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShopList, ShopListAdmin)
admin.site.unregister(Group)
