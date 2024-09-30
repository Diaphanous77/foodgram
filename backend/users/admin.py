from django.contrib import admin
from recipes.models import Favorite, ShopList

from .models import Subscription, User


class SubsInLine(admin.TabularInline):
    model = Subscription
    fk_name = 'user'
    extra = 1


class FavoriteInLine(admin.TabularInline):
    model = Favorite
    fk_name = 'user'
    extra = 1


class ShoplistInLine(admin.TabularInline):
    model = ShopList
    fk_name = 'user'
    extra = 1


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'password',
        'role',
    )
    search_fields = ('username',)
    list_filter = ('username', 'email')
    inlines = (SubsInLine, FavoriteInLine, ShoplistInLine,)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')


admin.site.register(User, UserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
