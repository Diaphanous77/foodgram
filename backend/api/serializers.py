import base64

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import Follow

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(default=False)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'username',
            'avatar',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'id'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None:
            return False
        user = request.user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(follower=user, author=obj).exists()


class UserSetImageSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class FollowSerializer(UserSerializer):

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'username',
            'id',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.id)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = BriefDescriptionRecipeSerializer(recipes,
                                                      many=True,
                                                      read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.id).count()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug'
        )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'

    def validate(self, data):
        user = self.context.get('request').user
        recipe = data.get('recipe')
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в избранное')
        return data


class BriefDescriptionRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class RecipesSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, read_only=True, source='recipe_ingredient')

    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    def get_is_favorited(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Favorite.objects.filter(
                user=self.context.get('request').user,
                recipe=obj
            ).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and ShoppingCart.objects.filter(
                user=self.context.get('request').user,
                recipe=obj
            ).exists()
        )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart',
        )


class CreateRecipesIngredientsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'amount'
        )


class CreateRecipesSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = CreateRecipesIngredientsSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
            'author'
        )

    def validate(self, data):
        if not data.get('ingredients'):
            raise ValidationError('Нужно добавить хотя бы один ингредиент!')
        if not data.get('tags'):
            raise ValidationError('Нужно добавить хотя бы один тег!')

        ingredients_list = data['ingredients']
        ingredients = []

        for ingredient in ingredients_list:
            if not Ingredient.objects.filter(id=ingredient['id']).exists():
                raise ValidationError('Такого ингредиента не существует!')
            ingredients.append(ingredient['id'])
            if ingredients.count(ingredient['id']) > 1:
                raise ValidationError(
                    'Невозможно добавить два одинаковых ингредиента!'
                )

        tags_list = data['tags']
        tags = []
        for tag in tags_list:
            if tag in tags:
                raise ValidationError('Невозможно добавить два '
                                      'одинаковых тега!')
            tags.append(tag)
        return data

    def bulk_create_update(self, ingredients, recipe):
        ingredient_list = []
        for ingredient in ingredients:
            ingredient_list.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount')
                )
            )
        RecipeIngredient.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.bulk_create_update(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.bulk_create_update(ingredients, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipesSerializer(instance, context=self.context).data
