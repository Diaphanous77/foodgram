from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Follow, User


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'author')
    list_filter = ('follower', 'author')
    search_fields = ('follower', 'author')


@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name'
    )
    list_filter = (
        'username',
        'email',
        'first_name',
        'last_name'
    )
    search_fields = (
        'username',
        'email',
    )
