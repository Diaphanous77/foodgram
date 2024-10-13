from rest_framework import serializers
from recipes.models import (Ingredient, Tag, Recipe,
                            IngredientInRecipe, Favorite, ShopList)
from django.core.validators import MaxValueValidator, MinValueValidator

from users.models import Subscription
from users.serializers import UserGetSerializer
from api.fields import Base64ImageField


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""
    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Subscription
        fields = ('author', 'user')
        message = 'вы уже подписаны на данного автора'

    def create(self, validated_data):
        return Subscription.objects.create(
            user=self.context.get('request').user, **validated_data)

    def validate_author(self, value):
        if self.context.get('request').user == value:
            raise serializers.ValidationError({
                'errors': 'Подписка на самого себя не возможна!'
            })
        return value


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = ('id',
                  'name',
                  'measurement_unit',
                  'amount')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения ингредиентов в рецептах."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient.id'
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(
        # source='ingredientinrecipe.amount',
        # read_only=True,
        validators=[
            MinValueValidator(1, message='Кол-во не может быть меньше 1'),
            MaxValueValidator(700, message='Кол-во не может быть более 700')
        ]
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id',
                  'name',
                  'measurement_unit',
                  'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""
    class Meta:
        model = Tag
        fields = ('id',
                  'name',
                  'slug')


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe и GET запросов к /recipe/
    /recipe/id/.
    """
    tags = TagSerializer(many=True, read_only=True)
    author = UserGetSerializer()
    ingredients = IngredientInRecipeSerializer(
        source='IngredientInRecipe',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    slug_url = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time', 'slug',
                  'slug_url',)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False

        return Favorite.objects.filter(recipe=obj, user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False

        return ShopList.objects.filter(
            recipe=obj, user=request.user
        ).exists()

    def get_slug_url(self, obj):
        """Генерирует полный URL для поля slug."""
        request = self.context.get('request')
        if request is None:
            return None
        return request.build_absolute_uri(f'/api/recipe/{obj.slug}/')


class RecipePostSerializer(serializers.ModelSerializer):
    """Модель для создания рецептов."""
    author = UserGetSerializer(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientInRecipeSerializer(
        source='IngredientInRecipe',
        many=True
    )
    image = Base64ImageField(
        required=False,
        allow_null=True
    )
    amount = serializers.IntegerField(
        required=False,
        validators=[
            MinValueValidator(1, message='Кол-во не может быть меньше 1'),
            MaxValueValidator(700, message='Кол-во не может быть более 700')
        ]
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'amount', 'ingredients', 'name',
                  'image', 'text', 'cooking_time')

    @staticmethod
    def save_ingredients(recipe, ingredients):
        ingredients_list = []
        for ingredient in ingredients:
            current_ingredient = ingredient['ingredient']['id']
            current_amount = ingredient.get('amount')

            ingredients_list.append(
                IngredientInRecipe(
                    recipe=recipe,
                    ingredient=current_ingredient,
                    amount=current_amount
                )
            )
        IngredientInRecipe.objects.bulk_create(ingredients_list)

    def validate_cooking_time(self, cooking_time):
        if cooking_time < 1:
            raise serializers.ValidationError(
                'Время готовки должно быть не меньше одной минуты')
        return cooking_time

    def create(self, validated_data):
        author = self.context.get('request').user
        ingredients = validated_data.pop('IngredientInRecipe')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data, author=author)
        recipe.tags.add(*tags)
        self.save_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('IngredientInRecipe')

        tags = validated_data.pop('tags')
        instance.name = validated_data.pop('name')
        instance.text = validated_data.pop('text')
        instance.cooking_time = validated_data.pop('cooking_time')
        instance.tags.clear()
        instance.tags.add(*tags)
        instance.ingredients.clear()
        recipe = instance
        self.save_ingredients(recipe, ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        serializer = RecipeGetSerializer(
            instance,
            context={'request': self.context.get('request')}
        )
        return serializer.data
    
    def validate_ingredients(self, ingredients):
        ingredient_ids = [ingredient['ingredient']['id'] for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError('Ингредиенты не должны дублироваться.')
        return ingredients

    def validate_tags(self, tags):
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги не должны дублироваться.')
        return tags


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных рецептов."""
    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault())
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Favorite
        fields = ('recipe', 'user', )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=['recipe', 'user', ],
                message='Этот рецепт уже добавлен в избранное.'
            )
        ]

    def create(self, validated_data):
        return Favorite.objects.create(
            user=self.context.get('request').user, **validated_data)


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ShopList
        fields = ('recipe', 'user',)
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ShopList.objects.all(),
                fields=['recipe', 'user', ],
                message='Этот рецепт уже добавлен в список покупок.'
            )
        ]

    def create(self, validated_data):
        return ShopList.objects.create(
            user=self.context.get('request').user, **validated_data)
