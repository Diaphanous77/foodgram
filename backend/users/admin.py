from django.contrib import admin
from recipes.models import Favorite, ShopList
from .models import User, Subscription


class SubsInLine(admin.TabularInline):
    """Подписки"""
    model = Subscription
    fk_name = 'user'
    extra = 1


class FavoriteInLine(admin.TabularInline):
    """Избранное"""
    model = Favorite
    fk_name = 'user'
    extra = 1


class ShoplistInLine(admin.TabularInline):
    """Покупки"""
    model = ShopList
    fk_name = 'user'
    extra = 1


class UserAdmin(admin.ModelAdmin):
    """Пользователи"""
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'password',
    )
    search_fields = ('username',)
    list_filter = ('username', 'email')
    inlines = (SubsInLine, FavoriteInLine, ShoplistInLine,)


class SubscriptionAdmin(admin.ModelAdmin):
    """Подписки пользователя"""
    list_display = ('user', 'author')


admin.site.register(User, UserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
