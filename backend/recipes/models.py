import shortuuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint
from users.models import User


class Ingredient(models.Model):
    """Ингредиенты и их количество для составления рецепта
       с указанием единиц измерения.
    """
    name = models.CharField(
        'Название ингредиента',
        max_length=200,
        blank=False
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=100,
        blank=False
    )
    amount = models.IntegerField(
        'Количество ингредиентов в данном рецепте',
        null=True,
        validators=[
            MaxValueValidator(700),
            MinValueValidator(1)
        ]
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name} в {self.measurement_unit}'


class Tag(models.Model):
    """Тэги."""
    name = models.CharField(
        'Тэг',
        unique=True,
        max_length=200,
        blank=False
    )
    slug = models.SlugField(unique=True, blank=False, db_index=True,)

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Рецепт."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        blank=False
    )
    name = models.CharField(
        'Название',
        max_length=200,
        blank=False
    )
    image = models.ImageField(
        'Картинка',
        upload_to='recipes/images/',
    )
    text = models.TextField(
        'Описание рецепта',
        blank=False
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        related_name='recipes',
        blank=False
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        blank=False
    )
    cooking_time = models.IntegerField(
        'Время приготовления, мин',
        blank=False,
        validators=[
            MinValueValidator(
                1, 'Время приготовление должно быть не менее минуты'
            )
        ]
    )
    pub_date = models.DateField(
        'Дата создания',
        auto_now_add=True
    )

    slug = models.SlugField(
        'Ссылка',
        max_length=50,
        unique=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            # генерация короткой ссылки
            self.slug = shortuuid.uuid()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """Связь рецепта и ингредиентов."""
    recipe = models.ForeignKey(
        Recipe,
        related_name='IngredientInRecipe',
        on_delete=models.CASCADE,
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='IngredientInRecipe',
        on_delete=models.CASCADE
    )
    amount = models.IntegerField(
        'Количество ингредиентов в данном рецепте',
        null=False,
        validators=[
            MaxValueValidator(700, "Кол-во не может быть более 700"),
            MinValueValidator(1, "Кол-во не может быть меньше 1")
        ]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        constraints = [
            UniqueConstraint(fields=['recipe', 'ingredient'], name="unique_ingredient_in_recipe")
        ]

    def __str__(self):
        return f'{self.ingredient.name} в рецепте {self.recipe.name}'


class Favorite(models.Model):
    """Избанное."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='Favorite',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='Favorite',
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            UniqueConstraint(fields=['user', 'recipe'], name='unique_favorite')
        ]

    def __str__(self):
        return f'{self.recipe.name} в избранном {self.user.username}'


class ShopList(models.Model):
    """Список покупок."""
    user = models.ForeignKey(
        User,
        related_name='ShoppingRecipe',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='shopping_cart',
        on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Рецепт в списке покупок'
        verbose_name_plural = 'Рецепты в списке покупок'
        constraints = [
            UniqueConstraint(fields=['user', 'recipe'],
                             name='unique_shopping_cart')
        ]

    def __str__(self):
        return f'{self.recipe.name} в списке покупок у {self.user.username}'
