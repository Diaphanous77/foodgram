from api.fields import Base64ImageField
from django.core.validators import MaxValueValidator, MinValueValidator
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShopList, Tag)
from rest_framework import serializers
from users.models import Subscription
from django.db.models import Model, Q
from rest_framework.response import Response
from users.models import User
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import status
from rest_framework.exceptions import ValidationError


class UserGetSerializer(UserSerializer):
    """Сериализатор для просмотра профиля пользователя."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False

        return Subscription.objects.filter(
            author=obj, user=request.user
        ).exists()


class UserWithRecipesSerializer(UserGetSerializer):
    """Сериализатор для просмотра пользователя с рецептами."""
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = UserGetSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )

    def validate(self, data):
        author = self.instance
        user = self.context.get('request').user
        if Subscription.objects.filter(author=author, user=user).exists():
            raise ValidationError(
                detail='Вы уже подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user == author:
            raise ValidationError(
                detail='Нельзя подписаться на самого себя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, object):
        request = self.context.get('request')
        context = {'request': request}
        recipe_limit = request.query_params.get('recipe_limit')
        queryset = object.recipes.all()
        if recipe_limit:
            queryset = queryset[:int(recipe_limit)]
        return RecipeShortSerializer(queryset, context=context, many=True).data


class UserPostSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""
    class Meta:
        model = User
        fields = ('id',
                  'username',
                  'first_name',
                  'last_name',
                  'password',
                  'email',
                  'avatar',
                  )

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления аватара пользователя."""
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ['avatar']


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

    def is_obj_exists_if_not_anonymous(self, model: Model, filter_query: Q) -> bool:
        request = self.context.get("request")
        if request.user.is_anonymous:
            return False
        return model.objects.filter(filter_query).exists()
    
    def get_request(self) -> Response:
        return self.context.get("request")
    
    def get_user(self):
        return self.get_request().user

    def get_is_favorited(self, obj):
        return self.is_obj_exists_if_not_anonymous(Favorite, Q(recipe=obj) & Q(user=self.get_user()))

    def get_is_in_shopping_cart(self, obj):
        return self.is_obj_exists_if_not_anonymous(ShopList, Q(recipe=obj) & Q(user=self.get_user()))

    def get_slug_url(self, obj):
        """Генерирует полный URL для поля slug."""
        request = self.get_request()
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
        ingredients = validated_data.pop('IngredientInRecipe', [])
        tags = validated_data.pop('tags', [])
        
        super().update(instance, validated_data)
        
        instance.tags.clear()
        instance.tags.add(*tags)

        instance.ingredients.clear()
        self.save_ingredients(instance, ingredients)

        instance.save()
        return instance


    def to_representation(self, instance):
        serializer = RecipeGetSerializer(
            instance,
            context={'request': self.context.get('request')}
        )
        return serializer.data

    def validate_ingredients(self, ingredients):
        ingredient_ids = [ingredient['ingredient']['id'] for ingredient
                          in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны дублироваться.')
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


class RecipeShortSerializer(serializers.ModelSerializer):
    '''Сериализатор для отображения краткой информации о рецептах.'''

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )