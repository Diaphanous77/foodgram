from rest_framework import permissions, status
from rest_framework.exceptions import APIException


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class PermissionDenied(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Нет авторизации'
    default_code = 'Unauthorized'
