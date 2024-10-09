from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint


class User(AbstractUser):
    username = models.CharField(
        'Логин',
        max_length=150,
        blank=False,
        unique=True,
    )

    first_name = models.CharField(
        'Имя пользователя',
        max_length=150,
        blank=False
    )
    last_name = models.CharField(
        'Фамилия пользователя',
        max_length=150,
        blank=False
    )
    password = models.CharField(
        'Пароль',
        max_length=150,
        blank=False
    )
    email = models.EmailField(
        max_length=254,
        blank=False,
        unique=True
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    @property
    def is_admin(self):
        return self.is_superuser

    class Meta:
        ordering = ['id']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Подписки на авторов."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор, на которого подписываются',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            UniqueConstraint(fields=['user', 'author'],
                             name='unique_subscription')
        ]
